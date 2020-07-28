# coding: utf-8
"""项目初始化脚本"""

import os

import django
import shutil

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from basics.models import GlobalCode, GlobalCodeType


def main():
    names = ['胶料状态', '产地', '原材料包装单位', '原材料类别', '胶料段次']
    for i, name in enumerate(names):
        instance = GlobalCodeType.objects.create(type_no=str(i+1), type_name=name, used_flag=1)
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
        for item in items:
            GlobalCode.objects.create(global_no=str(i+1), global_name=item, global_type=instance)


if __name__ == '__main__':
    main()
