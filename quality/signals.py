# -*- coding: UTF-8 -*-
"""
auther:
datetime: 2020/9/29
name:
"""
import traceback

from django.db.models import Max
from django.db.models.signals import post_save
from django.dispatch import receiver

from production.models import PalletFeedbacks
from quality.models import MaterialTestResult, MaterialTestOrder, MaterialDealResult, \
    MaterialDataPointIndicator, DataPointStandardError
import logging

logger = logging.getLogger('quality_log')


def judge_standard_error_deal_suggestion(data_point_name, product_no, value):
    """
    寻找某个数据点在某个的pass章范围的处理意见
    @param data_point_name: 数据点名称
    @param product_no: 胶料名称
    @param value: 数据点检测值
    @return: pass章处理意见
    """
    indicator = MaterialDataPointIndicator.objects.filter(
        data_point__name=data_point_name,
        material_test_method__material__material_name=product_no,
        level=1).first()
    if indicator:
        upper_limit = indicator.upper_limit
        lower_limit = indicator.lower_limit
        for error in DataPointStandardError.objects.filter(data_point__name=data_point_name).all():
            lower_value = error.lower_value
            upper_value = error.upper_value
            lv_type = error.lv_type
            uv_type = error.uv_type
            if lower_value >= 0 and upper_value >= 0:
                a = value >= upper_limit + lower_value if lv_type == 1 else value > upper_limit + lower_value
                b = value <= upper_limit + upper_value if uv_type == 1 else value < upper_limit + upper_value
                if a and b:
                    return error.label
            elif lower_value <= 0 and upper_value <= 0:
                a = value >= lower_value + lower_limit if lv_type == 1 else value > lower_value + lower_limit
                b = value <= upper_value + lower_limit if uv_type == 1 else value < upper_value + lower_limit
                if a and b:
                    return error.label
            else:
                a = value >= lower_value + lower_limit if lv_type == 1 else value > lower_value + lower_limit
                b = value <= upper_value + upper_limit if uv_type == 1 else value < upper_value + upper_limit
                if a and b:
                    return error.label
                return None
        return None
    return None


@receiver(post_save, sender=MaterialTestResult)
def batching_post_save(sender, instance=None, created=False, update_fields=None, **kwargs):
    # 等级综合判定
    try:
        if created:
            # 取test_order
            material_test_order = instance.material_test_order

            # 该test_order所有数据点最后检测result
            max_result_ids = list(material_test_order.order_results.values(
                'test_indicator_name', 'test_method_name', 'data_point_name'
            ).annotate(max_id=Max('id')).values_list('max_id', flat=True))

            # 判断该test_order是否合格：根据最后数据点的检测值等级等级大于1判断
            if max_result_ids:
                test_results = MaterialTestResult.objects.filter(id__in=max_result_ids)
                if test_results.filter(level__gt=1).exists():
                    material_test_order.is_qualified = False
                else:
                    material_test_order.is_qualified = True

            # 判断当前数据点检测值是否在合格区间，存在的话更新改test_result的is_passed字段为true和处理意见
            if instance.level > 1:
                deal_suggestion = judge_standard_error_deal_suggestion(instance.data_point_name,
                                                                       material_test_order.product_no,
                                                                       instance.value)
                if deal_suggestion:
                    MaterialTestResult.objects.filter(
                        id=instance.id).update(
                        is_passed=True, pass_suggestion=deal_suggestion)
            else:
                MaterialTestResult.objects.filter(id=instance.id).update(is_passed=False)

            # 判断该test_order是否pass：根据这最新所有数据点通过pass章的数量和不合格的数据点是否都等于1，是的话更新is_passed字段为true
            test_order_passed_count = MaterialTestResult.objects.filter(id__in=max_result_ids, is_passed=True).count()
            test_order_unqualified_count = MaterialTestResult.objects.filter(id__in=max_result_ids, level__gt=1).count()
            if test_order_passed_count == test_order_unqualified_count == 1:
                material_test_order.is_passed = True
            else:
                material_test_order.is_passed = False
            material_test_order.save()

            # 取托盘所有test_order
            lot_no = material_test_order.lot_no
            pfb_obj = PalletFeedbacks.objects.filter(lot_no=lot_no).first()
            if not pfb_obj:
                return
            test_orders = MaterialTestOrder.objects.filter(lot_no=lot_no)

            # 取检测车次
            test_trains_set = set(test_orders.values_list('actual_trains', flat=True))
            # 取托盘反馈生产车次
            actual_trains_set = {i for i in range(pfb_obj.begin_trains, pfb_obj.end_trains + 1)}

            common_trains_set = actual_trains_set & test_trains_set
            # 判断托盘反馈车次都存在检测数据
            if not len(actual_trains_set) == len(test_trains_set) == len(common_trains_set):
                return

            # 判断该托盘所有test_order检测结果

            # 1、只有一车为pass章的
            if MaterialTestOrder.objects.filter(lot_no=material_test_order.lot_no, is_passed=True).count() == 1:
                level = 1
                test_result = 'PASS'
                last_result_ids = list(MaterialTestResult.objects.filter(
                    material_test_order__lot_no=lot_no).values(
                    'material_test_order', 'test_indicator_name', 'test_method_name', 'data_point_name'
                ).annotate(max_id=Max('id')).values_list('max_id', flat=True))
                # 取该托唯一一个pass章的数据点
                passed_result = MaterialTestResult.objects.filter(
                    id__in=last_result_ids,
                    is_passed=True).last()
                deal_suggestion = getattr(passed_result, 'pass_suggestion', '放行')
            # 2、所有车次都合格
            elif not MaterialTestOrder.objects.filter(is_qualified=False,
                                                      lot_no=material_test_order.lot_no).exists():
                level = 1
                test_result = '一等品'
                deal_suggestion = '合格'
            # 3、不合格
            else:
                level = 3
                test_result = '三等品'
                deal_suggestion = '不合格'

            deal_result_dict = {
                'level': level,
                'test_result': test_result,
                'reason': 'reason',
                'status': '待处理',
                'deal_result': '一等品' if level == 1 else '三等品',
                'production_factory_date': pfb_obj.end_time,
                'deal_suggestion': deal_suggestion
            }
            instance = MaterialDealResult.objects.filter(lot_no=lot_no)
            if instance:
                deal_result_dict['update_store_test_flag'] = 4
                instance.update(**deal_result_dict)
            else:
                deal_result_dict['lot_no'] = lot_no
                MaterialDealResult.objects.create(**deal_result_dict)
    except Exception as e:
        logger.error(traceback.format_exc())
