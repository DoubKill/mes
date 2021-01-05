import os
import sys

import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from django.utils import timezone
from datetime import timedelta, datetime
from quality.models import MaterialTestOrder, Lot, Train, Indicator, TestDataPoint, TestResult, \
    Batch, BatchEquip, BatchMonth, BatchDay, BatchClass, BatchProductNo, BatchYear

# for model in BatchYear, BatchMonth, BatchDay, BatchEquip, BatchClass, \
# BatchProductNo, Batch, Lot, Train, Indicator, TestDataPoint, TestResult:
#     model.objects.all().delete()

# 中间表分发数据
for order in MaterialTestOrder.objects.filter(production_factory_date__gte=(timezone.now()-timedelta(days=30)).date()):
    production_factory_date = order.production_factory_date
    batch_year, _ = BatchYear.objects.get_or_create(date=datetime(year=production_factory_date.year,
                                                                  month=1,
                                                                  day=1))
    batch_month, _ = BatchMonth.objects.get_or_create(date=datetime(year=production_factory_date.year,
                                                                    month=production_factory_date.month,
                                                                    day=1))
    batch_day, _ = BatchDay.objects.get_or_create(date=
                                                  datetime(year=production_factory_date.year,
                                                           month=production_factory_date.month,
                                                           day=production_factory_date.day))
    batch_equip, _ = BatchEquip.objects.get_or_create(production_equip_no=
                                                      order.production_equip_no)

    batch_class, _ = BatchClass.objects.get_or_create(production_class=
                                                      order.production_class)

    batch_product_no, _ = BatchProductNo.objects.get_or_create(product_no=
                                                               order.product_no)

    batch, _ = Batch.objects.get_or_create(production_factory_date=order.production_factory_date,
                                           batch_year=batch_year,
                                           batch_month=batch_month,
                                           batch_day=batch_day,
                                           batch_equip=batch_equip,
                                           batch_class=batch_class,
                                           batch_product_no=batch_product_no)

    lot, _ = Lot.objects.get_or_create(lot_no=order.lot_no, batch=batch)
    train, _ = Train.objects.get_or_create(lot=lot, actual_trains=order.actual_trains)
    for test_result in order.order_results.all():
        indicator, _ = Indicator.objects.get_or_create(name=test_result.test_indicator_name)
        test_data_point, _ = TestDataPoint.objects.get_or_create(
            name=test_result.data_point_name,
            indicator=indicator)
        if test_result.data_point_indicator and not test_data_point.data_point_indicator:
            test_data_point.data_point_indicator = test_result.data_point_indicator
            test_data_point.save()
        result, _ = TestResult.objects.get_or_create(train=train,
                                                     point=test_data_point)
        if result.max_times < test_result.test_times:
            result.max_times = test_result.test_times
            # qualified = None if (not test_result.mes_result and not test_result.result) else \
            #     (test_result.mes_result == '一等品' or not test_result.mes_result) and test_result.result == '一等品'

            # qualified = None if (not test_result.mes_result and not test_result.result) else \
            #     (test_result.mes_result == '合格' or test_result.mes_result == '一等品'
            #      or not test_result.mes_result) and (test_result.result == '合格'
            #                                          or test_result.result == '一等品'
            #                                          or not test_result.result)

            result.qualified = (test_result.level == 1)
            result.value = test_result.value
            result.save()
# level 为一是合格
