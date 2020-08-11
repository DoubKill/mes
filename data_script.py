# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/8/8
name: 
"""
import datetime
import os
import uuid
import django



os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from basics.models import PlanSchedule
from plan.models import ProductClassesPlan
from production.models import TrainsFeedbacks


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
    plan_schedule_set = PlanSchedule.objects.filter(delete_flag=False)
    # day_plan_id_list = plan_schedule.ps_day_plan.filter(delete_flag=False).values_list("id", flat=True)
    day_plan_set = []
    for plan_schedule in plan_schedule_set:
        if plan_schedule:
            day_plan_set = plan_schedule.ps_day_plan.filter(delete_flag=False)
        else:
            continue
        for day_plan in list(day_plan_set):
            instance = {}
            plan_trains = 0
            actual_trains = 0
            class_plan_set = ProductClassesPlan.objects.filter(product_day_plan=day_plan.id)
            n = 0
            for class_plan in list(class_plan_set):
                n += 1
                data = {
                    "plan_classes_uid": class_plan.plan_classes_uid,
                    "plan_trains": class_plan.plan_trains,
                    "actual_trains": n,
                    "bath_no": 0,
                    "equip_no": day_plan.equip.equip_no,
                    "product_no": "test-pro-1",
                    "plan_weight": class_plan.weight,
                    "actual_weight": n * 100,
                    "begin_time": datetime.datetime.now(),
                    "end_time": datetime.datetime.now(),
                    "operation_user": "string-user",
                    "classes": class_plan.classes_detail.classes.global_name
                }
                TrainsFeedbacks.objects.create(**data)


if __name__ == '__main__':
    run()
