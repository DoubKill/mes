# -*- coding: UTF-8 -*-
"""
auther: 李威
datetime: 2020/11/2
name: 触发任务，
desc: 快检结果更新到mes，mes将触发该脚本将快检结果同步至wms
"""
import json
import os

import django

from mes.common_code import order_no
from terminal.utils import issue_plan, INWeighSystem

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from inventory.utils import BaseUploader
from inventory.models import BzFinalMixingRubberInventoryLB

class KJJGUploader(BaseUploader):
    dict_filter = {'混炼': "http://10.4.23.101:1011/Service1.asmx?op=TRANS_MES_TO_WMS_KJJG",
                   '终炼': "http://10.4.23.101:1020/Service1.asmx?op=TRANS_MES_TO_WMS_KJJG"}

    def __init__(self, ware):
        self.end_type = ware
        self.endpoint = self.dict_filter[self.end_type]
    # endpoint = "http://10.4.23.101:1010/Service1.asmx?op=TRANS_MES_TO_WMS_KJJG"  # 混炼胶库
    # endpoint = "http://10.4.23.101:1020/Service1.asmx?op=TRANS_MES_TO_WMS_KJJG"  # 终炼胶库

    def gen_payload(self, msg_id, r_type, msg_count, str_user, str_json):
        xml_data = """<?xml version="1.0" encoding="utf-8"?>
                <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                  <soap:Body>
                    <TRANS_MES_TO_WMS_KJJG xmlns="http://www.riamb.ac.cn/asrs/WebService/TA_SAP/">
                      <MsgId>{}</MsgId>
                      <KJTYPE>{}</KJTYPE>
                      <MsgConut>{}</MsgConut>
                      <strUser>{}</strUser>
                      <strJson>{}</strJson>
                    </TRANS_MES_TO_WMS_KJJG>
                  </soap:Body>
                </soap:Envelope>""".format(msg_id, r_type, msg_count, str_user, str_json)
        return xml_data

    def gen_result(self, data):
        data = data.get('soap:Envelope'
                        ).get('soap:Body'
                              ).get('TRANS_MES_TO_WMS_KJJGResponse'
                                    ).get('TRANS_MES_TO_WMS_KJJGResult')
        try:
            items = json.loads(data).get('items')
        except:
            items = json.loads(data)
        ret = []
        for item in items:
            if item['flag'] != '01':  # 01代表成功
                ret.append(item['msg'])
        return ret


def update_wms_kjjg(ware, items=[{
            "WORKID": "11223",                            #  任务id                  string
            "MID": "C-HMB-F150-12",                  # 物料编号                string
            "PICI": "20200101",                             # 批次号/计划号        string
            "RFID": "20120001",                            # RFID托盘号            string
            "DJJG": "一等品",                                  # 品质等级               string
            "SENDDATE": "20200513 09:22:22"    # 下发时间                string
        }]):
    def get_base_data():
        """
        items 按照业务要求填充
        :param items: [
                {"WORKID": "11223",
                 "MID": "C-HMB-F150-12",
                 "PICI": "20200101",
                 "NUM": "1",
                 "STATIONID": "二层后端",
                 "SENDDATE": "20200513 09:22:22"},
                {"WORKID": "11224",
                 "MID": "C-HMB-F150-11",
                 "PICI": "20200101",
                 "NUM": "1",
                 "STATIONID": "二层前端",
                 "SENDDATE": "20200513 09:22:22"}
            ]
        :return:
        """
        user = "Mes"
        out_type = "物料快检"
        data_json = {
            "msgId": "1",
            "KJTYPE": out_type,
            "msgConut": "2",
            "SENDUSER": user,
            "items": items
        }
        msg_id = order_no()
        msg_count = str(len(data_json["items"]))
        data_json["msgId"] = msg_id
        data_json["msgConut"] = msg_count
        return msg_id, out_type, msg_count, user, json.dumps(data_json, ensure_ascii=False)
    sender = KJJGUploader(ware)
    ret = sender.request(*get_base_data())
    return ret



if __name__ == '__main__':
    # update_wms_kjjg([{'WORKID': '202105070011', 'MID': 'C-1MB-K503-09', 'PICI': '2021021322073855Z05', 'RFID': '20121082', 'DJJG': '一等品', 'SENDDATE': '20210516 09:41:40'}])

    door_info = {
        "开门信号1": "0",   # 称量系统 A料仓 1~11  例开A6号料仓门传"6"
        "开门信号2": "0"    # 称量系统 B料仓 1~11  例开B6号料仓门传"6"
    }
    update_trains = {
        "plan_no": "210519110215",  # 计划操作编号
        "action": "1",               # 具体计划的操作方式
        "num": 30                  # 需修改的车次
    }
    reload_data = {
        "plan_no": "210519110215",  # 计划操作编号
        "action": "1",  # 具体计划的操作方式
    }
    stop_data = {
        "plan_no": "210519110215",  # 计划操作编号
        "action": "1",  # 具体计划的操作方式
    }
    add_data = {
        "plan_no": "99c4fd9e914f11eb88870050568ff1ef",
        "action": "1"
    }
    issue_data = {
        "plan_no": "99c4fd9e914f11eb88870050568ff1ef",  # 计划编号
        "recipe_no": "C-FM-C590-06(E580)",              # 配方编号需要带机型
        "num": 100,                                     # 计划车次
        "action": "1"
    }
    # # 对接的是易控软件，传入的参数需为有序字典， 即在构建字典的顺序是，key值需按样例给出的顺序
    # xlc01.reload_plan(reload_data)
    # xlc01.update_trains(update_trains)
    # print(xlc01.door_info(door_info))
    # xlc01.stop(stop_data)
    # issue_recipe("C-1MB-C510-09", "S01")
    issue_plan("99c4fd9e914f11eb88870050568ff1ef", "S01")
    xlc01 = INWeighSystem("S01")
    # print(xlc01.issue_plan(issue_data))  #慎用 会直接到plc
    # print(xlc01.add_plan(add_data))

