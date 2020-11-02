'''
统计和分析快检模块的数据，并将其存入MaterialDealResult（胶料处理结果）表中
'''

import os
import time

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()
from quality.models import MaterialDealResult, MaterialTestOrder, MaterialTestResult
from production.models import PalletFeedbacks
from django.db.transaction import atomic
from django.db.models import Max
import logging

logger = logging.getLogger('send_log')


@atomic()
def synthesize_to_material_deal_result():
    mdr_lot_no_list = list(set(MaterialTestOrder.objects.values_list('lot_no', flat=True)))
    mdr_dict = {}
    for mdr_lot_no in mdr_lot_no_list:
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
        for mtr_obj in level_list:
            if not mtr_obj.data_point_indicator:
                reason = reason + f'第{mtr_obj.material_test_order.actual_trains}车次{mtr_obj.data_point_name}指标{mtr_obj.value}数据错误！，\n'
                exist_data_point_indicator = False
            else:
                if mtr_obj.data_point_indicator.level > max_mtr.data_point_indicator.level:
                    max_mtr = mtr_obj
                # 判断value值与指标上下限
                if mtr_obj.data_point_indicator.result == "合格":
                    continue
                if mtr_obj.value < mtr_obj.data_point_indicator.lower_limit:
                    reason = reason + f'第{mtr_obj.material_test_order.actual_trains}车次{mtr_obj.data_point_name}指标{mtr_obj.value}低于下限{mtr_obj.data_point_indicator.lower_limit}，\n'
                if mtr_obj.value > mtr_obj.data_point_indicator.upper_limit:
                    reason = reason + f'第{mtr_obj.material_test_order.actual_trains}车次{mtr_obj.data_point_name}指标{mtr_obj.value}高于上限{mtr_obj.data_point_indicator.upper_limit}，\n'
                if mtr_obj.data_point_indicator.lower_limit <= mtr_obj.value <= mtr_obj.data_point_indicator.upper_limit:
                    reason = reason + f'第{mtr_obj.material_test_order.actual_trains}车次{mtr_obj.data_point_name}指标{mtr_obj.value}在{mtr_obj.data_point_indicator.lower_limit}至{mtr_obj.data_point_indicator.upper_limit}区间内，\n'

        # 在生产模块里找开始生产时间
        pfb_obj = PalletFeedbacks.objects.filter(lot_no=mdr_lot_no).last()
        if exist_data_point_indicator:
            mdr_dict['level'] = max_mtr.data_point_indicator.level
            mdr_dict['deal_result'] = max_mtr.data_point_indicator.result
            mdr_dict['production_factory_date'] = pfb_obj.begin_time
        else:  # 数据不在上下限范围内，这个得前端做好约束
            mdr_dict['deal_result'] = '不合格！'
            mdr_dict['level'] = 0
            mdr_dict['production_factory_date'] = '1212-12-12'

        mdr_dict['reason'] = reason
        mdr_dict['status'] = '待处理'

        iir_mdr_obj = MaterialDealResult.objects.filter(lot_no=mdr_lot_no).first()
        if iir_mdr_obj:
            MaterialDealResult.objects.filter(lot_no=mdr_lot_no).update(**mdr_dict)
        else:
            MaterialDealResult.objects.create(**mdr_dict)


def run():
    logger.info("统计和分析快检模块的数据，并将其存入MaterialDealResult（胶料处理结果）表中")
    while True:
        try:
            synthesize_to_material_deal_result()
        except Exception as e:
            logger.error(f"{synthesize_to_material_deal_result.__doc__}|{e}")
        # 每五秒统计一次
        time.sleep(5)


if __name__ == '__main__':
    run()
