import copy
import json
import logging
import random
import re
from datetime import datetime, timedelta
from decimal import Decimal

import requests
from django.db.models import Q, Sum, Max, Min, Count, F
from django.db.transaction import atomic
from django.db.utils import ConnectionDoesNotExist
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from basics.models import WorkSchedulePlan, GlobalCode
from inventory.models import MixGumOutInventoryLog, DepotPallt
from mes import settings
from mes.base_serializer import BaseModelSerializer
from mes.conf import COMMON_READ_ONLY_FIELDS, JZ_EQUIP_NO
from plan.models import ProductClassesPlan, BatchingClassesPlan, BatchingClassesEquipPlan
from production.models import PalletFeedbacks
from recipe.models import ERPMESMaterialRelation, ProductBatchingDetail, \
    ProductBatchingEquip, ProductBatchingDetailPlan
from terminal.models import EquipOperationLog, WeightBatchingLog, FeedingLog, WeightTankStatus, \
    WeightPackageLog, FeedingMaterialLog, LoadMaterialLog, MaterialInfo, Bin, Plan, RecipePre, ReportBasic, \
    ReportWeight, LoadTankMaterialLog, PackageExpire, RecipeMaterial, CarbonTankFeedWeightSet, \
    FeedingOperationLog, CarbonTankFeedingPrompt, PowderTankSetting, OilTankSetting, ReplaceMaterial, ReturnRubber, \
    ToleranceRule, WeightPackageManual, WeightPackageManualDetails, WeightPackageSingle, OtherMaterialLog, \
    WeightPackageWms, MachineManualRelation, WeightPackageLogDetails, WeightPackageLogManualDetails, WmsAddPrint, \
    JZMaterialInfo, JZBin, JZPlan, JZRecipeMaterial, JZRecipePre, JZExecutePlan
from terminal.utils import TankStatusSync, CLSystem, material_out_barcode, get_tolerance, get_common_equip, get_real_ip, \
    JZTankStatusSync, JZCLSystem, send_dk

logger = logging.getLogger('send_log')


def generate_bra_code(equip_no, factory_date, classes):
    # 后端生成，工厂编码E101 + 称量机台号 + 小料计划的工厂日期8位 + 班次1 - 3 + 四位随机数。
    # 重复打印条码规则不变，重新生成会比较麻烦，根据修改的工厂时间班次来生成，序列号改成字母。从A~Z
    random_str = ['z', 'y', 'x', 'w', 'v', 'u', 't', 's', 'r',
                  'q', 'p', 'o', 'n', 'm', 'l', 'k', 'j', 'i',
                  'h', 'g', 'f', 'e', 'd', 'c', 'b', 'a',
                  '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    classes_dict = {'早班': '1', '中班': '2', '夜班': '3'}
    return 'E101{}{}{}{}'.format(equip_no, ''.join(str(factory_date).split('-')),
                                 classes_dict[classes],
                                 ''.join(random.sample(random_str, 4)))


class LoadMaterialLogSerializer(BaseModelSerializer):
    product_no = serializers.ReadOnlyField(source='feed_log.product_no')
    created_date = serializers.DateTimeField(source='feed_log.feed_begin_time')
    trains = serializers.ReadOnlyField(source='feed_log.trains')

    class Meta:
        model = LoadMaterialLog
        fields = '__all__'


class LoadMaterialLogUpdateSerializer(BaseModelSerializer):
    adjust_left_weight = serializers.DecimalField(write_only=True, decimal_places=2, max_digits=8)

    class Meta:
        model = LoadTankMaterialLog
        fields = ['adjust_left_weight']


class LoadMaterialLogCreateSerializer(BaseModelSerializer):
    bra_code = serializers.CharField(write_only=True)

    def validate(self, attrs):
        # 条码来源有三种，wms子系统、收皮条码，称量打包条码
        bra_code = attrs['bra_code']
        plan_classes_uid = attrs['plan_classes_uid']
        # 非胶皮、不加硫、抛出正常扫码信息
        scan_material_type, add_s, scan_material_msg = '胶块', False, ''
        # 是否走进物料在配方里的判断、是否发送到群控, 物料是否走入在配方中的判断
        flag, send_flag, material_in_flag = True, True, True
        # 物料编码、物料名称、物料重量、单位、扫码物料
        material_no, material_name, total_weight, unit, scan_material = None, None, 0, 'KG', ''
        now_date = datetime.now()
        # 计划号中存在条码
        is_used = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, bra_code=bra_code)
        if is_used:
            raise serializers.ValidationError('同一计划中不可多次扫同一条码')
        common_xl = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, scan_material_type__in=['机配', '人工配', '细料', '硫磺'])
        if common_xl and bra_code.startswith('TYLB'):
            raise serializers.ValidationError('本计划不可扫通用料包')
        common_scan = OtherMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, other_type='通用料包', status=1)
        if common_scan and (bra_code.startswith('S') or bra_code.startswith('F') or bra_code.startswith('MM')):
            raise serializers.ValidationError('本计划只能扫通用料包')
        # 获取计划
        classes_plan = ProductClassesPlan.objects.filter(plan_classes_uid=plan_classes_uid).first()
        if not classes_plan:
            raise serializers.ValidationError('该计划不存在')
        # 获取机型  check_used获取扫码限制使用
        scan_dev = classes_plan.equip.category.category_name
        # 获取配方信息
        material_name_weight, cnt_type_details = classes_plan.product_batching.get_product_batch(classes_plan)
        if not material_name_weight:
            raise serializers.ValidationError(f'获取配方详情失败:{classes_plan.product_batching.stage_product_batch_no}')
        detail_infos = {i['material__material_name']: i['actual_weight'] for i in material_name_weight}
        for i in material_name_weight:
            if i['material__material_name'] in ['硫磺', '细料']:
                if not cnt_type_details:
                    raise serializers.ValidationError('未找到MES配方')
                detail_infos[i['material__material_name']] = sum([i['actual_weight'] for i in cnt_type_details])
            else:
                detail_infos[i['material__material_name']] = i['actual_weight']
        materials = detail_infos.keys()
        if bra_code.startswith('TYLB'):  # 2号细料与3号硫磺设备对接前扫通用条码
            xl_recipe = [i for i in material_name_weight if i['material__material_name'] in ['硫磺', '细料']]
            if xl_recipe:  # 需要料包
                OtherMaterialLog.objects.create(**{'plan_classes_uid': plan_classes_uid, 'product_no': classes_plan.product_batching.stage_product_batch_no,
                                                   'material_name': '通用料包', 'bra_code': bra_code, 'status': 1, 'other_type': '通用料包'})
                raise serializers.ValidationError('通用料包扫码成功')
            else:
                common_scan = OtherMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, other_type='通用料包', status=1)
                if common_scan:
                    raise serializers.ValidationError('已经扫过通用料包条码')
                else:
                    raise serializers.ValidationError('配方不需要使用料包')
        elif bra_code.startswith('AAJ1Z'):  # 胶皮
            scan_material_type = '胶皮'
            if bra_code.startswith('AAJ1Z20'):  # 补打胶皮
                return_rubber = ReturnRubber.objects.filter(bra_code=bra_code).last()
                if return_rubber:
                    add_s = True if return_rubber.print_type == '加硫' else False
                    material_no = return_rubber.product_no
                    material_name = material_no
                    scan_material = material_no
                    # 原意当作掺料使用, 修改: 当前生产胶皮与卡片一致, 默认重量600公斤(300公斤一车, 默认2车)
                    total_weight = Decimal(320 * (return_rubber.end_trains - return_rubber.begin_trains + 1)) if material_no in materials else 0
            else:  # 收皮条码
                pallet_feedback = PalletFeedbacks.objects.filter(lot_no=bra_code).first()
                if pallet_feedback:
                    if re.findall('FM|RFM|RE', pallet_feedback.product_no):
                        add_s = True
                    # 配方中含有种子胶
                    seed = [i for i in materials if '种子胶' in i]
                    if seed and pallet_feedback.product_no == classes_plan.product_batching.stage_product_batch_no:
                        material_no = seed[0]
                        material_name = seed[0]
                        scan_material = pallet_feedback.product_no
                    else:
                        material_no = pallet_feedback.product_no
                        material_name = pallet_feedback.product_no
                        scan_material = material_name
                    total_weight = pallet_feedback.actual_weight
                    unit = unit
                    DepotPallt.objects.filter(pallet_data__lot_no=bra_code).update(outer_time=now_date, pallet_status=2)
        elif len(bra_code) > 12 and bra_code[12] in ['H', 'Z']:  # 胶皮补打
            start_time = f'20{bra_code[:2]}-{bra_code[2:4]}-{bra_code[4:6]} {bra_code[6:8]}:{bra_code[8:10]}:{bra_code[10:12]}'
            end_time = str(datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S') + timedelta(seconds=1))
            location = f'{bra_code[13]}-{bra_code[14]}-{bra_code[15: len(bra_code) - 1]}-{bra_code[-1]}'
            db_name = 'bz' if bra_code[12] == 'H' else 'lb'
            instance = MixGumOutInventoryLog.objects.using(db_name).filter(location=location, start_time__gte=start_time, start_time__lte=end_time).last()
            if instance:
                scan_material_type = '胶皮'
                if db_name == 'lb':
                    add_s = True
                material_no = instance.material_no
                material_name = instance.material_no
                total_weight = instance.weight
                unit = unit
                attrs['scan_material'] = material_name
        elif bra_code.startswith('S') or bra_code.startswith('F'):  # 料包称量履历
            weight_package = WeightPackageLog.objects.filter(bra_code=bra_code).first()
            if weight_package:
                scan_material_type = '机配'
                material_no = material_name = weight_package.material_name
                total_weight = weight_package.package_count * weight_package.split_count
                unit = '包'
                scan_material = material_no
        elif bra_code.startswith('MM'):  # 人工配
            manual = WeightPackageManual.objects.filter(bra_code=bra_code).first()
            if manual and manual.real_count != 0:
                material_no = material_name = manual.manual_weight_names
                # 扫过原材料小料码则不能扫入人工单配该物料码(粘合剂KY-7A-C)
                wms_xl_material = OtherMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, status=1,
                                                                  other_type='原材料小料', material_name__in=material_name.keys())
                if wms_xl_material:
                    raise serializers.ValidationError('已经扫入原材料小料，不可再扫该物料人工单配')
                material_name.update({'single_weight': Decimal(manual.split_num)})
                scan_material_type = '人工配'
                total_weight = manual.split_num * manual.real_count
                unit = '包'
                scan_material = manual.product_no
        elif bra_code.startswith('MC'):  # 人工配(油料、CTP、配方物料)[隶属原材料胶块]
            single = WeightPackageSingle.objects.filter(bra_code=bra_code).first()
            if single:
                scan_material = single.material_name
                # 扫过原材料小料码则不能扫入人工单配该物料码(粘合剂KY-7A-C)
                wms_xl_material = OtherMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, status=1,
                                                                  other_type='原材料小料', material_name=scan_material)
                if wms_xl_material:
                    raise serializers.ValidationError('已经扫入原材料小料，不可再扫该物料人工单配')
                # 查询配方中对应名称[扫码:环保型塑解剂, 群控: 环保型塑解剂-C]
                mes_recipe = {i[:-2]: i for i in materials if i.endswith('-C') or i.endswith('-X')}
                material_name = mes_recipe[single.material_name] if single.material_name in mes_recipe else single.material_name
                material_no = material_name
                total_weight = single.package_count * single.split_num if single.batching_type == '配方' else single.package_count
                unit = '包'
        elif bra_code.startswith('WMS'):
            wms = WmsAddPrint.objects.filter(bra_code=bra_code).first()
            if wms:
                scan_material_type = '胶皮'
                scan_material = wms.material_name
                # 查询配方中对应名称[扫码:环保型塑解剂, 群控: 环保型塑解剂-C]
                mes_recipe = {i[:-2]: i for i in materials if i.endswith('-C') or i.endswith('-X')}
                material_name = mes_recipe[wms.material_name] if wms.material_name in mes_recipe else wms.material_name
                material_no = material_name
                total_weight = wms.single_weight
                unit = 'KG'
        else:  # 总厂胶块:查原材料出库履历查到原材料物料编码
            try:
                res = material_out_barcode(bra_code) if not settings.DEBUG else None
            except Exception as e:
                raise serializers.ValidationError(e)
            if res:
                scan_material = res.get('WLMC')
                material_name_set = set(ERPMESMaterialRelation.objects.filter(zc_material__wlxxid=res['WLXXID'], use_flag=True).values_list('material__material_name', flat=True))
                if not material_name_set:
                    raise serializers.ValidationError('该物料未与MES原材料建立绑定关系！')
                cnt_names = [i.get('material__material_name') for i in cnt_type_details]
                same_cnt = list(material_name_set & set(cnt_names))
                if same_cnt:
                    material_name = same_cnt[0]
                    # 已经通过单配扫入并且没有使用完则不能扫原材料小料条码
                    load_material = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid,
                                                                       material_name=material_name,
                                                                       useup_time__year='1970')
                    if load_material:
                        raise serializers.ValidationError(f'该物料已经扫过人工单配{material_name}')
                    # 去除原材料小料(群控扣重时需要去除原材料小料物料[mes返回标准内])
                    wms_xl_material = OtherMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, status=1,
                                                                      other_type='原材料小料', bra_code=bra_code)
                    if wms_xl_material:
                        raise serializers.ValidationError('原材料小料条码已经扫过')
                    OtherMaterialLog.objects.create(**{'plan_classes_uid': plan_classes_uid, 'other_type': '原材料小料',
                                                       'product_no': classes_plan.product_batching.stage_product_batch_no,
                                                       'material_name': material_name, 'bra_code': bra_code,
                                                       'status': 1})
                    raise serializers.ValidationError('原材料小料扫码成功')
                comm_material = list(material_name_set & materials)
                if comm_material:
                    material_name = comm_material[0]
                    material_no = comm_material[0]
                else:  # 胶块替代(1、不能通过直接绑定erp替代; 2、增加这段逻辑确保替代胶块能走到下面物料是否在配方中判断)
                    material_name = scan_material
                    material_no = scan_material
                total_weight = Decimal(res.get('ZL'))
                unit = res.get('BZDW')
        if not material_name:
            raise serializers.ValidationError('未找到该条形码信息！')
        # 适配掺料、待处理料放行
        if scan_material_type == '胶皮':
            s_result = self.material_pass(plan_classes_uid, scan_material, material_type=scan_material_type)
            if s_result[0]:
                material_no = material_name = s_result[1]
                # attrs.update({'material_no': material_no, 'material_name': material_name})
        attrs['equip_no'] = classes_plan.equip.equip_no
        attrs['material_name'] = material_name
        attrs['material_no'] = material_no
        attrs['tank_data'] = {'msg': '', 'bra_code': bra_code, 'init_weight': total_weight, 'scan_time': str(now_date),
                              'useup_time': '1970-01-01 00:00:00', 'unit': unit,
                              'material_no': material_no, 'material_name': material_name, 'real_weight': total_weight,
                              'scan_material': scan_material, 'plan_classes_uid': plan_classes_uid,
                              'scan_material_type': scan_material_type}
        # 判断物料是否在配方中
        if isinstance(material_name, dict) or material_name not in materials or (bra_code.startswith('AAJ1Z20') and total_weight==0):
            flag, send_flag = True, True
            record_data = {'plan_classes_uid': plan_classes_uid, 'bra_code': bra_code,
                           'product_no': classes_plan.product_batching.stage_product_batch_no,
                           'material_name': scan_material, 'plan_weight': total_weight}
            other_type, status = scan_material_type, False
            # 添加到工艺放行表中的数据
            replace_material_data = {"plan_classes_uid": plan_classes_uid, "equip_no": classes_plan.equip.equip_no,
                                     "product_no": classes_plan.product_batching.stage_product_batch_no,
                                     "real_material": scan_material, "bra_code": bra_code, "status": "未处理",
                                     "created_user": self.context['request'].user, "real_material_no": scan_material,
                                     "last_updated_date": now_date, "material_type": scan_material_type}
            # 胶皮
            if scan_material_type == '胶皮':
                flag, send_flag = False, False
                # 查看群控配方是否含有掺料和待处理料
                product_recipe = ProductBatchingDetailPlan.objects.using('SFJ').filter(plan_classes_uid=plan_classes_uid)
                if not product_recipe:
                    raise serializers.ValidationError(f'未获取到计划的配方详情{plan_classes_uid}')
                query_set = product_recipe.filter(Q(Q(material_name__icontains='掺料') |
                                                  Q(material_name__icontains='待处理料')))
                if query_set:  # 此处由工艺确认: 掺料与待处理料不会同时出现在一个配方中
                    recipe_material_name = query_set.first().material_name
                    # 查询掺料放行
                    s_result = self.material_pass(plan_classes_uid, scan_material, material_type=scan_material_type)
                    if s_result[0]:
                        other_type, status, scan_material_msg = recipe_material_name, True, f'物料:{recipe_material_name} 扫码成功'
                    else:
                        # 配方尾缀为K的不区分顺序
                        if classes_plan.product_batching.stage_product_batch_no.endswith('K'):
                            if '加硫' in recipe_material_name:
                                if add_s:
                                    other_type, status, scan_material_msg = recipe_material_name, True, f'物料:{scan_material} 扫码成功'
                                else:
                                    other_type, scan_material_msg = recipe_material_name, '扫码失败: 请投入加硫料'
                            else:
                                if add_s:
                                    other_type, scan_material_msg = recipe_material_name, '扫码失败: 请投入无硫料'
                                else:
                                    other_type, status, scan_material_msg = recipe_material_name, True, f'物料:{scan_material} 扫码成功'
                        else:
                            # 炼胶类型判断: 混炼/终炼
                            if re.findall('FM|RFM|RE', classes_plan.product_batching.stage_product_batch_no):
                                # 待处理料不需要做加硫磺前后判断
                                if '掺料' in recipe_material_name:
                                    # 加硫磺前后(上面限定了胶皮,这里不会出现小料硫磺xxx-硫磺)
                                    s_id = product_recipe.filter(Q(material_name__icontains='硫磺')).first()
                                    if s_id:
                                        if s_id.sn < query_set.first().sn:
                                            # 硫磺在前, 只能投加硫料
                                            if add_s:
                                                other_type, status, scan_material_msg = recipe_material_name, True, f'掺料:{scan_material} 扫码成功'
                                            else:
                                                other_type, scan_material_msg = recipe_material_name, '扫码失败: 请投入加硫料'
                                        else:
                                            if add_s:
                                                other_type, scan_material_msg = recipe_material_name, '扫码失败: 请投入无硫料'
                                            else:
                                                other_type, status, scan_material_msg = recipe_material_name, True, f'掺料:{scan_material} 扫码成功'
                                    else:  # 有掺料无硫磺
                                        if add_s:
                                            other_type, status, scan_material_msg = recipe_material_name, True, f'掺料:{scan_material} 扫码成功'
                                        else:
                                            other_type, scan_material_msg = recipe_material_name, '扫码失败: 请投入加硫料'
                                else:  # 加硫待处理料、无硫待处理料、前两者都有
                                    add_s_wait_s = query_set.filter(material_name__icontains='加硫待处理料')
                                    no_s_wait_s = query_set.filter(material_name__icontains='无硫待处理料')
                                    if add_s_wait_s and not no_s_wait_s:
                                        if add_s:
                                            other_type, status, scan_material_msg = recipe_material_name, True, f'待处理物料:{scan_material}扫码成功'
                                        else:
                                            other_type, scan_material_msg = recipe_material_name, '扫码失败: 请投入加硫料'
                                    elif no_s_wait_s and not add_s_wait_s:
                                        if add_s:
                                            other_type, scan_material_msg = recipe_material_name, '扫码失败: 请投入无硫料'
                                        else:
                                            other_type, status, scan_material_msg = recipe_material_name, True, f'待处理物料:{scan_material}扫码成功'
                                    else:
                                        other_type, status, scan_material_msg = recipe_material_name, True, f'待处理物料:{scan_material}扫码成功'
                            else:
                                # 加硫禁止投料
                                if add_s:
                                    other_type, scan_material_msg = recipe_material_name, '扫码失败: 请投入无硫料'
                                else:
                                    other_type, status, scan_material_msg = recipe_material_name, True, f'物料:{scan_material} 扫码成功'
                else:
                    scan_material_msg = '配方中无掺料, 所投物料不在配方中'
                if not OtherMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, bra_code=bra_code, status=status, other_type=other_type):
                    record_data.update({'other_type': other_type, 'status': status})
                    OtherMaterialLog.objects.create(**record_data)
                if '成功' not in scan_material_msg and not ReplaceMaterial.objects.filter(plan_classes_uid=plan_classes_uid, bra_code=bra_code, reason_type='物料名不一致'):
                    ReplaceMaterial.objects.create(**replace_material_data)
            # 胶块/细料
            else:
                if scan_material_type == '胶块':
                    res = self.material_pass(plan_classes_uid, scan_material, material_type=scan_material_type)
                    if not res[0]:
                        scan_material_msg = '胶块不在配方中, 请工艺确认'
                        if not ReplaceMaterial.objects.filter(plan_classes_uid=plan_classes_uid, bra_code=bra_code):
                            ReplaceMaterial.objects.create(**replace_material_data)
                        if not OtherMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, bra_code=bra_code, status=status, other_type=scan_material_type):
                            record_data.update({'other_type': scan_material_type})
                            OtherMaterialLog.objects.create(**record_data)
                        flag, send_flag = False, False
                    # 通配条码(MC开头)需要判别有效期
                    if flag and bra_code.startswith('MC'):
                        if now_date > single.expire_datetime:
                            res = self.material_pass(plan_classes_uid, scan_material, reason_type='超过有效期', material_type=scan_material_type)
                            if not res[0]:
                                scan_material_msg = '通用配方包已过期, 请工艺确认'
                                if not ReplaceMaterial.objects.filter(plan_classes_uid=plan_classes_uid, bra_code=bra_code, reason_type='超过有效期'):
                                    replace_material_data.update({'reason_type': '超过有效期', 'expire_datetime': single.expire_datetime})
                                    ReplaceMaterial.objects.create(**replace_material_data)
                                record_data.update({'other_type': scan_material_type})
                                OtherMaterialLog.objects.create(**record_data)
                                flag, send_flag = False, False
                    if flag:
                        material_no = material_name = res[1]
                        attrs.update({'material_name': material_name, 'material_no': material_no})
                        attrs['tank_data'].update({'material_name': material_name, 'material_no': material_no})
                else:  # 料包
                    if '硫磺' not in materials and '细料' not in materials:  # 是否存在料包
                        raise serializers.ValidationError('该配方生产不需要投入料包')
                    xl_total_weight = detail_infos.get('硫磺') if '硫磺' in materials else detail_infos.get('细料')
                    total_standard_error = sum([i['standard_error'] for i in cnt_type_details])
                    already_y = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, scan_material_type__in=['硫磺', '细料'], useup_time__year='1970')
                    already_n = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, scan_material_type__in=['机配', '人工配'], useup_time__year='1970')
                    if scan_material_type == '机配':  # 扫描机配料包三种场景(细料/硫磺、机配+人工配)
                        merge_flag = weight_package.merge_flag
                        product_no_dev = re.split(r'\(|\（|\[', material_name)[0]
                        if 'ONLY' in weight_package.product_no and weight_package.product_no.split('-')[-2] != classes_plan.equip.equip_no:
                            raise serializers.ValidationError(f"物料为{weight_package.product_no}, 无法在当前机台使用投料")
                        if (already_y and not merge_flag) or (already_n and merge_flag):
                            raise serializers.ValidationError('扫码合包配置冲突')
                        if already_y and already_y.last().single_need != weight_package.split_count:
                            raise serializers.ValidationError('分包数与之前扫入不一致')
                        if weight_package.dev_type != scan_dev:
                            raise serializers.ValidationError('投料与生产机型不一致, 无法投料')
                        if product_no_dev != classes_plan.product_batching.stage_product_batch_no:
                            # 试验配方会使用正常配方料包 ex: C-1MB-C590-07(正常) K-1MB-TC590-45(试验[版本可能不同])
                            if product_no_dev.count('-') >= 2:
                                stage, site = product_no_dev.split('-')[1:3]
                                test_name_prefix = f'K-{stage}-T{site}'
                                if not classes_plan.product_batching.stage_product_batch_no.startswith(test_name_prefix):
                                    res = self.material_pass(plan_classes_uid, scan_material, material_type=scan_material_type)
                                    if not res[0]:
                                        scan_material_msg = '配方名不一致, 请工艺确认'
                                        if not ReplaceMaterial.objects.filter(plan_classes_uid=plan_classes_uid, bra_code=bra_code, reason_type='物料名不一致'):
                                            ReplaceMaterial.objects.create(**replace_material_data)
                                        flag, send_flag = False, False
                        if flag and weight_package.expire_days != 0 and now_date - weight_package.batch_time > timedelta(days=weight_package.expire_days):
                            res = self.material_pass(plan_classes_uid, scan_material, reason_type='超过有效期', material_type=scan_material_type)
                            if not res[0]:
                                scan_material_msg = '料包已过期, 请工艺确认'
                                if not ReplaceMaterial.objects.filter(plan_classes_uid=plan_classes_uid, bra_code=bra_code, reason_type='超过有效期'):
                                    expire_datetime = weight_package.batch_time + timedelta(days=weight_package.expire_days)
                                    replace_material_data.update({'reason_type': '超过有效期', 'expire_datetime': expire_datetime})
                                    ReplaceMaterial.objects.create(**replace_material_data)
                                flag, send_flag = False, False
                        if flag and merge_flag and abs(weight_package.total_weight[0] - xl_total_weight) > total_standard_error:  # 合包但重量不一致
                            scan_material_type = '硫磺' if '硫磺' in materials else '细料'
                            material_no = material_name = '细料' if '细料' in materials else '硫磺'
                            res = self.material_pass(plan_classes_uid, scan_material, reason_type='重量不匹配', material_type=scan_material_type)
                            if not res[0]:
                                scan_material_msg = '料包重量与配方不一致, 请工艺确认'
                                if not ReplaceMaterial.objects.filter(plan_classes_uid=plan_classes_uid, bra_code=bra_code, reason_type='重量不匹配'):
                                    replace_material_data.update({'reason_type': '重量不匹配', 'material_type': scan_material_type})
                                    ReplaceMaterial.objects.create(**replace_material_data)
                                flag, send_flag = False, False
                        if flag and not merge_flag:
                            machine_details = WeightPackageLogDetails.objects.filter(weight_package=weight_package)
                            # 转换配方内物料名与称量配方物料比较
                            cnt_type_data = {}
                            for i in cnt_type_details:
                                if i['material__material_name'].endswith('-C') or i['material__material_name'].endswith('-X'):
                                    cnt_type_data[i['material__material_name'][:-2]] = i['material__material_name']
                                else:
                                    cnt_type_data[i['material__material_name']] = i['material__material_name']
                            if set(machine_details.values_list('name', flat=True)) - set(cnt_type_data.keys()):
                                raise serializers.ValidationError('扫码机配物料种类和配方不一致')
                            material_no = material_name = {cnt_type_data.get(i.name): i.weight for i in machine_details}
                            material_name['single_weight'] = weight_package.split_count
                            # 扫到物料对应条码列表、扫到物料对应物料的分包数、料框表里的条码对应种类数
                            scan_bra_code, scan_split_num, load_tank_materials = [], [], 0
                            for i in cnt_type_details:
                                name = i['material__material_name'][:-2] if i['material__material_name'].endswith('-C') or i['material__material_name'].endswith('-X') else i['material__material_name']
                                instance = machine_details.filter(name=name).first()
                                if not instance:
                                    continue
                                if abs(instance.weight * weight_package.split_count - i['actual_weight']) > i['standard_error']:
                                    res = self.material_pass(plan_classes_uid, i['material__material_name'], reason_type='重量不匹配', material_type=scan_material_type)
                                    if not res[0]:
                                        scan_material_msg = '料包重量与配方不一致, 请工艺确认'
                                        if not ReplaceMaterial.objects.filter(plan_classes_uid=plan_classes_uid, bra_code=bra_code, reason_type='重量不匹配'):
                                            replace_material_data.update({'reason_type': '重量不匹配'})
                                            replace_material_data['real_material'] = i['material__material_name']
                                            ReplaceMaterial.objects.create(**replace_material_data)
                                        flag, send_flag = False, False
                                scan_material = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, material_name=i['material__material_name'], useup_time__year='1970').last()
                                if scan_material:
                                    load_tank_materials = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, bra_code=scan_material.bra_code).count()
                                    scan_split_num.append(scan_material.single_need)
                                    scan_bra_code.append(scan_material.bra_code)
                            else:
                                material_name_length = len([i for i in material_name.keys() if i != 'single_weight'])
                                if scan_bra_code and (len(scan_bra_code) != material_name_length or len(set(scan_bra_code)) != 1 or len(set(scan_split_num)) != 1 or set(scan_split_num) != {material_name['single_weight']} or material_name_length != load_tank_materials):
                                    raise serializers.ValidationError('添加的人工配料与之前不一致')
                        if flag:
                            if merge_flag:
                                material_no = material_name = '细料' if '细料' in materials else '硫磺'
                            else:
                                material_name['single_weight'] = weight_package.split_count
                            attrs.update({'material_name': material_name, 'material_no': material_no})
                            attrs['tank_data'].update({'material_name': material_name, 'material_no': material_no, 'scan_material': material_name,
                                                       'scan_material_type': scan_material_type if not merge_flag else ('硫磺' if '硫磺' in materials else '细料')})
                    else:  # 两种场景(全人工配、机配+人工配)
                        if 'ONLY' in manual.product_no and manual.product_no.split('-')[-2] != classes_plan.equip.equip_no:
                            raise serializers.ValidationError(f"物料为{manual.product_no.split('-')[-2]}, 无法在当前机台使用投料")
                        if already_y:
                            raise serializers.ValidationError('扫码合包配置冲突')
                        replace_material_data.update({'material_type': '人工配'})
                        product_no_dev = re.split(r'\(|\（|\[', manual.product_no)[0]
                        if manual.dev_type != scan_dev:
                            raise serializers.ValidationError('投料与生产机型不一致, 无法投料')
                        if product_no_dev != classes_plan.product_batching.stage_product_batch_no:
                            # 试验配方会使用正常配方料包 ex: C-1MB-C590-07(正常) K-1MB-TC590-45(试验[版本可能不同])
                            if product_no_dev.count('-') >= 2:
                                stage, site = product_no_dev.split('-')[1:3]
                                test_name_prefix = f'K-{stage}-T{site}'
                                if not classes_plan.product_batching.stage_product_batch_no.startswith(test_name_prefix):
                                    res = self.material_pass(plan_classes_uid, scan_material, material_type=scan_material_type)
                                    if not res[0]:
                                        scan_material_msg = '配方名不一致, 请工艺确认'
                                        if not ReplaceMaterial.objects.filter(plan_classes_uid=plan_classes_uid, bra_code=bra_code):
                                            ReplaceMaterial.objects.create(**replace_material_data)
                                        flag, send_flag = False, False
                        if flag and manual.expire_day != 0 and now_date > manual.expire_datetime:
                            res = self.material_pass(plan_classes_uid, scan_material, reason_type='超过有效期', material_type=scan_material_type)
                            if not res[0]:
                                scan_material_msg = '料包已过期, 请工艺确认'
                                if not ReplaceMaterial.objects.filter(plan_classes_uid=plan_classes_uid, bra_code=bra_code, reason_type='超过有效期'):
                                    replace_material_data.update({'reason_type': '超过有效期'})
                                    ReplaceMaterial.objects.create(**replace_material_data)
                                flag, send_flag = False, False
                        if flag:  # 机配+人工配但重量不一致,需要比较物料
                            if set(manual.detail_material_names) - set([i['material__material_name'] for i in cnt_type_details]):
                                raise serializers.ValidationError('扫码人工物料种类和配方不一致')
                            scan_bra_code, scan_split_num, load_tank_materials = [], [], 0
                            for i in cnt_type_details:
                                s_weight = material_name.get(i['material__material_name'])
                                if not s_weight:
                                    continue
                                if abs(s_weight - i['actual_weight']) > i['standard_error']:
                                    res = self.material_pass(plan_classes_uid, i['material__material_name'], reason_type='重量不匹配', material_type=scan_material_type)
                                    if not res[0]:
                                        scan_material_msg = '料包重量与配方不一致, 请工艺确认'
                                        if not ReplaceMaterial.objects.filter(plan_classes_uid=plan_classes_uid, bra_code=bra_code, reason_type='重量不匹配'):
                                            replace_material_data.update({'real_material': i['material__material_name'], 'reason_type': '重量不匹配'})
                                            ReplaceMaterial.objects.create(**replace_material_data)
                                        flag, send_flag = False, False
                                        break
                                scan_material = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, material_name=i['material__material_name'], useup_time__year='1970').last()
                                if scan_material:
                                    load_tank_materials = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, bra_code=scan_material.bra_code).count()
                                    scan_split_num.append(scan_material.single_need)
                                    scan_bra_code.append(scan_material.bra_code)
                            else:
                                material_name_length = len([i for i in material_name.keys() if i != 'single_weight'])
                                if scan_bra_code and (len(scan_bra_code) != material_name_length or len(set(scan_bra_code)) != 1 or len(set(scan_split_num)) != 1 or set(scan_split_num) != {material_name['single_weight']} or material_name_length != load_tank_materials):
                                    raise serializers.ValidationError('添加的人工配料与之前不一致')
                                flag, send_flag = True, True
        details = []
        if flag:
            # 配方中物料单车需要重量
            if not isinstance(material_name, dict):
                if bra_code.startswith('S') or bra_code.startswith('F'):
                    single_material_weight = weight_package.split_count
                elif bra_code.startswith('MC'):
                    single_material_weight = 1 if single.batching_type == '通用' else single.split_num
                    instance = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, material_name=material_name, useup_time__year='1970').last()
                    if instance and instance.unit == '包' and single_material_weight != instance.single_need:
                        raise serializers.ValidationError('投入物料分包数与之前不一致')
                else:
                    single_material_weight = detail_infos[material_name]
                attrs = self.check_used(plan_classes_uid, material_name, bra_code, total_weight, single_material_weight, attrs, scan_dev)
                details.append(dict(attrs))
            else:
                single_material_weight = material_name.pop('single_weight', 1)
                for k in material_name.keys():
                    copy_attrs = copy.deepcopy(attrs)
                    res_attrs = self.check_used(plan_classes_uid, k, bra_code, total_weight, single_material_weight, copy_attrs, scan_dev)
                    if res_attrs['status'] == 2:
                        raise serializers.ValidationError(res_attrs['tank_data']['msg'])
                    res_attrs['tank_data'].update({'material_name': k, 'material_no': k, 'scan_material': k})
                    res_attrs.update({'material_name': k, 'material_no': k})
                    details.append(res_attrs)
        attrs = {'attrs': details, 'created_username': self.context['request'].user.username, 'scan_material_type': scan_material_type}
        if send_flag:
            try:
                resp = requests.post(url=settings.AUXILIARY_URL + 'api/v1/production/current_weigh/', json=attrs, timeout=5)
            except Exception as e:
                logger.error('群控服务器错误！')
                raise serializers.ValidationError(e.args[0])
        if scan_material_msg:
            dk_equip = GlobalCode.objects.filter(use_flag=True, global_type__use_flag=True, global_type__type_name='导开机控制机台', global_name=classes_plan.equip.equip_no)
            if scan_material_type == '胶皮' and dk_equip:
                dk_control = 'Start' if '成功' in scan_material_msg else 'Stop'
                status, text = send_dk(classes_plan.equip.equip_no, dk_control)
                if not status:  # 发送导开机启停信号异常
                    logger.error(f'发送导开机信号异常, 计划号: {plan_classes_uid}, 机台: {classes_plan.equip.equip_no}, 错误:{text}')
                    raise serializers.ValidationError(f'发送导开机信号异常:{text}')
                else:  # 失败信号发送成功需要终端阻断进程
                    if dk_control == 'Stop':
                        raise serializers.ValidationError('发送导开机停止信号成功')
            raise serializers.ValidationError(scan_material_msg)
        for i in details:
            msg = i['tank_data'].pop('msg')
            if msg:
                raise serializers.ValidationError(msg)
        return attrs

    def material_pass(self, plan_classes_uid, scan_material, reason_type='物料名不一致', material_type='机配'):
        """
        查看当前不可放行的物料是否有放行的处理记录
        """
        # 查找物料替代表
        replace_record = ReplaceMaterial.objects.filter(plan_classes_uid=plan_classes_uid, status='已处理',
                                                        reason_type=reason_type, real_material=scan_material,
                                                        material_type=material_type, result=1).first()
        if replace_record and replace_record.result:
            # 转换物料名
            material_no = material_name = replace_record.recipe_material
            return True, material_name
        return False, ''

    def check_used(self, plan_classes_uid, material_name, bra_code, total_weight, single_material_weight, attrs, scan_dev):
        """
        判断物料是否充足、是否重复扫码等逻辑
        """
        # 获取计划号对应料框信息
        all_load_materials = list(LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid).values_list('material_name', flat=True))
        add_materials = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, useup_time__year='1970', material_name=material_name)
        if not add_materials:
            # 上一条计划剩余量判定
            pre_material = LoadTankMaterialLog.objects.filter(bra_code=bra_code).order_by('id').last()
            # 料框表中无该条码信息
            if not pre_material:
                attrs['tank_data'].update({'actual_weight': 0, 'adjust_left_weight': total_weight,
                                           'single_need': single_material_weight})
                attrs['status'] = 1
            # 存在该条码信息(其他计划使用过)
            else:
                # 未用完
                if pre_material.adjust_left_weight != 0:
                    attrs['tank_data'].update({'actual_weight': pre_material.actual_weight,
                                               'real_weight': pre_material.real_weight, 'pre_material_id': pre_material.id,
                                               'adjust_left_weight': pre_material.adjust_left_weight,
                                               'variety': pre_material.variety,
                                               'single_need': single_material_weight})
                    attrs['status'] = 1
                # 已用完(异常扫码)
                else:
                    attrs['tank_data'].update({'msg': '该物料条码已无剩余量,请扫新条码'})
                    attrs['status'] = 2
        else:
            # 扫码物料不在已有物料中
            if material_name not in all_load_materials:
                attrs['tank_data'].update({'actual_weight': 0, 'adjust_left_weight': total_weight,
                                           'single_need': single_material_weight})
                attrs['status'] = 1
            # 同物料扫码
            else:
                n_scan_material_type = attrs['tank_data'].get('scan_material_type')
                check_flag = True
                # 胶块6分钟内不超过4框, 胶皮4分钟内不超过4架
                if n_scan_material_type in ['胶块', '胶皮']:
                    limit_minutes, limit_nums = [4, 4] if n_scan_material_type == '胶皮' else [6, 4]
                    g_config = GlobalCode.objects.filter(use_flag=True, global_type__use_flag=True, global_type__type_name='密炼扫码限制', global_name__startswith=f'{scan_dev}-{n_scan_material_type}').last()
                    if g_config:
                        try:
                            limit_minutes, limit_nums = list(map(lambda x: int(x), g_config.global_name.split('-')[-2:]))
                        except:
                            pass
                    limit_time = datetime.now() - timedelta(minutes=limit_minutes)
                    num = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, material_name=material_name, scan_time__gte=limit_time).count()
                    if num >= limit_nums:
                        check_flag = False
                        attrs['tank_data'].update({'msg': f'扫码过快: {n_scan_material_type}{limit_minutes}分钟不超过{limit_nums}次'})
                        attrs['status'] = 2
                if check_flag:
                    last_same_material = add_materials.first()
                    # 包->重量(换算累加)  重量->包(换算累加)  包->包(直接累加)  重量->重量(直接累加)
                    if n_scan_material_type in ['胶块', '胶皮']:
                        if last_same_material.unit == '包' and not bra_code.startswith('MC'):
                            last_single = WeightPackageSingle.objects.filter(bra_code=last_same_material.bra_code).last()
                            if last_single:
                                last_single_weight = Decimal(last_single.single_weight)
                                weight = total_weight + last_same_material.real_weight * last_single_weight
                                attrs['tank_data'].update(
                                    {
                                        'actual_weight': last_same_material.actual_weight * last_single_weight,
                                        'adjust_left_weight': weight, 'real_weight': weight,
                                        'init_weight': total_weight + last_same_material.init_weight * last_single_weight,
                                        'single_need': single_material_weight,
                                        'pre_material_id': last_same_material.id})
                            else:
                                weight = total_weight
                                attrs['tank_data'].update({'actual_weight': 0, 'adjust_left_weight': weight,
                                                           'real_weight': weight, 'init_weight': total_weight,
                                                           'single_need': single_material_weight,
                                                           'pre_material_id': last_same_material.id})
                        elif last_same_material.unit != '包' and bra_code.startswith('MC'):
                            last_single_weight = last_same_material.single_need
                            weight = total_weight + last_same_material.real_weight // last_single_weight
                            attrs['tank_data'].update({'actual_weight': last_same_material.actual_weight // last_single_weight,
                                                       'adjust_left_weight': weight, 'real_weight': weight,
                                                       'init_weight': total_weight + last_same_material.init_weight // last_single_weight,
                                                       'single_need': single_material_weight,
                                                       'pre_material_id': last_same_material.id})
                        else:
                            weight = total_weight + last_same_material.real_weight
                            attrs['tank_data'].update({'actual_weight': last_same_material.actual_weight,
                                                       'adjust_left_weight': weight, 'real_weight': weight,
                                                       'init_weight': total_weight + last_same_material.init_weight,
                                                       'single_need': single_material_weight,
                                                       'pre_material_id': last_same_material.id})
                    else:
                        weight = total_weight + last_same_material.real_weight
                        attrs['tank_data'].update({'actual_weight': last_same_material.actual_weight,
                                                   'adjust_left_weight': weight, 'real_weight': weight,
                                                   'init_weight': total_weight + last_same_material.init_weight,
                                                   'single_need': single_material_weight,
                                                   'pre_material_id': last_same_material.id})
                    attrs['status'] = 1
        return attrs

    def create(self, validated_data):
        equip_no = None
        details = validated_data.get('attrs')
        scan_material_type = validated_data.pop('scan_material_type', '')
        plan_classes_uid, trains = '', 1
        for i in details:
            equip_no = i.get('equip_no')
            tank_data = i.get('tank_data')
            plan_classes_uid = i.get('plan_classes_uid')
            trains = i.get('trains')
            pre_material_id = tank_data.pop('pre_material_id', '')
            # 上一计划的条码物料归零(同计划中同物料的先一物料扣重时归0): 料包可能对应多条数据
            if pre_material_id:
                pre_material = LoadTankMaterialLog.objects.filter(id=pre_material_id).first()
                LoadTankMaterialLog.objects.filter(plan_classes_uid=pre_material.plan_classes_uid, bra_code=pre_material.bra_code)\
                    .update(**{'actual_weight': pre_material.init_weight, 'adjust_left_weight': 0, 'real_weight': 0,
                               'useup_time': datetime.now()})
            instance = LoadTankMaterialLog.objects.create(**tank_data)
        # 胶皮扫码正确发送消息给导开机
        dk_equip = GlobalCode.objects.filter(use_flag=True, global_type__use_flag=True, global_type__type_name='导开机控制机台', global_name=equip_no)
        if scan_material_type == '胶皮' and dk_equip:
            status, text = send_dk(equip_no, 'Start')
            if not status:  # 发送导开机启停信号异常只记录
                logger.error(f'发送导开机信号异常, 计划号: {plan_classes_uid}, 机台: {equip_no}, 错误:{text}')
                raise serializers.ValidationError(f'导开机启动信号发送失败: {text}')
        # 判断补充进料后是否能进上辅机
        fml = FeedingMaterialLog.objects.using('SFJ').filter(plan_classes_uid=plan_classes_uid, trains=int(trains)).last()
        if fml and fml.add_feed_result == 1:
            # 请求进料判断接口
            try:
                resp = requests.post(url=settings.AUXILIARY_URL + 'api/v1/production/handle_feed/', timeout=5,
                                     json=validated_data)
                content = json.loads(resp.content.decode())
                if content['success']:
                    logger.info(f'{trains}车扫码补料后调用接口成功')
                else:
                    logger.error(f'{trains}车扫码补料后调用接口时不可进料')
            except:
                logger.error(f'{trains}车扫码补料后调用接口时群控服务器错误！')
        return validated_data

    class Meta:
        model = FeedingMaterialLog
        fields = ('plan_classes_uid', 'bra_code', 'batch_classes', 'batch_group', 'trains')


class ReplaceMaterialSerializer(BaseModelSerializer):

    def to_representation(self, instance):
        res = super().to_representation(instance)
        if res['status'] != '已处理':
            res['last_updated_date'] = None
        return res

    class Meta:
        model = ReplaceMaterial
        fields = '__all__'


class ReturnRubberSerializer(BaseModelSerializer):
    print_username = serializers.ReadOnlyField(source='last_updated_user.username', help_text='打印员')

    def create(self, validated_data):
        now_date = datetime.now().replace(microsecond=0)
        classes_dict = {'早班': '1', '中班': '2', '夜班': '3'}
        # 获取班次班组
        batch_class = '早班' if '08:00:00' < str(now_date)[-8:] < '20:00:00' else '夜班'
        record = WorkSchedulePlan.objects.filter(plan_schedule__day_time=str(now_date)[:10], classes__global_name=batch_class,
                                                 plan_schedule__work_schedule__work_procedure__global_name='密炼').first()
        batch_group = record.group.global_name if record else ''
        # 生成条码
        prefix_code = f"AAJ1Z20{now_date.date().strftime('%Y%m%d')}{classes_dict[batch_class]}"
        max_code = ReturnRubber.objects.filter(bra_code__startswith=prefix_code).aggregate(max_code=Max('bra_code'))['max_code']
        bra_code = prefix_code + ("%04d" % (int(max_code[-4:]) + 1) if max_code else '0001')
        validated_data.update({'batch_class': batch_class, 'batch_group': batch_group, 'bra_code': bra_code,
                               'created_user': self.context['request'].user, 'last_updated_user': self.context['request'].user,
                               'ip_address': get_real_ip(self.context['request'].META)})
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if instance.print_flag == 1:
            raise serializers.ValidationError('打印尚未完成, 请稍后重试')
        validated_data.update({'print_flag': 1, 'last_updated_user': self.context['request'].user,
                               'last_updated_date': datetime.now(), 'ip_address': get_real_ip(self.context['request'].META)})
        return super().update(instance, validated_data)

    class Meta:
        model = ReturnRubber
        fields = '__all__'
        read_only_fields = ['bra_code', 'batch_group', 'batch_class']


class ToleranceRuleSerializer(BaseModelSerializer):
    distinguish_name = serializers.ReadOnlyField(source='distinguish.keyword_name')
    project_name = serializers.ReadOnlyField(source='project.keyword_name')

    def validate(self, attrs):
        standard_error = attrs.get('standard_error')
        small_handle = attrs.get('small_handle')
        small_num = attrs.get('small_num')
        big_num = attrs.get('big_num')
        if standard_error < 0:
            raise serializers.ValidationError('容许差值应为正数')
        if small_handle:
            if small_num < 0 or big_num < 0 or small_num > big_num:
                raise serializers.ValidationError('两侧数字未填全或左侧数字大于右侧数字')
        return attrs

    def to_representation(self, instance):
        res = super().to_representation(instance)
        res['handle_standard_error'] = f'{instance.handle.keyword_name}{str(instance.standard_error)}{instance.unit}'
        return res

    class Meta:
        model = ToleranceRule
        fields = '__all__'


class EquipOperationLogSerializer(BaseModelSerializer):
    class Meta:
        model = EquipOperationLog
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class BatchingClassesEquipPlanSerializer(BaseModelSerializer):
    dev_type_name = serializers.CharField(source='batching_class_plan.weigh_cnt_type'
                                                 '.product_batching.dev_type.category_name', read_only=True)
    product_no = serializers.CharField(source='batching_class_plan.weigh_cnt_type.'
                                              'product_batching.stage_product_batch_no',
                                       read_only=True)
    product_factory_date = serializers.CharField(source='batching_class_plan.work_schedule_plan.plan_schedule.day_time',
                                                 read_only=True)
    plan_trains = serializers.IntegerField(source='packages', read_only=True)
    classes = serializers.CharField(source='batching_class_plan.work_schedule_plan.classes.global_name', read_only=True)
    finished_trains = serializers.SerializerMethodField(read_only=True)
    plan_batching_uid = serializers.ReadOnlyField(source='batching_class_plan.plan_batching_uid')
    name = serializers.ReadOnlyField(source='batching_class_plan.weigh_cnt_type.name')

    @staticmethod
    def get_finished_trains(obj):
        finished_trains = WeightPackageLog.objects.filter(plan_batching_uid=obj.batching_class_plan.plan_batching_uid
                                                          ).aggregate(trains=Max('package_fufil'))['trains']
        return finished_trains if finished_trains else 0

    class Meta:
        model = BatchingClassesEquipPlan
        fields = '__all__'


class WeightBatchingLogSerializer(BaseModelSerializer):
    created_username = serializers.CharField(source='created_user.username')

    class Meta:
        model = WeightBatchingLog
        fields = ('id', 'tank_no', 'material_no', 'material_name', 'bra_code', 'created_date', 'status', 'scan_material',
                  'created_username')


class WeightBatchingLogCreateSerializer(BaseModelSerializer):

    def validate(self, attr):
        equip_no = attr['equip_no']
        bra_code = attr['bra_code']
        material_name = material_no = ''
        if bra_code.startswith('MC'):  # 通用原材料卡片条码(mes生成)
            single = WeightPackageSingle.objects.filter(batching_type='通用', bra_code=bra_code).last()
            if not single:
                raise serializers.ValidationError('未找到通用条码信息')
            init_count = single.package_count
            scan_material = single.material_name
            material_name_set = {single.material_name}
        else:
            # 查原材料出库履历查到原材料物料编码
            try:
                res = material_out_barcode(bra_code)
            except Exception as e:
                if settings.DEBUG:
                    res = None
                else:
                    raise serializers.ValidationError(e)
            if not res:
                raise serializers.ValidationError('未找到条码对应信息')
            scan_material = res.get('WLMC')
            material_name_set = set(ERPMESMaterialRelation.objects.filter(
                zc_material__wlxxid=res['WLXXID'],
                use_flag=True
            ).values_list('material__material_name', flat=True))
            if not material_name_set:
                raise serializers.ValidationError('该物料未与MES原材料建立绑定关系！')
            init_count = res.get('SL', 0)
            # 查看条码数量是否用完
        used_num = WeightBatchingLog.objects.filter(bra_code=bra_code, status=1).count()
        if used_num >= init_count:
            raise serializers.ValidationError('条码数量已经使用完, 请扫新条码')
        attr['scan_material'] = scan_material
        # 机台计划配方的所有物料名
        try:
            date_now = datetime.now().date()
            date_before = date_now - timedelta(days=1)
            if equip_no in JZ_EQUIP_NO:
                date_now_planid = date_now.strftime('%Y%m%d')
                date_before_planid = date_before.strftime('%Y%m%d')
                plan_model, material_model = JZPlan, JZRecipeMaterial
            else:
                date_now_planid = date_now.strftime('%Y%m%d')[2:]
                date_before_planid = date_before.strftime('%Y%m%d')[2:]
                plan_model, material_model = Plan, RecipeMaterial
            all_recipe = plan_model.objects.using(equip_no).filter(
                Q(planid__startswith=date_now_planid) | Q(planid__startswith=date_before_planid),
                state__in=['运行中', '等待', '运行']).all().order_by('-state', 'order_by')[:3].values_list('recipe', flat=True)
        except:
            raise serializers.ValidationError('称量机台{}错误'.format(equip_no))
        if not all_recipe:
            raise serializers.ValidationError('机台{}无进行中或已完成的配料计划'.format(equip_no))
        materials = set(material_model.objects.using(equip_no).filter(recipe_name__in=set(all_recipe))
                        .values_list('name', flat=True))
        comm_material = list(material_name_set & materials)
        if comm_material:
            material_name = comm_material[0]
            material_no = comm_material[0]
        attr['batch_time'] = datetime.now()
        # 扫码物料不在当日计划配方对应原材料中
        if not material_name:
            attr['status'] = 2
            attr['tank_no'] = ''
            attr['failed_reason'] = '不在称量计划内, 无法开门'
        else:
            # 从称量系统同步料罐状态到mes表中
            try:
                tank_status_sync = JZTankStatusSync(equip_no=equip_no) if equip_no in JZ_EQUIP_NO else TankStatusSync(equip_no=equip_no)
                tank_status_sync.sync()
            except:
                raise serializers.ValidationError('mes同步称量系统{}料罐状态失败'.format(equip_no))
            # 扫码物料与所有料罐不一致
            tank_info = WeightTankStatus.objects.filter(equip_no=equip_no, use_flag=True)
            feed_info = tank_info.filter(material_name=material_name)
            if not feed_info:
                attr['status'] = 2
                attr['tank_no'] = ''
                attr['failed_reason'] = '没有对应的料罐, 无法开门'
            else:
                single_tank = feed_info.first()
                if single_tank.status == 2:
                    attr['status'] = 2
                    attr['tank_no'] = single_tank.tank_no
                    attr['failed_reason'] = '料罐处于高位, 无法开门'
                else:
                    # 所有门都是关闭才可以打开(上面已经同步了当前料罐的状态了)
                    open_doors = tank_info.filter(open_flag=True)
                    if len(open_doors) != 0:
                        if len(open_doors) == 1 and single_tank.tank_no == open_doors.first().tank_no:
                            attr['tank_no'] = single_tank.tank_no
                        else:
                            attr['status'] = 2
                            attr['tank_no'] = single_tank.tank_no
                            attr['failed_reason'] = '已经有打开的料罐门, 不可再开'
                    else:
                        attr['tank_no'] = single_tank.tank_no
        attr['material_name'] = material_name
        attr['material_no'] = material_no
        attr['created_user'] = self.context['request'].user
        return attr

    class Meta:
        model = WeightBatchingLog
        fields = ('equip_no', 'bra_code', 'batch_classes', 'batch_group', 'dev_type', 'location_no')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class FeedingLogSerializer(BaseModelSerializer):
    class Meta:
        model = FeedingLog
        fields = ('feeding_port', 'material_name', 'created_date')
        read_only_fields = ('created_date',)


class WeightTankStatusSerializer(BaseModelSerializer):
    tank_no = serializers.CharField(max_length=64, help_text='料罐编码',
                                    validators=[UniqueValidator(queryset=WeightTankStatus.objects.all(),
                                                                message='该料罐编号已存在！')])

    class Meta:
        model = WeightTankStatus
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class WeightPackageLogCreateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(write_only=True, help_text='行标')
    display_manual_info = serializers.ListField(help_text='打印机配卡片时人工配料显示', write_only=True, default=[])
    manual_infos = serializers.ListField(help_text="""人工配物料信息[{"manual_type": "manual_single", "manual_id":1, "package_count": 10, "name": ["a", "b"]},
                                                                   {"manual_type": "manual", "manual_id":2, "package_count": 10, "name": ["c"]}]""", write_only=True, default=[])

    def validate(self, attrs):
        id = attrs.pop('id')
        plan_weight_uid = attrs.get('plan_weight_uid')
        bra_code = attrs.get('bra_code')
        split_count = attrs.get('split_count')
        print_begin_trains = attrs['print_begin_trains']
        package_count = attrs['package_count']
        product_no = attrs['product_no']
        dev_type = attrs['dev_type']
        equip_no = attrs['equip_no']
        batch_classes = attrs['batch_classes']
        package_fufil = attrs['package_fufil']
        merge_flag = attrs.get('merge_flag', False)
        batch_time = attrs['batch_time']
        manual_infos = attrs.get('manual_infos')
        # 需要合包但没有扫入人工配料
        if merge_flag and not manual_infos:
            raise serializers.ValidationError('称量计划设置了合包, 请扫码加入人工配料')
        # 配置数量判断
        total_package_count_data, ids_data = {}, {}
        if manual_infos:
            for item in manual_infos:
                k = tuple(set(item['names']))
                # 原材料累加包数比较  人工配料累加配置数量比较
                count = item['package_count']
                if item['manual_type'] == 'manual_single':
                    count = WeightPackageWms.objects.get(id=item['manual_id']).now_package
                if k not in total_package_count_data:
                    total_package_count_data[k] = {'manual_type': item['manual_type'], 'count': count}
                else:
                    total_package_count_data[k]['count'] = total_package_count_data[k]['count'] + count
                ids_data[k] = [item['manual_id']] if k not in ids_data else ids_data[k] + [item['manual_id']]
            manual_infos.append({'total_package_count_data': total_package_count_data, 'ids_data': ids_data})
        for k, v in total_package_count_data.items():
            if v['manual_type'] == 'manual' and v['count'] < package_count:
                raise serializers.ValidationError(f"人工料包配置数量不足,应包含物料:{','.join(list(k))}, 当前总配置数:{v['count']}")
            if v['manual_type'] == 'manual_single' and v['count'] < package_count * split_count:
                raise serializers.ValidationError(f"原材料{','.join(list(k))}包数不足,已有:{v['count']}, 所需总数:{package_count * split_count}")
        history_print = WeightPackageLog.objects.filter(plan_weight_uid=plan_weight_uid, equip_no=equip_no).aggregate(already_print=Sum('package_count'))['already_print']
        already_print = history_print if history_print else 0
        if package_count > package_fufil - already_print:
            raise serializers.ValidationError('配置总数量不可大于已完成配料车次')
        # 计算有效期
        single_expire_record = PackageExpire.objects.filter(product_no=product_no)
        if not single_expire_record:
            days = 0
        else:
            single_date = single_expire_record.first()
            days = single_date.package_fine_usefullife if equip_no.startswith('F') else single_date.package_sulfur_usefullife
        str_batch_time = ''.join(str(batch_time)[:10].split('-'))
        # 生成条码: 机台（3位）+年月日（8位）+班次（1位）+自增数（4位） 班次：1早班  2中班  3晚班
        # 履历表中无数据则初始为1, 否则获取最大数+1
        map_list = {"早班": '1', "中班": '2', "夜班": '3'}
        train_batch_classes = map_list.get(batch_classes)
        if not train_batch_classes:
            raise serializers.ValidationError(f'{batch_classes}不在[早班、中班、晚班]内')
        prefix = f"{equip_no}{str_batch_time}{train_batch_classes}"
        max_code = WeightPackageLog.objects.filter(bra_code__startswith=prefix).aggregate(max_code=Max('bra_code'))['max_code']
        incr_num = 1 if not max_code else int(max_code[-4:]) + 1
        bra_code = prefix + '%04d' % incr_num
        attrs.update({'bra_code': bra_code, 'begin_trains': print_begin_trains, 'material_no': product_no,
                      'material_name': product_no, 'noprint_count': package_fufil - package_count, 'expire_days': days,
                      'end_trains': print_begin_trains + package_count - 1, 'print_flag': 1, 'already_print': already_print,
                      'batch_time': str(batch_time), 'ip_address': get_real_ip(self.context['request'].META)})
        return attrs

    @atomic
    def create(self, validated_data):
        equip_no = validated_data['equip_no']
        manual_infos = validated_data.pop('manual_infos')
        display_manual_info = validated_data.pop('display_manual_info')
        already_print = validated_data.pop('already_print')
        plan_weight_uid = validated_data['plan_weight_uid']
        machine_package_count = validated_data['package_count']
        split_count = validated_data['split_count']
        instance = WeightPackageLog.objects.create(**validated_data)
        material_model = JZRecipeMaterial if equip_no in JZ_EQUIP_NO else RecipeMaterial
        # 增加机配详情
        details = material_model.objects.using(equip_no).filter(recipe_name=instance.product_no)
        if not details:
            raise serializers.ValidationError(f"{instance.equip_no}上没有找到该配方明细物料")
        detail_list = []
        for s in details:
            create_data = {'weight_package_id': instance.id, 'name': s.name, 'weight': s.weight, 'error': s.error}
            d_instance = WeightPackageLogDetails(**create_data)
            detail_list.append(d_instance)
        WeightPackageLogDetails.objects.bulk_create(detail_list)
        if manual_infos:
            handle_info = manual_infos.pop(-1)
            total_package_count_data, ids_data = handle_info.get('total_package_count_data'), handle_info.get('ids_data')
            # 机配物料关联人工配料
            for i in manual_infos:
                k = tuple(set(i['names']))
                update_kwargs = {}
                total_package_count, ids = total_package_count_data.get(k), ids_data.get(k)
                create_data = {"weight_package_id": instance.id, "count": i['package_count'], 'content': json.dumps(i['names'])}
                if 'single' in i['manual_type']:
                    create_data['manual_wms_id'] = i['manual_id']
                    update_kwargs['now_package'] = 0 if i['manual_id'] != ids[-1] else total_package_count['count'] - machine_package_count * split_count
                    db_name = WeightPackageWms
                else:
                    create_data['manual_id'] = i['manual_id']
                    update_kwargs['real_count'] = 0 if i['manual_id'] != ids[-1] else total_package_count['count'] - machine_package_count
                    db_name = WeightPackageManual
                # 归零和减重(最新一条减重,其余的归零)
                db_name.objects.filter(id=i['manual_id']).update(**update_kwargs)
                MachineManualRelation.objects.create(**create_data)
        if display_manual_info:  # 固定人工配料信息(没有则新建)
            history_record = WeightPackageLogManualDetails.objects.filter(plan_weight_uid=plan_weight_uid, equip_no=equip_no)
            if not history_record:
                create_list = []
                for i in display_manual_info:
                    created_data = {'plan_weight_uid': plan_weight_uid, 'material_type': i['material_type'],
                                    'handle_material_name': i['handle_material_name'], 'weight': i['weight'],
                                    'error': i['error'], 'equip_no': equip_no}
                    create_list.append(WeightPackageLogManualDetails(**created_data))
                WeightPackageLogManualDetails.objects.bulk_create(create_list)
        # 更新未打印数量
        noprint_count = validated_data['package_fufil'] - (already_print + machine_package_count)
        WeightPackageLog.objects.filter(plan_weight_uid=plan_weight_uid, equip_no=equip_no).update(noprint_count=noprint_count)
        return instance

    class Meta:
        model = WeightPackageLog
        fields = ['plan_weight_uid', 'product_no', 'plan_weight', 'dev_type', 'id', 'record', 'print_flag', 'batch_time',
                  'package_count', 'print_begin_trains', 'noprint_count', 'package_fufil', 'package_plan_count',
                  'equip_no', 'batch_group', 'batch_classes', 'status', 'print_count', 'merge_flag', 'manual_infos',
                  'expire_days', 'split_count', 'batch_user', 'bra_code', 'machine_manual_weight', 'display_manual_info']


class WeightPackageLogCUpdateSerializer(serializers.ModelSerializer):
    print_flag = serializers.IntegerField(write_only=True)

    def validate(self, attrs):
        print_flag = attrs.get('print_flag')
        if not isinstance(print_flag, int):
            raise serializers.ValidationError('回传打印状态应为整数')
        attrs['status'] = 'Y'
        attrs['print_count'] = 1
        return attrs

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

    class Meta:
        model = WeightPackageLog
        fields = ['print_flag']


class WeightPackageLogSerializer(BaseModelSerializer):

    def to_representation(self, instance):
        res = super().to_representation(instance)
        manual_headers, manual_body, batching_type = {}, [], '机配'
        expire_datetime = str(instance.batch_time + timedelta(days=res['expire_days'])) if res['expire_days'] != 0 else '9999-09-09 00:00:00'
        machine_manual_tolerance, total_manual_weight = '', 0
        # 拼接人工配信息
        if instance.merge_flag:
            batching_type = '机配+人工配'
            # 查询人工配料信息
            manual_ids, manual_wms_ids = instance.total_weight[2:]
            weight_package_manual = WeightPackageManual.objects.filter(id__in=manual_ids)
            weight_package_wms = WeightPackageWms.objects.filter(id__in=manual_wms_ids)
            manual_headers = {'product_no': res['product_no'], 'dev_type': res['dev_type'],
                              'total_nums': instance.total_weight[1]}
            manual_body = []
            detail_manual, detail_machine = 0, 0
            if weight_package_manual and not weight_package_wms:
                # 最早一条人工配料数据
                min_date = weight_package_manual.aggregate(first_date=Min('last_updated_date'), id=Min('id'))
                first_record = weight_package_manual.filter(id=min_date['id']).first()
                manual_data = WeightPackageManualSerializer(weight_package_manual, many=True).data
                for item in manual_data:
                    for i in item['manual_details']:
                        batch_type = i.pop('batch_type')
                        weight = i.pop('standard_weight')
                        if batch_type == '人工配':
                            detail_manual += weight
                        i.update({'batching_type': batch_type, 'single_weight': weight})
                    total_manual_weight += Decimal(item['single_weight'].split('±')[0])
                    manual_body += item['manual_details']
            elif not weight_package_manual and weight_package_wms:
                # 最早一条人工配料数据
                first_record = None
                manual_data = WeightPackageWmsSerializer(weight_package_wms, many=True).data
                for item in manual_data:
                    weight_tolerance = item['single_weight'].split('±')
                    detail_manual += Decimal(weight_tolerance[0])
                    total_manual_weight += Decimal(weight_tolerance[0])
                    manual_body.append({'material_name': item['material_name'],
                                        'single_weight': Decimal(weight_tolerance[0]),
                                        'tolerance': f'±{weight_tolerance[-1]}' if len(weight_tolerance) > 1 else '',
                                        'batching_type': item['batching_type'],
                                        'batch_user': '原材料',
                                        'batch_time': item['batch_time'][:10]})
            else:
                # 最早人工配信息
                min_date_manual = weight_package_manual.aggregate(first_date=Min('last_updated_date'), id=Min('id'))
                first_record = weight_package_manual.filter(id=min_date_manual['id']).first()
                manual_data = WeightPackageManualSerializer(weight_package_manual, many=True).data
                manual_wms_data = WeightPackageWmsSerializer(weight_package_wms, many=True).data
                for item in manual_data:
                    for i in item['manual_details']:
                        batch_type = i.pop('batch_type')
                        weight = i.pop('standard_weight')
                        if batch_type == '人工配':
                            detail_manual += weight
                        i.update({'batching_type': batch_type, 'single_weight': weight})
                    total_manual_weight += Decimal(item['single_weight'].split('±')[0])
                    manual_body += item['manual_details']
                for item in manual_wms_data:
                    weight_tolerance = item['single_weight'].split('±')
                    detail_manual += Decimal(weight_tolerance[0])
                    total_manual_weight += Decimal(weight_tolerance[0])
                    manual_body.append({'material_name': item['material_name'],
                                        'single_weight': Decimal(weight_tolerance[0]),
                                        'tolerance': f'±{weight_tolerance[-1]}' if len(weight_tolerance) > 1 else '',
                                        'batching_type': item['batching_type'],
                                        'batch_user': '原材料',
                                        'batch_time': item['batch_time'][:10]})
            # 获取公差
            tolerance = get_tolerance(batching_equip=res['equip_no'], standard_weight=total_manual_weight, project_name='all')
            manual_headers.update({'print_datetime': str(first_record.last_updated_date.date()) if first_record else str(datetime.now().replace(microsecond=0)),
                                   'class_group': f'{first_record.batch_group}/{first_record.batch_class}' if first_record else '',
                                   'manual_weight': total_manual_weight, 'manual_tolerance': tolerance,
                                   'detail_manual': detail_manual, 'detail_machine': total_manual_weight - detail_manual})
        else:  # 不合包显示人工配料信息
            manual_record = WeightPackageLogManualDetails.objects.filter(plan_weight_uid=res['plan_weight_uid'], equip_no=instance.equip_no)
            if manual_record:
                res.update({'display_manual_info': list(manual_record.values('material_type', 'handle_material_name', 'weight', 'error'))})
            else:
                # res.update({'display_manual_info': ''})  适配之前打印的数据所以注释这行
                ml_equip_no, msg = '', ''
                product_no_dev = re.split(r'\(|\（|\[', res['product_no'])[0]
                if 'ONLY' in res['product_no']:
                    ml_equip_no = res['product_no'].split('-')[-2]
                else:
                    flag, result = get_common_equip(product_no_dev, res['dev_type'])
                    if flag:
                        ml_equip_no = result[0]
                    else:
                        msg = result
                if ml_equip_no:
                    machine_materials = list(instance.weight_package_machine.all().values_list('name', flat=True))
                    batch_info_res = []
                    batch_info = ProductBatchingEquip.objects.filter(
                        ~Q(Q(feeding_mode__startswith='C') | Q(feeding_mode__startswith='P')),
                        ~Q(handle_material_name__in=machine_materials), is_used=True, type=4, equip_no=ml_equip_no,
                        product_batching__stage_product_batch_no=product_no_dev, product_batching__dev_type__category_name=res['dev_type'])
                    for j in batch_info:
                        batch_info_res.append({
                            'material_type': '细料' if res['equip_no'][0] == 'F' else '硫磺', 'handle_material_name': j.material.material_name,
                            'weight': j.batching_detail_equip.actual_weight if j.batching_detail_equip else j.cnt_type_detail_equip.standard_weight,
                            'error': j.batching_detail_equip.standard_error if j.batching_detail_equip else j.cnt_type_detail_equip.standard_error,
                        })
                    res.update({'display_manual_info': list(batch_info_res)})
                else:
                    res.update({'display_manual_info': msg})
            # 计算合计
            if isinstance(res['display_manual_info'], list) and res['display_manual_info']:
                all_manual_weight = sum([j['weight'] for j in res['display_manual_info']])
                res.update({'all_manual_weight': all_manual_weight})
        # 总公差
        machine_manual_tolerance = get_tolerance(batching_equip=res['equip_no'], standard_weight=instance.machine_manual_weight, project_name='all')
        res.update({'batching_type': batching_type, 'manual_headers': manual_headers, 'manual_body': manual_body,
                    'machine_manual_weight': instance.machine_manual_weight, 'machine_manual_tolerance': machine_manual_tolerance,
                    'manual_weight': total_manual_weight, 'machine_weight': instance.plan_weight,
                    'print_datetime': instance.last_updated_date.strftime('%Y-%m-%d %H:%M:%S'), 'expire_datetime': expire_datetime})
        # 最新打印数据
        last_instance = WeightPackageLog.objects.filter(plan_weight_uid=instance.plan_weight_uid, equip_no=instance.equip_no).last()
        res['order_flag'] = True if last_instance.bra_code == res['bra_code'] and res['noprint_count'] != 0 else False
        # 已使用数量
        used_trains = 0
        load_tank = LoadTankMaterialLog.objects.filter(bra_code=res['bra_code']).order_by('id').last()
        if load_tank:
            used_trains = res['package_count'] if load_tank.useup_time.year == 1970 or load_tank.actual_weight >= res['package_count'] else load_tank.actual_weight
        res.update({'next_package_count': last_instance.package_count, 'used_trains': used_trains})
        return res

    class Meta:
        model = WeightPackageLog
        fields = ['id', 'plan_weight_uid', 'product_no', 'plan_weight', 'dev_type', 'batch_time', 'bra_code', 'record',
                  'package_count', 'print_begin_trains', 'noprint_count', 'package_fufil', 'package_plan_count',
                  'equip_no', 'print_flag', 'batch_group', 'status', 'begin_trains', 'end_trains', 'batch_classes',
                  'batch_user', 'expire_days', 'last_updated_date', 'merge_flag', 'split_count', 'print_count',
                  'ip_address']


class WeightPackageLogUpdateSerializer(serializers.ModelSerializer):

    def update(self, instance, validated_data):
        validated_data.update({'print_flag': True, 'last_updated_date': datetime.now(), 'ip_address': get_real_ip(self.context['request'].META),
                               'last_updated_user': self.context['request'].user, 'print_datetime': datetime.now()})
        return super().update(instance, validated_data)

    class Meta:
        model = WeightPackageLog
        fields = ['print_count']


class WeightPackageWmsSerializer(BaseModelSerializer):

    class Meta:
        model = WeightPackageWms
        fields = '__all__'


class WeightPackageManualSerializer(BaseModelSerializer):
    manual_details = serializers.ListField(help_text='单配物料详情列表', write_only=True, default=[])

    def to_representation(self, instance):
        res = super().to_representation(instance)
        manual_details = []
        r_client = self.context.get('request')
        client = r_client.query_params.get('client') if r_client else None
        for i in instance.package_details.all():
            material_name = i.material_name
            if client:
                material_name = i.material_name[:-2] if i.material_name.endswith('-C') or i.material_name.endswith('-X') else i.material_name
            item = {'batch_time': i.created_date.strftime('%Y-%m-%d'), 'batch_user': i.created_user.username,
                    'material_name': material_name, 'standard_weight': i.standard_weight, 'batch_type': i.batch_type,
                    'tolerance': i.tolerance}
            manual_details.append(item)
        res.update({'manual_details': manual_details, 'package_count': instance.real_count})
        return res

    @atomic
    def create(self, validated_data):
        map_list = {"早班": '1', "中班": '2', "夜班": '3'}
        now_date = datetime.now().replace(microsecond=0)
        batching_equip = validated_data.get('batching_equip')
        package_count = validated_data.get('package_count')
        product_no = validated_data.get('product_no')
        manual_details = validated_data.pop('manual_details', [])
        # 班次, 班组
        batch_class = '早班' if '08:00:00' <= str(now_date)[-8:] < '20:00:00' else '夜班'
        record = WorkSchedulePlan.objects.filter(plan_schedule__day_time=str(now_date.date()),
                                                 classes__global_name=batch_class,
                                                 plan_schedule__work_schedule__work_procedure__global_name='密炼').first()
        batch_group = record.group.global_name if record else ''
        # 条码
        prefix = f"MM{batching_equip}{now_date.date().strftime('%Y%m%d')}{map_list.get(batch_class)}"
        max_code = WeightPackageManual.objects.filter(bra_code__startswith=prefix).aggregate(max_code=Max('bra_code'))['max_code']
        bra_code = prefix + ('%04d' % (int(max_code[-4:]) + 1) if max_code else '0001')
        total_weight = 0
        for item in manual_details:
            total_weight += round(Decimal(item.get('standard_weight', 0)), 3)
        # 根据重量查询公差
        distinguish_name, project_name = ["细料称量", "整包细料重量"] if batching_equip.startswith('F') else ["硫磺称量", "整包硫磺重量"]
        rule = ToleranceRule.objects.filter(distinguish__keyword_name=distinguish_name, project__keyword_name=project_name,
                                            small_num__lt=total_weight, big_num__gte=total_weight, use_flag=True).first()
        tolerance = f"{rule.handle.keyword_name}{rule.standard_error}{rule.unit}" if rule else ""
        single_weight = f"{str(total_weight)}{tolerance}"
        # 增加有效期
        expire_day, expire_datetime = 0, '9999-09-09 00:00:00'
        expire_record = PackageExpire.objects.filter(product_no=f"{product_no}").first()
        if expire_record:
            expire_day = expire_record.package_fine_usefullife if 'F' in batching_equip else expire_record.package_sulfur_usefullife
            expire_datetime = expire_datetime if expire_day == 0 else (now_date + timedelta(days=expire_day)).strftime('%Y-%m-%d %H:%M:%S')
        validated_data.update({'created_user': self.context['request'].user, 'batch_class': batch_class, 'real_count': package_count,
                               'batch_group': batch_group, 'bra_code': bra_code, 'single_weight': single_weight,
                               'end_trains': validated_data['begin_trains'] + validated_data['package_count'] - 1,
                               'print_flag': True, 'print_datetime': now_date, 'expire_day': expire_day,
                               'expire_datetime': expire_datetime,
                               'ip_address': get_real_ip(self.context['request'].META)})
        instance = super().create(validated_data)
        # 添加单配物料详情
        for item in manual_details:
            create_data = {'manual_details_id': instance.id, 'material_name': item.get('material__material_name'),
                           'standard_weight': item.get('standard_weight'), 'batch_type': item.get('batch_type'),
                           'tolerance': item.get('tolerance'), 'created_user': self.context['request'].user,
                           'standard_weight_old': item.get('standard_weight_old')}
            WeightPackageManualDetails.objects.create(**create_data)
        return instance

    def update(self, instance, validated_data):
        if instance.print_flag == 1:
            raise serializers.ValidationError('打印尚未完成, 请稍后重试')
        validated_data.update({'print_flag': True, 'last_updated_date': datetime.now(), 'ip_address': get_real_ip(self.context['request'].META),
                               'last_updated_user': self.context['request'].user, 'print_datetime': datetime.now()})
        return super().update(instance, validated_data)

    class Meta:
        model = WeightPackageManual
        fields = '__all__'
        read_only_fields = ['bra_code', 'single_weight', 'batch_group', 'batch_class']


class WeightPackageSingleSerializer(BaseModelSerializer):
    dev_type_name = serializers.ReadOnlyField(source='dev_type.category_name', help_text='机型名称')
    feeding_mode = serializers.CharField(help_text='物料的投料方式:R 不需要打条码', write_only=True, default='P')

    def to_representation(self, instance):
        res = super().to_representation(instance)
        res.update({'batch_type': '人工配', 'batch_time': res['created_date'][:10]})
        return res

    @atomic
    def create(self, validated_data):
        feeding_mode = validated_data.pop('feeding_mode')
        expire_day = validated_data.get('expire_day')
        map_list = {"早班": '1', "中班": '2', "夜班": '3'}
        now_date = datetime.now().replace(microsecond=0)
        material_name, single_weight, split_num = validated_data.get('material_name'), validated_data.get('single_weight'), validated_data.get('split_num')
        if split_num:
            single_weight = round(Decimal(single_weight) / split_num, 3)
        else:
            try:
                single_weight = round(Decimal(single_weight), 3)
            except:
                raise serializers.ValidationError('重量应为有效数值')
        # 班次, 班组
        batch_class = '早班' if '08:00:00' <= str(now_date)[-8:] < '20:00:00' else '夜班'
        record = WorkSchedulePlan.objects.filter(plan_schedule__day_time=str(now_date.date()),
                                                 classes__global_name=batch_class,
                                                 plan_schedule__work_schedule__work_procedure__global_name='密炼').first()
        batch_group = record.group.global_name if record else ''
        # 条码
        if feeding_mode.startswith('R'):
            bra_code = ''
        else:
            prefix = f"MC{now_date.date().strftime('%Y%m%d')}{map_list.get(batch_class)}"
            max_code = WeightPackageSingle.objects.filter(bra_code__startswith=prefix).aggregate(max_code=Max('bra_code'))['max_code']
            bra_code = prefix + ('%04d' % (int(max_code[-4:]) + 1) if max_code else '0001')
        # 单物料所有量程公差
        rule = ToleranceRule.objects.filter(distinguish__re_str__icontains=material_name, use_flag=True).first()
        tolerance = f"{rule.handle.keyword_name}{rule.standard_error}{rule.unit}" if rule else ""
        single_weight = f"{single_weight}{tolerance}"
        validated_data.update({'created_user': self.context['request'].user, 'batch_class': batch_class,
                               'batch_group': batch_group, 'bra_code': bra_code, 'single_weight': single_weight,
                               'end_trains': validated_data['begin_trains'] + validated_data['package_count'] - 1,
                               'print_flag': True, 'print_datetime': now_date,
                               'expire_datetime': now_date + timedelta(days=expire_day),
                               'ip_address': get_real_ip(self.context['request'].META)})
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if instance.print_flag == 1:
            raise serializers.ValidationError('打印尚未完成, 请稍后重试')
        validated_data.update({'print_flag': True, 'last_updated_date': datetime.now(), 'ip_address': get_real_ip(self.context['request'].META),
                               'last_updated_user': self.context['request'].user, 'print_datetime': datetime.now()})
        return super().update(instance, validated_data)

    class Meta:
        model = WeightPackageSingle
        fields = '__all__'
        read_only_fields = ['bra_code', 'batch_group', 'batch_class']


class WmsAddPrintSerializer(BaseModelSerializer):

    @atomic
    def create(self, validated_data):
        map_list = {"早班": '1', "中班": '2', "夜班": '3'}
        now_date = datetime.now().replace(microsecond=0)
        # 班次, 班组
        batch_class = '早班' if '08:00:00' <= str(now_date)[-8:] < '20:00:00' else '夜班'
        record = WorkSchedulePlan.objects.filter(plan_schedule__day_time=str(now_date.date()),
                                                 classes__global_name=batch_class,
                                                 plan_schedule__work_schedule__work_procedure__global_name='密炼').first()
        batch_group = record.group.global_name if record else ''
        prefix = f"WMS{now_date.date().strftime('%Y%m%d')}{map_list.get(batch_class)}"
        max_code = WmsAddPrint.objects.filter(bra_code__startswith=prefix).aggregate(max_code=Max('bra_code'))['max_code']
        bra_code = prefix + ('%04d' % (int(max_code[-4:]) + 1) if max_code else '0001')
        validated_data.update({'batch_class': batch_class, 'batch_group': batch_group, 'bra_code': bra_code,
                               'print_datetime': now_date, 'print_flag': True,
                               'ip_address': get_real_ip(self.context['request'].META)})
        return super().create(validated_data)

    @atomic
    def update(self, instance, validated_data):
        now_date = datetime.now().replace(microsecond=0)
        if instance.print_flag == 1:
            raise serializers.ValidationError('打印尚未完成, 请稍后重试')
        validated_data.update({'print_flag': True, 'last_updated_date': now_date, 'print_datetime': now_date,
                               'ip_address': get_real_ip(self.context['request'].META),
                               'last_updated_user': self.context['request'].user, })
        return super().update(instance, validated_data)

    class Meta:
        model = WmsAddPrint
        fields = '__all__'
        read_only_fields = ['bra_code', 'batch_group', 'batch_class']


class WeightPackagePlanSerializer(BaseModelSerializer):
    plan_weight_uid = serializers.ReadOnlyField(source='planid')
    product_no = serializers.ReadOnlyField(source='recipe')
    plan_weight = serializers.ReadOnlyField(default=0)
    batch_time = serializers.ReadOnlyField(default='')
    noprint_count = serializers.ReadOnlyField(source='actno')
    package_fufil = serializers.ReadOnlyField(source='actno')
    package_plan_count = serializers.ReadOnlyField(source='setno')
    dev_type = serializers.ReadOnlyField(default='')
    bra_code = serializers.ReadOnlyField(default='')
    record = serializers.ReadOnlyField(source='id')
    package_count = serializers.ReadOnlyField(default='')
    print_begin_trains = serializers.ReadOnlyField(default='')
    equip_no = serializers.ReadOnlyField(default='')
    print_flag = serializers.ReadOnlyField(default=0)
    batch_group = serializers.SerializerMethodField()
    status = serializers.ReadOnlyField(default='N')
    begin_trains = serializers.ReadOnlyField(default='')
    end_trains = serializers.ReadOnlyField(default='')
    batch_classes = serializers.ReadOnlyField(source='grouptime')
    used_trains = serializers.ReadOnlyField(default=0)

    def to_representation(self, instance):
        res = super().to_representation(instance)
        if instance.merge_flag is None:
            res['merge_flag'] = False
        return res

    def get_batch_group(self, obj):
        group = obj.grouptime if obj.grouptime != '中班' else ('早班' if '08:00:00' < obj.addtime[-8:] < '20:00:00' else '夜班')
        record = WorkSchedulePlan.objects.filter(plan_schedule__day_time=obj.date_time, classes__global_name=group,
                                                 plan_schedule__work_schedule__work_procedure__global_name='密炼').first()
        if record:
            return record.group.global_name
        else:
            return ''

    class Meta:
        model = Plan
        fields = ['id', 'plan_weight_uid', 'product_no', 'plan_weight', 'batch_time', 'noprint_count', 'package_fufil',
                  'print_flag', 'package_plan_count', 'dev_type', 'bra_code', 'record', 'package_count', 'status',
                  'print_begin_trains', 'equip_no', 'batch_group', 'begin_trains', 'end_trains', 'batch_classes', 'oper',
                  'merge_flag', 'starttime', 'used_trains']


class WeightPackageRetrieveLogSerializer(BaseModelSerializer):
    material_details = serializers.SerializerMethodField(read_only=True)

    @staticmethod
    def get_material_details(obj):
        return BatchingClassesPlan.objects.get(plan_batching_uid=obj.plan_batching_uid).weigh_cnt_type. \
            weight_details.filter(delete_flag=False).values('material__material_no',
                                                            'standard_weight',
                                                            'weigh_cnt_type__package_cnt')

    class Meta:
        model = WeightPackageLog
        fields = '__all__'


class WeightPackageUpdateLogSerializer(BaseModelSerializer):
    material_details = serializers.SerializerMethodField(read_only=True)

    @staticmethod
    def get_material_details(obj):
        return BatchingClassesPlan.objects.get(plan_batching_uid=obj.plan_batching_uid).weigh_cnt_type. \
            weight_details.filter(delete_flag=False).values('material__material_no',
                                                            'standard_weight',
                                                            'weigh_cnt_type__package_cnt')

    def update(self, instance, validated_data):
        instance.times += 1
        instance.save()
        return instance

    class Meta:
        model = WeightPackageLog
        fields = ('id', 'equip_no', 'plan_batching_uid', 'product_no', 'batch_classes', 'bra_code',
                  'batch_group', 'location_no', 'dev_type', 'begin_trains', 'end_trains', 'quantity',
                  'production_factory_date', 'production_classes', 'production_group', 'created_date',
                  'material_details')
        read_only_fields = ('equip_no', 'plan_batching_uid', 'product_no', 'batch_classes', 'bra_code',
                            'batch_group', 'location_no', 'dev_type', 'begin_trains', 'end_trains', 'quantity',
                            'production_factory_date', 'production_classes', 'production_group', 'created_date',
                            'material_details')


class WeightPackagePartialUpdateLogSerializer(BaseModelSerializer):

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        while 1:
            bra_code = generate_bra_code(instance.equip_no,
                                         instance.production_factory_date,
                                         instance.production_classes)
            if not WeightPackageLog.objects.filter(bra_code=bra_code).exists():
                break
        instance.bra_code = bra_code
        instance.save()
        return instance

    class Meta:
        model = WeightPackageLog
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class LoadMaterialLogListSerializer(serializers.ModelSerializer):
    mixing_finished = serializers.SerializerMethodField(help_text='混炼/终炼', read_only=True)
    product_no = serializers.ReadOnlyField(source='feed_log.product_no')
    created_date = serializers.DateTimeField(source='feed_log.feed_begin_time')
    trains = serializers.ReadOnlyField(source='feed_log.trains')
    production_factory_date = serializers.ReadOnlyField(source='feed_log.production_factory_date')
    production_classes = serializers.ReadOnlyField(source='feed_log.production_classes')
    equip_no = serializers.ReadOnlyField(source='feed_log.equip_no')
    plan_classes_uid = serializers.ReadOnlyField(source='feed_log.plan_classes_uid')

    def get_mixing_finished(self, obj):
        product_no = obj.feed_log.product_no
        if "FM" in product_no:
            return '终炼'
        else:
            return "混炼"

    class Meta:
        model = LoadMaterialLog
        fields = '__all__'


class WeightBatchingLogListSerializer(BaseModelSerializer):

    class Meta:
        model = WeightBatchingLog
        fields = '__all__'


"""
小料称量序列化器
"""


class MaterialInfoSerializer(serializers.ModelSerializer):
    equip_no = serializers.CharField(write_only=True, help_text='称量机台')

    def create(self, validated_data):
        equip_no = validated_data.pop('equip_no')
        validated_data['time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            material_model = JZMaterialInfo if equip_no in JZ_EQUIP_NO else MaterialInfo
            instance = material_model.objects.using(equip_no).create(**validated_data)
        except ConnectionDoesNotExist:
            raise serializers.ValidationError('称量机台{}服务错误！'.format(equip_no))
        except Exception:
            raise
        return instance

    class Meta:
        model = MaterialInfo
        fields = '__all__'
        read_only_fields = ('time', 'remark')


class BinSerializer(serializers.ModelSerializer):

    class Meta:
        model = Bin
        fields = '__all__'


class JZBinSerializer(serializers.ModelSerializer):

    class Meta:
        model = JZBin
        fields = '__all__'


class PlanSerializer(serializers.ModelSerializer):
    equip_no = serializers.CharField(write_only=True, help_text='称量机台')

    def to_representation(self, instance):
        res = super().to_representation(instance)
        if res.get('merge_flag') is None:
            res['merge_flag'] = False
        return res

    def create(self, validated_data):
        equip_no = validated_data.pop('equip_no')
        # 称量重量与mes不同无法下发计划
        recipe_obj = RecipePre.objects.using(equip_no).filter(name=validated_data['recipe']).first()
        product_no_dev, dev_type = re.split(r'\(|\（|\[', recipe_obj.name)[0], recipe_obj.ver
        if 'ONLY' in validated_data['recipe']:
            ml_equip_no = recipe_obj.name.split('-')[-2]
        else:
            flag, result = get_common_equip(product_no_dev, dev_type)
            if flag:
                ml_equip_no = result[0]
            else:
                raise serializers.ValidationError(result)
        recipe_materials = list(RecipeMaterial.objects.using(equip_no).filter(recipe_name=recipe_obj.name).values_list('name', flat=True))
        if not recipe_materials:
            raise serializers.ValidationError(f'{equip_no}未找到配方{recipe_obj.name}明细物料信息, 无法新增计划')
        mes_recipe = ProductBatchingEquip.objects.filter(is_used=True, equip_no=ml_equip_no, type=4,
                                                         feeding_mode__startswith=equip_no[0],
                                                         handle_material_name__in=recipe_materials,
                                                         product_batching__stage_product_batch_no=product_no_dev,
                                                         product_batching__dev_type__category_name=dev_type)
        mes_machine_weight = mes_recipe.aggregate(weight=Sum('cnt_type_detail_equip__standard_weight'))['weight']
        if not mes_machine_weight:
            raise serializers.ValidationError('获取mes设置重量失败, 无法比较重量')
        if abs(recipe_obj.weight * recipe_obj.split_count - mes_machine_weight) > Decimal('0.01'):
            raise serializers.ValidationError(f'称量配方重量: {recipe_obj.weight}与mes配方不一致: {round(mes_machine_weight, 3)}')
        last_group_plan = Plan.objects.using(equip_no).filter(date_time=validated_data['date_time'],
                                                              grouptime=validated_data['grouptime']
                                                              ).order_by('order_by').last()
        if last_group_plan:
            validated_data['order_by'] = last_group_plan.order_by + 1
        else:
            validated_data['order_by'] = 1
        # 查询配方的合包状态
        recipe = RecipePre.objects.using(equip_no).filter(name=validated_data['recipe']).first()
        validated_data['merge_flag'] = recipe.merge_flag if recipe else False
        split_count = 1 if not recipe else recipe.split_count
        validated_data['setno'] = validated_data['setno'] * split_count
        validated_data['planid'] = datetime.now().strftime('%Y%m%d%H%M%S')[2:]
        validated_data['state'] = '等待'
        validated_data['actno'] = 0
        validated_data['oper'] = self.context['request'].user.username
        validated_data['addtime'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            instance = Plan.objects.using(equip_no).create(**validated_data)
            ins = CLSystem(equip_no)
            ins.add_plan(instance.planid)
        except ConnectionDoesNotExist:
            raise serializers.ValidationError('称量机台{}服务错误！'.format(equip_no))
        except Exception as e:
            raise serializers.ValidationError('新增计划异常')
        return instance

    class Meta:
        model = Plan
        read_only_fields = ('planid', 'state', 'actno', 'order_by', 'addtime', 'starttime', 'stoptime', 'oper')
        fields = '__all__'


class JZPlanSerializer(serializers.ModelSerializer):
    equip_no = serializers.CharField(write_only=True, help_text='称量机台')

    def to_representation(self, instance):
        res = super().to_representation(instance)
        if res.get('merge_flag') is None:
            res['merge_flag'] = False
        return res

    def create(self, validated_data):
        equip_no = validated_data.pop('equip_no')
        plan_model, pre_model, material_model = JZPlan, JZRecipePre, JZRecipeMaterial
        # 称量重量与mes不同无法下发计划
        recipe_obj = pre_model.objects.using(equip_no).filter(name=validated_data['recipe']).first()
        product_no_dev, dev_type = re.split(r'\(|\（|\[', recipe_obj.name)[0], recipe_obj.ver
        if 'ONLY' in validated_data['recipe']:
            ml_equip_no = recipe_obj.name.split('-')[-2]
        else:
            flag, result = get_common_equip(product_no_dev, dev_type)
            if flag:
                ml_equip_no = result[0]
            else:
                raise serializers.ValidationError(result)
        recipe_materials = list(material_model.objects.using(equip_no).filter(recipe_name=recipe_obj.name).values_list('name', flat=True))
        if not recipe_materials:
            raise serializers.ValidationError(f'{equip_no}未找到配方{recipe_obj.name}明细物料信息, 无法新增计划')
        mes_recipe = ProductBatchingEquip.objects.filter(is_used=True, equip_no=ml_equip_no, type=4,
                                                         feeding_mode__startswith=equip_no[0],
                                                         handle_material_name__in=recipe_materials,
                                                         product_batching__stage_product_batch_no=product_no_dev,
                                                         product_batching__dev_type__category_name=dev_type)
        mes_machine_weight = mes_recipe.aggregate(weight=Sum('cnt_type_detail_equip__standard_weight'))['weight']
        if not mes_machine_weight:
            raise serializers.ValidationError('获取mes设置重量失败, 无法比较重量')
        if abs(recipe_obj.weight * recipe_obj.split_count - mes_machine_weight) > Decimal('0.01'):
            raise serializers.ValidationError(f'称量配方重量: {recipe_obj.weight}与mes配方不一致: {round(mes_machine_weight, 3)}')
        last_group_plan = plan_model.objects.using(equip_no).filter(date_time=validated_data['date_time'],
                                                                    grouptime=validated_data['grouptime']
                                                                    ).order_by('order_by').last()
        if last_group_plan:
            validated_data['order_by'] = last_group_plan.order_by + 1
        else:
            validated_data['order_by'] = 1
        now_time = datetime.now().strftime('%Y%m%d%H%M%S')
        prefix = f'{now_time[:8]}X'
        max_plan_id = plan_model.objects.using(equip_no).filter(planid__startswith=prefix).aggregate(plan_id=Max('planid'))['plan_id']
        # 比对嘉正称量本地计划号与顺序
        max_local = JZExecutePlan.objects.using(equip_no).filter(planid__startswith=prefix).aggregate(max_plan_id=Max('planid'), max_order_by=Max('order_by'))
        if max_local['max_order_by'] and max_local['max_order_by'] > validated_data['order_by'] - 1:
            validated_data['order_by'] = max_local['max_order_by'] + 1
        if max_plan_id and not max_local['max_plan_id']:
            plan_id = prefix + '%04d' % (int(max_plan_id[-4:]) + 1)
        elif not max_plan_id and max_local['max_plan_id']:
            plan_id = prefix + '%04d' % (int(max_local['max_plan_id'][-4:]) + 1)
        elif not max_plan_id and not max_local['max_plan_id']:
            plan_id = prefix + '0001'
        else:
            plan_id = prefix + ('%04d' % (int(max_plan_id[-4:]) + 1) if max_plan_id > max_local['max_plan_id'] else '%04d' % (int(max_local['max_plan_id'][-4:]) + 1))
        # 查询配方的合包状态
        recipe = pre_model.objects.using(equip_no).filter(name=validated_data['recipe']).first()
        validated_data['merge_flag'] = recipe.merge_flag if recipe else False
        split_count = 1 if not recipe else recipe.split_count
        validated_data['setno'] = validated_data['setno'] * split_count
        validated_data['planid'] = plan_id
        validated_data['state'] = '等待'
        validated_data['actno'] = 0
        validated_data['starttime'] = None
        validated_data['stoptime'] = None
        validated_data['downtime'] = None
        validated_data['oper'] = self.context['request'].user.username
        validated_data['addtime'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            instance = plan_model.objects.using(equip_no).create(**validated_data)
        except ConnectionDoesNotExist:
            raise serializers.ValidationError('称量机台{}服务错误！'.format(equip_no))
        except Exception as e:
            raise serializers.ValidationError('新增计划异常')
        return instance

    class Meta:
        model = JZPlan
        read_only_fields = ('planid', 'state', 'actno', 'order_by', 'addtime', 'starttime', 'stoptime', 'oper',
                            'downtime', 'create_flag')
        fields = '__all__'


class PlanUpdateSerializer(serializers.ModelSerializer):
    action = serializers.IntegerField(help_text='动作 1：下达计划  2：计划重传  3：修改车次 4：计划停止', write_only=True)
    equip_no = serializers.CharField(write_only=True, help_text='称量机台')

    def update(self, instance, validated_data):
        action = validated_data['action']
        equip_no = validated_data['equip_no']
        ins = CLSystem(equip_no)
        if action == 1:
            ins.issue_plan(instance.planid, instance.recipe, instance.setno)
        elif action == 2:
            ins.reload_plan(instance.planid, instance.recipe)
        elif action == 3:
            # 查询配方的合包状态
            recipe = RecipePre.objects.using(equip_no).filter(name=instance.recipe).first()
            split_count = 1 if not recipe else recipe.split_count
            setno = validated_data['setno'] * split_count
            actno = instance.actno if instance.actno else 0
            if not setno:
                raise serializers.ValidationError('设定车次不可为空!')
            if setno <= actno:
                raise serializers.ValidationError('设定车次不能小于完成车次!')
            if '运行' in instance.state and setno - actno < 5:
                raise serializers.ValidationError('正在运行的计划修改车次必须大于完成车次5车')
            ins.update_trains(instance.planid, setno)
        elif action == 4:
            ins.stop(instance.planid)
            instance.state = '终止'
            instance.save()
        else:
            raise serializers.ValidationError('action参数错误！')
        return instance

    class Meta:
        model = Plan
        fields = ('id', 'setno', 'action', 'equip_no')


class JZPlanUpdateSerializer(serializers.ModelSerializer):
    action = serializers.IntegerField(help_text='动作 1：下达计划  2：计划重传  3：修改车次 4：计划停止', write_only=True)
    equip_no = serializers.CharField(write_only=True, help_text='称量机台')

    def update(self, instance, validated_data):
        action = validated_data['action']
        equip_no = validated_data['equip_no']
        ins = JZCLSystem(equip_no)
        with atomic(using=equip_no):
            try:
                if action == 1:
                    if instance.downtime:  # 已经下达过
                        raise serializers.ValidationError('该计划已经下达过')
                    ins.issue_plan(instance.planid, instance.recipe, instance.setno)
                elif action == 2:
                    raise serializers.ValidationError('不支持称量计划重传')
                elif action == 3:
                    recipe = RecipePre.objects.using(equip_no).filter(name=instance.recipe).first()
                    split_count = 1 if not recipe else recipe.split_count
                    setno = validated_data['setno'] * split_count
                    actno = instance.actno if instance.actno else 0
                    if not setno:
                        raise serializers.ValidationError('设定车次不可为空!')
                    if setno <= actno:
                        raise serializers.ValidationError('设定车次不能小于完成车次!')
                    if '运行' in instance.state and setno - actno < 5:
                        raise serializers.ValidationError('正在运行的计划修改车次必须大于完成车次5车')
                    ins.update_trains(instance.planid, setno)
                elif action == 4:
                    ins.stop(instance.planid)
                else:
                    raise serializers.ValidationError('action参数错误！')
            except Exception as e:
                raise serializers.ValidationError(e.args[0])
        return instance

    class Meta:
        model = JZPlan
        fields = ('id', 'setno', 'action', 'equip_no')


class RecipePreSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        res = super().to_representation(instance)
        if instance.merge_flag is None:
            res['merge_flag'] = False
        if instance.split_count is None:
            res['split_count'] = 1
        return res

    class Meta:
        model = RecipePre
        fields = '__all__'


class ReportBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportBasic
        fields = '__all__'


class ReportWeightSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportWeight
        fields = '__all__'


class XLPlanCSerializer(serializers.ModelSerializer):
    dev_type = serializers.CharField(default='', help_text='生产机型')

    class Meta:
        model = Plan
        fields = ['id', 'recipe', 'setno', 'actno', 'state', 'dev_type', 'planid']


class XLPromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeightTankStatus
        fields = ['id', 'tank_no', 'material_name']


class PowderTankSettingSerializer(serializers.ModelSerializer):
    material_name = serializers.ReadOnlyField(source='material.material_name')

    class Meta:
        model = PowderTankSetting
        fields = ['id', 'equip_no', 'tank_no', 'material', 'bar_code', 'use_flag', 'material_name']


class OilTankSettingSerializer(serializers.ModelSerializer):
    material_name = serializers.ReadOnlyField(source='material.material_name')

    class Meta:
        model = OilTankSetting
        fields = ['id', 'tank_no', 'material', 'bar_code', 'use_flag', 'material_name']


class CarbonTankSetSerializer(serializers.ModelSerializer):

    class Meta:
        model = CarbonTankFeedWeightSet
        fields = '__all__'


class CarbonTankSetUpdateSerializer(serializers.ModelSerializer):

    def validate(self, attrs):
        attrs['update_user'] = self.context['request'].user.username
        attrs['update_datetime'] = datetime.now().date()
        return attrs

    class Meta:
        model = CarbonTankFeedWeightSet
        fields = ['tank_capacity_type', 'tank_capacity', 'feed_capacity_low', 'feed_capacity_mid']


class FeedingOperationLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = FeedingOperationLog
        fields = '__all__'


class CarbonFeedingPromptSerializer(serializers.ModelSerializer):

    class Meta:
        model = CarbonTankFeedingPrompt
        fields = '__all__'


class CarbonFeedingPromptCreateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(allow_null=True)

    def create(self, validated_data):
        record_id = validated_data.pop('id')
        equip_id = validated_data.get('equip_id')
        tank_no = validated_data.get('tank_no')
        changed = validated_data.get('feed_change')
        # 没有id表示初次加载
        if record_id:
            # 更新旧罐号信息: 少变多按id删除数据, 多变少按罐号删除数据
            feed_change = CarbonTankFeedingPrompt.objects.filter(equip_id=equip_id, tank_no=tank_no).count()
            if changed >= feed_change:
                CarbonTankFeedingPrompt.objects.filter(id=record_id).delete()
            else:
                CarbonTankFeedingPrompt.objects.filter(equip_id=equip_id, tank_no=tank_no).delete()
        instance = CarbonTankFeedingPrompt.objects.create(**validated_data)
        return instance

    class Meta:
        model = CarbonTankFeedingPrompt
        fields = ['id', 'equip_id', 'tank_no', 'tank_capacity_type', 'tank_material_name', 'tank_level_status',
                  'feedcapacity_weight_set', 'feedport_code', 'feed_material_name', 'feed_status', 'feed_change',
                  'is_no_port_one', 'ex_warehouse_flag', 'wlxxid']
