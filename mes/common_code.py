import decimal
import json
import time
import uuid
from calendar import timegm
from io import BytesIO

import pymssql
import requests
import xlwt
from DBUtils.PooledDB import PooledDB
from django.contrib.auth.backends import ModelBackend
from django.db.models import Min, Max, Sum, Q
from django.http import HttpResponse
from rest_framework import status, mixins
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from datetime import date, timedelta, datetime

from mes.conf import BZ_HOST, BZ_USR, BZ_PASSWORD
from system.models import User, Permissions, ChildSystemInfo
from rest_framework import status as rf_status
import logging

from rest_framework_jwt.compat import get_username
from rest_framework_jwt.compat import get_username_field
from rest_framework_jwt.settings import api_settings


logger = logging.getLogger("send_log")


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

    @property
    def raw_permissions(self):
        permissions = []
        for group in self.group_extensions.all():
            group_permissions = list(group.permissions.values_list('code', flat=True))
            permissions.extend(group_permissions)
        return permissions


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


def date_range(start, end):
    """获取两个日期之间的所有日期"""
    delta = end - start  # as timedelta
    days = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(delta.days + 1)]
    return days


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


class OSum(Sum):

    def as_oracle(self, compiler, connection):
        # if self.output_field.get_internal_type() == 'DurationField':
        expression = self.get_source_expressions()[0]
        from django.db.backends.oracle.functions import IntervalToSeconds, SecondsToInterval
        return compiler.compile(
            SecondsToInterval(Sum(IntervalToSeconds(expression), filter=self.filter))
        )


class OMax(Max):
    def as_oracle(self, compiler, connection):
        # if self.output_field.get_internal_type() == 'DurationField':
        expression = self.get_source_expressions()[0]
        from django.db.backends.oracle.functions import IntervalToSeconds, SecondsToInterval
        return compiler.compile(
            SecondsToInterval(Max(IntervalToSeconds(expression), filter=self.filter))
        )


class OMin(Min):
    def as_oracle(self, compiler, connection):
        # if self.output_field.get_internal_type() == 'DurationField':
        expression = self.get_source_expressions()[0]
        from django.db.backends.oracle.functions import IntervalToSeconds, SecondsToInterval
        return compiler.compile(
            SecondsToInterval(Min(IntervalToSeconds(expression), filter=self.filter))
        )


class WebService(object):
    client = requests.request
    url = "http://{}:9000/小料称量"

    @classmethod
    def issue(cls, data, category, method="post", equip_no=6, equip_name="收皮终端"):
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'http://tempuri.org/INXWebService/{}'
        }

        child_system = ChildSystemInfo.objects.filter(system_name=f"{equip_name}{equip_no}").first()
        recv_ip = child_system.link_address
        url = cls.url.format(recv_ip)
        headers['SOAPAction'] = headers['SOAPAction'].format(category)
        body = cls.trans_dict_to_xml(data, category)
        rep = cls.client(method, url, headers=headers, data=body, timeout=5)
        # print(rep.text)
        if rep.status_code < 300:
            return True, rep.text
        elif rep.status_code == 500:
            logger.error(rep.text)
            return False, rep.text
        else:
            return False, rep.text

    # dict数据转soap需求xml
    @staticmethod
    def trans_dict_to_xml(data, category):
        """
        将 dict 对象转换成微信支付交互所需的 XML 格式数据

        :param data: dict 对象
        :return: xml 格式数据
        """

        xml = []
        for k in data.keys():
            v = data.get(k)
            if k == 'detail' and not v.startswith('<![CDATA['):
                v = '<![CDATA[{}]]>'.format(v)
            xml.append('<{key}>{value}</{key}>'.format(key=k, value=v))
        res = """<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"> <s:Body>
                    <{} xmlns="http://tempuri.org/">
                       {}
                    </{}>
                </s:Body>
                </s:Envelope>""".format(category, ''.join(xml), category)
        res = res.encode("utf-8")
        return res


def get_template_response(titles: list, filename="", description=""):
    """
    :param titles: 表头
    :param filename: 模板名
    :param description: 第一行的模板描述及备注
    :return: 模板对象
    """
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment;filename= ' + filename.encode('gbk').decode('ISO-8859-1') + '.xls'
    # 创建工作簿
    style = xlwt.XFStyle()
    style.alignment.wrap = 1
    ws = xlwt.Workbook(encoding='utf-8')
    # 添加第一页数据表
    w = ws.add_sheet(filename)
    target = 0
    if description:
        target += 1
        w.write(0, 0, description)
    for x in titles:
        w.write(target, titles.index(x), x)
    output = BytesIO()
    ws.save(output)
    # 重新定位到开始
    output.seek(0)
    response.write(output.getvalue())
    return response


class UsernameMobileAuthBackend(ModelBackend):
    """用户名或工号登录"""

    def authenticate(self, request, username=None, password=None, **kwargs):
        """判断用户名、工号和密码是否正确"""
        query_set = User.objects.filter(Q(username=username) | Q(num=username))
        try:
            if query_set.exists():
                user = query_set.get()
                if user.check_password(password):
                    return user
        except:
            return None
        return None


def zdy_jwt_payload_handler(user):
    username_field = get_username_field()
    username = get_username(user)

    payload = {
        'user_id': user.pk,
        'username': username,
        'exp': datetime.utcnow() + timedelta(days=365)  # 此处设置过期时间为一年
    }
    if hasattr(user, 'email'):
        payload['email'] = user.email
    if isinstance(user.pk, uuid.UUID):
        payload['user_id'] = str(user.pk)

    payload[username_field] = username

    # Include original issued at time for a brand new token,
    # to allow token refresh
    if api_settings.JWT_ALLOW_REFRESH:
        payload['orig_iat'] = timegm(
            datetime.utcnow().utctimetuple()
        )

    if api_settings.JWT_AUDIENCE is not None:
        payload['aud'] = api_settings.JWT_AUDIENCE

    if api_settings.JWT_ISSUER is not None:
        payload['iss'] = api_settings.JWT_ISSUER

    return payload
