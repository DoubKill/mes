import datetime
import os

import xlrd
import xlwt
from django.http import HttpResponse
from io import BytesIO

from rest_framework.exceptions import ValidationError

from equipment.models import PropertyTypeNode, Property
from quality.utils import get_cur_sheet, get_sheet_data
import json
from socket import timeout

import requests
import time
import hmac
import hashlib
import base64
import urllib.parse
from rest_framework.exceptions import ValidationError

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
            try:
                Property.objects.create(property_no=i[1], src_no=i[2], financial_no=i[3], equip_type=i[4],
                                        equip_no=i[5],
                                        equip_name=i[6], made_in=i[7], capacity=i[8], price=i[9], status=status,
                                        property_type_node=ptn_obj, leave_factory_no=i[12],
                                        leave_factory_date=leave_factory_date, use_date=use_date)
            except Exception as e:
                raise ValidationError('导入失败，请检查文件格式')
    return True

def send_ding_msg(url, secret, msg, isAtAll, atMobiles=None):
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
        r = {'errcode': 400, 'errmsg': '网络错误'}
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
"""
