import base64
import datetime
import hashlib
import hmac
import os
import time
import urllib

import requests

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from django.db.models import Sum, Max

from plan.models import ProductClassesPlan
from production.models import TrainsFeedbacks

factory_date = datetime.datetime.now().date() - datetime.timedelta(days=1)
plan_set = ProductClassesPlan.objects.filter(
        work_schedule_plan__plan_schedule__day_time=factory_date,
        delete_flag=False)
plan_data = plan_set.values('equip__equip_no').annotate(plan_num=Sum('plan_trains'))
plan_uid = plan_set.values_list("plan_classes_uid", flat=True)
max_ids = TrainsFeedbacks.objects.filter(plan_classes_uid__in=plan_uid)\
    .values('plan_classes_uid').annotate(max_id=Max('id')).values_list('max_id', flat=True)
ret_set = TrainsFeedbacks.objects.filter(id__in=max_ids).values("equip_no").\
    annotate(plan_sum=Sum('plan_trains'), actual_sum=Sum('actual_trains')).order_by("equip_no").\
    values("equip_no", "plan_sum", "actual_sum")
mk_str = "\n - \n计划车次/实际车次"
for temp in ret_set:
    mk_str += f"""\n - {temp.get('equip_no')}:\t{temp.get('plan_sum')}/{temp.get('actual_sum')}"""
mk_str += "\n"
now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
# data = "\n - Z01:\t100/99\n - Z02:\t100/99\n - Z03:\t100/99\n - Z04:\t100/99\n - Z05:\t100/99\n\n"
message = {
    "msgtype": "markdown",
    "markdown": {
        "title": "密炼机台产量通知（车）",
        "text": f"#### 密炼机台产量统计（车） {mk_str}> ![screenshot](https://img.alicdn.com/tfs/TB1NwmBEL9TBuNjy1zbXXXpepXa-2400-1218.png)\n> ###### {now_time}发布 [mes](http://10.4.10.54) \n"
    },
    "at": {
    "atMobiles": [
    "15058301792"
    ],
    "isAtAll": True
    }
}

def send_ding_msg(msg="产量", isAtAll=True, atMobiles=None,
                  url="https://oapi.dingtalk.com/robot/send?access_token=7ab5afe7f9982ac5407ec619dfb1dd6a5e2a149fd191557527f027bc131d8635",
                  secret="SEC3c1de736eed3d8542c8116ebcea98bff51a158f7fc84fde2f4204b972ccc9706"):
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
    # # 这里使用  文本类型
    # data = {
    #     "msgtype": "text",
    #     "text": {
    #         "content": msg
    #     },
    #     "at": {  # @
    #         "atMobiles": atMobiles,  # 专门@某一个人 同时下面的isAtAll要为False
    #         "isAtAll": isAtAll  # 为真是@所有人
    #     }
    # }

    try:
        r = requests.post(url, json=message, headers=headers, timeout=3)
        r = r.json()
    except Exception as e:
        r = {'errcode': 400, 'errmsg': '网络异常'}
    return r


if __name__ == '__main__':
    send_ding_msg()