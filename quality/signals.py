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
from quality.models import MaterialTestResult
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
