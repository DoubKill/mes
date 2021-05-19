import decimal
import json
import time
from io import BytesIO

import pymssql
import requests
import xlwt
from DBUtils.PooledDB import PooledDB
from django.db.models import Min, Max, Sum
from django.db.transaction import atomic
from django.http import HttpResponse
from rest_framework import status, mixins
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.reverse import reverse
from suds.client import Client
from datetime import date, timedelta, datetime

from mes.conf import BZ_HOST, BZ_USR, BZ_PASSWORD
from plan.models import BatchingClassesPlan
from recipe.models import ProductBatching
from system.models import User, Permissions, ChildSystemInfo
from rest_framework import status as rf_status
import logging

from terminal.models import WeightTankStatus, RecipePre, RecipeMaterial, Plan, Bin

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


class INWeighSystem(object):
    equip_no_ip = {
        "F01": "192.168.1.131",
        "F02": "192.168.1.131",
        "F03": "192.168.1.131",
        "S01": "192.168.1.131",
        "S02": "192.168.1.131",
    }

    def __init__(self, equip_no: str):
        self.weigh_system = Client(f"http://{self.equip_no_ip.get(equip_no, '192.168.1.131')}:9000/xlserver?wsdl")

    def stop(self, data):
        """

        :param data: stop_data = {
                        "plan_no": "210517091223",  # 计划操作编号
                        "action": "1",  # 具体计划的操作方式
                    }
        :return:
        """
        stop_plan = self.weigh_system.service.stop_plan(*data.values())  # 停止计划
        return stop_plan

    def door_info(self, data):
        """

        :param data:  door_info = {
                        "开门信号1": "1",   # 称量系统 A料仓 1~11  例开A6号料仓门传"6"
                        "开门信号2": "2"    # 称量系统 B料仓 1~11  例开B6号料仓门传"6"
                    }
        :return:
        """
        door_info = self.weigh_system.service.open_door(*data.values())  # 开门信号及料仓信号反馈
        return door_info

    def update_trains(self, data):
        """
        :param data: update_trains = {
                        "plan_no": "210517091223",  # 计划操作编号
                        "action": "1",               # 具体计划的操作方式
                        "num": 122                  # 需修改的车次
                    }
        :return:
        """
        update_trains = self.weigh_system.service.update_num(*data.values())  # 更新计划车次
        return update_trains

    def reload_plan(self, data):
        """

        :param data: reload_data = {
                        "plan_no": "210517091223",  # 计划操作编号
                        "action": "1",  # 具体计划的操作方式
                    }
        :return:
        """
        reload_plan = self.weigh_system.service.reload_plan(*data.values())  # 重传计划/配方
        return reload_plan


class TankStatusSync(INWeighSystem):

    def __init__(self, equip_no: str):
        self.queryset = WeightTankStatus.objects.using(equip_no).filter(equip_no=equip_no)
        self.equip_no = equip_no
        super(TankStatusSync, self).__init__(equip_no)

    @atomic
    def sync(self):
        req_data = {
            "开门信号1": "0",  # 称量系统 A料仓 1~11  例开A6号料仓门传"6"，传0表示只查不改变料门信息
            "开门信号2": "0"  # 称量系统 B料仓 1~11  例开B6号料仓门传"6"，传0表示只查不改变料门信息
        }
        rep_json = self.door_info(req_data)
        data = json.loads(rep_json)
        for x in self.queryset:
            temp_no = x.tank_no
            # 万龙表里的罐号跟接口里的罐号不一致，需要做个转换
            if len(temp_no) == 3:
                tank_no = temp_no[1:3] + temp_no[:1]
            else:
                tank_no = temp_no[::-1]
            high_level = tank_no + "_high_level"
            low_level = tank_no + "_low_level"
            material_name = tank_no + "_name"
            door_status = tank_no + "_door"
            x.open_flag = False if data.get(door_status, True) else True
            # 高位有料表示高位报警
            if data[high_level]:
                x.status = 2
            # 低位有料表示地位报警
            if not data[low_level]:
                x.status = 1
            # 其余表示正常
            x.status = 3
            x.material_name = data[material_name]
            x.material_no = data[material_name]
            x.save()


# @atomic()
def issue_recipe(recipe_no, equip_no):
    recipe = ProductBatching.objects.exclude(used_type=6).filter(stage_product_batch_no=recipe_no,
                                                                 dev_type__isnull=False, batching_type=2).last()
    weigh_recipe_name = f"{recipe.stage_product_batch_no}({recipe.dev_type.category_no})"
    time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    temp = recipe.weight_cnt_types.filter(delete_flag=False, package_type=1).last()
    weight = temp.weight_details.filter(delete_flag=False).aggregate(total_weight=Sum('standard_weight'))[
        'total_weight'] if temp else 0
    error = temp.weight_details.filter(delete_flag=False).aggregate(total_error=Sum('standard_error'))[
        'total_error'] if temp else 0
    default = {
        "ver": recipe.versions,
        "remark1": recipe.dev_type.category_no,
        "weight": weight,
        "error": error,
        "time": time_now,
        "use_not": 0 if recipe.used_type == 4 else 1
    }
    RecipePre.objects.using(equip_no).update_or_create(defaults=default, **{
        "name": weigh_recipe_name})
    weigh_details = temp.weight_details.filter(delete_flag=False) if temp else []
    weigh_data_list = [
        RecipeMaterial(recipe_name=weigh_recipe_name, name=x.material.material_name, weight=x.standard_weight,
                       error=x.standard_error, time=time_now) for x in weigh_details]
    RecipeMaterial.objects.using(equip_no).filter(recipe_name=weigh_recipe_name).delete()
    RecipeMaterial.objects.using(equip_no).bulk_create(weigh_data_list)


# @atomic()
def issue_plan(plan_no : str, equip_no : str, username: str="mes") -> str:
    plan = BatchingClassesPlan.objects.filter(plan_batching_uid=plan_no).last()
    time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    weigh_recipe_name = f"{plan.weigh_cnt_type.product_batching.stage_product_batch_no}({plan.weigh_cnt_type.product_batching.dev_type.category_no})"
    default = {
        "recipe": weigh_recipe_name,
        "recipe_ver": plan.weigh_cnt_type.product_batching.versions,
        "starttime": time_now,
        "grouptime": plan.work_schedule_plan.classes.global_name,
        "oper": username,
        "state": "等待",
        "setno": plan.plan_package,
        "actno": 0,
        "order_by": 1,
        "date_time": plan.work_schedule_plan.plan_schedule.day_time.strftime('%Y-%m-%d'),
        "addtime": time_now
    }
    instance, flag = Plan.objects.using(equip_no).get_or_create(defaults=default, **{
        "planid": plan_no})
    if flag == False:
        return "配料计划已下达"
    return "配料计划下达成功"


@atomic()
def sync_tank(equip_no):
    queryset = WeightTankStatus.objects.filter(equip_no=equip_no)
    # 建议料罐表里增加条码字段
    for x in queryset:
        tank_no = x.get("tank_no")
        default = {
            "name": x.get("material_name"),
            "code": x.get("barcode")
        }
        Bin.objects.using(equip_no).update_or_create(default=default, **{"bin": tank_no})