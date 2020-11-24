from django.test import TestCase

# Create your tests here.
'''给测试用的 应为计划履历目前在页面上没新增的功能，数据都是假数据'''
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()
from inventory.models import DispatchPlan, DispatchLog, DispatchLocation


def add_dispatch_log():
    dp_set = DispatchPlan.objects.filter(delete_flag=False)
    for dp_obj in dp_set:
        for i in range(15):
            dl_dict = {'order_no': dp_obj.order_no,
                       'pallet_no': '这个字段不知道咋取',
                       'need_qty': dp_obj.need_qty,
                       'need_weight': dp_obj.need_weight,
                       'dispatch_type': dp_obj.dispatch_type,
                       'material_no': dp_obj.material.material_no,
                       'quality_status': '',  # 这个字段不知道咋取
                       'lot_no': '这个字段不知道咋取',
                       'order_type': dp_obj.order_type,
                       'status': dp_obj.status,
                       'qty': dp_obj.qty if dp_obj.qty else i * i,
                       'weight': i,
                       'dispatch_location': dp_obj.dispatch_location,
                       'dispatch_user': dp_obj.dispatch_user,
                       'fin_time': dp_obj.fin_time
                       }
            DispatchLog.objects.create(**dl_dict)


if __name__ == '__main__':
    add_dispatch_log()
