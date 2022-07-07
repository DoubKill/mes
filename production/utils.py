# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/8/3
name: 
"""
import json
from datetime import datetime

from basics.models import WorkSchedulePlan
from production.models import OperationLog, EmployeeAttendanceRecords
from production.serializers import OperationLogSerializer


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
    last_obj = EmployeeAttendanceRecords.objects.filter(user__username=user_name, factory_date=factory_date).last()
    if last_obj:  # 有打卡记录
        filter_kwargs = {'classes__global_name': last_obj.classes, 'group__global_name': last_obj.group,
                         'plan_schedule__day_time': factory_date,
                         'plan_schedule__work_schedule__work_procedure__global_name': global_name}
    else:  # 没有打卡记录[有班组(打卡)、无班组]
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


