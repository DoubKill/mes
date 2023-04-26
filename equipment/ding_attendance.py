"""
__Title__ = 'ding_id_attenance.py'
__Author__ = 'yangzhenchao'
__Date__ = '2023/4/24'
__Version__ = 'Python 3.9'
__Software__ = 'PyCharm'
"""
import os
import sys
import django

from datetime import datetime, timedelta

from django.db.models import F, Q
from django.db.transaction import atomic

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from mes import settings
from equipment.utils import DinDinAPI, get_children_section
from system.models import Section
from equipment.models import DingUser
from basics.models import WorkSchedulePlan


class DingIdAttendance(object):

    @atomic
    def user_optional(self, section_name='设备科'):
        ding_api = DinDinAPI()
        # 设备科下的所有部门
        init_section = Section.objects.filter(name=section_name).last()
        section_list = get_children_section(init_section) if init_section else []
        # 忽略的用户
        ignore_ids = DingUser.objects.filter(delete_flag=True).values_list('user_id', flat=True)
        # 获取所有人员
        staffs = Section.objects.filter(~Q(section_users__id__in=ignore_ids), name__in=section_list, section_users__is_active=1)\
            .annotate(phone_number=F('section_users__phone_number'), uid=F('section_users__id')).values('phone_number', 'uid')
        # 获取当前时间的工厂日期
        now = datetime.now()
        current_work_schedule_plan = WorkSchedulePlan.objects.filter(start_time__lte=now, end_time__gte=now,
                                                                     plan_schedule__work_schedule__work_procedure__global_name='密炼').first()
        if current_work_schedule_plan:
            s_date_now = current_work_schedule_plan.plan_schedule.day_time
            date_now = str(s_date_now)
        else:
            date_now = str(now.date())
        if settings.DEBUG:
            for staff in staffs:
                uid, phone_number = staff.get('uid'), staff.get('phone_number')
                # 根据手机号获取用户钉钉uid
                ding_uid = ding_api.get_user_id(phone_number)
                # 更新或者创建
                DingUser.objects.update_or_create(user_id=uid, defaults={'user_id': uid, 'ding_uid': ding_uid, 'phone_number': phone_number,
                                                                         'optional': True if ding_uid else False})
        else:
            user_ding, default_optional = {}, False
            for staff in staffs:
                uid, phone_number = staff.get('uid'), staff.get('phone_number')
                # 根据手机号获取用户钉钉uid
                ding_uid = ding_api.get_user_id(phone_number)
                if ding_uid:
                    user_ding[ding_uid] = {'user_id': uid, 'ding_uid': ding_uid, 'phone_number': phone_number, 'optional': default_optional}
                else:
                    DingUser.objects.update_or_create(user_id=uid, defaults={'user_id': uid, 'ding_uid': ding_uid, 'phone_number': phone_number,
                                                                             'optional': default_optional})
            # 查询、整合考勤记录
            attendance, user_ids, records = {}, list(user_ding.keys()), []
            # 考勤记录一次最多查询50个人, 所以需要分批查询(钉钉一次返回最多50条考勤记录)
            for i in range(0, len(user_ids), 10):
                record = ding_api.get_user_attendance(user_ids[i:i+10], begin_time=date_now, end_time=date_now)
                records.extend(record)
            # 整合考勤记录
            for r in records:
                attendance[r['userId']] = attendance.get(r['userId'], []) + [r]
            # 判断是否为可选人员
            for k, v in attendance.items():
                if len([i for i in v if i['checkType'] != 'OnDuty' and i['timeResult'] != 'NotSigned']) == 0:
                    user_ding[k]['optional'] = True
            # 更新或者创建
            for k, v in user_ding.items():
                DingUser.objects.update_or_create(user_id=v['user_id'], defaults={'user_id': v['user_id'], 'ding_uid': v['ding_uid'],
                                                                                  'optional': v['optional'], 'phone_number': v['phone_number']})


if __name__ == '__main__':
    ding = DingIdAttendance()
    ding.user_optional()
