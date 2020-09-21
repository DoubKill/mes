# coding: utf-8
"""项目初始化脚本"""

import os

import django
import shutil

from django.db.transaction import atomic

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from system.models import User, Permissions

permission_data = [
        {'id': 1, 'code': 'global_types', 'name': '公共代码管理', 'parent_id': None},
        {'id': 2, 'code': 'view_global_types', 'name': '查看', 'parent_id': 1},
        {'id': 3, 'code': 'add_global_types', 'name': '增加', 'parent_id': 1},
        {'id': 4, 'code': 'change_global_types', 'name': '修改', 'parent_id': 1},
        {'id': 5, 'code': 'delete_global_types', 'name': '启用/停用', 'parent_id': 1},
        {'id': 6, 'code': 'groups', 'name': '角色管理', 'parent_id': None},
        {'id': 7, 'code': 'view_groups', 'name': '查看', 'parent_id': 6},
        {'id': 8, 'code': 'add_groups', 'name': '增加', 'parent_id': 6},
        {'id': 9, 'code': 'change_groups', 'name': '修改', 'parent_id': 6},
        {'id': 10, 'code': 'delete_groups', 'name': '启用/停用', 'parent_id': 6},
        {'id': 11, 'code': 'users', 'name': '用户管理', 'parent_id': None},
        {'id': 12, 'code': 'view_users', 'name': '查看', 'parent_id': 11},
        {'id': 13, 'code': 'add_users', 'name': '增加', 'parent_id': 11},
        {'id': 14, 'code': 'change_users', 'name': '修改', 'parent_id': 11},
        {'id': 15, 'code': 'delete_users', 'name': '启用/停用', 'parent_id': 11},
        {'id': 16, 'code': 'group-users', 'name': '角色别用户管理', 'parent_id': None},
        {'id': 17, 'code': 'view_group-users', 'name': '查看', 'parent_id': 16},
        {'id': 18, 'code': 'add_group-users', 'name': '修改', 'parent_id': 16}
    ]


@atomic()
def init_permissions():
    for item in permission_data:
        Permissions.objects.create(**item)


def main():
    print('开始迁移数据库')
    apps = ('system', 'basics', 'plan', 'production', 'recipe')

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
    init_permissions()


if __name__ == '__main__':
    main()
