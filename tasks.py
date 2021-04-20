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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from inventory.utils import BaseUploader
from mes.common_code import order_no
from inventory.models import BzFinalMixingRubberInventoryLB

class KJJGUploader(BaseUploader):
    dict_filter = {'混炼': "http://10.4.23.101:1010/Service1.asmx?op=TRANS_MES_TO_WMS_KJJG",
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


def update_wms_kjjg(items=[{
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
        print(data_json)
        return msg_id, out_type, msg_count, user, json.dumps(data_json, ensure_ascii=False)
#         return "1", "物料快检", "1", "GJ_001", json.dumps({
#         "msgId": "1",                       #  任务包号       string
#         "KJTYPE": "物料快检",          #   质检类型       string
#         "msgConut": "1",                 #  子任务数量    string
#         "SENDUSER": "GJ_001",      #  质检操作人     string
#         "items": [{
#             "WORKID": "11223",                            #  任务id                string
#             "MID": "C-HMB-F150-12",                  # 物料编号              string
#             "PICI": "20200101",                             # 批次号/计划号       string
#             "NUM": "100",                                     # 车数量                     string
#             "KJJG": "合格",                                      # 品质状态               string
#             "SENDDATE": "20200513 09:22:22"    # 下发时间               string
#         }]
#     }
# , ensure_ascii=False)
    #TODO
    container = items[0]["RFID"]
    container_no_list = BzFinalMixingRubberInventoryLB.objects.using("lb").all().values_list("container_no", flat=True)
    if container in container_no_list:
        ware = "终炼"
    else:
        ware = "混炼"
    sender = KJJGUploader(ware)
    ret = sender.request(*get_base_data())
    return ret

if __name__ == '__main__':
    update_wms_kjjg([{'WORKID': '202104160003', 'MID': 'C-FM-Y792-02', 'PICI': '20215818112458i35', 'RFID': '20115409', 'DJJG': '一等品', 'SENDDATE': '20210416 09:41:40'}])