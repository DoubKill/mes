# -*- coding: UTF-8 -*-
"""
auther: liwei
datetime: 2020/8/8
name: 生产数据模拟脚本
"""
import datetime
import time as t
import os
import random
import uuid
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from plan.models import ProductClassesPlan, ProductDayPlan
from production.models import TrainsFeedbacks, PalletFeedbacks, EquipStatus
import random

pallet_count = 5


class ProductDataEmulator():

    def __init__(self, *args, **kwargs):
        self.plan_train = kwargs.get("plan_train")

    @staticmethod
    def init_datatable(self):
        pass


def run():
    # TrainsFeedbacks.objects.all().delete()
    # PalletFeedbacks.objects.all().delete()
    # EquipStatus.objects.all().delete()

    # plan_schedule_set = PlanSchedule.objects.filter(delete_flag=False)
    # for plan_schedule in plan_schedule_set:
    #     if plan_schedule:
    #         day_plan_set = plan_schedule.ps_day_plan.filter(delete_flag=False)
    #     else:
    #         continue
    day_plan_set = ProductDayPlan.objects.filter(delete_flag=False)
    for day_plan in list(day_plan_set):
        class_plan_set = ProductClassesPlan.objects.filter(product_day_plan=day_plan.id)
        bath_no = 1
        for class_plan in list(class_plan_set):
            plan_trains = class_plan.plan_trains
            start_time = class_plan.work_schedule_plan.start_time
            for m in range(1, int(plan_trains) + 1):
                class_name = class_plan.work_schedule_plan.classes.global_name
                equip_no = day_plan.equip.equip_no
                product_no = day_plan.product_batching.stage_product_batch_no
                plan_weight = class_plan.weight
                # time_str = '2020-08-01 08:00:00'
                # time = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                # if class_name == "早班":
                #     time = time
                # elif class_name == "中班":
                #     time = time + datetime.timedelta(hours=8)
                # else:
                #     time = time + datetime.timedelta(hours=16)
                end_time = start_time + datetime.timedelta(seconds=150)
                train_data = {
                    "plan_classes_uid": class_plan.plan_classes_uid,
                    "plan_trains": plan_trains,
                    "actual_trains": m,
                    "bath_no": bath_no,
                    "equip_no": equip_no,
                    "product_no": product_no,
                    "plan_weight": plan_weight,
                    "actual_weight": m * 5,
                    "begin_time": start_time,
                    "end_time": end_time,
                    "operation_user": "string-user",
                    "classes": class_name,
                    "product_time": end_time,
                }
                start_time = end_time
                TrainsFeedbacks.objects.create(**train_data)
                if m % pallet_count == 0:
                    end_time = start_time + datetime.timedelta(seconds=150 * 5)
                    pallet_data = {
                        "plan_classes_uid": class_plan.plan_classes_uid,
                        "bath_no": bath_no,
                        "equip_no": equip_no,
                        "product_no": product_no,
                        "plan_weight": plan_weight * 5,
                        "actual_weight": m * 5 * 5,
                        "begin_time": start_time,
                        "end_time": end_time,
                        "operation_user": "string-user",
                        "begin_trains": m - (pallet_count - 1),
                        "end_trains": m,
                        "pallet_no": f"{bath_no}|test",
                        # "barcode": "KJDL:LKYDFJM<NLIIRD",
                        "classes": class_name,
                        "lot_no": str(random.randint(999999999, 99999999999999999)) + ''.join(random.sample(
                            'zyxwvutsrqponmlkjihgfedcba', 5)),  # 这个字段之前是没有的 但是表里有 快检那边会用的到 所以给他加上了 随机生成的 数字加字母随机生成字符串
                        "product_time": end_time,
                        "factory_date": datetime.datetime.now().strftime('%Y-%m-%d')
                    }
                    start_time = end_time
                    bath_no += 1
                    PalletFeedbacks.objects.create(**pallet_data)
                # for x in range(5):
                #     equip_status_data = {
                #         "plan_classes_uid": class_plan.plan_classes_uid,
                #         "equip_no": equip_no,
                #         "temperature": random.randint(300, 700),
                #         "rpm": random.randint(500, 2000),
                #         "energy": random.randint(50, 500),
                #         "power": random.randint(50, 500),
                #         "pressure": random.randint(80, 360),
                #         "status": "running",
                #         "current_trains": m,
                #         "product_time": end_time + datetime.timedelta(seconds=1),
                #     }
                #     EquipStatus.objects.create(**equip_status_data)
                #     # t.sleep(1)


if __name__ == '__main__':
    run()
