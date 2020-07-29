# coding: utf-8
"""项目初始化脚本"""

import os

import django
import shutil

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from basics.models import GlobalCode, GlobalCodeType


def main():
<<<<<<< HEAD:add_test_data.py
    names = ['胶料状态', '产地', '原材料包装单位', '原材料类别', '胶料段次', '班组', '班次', '设备类型', '工序']
=======
    names = ['胶料状态', '产地', '原材料包装单位', '原材料类别', '胶料段次', '炼胶机类型']
>>>>>>> b7c40d82a8c3179799af7baecf5d2995d7912c35:add_test_data.py
    for i, name in enumerate(names):
        instance, _ = GlobalCodeType.objects.get_or_create(type_no=str(i+1), type_name=name, used_flag=1)
        if i == 0:
            items = ['编辑', '应用', '废弃']
        elif i == 1:
            items = ['安吉', '下沙']
        elif i == 2:
            items = ['袋', '包', '盒']
        elif i == 3:
            items = ['橡胶', '油料', '炭黑']
        elif i == 4:
            items = ['MB1', 'MB2', 'FM']
        elif i == 5:
<<<<<<< HEAD:add_test_data.py
            items = ["a班", "b班", "c班"]
        elif i == 6:
            items = ["早班", "中班", "晚班"]
        elif i == 7:
            items = ["密炼设备", "快检设备", "传送设备"]
        elif i == 8:
            items = ["一段", "二段", "三段"]
=======
            items = ['400', '500', '600']
>>>>>>> b7c40d82a8c3179799af7baecf5d2995d7912c35:add_test_data.py
        for item in items:
            GlobalCode.objects.get_or_create(global_no=str(i+1), global_name=item, global_type=instance)


if __name__ == '__main__':
    main()
