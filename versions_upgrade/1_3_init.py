
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
    """新增页面权限（收发货管理、不合格处置单管理）"""
    permission_data = [
        {'id': 164, 'code': 'delivery_plan', 'name': '发货计划管理', 'parent_id': None},
        {'id': 165, 'code': 'view_delivery_plan', 'name': '查看', 'parent_id': 164},
        {'id': 166, 'code': 'add_delivery_plan', 'name': '新增', 'parent_id': 164},
        {'id': 167, 'code': 'change_delivery_plan', 'name': '修改', 'parent_id': 164},
        {'id': 168, 'code': 'delete_delivery_plan', 'name': '关闭', 'parent_id': 164},

        {'id': 169, 'code': 'delivery_history', 'name': '发货履历管理', 'parent_id': None},
        {'id': 170, 'code': 'view_delivery_history', 'name': '查看', 'parent_id': 169},

        {'id': 171, 'code': 'delivery_address', 'name': '发货地管理', 'parent_id': None},
        {'id': 172, 'code': 'view_delivery_address', 'name': '查看', 'parent_id': 171},
        {'id': 173, 'code': 'add_delivery_address', 'name': '新增', 'parent_id': 171},
        {'id': 174, 'code': 'change_delivery_address', 'name': '修改', 'parent_id': 171},
        {'id': 175, 'code': 'delete_delivery_address', 'name': '启用/停用', 'parent_id': 171},

        {'id': 176, 'code': 'unqualified_trains', 'name': '不合格处置单生成', 'parent_id': None},
        {'id': 177, 'code': 'view_unqualified_trains', 'name': '查看', 'parent_id': 176},
        {'id': 178, 'code': 'add_unqualified_trains', 'name': '新增处置单', 'parent_id': 176},

        {'id': 179, 'code': 'unqualified_order', 'name': '不合格处置单管理', 'parent_id': None},
        {'id': 180, 'code': 'view_unqualified_order', 'name': '查看', 'parent_id': 179},
        {'id': 181, 'code': 'reason_unqualified_trains', 'name': '原因编辑', 'parent_id': 179},
        {'id': 182, 'code': 'tech_unqualified_trains', 'name': '技术编辑', 'parent_id': 179},
        {'id': 183, 'code': 'check_unqualified_trains', 'name': '检查编辑', 'parent_id': 179},
        {'id': 184, 'code': 'export_unqualified_trains', 'name': '导出', 'parent_id': 179},

    ]
    for item in permission_data:
        Permissions.objects.get_or_create(**item)


if __name__ == '__main__':
    add_permissions()
