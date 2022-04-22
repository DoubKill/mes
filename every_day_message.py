import base64
import datetime
import hashlib
import hmac
import logging
import os
import time
import urllib

import requests

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from system.models import User
from mes import settings
from django.db.models import Sum, Count

from plan.models import ProductClassesPlan
from production.models import TrainsFeedbacks
from basics.models import Equip, PlanSchedule, GlobalCode

logger = logging.getLogger('send_log')


def product_day_message():
    # 日产量数据统计并转换成钉钉通知数据
    end_date = datetime.datetime.now().date()
    factory_date = datetime.datetime.now().date() - datetime.timedelta(days=1)
    time_str_start = " 08:00:00"
    time_str_end = " 07:59:59"

    plan_data = dict(ProductClassesPlan.objects.filter(
        work_schedule_plan__plan_schedule__day_time=factory_date,
        delete_flag=False).values('equip__equip_no').annotate(plan_num=Sum('plan_trains')).values_list('equip__equip_no', 'plan_num'))
    actual_data = dict(TrainsFeedbacks.objects.filter(
        factory_date=factory_date).values('equip_no').annotate(actual_sum=Count('id')).values_list('equip_no', 'actual_sum'))

    equip_list = list(Equip.objects.filter(category__equip_type__global_name="密炼设备").order_by('equip_no').values_list("equip_no", flat=True))
    plan_list = []
    actual_list = []
    mk_str = f"统计时间: {factory_date.strftime('%Y-%m-%d') + time_str_start} -> {end_date.strftime('%Y-%m-%d') + time_str_end}\n - 计划车数/实际车数"

    for equip_no in equip_list:
        plan_list.append(plan_data.get(equip_no, 0))
        actual_list.append(actual_data.get(equip_no, 0))
        mk_str += f"""\n - {equip_no}:\t{plan_data.get(equip_no, 0)}/{actual_data.get(equip_no, 0)}"""
    plan_all = sum(plan_list)
    actual_all = sum(actual_list)
    mk_str += f"\n - 日计划量/生产量: {plan_all}/{actual_all} \n"
    now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # data = "\n - Z01:\t100/99\n - Z02:\t100/99\n - Z03:\t100/99\n - Z04:\t100/99\n - Z05:\t100/99\n\n"
    from pyecharts.charts import Bar
    from pyecharts import options as opts

    # 导入输出图片工具
    # from pyecharts.render import make_snapshot
    # from snapshot_phantomjs import snapshot
    # 创建一个柱状图Bar实例

    bar = (
        Bar()
            # .set_colors(colors="#FFDEAD")
            # 添加X轴数据
            .add_xaxis(equip_list)
            # 添加Y轴数据,系列的名称
            .add_yaxis('计划车数', plan_list, color="#FF6600")
            .add_yaxis('实际车数', actual_list, color="#87CEFA")
            # 添加标题

            .set_global_opts(title_opts=opts.TitleOpts(title="各机台生产情况",
                                                       subtitle=f"{factory_date.strftime('%Y-%m-%d') + time_str_start} -> {end_date.strftime('%Y-%m-%d') + time_str_end}"))
    )
    bar.render(path="index.html")
    # # 输出保存为图片
    # make_snapshot(snapshot, "D:\index.html", "D:\index.gif", pixel_ratio=1)
    # bar = Bar("各机台生产情况", f"{factory_date.strftime('%Y-%m-%d') + time_str} -> {end_date.strftime('%Y-%m-%d') + time_str}")
    # bar.add('计划车数', equip_list, plan_list, mark_point=['average']) # 标记点：商家1的平均值
    # bar.add('实际车数', equip_list, actual_list ,mark_line=['min', 'max']) # 标记线：商家2的最小/大值
    # with open(r"D:\index.gif", 'rb') as f:
    #     base64_data = base64.b64encode(f.read())
    #     s = base64_data.decode()
    text = f"# 密炼机台产量统计(车)\n\n{mk_str} > [[数据可视化]](http://10.4.10.54/data/)\n\n**发布时间:{now_time}** [[mes]](http://10.4.10.54/)"
    message = {
        "msgtype": "markdown",
        "markdown": {
            "title": "每日通知",
            "text": text
        },
        "at": {
            "atMobiles": [],
            "isAtAll": True
        }
    }
    return message


def equip_errors():
    text = f"# 设备故障统计\n\n > [[设备故障日报表]](http://10.4.10.54/#/phone/fault-day-statistics)\n\n > [[设备故障周报表]](http://10.4.10.54/#/phone/fault-week-statistics)\n\n > [[设备故障月报表]](http://10.4.10.54/#/phone/fault-month-statistics)"
    message = {
        "msgtype": "markdown",
        "markdown": {
            "title": "设备故障率统计",
            "text": text
        },
        "at": {
            "atMobiles": [],
            "isAtAll": True
        }
    }
    return message


def send_ding_msg(data=None, isAtAll=True, atMobiles=None,
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
    # dx = json.dumps(message).encode("utf8")
    try:
        r = requests.post(url, json=data, headers=headers, timeout=3)
        r = r.json()
    except Exception as e:
        r = {'errcode': 400, 'errmsg': f'网络异常:{e}'}
    return r


def check_classes():
    limit_date = datetime.datetime.now().date() + datetime.timedelta(days=7)
    already_classes = PlanSchedule.objects.filter(delete_flag=False, day_time__gte=limit_date)
    message = ''
    if not already_classes:  # 提醒排班
        # 获取人员信息
        user_name_list = set(GlobalCode.objects.filter(delete_flag=False, global_type__use_flag=True, global_type__type_name='未排班提醒').values_list('global_name', flat=True))
        users = User.objects.filter(is_active=True, username__in=user_name_list)
        phones = list(users.values_list('phone_number', flat=True))
        message = {
            "msgtype": "markdown",
            "markdown": {
                "title": "每日mes排班检查",
                "text": ("" if not phones else " ".join([f"@{i}" for i in phones]) + "\n\n") + "最新排班日期距今天已不足7日, 请尽快登录mes系统处理"
            },
            "at": {
                "atMobiles": phones,
                "isAtAll": False if phones else True
            }
        }
        logger.info('发送排班提醒成功')
    else:
        logger.info('排班周期充足')
    return message


if __name__ == '__main__':
    # 产量通知
    message = product_day_message()
    # 设备故障统计通知
    equip_message = equip_errors()
    # 检查排班
    class_message = check_classes()
    if settings.DEBUG:
        send_ding_msg(data=message, url='https://oapi.dingtalk.com/robot/send?access_token=3daeb8d9276b40e29fdba4b6578e39af6c860a7be0f8c75d55040a0bad57aad4', secret='SEC6ac31d2d123d02e32b221f49605f96b8ebeb2e9c5d4776b86c3d49c211fdd6a2')
        send_ding_msg(data=equip_message, url='https://oapi.dingtalk.com/robot/send?access_token=3daeb8d9276b40e29fdba4b6578e39af6c860a7be0f8c75d55040a0bad57aad4', secret='SEC6ac31d2d123d02e32b221f49605f96b8ebeb2e9c5d4776b86c3d49c211fdd6a2')
        if class_message:
            send_ding_msg(data=class_message, url='https://oapi.dingtalk.com/robot/send?access_token=3daeb8d9276b40e29fdba4b6578e39af6c860a7be0f8c75d55040a0bad57aad4', secret='SEC6ac31d2d123d02e32b221f49605f96b8ebeb2e9c5d4776b86c3d49c211fdd6a2')
    else:
        send_ding_msg(data=message)
        send_ding_msg(data=equip_message)
        if class_message:
            send_ding_msg(data=class_message)
