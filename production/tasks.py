import os
import sys
import django
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from django.db.models import *
from django.db.transaction import atomic
from basics.models import WorkSchedulePlan, Equip
from terminal.utils import get_current_factory_date
from production.models import FinishRatio, TrainsFeedbacks, MachineTargetYieldSettings, ActualWorkingDay, EquipDownDetails, EmployeeAttendanceRecords


class SaveFinishRatio(object):
    """记录员工当月的完成率"""

    def get_date(self):
        now_date = datetime.now()
        check_date = f'{now_date.strftime("%Y-%m")}-01 12:00:00'
        if now_date.strftime("%Y-%m-%d %H:%M:%S") <= check_date:
            s_time = now_date - timedelta(days=1)
        else:
            s_time = now_date
        return now_date.strftime("%Y-%m")

    def get_equip_ratio(self, target_month, group_name=None):
        month_split = target_month.split('-')
        year = int(month_split[0])
        month = int(month_split[1])
        schedule_data = WorkSchedulePlan.objects.filter(plan_schedule__work_schedule__work_procedure__global_name='密炼', plan_schedule__day_time__year=year,
                                                        plan_schedule__day_time__month=month)\
            .order_by('start_time').values('plan_schedule__day_time', 'classes__global_name', 'group__global_name')
        production_data = TrainsFeedbacks.objects.filter(factory_date__year=year, factory_date__month=month)\
            .values('equip_no', 'factory_date', 'classes').annotate(total_trains=Count('id')).order_by('equip_no', 'factory_date')
        equip_target_data = MachineTargetYieldSettings.objects.filter(target_month=target_month).values()
        target_data = {}
        if equip_target_data:
            target_data = equip_target_data[0]
        schedule_dict = {}
        for i in schedule_data:
            k = '{}-{}'.format(i['plan_schedule__day_time'].strftime("%m/%d"), i['classes__global_name'][0])
            schedule_dict[k] = i['group__global_name'][0]

        working_days = ActualWorkingDay.objects.filter(
            factory_date__year=year, factory_date__month=month).aggregate(days=Sum('num'))['days']
        working_days = 0 if not working_days else working_days
        down_days_dict = dict(EquipDownDetails.objects.filter(
            factory_date__year=year,
            factory_date__month=month
        ).values('equip_no').annotate(days=Sum('times') / 60 / 24).values_list('equip_no', 'days'))
        if month == datetime.now().month and year == datetime.now().year:
            now_date = get_current_factory_date()['factory_date']
            group_schedule_days = WorkSchedulePlan.objects.filter(
                plan_schedule__work_schedule__work_procedure__global_name='密炼',
                plan_schedule__day_time__year=year,
                plan_schedule__day_time__month=month,
                plan_schedule__day_time__lte=now_date,
                group__global_name=group_name
            ).count()
        else:
            group_schedule_days = WorkSchedulePlan.objects.filter(
                plan_schedule__work_schedule__work_procedure__global_name='密炼',
                plan_schedule__day_time__year=year,
                plan_schedule__day_time__month=month,
                group__global_name=group_name
            ).count()
        group_down_days_dict = dict(EquipDownDetails.objects.filter(
            factory_date__year=year,
            factory_date__month=month,
            group=group_name
        ).values('equip_no').annotate(days=Sum('times') / 60 / 24).values_list('equip_no', 'days'))
        equip_production_data_dict = {i: {'equip_no': i,
                                          'total_trains': 0,
                                          'target_trains': target_data.get(i, 0),
                                          'days': working_days - down_days_dict.get(i, 0),
                                          'group_days': group_schedule_days - group_down_days_dict.get(i, 0),
                                          } for i in
                                      list(Equip.objects.filter(
                                          category__equip_type__global_name="密炼设备"
                                      ).order_by('equip_no').values_list("equip_no", flat=True))}
        for d in production_data:
            equip_no = d['equip_no']
            k = '{}-{}'.format(d['factory_date'].strftime("%m/%d"), d['classes'][0])
            key = '{}-{}'.format(k, schedule_dict[k])
            trains = d['total_trains'] // 2 if equip_no == 'Z04' else d['total_trains']
            equip_production_data_dict[equip_no][key] = trains
            equip_production_data_dict[equip_no]['total_trains'] += trains
        result = {}
        data = equip_production_data_dict.values()
        for i in data:
            total_target_trains = i['days'] * i['target_trains'] * 2
            result[i['equip_no']] = 0 if total_target_trains == 0 else round(i['total_trains'] / total_target_trains, 2)
        return result

    def handle_attendance(self, select_date, equip_ratio):
        user_query = EmployeeAttendanceRecords.objects.filter(~Q(Q(is_use__in=['废弃', '驳回']) | Q(section__in=['班长', '机动'])),
                                                              end_date__isnull=False, begin_date__isnull=False,
                                                              actual_time__isnull=False, clock_type='密炼', factory_date__startswith=select_date)\
            .values('user', 'factory_date', 'section', 'begin_date').annotate(avg_time=Avg('actual_time'), username=F('user__username'))\
            .values('username', 'factory_date', 'section', 'avg_time')
        _data = {}
        for i in user_query:
            # 获取机台
            info = list(EmployeeAttendanceRecords.objects.filter(user__username=i['username'], factory_date=i['factory_date'], section=i['section']).order_by('equip').values_list('equip', flat=True))
            key = f"{i['username']}-{i['section']}-{'-'.join(info)}"
            user_data = _data.get(i['username'])
            if not user_data:
                _data[i['username']] = {key: i['avg_time']}
            else:
                user_data[key] = round(i['avg_time'] + (0 if not user_data.get(key) else user_data.get(key)), 2)
        # 个人最长时间的机台完成率
        user_ratio = []
        for k, v in _data.items():
            if not v:
                continue
            max_key = max(v, key=v.get)
            equips = max_key.split('-')[2:]
            _ratio = round(sum([equip_ratio.get(equip, 0) for equip in equips]) / len(equips), 2)
            user_ratio.append({'target_month': select_date, 'username': k, 'ratio': _ratio, 'equip_list': ','.join(equips), 'actual_time': v[max_key]})
        return user_ratio

    @atomic
    def execute_sync(self):
        # 获取月份
        select_date = self.get_date()
        # 获取机台完成率
        equip_ratio = self.get_equip_ratio(select_date)  # {'Z01': 45.55, 'Z02': 69.4...}
        # 处理人员信息与机台完成率
        user_ratio = self.handle_attendance(select_date, equip_ratio)  # [{'target_month': '2022-10', 'username': '张三', 'ratio': 45.55, 'equip_list': 'Z01, Z14', 'actual_time': 104.56}...]
        # 保存或更新记录各人员炼胶完成率
        for i in user_ratio:
            FinishRatio.objects.update_or_create(defaults=i, **{'target_month': select_date, 'username': i['username']})


if __name__ == '__main__':
    s = SaveFinishRatio()
    s.execute_sync()

