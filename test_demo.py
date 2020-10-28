# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/10/28
name: 
"""
import os

import django
import requests
from rest_framework.exceptions import ValidationError


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()


from system.models import ChildSystemInfo


class WebService(object):
    client = requests.request
    url = "http://{}:9000/planService"

    @classmethod
    def issue(cls, method="post", equip_no=6, equip_name="收皮终端"):
        headers = {
            "Host": "10.4.23.101",
            'Content-Type': 'text/xml; charset=utf-8',
            "Content-Length": "length",
            'SOAPAction': 'http://www.riamb.ac.cn/asrs/WebService/TA_SAP/TRANS_MES_TO_WMS_OUTWORK'
        }

        # child_system = ChildSystemInfo.objects.filter(system_name=f"{equip_name}{equip_no}").first()
        # recv_ip = child_system.link_address
        # url = cls.url.format(recv_ip)
        url = "http://10.4.23.101:1010/Service1.asmx?op=TRANS_MES_TO_WMS_OUTWORK"
        # headers['SOAPAction'] = headers['SOAPAction'].format(category)
        # body = cls.trans_dict_to_xml(data, category)
        body = """<?xml version="1.0" encoding="utf-8"?>
                <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                  <soap:Body>
                    <TRANS_MES_TO_WMS_OUTWORK xmlns="http://www.riamb.ac.cn/asrs/WebService/TA_SAP/">
                      <MsgId>1</MsgId>
                      <OutType>out</OutType>
                      <MsgConut>2</MsgConut>
                      <strUser>GJ_001</strUser>
                      <strJson>{\"items\":[{\"WORKID\":\"11223\",\"MID\":\"C-HMB-F150-12\",\"PICI\":\"20200101\",\"NUM\":\"100\",\"STATIONID\":\"二层后端\",\"SENDDATE\":\"2020051309:22:22\"},{\"WORKID\":\"11224\",\"MID\":\"C-HMB-F150-11\",\"PICI\":\"20200101\",\"NUM\":\"100\",\"STATIONID\":\"二层前端\",\"SENDDATE\":\"2020051309:22:22\"}]}</strJson>
                    </TRANS_MES_TO_WMS_OUTWORK>
                  </soap:Body>
                </soap:Envelope>
                """.encode("utf-8")
        rep = cls.client(method, url, headers=headers, data=body, timeout=3)
        # print(rep.text)
        if rep.status_code < 300:
            print(rep.text)
            if "已存在" in rep.text:
                raise ValidationError("该配方已存在于上辅机，请勿重复下达")
            elif "不存在" in rep.text:
                raise ValidationError("该配方不存在于上辅机，无法重传，请检查")
            return True, rep.text
        elif rep.status_code == 500:
            print(rep.text)
            return False, rep.text
        else:
            print(rep.text)
            return False, rep.text

    # dict数据转soap需求xml
    @staticmethod
    def trans_dict_to_xml(data, category):
        """
        将 dict 对象转换成微信支付交互所需的 XML 格式数据

        :param data: dict 对象
        :return: xml 格式数据
        """
        xml = []
        for k in data.keys():
            v = data.get(k)
            if k == 'detail' and not v.startswith('<![CDATA['):
                v = '<![CDATA[{}]]>'.format(v)
            xml.append('<{key}>{value}</{key}>'.format(key=k, value=v))
        res = """<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"> <s:Body>
                    <{} xmlns="http://tempuri.org/">
                       {}
                    </{}>
                </s:Body>
                </s:Envelope>""".format(category, ''.join(xml), category)
        res = res.encode("utf-8")
        return res


if __name__ == "__main__":
    WebService.issue()