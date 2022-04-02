import logging
import math
import os
import sys
from datetime import datetime, timedelta

import django
from django.db.models import Q

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from basics.models import Equip
from system.models import User
from equipment.models import EquipApplyOrder, EquipOrderAssignRule, EquipInspectionOrder
from equipment.utils import DinDinAPI

logger = logging.getLogger("send_ding_msg")


def handle(order):
    # 提醒消息里的链接类型 False 非巡检  True 巡检
    inspection = False if order.work_type != '巡检' else True
    # 获取规则
    instance = Equip.objects.filter(equip_no=order.equip_no).first()
    # 设备类型
    equip_type = instance.category.equip_type.global_name if instance else ''
    receive_interval = receive_warning_times = start_interval = start_warning_times = accept_interval = accept_warning_times = 0
    # 工单指派规则
    rule = EquipOrderAssignRule.objects.filter(equip_type__global_name=equip_type, work_type=order.work_type,
                                               use_flag=1).first()
    if rule:
        receive_interval = rule.receive_interval
        receive_warning_times = rule.receive_warning_times
        start_interval = rule.start_interval
        start_warning_times = rule.start_warning_times
        accept_interval = rule.accept_interval
        accept_warning_times = rule.accept_warning_times
    now_date = datetime.now().replace(microsecond=0)
    if order.status == "已指派":
        if not receive_interval or not receive_warning_times:
            logger.info(f"超时提醒: 规则不存在或未设置提醒间隔或次数:设备类型{equip_type},作业类型{order.work_type}-{order.work_order_no}")
            return f"超时提醒: 规则不存在或未设置提醒间隔或次数:设备类型{equip_type},作业类型{order.work_type}-{order.work_order_no}"
        record_time = order.assign_datetime
        check_result, times = compare_time(now_date, record_time, receive_interval, receive_warning_times)
        if check_result:
            order.timeout_color = "粉红色"
            order.save()
            all_user = ''
            # 发送消息提醒
            if order.work_type == "维修":
                # 报修发消息给被指派人和上级
                all_user = "1,2"
            elif order.work_type == "巡检":
                # 发送消息提醒
                if order.equip_repair_standard.remind_flag1:
                    all_user += "1"
                if order.equip_repair_standard.remind_flag2:
                    all_user += "2"
                if order.equip_repair_standard.remind_flag3:
                    all_user += "3"
            else:
                # 根据维护标准提示(保养/润滑/标定)
                if order.equip_maintenance_standard.remind_flag1:
                    all_user += "1"
                if order.equip_maintenance_standard.remind_flag2:
                    all_user += "2"
                if order.equip_maintenance_standard.remind_flag3:
                    all_user += "3"
            if not all_user:
                logger.info(f"超时提醒: 本单据{order.work_order_no}标准中未设置提醒")
                return "超时提醒: 本单据{order.work_order_no}标准中未设置提醒"
            uids = get_ding_uids_by_name(order.assign_to_user, all_user=all_user)
            if order.work_type != '巡检':
                fault_name = order.result_fault_cause if order.result_fault_cause else (
                    order.equip_repair_standard.standard_name if order.equip_repair_standard else order.equip_maintenance_standard.standard_name)
                content = {"title": f"第{times}次催办\r\n您名下单据超期未接单",
                           "form": [{"key": "工单编号:", "value": order.work_order_no},
                                    {"key": "机台:", "value": order.equip_no},
                                    {"key": "部位名称:",
                                     "value": order.equip_part_new.part_name if order.equip_part_new else ''},
                                    {"key": "故障原因:", "value": fault_name},
                                    {"key": "重要程度:", "value": order.importance_level},
                                    {"key": "被指派人:", "value": order.assign_to_user},
                                    {"key": "指派时间:", "value": str(order.assign_datetime)},
                                    {"key": "提醒时间:", "value": str(now_date)}]}
            else:
                content = {"title": f"第{times}次催办\r\n您名下单据超期未接单",
                           "form": [{"key": "工单编号:", "value": order.work_order_no},
                                    {"key": "机台:", "value": order.equip_no},
                                    {"key": "巡检标准:", "value": order.equip_repair_standard.standard_name},
                                    {"key": "重要程度:", "value": order.importance_level},
                                    {"key": "被指派人:", "value": order.assign_to_user},
                                    {"key": "指派时间:", "value": str(order.assign_datetime)},
                                    {"key": "提醒时间:", "value": str(now_date)}]}
            if "1" in all_user:
                ding_api.send_message(uids[:1], content, order_id=order.id, inspection=inspection)
                if len(uids) > 2:
                    ding_api.send_message(uids[1:], content)
            else:
                ding_api.send_message(uids, content)
            logger.info(f"超时提醒: 超期未接单提醒已经发送-{order.work_order_no}")
    elif order.status == "已接单":
        if not start_interval or not start_warning_times:
            logger.info(f"超时提醒: 规则不存在或未设置提醒间隔或次数:设备类型{equip_type},作业类型{order.work_type}-{order.work_order_no}")
            return f"超时提醒: 规则不存在或未设置提醒间隔或次数:设备类型{equip_type},作业类型{order.work_type}-{order.work_order_no}"
        record_time = order.receiving_datetime
        check_result, times = compare_time(now_date, record_time, start_interval, start_warning_times)
        if check_result:
            order.timeout_color = "酱红色"
            order.save()
            all_user = ''
            # 发送消息提醒
            if order.work_type == "维修":
                # 报修发消息给被指派人和上级
                all_user = "1,2"
            elif order.work_type == "巡检":
                # 发送消息提醒
                if order.equip_repair_standard.remind_flag1:
                    all_user += "1"
                if order.equip_repair_standard.remind_flag2:
                    all_user += "2"
                if order.equip_repair_standard.remind_flag3:
                    all_user += "3"
            else:
                # 根据维护标准提示(保养/润滑/标定)
                if order.equip_maintenance_standard.remind_flag1:
                    all_user += "1"
                if order.equip_maintenance_standard.remind_flag2:
                    all_user += "2"
                if order.equip_maintenance_standard.remind_flag3:
                    all_user += "3"
            if not all_user:
                logger.info(f"超时提醒: 本单据{order.work_order_no}标准中未设置提醒")
                return "超时提醒: 本单据{order.work_order_no}标准中未设置提醒"
            uids = get_ding_uids_by_name(order.receiving_user, all_user=all_user)
            if order.work_type != '巡检':
                fault_name = order.result_fault_cause if order.result_fault_cause else (
                    order.equip_repair_standard.standard_name if order.equip_repair_standard else order.equip_maintenance_standard.standard_name)
                content = {"title": f"第{times}次催办\r\n您名下单据超期未执行",
                           "form": [{"key": "工单编号:", "value": order.work_order_no},
                                    {"key": "机台:", "value": order.equip_no},
                                    {"key": "部位名称:",
                                     "value": order.equip_part_new.part_name if order.equip_part_new else ''},
                                    {"key": "故障原因:", "value": fault_name},
                                    {"key": "重要程度:", "value": order.importance_level},
                                    {"key": "接单人:", "value": order.receiving_user},
                                    {"key": "接单时间:", "value": str(order.receiving_datetime)},
                                    {"key": "提醒时间:", "value": str(now_date)}]}
            else:
                content = {"title": f"第{times}次催办\r\n您名下单据超期未执行",
                           "form": [{"key": "工单编号:", "value": order.work_order_no},
                                    {"key": "机台:", "value": order.equip_no},
                                    {"key": "巡检标准:", "value": order.equip_repair_standard.standard_name},
                                    {"key": "重要程度:", "value": order.importance_level},
                                    {"key": "接单人:", "value": order.receiving_user},
                                    {"key": "接单时间:", "value": str(order.receiving_datetime)},
                                    {"key": "提醒时间:", "value": str(now_date)}]}
            if "1" in all_user:
                ding_api.send_message(uids[:1], content, order_id=order.id, inspection=inspection)
                if len(uids) > 2:
                    ding_api.send_message(uids[1:], content)
            else:
                ding_api.send_message(uids, content)
            logger.info(f"超时提醒: 超期未执行提醒已经发送-{order.work_order_no}")
    else:
        # 已完成
        if not accept_interval or not accept_warning_times:
            logger.info(f"超时提醒: 规则不存在或未设置提醒间隔或次数:设备类型{equip_type},作业类型{order.work_type}-{order.work_order_no}")
            return f"超时提醒: 规则不存在或未设置提醒间隔或次数:设备类型{equip_type},作业类型{order.work_type}-{order.work_order_no}"
        record_time = order.repair_end_datetime
        check_result, times = compare_time(now_date, record_time, accept_interval, accept_warning_times)
        if check_result:
            order.timeout_color = "红色"
            order.save()
            uids = get_ding_uids_by_name(order.accept_user, all_user='1,2')
            fault_name = order.result_fault_cause if order.result_fault_cause else (
                order.equip_repair_standard.standard_name if order.equip_repair_standard else order.equip_maintenance_standard.standard_name)
            content = {"title": f"第{times}次催办\r\n您名下单据超期未验收",
                       "form": [{"key": "工单编号:", "value": order.work_order_no},
                                {"key": "机台:", "value": order.equip_no},
                                {"key": "部位名称:",
                                 "value": order.equip_part_new.part_name if order.equip_part_new else ''},
                                {"key": "故障原因:", "value": fault_name},
                                {"key": "重要程度:", "value": order.importance_level},
                                {"key": "维修人:", "value": order.repair_user},
                                {"key": "维修完成时间:", "value": str(order.repair_end_datetime)},
                                {"key": "提醒时间:", "value": str(now_date)}]}
            ding_api.send_message(uids[:1], content, order_id=order.id, inspection=inspection)
            logger.info(f"超时提醒: 超期未验收提醒已经发送-{order.work_order_no}")
    return "超时提醒: 单据提醒处理完成"


def compare_time(now_datetime, check_time, interval, times):
    """获取比较时间"""
    alarm_time = [i * interval for i in range(1, times + 1)]
    num = math.ceil((now_datetime - check_time).seconds / 60)
    if num in alarm_time:
        return True, int(num / interval)
    return False, 0


def get_ding_uids_by_name(user_name, all_user):
    maps = {"1": "phone_number", "2": "section__in_charge_user__phone_number",
            "3": "section__parent_section__in_charge_user__phone_number"}
    # 获取部门所有员工信息
    phones = User.objects.filter(username__in=user_name.split(",")).values("phone_number",
                                                                           "section__in_charge_user__phone_number",
                                                                           "section__parent_section__in_charge_user__phone_number")
    uids = []
    for phone in phones:
        for user in all_user.split(","):
            ding_uid = ding_api.get_user_id(phone.get(maps[user]))
            if ding_uid:
                uids.append(ding_uid)
    return list(set(uids))


if __name__ == "__main__":
    ding_api = DinDinAPI()
    # 所有维修工单
    repair_orders = list(EquipApplyOrder.objects.filter(~Q(status__in=["已生成", "已验收", "已关闭", "已开始"])))
    # 所有巡检工单
    inspect_orders = list(EquipInspectionOrder.objects.filter(~Q(status__in=["已生成", "已关闭", "已开始", "已完成"])))
    orders = repair_orders + inspect_orders
    if not orders:
        logger.info("超时提醒: 不存在需要超时提醒的工单")
    for order in orders:
        res = handle(order)
