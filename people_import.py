import os
import django
import xlrd



os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from system.models import User, GroupExtension
from django.contrib.auth.hashers import make_password


def people():
    data = xlrd.open_workbook('账户准备分厂MES人员录入名单20210330.xlsx')
    table = data.sheet_by_name('Sheet1')
    for rowNum in range(1, table.nrows):
        value = table.row_values(rowNum)
        user = User.objects.get(username=value[2])
        # group_list = []
        group_name_dict = {
            "查看权限": "查看组",
            "超级管理员": "超级管理员",
            "工艺计划维护": "工艺计划维护",
            "工艺内最高权限": "工艺管理",
            "全部最高权限": "超级管理员",
            "设备管理维护": "设备管理",
            "设备基础权限": "设备基础",
            "设备内管理最高权限": "设备管理",
            "生产基础权限": "生产基础",
            "生产内最高权限": "生产管理",
            "生产收发基础权限": "生产收发基础",
            "中控计划下发": "工艺计划维护",
            "生产计划维护": "工艺计划维护"

        }
        group_set = GroupExtension.objects.filter(name=group_name_dict.get(value[4], "查看权限"))
        # user_data = dict(
        #     username=value[2],
        #     num=int(value[1]),
        #     password=make_password(value[5]),
        # )
        # user = User.objects.create(**user_data)
        user.group_extensions.set(group_set)



if __name__ == '__main__':
    people()