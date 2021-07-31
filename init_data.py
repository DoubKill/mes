# coding: utf-8
"""项目初始化脚本"""

import os

import django
import shutil

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from django.db.transaction import atomic
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

    {'id': 73, 'code': 'material_inventory', 'name': '原料库存', 'parent_id': None},
    {'id': 74, 'code': 'view_material_inventory', 'name': '查看', 'parent_id': 73},

    {'id': 75, 'code': 'product_inventory', 'name': '混炼胶库存', 'parent_id': None},
    {'id': 76, 'code': 'view_product_inventory', 'name': '查看', 'parent_id': 75},

    {'id': 78, 'code': 'test_indicator', 'name': '胶料试验指标管理', 'parent_id': None},
    {'id': 79, 'code': 'view_test_indicator', 'name': '查看', 'parent_id': 78},
    {'id': 80, 'code': 'add_test_indicator', 'name': '新增', 'parent_id': 78},
    {'id': 81, 'code': 'change_test_indicator', 'name': '修改', 'parent_id': 78},

    {'id': 82, 'code': 'test_type', 'name': '胶料试验类型管理', 'parent_id': None},
    {'id': 83, 'code': 'view_test_type', 'name': '查看', 'parent_id': 82},
    {'id': 84, 'code': 'add_test_type', 'name': '新增', 'parent_id': 82},
    {'id': 85, 'code': 'change_test_type', 'name': '修改', 'parent_id': 82},
    {'id': 86, 'code': 'pointAdd_test_type', 'name': '新增类型数据点', 'parent_id': 82},
    {'id': 87, 'code': 'pointChange_test_type', 'name': '修改类型数据点', 'parent_id': 82},

    {'id': 88, 'code': 'test_method', 'name': '胶料试验方法管理', 'parent_id': None},
    {'id': 89, 'code': 'view_test_method', 'name': '查看', 'parent_id': 88},
    {'id': 90, 'code': 'add_test_method', 'name': '新增', 'parent_id': 88},
    {'id': 91, 'code': 'change_test_method', 'name': '修改', 'parent_id': 88},

    {'id': 92, 'code': 'level', 'name': '胶料等级管理', 'parent_id': None},
    {'id': 93, 'code': 'view_level', 'name': '查看', 'parent_id': 92},
    {'id': 94, 'code': 'add_level', 'name': '新增', 'parent_id': 92},
    {'id': 95, 'code': 'delete_level', 'name': '删除', 'parent_id': 92},

    {'id': 96, 'code': 'evaluating', 'name': '胶料判断基准录入', 'parent_id': None},
    {'id': 97, 'code': 'view_evaluating', 'name': '查看', 'parent_id': 96},
    {'id': 98, 'code': 'add_evaluating', 'name': '新增', 'parent_id': 96},
    {'id': 99, 'code': 'change_evaluating', 'name': '修改', 'parent_id': 96},

    {'id': 100, 'code': 'month_passing_rate', 'name': '胶料月合格率统计', 'parent_id': None},
    {'id': 101, 'code': 'view_month_passing_rate', 'name': '查看', 'parent_id': 100},

    {'id': 102, 'code': 'product_month_passing_rate', 'name': '胶料月合格率统计', 'parent_id': None},
    {'id': 103, 'code': 'view_product_month_passing_rate', 'name': '查看', 'parent_id': 102},

    {'id': 104, 'code': 'product_daily_passing_rate', 'name': '胶料日合格率统计', 'parent_id': None},
    {'id': 105, 'code': 'view_product_daily_passing_rate', 'name': '查看', 'parent_id': 104},

    {'id': 106, 'code': 'non-conformity_product', 'name': '胶料不合格品处理', 'parent_id': None},
    {'id': 107, 'code': 'view_non-conformity_product', 'name': '查看', 'parent_id': 106},
    {'id': 108, 'code': 'change_non-conformity_product', 'name': '修改', 'parent_id': 106},

    {'id': 109, 'code': 'deal_suggestion', 'name': '胶料处理意见管理', 'parent_id': None},
    {'id': 110, 'code': 'view_deal_suggestion', 'name': '查看', 'parent_id': 109},
    {'id': 111, 'code': 'add_deal_suggestion', 'name': '新增', 'parent_id': 109},
    {'id': 112, 'code': 'change_deal_suggestion', 'name': '修改', 'parent_id': 109},

    {'id': 113, 'code': 'test_result', 'name': '胶料检测数据录入', 'parent_id': None},
    {'id': 114, 'code': 'view_test_result', 'name': '查看', 'parent_id': 113},
    {'id': 115, 'code': 'add_test_result', 'name': '新增', 'parent_id': 113},

    {'id': 116, 'code': 'result_info', 'name': '胶料快检结果详细信息', 'parent_id': None},
    {'id': 117, 'code': 'view_result_info', 'name': '查看', 'parent_id': 116},
    {'id': 163, 'code': 'export_result_info', 'name': '导出', 'parent_id': 116},

    {'id': 118, 'code': 'deal_result', 'name': '胶料快检信息综合管理', 'parent_id': None},
    {'id': 119, 'code': 'view_deal_result', 'name': '查看', 'parent_id': 118},
    {'id': 162, 'code': 'print_deal_result', 'name': '打印', 'parent_id': 118},
    {'id': 540, 'code': 'all_deal_result', 'name': '批量修改车次', 'parent_id': 118},
    {'id': 541, 'code': 'only_deal_result', 'name': '修改指定车次', 'parent_id': 118},

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

    {'id': 135, 'code': 'in_out_history', 'name': '物料出入库履历', 'parent_id': None},
    {'id': 136, 'code': 'view_in_out_history', 'name': '查看', 'parent_id': 135},

    {'id': 137, 'code': 'goods', 'name': '物料库位信息', 'parent_id': None},
    {'id': 138, 'code': 'view_goods', 'name': '查看', 'parent_id': 137},

    {'id': 139, 'code': 'inventory_plan', 'name': '胶片库出库计划', 'parent_id': None},
    {'id': 140, 'code': 'view_inventory_plan', 'name': '查看', 'parent_id': 139},
    {'id': 141, 'code': 'norman_inventory_plan', 'name': '正常出库', 'parent_id': 139},
    {'id': 142, 'code': 'assign_inventory_plan', 'name': '指定出库', 'parent_id': 139},
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

    {'id': 155, 'code': 'LB_inventory_plan', 'name': '帘布库出库计划', 'parent_id': None},
    {'id': 156, 'code': 'view_LB_inventory_plan', 'name': '查看', 'parent_id': 155},
    {'id': 157, 'code': 'norman_LB_inventory_plan', 'name': '正常出库', 'parent_id': 155},
    {'id': 158, 'code': 'assign_LB_inventory_plan', 'name': '指定出库', 'parent_id': 155},
    {'id': 159, 'code': 'manual_LB_inventory_plan', 'name': '人工出库', 'parent_id': 155},
    {'id': 160, 'code': 'close_LB_inventory_plan', 'name': '关闭', 'parent_id': 155},
    {'id': 161, 'code': 'change_LB_inventory_plan', 'name': '编辑', 'parent_id': 155},

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

    {'id': 185, 'code': 'location', 'name': '库存位管理', 'parent_id': None},
    {'id': 186, 'code': 'view_location', 'name': '查看', 'parent_id': 185},
    {'id': 187, 'code': 'add_location', 'name': '新增', 'parent_id': 185},
    {'id': 188, 'code': 'change_location', 'name': '修改', 'parent_id': 185},
    {'id': 189, 'code': 'delete_location', 'name': '启用/停用', 'parent_id': 185},

    {'id': 190, 'code': 'spare_location', 'name': '库存位管理', 'parent_id': None},
    {'id': 191, 'code': 'view_spare_location', 'name': '查看', 'parent_id': 190},
    {'id': 192, 'code': 'add_spare_location', 'name': '新增', 'parent_id': 190},
    {'id': 193, 'code': 'change_spare_location', 'name': '修改', 'parent_id': 190},
    {'id': 194, 'code': 'delete_spare_location', 'name': '启用/停用', 'parent_id': 190},

    {'id': 195, 'code': 'spare_type', 'name': '类型管理', 'parent_id': None},
    {'id': 196, 'code': 'view_spare_type', 'name': '查看', 'parent_id': 195},
    {'id': 197, 'code': 'add_spare_type', 'name': '新增', 'parent_id': 195},
    {'id': 198, 'code': 'change_spare_type', 'name': '修改', 'parent_id': 195},
    {'id': 199, 'code': 'delete_spare_type', 'name': '启用/停用', 'parent_id': 195},

    {'id': 200, 'code': 'spare_info', 'name': '备品备件基本信息管理', 'parent_id': None},
    {'id': 201, 'code': 'view_spare_info', 'name': '查看', 'parent_id': 200},
    {'id': 202, 'code': 'add_spare_info', 'name': '新增', 'parent_id': 200},
    {'id': 203, 'code': 'change_spare_info', 'name': '修改', 'parent_id': 200},
    {'id': 204, 'code': 'delete_spare_info', 'name': '删除', 'parent_id': 200},

    {'id': 205, 'code': 'location_binding', 'name': '货架物料绑定管理', 'parent_id': None},
    {'id': 206, 'code': 'view_location_binding', 'name': '查看', 'parent_id': 205},
    {'id': 207, 'code': 'add_location_binding', 'name': '新增', 'parent_id': 205},
    {'id': 208, 'code': 'change_location_binding', 'name': '修改', 'parent_id': 205},
    {'id': 209, 'code': 'delete_location_binding', 'name': '删除', 'parent_id': 205},

    {'id': 210, 'code': 'spare_inventory', 'name': '备品备件库位管理', 'parent_id': None},
    {'id': 211, 'code': 'view_spare_inventory', 'name': '查看', 'parent_id': 210},
    {'id': 212, 'code': 'price_spare_inventory', 'name': '查看单价', 'parent_id': 210},

    {'id': 213, 'code': 'spare_stock', 'name': '备品备件库存管理', 'parent_id': None},
    {'id': 214, 'code': 'view_spare_stock', 'name': '查看', 'parent_id': 213},
    {'id': 215, 'code': 'price_spare_stock', 'name': '查看单价', 'parent_id': 213},

    {'id': 216, 'code': 'spare_import', 'name': '备品备件库存导入', 'parent_id': None},
    {'id': 217, 'code': 'view_spare_import', 'name': '查看', 'parent_id': 216},
    {'id': 218, 'code': 'import_spare_import', 'name': '导入', 'parent_id': 216},
    {'id': 219, 'code': 'download_spare_import', 'name': '下载', 'parent_id': 216},

    {'id': 220, 'code': 'spare_inbound', 'name': '备品备件入库管理', 'parent_id': None},
    {'id': 221, 'code': 'view_spare_inbound', 'name': '查看', 'parent_id': 220},
    {'id': 222, 'code': 'add_spare_inbound', 'name': '新增', 'parent_id': 220},
    {'id': 223, 'code': 'inbound_spare_inbound', 'name': '入库', 'parent_id': 220},
    {'id': 224, 'code': 'history_spare_inbound', 'name': '查看履历', 'parent_id': 220},
    {'id': 225, 'code': 'price_spare_inbound', 'name': '查看单价', 'parent_id': 220},

    {'id': 226, 'code': 'spare_outbound', 'name': '备品备件出库管理', 'parent_id': None},
    {'id': 227, 'code': 'view_spare_outbound', 'name': '查看', 'parent_id': 226},
    {'id': 228, 'code': 'cancel_spare_outbound', 'name': '撤销', 'parent_id': 226},
    {'id': 229, 'code': 'inbound_spare_outbound', 'name': '出库', 'parent_id': 226},
    {'id': 230, 'code': 'history_spare_outbound', 'name': '查看履历', 'parent_id': 226},
    {'id': 231, 'code': 'price_spare_outbound', 'name': '查看单价', 'parent_id': 226},

    {'id': 232, 'code': 'stock_count', 'name': '备品备件盘点管理', 'parent_id': None},
    {'id': 233, 'code': 'view_stock_count', 'name': '查看', 'parent_id': 232},
    {'id': 234, 'code': 'change_stock_count', 'name': '更改', 'parent_id': 232},
    {'id': 235, 'code': 'history_stock_count', 'name': '查看履历', 'parent_id': 232},

    {'id': 236, 'code': 'inbound_history', 'name': '备品备件入库履历', 'parent_id': None},
    {'id': 237, 'code': 'view_inbound_history', 'name': '查看', 'parent_id': 236},
    {'id': 238, 'code': 'export_inbound_history', 'name': '导出', 'parent_id': 236},
    {'id': 239, 'code': 'price_inbound_history', 'name': '查看单价', 'parent_id': 236},

    {'id': 240, 'code': 'outbound_history', 'name': '备品备件出库履历', 'parent_id': None},
    {'id': 241, 'code': 'view_outbound_history', 'name': '查看', 'parent_id': 240},
    {'id': 242, 'code': 'export_outbound_history', 'name': '导出', 'parent_id': 240},
    {'id': 243, 'code': 'price_outbound_history', 'name': '查看单价', 'parent_id': 240},

    {'id': 244, 'code': 'stock_history', 'name': '备品备件盘点履历', 'parent_id': None},
    {'id': 245, 'code': 'view_stock_history', 'name': '查看', 'parent_id': 244},
    {'id': 246, 'code': 'export_stock_history', 'name': '导出', 'parent_id': 244},

    {'id': 247, 'code': 'trains_report', 'name': '车次报表', 'parent_id': None},
    {'id': 248, 'code': 'view_trains_report', 'name': '查看', 'parent_id': 247},

    {'id': 249, 'code': 'production_analyze', 'name': '产量计划实际分析', 'parent_id': None},
    {'id': 250, 'code': 'view_production_analyze', 'name': '查看', 'parent_id': 249},
    {'id': 251, 'code': 'change_production_analyze', 'name': '编辑', 'parent_id': 249},

    {'id': 252, 'code': 'section_production', 'name': '区间产量统计', 'parent_id': None},
    {'id': 253, 'code': 'view_section_production', 'name': '查看', 'parent_id': 252},

    {'id': 254, 'code': 'finalRubber_plan', 'name': '终炼胶出库计划', 'parent_id': None},
    {'id': 255, 'code': 'view_finalRubber_plan', 'name': '查看', 'parent_id': 254},
    {'id': 256, 'code': 'norman_finalRubber_plan', 'name': '正常出库', 'parent_id': 254},
    {'id': 257, 'code': 'assign_finalRubber_plan', 'name': '指定出库', 'parent_id': 254},
    {'id': 258, 'code': 'manual_finalRubber_plan', 'name': '人工出库', 'parent_id': 254},
    {'id': 259, 'code': 'close_finalRubber_plan', 'name': '关闭', 'parent_id': 254},
    {'id': 260, 'code': 'change_finalRubber_plan', 'name': '编辑', 'parent_id': 254},

    {'id': 261, 'code': 'compoundRubber_plan', 'name': '混炼胶出库计划', 'parent_id': None},
    {'id': 262, 'code': 'view_compoundRubber_plan', 'name': '查看', 'parent_id': 261},
    {'id': 263, 'code': 'norman_compoundRubber_plan', 'name': '正常出库', 'parent_id': 261},
    {'id': 264, 'code': 'assign_compoundRubber_plan', 'name': '指定出库', 'parent_id': 261},
    {'id': 265, 'code': 'manual_compoundRubber_plan', 'name': '人工出库', 'parent_id': 261},
    {'id': 266, 'code': 'close_compoundRubber_plan', 'name': '关闭', 'parent_id': 261},
    {'id': 267, 'code': 'change_compoundRubber_plan', 'name': '编辑', 'parent_id': 261},

    {'id': 270, 'code': 'weight_tank', 'name': '称量系统料仓信息管理', 'parent_id': None},
    {'id': 271, 'code': 'view_weight_tank', 'name': '查看', 'parent_id': 270},
    {'id': 272, 'code': 'change_weight_tank', 'name': '修改', 'parent_id': 270},
    {'id': 273, 'code': 'add_weight_tank', 'name': '新增', 'parent_id': 270},
    {'id': 274, 'code': 'delete_weight_tank', 'name': '启用/停用', 'parent_id': 270},

    {'id': 275, 'code': 'weight_batching', 'name': '小料配料标准管理', 'parent_id': None},
    {'id': 276, 'code': 'view_weight_batching', 'name': '查看', 'parent_id': 275},
    {'id': 277, 'code': 'add_weight_batching', 'name': '增加', 'parent_id': 275},
    {'id': 278, 'code': 'change_weight_batching', 'name': '修改', 'parent_id': 275},
    {'id': 280, 'code': 'submit_weight_batching', 'name': '提交', 'parent_id': 275},
    {'id': 281, 'code': 'check_weight_batching', 'name': '校对', 'parent_id': 275},
    {'id': 282, 'code': 'use_weight_batching', 'name': '启用', 'parent_id': 275},
    {'id': 283, 'code': 'refuse_weight_batching', 'name': '驳回', 'parent_id': 275},
    {'id': 284, 'code': 'abandon_weight_batching', 'name': '弃用', 'parent_id': 275},

    {'id': 285, 'code': 'batching_plan', 'name': '小料计划下达', 'parent_id': None},
    {'id': 286, 'code': 'view_batching_plan', 'name': '查看', 'parent_id': 285},
    {'id': 287, 'code': 'change_batching_plan', 'name': '修改', 'parent_id': 285},
    {'id': 288, 'code': 'send_batching_plan', 'name': '下达', 'parent_id': 285},

    {'id': 289, 'code': 'batching_reality', 'name': '小料称量计划与实际对比', 'parent_id': None},
    {'id': 290, 'code': 'view_batching_reality', 'name': '查看', 'parent_id': 289},

    {'id': 291, 'code': 'batch_log', 'name': '密炼投入履历', 'parent_id': None},
    {'id': 292, 'code': 'view_batch_log', 'name': '查看', 'parent_id': 291},

    {'id': 293, 'code': 'drug_analyze', 'name': '药品投入统计', 'parent_id': None},
    {'id': 294, 'code': 'view_drug_analyze', 'name': '查看', 'parent_id': 293},

    {'id': 295, 'code': 'zl_dashboard', 'name': '终炼胶出库看板', 'parent_id': None},
    {'id': 296, 'code': 'view_fm_dashboard', 'name': '查看', 'parent_id': 295},

    {'id': 297, 'code': 'hl_dashboard', 'name': '混炼胶出库看板', 'parent_id': None},
    {'id': 298, 'code': 'view_hl_dashboard', 'name': '查看', 'parent_id': 297},


    {'id': 299, 'code': 'equip_part', 'name': '设备部位定义', 'parent_id': None},
    {'id': 300, 'code': 'view_equip_part', 'name': '查看', 'parent_id': 299},
    {'id': 301, 'code': 'add_equip_part', 'name': '增加', 'parent_id': 299},
    {'id': 302, 'code': 'change_equip_part', 'name': '编辑', 'parent_id': 299},
    {'id': 303, 'code': 'delete_equip_part', 'name': '删除', 'parent_id': 299},

    {'id': 304, 'code': 'equip_down_type', 'name': '停机类型定义', 'parent_id': None},
    {'id': 305, 'code': 'view_equip_down_type', 'name': '查看', 'parent_id': 304},
    {'id': 306, 'code': 'add_equip_down_type', 'name': '增加', 'parent_id': 304},
    {'id': 307, 'code': 'delete_equip_down_type', 'name': '删除', 'parent_id': 304},

    {'id': 308, 'code': 'equip_down_reason', 'name': '停机原因定义', 'parent_id': None},
    {'id': 309, 'code': 'add_equip_down_reason', 'name': '增加', 'parent_id': 308},
    {'id': 310, 'code': 'view_equip_down_reason', 'name': '查看', 'parent_id': 308},
    {'id': 311, 'code': 'change_equip_down_reason', 'name': '编辑', 'parent_id': 308},
    {'id': 312, 'code': 'delete_equip_down_reason', 'name': '删除', 'parent_id': 308},

    {'id': 313, 'code': 'equip_current_status', 'name': '设备维修申请页面', 'parent_id': None},
    {'id': 314, 'code': 'view_equip_current_status', 'name': '查看', 'parent_id': 313},
    {'id': 315, 'code': 'maintenance_request_equip_current_status ', 'name': '维修申请', 'parent_id': 313},
    {'id': 316, 'code': 'affirm_equip_current_status', 'name': '确认启动', 'parent_id': 313},

    {'id': 317, 'code': 'equip_maintenance_order', 'name': '设备维修单管理', 'parent_id': None},
    {'id': 318, 'code': 'view_equip_maintenance_order', 'name': '查看', 'parent_id': 317},
    {'id': 319, 'code': 'change_equip_maintenance_order', 'name': '编辑', 'parent_id': 317},
    {'id': 320, 'code': 'add_equip_maintenance_order', 'name': '增加', 'parent_id': 317},
    {'id': 321, 'code': 'designate_equip_maintenance_order', 'name': '指派', 'parent_id': 317},
    {'id': 322, 'code': 'order_receiving_equip_maintenance_order', 'name': '接单', 'parent_id': 317},
    {'id': 323, 'code': 'chargeback_equip_maintenance_order', 'name': '退单', 'parent_id': 317},
    {'id': 324, 'code': 'close_equip_maintenance_order', 'name': '关闭', 'parent_id': 317},

    {'id': 325, 'code': 'equip_status', 'name': '设备运行现况', 'parent_id': None},
    {'id': 326, 'code': 'view_equip_status', 'name': '查看', 'parent_id': 325},

    {'id': 327, 'code': 'equip_maintenance_order_log', 'name': '设备维修履历', 'parent_id': None},
    {'id': 328, 'code': 'view_equip_maintenance_order_log', 'name': '查看', 'parent_id': 327},

    {'id': 329, 'code': 'property_type_node', 'name': '资产类型节点', 'parent_id': None},
    {'id': 330, 'code': 'view_property_type_node', 'name': '查看', 'parent_id': 329},
    {'id': 331, 'code': 'add_property_type_node', 'name': '增加', 'parent_id': 329},
    {'id': 332, 'code': 'delete_property_type_node', 'name': '删除', 'parent_id': 329},

    {'id': 333, 'code': 'property', 'name': '资产', 'parent_id': None},
    {'id': 334, 'code': 'view_property', 'name': '查看', 'parent_id': 333},
    {'id': 335, 'code': 'add_property', 'name': '增加', 'parent_id': 333},
    {'id': 336, 'code': 'change_property', 'name': '编辑', 'parent_id': 333},
    {'id': 337, 'code': 'delete_property', 'name': '删除', 'parent_id': 333},
    {'id': 338, 'code': 'import_property', 'name': '导入', 'parent_id': 333},
    {'id': 339, 'code': 'download_property', 'name': '模板下载', 'parent_id': 333},

    {'id': 340, 'code': 'platform_config', 'name': '通知配置', 'parent_id': None},
    {'id': 341, 'code': 'add_platform_config', 'name': '增加', 'parent_id': 340},
    {'id': 342, 'code': 'delete_platform_config', 'name': '删除', 'parent_id': 340},
    {'id': 343, 'code': 'change_platform_config', 'name': '编辑', 'parent_id': 340},
    {'id': 344, 'code': 'view_platform_config', 'name': '查看', 'parent_id': 340},

    {'id': 345, 'code': 'barcodequality', 'name': '临时条码质量维护', 'parent_id': None},
    {'id': 346, 'code': 'view_barcodequality', 'name': '查看临时条码质量', 'parent_id': 345},
    {'id': 347, 'code': 'add_barcodequality', 'name': '维护临时条码质量', 'parent_id': 345},
    {'id': 348, 'code': 'export_barcodequality', 'name': '导出临时条码质量维护', 'parent_id': 345},

    {'id': 349, 'code': 'material_map', 'name': 'ERP原材料信息', 'parent_id': None},
    {'id': 350, 'code': 'view_material_map', 'name': '查看', 'parent_id': 349},
    {'id': 351, 'code': 'add_material_map', 'name': '新增', 'parent_id': 349},
    {'id': 493, 'code': 'change_material_map', 'name': '修改', 'parent_id': 349},
    {'id': 494, 'code': 'delete_material_map', 'name': '停用/启用', 'parent_id': 349},

    {'id': 352, 'code': 'bar_code', 'name': '条码变更', 'parent_id': None},
    {'id': 353, 'code': 'view_bar_code', 'name': '查看', 'parent_id': 352},
    {'id': 354, 'code': 'rebuild_bar_code', 'name': '重新生成', 'parent_id': 352},

    {'id': 355, 'code': 'material_temp_input', 'name': '原材料临时快检结果录入', 'parent_id': None},
    {'id': 356, 'code': 'view_material_temp_input', 'name': '查看', 'parent_id': 355},
    {'id': 357, 'code': 'add_material_temp_input', 'name': '录入', 'parent_id': 355},

    {'id': 358, 'code': 'material_equipment', 'name': '原料试快检设备管理', 'parent_id': None},
    {'id': 359, 'code': 'view_material_equipment', 'name': '查看', 'parent_id': 358},
    {'id': 360, 'code': 'add_material_equipment', 'name': '新增', 'parent_id': 358},
    {'id': 361, 'code': 'change_material_equipment', 'name': '修改', 'parent_id': 358},

    {'id': 362, 'code': 'material_examine_type', 'name': '原料快检类型管理', 'parent_id': None},
    {'id': 363, 'code': 'view_material_examine_type', 'name': '查看', 'parent_id': 362},
    {'id': 364, 'code': 'add_material_examine_type', 'name': '新增', 'parent_id': 362},
    {'id': 365, 'code': 'change_material_examine_type', 'name': '修改', 'parent_id': 362},
    # {'id': 366, 'code': 'pointAdd_raw_test_type', 'name': '新增类型数据点', 'parent_id': 362},
    # {'id': 367, 'code': 'pointChange_raw_test_type', 'name': '修改类型数据点', 'parent_id': 362},

    {'id': 368, 'code': 'material_examine_value', 'name': '原料检测值管理', 'parent_id': None},
    {'id': 369, 'code': 'view_material_examine_value', 'name': '查看', 'parent_id': 368},
    {'id': 370, 'code': 'add_material_examine_value', 'name': '新增', 'parent_id': 368},
    {'id': 371, 'code': 'change_material_examine_value', 'name': '修改', 'parent_id': 368},
    #
    {'id': 372, 'code': 'examine_material', 'name': '快检原材料管理', 'parent_id': None},
    {'id': 373, 'code': 'view_examine_material', 'name': '查看', 'parent_id': 372},
    {'id': 374, 'code': 'deal_examine_material', 'name': '不合格处理', 'parent_id': 372},
    # {'id': 375, 'code': 'deal_examine_material', 'name': '不合格处理', 'parent_id': 372},
    #
    # {'id': 376, 'code': 'raw_evaluating', 'name': '原料判断基准录入', 'parent_id': None},
    # {'id': 377, 'code': 'view_raw_evaluating', 'name': '查看', 'parent_id': 376},
    # {'id': 378, 'code': 'add_raw_evaluating', 'name': '新增', 'parent_id': 376},
    # {'id': 379, 'code': 'change_raw_evaluating', 'name': '修改', 'parent_id': 376},
    #
    # {'id': 380, 'code': 'raw_test_result', 'name': '原料检测数据录入', 'parent_id': None},
    # {'id': 381, 'code': 'view_raw_test_result', 'name': '查看', 'parent_id': 380},
    # {'id': 382, 'code': 'add_raw_test_result', 'name': '新增', 'parent_id': 380},
    #
    # {'id': 383, 'code': 'raw_result_info', 'name': '原料快检结果详细信息', 'parent_id': None},
    # {'id': 384, 'code': 'view_raw_result_info', 'name': '查看', 'parent_id': 383},
    # {'id': 385, 'code': 'change_raw_result_info', 'name': '修改', 'parent_id': 383},
    #
    # {'id': 386, 'code': 'raw_unqualified_material', 'name': '原料不合格品处理', 'parent_id': None},
    # {'id': 387, 'code': 'view_raw_unqualified_material', 'name': '查看', 'parent_id': 386},
    # {'id': 388, 'code': 'deal_raw_unqualified_material', 'name': '处理', 'parent_id': 386},
    # {'id': 389, 'code': 'submit_raw_unqualified_material', 'name': '确认/驳回', 'parent_id': 386},

    {'id': 390, 'code': 'material_retrospect', 'name': '原材料条码追朔', 'parent_id': None},
    {'id': 391, 'code': 'view_material_retrospect', 'name': '查看', 'parent_id': 390},

    {'id': 392, 'code': 'product_retrospect', 'name': '胶片条码追朔', 'parent_id': None},
    {'id': 393, 'code': 'view_product_retrospect', 'name': '查看', 'parent_id': 392},

    {'id': 394, 'code': 'material_outbound_plan', 'name': '原材料出库计划', 'parent_id': None},
    {'id': 395, 'code': 'view_material_outbound_plan', 'name': '查看', 'parent_id': 394},
    {'id': 396, 'code': 'norman_material_outbound_plan', 'name': '正常出库', 'parent_id': 394},
    {'id': 397, 'code': 'assign_material_outbound_plan', 'name': '指定出库', 'parent_id': 394},
    {'id': 398, 'code': 'manual_material_outbound_plan', 'name': '人工出库', 'parent_id': 394},
    {'id': 399, 'code': 'close_material_outbound_plan', 'name': '关闭', 'parent_id': 394},
    {'id': 400, 'code': 'change_material_outbound_plan', 'name': '编辑', 'parent_id': 394},

    {'id': 401, 'code': 'carbon_outbound_plan', 'name': '炭黑出库计划', 'parent_id': None},
    {'id': 402, 'code': 'view_carbon_outbound_plan', 'name': '查看', 'parent_id': 401},
    {'id': 403, 'code': 'norman_carbon_outbound_plan', 'name': '正常出库', 'parent_id': 401},
    {'id': 404, 'code': 'assign_carbon_outbound_plan', 'name': '指定出库', 'parent_id': 401},
    {'id': 405, 'code': 'manual_carbon_outbound_plan', 'name': '人工出库', 'parent_id': 401},
    {'id': 406, 'code': 'close_carbon_outbound_plan', 'name': '关闭', 'parent_id': 401},
    {'id': 407, 'code': 'change_carbon_outbound_plan', 'name': '编辑', 'parent_id': 401},

    {'id': 408, 'code': 'equip_daily_summary', 'name': '设备别故障日统计', 'parent_id': None},
    {'id': 409, 'code': 'view_equip_daily_summary', 'name': '查看', 'parent_id': 408},

    {'id': 410, 'code': 'equip_weekly_summary', 'name': '设备别故障周统计', 'parent_id': None},
    {'id': 411, 'code': 'view_equip_weekly_summary', 'name': '查看', 'parent_id': 410},

    {'id': 412, 'code': 'equip_monthly_summary', 'name': '设备别故障月统计', 'parent_id': None},
    {'id': 413, 'code': 'view_equip_monthly_summary', 'name': '查看', 'parent_id': 412},

    {'id': 414, 'code': 'department', 'name': '部门管理', 'parent_id': None},
    {'id': 415, 'code': 'view_department', 'name': '查看', 'parent_id': 414},
    {'id': 416, 'code': 'add_department', 'name': '新增', 'parent_id': 414},
    {'id': 417, 'code': 'delete_department', 'name': '停用', 'parent_id': 414},
    {'id': 418, 'code': 'change_department', 'name': '编辑', 'parent_id': 414},

    {'id': 419, 'code': 'production_record', 'name': '生产运行记录', 'parent_id': None},
    {'id': 420, 'code': 'view_production_record', 'name': '查看', 'parent_id': 419},

    {'id': 421, 'code': 'product_stock_detail', 'name': '胶料库存明细', 'parent_id': None},
    {'id': 422, 'code': 'view_product_stock_detail', 'name': '查看', 'parent_id': 421},

    {'id': 423, 'code': 'workshop_stock_detail', 'name': '车间库存明细', 'parent_id': None},
    {'id': 424, 'code': 'view_workshop_stock_detail', 'name': '查看', 'parent_id': 423},

    {'id': 425, 'code': 'xl_material', 'name': '小料称量物料管理', 'parent_id': None},
    {'id': 426, 'code': 'view_xl_material', 'name': '查看', 'parent_id': 425},
    {'id': 427, 'code': 'add_xl_material', 'name': '新增', 'parent_id': 425},
    # {'id': 428, 'code': 'change_xl_material', 'name': '修改', 'parent_id': 424},

    {'id': 429, 'code': 'xl_bin', 'name': '小料称量料仓管理', 'parent_id': None},
    {'id': 430, 'code': 'view_xl_bin', 'name': '查看', 'parent_id': 429},
    # {'id': 431, 'code': 'add_xl_bin', 'name': '新增', 'parent_id': 429},
    {'id': 432, 'code': 'change_xl_bin', 'name': '修改', 'parent_id': 429},
    # {'id': 433, 'code': 'delete_xl_material', 'name': '删除', 'parent_id': 429},

    {'id': 434, 'code': 'xl_recipe', 'name': '小料称量配方管理', 'parent_id': None},
    {'id': 435, 'code': 'view_xl_recipe', 'name': '查看', 'parent_id': 434},
    # {'id': 436, 'code': 'add_xl_recipe', 'name': '新增', 'parent_id': 434},
    # {'id': 437, 'code': 'change_xl_recipe', 'name': '修改', 'parent_id': 434},
    # {'id': 438, 'code': 'delete_xl_recipe', 'name': '删除', 'parent_id': 434},

    {'id': 439, 'code': 'xl_plan', 'name': '小料称量计划管理', 'parent_id': None},
    {'id': 440, 'code': 'view_xl_plan', 'name': '查看', 'parent_id': 439},
    {'id': 441, 'code': 'add_xl_plan', 'name': '新增', 'parent_id': 439},
    {'id': 442, 'code': 'change_xl_plan', 'name': '修改', 'parent_id': 439},
    {'id': 443, 'code': 'delete_xl_plan', 'name': '删除', 'parent_id': 439},
    {'id': 444, 'code': 'issue_xl_plan', 'name': '下达', 'parent_id': 439},
    {'id': 445, 'code': 'reload_xl_plan', 'name': '重传', 'parent_id': 439},
    {'id': 446, 'code': 'stop_xl_plan', 'name': '停止', 'parent_id': 439},

    {'id': 447, 'code': 'xl_report_basic', 'name': '小料称量车次报表', 'parent_id': None},
    {'id': 448, 'code': 'view_xl_report_basic', 'name': '查看', 'parent_id': 447},

    {'id': 449, 'code': 'xl_report_weight', 'name': '小料称量物料消耗报表', 'parent_id': None},
    {'id': 450, 'code': 'view_xl_report_weight', 'name': '查看', 'parent_id': 449},

    {'id': 451, 'code': 'material_outbound_record', 'name': '原材料出库单据', 'parent_id': None},
    {'id': 452, 'code': 'view_material_outbound_record', 'name': '查看', 'parent_id': 451},
    {'id': 453, 'code': 'space_material_outbound_record', 'name': '指定库位出库', 'parent_id': 451},
    {'id': 454, 'code': 'weight_material_outbound_record', 'name': '指定重量出库', 'parent_id': 451},

    {'id': 455, 'code': 'material_outbound_task', 'name': '原材料出库任务', 'parent_id': None},
    {'id': 456, 'code': 'view_material_outbound_task', 'name': '查看', 'parent_id': 455},

    {'id': 457, 'code': 'material_daily_summary', 'name': '原材料出库日报', 'parent_id': None},
    {'id': 458, 'code': 'view_material_daily_summary', 'name': '查看', 'parent_id': 457},

    {'id': 459, 'code': 'material_monthly_summary', 'name': '原材料出库月报', 'parent_id': None},
    {'id': 460, 'code': 'view_material_monthly_summary', 'name': '查看', 'parent_id': 459},

    {'id': 461, 'code': 'material_yearly_summary', 'name': '原材料出库年报', 'parent_id': None},
    {'id': 462, 'code': 'view_material_yearly_summary', 'name': '查看', 'parent_id': 461},

    {'id': 489, 'code': 'material_inventory_summary', 'name': '原材料库存统计', 'parent_id': None},
    {'id': 490, 'code': 'view_material_inventory_summary', 'name': '查看', 'parent_id': 489},

    {'id': 463, 'code': 'th_outbound_record', 'name': '炭黑库出库单据', 'parent_id': None},
    {'id': 464, 'code': 'view_th_outbound_record', 'name': '查看', 'parent_id': 463},
    {'id': 465, 'code': 'space_th_outbound_record', 'name': '指定库位出库', 'parent_id': 463},
    {'id': 466, 'code': 'weight_th_outbound_record', 'name': '指定重量出库', 'parent_id': 463},

    {'id': 467, 'code': 'th_outbound_task', 'name': '炭黑库出库任务', 'parent_id': None},
    {'id': 468, 'code': 'view_th_outbound_task', 'name': '查看', 'parent_id': 467},

    {'id': 469, 'code': 'th_daily_summary', 'name': '炭黑库出库日报', 'parent_id': None},
    {'id': 470, 'code': 'view_th_daily_summary', 'name': '查看', 'parent_id': 469},

    {'id': 471, 'code': 'material_th_summary', 'name': '炭黑库出库月报', 'parent_id': None},
    {'id': 472, 'code': 'view_th_monthly_summary', 'name': '查看', 'parent_id': 471},

    {'id': 473, 'code': 'th_yearly_summary', 'name': '炭黑库出库年报', 'parent_id': None},
    {'id': 474, 'code': 'view_th_yearly_summary', 'name': '查看', 'parent_id': 473},

    {'id': 491, 'code': 'th_inventory_summary', 'name': '炭黑库存统计', 'parent_id': None},
    {'id': 492, 'code': 'view_th_inventory_summary', 'name': '查看', 'parent_id': 491},

    {'id': 475, 'code': 'material_report_equip', 'name': '原材料上报设备管理', 'parent_id': None},
    {'id': 476, 'code': 'view_material_report_equip', 'name': '查看', 'parent_id': 475},
    {'id': 477, 'code': 'add_material_report_equip', 'name': '新增', 'parent_id': 475},
    {'id': 478, 'code': 'change_material_report_equip', 'name': '修改', 'parent_id': 475},

    {'id': 479, 'code': 'material_report_value', 'name': '原材料上报值管理', 'parent_id': None},
    {'id': 480, 'code': 'view_material_report_value', 'name': '查看', 'parent_id': 479},
    {'id': 481, 'code': 'add_material_report_value', 'name': '新增', 'parent_id': 479},

    {'id': 482, 'code': 'product_report_equip', 'name': '胶料上报设备管理', 'parent_id': None},
    {'id': 483, 'code': 'view_product_report_equip', 'name': '查看', 'parent_id': 482},
    {'id': 484, 'code': 'add_product_report_equip', 'name': '新增', 'parent_id': 482},
    {'id': 485, 'code': 'change_product_report_equip', 'name': '修改', 'parent_id': 482},

    {'id': 486, 'code': 'product_report_value', 'name': '胶料上报值管理', 'parent_id': None},
    {'id': 487, 'code': 'view_product_report_value', 'name': '查看', 'parent_id': 486},
    {'id': 488, 'code': 'add_product_report_value', 'name': '新增', 'parent_id': 486},
    {'id': 534, 'code': 'xl_weight_card', 'name': '小料称量质量追踪卡管理', 'parent_id': None},
    {'id': 535, 'code': 'view_xl_weight_card', 'name': '查看', 'parent_id': 534},
    {'id': 536, 'code': 'print_xl_weight_card', 'name': '打印', 'parent_id': 534},

    {'id': 537, 'code': 'xl_expire_data', 'name': '小料称量料包有效期', 'parent_id': None},
    {'id': 538, 'code': 'view_xl_expire_data', 'name': '查看', 'parent_id': 537},
    {'id': 539, 'code': 'save_xl_expire_data', 'name': '保存', 'parent_id': 537},

    # 下个权限id值从495开始
]


@atomic()
def init_permissions():
    for item in permission_data:
        Permissions.objects.create(**item)


def main():
    print('开始迁移数据库')
    apps = ('system', 'basics', 'plan', 'production',
            'recipe', 'quality', 'inventory', 'spareparts',
            'terminal', 'equipment')

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
