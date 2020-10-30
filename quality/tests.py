from django.test import TestCase

# Create your tests here.
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()
from quality.models import MaterialDealResult, MaterialTestOrder
from production.models import PalletFeedbacks
from django.db.transaction import atomic


@atomic()
def synthesize_to_material_deal_result():
    MaterialDealResult.objects.all().delete()
    mdr_lot_no_list = list(set(MaterialTestOrder.objects.values_list('lot_no', flat=True)))
    mdr_dict = {}
    for mdr_lot_no in mdr_lot_no_list:
        mdr_dict['lot_no'] = mdr_lot_no
        mto_set = MaterialTestOrder.objects.filter(lot_no=mdr_lot_no).all()
        level_list = []
        for mto_obj in mto_set:
            mrt_obj = mto_obj.order_results.all().order_by('test_times').last()
            level_list.append(mrt_obj)
        max_mtr = level_list[0]
        # 找到检测次数最多的几条 每一条的等级进行比较选出做大的
        reason = ''
        for mtr_obj in level_list:
            if mtr_obj.data_point_indicator.level > max_mtr.data_point_indicator.level:
                max_mtr = mtr_obj
            # 判断value值与指标上下限
            if mtr_obj.value < mtr_obj.data_point_indicator.lower_limit:
                reason = reason + f'第{mtr_obj.material_test_order.actual_trains}车次{mtr_obj.test_indicator_name}指标{mtr_obj.value}低于下限{mtr_obj.data_point_indicator.lower_limit}，\n'
            if mtr_obj.value > mtr_obj.data_point_indicator.upper_limit:
                reason = reason + f'第{mtr_obj.material_test_order.actual_trains}车次{mtr_obj.test_indicator_name}指标{mtr_obj.value}高于上限{mtr_obj.data_point_indicator.upper_limit}，\n'
            if mtr_obj.data_point_indicator.lower_limit <= mtr_obj.value <= mtr_obj.data_point_indicator.upper_limit:
                reason = reason + f'第{mtr_obj.material_test_order.actual_trains}车次{mtr_obj.test_indicator_name}指标{mtr_obj.value}在{mtr_obj.data_point_indicator.lower_limit}至{mtr_obj.data_point_indicator.upper_limit}区间内，\n'

        # 在生产模块里找开始生产时间
        pfb_obj = PalletFeedbacks.objects.filter(lot_no=mdr_lot_no).last()
        mdr_dict['level'] = max_mtr.data_point_indicator.level
        mdr_dict['deal_result'] = max_mtr.data_point_indicator.result
        mdr_dict['reason'] = reason
        mdr_dict['status'] = '待处理'
        mdr_dict['production_factory_date'] = pfb_obj.begin_time
        print(mdr_dict)
        MaterialDealResult.objects.create(**mdr_dict)


if __name__ == '__main__':
    synthesize_to_material_deal_result()
