# -*- coding: UTF-8 -*-
"""
auther: 李威
datetime: 2020/11/2
name: 触发任务，
desc: 快检结果更新到mes，mes将触发该脚本将快检结果同步至wms
"""
import json
import os
import sys

import django

from inventory.models import MixGumInInventoryLog, MixGumOutInventoryLog, InventoryLog
from mes.conf import INVENTORY_MAP
from inventory.utils import BaseUploader
from mes.common_code import order_no

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()


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
        try:
            for item in items:
                if item['flag'] != '01':  # 01代表成功
                    ret.append(item['msg'])
        except:
            for item in items['items']:
                if item['flag'] != '01':  # 01代表成功
                    ret.append(item['msg'])
        return ret


def update_wms_kjjg(msg_id, items=[
    {"WORKID": "202005130922221",
     "MID": "C-HMB-F150-12",
     "PICI": "20200101",
     "NUM": "1",
     "KJJG": "合格",
     "SENDDATE": "20200513 09:22:22"}
]):
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
            "KJTYPE": out_type,
            "msgConut": len(items),
            "SENDUSER": user,
            "items": items
        }
        msg_count = len(data_json["items"])
        data_json["msgConut"] = msg_count
        return msg_id, out_type, msg_count, user, json.dumps(data_json, ensure_ascii=False)

    sender = KJJGUploader()
    ret = sender.request(*get_base_data())
    return ret


class OutworkHistorySync(object):

    INVENTORY = INVENTORY_MAP

    @classmethod
    def get_model_list(cls, queryset, **kwargs):
        ret = []
        model =  kwargs.get("model")
        order_type = kwargs.get("order_type")
        info = kwargs.get("info")
        for temp in queryset:
            data = {
                "warehouse_no": info[2],
                "warehouse_name": info[1],
                "order_no": temp.order_no,
                "pallet_no": temp.pallet_no,
                "location":  temp.location,
                "qty": temp.qty,
                "weight": temp.weight,
                "material_no": temp.material_no,
                "quality_status": temp.quality_status,
                "lot_no": temp.lot_no,
                "order_type": order_type,
                "inout_reason": temp.inout_reason,
                "inout_num_type": temp.inout_num_type,
                "inventory_type": temp.inventory_type,
                "unit": temp.unit,
                "initiator": temp.initiator,
                "start_time": temp.start_time,
                "fin_time": temp.fin_time,
                "classes" : "",
                "equip_no": "",
                "io_location": "",
                "dst_location": "",
            }
            ret.append(model(**data))
        return ret

    @classmethod
    def sync(cls):
        for info, model_dict in cls.INVENTORY.items():
            db = info[0]
            warehouse = info[1]
            if not model_dict:
                continue
            for order_type, model in model_dict.items():
                # if order_type == "出库":
                if not model:
                    continue
                temp = InventoryLog.objects.filter(order_type=order_type, warehouse_name=warehouse).last()
                if not temp:
                    continue
                target_time = temp.start_time
                temp_set = model.objects.using(db).filter(start_time__gt=target_time)
                ret = cls.get_model_list(temp_set, info=info, model=model)
                InventoryLog.objects.bulk_create(ret)


#
# if __name__ == '__main__':
#     OutworkHistorySync.sync()