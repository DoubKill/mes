import json

import requests
from django.shortcuts import render

# Create your views here.
from rest_framework import mixins
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from basics.models import GlobalCode
from inventory.models import OutOrderFeedBack
from inventory.serializers import ProductInventorySerializer
from inventory.utils import BaseUploader
from mes.common_code import SqlClient
from mes.conf import WMS_CONF
from recipe.models import Material


class MaterialInventory(GenericViewSet,
                        mixins.ListModelMixin, ):

    def get_queryset(self):
        return

    def data_adapt(self, instance):
        data = {
                "id": instance[8],
                "sn": instance[8],
                "material_no": instance[3],
                "material_name": instance[1],
                "material_type":instance[7],
                "qty": instance[0],
                "unit": instance[6],
                "unit_weight": instance[5],
                "total_weight": instance[2],
                "site": instance[4],
                "standard_flag": True if instance[9] else False,
            }
        return data

    def list(self, request, *args, **kwargs):
        params = request.query_params
        page = params.get("page", 1)
        page_size = params.get("page_size", 10)
        material_type = params.get("material_type")
        if material_type:
            sql = f"""select sum(tis.Quantity) qty, max(tis.MaterialName) material_name,
                           sum(tis.WeightOfActual) weight,tis.MaterialCode material_no,
                           max(tis.ProductionAddress) address, sum(tis.WeightOfActual)/sum(tis.Quantity) unit_weight,
                           max(tis.WeightUnit) unit, max(tim.MaterialGroupName) material_type,
                           Row_Number() OVER (order by tis.MaterialCode) sn, tis.StockDetailState status
                                from t_inventory_stock tis left join t_inventory_material tim on tim.MaterialCode=tis.MaterialCode
                            where tim.MaterialGroupName={material_type}
                            group by tis.MaterialCode, tis.StockDetailState;"""
        else:
            sql = f"""select sum(tis.Quantity) qty, max(tis.MaterialName) material_name,
                                       sum(tis.WeightOfActual) weight,tis.MaterialCode material_no,
                                       max(tis.ProductionAddress) address, sum(tis.WeightOfActual)/sum(tis.Quantity) unit_weight,
                                       max(tis.WeightUnit) unit, max(tim.MaterialGroupName) material_type,
                                       Row_Number() OVER (order by tis.MaterialCode) sn, tis.StockDetailState status
                                            from t_inventory_stock tis left join t_inventory_material tim on tim.MaterialCode=tis.MaterialCode
                                        group by tis.MaterialCode, tis.StockDetailState;"""
        try:
            st = (int(page) - 1) * int(page_size)
            et = int(page) * int(page_size)
        except:
            raise ValidationError("page/page_size异常，请修正后重试")
        else:
            if st not in range(0, 99999):
                raise ValidationError("page/page_size值异常")
            if et not in range(0, 99999):
                raise ValidationError("page/page_size值异常")
        sc = SqlClient(sql=sql, **WMS_CONF)
        temp = sc.all()
        count = len(temp)
        temp = temp[st:et]
        result = []
        for instance in temp:
            result.append(self.data_adapt(instance))
        sc.close()
        return Response({'results': result, "count": count})

        # ret = requests.get("http://49.235.45.128:8169/storageSpace/GetInventoryCount")
        # ret_json = json.loads(ret.text)
        # obj = Material.objects.get(material_no='L7125')
        # results = []
        # for i in ret_json.get("datas"):
        #     results = [{
        #         "sn": 1,
        #         "id": 1,
        #         "material_id": obj.id,
        #         "material_no": i.get('materialCode'),
        #         "material_name": i.get('materialName'),
        #         "material_type_id": obj.material_type_id,
        #         "material_type": obj.material_type.global_type.type_name,
        #         "qty": i.get('quantity'),
        #         "unit": "吨",
        #         "unit_weight": 1,
        #         "total_weight": 1,
        #         "need_weight": 1,
        #         "site": i.get('productionAddress'),
        #         "standard_flag": True,
        #     }]
        # return Response({'results': results})


class ProductInventory(GenericViewSet,
                       mixins.ListModelMixin, ):

    def get_queryset(self):
        return

    def data_adapt(self, instance, material_type):
        material = instance[4].rstrip()
        temp_dict = {
            "sn": instance[5],
            "material_no": material,
            "material_name": material,
            "material_type": material_type,
            "qty": instance[1],
            "unit": "kg",
            "unit_weight": round(instance[2] / instance[1], 2),
            "total_weight": instance[2],
            "need_weight": instance[2],
            "standard_flag": True if instance[3] == "合格品" else False,
            "site": instance[0]
        }
        return temp_dict

    def list(self, request, *args, **kwargs):
        params = request.query_params
        page = params.get("page", 1)
        page_size = params.get("page_size", 10)
        stage = params.get("stage")
        try:
            st = (int(page) - 1) * int(page_size)
            et = int(page) * int(page_size)
        except:
            raise ValidationError("page/page_size异常，请修正后重试")
        else:
            if st not in range(0, 99999):
                raise ValidationError("page/page_size值异常")
            if et not in range(0, 99999):
                raise ValidationError("page/page_size值异常")
        stage_list = GlobalCode.objects.filter(use_flag=True, global_type__use_flag=True,
                                               global_type__type_name="胶料段次").values_list("global_name", flat=True)
        if stage:
            if stage not in stage_list:
                raise ValidationError("胶料段次异常请修正后重试")
            sql = f"""SELECT max(库房名称) as 库房名称, sum(数量) as 数量, sum(重量) as 重量, max(品质状态) as 品质状态, 物料编码, Row_Number() OVER (order by 物料编码) sn
                FROM v_ASRS_STORE_MESVIEW where 物料编码 like '%{stage}%' group by 物料编码"""
        else:
            sql = f"""SELECT max(库房名称) as 库房名称, sum(数量) as 数量, sum(重量) as 重量, max(品质状态) as 品质状态, 物料编码, Row_Number() OVER (order by 物料编码) sn
                FROM v_ASRS_STORE_MESVIEW group by 物料编码"""
        sc = SqlClient(sql=sql)
        temp = sc.all()
        result = []
        for instance in temp:
            try:
                material_type = instance[4].split("-")[1]
            except:
                material_type = instance[4]
            if stage:
                if material_type == stage:
                    self.data_adapt(instance, material_type)
                    result.append(self.data_adapt(instance, material_type))
            else:
                self.data_adapt(instance, material_type)
                result.append(self.data_adapt(instance, material_type))
        count = len(result)
        result = result[st:et]
        sc.close()
        return Response({'results': result, "count": count})


class OutWorkFeedBack(APIView):

    # 出库反馈
    def post(self, request):
        """WMS->MES:任务编号、物料信息ID、物料名称、PDM号（促进剂以外为空）、批号、条码、重量、重量单位、
        生产日期、使用期限、托盘RFID、工位（出库口）、MES->WMS:信息接收成功or失败"""
        # 任务编号
        data = request.data
        if data:
            try:
                OutOrderFeedBack.objects.create(**data)
            except:
                result = {"work_id": data.get("task_id"), "msg": "FALSE"+data.get("material_no")+"物料在库内数量不足!", "flag": "99"}
            else:
                result = {"work_id": data.get("task_id"), "msg": "TRUE"+data.get("material_no")+"下发成功!", "flag": "01"}

            return Response(result)


class OutWork(APIView):
    # 帘布库出库
    class OUTWORKUploader(BaseUploader):
        endpoint = "http://10.4.23.101:1010/Service1.asmx?op=TRANS_MES_TO_WMS_OUTWORK"

        def gen_payload(self, msg_id, r_type, msg_count, str_user, str_json):
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
            return xml_data

        def gen_result(self, data):
            data = data.get('soap:Envelope').get('soap:Body').get('TRANS_MES_TO_WMS_OUTWORKResponse').get(
                'TRANS_MES_TO_WMS_OUTWORKResult')
            # items = json.loads(data).get('items')
            items = json.loads(data)
            print(items)
            # ret = []
            # for item in items:
            #     if item['flag'] != '01':  # 01代表成功
            #         ret.append(item['msg'])
            return items

    def get_base_data(self, sender):
        data_json = {
            "msgId": "1",
            "KJTYPE": "物料快检",
            "msgConut": "2",
            "SENDUSER": self.request.user.username,
            "items": [
                {"WORKID": "11223",
                 "MID": "C-HMB-F150-12",
                 "PICI": "20200101",
                 "NUM": "100",
                 "KJJG": "合格",
                 "SENDDATE":
                     "20200513 09:22:22"
                 },
                {"WORKID": "11224",
                 "MID": "C-HMB-F150-11",
                 "PICI": "20200101",
                 "NUM": "100",
                 "KJJG": "不合格",
                 "SENDDATE": "20200513 09:22:22"}
            ]
            }
        return "1", "物料快检", "2", "GJ_001", json.dumps(data_json, ensure_ascii=False)

    # 出库
    def post(self, request):
        sender = self.OUTWORKUploader()
        ret = sender.request(*self.get_base_data(sender))
        return Response(ret)


class OutWorkGum(APIView):
    # 混炼胶库出库
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
            items = json.loads(data).get('items')
            print(items)
            ret = []
            for item in items:
                if item['flag'] != '01':  # 01代表成功
                    ret.append(item['msg'])
            return ret

    def get_base_data(self, sender):
        data_json = {
            "msgId": "1",
            "KJTYPE": "物料快检",
            "msgConut": "2",
            "SENDUSER": self.request.user.username,
            "items": [
                {"WORKID": "11223",
                 "MID": "C-HMB-F150-12",
                 "PICI": "20200101",
                 "NUM": "100",
                 "KJJG": "合格",
                 "SENDDATE":
                     "20200513 09:22:22"
                 },
                {"WORKID": "11224",
                 "MID": "C-HMB-F150-11",
                 "PICI": "20200101",
                 "NUM": "100",
                 "KJJG": "不合格",
                 "SENDDATE": "20200513 09:22:22"}
            ]
            }
        return "1", "物料快检", "2", "GJ_001", json.dumps(data_json, ensure_ascii=False)

    # 出库
    def post(self, request):
        sender = self.KJJGUploader()
        ret = sender.request(*self.get_base_data(sender))
        return Response(ret)
