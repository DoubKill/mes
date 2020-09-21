# coding: utf-8
"""项目初始化脚本"""

import os

import django
import shutil

from django.db.transaction import atomic

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from system.models import User, Permissions

permission_data = [
        {'id': 1, 'code': 'global_types', 'name': '公共代码管理', 'parent_id': None},
        {'id': 2, 'code': 'view_global_types', 'name': '查看', 'parent_id': 1},
        {'id': 3, 'code': 'add_global_types', 'name': '增加', 'parent_id': 1},
        {'id': 4, 'code': 'change_global_types', 'name': '修改', 'parent_id': 1},
        {'id': 5, 'code': 'delete_global_types', 'name': '启用/停用', 'parent_id': 1},

        {'id': 6, 'code': 'groups', 'name': '角色管理', 'parent_id': None},
        {'id': 7, 'code': 'view_groups', 'name': '查看', 'parent_id': 6},
        {'id': 8, 'code': 'add_groups', 'name': '增加', 'parent_id': 6},
        {'id': 9, 'code': 'change_groups', 'name': '修改', 'parent_id': 6},
        {'id': 10, 'code': 'delete_groups', 'name': '启用/停用', 'parent_id': 6},

        {'id': 11, 'code': 'users', 'name': '用户管理', 'parent_id': None},
        {'id': 12, 'code': 'view_users', 'name': '查看', 'parent_id': 11},
        {'id': 13, 'code': 'add_users', 'name': '增加', 'parent_id': 11},
        {'id': 14, 'code': 'change_users', 'name': '修改', 'parent_id': 11},
        {'id': 15, 'code': 'delete_users', 'name': '启用/停用', 'parent_id': 11},

        {'id': 16, 'code': 'group-users', 'name': '角色别用户管理', 'parent_id': None},
        {'id': 17, 'code': 'view_group-users', 'name': '查看', 'parent_id': 16},
        {'id': 18, 'code': 'add_group-users', 'name': '修改', 'parent_id': 16},

        {'id': 19, 'code': 'work_schedules', 'name': '倒班时间管理', 'parent_id': None},
        {'id': 20, 'code': 'view_work_schedules', 'name': '查看', 'parent_id': 19},
        {'id': 21, 'code': 'add_work_schedules', 'name': '增加', 'parent_id': 19},
        {'id': 22, 'code': 'change_work_schedules', 'name': '修改', 'parent_id': 19},
        {'id': 23, 'code': 'delete_work_schedules', 'name': '启用/停用', 'parent_id': 19},

        {'id': 24, 'code': 'plan_schedules', 'name': '工厂排班管理', 'parent_id': None},
        {'id': 25, 'code': 'view_plan_schedules', 'name': '查看', 'parent_id': 24},
        {'id': 26, 'code': 'add_plan_schedules', 'name': '增加', 'parent_id': 24},

        {'id': 27, 'code': 'equip_attrs', 'name': '设备种类', 'parent_id': None},
        {'id': 28, 'code': 'view_equip_attrs', 'name': '查看', 'parent_id': 27},
        {'id': 29, 'code': 'add_equip_attrs', 'name': '增加', 'parent_id': 27},
        {'id': 30, 'code': 'change_equip_attrs', 'name': '修改', 'parent_id': 27},
        {'id': 31, 'code': 'delete_equip_attrs', 'name': '启用/停用', 'parent_id': 27},

        {'id': 32, 'code': 'equips', 'name': '设备基础信息', 'parent_id': None},
        {'id': 33, 'code': 'view_equips', 'name': '查看', 'parent_id': 32},
        {'id': 34, 'code': 'add_equips', 'name': '增加', 'parent_id': 32},
        {'id': 35, 'code': 'change_equips', 'name': '修改', 'parent_id': 32},
        {'id': 36, 'code': 'delete_equips', 'name': '启用/停用', 'parent_id': 32},

        {'id': 37, 'code': 'materials', 'name': '原材料信息', 'parent_id': None},
        {'id': 38, 'code': 'view_materials', 'name': '查看', 'parent_id': 37},
        {'id': 39, 'code': 'add_materials', 'name': '增加', 'parent_id': 37},
        {'id': 40, 'code': 'change_materials', 'name': '修改', 'parent_id': 37},
        {'id': 41, 'code': 'delete_materials', 'name': '启用/停用', 'parent_id': 37},

        {'id': 42, 'code': 'products', 'name': '胶料代码', 'parent_id': None},
        {'id': 43, 'code': 'view_products', 'name': '查看', 'parent_id': 42},
        {'id': 44, 'code': 'add_products', 'name': '增加', 'parent_id': 42},
        {'id': 45, 'code': 'change_products', 'name': '修改', 'parent_id': 42},
        {'id': 46, 'code': 'delete_products', 'name': '启用/停用', 'parent_id': 42},

        {'id': 47, 'code': 'recipes', 'name': '配方管理', 'parent_id': None},
        {'id': 48, 'code': 'view_recipes', 'name': '查看', 'parent_id': 47},
        {'id': 49, 'code': 'add_recipes', 'name': '增加', 'parent_id': 47},
        {'id': 50, 'code': 'change_recipes', 'name': '修改', 'parent_id': 47},
        {'id': 51, 'code': 'edit_recipes', 'name': '编辑', 'parent_id': 47},
        {'id': 52, 'code': 'submit_recipes', 'name': '提交', 'parent_id': 47},
        {'id': 53, 'code': 'check_recipes', 'name': '校对', 'parent_id': 47},
        {'id': 54, 'code': 'use_recipes', 'name': '启用', 'parent_id': 47},
        {'id': 55, 'code': 'refuse_recipes', 'name': '驳回', 'parent_id': 47},
        {'id': 56, 'code': 'abandon_recipes', 'name': '弃用', 'parent_id': 47},
        {'id': 57, 'code': 'send_recipes', 'name': '发送至上辅机', 'parent_id': 47},

        {'id': 58, 'code': 'plans', 'name': '计划管理', 'parent_id': None},
        {'id': 59, 'code': 'view_plans', 'name': '查看', 'parent_id': 58},
        {'id': 60, 'code': 'add_plans', 'name': '增加', 'parent_id': 58},
        {'id': 61, 'code': 'change_plans', 'name': '修改', 'parent_id': 58},
        {'id': 62, 'code': 'delete_plans', 'name': '删除', 'parent_id': 58},

        {'id': 63, 'code': 'material_demanded', 'name': '原材料需求量', 'parent_id': None},
        {'id': 64, 'code': 'view_material_demanded', 'name': '查看', 'parent_id': 63},

        {'id': 65, 'code': 'product_actual', 'name': '密炼实绩', 'parent_id': None},
        {'id': 66, 'code': 'view_product_actual', 'name': '查看', 'parent_id': 65},

        {'id': 67, 'code': 'plan_reality', 'name': '密炼机台别计划对比', 'parent_id': None},
        {'id': 68, 'code': 'view_plan_reality', 'name': '查看', 'parent_id': 67},

        {'id': 69, 'code': 'product_record', 'name': '密炼生产履历', 'parent_id': None},
        {'id': 70, 'code': 'view_product_record', 'name': '查看', 'parent_id': 69},

        {'id': 71, 'code': 'pallet_feedback', 'name': '日别胶料收皮管理', 'parent_id': None},
        {'id': 72, 'code': 'view_pallet_feedback', 'name': '查看', 'parent_id': 71},

        {'id': 73, 'code': 'material_inventory', 'name': '原材料库存', 'parent_id': None},
        {'id': 74, 'code': 'view_material_inventory', 'name': '查看', 'parent_id': 73},

        {'id': 75, 'code': 'product_inventory', 'name': '胶料库存', 'parent_id': None},
        {'id': 76, 'code': 'view_product_inventory', 'name': '查看', 'parent_id': 75},
]


@atomic()
def init_permissions():
    for item in permission_data:
        Permissions.objects.create(**item)


def main():
    print('开始迁移数据库')
    apps = ('system', 'basics', 'plan', 'production', 'recipe')

    for app in apps:
        try:
            shutil.rmtree(f"{app}/migrations")
        except Exception:
            pass

    os.system(
        'python manage.py makemigrations {}'.format(
            ' '.join(apps)
        ))
    os.system('python manage.py migrate')

    print('创建超级管理员...')
    User.objects.create_superuser('18888888888', '123456@qq.com', '123456')
    init_permissions()


if __name__ == '__main__':
    main()
