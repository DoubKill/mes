# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/8/8
name: 
"""
import datetime
import time as t
import os
import random
import uuid
import django



os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from basics.models import PlanSchedule
from plan.models import ProductClassesPlan
from production.models import TrainsFeedbacks, PalletFeedbacks, EquipStatus


def gen_uuid():
    return str(uuid.uuid1())


def run():
    TrainsFeedbacks.objects.all().delete()
    PalletFeedbacks.objects.all().delete()
    EquipStatus.objects.all().delete()
    plan_schedule_set = PlanSchedule.objects.filter(delete_flag=False)
    for plan_schedule in plan_schedule_set:
        if plan_schedule:
            day_plan_set = plan_schedule.ps_day_plan.filter(delete_flag=False)
        else:
            continue
        for day_plan in list(day_plan_set):
            class_plan_set = ProductClassesPlan.objects.filter(product_day_plan=day_plan.id)
            bath_no = 1
            for m in range(1, 26):
                for class_plan in list(class_plan_set):
                    class_name = class_plan.classes_detail.classes.global_name
                    equip_no = day_plan.equip.equip_no
                    product_no = day_plan.product_batching.product_info.product_name
                    plan_trains = class_plan.plan_trains
                    plan_weight = class_plan.weight
                    time_str = '2020-08-01 08:00:00'
                    time = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    if class_name == "早班":
                        time = time
                    elif class_name == "中班":
                        time = time + datetime.timedelta(hours=8)
                    else:
                        time = time + datetime.timedelta(hours=16)
                    train_data = {
                        "plan_classes_uid": class_plan.plan_classes_uid,
                        "plan_trains": plan_trains,
                        "actual_trains": m,
                        "bath_no": bath_no,
                        "equip_no": equip_no,
                        "product_no": product_no,
                        "plan_weight": plan_weight,
                        "actual_weight": m*5,
                        "begin_time": time,
                        "end_time": time + datetime.timedelta(minutes=45),
                        "operation_user": "string-user",
                        "classes": class_name
                    }
                    TrainsFeedbacks.objects.create(**train_data)
                    if m % 5 == 0:
                        pallet_data = {
                                "plan_classes_uid": class_plan.plan_classes_uid,
                                "bath_no": bath_no,
                                "equip_no": equip_no,
                                "product_no": product_no,
                                "plan_weight": plan_weight*5,
                                "actual_weight": m*5*5,
                                "begin_time": time,
                                "end_time": time + datetime.timedelta(minutes=45*5),
                                "operation_user": "string-user",
                                "begin_trains": 1,
                                "end_trains": m,
                                "pallet_no": f"{bath_no}|test",
                                "barcode": "KJDL:LKYDFJM<NLIIRD",
                                "classes": class_name
                            }
                        bath_no += 1
                        PalletFeedbacks.objects.create(**pallet_data)
                    for x in range(5):
                        equip_status_data = {
                            "plan_classes_uid": class_plan.plan_classes_uid,
                            "equip_no": equip_no,
                            "temperature": random.randint(300,700),
                            "rpm": random.randint(500,2000),
                            "energy": random.randint(50,500),
                            "power": random.randint(50,500),
                            "pressure": random.randint(80,360),
                            "status": "running",
                            "current_trains": m,
                        }
                        EquipStatus.objects.create(**equip_status_data)
                        t.sleep(1)


if __name__ == '__main__':
    run()
