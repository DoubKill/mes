import json

from inventory.utils import BaseUploader


class KJJGUploader(BaseUploader):
    endpoint = "http://10.4.23.101:1010/Service1.asmx?op=TRANS_MES_TO_WMS_UPDATE"

    def gen_payload(self, msg_id, r_type, msg_count, str_user, str_json):
        xml_data = """<?xml version="1.0" encoding="utf-8"?>
                <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                  <soap:Body>
                    <TRANS_MES_TO_WMS_UPDATE xmlns="http://www.riamb.ac.cn/asrs/WebService/TA_SAP/">
                      <MsgId>{}</MsgId>
                      <MsgConut>{}</MsgConut>
                      <strUser>{}</strUser>
                      <strJson>{}</strJson>
                    </TRANS_MES_TO_WMS_UPDATE>
                  </soap:Body>
                </soap:Envelope>""".format(msg_id, r_type, msg_count, str_user, str_json)
        return xml_data

    def gen_result(self, data):
        data = data.get('soap:Envelope'
                        ).get('soap:Body'
                              ).get('TRANS_MES_TO_WMS_UPDATEResponse'
                                    ).get('TRANS_MES_TO_WMS_UPDATEResult')
        items = json.loads(data).get('items')
        print(items)
        ret = []
        for item in items:
            if item['flag'] != '01':  # 01代表成功
                ret.append(item['msg'])
        return ret



if __name__ == '__main__':


    demo_data = {
        "msgId": "1",
        "msgConut": "2",
        "UPDATEUSER": "GJ_001",
        "items": [{
            "WORKID": "11223",
            "MID": "C-HMB-F150-12",
            "PICI": "Z06MN01",
            "RFID": "20200101",
            "LOTNO": "E101B012020103010118",
            "STORE": "终炼胶库",
            "QUALITY": "ok",
            "SENDDATE": "20200513 09:22:22"
            },
            {
            "WORKID": "11224",
            "MID": "C-HMB-F150-12",
            "PICI": "Z06MN01",
            "RFID": "20200102",
            "LOTNO": "E101B012020103010119",
            "STORE": "终炼胶库",
            "QUALITY": "no",
            "SENDDATE": "20200513 09:22:23"
            }]
        }