import logging
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
from equipment.models import EquipApplyOrder, EquipOrderAssignRule
from equipment.utils import DinDinAPI

logger = logging.getLogger("send_ding_msg")

ding_api = DinDinAPI()


def handle(order):
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
    if order.status == "已生成":
        pass
    elif order.status == "已指派":
        if not receive_interval or not receive_warning_times:
            logger.info(f"超时提醒: 规则不存在或未设置提醒间隔或次数:设备类型{equip_type},作业类型{order.work_type}")
            return f"超时提醒: 规则不存在或未设置提醒间隔或次数:设备类型{equip_type},作业类型{order.work_type}"
        record_time = order.assign_datetime
        check_result, times = compare_time(now_date, record_time, receive_interval, receive_warning_times)
        if check_result:
            order.timeout_color = "粉红色"
            order.save()
            all_user = ''
            # 发送消息提醒
            if order.work_type == "维修":
                if order.created_user.username != "系统":
                    # 报修发消息给被指派人和上级
                    all_user = "1,2"
                    uids = get_ding_uids_by_name(order.assign_to_user, all_user=all_user)
                else:
                    # 系统自动生成维修单, 根据维修标准里提示
                    if order.equip_repair_standard.remind_flag1:
                        all_user += "1"
                    if order.equip_repair_standard.remind_flag2:
                        all_user += "2"
                    if order.equip_repair_standard.remind_flag3:
                        all_user += "3"
                    uids = get_ding_uids_by_name(order.assign_to_user, all_user)
            else:
                # 根据维护标准提示(保养/润滑/标定)
                if order.equip_maintenance_standard.remind_flag1:
                    all_user += "1"
                if order.equip_maintenance_standard.remind_flag2:
                    all_user += "2"
                if order.equip_maintenance_standard.remind_flag3:
                    all_user += "3"
                uids = get_ding_uids_by_name(order.assign_to_user, all_user)
            if not all_user:
                logger.info(f"超时提醒: 本单据{order.work_order_no}标准中未设置提醒")
                return "超时提醒: 本单据{order.work_order_no}标准中未设置提醒"
            fault_name = order.result_fault_cause.fault_name if order.result_fault_cause else (
                order.equip_repair_standard.standard_name if order.equip_repair_standard else order.equip_maintenance_standard.standard_name)
            content = {"title": f"第{times}次催办\r\n您名下单据{order.work_order_no}超期未接单",
                       "form": [{"key": "工单编号:", "value": order.work_order_no},
                                {"key": "机台:", "value": order.equip_no},
                                {"key": "部位名称:",
                                 "value": order.equip_part_new.part_name if order.equip_part_new else ''},
                                {"key": "故障原因:", "value": fault_name},
                                {"key": "重要程度:", "value": order.importance_level},
                                {"key": "被指派人:", "value": order.assign_to_user},
                                {"key": "指派时间:", "value": str(order.assign_datetime)}]}
            if "1" in all_user:
                ding_api.send_message(uids[:1], content, order_id=order.id)
                if len(uids) > 2:
                    ding_api.send_message(uids[1:], content)
            else:
                ding_api.send_message(uids, content)
            logger.info(f"超时提醒: 超期未接单提醒已经发送")
    elif order.status == "已接单":
        if not start_interval or not start_warning_times:
            logger.info(f"超时提醒: 规则不存在或未设置提醒间隔或次数:设备类型{equip_type},作业类型{order.work_type}")
            return f"超时提醒: 规则不存在或未设置提醒间隔或次数:设备类型{equip_type},作业类型{order.work_type}"
        record_time = order.receiving_datetime
        check_result, times = compare_time(now_date, record_time, start_interval, start_warning_times)
        if check_result:
            order.timeout_color = "酱红色"
            order.save()
            all_user = ''
            # 发送消息提醒
            if order.work_type == "维修":
                if order.created_user.username != "系统":
                    # 报修发消息给被指派人和上级
                    all_user = "1,2"
                    uids = get_ding_uids_by_name(order.receiving_user, all_user=all_user)
                else:
                    # 系统自动生成维修单, 根据维修标准里提示
                    if order.equip_repair_standard.remind_flag1:
                        all_user += "1"
                    if order.equip_repair_standard.remind_flag2:
                        all_user += "2"
                    if order.equip_repair_standard.remind_flag3:
                        all_user += "3"
                    uids = get_ding_uids_by_name(order.receiving_user, all_user)
            else:
                # 根据维护标准提示(保养/润滑/标定)
                if order.equip_maintenance_standard.remind_flag1:
                    all_user += "1"
                if order.equip_maintenance_standard.remind_flag2:
                    all_user += "2"
                if order.equip_maintenance_standard.remind_flag3:
                    all_user += "3"
                uids = get_ding_uids_by_name(order.receiving_user, all_user)
            if not all_user:
                logger.info(f"超时提醒: 本单据{order.work_order_no}标准中未设置提醒")
                return "超时提醒: 本单据{order.work_order_no}标准中未设置提醒"
            fault_name = order.result_fault_cause.fault_name if order.result_fault_cause else (
                order.equip_repair_standard.standard_name if order.equip_repair_standard else order.equip_maintenance_standard.standard_name)
            content = {"title": f"第{times}次催办\r\n您名下单据{order.work_order_no}超期未执行",
                       "form": [{"key": "工单编号:", "value": order.work_order_no},
                                {"key": "机台:", "value": order.equip_no},
                                {"key": "部位名称:",
                                 "value": order.equip_part_new.part_name if order.equip_part_new else ''},
                                {"key": "故障原因:", "value": fault_name},
                                {"key": "重要程度:", "value": order.importance_level},
                                {"key": "接单人:", "value": order.receiving_user},
                                {"key": "接单时间:", "value": str(order.receiving_datetime)}]}
            if "1" in all_user:
                ding_api.send_message(uids[:1], content, order_id=order.id)
                if len(uids) > 2:
                    ding_api.send_message(uids[1:], content)
            else:
                ding_api.send_message(uids, content)
            logger.info(f"超时提醒: 超期未执行提醒已经发送")
    elif order.status == "已开始":
        pass
    else:
        # 已完成
        if not accept_interval or not accept_warning_times:
            logger.info(f"超时提醒: 规则不存在或未设置提醒间隔或次数:设备类型{equip_type},作业类型{order.work_type}")
            return f"超时提醒: 规则不存在或未设置提醒间隔或次数:设备类型{equip_type},作业类型{order.work_type}"
        record_time = order.receiving_datetime
        check_result, times = compare_time(now_date, record_time, accept_interval, accept_warning_times)
        if check_result:
            order.timeout_color = "red"
            order.save()
            all_user = ''
            # 发送消息提醒
            if order.work_type == "维修":
                if order.created_user.username != "系统":
                    # 报修发消息给被指派人和上级
                    all_user = "1,2"
                    uids = get_ding_uids_by_name(order.receiving_user, all_user=all_user)
                else:
                    # 系统自动生成维修单, 根据维修标准里提示
                    if order.equip_repair_standard.remind_flag1:
                        all_user += "1"
                    if order.equip_repair_standard.remind_flag2:
                        all_user += "2"
                    if order.equip_repair_standard.remind_flag3:
                        all_user += "3"
                    uids = get_ding_uids_by_name(order.receiving_user, all_user)
            else:
                # 根据维护标准提示(保养/润滑/标定)
                if order.equip_maintenance_standard.remind_flag1:
                    all_user += "1"
                if order.equip_maintenance_standard.remind_flag2:
                    all_user += "2"
                if order.equip_maintenance_standard.remind_flag3:
                    all_user += "3"
                uids = get_ding_uids_by_name(order.receiving_user, all_user)
            if not all_user:
                logger.info(f"本单据{order.work_order_no}标准中未设置提醒")
                return "本单据{order.work_order_no}标准中未设置提醒"
            fault_name = order.result_fault_cause.fault_name if order.result_fault_cause else (
                order.equip_repair_standard.standard_name if order.equip_repair_standard else order.equip_maintenance_standard.standard_name)
            content = {"title": f"第{times}次催办\r\n您名下单据{order.work_order_no}超期未验收",
                       "form": [{"key": "工单编号:", "value": order.work_order_no},
                                {"key": "机台:", "value": order.equip_no},
                                {"key": "部位名称:",
                                 "value": order.equip_part_new.part_name if order.equip_part_new else ''},
                                {"key": "故障原因:", "value": fault_name},
                                {"key": "重要程度:", "value": order.importance_level},
                                {"key": "维修人:", "value": order.repair_user},
                                {"key": "维修完成时间:", "value": str(order.repair_end_datetime)}]}
            if "1" in all_user:
                ding_api.send_message(uids[:1], content, order_id=order.id)
                if len(uids) > 2:
                    ding_api.send_message(uids[1:], content)
            else:
                ding_api.send_message(uids, content)
            logger.info(f"超时提醒: 超期未验收提醒已经发送")
    return "超时提醒: 单据提醒处理完成"


def compare_time(now_datetime, check_time, interval, times):
    """获取比较时间"""
    for i in range(1, times + 1):
        change_minutes = interval * i
        if check_time + timedelta(minutes=change_minutes) <= now_datetime <= check_time + timedelta(
                minutes=change_minutes + 1):
            return True, i
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


def check_to_msg():
    # 所有维修工单
    orders = EquipApplyOrder.objects.filter(~Q(status__in=["已验收", "已关闭"]))
    if not orders:
        logger.info("超时提醒: 所有维修单均已验收")
    for order in orders:
        res = handle(order)


if __name__ == "__main__":
    check_to_msg()
