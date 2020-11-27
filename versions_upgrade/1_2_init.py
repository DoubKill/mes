import os
import sys

import django
from django.db.transaction import atomic

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from system.models import Permissions


@atomic()
def add_permissions():
    """新增页面权限"""
    permission_data = [
        {'id': 155, 'code': 'LB_inventory_plan', 'name': '帘布库出库计划', 'parent_id': None},
        {'id': 156, 'code': 'view_LB_inventory_plan', 'name': '查看', 'parent_id': 155},
        {'id': 157, 'code': 'norman_LB_inventory_plan', 'name': '正常出库', 'parent_id': 155},
        {'id': 158, 'code': 'assign_LB_inventory_plan', 'name': '指定出库', 'parent_id': 155},
        {'id': 159, 'code': 'manual_LB_inventory_plan', 'name': '人工出库', 'parent_id': 155},
        {'id': 160, 'code': 'close_LB_inventory_plan', 'name': '关闭', 'parent_id': 155},
        {'id': 161, 'code': 'change_LB_inventory_plan', 'name': '编辑', 'parent_id': 155},
        {'id': 162, 'code': 'print_deal_result', 'name': '打印', 'parent_id': 118},
        {'id': 163, 'code': 'export_result_info', 'name': '导出', 'parent_id': 116},
         ]
    for item in permission_data:
        Permissions.objects.get_or_create(**item)


if __name__ == '__main__':
    add_permissions()
