"""
根据设备维护维修标准自动生成维护维修计划
"""

import os
import sys
import django
import datetime
import math


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes.settings')
django.setup()

from django.db.models import Count, Max
from django.db.transaction import atomic
from equipment.models import EquipMaintenanceStandard, EquipPlan, Equip, EquipApplyOrder, EquipInspectionOrder
from production.models import TrainsFeedbacks
from system.models import User


class MaintenancePlan:
    def create_plan(self, obj, equip, plan_date, next_date=None):
        work_type = {
            '巡检': 'XJ',
            '保养': 'BY',
            '润滑': 'RH',
            '标定': 'BD',
            '维修': 'BX',
        }
        user = User.objects.filter(username='系统自动').first()
        dic = EquipPlan.objects.filter(work_type=obj.work_type, created_date__date=datetime.date.today()).aggregate(
            Max('plan_id'))
        res = dic.get('plan_id__max')
        if res:
            plan_id = res[:10] + str('%04d' % (int(res[-4:]) + 1))
        else:
            plan_id = f'{work_type.get(obj.work_type)}{datetime.date.today().strftime("%Y%m%d")}0001'
        EquipPlan.objects.create(
            work_type=obj.work_type,
            plan_id=plan_id,
            plan_name=f'{obj.work_type}{plan_id}',
            equip_no=equip,
            equip_manintenance_standard=obj,
            equip_repair_standard=None,
            equip_condition=obj.equip_condition,
            importance_level=obj.important_level,
            plan_source='自动生成',
            status='未生成工单',
            planned_maintenance_date=plan_date,
            next_maintenance_date=next_date,
            created_date=datetime.datetime.now(),
            created_user=user
        )

    def maintenance_plan(self):
        queryset = EquipMaintenanceStandard.objects.filter(use_flag=True).all()
        for obj in queryset:
            if not obj.cycle_unit or not obj.start_time:
                continue
            start_time = datetime.datetime.strptime(str(obj.start_time),'%Y-%m-%d')  # 开始时间
            maintenance_cycle = obj.maintenance_cycle if obj.maintenance_cycle else 1  # 维护周期
            cycle_unit = obj.cycle_unit  # 周期单位
            cycle_num = obj.cycle_num if obj.cycle_num else 0  # 周期数
            # 一个周期时长
            cycle_time = {
                '4小时': datetime.timedelta(hours=4) * maintenance_cycle,
                '日': datetime.timedelta(days=1) * maintenance_cycle,
                '周': datetime.timedelta(days=7) * maintenance_cycle,
                '月': datetime.timedelta(days=30) * maintenance_cycle,
                '季度': datetime.timedelta(days=30) * maintenance_cycle,
                '年': datetime.timedelta(days=365) * maintenance_cycle,
                '半年': datetime.timedelta(days=182) * maintenance_cycle,
            }
            if obj.cycle_unit == '车数':
                equip_list = Equip.objects.filter(category=obj.equip_type).values('equip_no')
                for equip in equip_list:
                    actual_trains = TrainsFeedbacks.objects.filter(equip_no=equip['equip_no'],
                                                                   end_time__gte=start_time,
                                                                   end_time__lte=datetime.datetime.now()).aggregate(
                                                                   actual_trains=Count('id'))

                    actual_trains = actual_trains.get('actual_trains')
                    if cycle_num and actual_trains < maintenance_cycle * cycle_num:
                        for i in range(1, obj.cycle_num + 1):
                            if actual_trains in [(i-1) * obj.maintenance_cycle, i * obj.maintenance_cycle] and EquipPlan.objects.filter(equip_manintenance_standard=obj).count() == (i-1):
                                try:
                                    plan_time = datetime.datetime.now().replace(microsecond=0)
                                    self.create_plan(obj, equip['equip_no'], plan_time)
                                except: pass
                    else:
                        count = actual_trains // maintenance_cycle
                        if EquipPlan.objects.filter(equip_manintenance_standard=obj).count() < count:
                            plan_time = datetime.datetime.now().replace(microsecond=0)
                            self.create_plan(obj, equip['equip_no'], plan_time)
                continue
            elif obj.cycle_unit == '班次':
                equip_list = Equip.objects.filter(category=obj.equip_type).values('equip_no')
                if not Equip.objects.filter(category=obj.equip_type).values('equip_no').exists():
                    return ''
                equip = '，'.join([equip['equip_no'] for equip in equip_list])
                today = datetime.datetime.today()
                tomorrow = datetime.datetime.today() + datetime.timedelta(days=1)
                now = datetime.datetime.now()
                # 早班
                begin_time = datetime.datetime(today.year, today.month, today.day) + datetime.timedelta(hours=8)
                end_time = datetime.datetime(today.year, today.month, today.day) + datetime.timedelta(hours=20)
                tomorrow_time = datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day) + datetime.timedelta(hours=8)
                if begin_time <= now <= end_time:
                    if not EquipPlan.objects.filter(equip_manintenance_standard=obj, created_date__gte=begin_time,
                                                    created_date__lte=end_time).exists():
                        self.create_plan(obj, equip, begin_time, end_time)

                if end_time <= now <= tomorrow_time:
                    if not EquipPlan.objects.filter(equip_manintenance_standard=obj, created_date__gte=end_time,
                                                    created_date__lte=tomorrow_time).exists():
                        self.create_plan(obj, equip, end_time, tomorrow_time)
                continue
            else:
                if cycle_num:
                    count = cycle_num
                else:  # 周期数为0
                    count = math.ceil((datetime.datetime.now() - start_time) / cycle_time.get(cycle_unit))
                for i in range(1, count + 1):  # 1,   2 , 3
                    begin_time = start_time + cycle_time.get(cycle_unit) * (i - 1)
                    end_time = start_time + cycle_time.get(cycle_unit) * i
                    now = datetime.datetime.now()
                    if i == 1:
                        create_time = start_time - datetime.timedelta(days=3)
                    else:
                        create_time = begin_time - datetime.timedelta(days=3)
                    if create_time > begin_time:
                        continue
                    if now > end_time:
                        continue
                    equip_list = Equip.objects.filter(category=obj.equip_type).values('equip_no')
                    if not Equip.objects.filter(category=obj.equip_type).values('equip_no').exists():
                        return ''
                    equip = '，'.join([equip['equip_no'] for equip in equip_list])
                    if not EquipPlan.objects.filter(equip_manintenance_standard=obj, planned_maintenance_date=begin_time):
                        self.create_plan(obj, equip, begin_time, end_time)


class ApplyOrder:
    """
    提前一天自动生成维修工单
    """
    @atomic
    def create_order(self):
        queryset = EquipPlan.objects.filter(delete_flag=False).order_by('-id')
        for plan in queryset:
            equip_list = plan.equip_no.split('，')
            if plan.work_type == '巡检':
                if not EquipInspectionOrder.objects.filter(plan_id=plan.plan_id).exists() and (plan.planned_maintenance_date - datetime.datetime.now()) < datetime.timedelta(days=1):
                    for equip in equip_list:
                        max_order_code = EquipInspectionOrder.objects.filter(work_order_no__startswith=plan.plan_id). \
                            aggregate(max_order_code=Max('work_order_no'))['max_order_code']
                        work_order_no = plan.plan_id + '-' + (
                            '%04d' % (int(max_order_code.split('-')[-1]) + 1) if max_order_code else '0001')
                        user = User.objects.filter(username='系统自动').first()
                        EquipInspectionOrder.objects.create(plan_id=plan.plan_id,
                                                            plan_name=plan.plan_name,
                                                            work_type=plan.work_type,
                                                            work_order_no=work_order_no,
                                                            equip_no=equip,
                                                            equip_repair_standard=plan.equip_manintenance_standard,
                                                            planned_repair_date=plan.planned_maintenance_date,
                                                            status='已生成',
                                                            equip_condition=plan.equip_condition,
                                                            importance_level=plan.importance_level,
                                                            created_user=user
                                                   )
                    plan.status = '已生成工单'
                    plan.save()
            else:
                if not EquipApplyOrder.objects.filter(plan_id=plan.plan_id).exists() and (plan.planned_maintenance_date - datetime.datetime.now()) < datetime.timedelta(days=1):
                    for equip in equip_list:
                        max_order_code = EquipApplyOrder.objects.filter(work_order_no__startswith=plan.plan_id). \
                            aggregate(max_order_code=Max('work_order_no'))['max_order_code']
                        work_order_no = plan.plan_id + '-' + (
                            '%04d' % (int(max_order_code.split('-')[-1]) + 1) if max_order_code else '0001')
                        user = User.objects.filter(username='系统自动').first()
                        EquipApplyOrder.objects.create(plan_id=plan.plan_id,
                                                       plan_name=plan.plan_name,
                                                       work_type=plan.work_type,
                                                       work_order_no=work_order_no,
                                                       equip_no=equip,
                                                       equip_maintenance_standard=plan.equip_manintenance_standard,
                                                       equip_repair_standard=plan.equip_repair_standard,
                                                       planned_repair_date=plan.planned_maintenance_date,
                                                       status='已生成',
                                                       equip_condition=plan.equip_condition,
                                                       importance_level=plan.importance_level,
                                                       created_user=user)
                    plan.status = '已生成工单'
                    plan.save()


if __name__ == '__main__':
    maintenance_plan = MaintenancePlan()
    maintenance_plan.maintenance_plan()
    apply_order = ApplyOrder()
    apply_order.create_order()
