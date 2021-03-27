import decimal
import json
import time

import pymssql
from DBUtils.PooledDB import PooledDB
from rest_framework import status, mixins
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.reverse import reverse

from datetime import date, timedelta, datetime

from mes.conf import BZ_HOST, BZ_USR, BZ_PASSWORD
from mes.permissions import PermissonsDispatch
from system.models import User, Permissions
from rest_framework import status as rf_status


# 启用-》禁用    禁用-》启用
class CommonDeleteMixin(object):
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.use_flag:
            instance.use_flag = 0
        else:
            instance.use_flag = 1
        instance.last_updated_user = request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SyncCreateMixin(mixins.CreateModelMixin):
    # 创建时需记录同步数据的接口请继承该创建插件
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        setattr(response, "model_name", self.queryset.model.__name__)
        return response


class SyncUpdateMixin(mixins.UpdateModelMixin):
    # 更新时需记录同步数据的接口请继承该更新插件
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        setattr(response, "model_name", self.queryset.model.__name__)
        return response


class UserFunctions(object):
    """
    针对User类进行扩展
    """

    @property
    def group_list(self):
        """
        获取用户现在所属角色列表
        :return: list
        """
        return list(self.groups.values_list('name', flat=True))

    @property
    def permissions_list(self):
        """
        获取用户所有权限id
        :return: 权限id列表
        """
        permissions = {}
        permission_ids = []
        for group in self.group_extensions.all():
            permission_ids += list(group.permissions.values_list('id', flat=True))
        parent_permissions = Permissions.objects.filter(parent__isnull=True)
        for perm in parent_permissions:
            queryset = perm.children_permissions.all()
            if not self.is_superuser:
                queryset = queryset.filter(id__in=set(permission_ids))
            codes = [item.split('_')[0] for item in queryset.values_list('code', flat=True)]
            permissions[perm.code] = codes
        return permissions

    def model_permission(self, model_name):
        """
        获取用户关于具体一个model的权限
        :param model_name:
        :return:
        """
        return self.get_all_permissions()


User.__bases__ += (UserFunctions,)


def days_cur_month_dates():
    """获取当月所有日期列表"""
    m = datetime.now().month
    y = datetime.now().year
    days = (date(y, m + 1, 1) - date(y, m, 1)).days
    d1 = date(y, m, 1)
    d2 = date(y, m, days)
    delta = d2 - d1
    return [(d1 + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(delta.days + 1)]


def get_weekdays(days):
    """获取当前日期往前n天的日期"""
    date_list = []
    for i in range(days):
        date_list.append((timedelta(days=-i) + datetime.now()).strftime("%Y-%m-%d"))
    return date_list[::-1]


class SqlClient(object):
    """默认是连接sqlserver的客户端"""

    def __init__(self, host=BZ_HOST, user=BZ_USR, password=BZ_PASSWORD,
                 sql="SELECT *, Row_Number() OVER (order  by 库存索引) id FROM v_ASRS_STORE_MESVIEW", database=None):
        if database:
            pool = PooledDB(pymssql, database=database,
                            mincached=5, maxcached=10, maxshared=5, maxconnections=10, blocking=True,
                            maxusage=100, setsession=None, reset=True, host=host,
                            user=user, password=password
                            )
        else:
            pool = PooledDB(pymssql,
                            mincached=5, maxcached=10, maxshared=5, maxconnections=10, blocking=True,
                            maxusage=100, setsession=None, reset=True, host=host,
                            user=user, password=password
                            )
        conn = pool.connection()
        cursor = conn.cursor()
        self.sql = sql
        self.conn = conn
        self.cursor = cursor

    def all(self):
        self.cursor.execute(self.sql)
        self.data = self.cursor.fetchall()
        return self.data

    def first(self):
        self.cursor.execute("select top 1 * from v_ASRS_STORE_MESVIEW")
        self.data = self.cursor.fetchone()
        return self.data

    def count(self, sql="select count(*) as count from v_ASRS_STORE_MESVIEW"):
        self.cursor.execute(sql)
        self.data = self.cursor.fetchone()
        return self.data[0]

    def close(self):
        self.conn.close()
        self.cursor.close()


def order_no():
    return time.strftime("%Y%m%d%H%M%S")


class DecimalEncoder(json.JSONEncoder):
    """将Decimal类型转成float类型"""

    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)

        super(DecimalEncoder, self).default(o)


def response(success, data=None, message=None):
    info = {
            'success': success,
            'message': message,
            'data': data
        }
    return Response(data=info, status=rf_status.HTTP_200_OK)


class TerminalCreateAPIView(CreateAPIView):

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return response(
                success=False,
                message=list(serializer.errors.values())[0][0])  # 只返回一条错误信息
        self.perform_create(serializer)
        return response(success=True)


class MesPermisson(BasePermission):

    def method_map(self, method):
        mapper = {
            "get": "view",
            "post": "add",
            "put": "change",
            "delete": "delete",
            "patch": "change"
        }
        return mapper.get(method)


    def has_permission(self, request, view):
        try:
            model_name = view.queryset.model.__name__.lower()
        except Exception as e:
            print(e)
            return True
        method = request.Method.lower()
        operation = self.method_map(method)
        permissions = request.user.permissions_list
        permissions = [x.lower() for x in permissions]
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return True

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return True

