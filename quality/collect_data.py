
"""
    根据机台检测计划，自动采集诺甲系统质检数据
"""
import datetime
import json
import os
import sys
import uuid

import django


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

import pymssql
import logging
logger = logging.getLogger('quality_log')

from quality.models import ZCKJConfig, ProductTestPlanDetail, ProductTestPlan, MaterialDataPointIndicator, \
    MaterialTestResult, MaterialTestMethod, MaterialTestOrder, ProductReportEquip
from production.models import PalletFeedbacks


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


def main():
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
                                                                           value__isnull=True
                                                                           ).order_by('id').first()
                if not current_test_detail:
                    logger.error('检测机台：{}，检测任务已全部完成'.format(sub_machine.machine_no))
                    continue
                sql = """select Dvalue,DataName from Result where RID={};""".format(rid)
                conn = pymssql.connect(server, user, password, name)
                cur = conn.cursor()
                cur.execute(sql)
                data = cur.fetchall()

                # 更新当前检测任务结果值
                test_results = {item[1].strip(' '): item[0] for item in data}
                current_test_detail.value = json.dumps(test_results)
                current_test_detail.status = 2
                current_test_detail.save()

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

                        # 车次检测单
                        test_order = MaterialTestOrder.objects.filter(
                            lot_no=lot_no, actual_trains=train).first()
                        if not test_order:
                            test_order = MaterialTestOrder.objects.create(
                                lot_no=lot_no,
                                material_test_order_uid=uuid.uuid1(),
                                actual_trains=train,
                                product_no=product_no,
                                plan_classes_uid=pallet.plan_classes_uid,
                                production_class=production_class,
                                production_group=production_group,
                                production_equip_no=equip_no,
                                production_factory_date=factory_date
                            )

                        # 对数据点进行判级
                        for item in data:
                            value = item[0]
                            data_point_name = item[1].strip(' ')
                            if data_point_name not in test_data_points:
                                continue

                            # 获取判级标准
                            indicator = MaterialDataPointIndicator.objects.filter(
                                material_test_method=material_test_method,
                                data_point__name=data_point_name,
                                data_point__test_type__test_indicator__name=indicator_name,
                                upper_limit__gte=value,
                                lower_limit__lte=value).first()
                            if indicator:
                                mes_result = indicator.result
                                level = indicator.level
                            else:
                                mes_result = '三等品'
                                level = 2

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
                                created_user=equip_test_plan.created_user
                            )

            # 判断该机台计划是否全部检测完成
            # if equip_test_plan.product_test_plan_detail.filter(
            #         value__isnull=False).count() == equip_test_plan.product_test_plan_detail.count():
            #     equip_test_plan.status = 2
            #     equip_test_plan.save()

            if rids:
                sub_machine.max_rid = rids[-1]
                sub_machine.save()


if __name__ == '__main__':
    main()
