# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/8/3
name: 
"""
import json
from datetime import datetime, timedelta

from basics.models import WorkSchedulePlan, GlobalCode
from mes.common_code import get_virtual_time
from production.models import OperationLog, EmployeeAttendanceRecords, AttendanceGroupSetup, WeightClassPlan, \
    WeightClassPlanDetail
from production.serializers import OperationLogSerializer
from system.models import User
from terminal.utils import get_current_factory_date


class OpreationLogRecorder(object):

    def __init__(self, *args, **kwargs):
        self.equip_no = kwargs.get("equip_no", "")
        self.content = kwargs.get("content", {})
        temp_content = '{"message": "record log failed"}'
        if isinstance(self.content, dict):
            temp_content = json.dumps(self.content)
        self.data = dict(equip_no=self.equip_no, content=temp_content)

    def log_recoder(self):
        OperationLog.objects.create(**self.data)


def get_standard_time(user_name, factory_date, global_name='密炼', group=None, classes=None):
    """根据参数获取当天的上下班时间"""
    begin_time, end_time, now_time = None, None, f'{factory_date} {datetime.now().time()}'
    # last_obj = EmployeeAttendanceRecords.objects.filter(user__username=user_name, factory_date=factory_date).last()
    # if last_obj:  # 有打卡记录
    #     filter_kwargs = {'classes__global_name': last_obj.classes, 'group__global_name': last_obj.group,
    #                      'plan_schedule__day_time': factory_date,
    #                      'plan_schedule__work_schedule__work_procedure__global_name': global_name}
    # else:  # 没有打卡记录[有班组(打卡)、无班组]
    if group and classes:
        filter_kwargs = {'classes__global_name': classes, 'group__global_name': group,
                         'plan_schedule__day_time': factory_date,
                         'plan_schedule__work_schedule__work_procedure__global_name': global_name}
    else:
        filter_kwargs = {'start_time__lte': now_time, 'end_time__gte': now_time,
                         'plan_schedule__day_time': factory_date,
                         'plan_schedule__work_schedule__work_procedure__global_name': global_name}
    w = WorkSchedulePlan.objects.filter(**filter_kwargs).last()
    if w:
        begin_time, end_time = w.start_time, w.end_time
    return begin_time, end_time


def get_work_time(class_code, factory_date):
    """根据排班代码获取上班时间"""
    res = {}
    if class_code:
        s_global = GlobalCode.objects.filter(global_type__type_name='配料间排班详细分类', global_type__use_flag=True,
                                             use_flag=True, global_name=class_code)
        if s_global:
            for i in s_global:
                pare = i.description.split('-')
                if len(pare) in [3, 6]:
                    for j in range(len(pare) // 3):
                        index, begin_date, end_date = j * 3, factory_date, factory_date
                        if pare[index] == '夜班':
                            next_day = (datetime.strptime(factory_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
                            begin_date, end_date = next_day if pare[index + 1] == '00:00:00' else factory_date, next_day
                        if pare[index] in ['中班', '2']:
                            next_day = (datetime.strptime(factory_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
                            begin_date, end_date = factory_date, next_day if pare[index + 2] == '00:00:00' else factory_date
                        res.update({pare[index]: [f'{begin_date} {pare[index + 1]}', f'{end_date} {pare[index + 2]}']})
    if len(res) >= 2:
        now_time = get_virtual_time()
        h = now_time.time().hour
        if 24 >= h >= 22 or 0 <= h <= 2:
            res = dict(sorted(res.items(), key=lambda x: x[0]))
    return res


def get_classes_plan(select_date=None, work_procedure=None, username=None):
    pre_date = select_date if select_date else datetime.now().strftime('%Y-%m-%d')
    work_procedure = work_procedure if work_procedure else '密炼'
    res = {}
    if work_procedure == '密炼':
        classes_plan = WorkSchedulePlan.objects.filter(plan_schedule__day_time=pre_date,
                                                       plan_schedule__work_schedule__work_procedure__global_name=work_procedure) \
            .values('classes__global_name', 'start_time', 'end_time')
        if classes_plan:
            res = {i['classes__global_name']: [i['start_time'].strftime('%Y-%m-%d %H:%M:%S'),
                                               i['end_time'].strftime('%Y-%m-%d %H:%M:%S')] for i in
                   classes_plan}
    else:
        classes_plan = WeightClassPlanDetail.objects.filter(weight_class_plan__user__username=username, factory_date=select_date,
                                                            weight_class_plan__delete_flag=False).last()
        if classes_plan and classes_plan.class_code:
            res = get_work_time(classes_plan.class_code, select_date)
    return res


def get_user_group(user_name, choice_type='密炼'):
    """获取考勤组负责人对应班组数据"""
    user_groups = []
    u_flag = User.objects.filter(is_superuser=True, username=user_name)
    att_set = AttendanceGroupSetup.objects.filter(group__isnull=False, type=choice_type)
    if u_flag:
        user_groups = list(att_set.values_list('group', flat=True).distinct())
    else:
        for i in att_set:
            if not i.principal:
                continue
            if user_name in i.principal.split(',') and i.group not in user_groups:
                user_groups.append(i.group)
    return user_groups


def get_user_weight_flag(user):
    """查询员工是否是称量人员"""
    flag, clock_type = False, '密炼'
    factory_date = get_current_factory_date()['factory_date']
    classes_plan = WeightClassPlanDetail.objects.filter(weight_class_plan__user=user, factory_date=factory_date,
                                                        weight_class_plan__delete_flag=False).last()
    if classes_plan:
        if classes_plan.class_code:
            flag, clock_type = True, '生产配料'
    return flag, clock_type

