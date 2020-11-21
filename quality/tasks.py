import os
import sys

import django


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from django.utils import timezone
from datetime import timedelta, datetime
from basics.models import PlanSchedule, WorkSchedulePlan
from quality.models import MaterialTestOrder, \
    MaterialTestResult, Lot, Train, \
    Indicator, TestDataPoint, TestResult, Batch, BatchEquip, BatchMonth, BatchDay, BatchClass, BatchProductNo
from django.db.models import Q, F
from django.db.models import Count
from django.db.models import FloatField


# 中间表分发数据
for order in MaterialTestOrder.objects.all():
    production_factory_date = order.production_factory_date
    batch_month, _ = BatchMonth.objects.get_or_create(date=
                                                      datetime(year=production_factory_date.year,
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
            indicator=indicator,
            data_point_indicator=test_result.data_point_indicator
        )
        result, _ = TestResult.objects.get_or_create(train=train,
                                                     point=test_data_point)
        if result.max_times < test_result.test_times:
            result.max_times = test_result.test_times
            qualified = None if (not test_result.mes_result and not test_result.result) else \
                (test_result.mes_result == '一等品' or not test_result.mes_result) and test_result.result == '一等品'
            result.qualified = qualified
            result.value = test_result.value
            result.save()
#
# lb_train_count = Count('lot__train', filter=Q(lot__train__testresult__point__indicator__name='流变'),
#                        output_field=FloatField())
#
# lb_test_pass_count = Count('lot__train', filter=Q(lot__train__testresult__point__indicator__name='流变',
#                                                   lot__train__testresult__qualified=True),
#                            output_field=FloatField())
#
#
# batches = Batch.objects.annotate(lb_train_count=lb_train_count)\
#     .annotate(lb_test_pass_count=lb_test_pass_count)\
#
# for batch in batches:
#     print(batch.id, batch.lb_test_pass_count / batch.lb_train_count)

# for point in TestDataPoint.objects.all():
#     point.testresult_set
# TestDataPoint.objects.annotate(upper_limit_count=Count('testresult__train', filter=
#                                      Q(testresult__qualified=False,
#                                        testresult__value__gt=F('data_point_indicator__upper_limit'))))
#
# for batch_product_no in BatchProductNo.objects.all():
#     # BatchDay.objects.filter(batch__batch_product_no=batch_product_no)
#     BatchDay.objects.annotate(Count('batch__lot__train',
#                 filter=Q(batch__batch_product_no=batch_product_no)))\
#         .annotate(Count('batch__lot__train',
#                 filter=Q(batch__batch_product_no=batch_product_no,
#                          batch__lot__train__testresult__qualified=True)))\
#         .filter(batch__batch_product_no=batch_product_no)