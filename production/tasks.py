"""
__Title__ = 'yzc_test.py'
__Author__ = 'yangzhenchao'
__Date__ = '2022/11/5'
__Version__ = 'Python 3.9'
__Software__ = 'PyCharm'
"""
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

    def get_equip_ratio(self, target_month):
        month_split = target_month.split('-')
        year = int(month_split[0])
        month = int(month_split[1])
        production_data = TrainsFeedbacks.objects.filter(
            factory_date__year=year,
            factory_date__month=month
        ).values('equip_no', 'factory_date', 'classes').annotate(total_trains=Count('id'))
        if month == datetime.now().month and year == datetime.now().year:
            now_date = get_current_factory_date()['factory_date']
            schedule_queryset = WorkSchedulePlan.objects.filter(
                plan_schedule__work_schedule__work_procedure__global_name='密炼',
                plan_schedule__day_time__year=year,
                plan_schedule__day_time__month=month,
                plan_schedule__day_time__lte=now_date,
            )
        else:
            schedule_queryset = WorkSchedulePlan.objects.filter(
                plan_schedule__work_schedule__work_procedure__global_name='密炼',
                plan_schedule__day_time__year=year,
                plan_schedule__day_time__month=month,
            )
        group_schedule_data = schedule_queryset.values('group__global_name').annotate(cnt=Count('id'))
        date_classes_dict = {'{}-{}'.format(i.plan_schedule.day_time.strftime("%m-%d"), i.classes.global_name): i.group.global_name for i in
                             schedule_queryset}
        down_data = EquipDownDetails.objects.filter(
            factory_date__year=year,
            factory_date__month=month
        ).values('group', 'equip_no').annotate(s=Sum('times'))
        equip_target_data = MachineTargetYieldSettings.objects.filter(target_month=target_month).values()
        target_data = {}
        if equip_target_data:
            target_data = equip_target_data[0]
        group_data_dict = {i: {'equip_no': i, 'target_trains': target_data.get(i, 0)} for i in
                           list(Equip.objects.filter(
                               category__equip_type__global_name="密炼设备"
                           ).order_by('equip_no').values_list("equip_no", flat=True))}

        for p in production_data:
            equip_no = p['equip_no']
            trains = p['total_trains'] if equip_no != 'Z04' else p['total_trains'] // 2
            gp = date_classes_dict.get('{}-{}'.format(p['factory_date'].strftime("%m-%d"), p['classes']))
            if not gp:
                continue
            gp_key = 'trains_{}'.format(gp)
            if gp_key not in group_data_dict[equip_no]:
                group_data_dict[equip_no][gp_key] = trains
            else:
                group_data_dict[equip_no][gp_key] += trains
        group_list = []  # 获取班组
        for s in group_schedule_data:
            s_key = 'days_{}'.format(s['group__global_name'])
            for equip_no in group_data_dict.keys():
                group_data_dict[equip_no][s_key] = s['cnt']
            if s['group__global_name'] not in group_list:
                group_list.append(s['group__global_name'])

        for d in down_data:
            equip_no = d['equip_no']
            gp = d['group']
            times = d['s']
            d_key = 'down_{}'.format(gp)
            if d_key not in group_data_dict[equip_no]:
                group_data_dict[equip_no][d_key] = times
            else:
                group_data_dict[equip_no][d_key] += times
        res = {}
        for i in group_data_dict.values():
            target_trains = i.get('target_trains')
            for g in group_list:
                s_train, s_day = i.get(f'trains_{g}', 0), i.get(f'days_{g}', 0)
                ratio = 0 if target_trains == 0 or s_day == 0 else round(s_train / (target_trains * s_day), 4)
                if g not in res:
                    res[g] = {i.get('equip_no'): ratio}
                else:
                    res[g][i.get('equip_no')] = ratio
        return res

    def get_user_group(self, select_date):
        res, exist_r = {}, []
        user_query = EmployeeAttendanceRecords.objects.filter(
            ~Q(Q(is_use__in=['废弃', '驳回']) | Q(section__in=['班长', '机动']) | Q(status='调岗')),
            end_date__isnull=False, begin_date__isnull=False,
            actual_time__isnull=False, clock_type='密炼', factory_date__startswith=select_date)
        for i in user_query:
            username, group, factory_date = i.user.username, i.group, i.factory_date
            key = f"{username}-{factory_date}"
            if key in exist_r:
                continue
            if username in res:
                res[username][group] = res[username].get(group, 0) + 1
            else:
                res[username] = {group: 1}
            exist_r.append(key)
        return res

    def handle_attendance(self, select_date, equip_ratio):
        user_query = EmployeeAttendanceRecords.objects.filter(
            ~Q(Q(is_use__in=['废弃', '驳回']) | Q(section__in=['班长', '机动'])),
            end_date__isnull=False, begin_date__isnull=False,
            actual_time__isnull=False, clock_type='密炼', factory_date__startswith=select_date) \
            .values('user', 'factory_date', 'section', 'begin_date').annotate(avg_time=Avg('actual_time'),
                                                                              username=F('user__username')) \
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
        # 人员最长天数对应班组
        user_group = self.get_user_group(select_date)
        # 个人最长时间的机台完成率
        user_ratio = []
        for k, v in _data.items():
            if not v:
                continue
            max_key = max(v, key=v.get)
            equips = max_key.split('-')[2:]
            group_info = user_group.get(k)
            if not group_info:
                _ratio = 0
            else:
                max_group = max(group_info, key=group_info.get)
                equips_ratio = equip_ratio.get(max_group)
                if not equips_ratio:
                    _ratio = 0
                else:
                    _ratio = round(sum([equips_ratio.get(equip, 0) for equip in equips]) / len(equips), 4)
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
