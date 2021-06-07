
import os
import sys
import uuid
from datetime import datetime

import django
from django.db.models import Max

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from production.models import PalletFeedbacks
from quality.models import MaterialTestOrder, MaterialTestResult, TestType
from basics.models import WorkSchedulePlan
from quality.models import ZCKJConfig

import pymssql
import logging
logger = logging.getLogger('quality_log')


def get_min_max_id(server, user, password, database, test_date):
    sql = """select min(RID), max(RID) from ResultInfo where TestDate>'{}';""".format(test_date)
    conn = pymssql.connect(server, user, password, database)
    cur = conn.cursor()
    cur.execute(sql)
    data = cur.fetchall()
    return data[0][0], data[0][1]


def main():
    for config in ZCKJConfig.objects.all():
        max_test_date = MaterialTestResult.objects.filter(origin=config.id).aggregate(
            max_test_date=Max('test_factory_date'))['max_test_date']
        if not max_test_date:
            max_test_date = '2020-11-22 00:00:00'
        else:
            max_test_date = datetime.strftime(max_test_date, "%Y-%m-%d %H:%M:%S")
        logger.info('ip:{}， max_test_date: {}'.format(config.server, max_test_date))
        server = config.server
        user = config.user
        password = config.password
        name = config.name
        try:
            min_id, max_id = get_min_max_id(server, user, password, name, max_test_date)
        except Exception:
            logger.error('connect database:{} error !'.format(server))
            continue
        if not min_id:
            continue
        while max_id >= min_id+1:
            sql = """select
                   r.DValue,
                   c.CompoundName,
                   rf.TestClass,
                   rf.TestGroup,
                   r.DataName,
                   mtm.MethodName,
                   rf.Result,
                   rf.Shift,
                   rf.MixDate,
                   rf.MixerNo,
                   rf.TestDate,
                   rf.TestNo,
                   mt.MachineTypename,
                   rf.CompoundCode,
                   tt.TypeName
                from ResultInfo rf
            inner join SubTest st on st.RID=rf.RID
            inner join Result r on rf.RID=r.RID
            inner join Compound c on c.id=rf.CompoundID
            inner join MainTestMethod mtm on mtm.id=rf.MainMethodID
            inner join TestType tt on tt.ID=mtm.TestTypeID
            inner join MachineType1 mt on mt.ID=tt.MachineTypeID
            where 
                rf.RID>={} 
                and rf.RID<={} 
                and rf.TestGroup!='' 
                and rf.MixerNo in ('Z01', 'Z02','Z03','Z04','Z05',
                                   'Z06','Z07','Z08','Z09','Z10',
                                   'Z11', 'Z12','Z13','Z14','Z15')
                and rf.TestClass!='';""".format(str(min_id), str(min_id+1000))
            conn = pymssql.connect(server, user, password, name)
            cur = conn.cursor()
            cur.execute(sql)
            data = cur.fetchall()
            for item in data:
                value = item[0]
                product_no = item[1].strip(' ')  # 胶料代码
                production_class = item[2].strip(' ')  # 生产班次
                data_point_name = item[4].strip(' ')  # 数据点
                method_name = item[5].strip(' ')  # 试验方法名称
                result = item[6].strip(' ')  # 结果
                trains = int(item[7])  # 车次
                d = []
                for a in item[8].strip(' ').split('/'):
                    d.append(a.zfill(2))
                product_date = '-'.join(d)  # 生产日期
                equip_no = item[9].strip(' ')  # 设备编号
                test_date = item[10]  # 试验日期
                test_times = item[11]  # 试验次数
                try:
                    interval = int(item[13].strip(' '))
                except Exception:
                    interval = 1
                test_group = item[3].strip(' ')  # 试验班组
                test_type_name = item[-1].strip(' ')  # 检测类型

                # 根据机器名称找到指标点
                test_type = TestType.objects.filter(name=test_type_name).first()
                if not test_type:
                    logger.error('no test type:{}'.format(test_type_name))
                    continue
                else:
                    indicator_name = test_type.test_indicator.name

                # 根据班组找班次（找到的不一定对）
                schedule_plan = WorkSchedulePlan.objects.filter(
                    plan_schedule__work_schedule__schedule_name='三班两运转',
                    plan_schedule__day_time=product_date,
                    classes__global_name=production_class
                ).first()
                if schedule_plan:
                    group = schedule_plan.group.global_name
                else:
                    group = 'A'

                # 关键看能不能找到托盘反馈数据
                for i in range(trains, trains+interval):
                    # 根据机台编号、胶料代码、班次、日期找托盘lot_no
                    pallet = PalletFeedbacks.objects.filter(
                        equip_no=equip_no,
                        product_no__icontains=product_no,
                        classes=production_class,
                        factory_date=product_date,
                        begin_trains__lte=i,
                        end_trains__gte=i
                    ).first()
                    if not pallet:
                        logger.error("cant find pallet data, 设备：{}， 胶料：{}， 班次：{}， 日期：{}， 车次：{}".format(
                            equip_no, product_no, production_class, product_date, i))
                        continue
                    lot_no = pallet.lot_no
                    test_order = MaterialTestOrder.objects.filter(lot_no=lot_no,
                                                                  actual_trains=i).first()
                    if not test_order:
                        test_order = MaterialTestOrder.objects.create(
                            lot_no=lot_no,
                            material_test_order_uid=uuid.uuid1(),
                            actual_trains=i,
                            product_no=product_no,
                            plan_classes_uid=pallet.plan_classes_uid,
                            production_class=production_class,
                            production_group=group,
                            production_equip_no=equip_no,
                            production_factory_date=product_date
                        )
                    # TODO   由MES判断检测结果
                    # material_test_method = MaterialTestMethod.objects.filter(
                    #     material__material_no=product_no,
                    #     test_method__name=method_name,
                    #     test_method__test_type__test_indicator__name=indicator_name,
                    #     data_point__name=data_point_name,
                    #     data_point__test_type__test_indicator__name=indicator_name).first()
                    # if material_test_method:
                    #     indicator = MaterialDataPointIndicator.objects.filter(
                    #         material_test_method=material_test_method,
                    #         data_point__name=data_point_name,
                    #         data_point__test_type__test_indicator__name=indicator_name,
                    #         upper_limit__gte=value,
                    #         lower_limit__lte=value).first()
                    #     if indicator:
                    #         mes_result = indicator.result
                    #         level = indicator.level
                    #     else:
                    #         mes_result = '三等品'
                    #         level = 2
                    # else:
                    #     mes_result = '三等品'
                    #     level = 2

                    if not MaterialTestResult.objects.filter(
                            material_test_order=test_order,
                            test_times=test_times,
                            data_point_name=data_point_name,
                            test_indicator_name=indicator_name,
                            origin=config.id).exists():
                        MaterialTestResult.objects.create(
                            material_test_order=test_order,
                            test_factory_date=test_date,
                            value=value,
                            test_times=test_times,
                            data_point_name=data_point_name,
                            test_method_name=method_name,
                            test_indicator_name=indicator_name,
                            result='一等品' if result == '合格' else '三等品',
                            mes_result=result,
                            machine_name=indicator_name+'仪',
                            test_group=test_group,
                            level=1 if result == '合格' else 2,
                            test_class=production_class,
                            origin=config.id)
            conn.close()
            min_id += 1000


if __name__ == '__main__':
    main()
