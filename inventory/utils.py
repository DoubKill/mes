# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/10/29
name: 
"""
import json
from io import BytesIO

import requests
import xlwt
import xmltodict
from django.http import HttpResponse
from rest_framework.exceptions import ValidationError
from suds.client import Client


class BaseUploader(object):
    endpoint = ""

    def request(self, msg_id, out_type, msg_count, str_user, json_data):
        if not self.endpoint:
            raise NotImplementedError('未设置endpoint')
        pay_load = self.gen_payload(msg_id, out_type, msg_count, str_user, json_data)
        headers = {
            "Content-Type": "text/xml; charset=utf-8"
        }
        pay_load = pay_load.encode('utf-8')
        try:
            resp = requests.post(self.endpoint, data=pay_load, headers=headers, timeout=5)
        except Exception:
            raise ValidationError('请求失败，请联系管理员！')
        if resp.status_code != 200:
            # print(resp.text)
            raise Exception(resp.text)
        resp_xml = resp.text
        json_data = xmltodict.parse(resp_xml)
        # print(json_data)
        return self.gen_result(json_data)

    def gen_result(self, data):
        raise NotImplementedError()

    def gen_payload(self, msg_id, out_type, msg_count, str_user, json_data):
        raise NotImplementedError()


class OUTWORKUploader(BaseUploader):
    endpoint = "http://10.4.23.101:1010/Service1.asmx?op=TRANS_MES_TO_WMS_OUTWORK"
    dict_filter = {'正常出库': "http://10.4.23.101:1011/Service1.asmx?op=TRANS_MES_TO_WMS_OUTWORK",
                   '指定出库': "http://10.4.23.101:1011/Service1.asmx?op=TRANS_MES_TO_WMS_OUTWORK_KJYC"}

    def __init__(self, end_type):
        self.end_type = end_type
        self.endpoint = self.dict_filter[self.end_type]


    def gen_payload(self, msg_id, r_type, msg_count, str_user, str_json):
        if self.end_type == "正常出库":
            xml_data = """
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                <soap:Body><TRANS_MES_TO_WMS_OUTWORK xmlns="http://www.riamb.ac.cn/asrs/WebService/TA_SAP/">
                    <MsgId>{}</MsgId>
                    <OutType>{}</OutType>
                    <MsgConut>{}</MsgConut>
                    <strUser>{}</strUser>
                    <strJson>{}</strJson>
                </TRANS_MES_TO_WMS_OUTWORK>
                </soap:Body>
            </soap:Envelope>""".format(msg_id, r_type, msg_count, str_user, str_json)
        else:
            xml_data = """
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                <soap:Body><TRANS_MES_TO_WMS_OUTWORK_KJYC xmlns="http://www.riamb.ac.cn/asrs/WebService/TA_SAP/">
                    <MsgId>{}</MsgId>
                    <OutType>{}</OutType>
                    <MsgConut>{}</MsgConut>
                    <strUser>{}</strUser>
                    <strJson>{}</strJson>
                </TRANS_MES_TO_WMS_OUTWORK_KJYC>
                </soap:Body>
            </soap:Envelope>""".format(msg_id, r_type, msg_count, str_user, str_json)
        return xml_data

    def gen_result(self, data):
        if self.end_type == "正常出库":
            data = data.get('soap:Envelope').get('soap:Body').get('TRANS_MES_TO_WMS_OUTWORKResponse').get(
            'TRANS_MES_TO_WMS_OUTWORKResult')
        else:
            data = data.get('soap:Envelope').get('soap:Body').get('TRANS_MES_TO_WMS_OUTWORK_KJYCResponse').get(
                'TRANS_MES_TO_WMS_OUTWORK_KJYCResult')
        # items = json.loads(data).get('items')
        items = json.loads(data)
        # ret = []
        # for item in items:
        #     if item['flag'] != '01':  # 01代表成功
        #         ret.append(item['msg'])
        return items


class OUTWORKUploaderLB(BaseUploader):
    dict_filter = {'正常出库': "http://10.4.23.101:1020/Service1.asmx?op=TRANS_MES_TO_WMS_OUTWORK",
                   '指定出库': "http://10.4.23.101:1020/Service1.asmx?op=TRANS_MES_TO_WMS_OUTWORK_KJYC"}

    def __init__(self, end_type):
        self.end_type = end_type
        self.endpoint = self.dict_filter[self.end_type]

    # endpoint = dict_filter['']

    def gen_payload(self, msg_id, r_type, msg_count, str_user, str_json):
        if self.end_type == "正常出库":
            xml_data = """
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                <soap:Body><TRANS_MES_TO_WMS_OUTWORK xmlns="http://www.riamb.ac.cn/asrs/WebService/TA_SAP/">
                    <MsgId>{}</MsgId>
                    <OutType>{}</OutType>
                    <MsgConut>{}</MsgConut>
                    <strUser>{}</strUser>
                    <strJson>{}</strJson>
                </TRANS_MES_TO_WMS_OUTWORK>
                </soap:Body>
            </soap:Envelope>""".format(msg_id, r_type, msg_count, str_user, str_json)
        else:
            xml_data = """
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                <soap:Body><TRANS_MES_TO_WMS_OUTWORK_KJYC xmlns="http://www.riamb.ac.cn/asrs/WebService/TA_SAP/">
                    <MsgId>{}</MsgId>
                    <OutType>{}</OutType>
                    <MsgConut>{}</MsgConut>
                    <strUser>{}</strUser>
                    <strJson>{}</strJson>
                </TRANS_MES_TO_WMS_OUTWORK_KJYC>
                </soap:Body>
            </soap:Envelope>""".format(msg_id, r_type, msg_count, str_user, str_json)
        return xml_data

    def gen_result(self, data):
        if self.end_type == "正常出库":
            data = data.get('soap:Envelope').get('soap:Body').get('TRANS_MES_TO_WMS_OUTWORKResponse').get(
            'TRANS_MES_TO_WMS_OUTWORKResult')
        else:
            data = data.get('soap:Envelope').get('soap:Body').get('TRANS_MES_TO_WMS_OUTWORK_KJYCResponse').get(
                'TRANS_MES_TO_WMS_OUTWORK_KJYCResult')
        # items = json.loads(data).get('items')
        items = json.loads(data)
        # ret = []
        # for item in items:
        #     if item['flag'] != '01':  # 01代表成功
        #         ret.append(item['msg'])
        print("ret", items)
        return items


def wms_out(url, body, method="POST"):
    header = {
        "Content-Type": "application/json"
    }
    ret = requests.request(method, url, json=body, headers=header)
    return ret.json()


class HFSystem(object):

    def __init__(self):
        self.url = 'http://10.4.24.25:3000/StockService?wsdl'
        self.hf_system = Client(self.url, timeout=3)

    def get_hf_info(self):
        """获取烘箱信息"""
        res = self.hf_system.service.GetOASTDetails()
        res_json = json.loads(res)
        if res_json.get('Result') == '0':
            raise ValueError(res_json.get('Message'))
        return res_json.get('OastDetails')

    def manual_out_hf(self, oast_no):
        """向wcs下发烘箱出库指令 oast_no={'OastNo': '1'}"""
        res = self.hf_system.service.ManualOASTOutTask(json.dumps(oast_no))
        res_json = json.loads(res)
        if res_json.get('Result') == '0':
            raise ValueError(res_json.get('Message'))
        return res_json

    def force_bake(self, data):
        """
        向wcs下发烘箱强制指令
        强制出料: data={'OastNo': '1', 'OastType': 'E'}
        强制烘烤: data={'OastNo': '2', 'OastType': 'S', 'Temperature': 100, 'Duration': 2.5}  wcs请求比mes多一个client参数
        OastNo: 烘箱编号 OastType: 操作类型[E强制出料、S强制烘烤]  Temperature 标准温度  Duration 标准时长
        """
        res = self.hf_system.service.ForceBakeOA(json.dumps(data))
        res_json = json.loads(res)
        if res_json.get('Result') == '0':
            raise ValueError(res_json.get('Message'))
        return f"{data.get('OastNo')}号烘箱强制操作成功"
