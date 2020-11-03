# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/10/29
name: 
"""
import requests
import xmltodict


class BaseUploader(object):
    endpoint = ""

    def request(self, msg_id, out_type, msg_count, str_user, json_data):
        print(json_data)
        if not self.endpoint:
            raise NotImplementedError('未设置endpoint')
        pay_load = self.gen_payload(msg_id, out_type, msg_count, str_user, json_data)
        headers = {
            "Content-Type": "text/xml; charset=utf-8"
        }
        pay_load = pay_load.encode('utf-8')
        resp = requests.post(self.endpoint, data=pay_load, headers=headers)
        if resp.status_code != 200:
            raise Exception(resp.content)
        resp_xml = resp.text
        json_data = xmltodict.parse(resp_xml)
        print(json_data)
        print('json_data')
        return self.gen_result(json_data)

    def gen_result(self, data):
        raise NotImplementedError()

    def gen_payload(self, msg_id, out_type, msg_count, str_user, json_data):
        raise NotImplementedError()

    def gen_task_id(self):
        #TODO
        pass
    def gen_order_id(self):
        #TODO
        pass




