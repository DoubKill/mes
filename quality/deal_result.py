import datetime
import time

from inventory.tasks import update_wms_kjjg
from mes.common_code import order_no
from quality.models import MaterialDealResult, MaterialTestOrder, MaterialTestResult, LevelResult, \
    MaterialDataPointIndicator, MaterialTestMethod
from production.models import PalletFeedbacks
from django.db.transaction import atomic
from django.db.models import Max, Min


@atomic()
def synthesize_to_material_deal_result(mdr_lot_no):
    """等级综合判定"""
    # 1、先找到这个胶料所有指标
    mto_set_all = MaterialTestOrder.objects.filter(lot_no=mdr_lot_no).values_list('product_no', flat=True)
    mto_product_no_list = list(mto_set_all)
    mtm_set = MaterialTestMethod.objects.filter(material__material_name__in=mto_product_no_list).all()
    name_list = []
    for mtm_obj in mtm_set:
        name = mtm_obj.test_method.test_type.test_indicator.name
        name_list.append(name)

    # 2、判断快检这边是不是所有的指标都有
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
    quality_point_indicator = True
    is_hege = True
    quality_sign = True  # 快检判定何三等品
    for mtr_obj in level_list:
        if not mtr_obj.mes_result:  # mes没有数据
            if not mtr_obj.result:  # 快检也没有数据
                reason = reason + f'{mtr_obj.material_test_order.actual_trains}车{mtr_obj.data_point_name}指标{mtr_obj.value}没有判定区间，\n'
                exist_data_point_indicator = False
            elif mtr_obj.result != '一等品':
                reason = reason + f'{mtr_obj.material_test_order.actual_trains}车{mtr_obj.data_point_name}指标{mtr_obj.value}在快检判为{mtr_obj.result}，\n'
                quality_sign = False

        elif mtr_obj.mes_result == '一等品':
            if mtr_obj.result not in ['一等品', None]:
                reason = reason + f'{mtr_obj.material_test_order.actual_trains}车{mtr_obj.data_point_name}指标{mtr_obj.value}在快检判为{mtr_obj.result}，\n'
                quality_sign = False

        elif mtr_obj.mes_result != '一等品':
            reason = reason + f'{mtr_obj.material_test_order.actual_trains}车{mtr_obj.data_point_name}指标{mtr_obj.value}在[{mtr_obj.data_point_indicator.lower_limit}:{mtr_obj.data_point_indicator.upper_limit}]，\n'

        if not max_mtr.data_point_indicator:
            max_mtr = mtr_obj
            is_hege = False
            continue
        if not mtr_obj.data_point_indicator:
            is_hege = False
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
    # try:
    #     msg_ids = order_no()
    #     mto_obj = MaterialTestOrder.objects.filter(lot_no=mdr_obj.lot_no).first()
    #     pfb_obj = PalletFeedbacks.objects.filter(pallet_no=mdr_obj.lot_no).first()
    #     item = []
    #     item_dict = {"WORKID": str(int(msg_ids) + 1), "MID": mto_obj.product_no, "PICI": pfb_obj.bath_no,
    #                  "NUM": mdr_obj.lot_no,
    #                  "KJJG": mdr_obj.deal_result,
    #                  "SENDDATE": datetime.datetime.now().strftime('%Y%m%d %H:%M:%S')}
    #     item.append(item_dict)
    #     jieguo = update_wms_kjjg(msg_id=msg_ids, items=item)
    # except:
    #     pass
    # else:
    #     mdr_obj.update_store_test_flag = True
    #     mdr_obj.save()
