from quality.models import MaterialDealResult, MaterialTestOrder, MaterialTestResult, LevelResult, \
    MaterialDataPointIndicator
from production.models import PalletFeedbacks
from django.db.transaction import atomic
from django.db.models import Max, Min


@atomic()
def synthesize_to_material_deal_result(mdr_lot_no):
    """等级综合判定"""
    mdr_dict = {}
    mdr_dict['lot_no'] = mdr_lot_no
    mto_set = MaterialTestOrder.objects.filter(lot_no=mdr_lot_no).all()
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
    exist_data_point_indicator = True
    quality_point_indicator = True
    is_hege = True
    for mtr_obj in level_list:
        if not mtr_obj.mes_result:  # mes找到不合格数据
            reason = reason + f'{mtr_obj.material_test_order.actual_trains}车{mtr_obj.data_point_name}指标{mtr_obj.value}没有判定区间，\n'
            exist_data_point_indicator = False
        elif mtr_obj.mes_result != '合格':
            reason = reason + f'{mtr_obj.material_test_order.actual_trains}车{mtr_obj.data_point_name}指标{mtr_obj.value}在[{mtr_obj.data_point_indicator.lower_limit}:{mtr_obj.data_point_indicator.upper_limit}]，\n'
            exist_data_point_indicator = False
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
    if not exist_data_point_indicator:  # mes判断
        if max_mtr.data_point_indicator:
            if is_hege:
                mdr_dict['level'] = max_mtr.data_point_indicator.level
                mdr_dict['deal_result'] = max_mtr.mes_result
            else:
                mdr_dict['level'] = MaterialDataPointIndicator.objects.aggregate(Max('level'))['level__max']
                mdr_dict['deal_result'] = '不合格'
        else:
            mdp_obj = MaterialDataPointIndicator.objects.filter(delete_flag=False, result='不合格').first()
            if mdp_obj:
                mdr_dict['level'] = mdp_obj.level
            else:
                mdr_dict['level'] = MaterialDataPointIndicator.objects.aggregate(Max('level'))['level__max']
            mdr_dict['deal_result'] = '不合格'
    else:
        for mtr_obj in level_list:  # 快检系统找到不合格数据
            reason = reason + '在快检系统中：'
            if mtr_obj.result not in ['合格', None]:
                reason = reason + f'{mtr_obj.material_test_order.actual_trains}车{mtr_obj.data_point_name}指标{mtr_obj.value}{mtr_obj.result}\n'
                quality_point_indicator = False

        if not quality_point_indicator:  # 快检判断
            mdp_obj = MaterialDataPointIndicator.objects.filter(delete_flag=False, result='不合格').first()
            if mdp_obj:
                mdr_dict['level'] = mdp_obj.level
            else:
                mdr_dict['level'] = MaterialDataPointIndicator.objects.aggregate(Max('level'))['level__max']
            mdr_dict['deal_result'] = '不合格'
        else:
            mdp_obj = MaterialDataPointIndicator.objects.filter(delete_flag=False, result='合格').first()
            if mdp_obj:
                mdr_dict['level'] = mdp_obj.level
            else:
                mdr_dict['level'] = MaterialDataPointIndicator.objects.aggregate(Min('level'))['level__min']
            mdr_dict['deal_result'] = '合格'
    pfb_obj = PalletFeedbacks.objects.filter(lot_no=mdr_lot_no).last()
    mdr_dict['production_factory_date'] = pfb_obj.begin_time

    iir_mdr_obj = MaterialDealResult.objects.filter(lot_no=mdr_lot_no).order_by('test_time').last()
    if iir_mdr_obj:
        mdr_dict['test_time'] = iir_mdr_obj.test_time + 1
        MaterialDealResult.objects.filter(lot_no=mdr_lot_no).update(status='复测')
        MaterialDealResult.objects.create(**mdr_dict)
    else:
        mdr_dict['test_time'] = 1
        MaterialDealResult.objects.create(**mdr_dict)
