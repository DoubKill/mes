# coding: utf-8
"""项目初始化脚本"""

import os

import django
import shutil

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from system.models import User


def main():
    print('开始迁移数据库')
    apps = ('system','basics', 'plan', 'production', 'recipe')

    for app in apps:
        try:
            shutil.rmtree(f"{app}/migrations")
        except Exception:
            pass

    os.system(
        'python manage.py makemigrations {}'.format(
            ' '.join(apps)
        ))
    os.system('python manage.py migrate')

    print('创建超级管理员...')
    User.objects.create_superuser('18888888888', '123456@qq.com', '123456')


if __name__ == '__main__':
    main()
