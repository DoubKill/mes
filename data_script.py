# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/8/8
name: 
"""
import datetime
import os
import random
import uuid
import django



os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from basics.models import PlanSchedule
from plan.models import ProductClassesPlan
from production.models import TrainsFeedbacks, PalletFeedbacks, EquipStatus


class ScriptConfigInit(object):

    def __init__(self):
        self.equip_status_data = {
            "plan_classes_uid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "equip_no": "string",
            "temperature": "string",
            "rpm": "string",
            "energy": "string",
            "power": "string",
            "pressure": "string",
            "status": "string"
        }

        self.expend_materials_data = {
            "plan_classes_uid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "equip_no": "string",
            "product_no": "string",
            "trains": 0,
            "plan_weight": "string",
            "actual_weight": "string",
            "masterial_no": "string"
        }

        self.operation_logs_data = {
            "equip_no": "string",
            "content": "string"
        }

        self.pallet_feedbacks = {
            "plan_classes_uid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "bath_no": 0,
            "equip_no": "string",
            "product_no": "string",
            "plan_weight": "string",
            "actual_weight": "string",
            "begin_time": "2020-08-08T06:27:04.455Z",
            "end_time": "2020-08-08T06:27:04.455Z",
            "operation_user": "string",
            "begin_trains": 0,
            "end_trains": 0,
            "pallet_no": "string",
            "barcode": "string"
        }

        self.plan_status = {
            "plan_classes_uid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "equip_no": "string",
            "product_no": "string",
            "status": "string",
            "operation_user": "string",
            "energy": "string"
        }

        self.quality_control = {
            "barcode": "string",
            "qu_content": "string"
        }

        self.trains_feedbacks = {
            "plan_classes_uid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "plan_trains": 0,
            "actual_trains": 0,
            "bath_no": 0,
            "equip_no": "string",
            "product_no": "string",
            "plan_weight": "string",
            "actual_weight": "string",
            "begin_time": "2020-08-08T06:31:29.213Z",
            "end_time": "2020-08-08T06:31:29.213Z",
            "operation_user": "string"
        }


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
                                "barcode": "KJDL:LKYDFJM<NLIIRD"
                            }
                        bath_no += 1
                        PalletFeedbacks.objects.create(**pallet_data)
                    for x in range(20):
                        equip_status_data = {
                            "plan_classes_uid": class_plan.plan_classes_uid,
                            "equip_no": equip_no,
                            "temperature": random.randint(300,700),
                            "rpm": random.randint(500,2000),
                            "energy": random.randint(50,500),
                            "power": random.randint(50,500),
                            "pressure": random.randint(80,360),
                            "status": "running"
                        }
                        EquipStatus.objects.create(**equip_status_data)


if __name__ == '__main__':
    run()
