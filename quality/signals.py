# -*- coding: UTF-8 -*-
"""
auther:
datetime: 2020/9/29
name:
"""
from django.db.models import Max
from django.db.models.signals import post_save
from django.dispatch import receiver

from quality.deal_result import synthesize_to_material_deal_result
from quality.models import MaterialTestResult, MaterialTestOrderRaw, UnqualifiedMaterialDealResult, \
    MaterialTestResultRaw, MaterialDataPointIndicatorRaw, MaterialTestMethodRaw
import logging

logger = logging.getLogger('send_log')


@receiver(post_save, sender=MaterialTestResult)
def batching_post_save(sender, instance=None, created=False, update_fields=None, **kwargs):
    # 等级综合判定
    try:
        logger.error(f"进入信号")
        synthesize_to_material_deal_result(instance.material_test_order.lot_no)
        # 判断某一车是否合格
        if created:
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

    except Exception as e:
        logger.error(f"{synthesize_to_material_deal_result.__doc__}|{e}")
        pass


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