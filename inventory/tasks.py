# -*- coding: UTF-8 -*-
"""
auther: 李威
datetime: 2020/11/2
name: 触发任务，
desc: 快检结果更新到mes，mes将触发该脚本将快检结果同步至wms
"""
import json

from inventory.utils import BaseUploader
from mes.common_code import order_no


class KJJGUploader(BaseUploader):
    endpoint = "http://10.4.23.101:1010/Service1.asmx?op=TRANS_MES_TO_WMS_KJJG"

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
        # items = json.loads(data).get('items')
        items = json.loads(data)
        ret = []
        for item in items:
            if item['flag'] != '01':  # 01代表成功
                ret.append(item['msg'])
        return ret


def update_wms_kjjg(msg_id, items):
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
            "msgId": msg_id,
            "OUTTYPE": out_type,
            "msgConut": "2",
            "SENDUSER": user,
            "items": items
        }
        msg_count = len(data_json["items"])
        data_json["msgConut"] = msg_count
        return msg_id, out_type, msg_count, user, json.dumps(data_json, ensure_ascii=False)
    sender = KJJGUploader()
    sender.request(*get_base_data())