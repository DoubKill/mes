# -*- coding: UTF-8 -*-
"""
auther:
datetime: 2020/9/29
name:
"""
from django.db.models import Max
from django.db.models.signals import post_save
from django.dispatch import receiver

from production.models import PalletFeedbacks
from quality.models import MaterialTestResult, MaterialTestOrderRaw, UnqualifiedMaterialDealResult, \
    MaterialTestResultRaw, MaterialDataPointIndicatorRaw, MaterialTestMethodRaw, MaterialTestOrder, MaterialDealResult
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
                if MaterialTestResult.objects.filter(id__in=max_result_ids, level__gt=1).exists():
                    material_test_order.is_qualified = False
                else:
                    material_test_order.is_qualified = True
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
            level = 3 if test_orders.filter(is_qualified=False).exists() else 1
            deal_result_dict = {
                'level': level,
                'test_result': '合格' if level == 1 else '不合格',
                'reason': 'reason',
                'status': '待处理',
                'deal_result': '一等品' if level == 1 else '三等品',
                'production_factory_date': pfb_obj.end_time,
                'deal_suggestion': '合格' if level == 1 else '不合格'
            }
            instance = MaterialDealResult.objects.filter(lot_no=lot_no)
            if instance:
                deal_result_dict['update_store_test_flag'] = 4
                instance.update(**deal_result_dict)
            else:
                deal_result_dict['lot_no'] = lot_no
                MaterialDealResult.objects.create(**deal_result_dict)
    except Exception as e:
        logger.error(e)


@receiver(post_save, sender=MaterialTestOrderRaw)
def material_rest_order_raw_post_save(sender, instance=None,
                                      created=False, update_fields=None, **kwargs):
    if not instance.is_qualified:
        max_result_ids = list(instance.order_results_raw.values(
            'test_method', 'data_point').annotate(max_id=Max('id')).values_list('max_id', flat=True))
        reason = ''
        for result in MaterialTestResultRaw.objects.filter(id__in=max_result_ids, level__gt=1):
            material_test_method = MaterialTestMethodRaw.objects.filter(
                material=instance.material,
                test_method=result.test_method).first()
            if material_test_method:
                indicator = MaterialDataPointIndicatorRaw.objects.filter(
                    material_test_method=material_test_method,
                    data_point=result.data_point,
                    level=1
                ).first()
            else:
                indicator = None
            if not indicator:
                reason += '{}缺少评判标准；'.format(result.data_point.name)
            elif result.value > indicator.upper_limit:
                reason += '{}：{}+{}；'.format(result.data_point.name,
                                              indicator.upper_limit,
                                              result.value-indicator.upper_limit)
            elif result.value < indicator.lower_limit:
                reason += '{}：{}-{}；'.format(result.data_point.name,
                                              indicator.lower_limit,
                                              indicator.lower_limit-result.value)
        if not hasattr(instance, 'deal_result'):
            UnqualifiedMaterialDealResult.objects.create(
                material_test_order_raw=instance,
                unqualified_reason=reason)
        else:
            UnqualifiedMaterialDealResult.objects.filter(
                material_test_order_raw=instance).update(unqualified_reason=reason)
    else:
        UnqualifiedMaterialDealResult.objects.filter(material_test_order_raw=instance).delete()