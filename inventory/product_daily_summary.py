"""
    胶片库存每日8点统计
"""


import datetime
import os
import sys

import django
import logging

from django.db.models import Sum


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()
logger = logging.getLogger('sync_log')

from inventory.models import BzFinalMixingRubberInventoryLB, BzFinalMixingRubberInventory, ProductStockDailySummary


def product_stock_daily_summary():
    if ProductStockDailySummary.objects.filter(factory_date=datetime.datetime.now().date()).exists():
        return
    t1 = list(BzFinalMixingRubberInventoryLB.objects.using('lb').filter(
        store_name='炼胶库').values('material_no').annotate(s=Sum('total_weight')))
    t2 = list(BzFinalMixingRubberInventory.objects.using('bz').values(
        'material_no').annotate(s=Sum('total_weight')))
    t1.extend(t2)
    ret = {}
    for item in t1:
        try:
            items = item['material_no'].split('-')
            stage = items[1]
            product_no = items[2]
        except Exception:
            continue
        k = stage+'-'+product_no
        if k not in ret:
            ret[k] = item['s']
        else:
            ret[k] += item['s']
    for key, value in ret.items():
        try:
            items = key.split('-')
            stage = items[0]
            product_no = items[1]
        except Exception:
            continue
        ProductStockDailySummary.objects.create(
            factory_date=datetime.datetime.now().date(),
            stock_weight=value,
            stage=stage,
            product_no=product_no
        )


if __name__ == '__main__':
    product_stock_daily_summary()
