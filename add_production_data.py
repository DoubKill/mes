# coding: utf-8
"""
    说明：添加生产数据、快检数据，可无限次数跑
"""

import datetime
import os
import random
import uuid

from django.db.models import Max
import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from plan.models import ProductClassesPlan
from production.models import PalletFeedbacks, TrainsFeedbacks
from quality.models import MaterialTestOrder, MaterialTestResult, MaterialTestMethod, MaterialDataPointIndicator


def main():
    for pcp in ProductClassesPlan.objects.filter(delete_flag=False, status__in=('已保存', '已下达', '运行中')):
        max_train = TrainsFeedbacks.objects.filter(
            plan_classes_uid=pcp.plan_classes_uid).aggregate(max_train=Max('actual_trains'))['max_train']
        if not max_train:
            st = 1
        else:
            st = max_train + 1
        now = datetime.datetime.now()
        b_day = datetime.timedelta(seconds=-random.randint(10, 100))
        e_day = datetime.timedelta(seconds=random.randint(10, 100))
        begin_time = now + b_day
        end_time = now + e_day
        if st <= pcp.plan_trains:
            TrainsFeedbacks.objects.create(
                plan_classes_uid=pcp.plan_classes_uid,
                plan_trains=pcp.plan_trains,
                actual_trains=st,
                bath_no='111',
                equip_no=pcp.equip.equip_no,
                product_no=pcp.product_batching.stage_product_batch_no,
                plan_weight=1000,
                actual_weight=1000,
                begin_time=begin_time,
                end_time=end_time,
                operation_user='admin',
                classes=pcp.work_schedule_plan.classes.global_name,
                product_time=now,
                factory_date=pcp.work_schedule_plan.plan_schedule.day_time)
            if st % 2 == 0:
                pf = PalletFeedbacks.objects.create(
                    plan_classes_uid=pcp.plan_classes_uid,
                    bath_no='111',
                    equip_no=pcp.equip.equip_no,
                    product_no=pcp.product_batching.stage_product_batch_no,
                    plan_weight=1000,
                    actual_weight=1000,
                    begin_time=begin_time,
                    end_time=end_time,
                    operation_user='admin',
                    begin_trains=st - 1,
                    end_trains=st,
                    pallet_no=''.join(random.sample(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'], 7)),
                    classes=pcp.work_schedule_plan.classes.global_name,
                    product_time=datetime.datetime.now(),
                    factory_date=pcp.work_schedule_plan.plan_schedule.day_time,
                    lot_no='AAJ1{}{}'.format(pcp.equip.equip_no, datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')),
                )
                # for train in [st - 1, st]:
                #     mto = MaterialTestOrder.objects.create(
                #         lot_no=pf.lot_no,
                #         material_test_order_uid=uuid.uuid1(),
                #         actual_trains=train,
                #         product_no=pcp.product_batching.stage_product_batch_no,
                #         plan_classes_uid=pcp.plan_classes_uid,
                #         production_class=pcp.work_schedule_plan.classes.global_name,
                #         production_group=pcp.work_schedule_plan.group.global_name,
                #         production_equip_no=pcp.equip.equip_no,
                #         production_factory_date=pcp.work_schedule_plan.plan_schedule.day_time)
                #     for i in range(random.randint(1, 3)):
                #         level = random.choice([1, 1, 1, 1, 2, 1, 1, 1, 1])
                #         value = random.randint(1, 100) if level == 1 else random.randint(101, 200)
                #         data = {
                #             '门尼': {'门尼粘度': {'160*3': ['ML1+4']}},
                #             '流变': {'标准硫化': {'250*4': ['MH', 'TC10', 'TC50', 'TC90']}},
                #             '比重': {'比重': {'360*5': ['比重值']}},
                #             '硬度': {'硬度': {'480*6': ['硬度值']}}}
                #         for indicator_name, data2 in data.items():
                #             for type_name, data3 in data2.items():
                #                 for method_name, data_point_names in data3.items():
                #                     for data_point_name in data_point_names:
                #                         item = dict()
                #                         item['value'] = value
                #                         item['material_test_order'] = mto
                #                         item['test_factory_date'] = datetime.datetime.now()
                #                         item['test_times'] = i + 1
                #                         item['data_point_name'] = data_point_name
                #                         item['test_method_name'] = method_name
                #                         item['test_indicator_name'] = indicator_name
                #                         material_test_method = MaterialTestMethod.objects.filter(
                #                             material__material_no=pcp.product_batching.stage_product_batch_no,
                #                             test_method__name=method_name,
                #                             test_method__test_type__test_indicator__name=indicator_name,
                #                             data_point__test_type__test_indicator__name=indicator_name,
                #                             data_point__name=data_point_name
                #                         ).first()
                #                         if material_test_method:
                #                             indicator = MaterialDataPointIndicator.objects.filter(
                #                                 material_test_method=material_test_method,
                #                                 data_point__name=data_point_name,
                #                                 data_point__test_type__test_indicator__name=indicator_name,
                #                                 upper_limit__gte=value,
                #                                 lower_limit__lte=value).first()
                #                             if indicator:
                #                                 item['mes_result'] = indicator.result
                #                                 item['data_point_indicator'] = indicator
                #                                 item['level'] = indicator.level
                #                             else:
                #                                 item['mes_result'] = '三等品'
                #                                 item['level'] = 2
                #                         else:
                #                             item['mes_result'] = '三等品'
                #                             item['level'] = 2
                #                         MaterialTestResult.objects.create(**item)
        else:
            pcp.status = '完成'
            pcp.save()


if __name__ == '__main__':
    # test
    # test
    main()
