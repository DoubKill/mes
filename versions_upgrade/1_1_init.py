import os
import sys

import django
from django.db.transaction import atomic

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from production.models import TrainsFeedbacks, PalletFeedbacks
from plan.models import ProductClassesPlan
from system.models import Permissions


@atomic()
def add_permissions():
    """新增页面权限"""
    permission_data = [
        {'id': 78, 'code': 'test_indicator', 'name': '试验指标管理', 'parent_id': None},
        {'id': 79, 'code': 'view_test_indicator', 'name': '查看', 'parent_id': 78},
        {'id': 80, 'code': 'add_test_indicator', 'name': '新增', 'parent_id': 78},
        {'id': 81, 'code': 'change_test_indicator', 'name': '修改', 'parent_id': 78},

        {'id': 82, 'code': 'test_type', 'name': '试验类型管理', 'parent_id': None},
        {'id': 83, 'code': 'view_test_type', 'name': '查看', 'parent_id': 82},
        {'id': 84, 'code': 'add_test_type', 'name': '新增', 'parent_id': 82},
        {'id': 85, 'code': 'change_test_type', 'name': '修改', 'parent_id': 82},
        {'id': 86, 'code': 'point_add_test_type', 'name': '新增类型数据点', 'parent_id': 82},
        {'id': 87, 'code': 'point_change_test_type', 'name': '修改类型数据点', 'parent_id': 82},

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
    for item in permission_data:
        Permissions.objects.create(**item)


def add_factory_date():
    """补充车次反馈和托盘反馈中的factory_date字段"""
    train_feed_backs = TrainsFeedbacks.objects.filter(factory_date__isnull=True)
    for train_feed_back in train_feed_backs:
        plan_classes_uid = train_feed_back.plan_classes_uid
        classes_plan = ProductClassesPlan.objects.filter(plan_classes_uid=plan_classes_uid).first()
        if classes_plan:
            train_feed_back.factory_date = classes_plan.work_schedule_plan.plan_schedule.day_time
            train_feed_back.save()

    pallet_feed_backs = PalletFeedbacks.objects.filter(factory_date__isnull=True)
    for pallet_feed_back in pallet_feed_backs:
        plan_classes_uid = pallet_feed_back.plan_classes_uid
        classes_plan = ProductClassesPlan.objects.filter(plan_classes_uid=plan_classes_uid).first()
        if classes_plan:
            pallet_feed_back.factory_date = classes_plan.work_schedule_plan.plan_schedule.day_time
            pallet_feed_back.save()


if __name__ == '__main__':
    add_permissions()
    add_factory_date()