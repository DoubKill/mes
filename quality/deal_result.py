import datetime
import json
import time

from inventory.models import BzFinalMixingRubberInventory, MaterialInventory
from inventory.tasks import update_wms_kjjg
from mes.common_code import order_no, DecimalEncoder
from quality.models import MaterialDealResult, MaterialTestOrder, MaterialTestResult, LevelResult, \
    MaterialDataPointIndicator, MaterialTestMethod
from production.models import PalletFeedbacks
from quality.serializers import MaterialDealResultListSerializer
from django.db.transaction import atomic
from django.db.models import Max, Min
import logging

logger = logging.getLogger('send_log')


def synthesize_to_material_deal_result(mdr_lot_no):
    """等级综合判定"""

    # 1、先找到这个胶料所有指标
    logger.error("1、先找到这个胶料所有指标")
    mto_set_all = MaterialTestOrder.objects.filter(lot_no=mdr_lot_no).values_list('product_no', flat=True)
    mto_product_no_list = list(mto_set_all)
    mtm_set = MaterialTestMethod.objects.filter(material__material_name__in=mto_product_no_list).all()
    name_list = []
    for mtm_obj in mtm_set:
        name = mtm_obj.test_method.test_type.test_indicator.name
        name_list.append(name)

    # 2、 判断是否所有车次都有
    logger.error("2、 判断是否所有车次都有")
    actual_trains_list = MaterialTestOrder.objects.filter(lot_no=mdr_lot_no).values_list('actual_trains', flat=True)
    train_liat = list(actual_trains_list)
    pfb_obj = PalletFeedbacks.objects.filter(lot_no=mdr_lot_no).first()
    for i in range(pfb_obj.begin_trains, pfb_obj.end_trains + 1):
        if i not in train_liat:
            return

    # 3、判断快检这边是不是所有的指标都有
    logger.error("3、判断快检这边是不是所有的指标都有")
    mto_set = MaterialTestOrder.objects.filter(lot_no=mdr_lot_no).all()
    for mto_obj in mto_set:
        test_indicator_name_list = []
        mtr_dpn_list = mto_obj.order_results.all().values('test_indicator_name').annotate(
            max_test_time=Max('test_times'))
        for mtr_dpn_dict in mtr_dpn_list:
            test_indicator_name_list.append(mtr_dpn_dict['test_indicator_name'])
        test_indicator_name_list = list(set(test_indicator_name_list))
        for name in name_list:
            if name not in test_indicator_name_list:  # 必须胶料所有的指标快检这边都有 没有就return
                return

    # 4、分析流程
    logger.error("4、分析流程")
    mdr_dict = {}
    mdr_dict['lot_no'] = mdr_lot_no
    level_list = []
    for mto_obj in mto_set:
        mrt_list = mto_obj.order_results.all().values('data_point_name').annotate(max_test_time=Max('test_times'))
        for mrt_dict in mrt_list:
            mrt_dict_obj = MaterialTestResult.objects.filter(material_test_order=mto_obj,
                                                             data_point_name=mrt_dict['data_point_name'],
                                                             test_times=mrt_dict['max_test_time']).last()
            level_list.append(mrt_dict_obj)
    max_mtr = level_list[0]
    # 找到检测次数最多的几条 每一条的等级进行比较选出做大的
    reason = ''
    exist_data_point_indicator = True  # 是否超出区间范围
    quality_sign = True  # 快检判定何三等品
    for mtr_obj in level_list:
        if not mtr_obj.mes_result:  # mes没有数据
            if not mtr_obj.result:  # 快检也没有数据
                reason = reason + f'{mtr_obj.material_test_order.actual_trains}车{mtr_obj.data_point_name}指标{mtr_obj.value}不在一等品判定区间，\n'
                exist_data_point_indicator = False
            elif mtr_obj.result not in ['一等品', '合格', None, '']:
                reason = reason + f'{mtr_obj.material_test_order.actual_trains}车{mtr_obj.data_point_name}指标{mtr_obj.value}在快检判为{mtr_obj.result}，\n'
                quality_sign = False

        elif mtr_obj.mes_result in ['一等品', '合格']:
            if mtr_obj.result not in ['一等品', '合格', None, '']:
                reason = reason + f'{mtr_obj.material_test_order.actual_trains}车{mtr_obj.data_point_name}指标{mtr_obj.value}在快检判为{mtr_obj.result}，\n'
                quality_sign = False

        elif mtr_obj.mes_result not in ['一等品', '合格']:
            if mtr_obj.data_point_indicator:
                reason = reason + f'{mtr_obj.material_test_order.actual_trains}车{mtr_obj.data_point_name}指标{mtr_obj.value}在[{mtr_obj.data_point_indicator.lower_limit}:{mtr_obj.data_point_indicator.upper_limit}]，\n'
            else:
                reason = reason + f'{mtr_obj.material_test_order.actual_trains}车{mtr_obj.data_point_name}指标{mtr_obj.value}不在一等品判断区间内，\n'
                exist_data_point_indicator = False
        if not max_mtr.data_point_indicator:
            max_mtr = mtr_obj
            continue
        if not mtr_obj.data_point_indicator:
            continue
        if mtr_obj.data_point_indicator.level > max_mtr.data_point_indicator.level:
            max_mtr = mtr_obj

    mdr_dict['reason'] = reason
    mdr_dict['status'] = '待处理'

    if exist_data_point_indicator:
        if quality_sign:
            mdr_dict['level'] = max_mtr.data_point_indicator.level
            mdr_dict['deal_result'] = max_mtr.mes_result
        else:
            mdr_dict['level'] = MaterialDataPointIndicator.objects.aggregate(Max('level'))['level__max']
            mdr_dict['deal_result'] = '三等品'
    else:
        mdr_dict['level'] = MaterialDataPointIndicator.objects.aggregate(Max('level'))['level__max']
        mdr_dict['deal_result'] = '三等品'

    pfb_obj = PalletFeedbacks.objects.filter(lot_no=mdr_lot_no).last()
    mdr_dict['production_factory_date'] = pfb_obj.begin_time

    iir_mdr_obj = MaterialDealResult.objects.filter(lot_no=mdr_lot_no).order_by('test_time').last()
    if iir_mdr_obj:
        mdr_dict['test_time'] = iir_mdr_obj.test_time + 1
        MaterialDealResult.objects.filter(lot_no=mdr_lot_no).update(status='复测')
        mdr_obj = MaterialDealResult.objects.create(**mdr_dict)
    else:
        mdr_dict['test_time'] = 1
        mdr_obj = MaterialDealResult.objects.create(**mdr_dict)

    # 5、向北自接口发送数据
    # 5.1、先判断库存和线边库里有没有数据
    pfb_obj = PalletFeedbacks.objects.filter(lot_no=mdr_obj.lot_no).first()
    bz_obj = BzFinalMixingRubberInventory.objects.using('bz').filter(container_no=pfb_obj.pallet_no).last()
    mi_obj = MaterialInventory.objects.filter(lot_no=mdr_obj.lot_no).first()
    # 5.2、一个库里有就发给北自，没有就不发给北自
    if bz_obj or mi_obj:
        try:
            # 4、update_store_test_flag这个字段用choise 1对应成功 2对应失败 3对应库存线边库都没有
            msg_ids = order_no()
            mto_obj = MaterialTestOrder.objects.filter(lot_no=mdr_obj.lot_no).first()
            pfb_obj = PalletFeedbacks.objects.filter(lot_no=mdr_obj.lot_no).first()
            item = []
            item_dict = {"WORKID": str(int(msg_ids) + 1),
                         "MID": mto_obj.product_no,
                         "PICI": str(pfb_obj.plan_classes_uid),
                         "RFID": pfb_obj.pallet_no,
                         "DJJG": mdr_obj.deal_result,
                         "SENDDATE": datetime.datetime.now().strftime('%Y%m%d %H:%M:%S')}
            item.append(item_dict)
            # 向北自发送数据
            logger.error("向北自发送数据")
            res = update_wms_kjjg(msg_id=msg_ids, items=item)
            if not res:  # res为空代表成功
                mdr_obj.update_store_test_flag = 1
                mdr_obj.save()
                logger.error("向北自发送数据,发送成功")
            else:
                mdr_obj.update_store_test_flag = 2
                mdr_obj.save()
                logger.error(f"发送失败{res}")
        except Exception as e:
            logger.error(f"调北自接口发生异常：{e}")
            pass
    else:  # 两个库都没有
        mdr_obj.update_store_test_flag = 3
        mdr_obj.save()
        logger.error("没有发送，两个库存和线边库里都没有")


def receive_deal_result(lot_no):
    """将快检信息综合管理接口(就是打印的卡片信息)封装成一个类，需要的时候就调用一下"""
    mdr_obj = MaterialDealResult.objects.filter(lot_no=lot_no).exclude(status='复测').last()
    mdrls = MaterialDealResultListSerializer()
    results = {}
    # id
    results['id'] = mdr_obj.id
    # day_time
    results['day_time'] = str(mdrls.get_day_time(mdr_obj))
    # lot_no
    results['lot_no'] = mdr_obj.lot_no
    # classes_group
    results['classes_group'] = mdrls.get_classes_group(mdr_obj)
    # equip_no
    results['equip_no'] = mdrls.get_equip_no(mdr_obj)
    # product_no
    results['product_no'] = mdrls.get_product_no(mdr_obj)
    # actual_weight
    results['actual_weight'] = mdrls.get_actual_weight(mdr_obj)
    # residual_weight
    results['residual_weight'] = mdrls.get_residual_weight(mdr_obj)
    # production_factory_date
    results['production_factory_date'] = str(mdr_obj.production_factory_date)
    # valid_time
    results['valid_time'] = mdrls.get_valid_time(mdr_obj)
    # test
    results['test'] = mdrls.get_test(mdr_obj)
    # print_time
    results['print_time'] = mdr_obj.print_time.strftime("%Y-%m-%d %H:%M:%S") if mdr_obj.print_time else None
    # deal_user
    results['deal_user'] = mdrls.get_deal_user(mdr_obj)
    # deal_time
    results['deal_time'] = mdrls.get_deal_time(mdr_obj)
    # mtr_list
    results['mtr_list'] = mdrls.get_mtr_list(mdr_obj)
    # actual_trains
    results['actual_trains'] = mdrls.get_actual_trains(mdr_obj)
    # operation_user
    results['operation_user'] = mdrls.get_operation_user(mdr_obj)
    # deal_result
    results['deal_result'] = mdr_obj.deal_result
    # deal_suggestion
    results['deal_suggestion'] = mdrls.get_deal_suggestion(mdr_obj)
    results = json.dumps(results, cls=DecimalEncoder)
    return results
