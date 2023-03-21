"""
    胶片库存每日8点统计、设备生产能力每日统计
"""


import datetime
import os
import sys

import django
import logging
from django.db.models import Sum, Avg, F

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()
logger = logging.getLogger('sync_log')

from inventory.models import BzFinalMixingRubberInventoryLB, BzFinalMixingRubberInventory, ProductStockDailySummary
from plan.models import SchedulingEquipCapacity
from production.models import TrainsFeedbacks
from mes.common_code import OAvg


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
            items = item['material_no'].strip().split('-')
            stage = items[1]
            product_no = items[2]
            version = items[3]
        except Exception:
            continue
        k = stage+'-'+product_no+'-'+version
        if k not in ret:
            ret[k] = item['s']
        else:
            ret[k] += item['s']
    for key, value in ret.items():
        try:
            items = key.split('-')
            stage = items[0]
            product_no = items[1]
            version = items[2]
        except Exception:
            continue
        ProductStockDailySummary.objects.create(
            factory_date=datetime.datetime.now().date(),
            stock_weight=value,
            stage=stage,
            product_no=product_no,
            version=version
        )


def calculate_product_equip_capacity():
    # SchedulingEquipCapacity.objects.all().delete()
    st = (datetime.datetime.now() - datetime.timedelta(days=30)).date()
    train_feedback = TrainsFeedbacks.objects.filter(
        factory_date__gte=st
    ).values('product_no', 'equip_no').annotate(
        agv_mix_time=OAvg((F('end_time') - F('begin_time'))),
        avg_interval_time=Avg('interval_time'),
        agv_gum_weight=Avg('gum_weight'),
    )
    for item in train_feedback:
        try:
            agv_mix_time = item['agv_mix_time'].total_seconds()
            if agv_mix_time <= 50 or agv_mix_time >= 400:
                continue
        except Exception:
            continue
        avg_interval_time = 15 if not item['avg_interval_time'] else item['avg_interval_time']
        agv_gum_weight = 0 if not item['agv_gum_weight'] else int(item['agv_gum_weight']/100)
        equip_no = item['equip_no']
        product_no = item['product_no']
        if not all([agv_mix_time, equip_no, product_no]):
            continue
        SchedulingEquipCapacity.objects.update_or_create(
            defaults={'avg_mixing_time': agv_mix_time,
                      'avg_interval_time': 10 if avg_interval_time > 30 else avg_interval_time,
                      'avg_rubbery_quantity': agv_gum_weight},
            **{'equip_no': equip_no, 'product_no': product_no})


if __name__ == '__main__':
    product_stock_daily_summary()
    calculate_product_equip_capacity()
