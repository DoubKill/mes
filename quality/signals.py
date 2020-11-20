# -*- coding: UTF-8 -*-
"""
auther:
datetime: 2020/9/29
name:
"""
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
        logger.error(f"信号结束")
    except Exception as e:
        logger.error(f"{synthesize_to_material_deal_result.__doc__}|{e}")
        pass
