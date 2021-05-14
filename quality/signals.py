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

logger = logging.getLogger('send_log')


@receiver(post_save, sender=MaterialTestResult)
def batching_post_save(sender, instance=None, created=False, update_fields=None, **kwargs):
    # 等级综合判定
    try:
        if created:
            """
            判断该车次检测信息是否合格
            """
            material_test_order = instance.material_test_order
            max_result_ids = list(material_test_order.order_results.values(
                'test_indicator_name', 'test_method_name', 'data_point_name'
            ).annotate(max_id=Max('id')).values_list('max_id', flat=True))
            if max_result_ids:
                test_results = MaterialTestResult.objects.filter(id__in=max_result_ids)
                if test_results.filter(level__gt=1).exists():
                    material_test_order.is_qualified = False
                else:
                    material_test_order.is_qualified = True

                # 判断该车次检测信息是否为pass(只需判断不合格数据点数量为1，且在pass范围内)
                if test_results.filter(level__gt=1).count() == 1:
                    test_result = test_results.filter(level__gt=1).first()
                    data_point_name = test_result.data_point_name
                    value = test_result.value
                    indicator = MaterialDataPointIndicator.objects.filter(
                        data_point__name=data_point_name,
                        material_test_method__material__material_name=material_test_order.product_no,
                        level=1).first()
                    if indicator:
                        # 误差范围都大于0
                        e1 = DataPointStandardError.objects.filter(
                            lower_value__gte=0, upper_value__gte=0
                        ).filter(lower_value__lte=value-indicator.upper_limit,
                                 upper_value__gte=value-indicator.upper_limit).first()
                        # 误差范围都小于0
                        e2 = DataPointStandardError.objects.filter(
                            lower_value__lte=0, upper_value__lte=0
                        ).filter(lower_value__lte=value-indicator.lower_limit,
                                 upper_value__gte=value-indicator.lower_limit).first()
                        # 误差范围开始值小于0，结束值大于0
                        e3 = DataPointStandardError.objects.filter(
                            lower_value__lte=0, upper_value__gte=0
                        ).filter(lower_value__lte=value - indicator.lower_limit,
                                 upper_value__gte=value - indicator.upper_limit).first()
                        if e1:
                            material_test_order.is_passed = True
                            material_test_order.pass_suggestion = e1.label
                        elif e2:
                            material_test_order.is_passed = True
                            material_test_order.pass_suggestion = e2.label
                        elif e3:
                            material_test_order.is_passed = True
                            material_test_order.pass_suggestion = e3.label
                        if e1 or e2 or e3:
                            test_results.filter(level__gt=1).update(is_passed=True)
                        else:
                            test_results.filter(level__gt=1).update(is_passed=False)
                            material_test_order.is_passed = False
                            material_test_order.pass_suggestion = None
                else:
                    material_test_order.is_passed = False
                    material_test_order.pass_suggestion = None
                    test_results.filter(level__gt=1).update(is_passed=False)
                material_test_order.save()

            lot_no = material_test_order.lot_no
            pfb_obj = PalletFeedbacks.objects.filter(lot_no=lot_no).first()
            if not pfb_obj:
                return
            test_orders = MaterialTestOrder.objects.filter(lot_no=lot_no)

            """
            生成综合判定数据
            """
            # 检测车次
            test_trains_set = set(test_orders.values_list('actual_trains', flat=True))
            # 实际托盘反馈车次
            actual_trains_set = {i for i in range(pfb_obj.begin_trains, pfb_obj.end_trains + 1)}

            common_trains_set = actual_trains_set & test_trains_set
            # 判断托盘反馈车次都存在检测数据
            if not len(actual_trains_set) == len(test_trains_set) == len(common_trains_set):
                return
            # level = 3 if test_orders.filter(is_qualified=False).exists() else 1
            if not test_orders.filter(is_qualified=False).exists():
                level = 1
                deal_suggestion = '合格'
            elif test_orders.filter(is_passed=True).count() == test_orders.filter(is_qualified=False).count() == 1:
                level = 1
                deal_suggestion = test_orders.filter(is_passed=True).first().pass_suggestion
            else:
                level = 3
                deal_suggestion = '不合格'
            deal_result_dict = {
                'level': level,
                'test_result': '合格' if level == 1 else '不合格',
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
