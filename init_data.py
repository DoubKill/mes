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
    {'id': 1, 'code': 'globalcodetype', 'name': '公共代码管理', 'parent_id': None},
    {'id': 2, 'code': 'view_globalcodetype', 'name': '查看', 'parent_id': 1},
    {'id': 3, 'code': 'add_globalcodetype', 'name': '增加', 'parent_id': 1},
    {'id': 4, 'code': 'change_globalcodetype', 'name': '修改', 'parent_id': 1},
    {'id': 5, 'code': 'delete_globalcodetype', 'name': '启用/停用', 'parent_id': 1},

    {'id': 6, 'code': 'groupextension', 'name': '角色管理', 'parent_id': None},
    {'id': 7, 'code': 'view_groupextension', 'name': '查看', 'parent_id': 6},
    {'id': 8, 'code': 'add_groupextension', 'name': '增加', 'parent_id': 6},
    {'id': 9, 'code': 'change_groupextension', 'name': '修改', 'parent_id': 6},
    {'id': 10, 'code': 'delete_groupextension', 'name': '启用/停用', 'parent_id': 6},

    {'id': 11, 'code': 'user', 'name': '用户管理', 'parent_id': None},
    {'id': 12, 'code': 'view_user', 'name': '查看', 'parent_id': 11},
    {'id': 13, 'code': 'add_user', 'name': '增加', 'parent_id': 11},
    {'id': 14, 'code': 'change_user', 'name': '修改', 'parent_id': 11},
    {'id': 15, 'code': 'delete_user', 'name': '启用/停用', 'parent_id': 11},

    {'id': 16, 'code': 'group_user', 'name': '角色别用户管理', 'parent_id': None},
    {'id': 17, 'code': 'view_group_user', 'name': '查看', 'parent_id': 16},
    {'id': 18, 'code': 'change_group_user', 'name': '修改', 'parent_id': 16},

    {'id': 19, 'code': 'workschedule', 'name': '倒班时间管理', 'parent_id': None},
    {'id': 20, 'code': 'view_workschedule', 'name': '查看', 'parent_id': 19},
    {'id': 21, 'code': 'add_workschedule', 'name': '增加', 'parent_id': 19},
    {'id': 22, 'code': 'change_workschedule', 'name': '修改', 'parent_id': 19},
    {'id': 23, 'code': 'delete_workschedule', 'name': '启用/停用', 'parent_id': 19},

    {'id': 24, 'code': 'planschedule', 'name': '工厂排班管理', 'parent_id': None},
    {'id': 25, 'code': 'view_planschedule', 'name': '查看', 'parent_id': 24},
    {'id': 26, 'code': 'add_planschedule', 'name': '增加', 'parent_id': 24},

    {'id': 27, 'code': 'equipcategoryattribute', 'name': '设备种类', 'parent_id': None},
    {'id': 28, 'code': 'view_equipcategoryattribute', 'name': '查看', 'parent_id': 27},
    {'id': 29, 'code': 'add_equipcategoryattribute', 'name': '增加', 'parent_id': 27},
    {'id': 30, 'code': 'change_equipcategoryattribute', 'name': '修改', 'parent_id': 27},
    {'id': 31, 'code': 'delete_equipcategoryattribute', 'name': '启用/停用', 'parent_id': 27},

    {'id': 32, 'code': 'equip', 'name': '设备基础信息', 'parent_id': None},
    {'id': 33, 'code': 'view_equip', 'name': '查看', 'parent_id': 32},
    {'id': 34, 'code': 'add_equip', 'name': '增加', 'parent_id': 32},
    {'id': 35, 'code': 'change_equip', 'name': '修改', 'parent_id': 32},
    {'id': 36, 'code': 'delete_equip', 'name': '启用/停用', 'parent_id': 32},

    {'id': 37, 'code': 'material', 'name': '原材料信息', 'parent_id': None},
    {'id': 38, 'code': 'view_material', 'name': '查看', 'parent_id': 37},
    {'id': 39, 'code': 'add_material', 'name': '增加', 'parent_id': 37},
    {'id': 40, 'code': 'change_material', 'name': '修改', 'parent_id': 37},
    {'id': 41, 'code': 'delete_material', 'name': '启用/停用', 'parent_id': 37},

    {'id': 42, 'code': 'productinfo', 'name': '胶料代码', 'parent_id': None},
    {'id': 43, 'code': 'view_productinfo', 'name': '查看', 'parent_id': 42},
    {'id': 44, 'code': 'add_productinfo', 'name': '增加', 'parent_id': 42},
    {'id': 45, 'code': 'change_productinfo', 'name': '修改', 'parent_id': 42},
    {'id': 46, 'code': 'delete_productinfo', 'name': '启用/停用', 'parent_id': 42},

    {'id': 47, 'code': 'productbatching', 'name': '配方管理', 'parent_id': None},
    {'id': 48, 'code': 'view_productbatching', 'name': '查看', 'parent_id': 47},
    {'id': 49, 'code': 'add_productbatching', 'name': '增加', 'parent_id': 47},
    {'id': 50, 'code': 'change_productbatching', 'name': '修改', 'parent_id': 47},
    {'id': 51, 'code': 'edit_productbatching', 'name': '编辑', 'parent_id': 47},
    {'id': 52, 'code': 'submit_productbatching', 'name': '提交', 'parent_id': 47},
    {'id': 53, 'code': 'check_productbatching', 'name': '校对', 'parent_id': 47},
    {'id': 54, 'code': 'use_productbatching', 'name': '启用', 'parent_id': 47},
    {'id': 55, 'code': 'refuse_productbatching', 'name': '驳回', 'parent_id': 47},
    {'id': 56, 'code': 'abandon_productbatching', 'name': '弃用', 'parent_id': 47},
    {'id': 57, 'code': 'send_productbatching', 'name': '配方下达', 'parent_id': 47},

    {'id': 58, 'code': 'productdayplan', 'name': '计划管理', 'parent_id': None},
    {'id': 59, 'code': 'view_productdayplan', 'name': '查看', 'parent_id': 58},
    {'id': 60, 'code': 'add_productdayplan', 'name': '增加', 'parent_id': 58},
    {'id': 61, 'code': 'change_productdayplan', 'name': '修改', 'parent_id': 58},
    {'id': 62, 'code': 'delete_productdayplan', 'name': '删除', 'parent_id': 58},
    {'id': 77, 'code': 'send_productdayplan', 'name': '计划下达', 'parent_id': 58},

    {'id': 63, 'code': 'materialdemanded', 'name': '原材料需求量', 'parent_id': None},
    {'id': 64, 'code': 'view_materialdemanded', 'name': '查看', 'parent_id': 63},

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

    {'id': 78, 'code': 'test_indicator', 'name': '试验指标管理', 'parent_id': None},
    {'id': 79, 'code': 'view_test_indicator', 'name': '查看', 'parent_id': 78},
    {'id': 80, 'code': 'add_test_indicator', 'name': '新增', 'parent_id': 78},
    {'id': 81, 'code': 'change_test_indicator', 'name': '修改', 'parent_id': 78},

    {'id': 82, 'code': 'test_type', 'name': '试验类型管理', 'parent_id': None},
    {'id': 83, 'code': 'view_test_type', 'name': '查看', 'parent_id': 82},
    {'id': 84, 'code': 'add_test_type', 'name': '新增', 'parent_id': 82},
    {'id': 85, 'code': 'change_test_type', 'name': '修改', 'parent_id': 82},
    {'id': 86, 'code': 'pointAdd_test_type', 'name': '新增类型数据点', 'parent_id': 82},
    {'id': 87, 'code': 'pointChange_test_type', 'name': '修改类型数据点', 'parent_id': 82},

    {'id': 88, 'code': 'test_method', 'name': '试验方法管理', 'parent_id': None},
    {'id': 89, 'code': 'view_test_method', 'name': '查看', 'parent_id': 88},
    {'id': 90, 'code': 'add_test_method', 'name': '新增', 'parent_id': 88},
    {'id': 91, 'code': 'change_test_method', 'name': '修改', 'parent_id': 88},

    {'id': 92, 'code': 'level', 'name': '等级管理', 'parent_id': None},
    {'id': 93, 'code': 'view_level', 'name': '查看', 'parent_id': 92},
    {'id': 94, 'code': 'add_level', 'name': '新增', 'parent_id': 92},
    {'id': 95, 'code': 'delete_level', 'name': '删除', 'parent_id': 92},

    {'id': 96, 'code': 'evaluating', 'name': '判断基准录入', 'parent_id': None},
    {'id': 97, 'code': 'view_evaluating', 'name': '查看', 'parent_id': 96},
    {'id': 98, 'code': 'add_evaluating', 'name': '新增', 'parent_id': 96},
    {'id': 99, 'code': 'change_evaluating', 'name': '修改', 'parent_id': 96},

    {'id': 100, 'code': 'month_passing_rate', 'name': '月合格率统计', 'parent_id': None},
    {'id': 101, 'code': 'view_month_passing_rate', 'name': '查看', 'parent_id': 100},

    {'id': 102, 'code': 'product_month_passing_rate', 'name': '胶料月合格率统计', 'parent_id': None},
    {'id': 103, 'code': 'view_product_month_passing_rate', 'name': '查看', 'parent_id': 102},

    {'id': 104, 'code': 'product_daily_passing_rate', 'name': '胶料日合格率统计', 'parent_id': None},
    {'id': 105, 'code': 'view_product_daily_passing_rate', 'name': '查看', 'parent_id': 104},

    {'id': 106, 'code': 'non-conformity_product', 'name': '不合格品处理', 'parent_id': None},
    {'id': 107, 'code': 'view_non-conformity_product', 'name': '查看', 'parent_id': 106},
    {'id': 108, 'code': 'change_non-conformity_product', 'name': '修改', 'parent_id': 106},

    {'id': 109, 'code': 'deal_suggestion', 'name': '处理意见管理', 'parent_id': None},
    {'id': 110, 'code': 'view_deal_suggestion', 'name': '查看', 'parent_id': 109},
    {'id': 111, 'code': 'add_deal_suggestion', 'name': '新增', 'parent_id': 109},
    {'id': 112, 'code': 'change_deal_suggestion', 'name': '修改', 'parent_id': 109},

    {'id': 113, 'code': 'test_result', 'name': '检测数据录入', 'parent_id': None},
    {'id': 114, 'code': 'view_test_result', 'name': '查看', 'parent_id': 113},
    {'id': 115, 'code': 'add_test_result', 'name': '新增', 'parent_id': 113},

    {'id': 116, 'code': 'result_info', 'name': '快检结果详细信息', 'parent_id': None},
    {'id': 117, 'code': 'view_result_info', 'name': '查看', 'parent_id': 116},

    {'id': 118, 'code': 'deal_result', 'name': '快检信息综合管理', 'parent_id': None},
    {'id': 119, 'code': 'view_deal_result', 'name': '查看', 'parent_id': 118},

    {'id': 120, 'code': 'class_production_summary', 'name': '班次密炼时间汇总', 'parent_id': None},
    {'id': 121, 'code': 'view_class_production_summary', 'name': '查看', 'parent_id': 120},

    {'id': 122, 'code': 'production_time_summary', 'name': '密炼时间占比汇总', 'parent_id': None},
    {'id': 123, 'code': 'view_production_time_summary', 'name': '查看', 'parent_id': 122},

    {'id': 124, 'code': 'single_trains_time_consume', 'name': '单车次时间汇总', 'parent_id': None},
    {'id': 125, 'code': 'view_single_trains_time_consume', 'name': '查看', 'parent_id': 124},

    {'id': 126, 'code': 'product_exchange_consume', 'name': '胶料时间切换汇总', 'parent_id': None},
    {'id': 127, 'code': 'view_product_exchange_consume', 'name': '查看', 'parent_id': 126},

    {'id': 128, 'code': 'warehouse', 'name': '仓库信息管理', 'parent_id': None},
    {'id': 129, 'code': 'view_warehouse', 'name': '查看', 'parent_id': 128},
    {'id': 130, 'code': 'add_warehouse', 'name': '新增', 'parent_id': 128},
    {'id': 131, 'code': 'change_warehouse', 'name': '修改', 'parent_id': 128},
    {'id': 132, 'code': 'delete_warehouse', 'name': '弃用', 'parent_id': 128},

    {'id': 133, 'code': 'warehouse_summary', 'name': '胶料库存汇总', 'parent_id': None},
    {'id': 134, 'code': 'view_warehouse_summary', 'name': '查看', 'parent_id': 133},

    {'id': 135, 'code': 'in_out_history', 'name': '出入库履历', 'parent_id': None},
    {'id': 136, 'code': 'view_in_out_history', 'name': '查看', 'parent_id': 135},

    {'id': 137, 'code': 'goods', 'name': '物料库存管理', 'parent_id': None},
    {'id': 138, 'code': 'view_goods', 'name': '查看', 'parent_id': 137},

    {'id': 139, 'code': 'inventory_plan', 'name': '胶片库出库计划', 'parent_id': None},
    {'id': 140, 'code': 'view_inventory_plan', 'name': '查看', 'parent_id': 139},
    {'id': 141, 'code': 'norman_inventory_plan', 'name': '正常出库', 'parent_id': 139},
    {'id': 142, 'code': 'assign_inventory_plan', 'name': '制定出库', 'parent_id': 139},
    {'id': 143, 'code': 'manual_inventory_plan', 'name': '人工出库', 'parent_id': 139},
    {'id': 144, 'code': 'close_inventory_plan', 'name': '关闭', 'parent_id': 139},
    {'id': 145, 'code': 'change_inventory_plan', 'name': '编辑', 'parent_id': 139},

    {'id': 146, 'code': 'expire_product', 'name': '过期胶料管理', 'parent_id': None},
    {'id': 147, 'code': 'view_expire_product', 'name': '查看', 'parent_id': 146},
    {'id': 148, 'code': 'deal_expire_product', 'name': '处理', 'parent_id': 146},
    {'id': 149, 'code': 'confirm_expire_product', 'name': '确认', 'parent_id': 146},

    {'id': 150, 'code': 'material_attr', 'name': '物料属性管理', 'parent_id': None},
    {'id': 151, 'code': 'view_material_attr', 'name': '查看', 'parent_id': 150},
    {'id': 152, 'code': 'add_material_attr', 'name': '新增', 'parent_id': 150},
    {'id': 153, 'code': 'change_material_attr', 'name': '修改', 'parent_id': 150},
    {'id': 154, 'code': 'delete_material_attr', 'name': '删除', 'parent_id': 150},
]


@atomic()
def init_permissions():
    for item in permission_data:
        Permissions.objects.create(**item)


def main():
    print('开始迁移数据库')
    apps = ('system', 'basics', 'plan', 'production', 'recipe', 'quality', 'inventory')

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
    User.objects.create_superuser('mes', '123456@qq.com', '123456')
    init_permissions()


if __name__ == '__main__':
    main()
