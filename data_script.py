# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/8/8
name: 
"""
import uuid

import requests


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
    print("--------start---------")
    print("--------end-----------")


if __name__ == '__main__':
    run()
