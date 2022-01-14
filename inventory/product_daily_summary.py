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
    t1 = list(BzFinalMixingRubberInventoryLB.objects.using('lb').filter(
        store_name='炼胶库').values('material_no').annotate(s=Sum('total_weight')))
    t2 = list(BzFinalMixingRubberInventory.objects.using('bz').values(
        'material_no').annotate(s=Sum('total_weight')))
    t1.extend(t2)
    ret = {}
    for item in t1:
        if item['material_no'] not in ret:
            ret[item['material_no']] = item['s']
        else:
            ret[item['material_no']] += item['s']
    for key, value in ret.items():
        ProductStockDailySummary.objects.create(
            factory_date=datetime.datetime.now().date(),
            product_no=key,
            stock_weight=value
        )


if __name__ == '__main__':
    product_stock_daily_summary()
