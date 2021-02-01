import json
from socket import timeout

import requests
import time
import hmac
import hashlib
import base64
import urllib.parse
from rest_framework.exceptions import ValidationError

"""
from spareparts.models import *
SpareType.objects.all().delete()
Spare.objects.all().delete()
SpareLocation.objects.all().delete()
SpareLocationBinding.objects.all().delete()
SpareInventory.objects.all().delete()
SpareInventoryLog.objects.all().delete()
"""


# url = 'https://oapi.dingtalk.com/robot/send?access_token=e789c3009a916030e74f8f740a792bd92f7c4e02f66d1ffcc3d16e35c23a5d15'
# url = 'https://oapi.dingtalk.com/robot/send?access_token=7ab5afe7f9982ac5407ec619dfb1dd6a5e2a149fd191557527f027bc131d8635'
# secret = 'SEC3c1de736eed3d8542c8116ebcea98bff51a158f7fc84fde2f4204b972ccc9706'


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
