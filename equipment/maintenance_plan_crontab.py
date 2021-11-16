import logging
import os
import sys
import django
import datetime
import logging

from django.db.transaction import atomic


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes.settings')
django.setup()

from equipment.models import EquipMaintenanceStandard, EquipPlan, Equip, EquipApplyOrder
from django.db.models import Count, Max

from production.models import TrainsFeedbacks


class MaintenancePlan:
    def create_plan(self, obj, equip, plan_date, next_date=None):
        work_type = {
            '巡检': 'XJ',
            '保养': 'BY',
            '润滑': 'RH',
            '标定': 'BD',
        }

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
            # created_user=
        )

    def maintenance_plan(self):
        queryset = EquipMaintenanceStandard.objects.filter(use_flag=True).all()
        for obj in queryset:
            if not obj.start_time:
                continue
            start_time = datetime.datetime.strptime(str(obj.start_time),'%Y-%m-%d')
            kwargs = {  # 判断条件
                '日': {'status': datetime.datetime.now() <= start_time + datetime.timedelta(days=obj.maintenance_cycle * obj.cycle_num) and
                  datetime.datetime.now() + datetime.timedelta(days=3) >= start_time},
                '小时': {'status': datetime.datetime.now() <= start_time + datetime.timedelta(hours=obj.maintenance_cycle * obj.cycle_num) and
                  datetime.datetime.now() + datetime.timedelta(days=3) >= start_time},
                '分钟': {'status': datetime.datetime.now() <= start_time + datetime.timedelta(minutes=obj.maintenance_cycle * obj.cycle_num) and
                  datetime.datetime.now() + datetime.timedelta(days=3) >= start_time},
                '秒': {'status': datetime.datetime.now() <= start_time + datetime.timedelta(seconds=obj.maintenance_cycle * obj.cycle_num) and
                  datetime.datetime.now() + datetime.timedelta(days=3) >= start_time}}

            if obj.cycle_unit == '车次':
                equip_list = Equip.objects.filter(category=obj.equip_type).values('equip_no')
                for equip in equip_list:
                    actual_trains = TrainsFeedbacks.objects.filter(equip_no=equip['equip_no'],
                                                                   factory_date__gte=start_time,
                                                                   factory_date__lte=datetime.datetime.now()).aggregate(
                                                                   actual_trains=Count('id'))
                    actual_trains = actual_trains.get('actual_trains')
                    if actual_trains < obj.maintenance_cycle * obj.cycle_num:
                        for i in range(1, obj.cycle_num + 1):
                            if actual_trains in [(i-1) * obj.maintenance_cycle, i * obj.maintenance_cycle] and EquipPlan.objects.filter(equip_manintenance_standard=obj).count() == (i-1):
                                # 获取开始时间
                                try:
                                    plan_time = TrainsFeedbacks.objects.filter(equip_no=equip['equip_no'],
                                                                   factory_date__gte=start_time,
                                                                   factory_date__lte=datetime.datetime.now()).order_by('id')[obj.maintenance_cycle * (i-1)].created_date
                                    self.create_plan(obj, equip['equip_no'], plan_time)
                                except: pass
            else:
                if kwargs.get(obj.cycle_unit)['status']:
                    equip_list = Equip.objects.filter(category=obj.equip_type).values('equip_no')
                    if not Equip.objects.filter(category=obj.equip_type).values('equip_no').exists():
                        return ''
                    equip = '，'.join([equip['equip_no'] for equip in equip_list])
                    for i in range(1, obj.cycle_num + 1):
                        kwargs = {
                            '日': {'first': (start_time - datetime.timedelta(days=3)),
                                  'st': (start_time + datetime.timedelta(days=obj.maintenance_cycle * (i - 1))),
                                  'et': (start_time + datetime.timedelta(days=obj.maintenance_cycle * i))},
                            '小时': {'first': (start_time - datetime.timedelta(hours=3)),
                                   'st': (start_time + datetime.timedelta(hours=obj.maintenance_cycle * (i - 1))),
                                   'et': (start_time + datetime.timedelta(hours=obj.maintenance_cycle * i))},
                            '分钟': {'first': (start_time - datetime.timedelta(minutes=3)),
                                   'st': (start_time + datetime.timedelta(minutes=obj.maintenance_cycle * (i - 1))),
                                   'et': (start_time + datetime.timedelta(minutes=obj.maintenance_cycle * i))},
                            '秒': {'first': (start_time - datetime.timedelta(seconds=3)),
                                  'st': (start_time + datetime.timedelta(seconds=obj.maintenance_cycle * (i - 1))),
                                  'et': (start_time + datetime.timedelta(seconds=obj.maintenance_cycle * i))},
                        }
                        if i == 1:
                            plan = EquipPlan.objects.filter(equip_manintenance_standard=obj,
                                                     planned_maintenance_date__gte=kwargs.get(obj.cycle_unit)['first'],
                                                     planned_maintenance_date__lte=kwargs.get(obj.cycle_unit)['et']).exists()
                            now_time = (kwargs.get(obj.cycle_unit)['first'] < datetime.datetime.now() < kwargs.get(obj.cycle_unit)['et'])
                            if not plan and now_time:
                                self.create_plan(obj, equip, kwargs.get(obj.cycle_unit)['first'], kwargs.get(obj.cycle_unit)['et'])
                        else:
                            plan = EquipPlan.objects.filter(equip_manintenance_standard=obj,
                                                     planned_maintenance_date__gte=kwargs.get(obj.cycle_unit)['st'],
                                                     planned_maintenance_date__lte=kwargs.get(obj.cycle_unit)['et']).exists()
                            now_time = (kwargs.get(obj.cycle_unit)['st'] < datetime.datetime.now() < kwargs.get(obj.cycle_unit)['et'])
                            if not plan and now_time:
                                self.create_plan(obj, equip, kwargs.get(obj.cycle_unit)['st'], kwargs.get(obj.cycle_unit)['et'])


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
                pass
            else:
                if not EquipApplyOrder.objects.filter(plan.plan_id).exists() and plan.planned_maintenance_date - datetime.datetime.now() < datetime.timedelta(days=1):
                    for equip in equip_list:
                        max_order_code = \
                        EquipApplyOrder.objects.filter(work_order_no__startswith=plan.plan_id).aggregate(
                            max_order_code=Max('work_order_no'))['max_order_code']
                        work_order_no = plan.plan_id + '-' + (
                            '%04d' % (int(max_order_code.split('-')[-1] + 1)) if max_order_code else '0001')

                        EquipApplyOrder.objects.create(plan_id=plan.plan_id,
                                                   plan_name=plan.plan_name,
                                                   work_type=plan.work_type,
                                                   work_order_no=work_order_no,
                                                   equip_no=equip,
                                                   equip_maintenance_standard=plan.equip_manintenance_standard,
                                                   planned_repair_date=plan.planned_repair_date,
                                                   status='已生成',
                                                   equip_condition=plan.equip_condition,
                                                   importance_level=plan.importance_level,
                                                   # created_user=self.request.user,
                                                   )
                    plan.status = '已生成工单'
                    plan.save()


if __name__ == '__main__':
    maintenance_plan = MaintenancePlan()
    maintenance_plan.maintenance_plan()
    apply_order = ApplyOrder()
    apply_order.create_order()
