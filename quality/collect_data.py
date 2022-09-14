
"""
    根据机台检测计划，自动采集诺甲系统质检数据
"""
import datetime
import json
import os
import sys
import uuid
from decimal import Decimal

import django
from django.db.transaction import atomic

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

import pymssql
import logging
from func_timeout import func_set_timeout
logger = logging.getLogger('quality_log')
from quality.utils import gen_pallet_test_result
from quality.models import ZCKJConfig, ProductTestPlanDetail, ProductTestPlan, MaterialDataPointIndicator, \
    MaterialTestResult, MaterialTestMethod, MaterialTestOrder, ProductReportEquip
from production.models import PalletFeedbacks


@func_set_timeout(3)
def get_rids(server, user, password, database, machine_no, rid, test_time):
    sql = """select 
    RID 
    from ResultInfo 
    where MachineNo='{}' and RID>{} and TestDate>'{}' order by RID;""".format(machine_no, rid, test_time)
    conn = pymssql.connect(server, user, password, database)
    cur = conn.cursor()
    cur.execute(sql)
    data = cur.fetchall()
    return [i[0] for i in data]


@func_set_timeout(3)
def get_result_info(server, user, password, database, rid):
    sql = """select Dvalue,DataName from Result where RID={};""".format(rid)
    conn = pymssql.connect(server, user, password, database)
    cur = conn.cursor()
    cur.execute(sql)
    data = cur.fetchall()
    return data


# @atomic()
def main():
    lot_nos = []
    for config in ZCKJConfig.objects.filter(use_flag=True):

        for sub_machine in config.sub_machines.all():
            server = config.server
            user = config.user
            password = config.password
            name = config.name

            # 获取检测机台当前正在进行中的检测计划
            equip_test_plan = ProductTestPlan.objects.filter(test_equip__no=sub_machine.machine_no,
                                                             status=1).order_by('id').last()

            if not equip_test_plan:
                # logger.error('机台：{}，暂无正在检测的计划'.format(sub_machine.machine_no))
                continue

            try:
                rids = get_rids(server,
                                user,
                                password,
                                name,
                                sub_machine.nj_machine_no,
                                sub_machine.max_rid,
                                equip_test_plan.created_date.strftime('%Y-%m-%d %H:%M:%S'))
            except Exception:
                logger.error('connect database:{} error !'.format(server))
                continue

            method_name = equip_test_plan.test_method_name
            indicator_name = equip_test_plan.test_indicator_name
            test_times = equip_test_plan.test_times
            test_group = equip_test_plan.test_group
            test_class = equip_test_plan.test_classes

            # 给检测任务绑定检测值
            for rid in rids:
                # 获取当前检测任务
                current_test_detail = ProductTestPlanDetail.objects.filter(test_plan=equip_test_plan,
                                                                           status=1
                                                                           ).order_by('id').first()
                if not current_test_detail:
                    logger.error('检测机台：{}，检测任务已全部完成'.format(sub_machine.machine_no))
                    continue
                try:
                    data = get_result_info(server, user, password, name, rid)
                except Exception:
                    logger.error('connect database:{} error !'.format(server))
                    continue

                # 更新当前检测任务结果值
                test_results = {item[1].strip(' '): {"name": item[1].strip(' '), "value": item[0], "flag": ""} for item in data}
                # 卡片判级
                product_no = current_test_detail.product_no  # 胶料编码
                production_class = current_test_detail.production_classes  # 班次
                production_group = current_test_detail.production_group  # 班组
                equip_no = current_test_detail.equip_no  # 机台
                factory_date = current_test_detail.factory_date  # 工厂日期

                material_test_method = MaterialTestMethod.objects.filter(
                    material__material_no=product_no,
                    test_method__name=method_name).first()
                if not material_test_method:
                    continue
                test_data_points = material_test_method.data_point.values_list('name', flat=True)

                is_qualified = True
                # 对数据点进行判级
                for item in data:
                    value = Decimal(item[0]).quantize(Decimal('0.000'))
                    data_point_name = item[1].strip(' ')
                    if data_point_name not in test_data_points:
                        continue

                    # 获取判级标准
                    indicator = MaterialDataPointIndicator.objects.filter(
                        material_test_method=material_test_method,
                        data_point__name=data_point_name,
                        data_point__test_type__test_indicator__name=indicator_name,
                        level=1).first()
                    if indicator:
                        if indicator.lower_limit <= value <= indicator.upper_limit:
                            mes_result = '一等品'
                            level = 1
                            test_results[data_point_name]['flag'] = 'N'
                        else:
                            mes_result = '三等品'
                            level = 2
                            if value > indicator.upper_limit:
                                test_results[data_point_name]['flag'] = 'H'
                            elif value < indicator.lower_limit:
                                test_results[data_point_name]['flag'] = 'L'
                            is_qualified = False
                    else:
                        continue
                        # mes_result = '三等品'
                        # level = 2

                    for train in range(current_test_detail.actual_trains,
                                       current_test_detail.actual_trains + equip_test_plan.test_interval):
                        pallets = PalletFeedbacks.objects.filter(
                            equip_no=equip_no,
                            product_no=product_no,
                            classes=production_class,
                            factory_date=factory_date,
                            begin_trains__lte=train,
                            end_trains__gte=train
                        )
                        if not pallets:
                            continue

                        for pallet in pallets:
                            lot_no = pallet.lot_no
                            lot_nos.append(lot_no)
                            test_order_data = {
                                                "lot_no": lot_no,
                                                'material_test_order_uid':  uuid.uuid1(),
                                                'actual_trains':  train,
                                                'product_no':  product_no,
                                                'plan_classes_uid':  pallet.plan_classes_uid,
                                                'production_class':  production_class,
                                                'production_group':  production_group,
                                                'production_equip_no':  equip_no,
                                                'production_factory_date':  factory_date}
                            while True:
                                try:
                                    test_order, created = MaterialTestOrder.objects.get_or_create(
                                        defaults=test_order_data, **{'lot_no': lot_no,
                                                                     'actual_trains': train})
                                    break
                                except Exception:
                                    pass
                            value0 = None
                            judged_upper_limit0 = 0
                            judged_lower_limit0 = 0
                            if not created:
                                dp_instances = test_order.order_results.filter(data_point_name=data_point_name)
                                if dp_instances:
                                    v = dp_instances.first()
                                    value0 = v.value
                                    judged_upper_limit0 = v.judged_upper_limit
                                    judged_lower_limit0 = v.judged_lower_limit
                                    dp_instances.delete()
                                    test_order.is_recheck = True
                                    test_order.save()
                            # 创建数据点检测结果
                            MaterialTestResult.objects.create(
                                material_test_order=test_order,
                                test_factory_date=datetime.datetime.now(),
                                value=value,
                                test_times=test_times,
                                data_point_name=data_point_name,
                                test_method_name=method_name,
                                test_indicator_name=indicator_name,
                                result=mes_result,
                                mes_result=mes_result,
                                machine_name=equip_test_plan.test_equip.no,
                                test_group=test_group,
                                level=level,
                                test_class=test_class,
                                is_judged=material_test_method.is_judged,
                                created_user=equip_test_plan.created_user,
                                judged_upper_limit=indicator.upper_limit,
                                judged_lower_limit=indicator.lower_limit,
                                value0=value0,
                                judged_upper_limit0=judged_upper_limit0,
                                judged_lower_limit0=judged_lower_limit0
                            )

                current_test_detail.value = json.dumps(list(test_results.values()))
                current_test_detail.is_qualified = is_qualified
                current_test_detail.status = 2
                current_test_detail.save()
                # test_indicator_name = current_test_detail.test_plan.test_indicator_name
                # mto = MaterialTestOrder.objects.filter(lot_no=current_test_detail.lot_no,
                #                                        actual_trains=current_test_detail.actual_trains).first()
                # if mto:
                #     max_result_ids = list(mto.order_results.filter(
                #         test_indicator_name=test_indicator_name
                #     ).values('data_point_name').annotate(max_id=Max('id')).values_list('max_id', flat=True))
                #     if mto.order_results.filter(id__in=max_result_ids, level__gt=1).exists():
                #         current_test_detail.is_qualified = False
                #     else:
                #         current_test_detail.is_qualified = True
                #     current_test_detail.save()
            # 判断该机台计划是否全部检测完成
            # if equip_test_plan.product_test_plan_detail.filter(
            #         value__isnull=False).count() == equip_test_plan.product_test_plan_detail.count():
            #     equip_test_plan.status = 2
            #     equip_test_plan.save()

            if rids:
                sub_machine.max_rid = rids[-1]
                sub_machine.save()
    gen_pallet_test_result(lot_nos)


if __name__ == '__main__':
    main()
