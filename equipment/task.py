import datetime
import logging
import os
import sys

import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

import xlwt
from django.db.models import Q
from django.http import HttpResponse
from io import BytesIO

from mes import settings
from basics.models import WorkSchedulePlan, GlobalCode
from equipment.models import PropertyTypeNode, Property, EquipApplyOrder, EquipApplyRepair, EquipInspectionOrder
from equipment.utils import DinDinAPI, get_staff_status, get_maintenance_status
from quality.utils import get_cur_sheet, get_sheet_data
import json
from django.db.transaction import atomic

import requests
import time
import hmac
import hashlib
import base64
import urllib.parse
from rest_framework.exceptions import ValidationError

logger = logging.getLogger('send_ding_msg')


def property_template():
    """资产导入模板"""
    response = HttpResponse(content_type='application/vnd.ms-excel')
    filename = '资产导入模板'
    response['Content-Disposition'] = 'attachment;filename= ' + filename.encode('gbk').decode('ISO-8859-1') + '.xls'
    # 创建工作簿
    style = xlwt.XFStyle()
    style.alignment.wrap = 1
    ws = xlwt.Workbook(encoding='utf-8')

    # 添加第一页数据表
    w = ws.add_sheet('资产导入模板')  # 新建sheet（sheet的名称为"sheet1"）
    # for j in [1, 4, 5, 7]:
    #     first_col = w.col(j)
    #     first_col.width = 256 * 20
    # 写入表头
    w.write(0, 0, u'状态只能填三种：使用中、废弃、限制。出厂日期和使用日期格式是2020/01/01')
    w.write(1, 0, u'序号')
    w.write(1, 1, u'固定资产')
    w.write(1, 2, u'原编码')
    w.write(1, 3, u'财务编码')
    w.write(1, 4, u'设备型号')
    w.write(1, 5, u'设备编码')
    w.write(1, 6, u'设备名称')
    w.write(1, 7, u'设备制造商')
    w.write(1, 8, u'产能')
    w.write(1, 9, u'价格')
    w.write(1, 10, u'状态')
    w.write(1, 11, u'类型')
    w.write(1, 12, u'出厂编码')
    w.write(1, 13, u'出厂日期')
    w.write(1, 14, u'使用日期')

    output = BytesIO()
    ws.save(output)
    # 重新定位到开始
    output.seek(0)
    response.write(output.getvalue())
    return response


@atomic()
def property_import(file):
    """导入资产"""
    cur_sheet = get_cur_sheet(file)
    data = get_sheet_data(cur_sheet, start_row=2)
    status_dict = {'使用中': 1, '废弃': 2, '限制': 3}
    for i in data:
        ptn_obj = PropertyTypeNode.objects.filter(name=i[11], delete_flag=False).first()
        if not ptn_obj:
            raise ValidationError(f'{i[11]}资产类型不存在，请先创建此资产类型')
        status = status_dict.get(i[10], None)
        if not status:
            raise ValidationError(f'{i[10]}状态不对，请按规定填写状态')

        p_obj = Property.objects.filter(property_no=i[1], delete_flag=False).first()
        if not p_obj:
            try:
                leave_factory_date = datetime.timedelta(days=i[13])
                leave_factory_date_1 = datetime.datetime.strptime('1899-12-30', '%Y-%m-%d') + leave_factory_date
                leave_factory_date = datetime.datetime.strftime(leave_factory_date_1, '%Y-%m-%d')
                use_date = datetime.timedelta(days=i[14])
                use_date_1 = datetime.datetime.strptime('1899-12-30', '%Y-%m-%d') + use_date
                use_date = datetime.datetime.strftime(use_date_1, '%Y-%m-%d')
            except Exception as e:
                raise ValidationError('时间格式不对')
            p_obj = Property.objects.filter(property_no=i[1]).first
            if p_obj:
                Property.objects.filter(property_no=i[1]).update(src_no=i[2], financial_no=i[3], equip_type=i[4],
                                                                 equip_no=i[5],
                                                                 equip_name=i[6], made_in=i[7], capacity=i[8],
                                                                 price=i[9], status=status,
                                                                 property_type_node=ptn_obj, leave_factory_no=i[12],
                                                                 leave_factory_date=leave_factory_date,
                                                                 use_date=use_date)
            else:
                try:
                    Property.objects.create(property_no=i[1], src_no=i[2], financial_no=i[3], equip_type=i[4],
                                            equip_no=i[5],
                                            equip_name=i[6], made_in=i[7], capacity=i[8], price=i[9], status=status,
                                            property_type_node=ptn_obj, leave_factory_no=i[12],
                                            leave_factory_date=leave_factory_date, use_date=use_date)
                except Exception as e:
                    raise ValidationError('导入失败，文件格式不正确')
    return True


def send_ding_msg(url, secret, msg, isAtAll, atMobiles=None, custom=False):
    """
    url:钉钉群机器人的Webhook
    secret:钉钉群机器人安全设置-加签
    msg:需要发送的数据
    isAtAll:是否@全体人员
    atMobiles:需要@人的手机号
    """

    timestamp = str(round(time.time() * 1000))
    secret = secret
    secret_enc = secret.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    url = url + '&' + f'timestamp={timestamp}&sign={sign}'
    # 中没有headers的'User-Agent'，通常会失败。
    headers = {"Content-Type": "application/json ;charset=utf-8"}

    if atMobiles:
        if not isinstance(atMobiles, list):
            return {'errcode': 404, 'errmsg': 'atMobiles不是列表'}
    # 这里使用  文本类型
    if custom:
        data = msg
    else:
        data = {
            "msgtype": "text",
            "text": {
                "content": msg
            },
            "at": {  # @
                "atMobiles": atMobiles,  # 专门@某一个人 同时下面的isAtAll要为False
                "isAtAll": isAtAll  # 为真是@所有人
            }
        }

    try:
        r = requests.post(url, data=json.dumps(data), headers=headers, timeout=3)
        r = r.json()
    except Exception as e:
        r = {'errcode': 400, 'errmsg': '网络异常'}
    return r


"""
1、当secret填写不对时，会提示如下信息
    {'errcode': 310000, 'errmsg': 'sign not match, more: [https://ding-doc.dingtalk.com/doc#/serverapi2/qf2nxq]'}
2、当url填写不对时，会提示如下信息
    {'errcode': 300001, 'errmsg': 'token is not exist'}
3、当发送成功时，会提示如下信息
    {'errcode': 0, 'errmsg': 'ok'}
4、当想要@某人时 但是手机号填写错误或者不写时，会提示如下信息
    {'errcode': 0, 'errmsg': 'ok'}
    会变成不@人，单纯的发送信息
    返回的信息和上面发送成功一样 所以除了查看钉钉信息 无法区分是否@某人成功
    所以建议后期使用钉钉提醒功能时，文案里加上@人的名字 不然无法区分是否是普通消息还是@人失败的消息
5、当想要@某人 但是atMobiles不是列表，会提示如下信息
    {'errcode': 404, 'errmsg': 'atMobiles不是列表'}
6、当请求失败时，会提示如下信息
    {'errcode': 400, 'errmsg': '网络异常'}
"""


def export_xls(export_filed_dict, data, file_name):
    response = HttpResponse(content_type='application/vnd.ms-excel')
    filename = file_name
    response['Content-Disposition'] = u'attachment;filename= ' + filename.encode('gbk').decode(
        'ISO-8859-1') + '.xls'
    # 创建一个文件对象
    wb = xlwt.Workbook(encoding='utf8')
    # 创建一个sheet对象
    sheet = wb.add_sheet(file_name, cell_overwrite_ok=True)
    style = xlwt.XFStyle()
    style.alignment.wrap = 1

    # 写入文件标题
    for col_num in range(len(export_filed_dict)):
        sheet.write(0, col_num, list(export_filed_dict.keys())[col_num])
        # 写入数据
        data_row = 1
        for i in data:
            # sheet.write(data_row, 0, data_row)
            sheet.write(data_row, col_num, i[list(export_filed_dict.values())[col_num]])
            data_row += 1

    # 写出到IO
    output = BytesIO()
    wb.save(output)
    # 重新定位到开始
    output.seek(0)
    response.write(output.getvalue())
    return response


class AutoDispatch(object):
    """自动派单"""

    def __init__(self):
        self.ding_api = DinDinAPI()
        if settings.DEBUG:
            self.group_url = 'https://oapi.dingtalk.com/robot/send?access_token=0879c81b51a595920edcde6de87092ee050945625581b2ea7277b17d469c3bdc&timestamp=1645250492135&sign=5LyxDyNHd%2FwbM07WMCH4recxPAwWvkE1Y8EPLNF4lGU%3D'
            self.group_secret = 'SEC9e441b6498487b844cc2000ee0f94b36fdf5bf9a2b61db556c12dc9353e7e4e0'
        else:
            self.group_url = 'https://oapi.dingtalk.com/robot/send?access_token=327a481ceb5bda5e71a560c7d1e87de8aa3e7edde2038bf4379db8c8389845ab'
            self.group_secret = 'SECf1842042def9a33612e3b7f064819033d2b5215d18deca79b14b3b1101d26081'

    def send_order(self, order):
        # 提醒消息里的链接类型 False 非巡检  True 巡检
        inspection = False
        section_name = ''
        now_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if order.work_type != '巡检':
            # 班组
            group = self.get_group_info()
            # 设备部门下改班组人员
            instance = GlobalCode.objects.filter(global_type__type_name='设备部门组织名称', use_flag=1,
                                                 global_type__use_flag=1).first()
            section_name = instance.global_name if instance else section_name
            choice_all_user = get_staff_status(DinDinAPI(), section_name, group=group) if section_name else []
            fault_name = order.result_fault_cause if order.result_fault_cause else (
                order.equip_repair_standard.standard_name if order.equip_repair_standard else order.equip_maintenance_standard.standard_name)
        else:
            # 查询巡检单是否有部分已经分派了
            part_order = EquipInspectionOrder.objects.filter(plan_id=order.plan_id, assign_to_user__isnull=False).first()
            if part_order:
                order.assign_user = '系统自动'
                order.assign_datetime = now_date
                order.assign_to_user = part_order.assign_to_user
                order.status = '已指派'
                order.last_updated_date = now_date
                order.save()
            inspection = True
            # 查询工单对应的包干人员[上班并且有空]
            choice_all_user = get_maintenance_status(self.ding_api, order.equip_no, order.equip_repair_standard.type)
            fault_name = order.equip_repair_standard.standard_name
        if not choice_all_user:
            logger.info(f'系统派单[{order.work_type}]: {order.work_order_no}-无人员可派单')
            return f'系统派单[{order.work_type}]: {order.work_order_no}-无人员可派单'
        working_persons = [i for i in choice_all_user if i['optional']]
        if order.work_type != '巡检':
            data = [i for i in choice_all_user if i.get('section_name') == section_name]
            leader_phone_number = '' if not data else data[0].get('leader_phone_number')
        else:
            leader_phone_number = choice_all_user[0].get('leader_phone_number')
        leader_ding_uid = self.ding_api.get_user_id(leader_phone_number)
        # 消息模板
        content = {
            "title": "",
            "form": [{"key": "工单编号:", "value": order.work_order_no},
                     {"key": "机台:", "value": order.equip_no},
                     {"key": "故障原因:", "value": fault_name},
                     {"key": "重要程度:", "value": order.importance_level},
                     {"key": "指派人:", "value": "系统自动"},
                     {"key": "指派时间:", "value": now_date}]}
        if not working_persons:
            # 发送消息给上级
            content.update({'title': f"系统派单: 无空闲可指派人员！"})
            logger.info(f'系统派单[{order.work_type}]: {order.work_order_no}-无空闲可指派人员')
            return [order.work_type, leader_ding_uid]
        processing_person = []
        for per in working_persons:
            if order.work_type != '巡检':
                processing_order = EquipApplyOrder.objects.filter(~Q(result_repair_final_result='等待'), status='已开始',
                                                                  repair_user__icontains=per['username'])
            else:
                processing_order = EquipInspectionOrder.objects.filter(status='已开始', repair_user__icontains=per['username'])
            if processing_order:
                processing_person.append(per)
                continue
            # 分派维修单
            order.assign_user = '系统自动'
            order.assign_datetime = now_date
            order.assign_to_user = per['username']
            order.status = '已指派'
            order.last_updated_date = now_date
            order.save()
            # 更新设备计划状态
            if order.work_type == '维修':
                repair_instance = EquipApplyRepair.objects.filter(plan_id=order.plan_id).first()
                if repair_instance:
                    repair_instance.status = '已指派'
                    repair_instance.last_updated_date = now_date
                    repair_instance.save()
            # 派单成功发送钉钉消息给当班人员
            content.update({'title': f"系统自动派发{order.work_type}工单成功，请尽快处理！"})
            self.ding_api.send_message([per.get('ding_uid')], content, order_id=order.id, inspection=inspection)
            # 派单成功发送消息到设备群聊
            message_url = f"eapp://pages/repairOrder/repairOrder?id={order.id}" + ("&isInspection=true" if inspection else "") + "&isView=1"
            msg_to_group = {
                "msgtype": "link",
                "link": {
                    "text": f"系统自动派发设备工单成功，请尽快处理！\n工单编号:{order.work_order_no}\n机台:{order.equip_no}\n故障原因:{fault_name}\n重要程度:{order.importance_level}\n指派人:系统自动\n被指派人:{per['username']}\n指派时间:{now_date}",
                    "title": "系统自动派发设备工单成功，请尽快处理！",
                    "picUrl": "",
                    "messageUrl": message_url
                }
            }
            url = self.get_group_url()
            send_ding_msg(url=url, secret=self.group_secret, msg=msg_to_group, isAtAll=False)
            logger.info(f"系统派单[{order.work_type}]-系统自动派单成功: {order.work_order_no}, 被指派人:{per['username']}")
            continue

        if len(processing_person) == len(working_persons):
            # 所有人都在忙, 派单失败, 钉钉消息推送给上级
            content.update({'title': f"所有人员均有工单在处理, 系统自动派单失败！"})
            logger.info(f'系统派单[{order.work_type}]: 系统自动派单失败: {order.work_order_no}, 可选人员:{working_persons}, 正在维修人员:{processing_person}')
            return [order.work_type, leader_ding_uid]
        return f'系统派单[{order.work_type}]: 完成一次定时派单处理'

    def get_group_info(self):
        now_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        group = '早班' if '08:00:00' < now_date[11:] < '20:00:00' else '夜班'
        record = WorkSchedulePlan.objects.filter(plan_schedule__day_time=now_date[:10], classes__global_name=group,
                                                 plan_schedule__work_schedule__work_procedure__global_name='密炼').first()
        return record.group.global_name

    def get_group_url(self):
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.group_secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, self.group_secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return f"{self.group_url}&timestamp={timestamp}&sign={sign}"


if __name__ == '__main__':
    auto_dispatch = AutoDispatch()
    repair_orders = list(EquipApplyOrder.objects.filter(status='已生成', back_order=False))
    inspect_order = list(EquipInspectionOrder.objects.filter(status='已生成', back_order=False))
    orders = repair_orders + inspect_order
    if not orders:
        logger.info("系统派单: 没有新生成的工单可派")
    failed = {}  # {ding_uid: {维修: 4, 巡检: 7}}
    for order in orders:
        res = auto_dispatch.send_order(order)
        if isinstance(res, list):
            work_type, leader_ding_uid = res
            if not leader_ding_uid:
                continue
            if leader_ding_uid in failed:
                statics = failed[leader_ding_uid]
                statics[work_type] = statics[work_type] + 1 if work_type in statics else 1
            else:
                failed[leader_ding_uid] = {work_type: 1}
    if failed:
        for leader_ding_uid, total_error_msg in failed.items():
            send_msg_content = ''
            for work_type, num in total_error_msg.items():
                send_msg_content += f'{work_type}: {num}'
            now_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            content = {"title": f"单据派单失败, 请及时查看: {send_msg_content}"}
            auto_dispatch.ding_api.send_message([leader_ding_uid], content)

