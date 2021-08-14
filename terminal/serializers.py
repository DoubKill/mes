import random
import re
from datetime import datetime, timedelta

import requests
from django.db.models import Q, Sum, Max
from django.db.utils import ConnectionDoesNotExist
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from basics.models import PlanSchedule, GlobalCode
from inventory.models import MaterialOutHistory, WmsInventoryMaterial
from mes import settings
from mes.base_serializer import BaseModelSerializer
from mes.conf import COMMON_READ_ONLY_FIELDS
from plan.models import ProductClassesPlan, BatchingClassesPlan, BatchingClassesEquipPlan
from production.models import PalletFeedbacks
from recipe.models import ZCMaterial, ERPMESMaterialRelation, WeighCntType
from terminal.models import EquipOperationLog, WeightBatchingLog, FeedingLog, WeightTankStatus, \
    WeightPackageLog, FeedingMaterialLog, LoadMaterialLog, MaterialInfo, Bin, Plan, RecipePre, ReportBasic, \
    ReportWeight, LoadTankMaterialLog, PackageExpire, RecipeMaterial
import logging

from terminal.utils import INWeighSystem, TankStatusSync

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
        # 计划号中存在条码
        is_used = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, bra_code=bra_code)
        if is_used:
            raise serializers.ValidationError('同一计划中不可多次扫同一条码')
        try:
            # 查原材料出库履历查到原材料物料编码
            wms_stock = MaterialOutHistory.objects.using('wms').filter(
                lot_no=bra_code).values('material_no', 'material_name', 'weight', 'unit')
        except Exception:
            raise serializers.ValidationError('连接WMS库失败，请联系管理员！')

        pallet_feedback = PalletFeedbacks.objects.filter(lot_no=bra_code).first()
        weight_package = WeightPackageLog.objects.filter(bra_code=bra_code).first()
        material_no = material_name = None
        total_weight = 0
        unit = 'KG'
        classes_plan = ProductClassesPlan.objects.filter(plan_classes_uid=plan_classes_uid).first()
        if not classes_plan:
            raise serializers.ValidationError('该计划不存在')
        if wms_stock:
            attrs['scan_material'] = wms_stock[0].get('material_name')
            material_name_set = set(ERPMESMaterialRelation.objects.filter(
                zc_material__wlxxid=wms_stock[0]['material_no'],
                use_flag=True
            ).values_list('material__material_name', flat=True))
            if not material_name_set:
                raise serializers.ValidationError('该物料未与MES原材料建立绑定关系！')
            comm_material = list(material_name_set & classes_plan.product_batching.batching_material_names)
            if comm_material:
                material_name = comm_material[0]
                material_no = comm_material[0]
                total_weight = wms_stock[0].get('weight')
                unit = wms_stock[0].get('unit')
        if pallet_feedback:
            material_no = pallet_feedback.product_no
            material_name = pallet_feedback.product_no
            total_weight = pallet_feedback.actual_weight
            unit = unit
            attrs['scan_material'] = material_name
        if weight_package:
            material_no = weight_package.material_no
            material_name = weight_package.material_name
            total_weight = weight_package.package_count
            unit = '包'
            attrs['scan_material'] = material_name
        if not material_name:
            raise serializers.ValidationError('未找到该条形码信息！')
        attrs['equip_no'] = classes_plan.equip.equip_no
        attrs['material_name'] = material_name
        attrs['material_no'] = material_no
        attrs['tank_data'] = {'msg': '', 'bra_code': bra_code, 'init_weight': total_weight, 'scan_time': datetime.now(),
                              'useup_time': datetime.strptime('1970-01-01 00:00:00', '%Y-%m-%d %H:%M:%S'), 'unit': unit,
                              'material_no': material_no, 'material_name': material_name, 'real_weight': total_weight,
                              'scan_material': attrs.pop('scan_material', ''), 'plan_classes_uid': plan_classes_uid}
        # 判断物料是否在配方中
        if material_name not in classes_plan.product_batching.batching_material_names:
            attrs['status'] = 2
        else:
            # 获取计划号对应料框信息
            add_materials = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, useup_time__year='1970',
                                                               material_name=material_name)

            if not add_materials:
                # 上一条计划剩余量判定
                pre_material = LoadTankMaterialLog.objects.filter(bra_code=bra_code).first()
                # 料框表中无该条码信息
                if not pre_material:
                    attrs['tank_data'].update({'actual_weight': 0, 'adjust_left_weight': total_weight})
                    attrs['status'] = 1
                # 存在该条码信息(其他计划使用过)
                else:
                    # 未用完
                    if pre_material.adjust_left_weight != 0:
                        attrs['tank_data'].update({'actual_weight': pre_material.actual_weight,
                                                   'real_weight': pre_material.real_weight, 'pre_material': pre_material,
                                                   'adjust_left_weight': pre_material.adjust_left_weight})
                        attrs['status'] = 1
                    # 已用完(异常扫码)
                    else:
                        attrs['tank_data'].update({'msg': '该物料条码已无剩余量,请扫新条码'})
                        attrs['status'] = 2
            else:
                # 扫码物料不在已有物料中
                if material_name not in add_materials.values_list('material_name', flat=True):
                    attrs['tank_data'].update({'actual_weight': 0, 'adjust_left_weight': total_weight})
                    attrs['status'] = 1
                # 同物料扫码
                else:
                    # 配方中物料单车需要重量
                    single_material_weight = classes_plan.product_batching.batching_details.filter(
                        material__material_name=material_name).first().actual_weight if '硫磺' not in material_name and\
                                                                                        '细料' not in material_name else \
                        classes_plan.product_batching.weight_cnt_types.filter(delete_flag=False, name=material_name).first().package_cnt
                    left_weight = add_materials.aggregate(left_weight=Sum('real_weight'))['left_weight']
                    if left_weight > single_material_weight:
                        attrs['tank_data'].update({'msg': '同物料未使用完, 不能扫码'})
                        attrs['status'] = 2
                    else:
                        # 剩余物料 < 单车需要物料
                        attrs['tank_data'].update({'actual_weight': 0, 'adjust_left_weight': total_weight})
                        attrs['status'] = 1
        try:
            resp = requests.post(url=settings.AUXILIARY_URL + 'api/v1/production/current_weigh/',
                                 data=attrs, timeout=5)
            code = resp.status_code
            if code == 200:
                logger.error('条码信息下发成功：{}'.format(resp.text))
            else:
                logger.error('条码信息下发错误：{}'.format(resp.text))
                raise serializers.ValidationError(resp.text)
        except Exception as e:
            logger.error('群控服务器错误！')
            raise serializers.ValidationError(e.args[0])
        if material_name not in classes_plan.product_batching.batching_material_names:
            raise serializers.ValidationError('条码错误，该物料不在生产配方中！')
        msg = attrs['tank_data'].pop('msg')
        if msg:
            raise serializers.ValidationError(msg)
        return attrs

    def create(self, validated_data):
        tank_data = validated_data.get('tank_data')
        pre_material = tank_data.pop('pre_material', '')
        # 上一计划的条码物料归零(同计划中同物料的先一物料扣重时归0)
        if pre_material:
            pre_material.actual_weight = pre_material.init_weight
            pre_material.adjust_left_weight = 0
            pre_material.real_weight = 0
            pre_material.useup_time = datetime.now()
            pre_material.save()
        instance = LoadTankMaterialLog.objects.create(**tank_data)
        return instance

    class Meta:
        model = FeedingMaterialLog
        fields = ('plan_classes_uid', 'bra_code', 'batch_classes', 'batch_group', 'trains')


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
        dev_type = attr['dev_type']
        bra_code = attr['bra_code']
        batch_classes = attr['batch_classes']
        batch_group = attr['batch_group']
        location_no = attr['location_no']
        try:
            wms_stock = MaterialOutHistory.objects.using('wms').filter(
                lot_no=attr['bra_code']).values('material_no', 'material_name')
        except Exception:
            if settings.DEBUG:
                wms_stock = None
            else:
                raise serializers.ValidationError('连接WMS库失败，请联系管理员！')
        if not wms_stock:
            raise serializers.ValidationError('该条码信息不存在！')
        material_name = material_no = ''
        attr['scan_material'] = wms_stock[0].get('material_name')
        material_name_set = set(ERPMESMaterialRelation.objects.filter(
            zc_material__wlxxid=wms_stock[0]['material_no'],
            use_flag=True
        ).values_list('material__material_name', flat=True))
        if not material_name_set:
            raise serializers.ValidationError('该物料未与MES原材料建立绑定关系！')
        # 机台计划配方的所有物料名
        try:
            date_now = datetime.now().date()
            date_before = date_now - timedelta(days=1)
            date_now_planid = ''.join(str(date_now).split('-'))[2:]
            date_before_planid = ''.join(str(date_before).split('-'))[2:]
            all_recipe = Plan.objects.using(equip_no).filter(
                Q(planid__startswith=date_now_planid) | Q(planid__startswith=date_before_planid),
                state__in=['运行中', '等待']).all().values_list('recipe', flat=True)
        except:
            raise serializers.ValidationError('称量机台{}错误'.format(equip_no))
        if not all_recipe:
            raise serializers.ValidationError('机台{}无进行中或已完成的配料计划'.format(equip_no))
        materials = set(RecipeMaterial.objects.using(equip_no).filter(recipe_name__in=set(all_recipe))
                        .values_list('name', flat=True))
        comm_material = list(material_name_set & materials)
        if comm_material:
            material_name = comm_material[0]
            material_no = comm_material[0]
        # else:
        #     raise serializers.ValidationError('所扫物料不在机台{}所有配料计划配方中'.format(equip_no))
        attr['batch_time'] = datetime.now()
        # 扫码物料不在当日计划配方对应原材料中
        if not material_name:
            attr['status'] = 2
            attr['tank_no'] = ''
            attr['failed_reason'] = '不在称量计划内, 无法开门'
        else:
            # 从称量系统同步料罐状态到mes表中
            try:
                tank_status_sync = TankStatusSync(equip_no=equip_no)
                tank_status_sync.sync()
            except:
                raise serializers.ValidationError('mes同步称量系统{}料罐状态失败'.format(equip_no))
            # 扫码物料与所有料罐不一致
            feed_info = WeightTankStatus.objects.filter(equip_no=equip_no, use_flag=True, material_name=material_name)
            if not feed_info:
                attr['status'] = 2
                attr['tank_no'] = ''
                attr['failed_reason'] = '没有对应的料罐, 无法开门'
            else:
                single_tank = feed_info.first()
                if single_tank.status == 2:
                    attr['status'] = 2
                    attr['tank_no'] = ''
                    attr['failed_reason'] = '料罐处于高位, 无法开门'
                else:
                    attr['tank_no'] = single_tank.tank_no
        attr['material_name'] = material_name
        attr['material_no'] = material_no
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

    def validate(self, attrs):
        id = attrs.pop('id')
        record = attrs.get('record')
        print_begin_trains = attrs['print_begin_trains']
        package_count = attrs['package_count']
        plan_weight_uid = attrs['plan_weight_uid']
        product_no = attrs['product_no']
        equip_no = attrs['equip_no']
        package_fufil = attrs['package_fufil']
        batch_classes = attrs['batch_classes']
        dev_type = attrs['dev_type']
        print_flag = attrs.get('print_flag')
        print_count = attrs.get('print_count', 1)
        plan_weight = attrs['plan_weight']
        batch_group = attrs['batch_group']
        package_plan_count = attrs['package_plan_count']
        status = attrs['status']
        # 打印数量判断
        if print_count <= 0 or print_count > package_count or not isinstance(print_count, int):
            raise serializers.ValidationError('打印张数需小于等于配置数量')
        weigh_type = 2 if equip_no.startswith('F') else 1
        weight_type_record = WeighCntType.objects.filter(product_batching__stage_product_batch_no=re.split(r'\(|\（', product_no)[0],
                                                         package_type=1, product_batching__dev_type__category_no=dev_type,
                                                         product_batching__used_type=4, weigh_type=weigh_type)
        if weight_type_record:
            attrs['material_no'] = weight_type_record.first().name
            attrs['material_name'] = attrs['material_no']
        else:
            raise serializers.ValidationError('称量系统计划中配方名称未在mes上找到对应料包名')
        # 配料时间
        batch_time = ReportBasic.objects.using(equip_no).get(planid=plan_weight_uid, actno=print_begin_trains).savetime
        # 计算有效期
        single_expire_record = PackageExpire.objects.filter(product_no=product_no)
        if not single_expire_record:
            single_date = PackageExpire.objects.create(**{'product_no': product_no, 'product_name': product_no,
                                                          'update_user': 'system', 'update_date': datetime.now().date()})
        else:
            single_date = single_expire_record.first()
        days = single_date.package_fine_usefullife if equip_no.startswith('F') else single_date.package_sulfur_usefullife
        data = {'bra_code': '', 'begin_trains': print_begin_trains, 'print_flag': 1, 'status': 'N',
                'end_trains': print_begin_trains + package_count - 1, 'noprint_count': package_fufil - package_count,
                'expire_days': days, 'batch_time': batch_time}
        # 履历表中数据重新打印
        last_print_reocrd = WeightPackageLog.objects.filter(id=id)
        if status == 'Y':
            last_print = last_print_reocrd.first()
            # 修改了起始车次或者包数的重新打印, 新增一条记录到履历表中
            if print_begin_trains != last_print.print_begin_trains or package_count != last_print.package_count:
                # 其实车次配料时间
                attrs.update(data)
            else:
                last_print.print_flag = 1
                last_print.print_count = print_count
                attrs['obj'] = last_print
        else:
            if last_print_reocrd and print_flag == 1 and print_begin_trains == last_print_reocrd.first().print_begin_trains\
                    and package_count == last_print_reocrd.first().package_count:
                raise serializers.ValidationError('已下发打印，等待打印机打印')
            # 生产计划中数据新增打印
            # 起始车次和数量的判断
            if print_begin_trains == 0 or print_begin_trains > package_fufil - 1:
                raise serializers.ValidationError('起始车次不在{}-{}的可选范围'.format(1, package_fufil - 1))
            if package_count > package_fufil - print_begin_trains + 1 or package_count <= 0:
                raise serializers.ValidationError('配置数量不在{}-{}的可选范围'.format(1, package_fufil - print_begin_trains + 1))
            attrs.update(data)
        if 'obj' not in attrs:
            # 生成条码: 机台（3位）+年月日（8位）+班次（1位）+自增数（4位） 班次：1早班  2中班  3晚班
            # 履历表中无数据则初始为1, 否则获取最大数+1
            incr_num = 1 if WeightPackageLog.objects.count() == 0 else \
                int(WeightPackageLog.objects.all().order_by('-created_date').first().bra_code[-4:]) + 1
            map_list = {"早班": '1', "中班": '2', "夜班": '3'}
            train_batch_classes = map_list.get(batch_classes)
            bra_code = equip_no + ''.join(batch_time[:10].split('-')) + train_batch_classes + '%04d' % incr_num
            attrs.update({'bra_code': bra_code})
        return attrs

    def create(self, validated_data):
        if 'obj' in validated_data:
            instance = validated_data['obj']
            instance.save()
        else:
            instance = WeightPackageLog.objects.create(**validated_data)
        return instance

    class Meta:
        model = WeightPackageLog
        fields = ['plan_weight_uid', 'product_no', 'plan_weight', 'dev_type', 'id', 'record', 'print_flag',
                  'package_count', 'print_begin_trains', 'noprint_count', 'package_fufil', 'package_plan_count',
                  'equip_no', 'batch_group', 'batch_classes', 'status', 'print_count']


class WeightPackageLogUpdateSerializer(serializers.ModelSerializer):
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
    # batch_time = serializers.DateTimeField(format='%Y-%m-%d', help_text='配料日期')

    class Meta:
        model = WeightPackageLog
        fields = ['id', 'plan_weight_uid', 'product_no', 'plan_weight', 'dev_type', 'batch_time', 'bra_code', 'record',
                  'package_count', 'print_begin_trains', 'noprint_count', 'package_fufil', 'package_plan_count',
                  'equip_no', 'print_flag', 'batch_group', 'status', 'begin_trains', 'end_trains', 'batch_classes']


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

    def get_batch_group(self, obj):
        work_schedule_plan = PlanSchedule.objects.filter(day_time=obj.date_time, delete_flag=False)\
            .select_related('work_schedule')\
            .prefetch_related('work_schedule_plan__classes', 'work_schedule_plan__group')[0].work_schedule_plan
        for i in work_schedule_plan.values_list('classes', 'group'):
            classes = GlobalCode.objects.get(id=i[0]).global_name
            if classes == obj.grouptime:
                return GlobalCode.objects.get(id=i[1]).global_name

    class Meta:
        model = Plan
        fields = ['id', 'plan_weight_uid', 'product_no', 'plan_weight', 'batch_time', 'noprint_count', 'package_fufil',
                  'print_flag', 'package_plan_count', 'dev_type', 'bra_code', 'record', 'package_count', 'status',
                  'print_begin_trains', 'equip_no', 'batch_group', 'begin_trains', 'end_trains', 'batch_classes']


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
    weight_batch_no = serializers.SerializerMethodField(help_text='小料配方', read_only=True)

    def get_weight_batch_no(self, obj):
        try:
            plan_batching_uid = obj.plan_batching_uid
            bcp_obj = BatchingClassesPlan.objects.filter(plan_batching_uid=plan_batching_uid, delete_flag=False).first()
            weight_batch_no = bcp_obj.weigh_cnt_type.weigh_batching.weight_batch_no
            return weight_batch_no
        except Exception as e:
            # print(e)
            return None

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
            instance = MaterialInfo.objects.using(equip_no).create(**validated_data)
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


class PlanSerializer(serializers.ModelSerializer):
    equip_no = serializers.CharField(write_only=True, help_text='称量机台')

    def create(self, validated_data):
        equip_no = validated_data.pop('equip_no')
        validated_data['planid'] = datetime.now().strftime('%Y%m%d%H%M%S')[2:]
        validated_data['state'] = '等待'
        validated_data['actno'] = 0
        validated_data['order_by'] = 1
        validated_data['addtime'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        validated_data['oper'] = self.context['request'].user.username
        try:
            instance = Plan.objects.using(equip_no).create(**validated_data)
        except ConnectionDoesNotExist:
            raise serializers.ValidationError('称量机台{}服务错误！'.format(equip_no))
        except Exception:
            raise
        return instance

    class Meta:
        model = Plan
        read_only_fields = ('planid', 'state', 'actno', 'order_by', 'addtime', 'starttime', 'stoptime', 'oper')
        fields = '__all__'


class PlanUpdateSerializer(serializers.ModelSerializer):
    action = serializers.IntegerField(help_text='动作 1：下达计划  2：计划重传  3：修改车次 4：计划停止', write_only=True)
    equip_no = serializers.CharField(write_only=True, help_text='称量机台')

    def update(self, instance, validated_data):
        action = validated_data['action']
        equip_no = validated_data['equip_no']
        if settings.DEBUG:
            if action == 1:
                instance.state = '运行'
                instance.save()
            elif action == 2:
                pass
            elif action == 3:
                setno = validated_data['setno']
                actno = instance.actno if instance.actno else 0
                if not setno:
                    raise serializers.ValidationError('设定车次不可为空!')
                if setno <= actno:
                    raise serializers.ValidationError('设定车次不能小于完成车次!')
                instance.setno = setno
                instance.save()
            elif action == 4:
                instance.state = '终止'
                instance.save()
        else:
            ins = INWeighSystem(equip_no)
            if action == 1:
                ins.issue_plan({
                    "plan_no": instance.planid,
                    "recipe_no": instance.recipe,
                    "num": instance.setno,
                    "action": "1"
                    })
            elif action == 2:
                ins.reload_plan(
                    {
                        "plan_no": instance.planid,
                        "action": "1",
                    }
                )
            elif action == 3:
                setno = validated_data['setno']
                actno = instance.actno if instance.actno else 0
                if not setno:
                    raise serializers.ValidationError('设定车次不可为空!')
                if setno <= actno:
                    raise serializers.ValidationError('设定车次不能小于完成车次!')
                ins.update_trains(
                    {
                        "plan_no": instance.planid,
                        "action": "1",
                        "num": instance.setno
                    }
                )
            elif action == 4:
                ins.stop({
                            "plan_no": instance.planid,
                            "action": "1"
                        })
            else:
                raise serializers.ValidationError('action参数错误！')
        return instance

    class Meta:
        model = Plan
        fields = ('id', 'setno', 'action', 'equip_no')


class RecipePreSerializer(serializers.ModelSerializer):

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
