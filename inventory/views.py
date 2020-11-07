import json
import time

import requests
from django.shortcuts import render

# Create your views here.
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from basics.models import GlobalCode
from inventory.filters import PutPlanManagementFilter
from inventory.models import OutOrderFeedBack, DeliveryPlan, MaterialInventory
from inventory.serializers import ProductInventorySerializer, PutPlanManagementSerializer, \
    OverdueMaterialManagementSerializer
from inventory.models import OutOrderFeedBack, WmsInventoryStock
from inventory.serializers import ProductInventorySerializer, BzFinalMixingRubberInventorySerializer, \
    WmsInventoryStockSerializer
from inventory.utils import BaseUploader
from mes.common_code import SqlClient
from mes.conf import WMS_CONF
from mes.derorators import api_recorder
from recipe.models import Material
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions
from .models import MaterialInventory as XBMaterialInventory
from .models import BzFinalMixingRubberInventory
from .serializers import XBKMaterialInventorySerializer


class MaterialInventoryView(GenericViewSet,
                        mixins.ListModelMixin, ):

    def get_queryset(self):
        return

    def data_adapt(self, instance):
        data = {
            "id": instance[8],
            "sn": instance[8],
            "material_no": instance[3],
            "material_name": instance[1],
            "material_type": instance[7],
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
                result = {"work_id": data.get("task_id"), "msg": "FALSE" + data.get("material_no") + "物料在库内数量不足!",
                          "flag": "99"}
            else:
                result = {"work_id": data.get("task_id"), "msg": "TRUE" + data.get("material_no") + "下发成功!",
                          "flag": "01"}

            return Response(result)


class OutWork(ModelViewSet):
    queryset = DeliveryPlan.objects.filter()
    serializer_class = PutPlanManagementSerializer
    # 帘布库出库
    # class OUTWORKUploader(BaseUploader):
    #     endpointloa = "http://10.4.23.101:1010/Service1.asmx?op=TRANS_MES_TO_WMS_OUTWORK"
    #
    #     def gen_payd(self, msg_id, r_type, msg_count, str_user, str_json):
    #         xml_data = """
    #         <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    #             <soap:Body><TRANS_MES_TO_WMS_OUTWORK xmlns="http://www.riamb.ac.cn/asrs/WebService/TA_SAP/">
    #                 <MsgId>{}</MsgId>
    #                 <OutType>{}</OutType>
    #                 <MsgConut>{}</MsgConut>
    #                 <strUser>{}</strUser>
    #                 <strJson>{}</strJson>
    #             </TRANS_MES_TO_WMS_OUTWORK>
    #             </soap:Body>
    #         </soap:Envelope>""".format(msg_id, r_type, msg_count, str_user, str_json)
    #         return xml_data
    #
    #     def gen_result(self, data):
    #         print(data)
    #         print('ssssssssssssssssssssssssssssssssssssssssss')
    #         data = data.get('soap:Envelope').get('soap:Body').get('TRANS_MES_TO_WMS_OUTWORKResponse').get(
    #             'TRANS_MES_TO_WMS_OUTWORKResult')
    #         # items = json.loads(data).get('items')
    #         items = json.loads(data)
    #         print("hhahahahahahahaha")
    #         print(items)
    #         # ret = []
    #         # for item in items:
    #         #     if item['flag'] != '01':  # 01代表成功
    #         #         ret.append(item['msg'])
    #         return items

    def get_base_data(self, sender,request):
        # data_json ={}
        # items =[]
        # params = request.data
        # msgId = time.strftime("%Y%m%d%H%M%S", time.localtime())
        # OUTTYPE = params.get('OUTTYPE','1')
        # msgConut = params.get('msgConut','1')
        # SENDUSER = request.user.username
        # items = params.get('items')
        # # for i in items:
        # #     i['WORKID']=i['MID']
        # data_json ={'msgId':msgId,"OUTTYPE":OUTTYPE,'msgConut':msgConut,'SENDUSER':SENDUSER,
        #             "items": [
        #                 {"WORKID": "11223",
        #                  "MID": "C-HMB-F150-12",
        #                  "PICI": "20200101",
        #                  "NUM": "1",
        #                  "STATIONID": "二层后端",
        #                  "SENDDATE": "20200513 09:22:22"},
        #                 {"WORKID": "11227",
        #                  "MID": "C-HMB-F150-11",
        #                  "PICI": "20200101",
        #                  "NUM": "1",
        #                  "STATIONID": "二层前端",
        #                  "SENDDATE": "20200513 09:22:22"}
        #             ]
        #             }

        # ................................
        data_json = {
            "msgId": "1",
            "OUTTYPE": "生产出库",
            "msgConut": "2",
            "SENDUSER": "GJ_001",
            "items": [
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
        }

        return "1", "生产出库", "2", "GJ_001", json.dumps(data_json, ensure_ascii=False)
    def get_base_data(self, sender, request):
        data_json = {}
        items = []
        params = request.data
        msgId = time.strftime("%Y%m%d%H%M%S", time.localtime())
        OUTTYPE = params.get('OUTTYPE', '1')
        msgConut = params.get('msgConut', '1')
        SENDUSER = request.user.username
        items = params.get('items')
        # for i in items:
        #     i['WORKID']=i['MID']
        data_json = {'msgId': msgId, "OUTTYPE": OUTTYPE, 'msgConut': msgConut, 'SENDUSER': SENDUSER,
                     "items": [
                         {"WORKID": "11223",
                          "MID": "C-HMB-F150-12",
                          "PICI": "20200101",
                          "NUM": "1",
                          "STATIONID": "二层后端",
                          "SENDDATE": "20200513 09:22:22"},
                         {"WORKID": "11227",
                          "MID": "C-HMB-F150-11",
                          "PICI": "20200101",
                          "NUM": "1",
                          "STATIONID": "二层前端",
                          "SENDDATE": "20200513 09:22:22"}
                     ]
                     }
        # data_json = {
        # "msgId": "hzy11",
        # "OUTTYPE": "生产出库123222",
        # "msgConut": "2",
        # "SENDUSER": "GJ_001hzy",
        # "items": [
        #      {"WORKID": "11223",
        #       "MID": "C-HMB-F150-12",
        #       "PICI": "20200101",
        #       "NUM": "1",
        #       "STATIONID": "二层后端",
        #       "SENDDATE": "20200513 09:22:22"},
        #      {"WORKID": "11227",
        #       "MID": "C-HMB-F150-11",
        #       "PICI": "20200101",
        #       "NUM": "1",
        #       "STATIONID": "二层前端",
        #       "SENDDATE": "20200513 09:22:22"}
        #  ]
        # }
        # ticks = time.strftime("%Y%m%d%H%M%S", time.localtime()) + data_json.get('msgId')
        # items = data_json.get('items')
        # for i in items:
        #     i.get('WORKID')
        #     ticks = time.strftime("%Y%m%d%H%M%S", time.localtime()) + i.get('WORKID')
        # print(data_json.get('msgId'))
        # print(ticks)
        # msgId = ticks
        # print(msgId)
        return "1", "1", "1", "1", json.dumps(data_json, ensure_ascii=False)

    # 出库
    def post(self, request):
        print(request.user.username)
        sender = self.OUTWORKUploader()
        ret = sender.request(*self.get_base_data(sender,request))
        print("eeesasdasdsada")
        print(ret)
        # items = ret['items']
        # for i in items:
        #     print(i['WORKID'])

        ret = sender.request(*self.get_base_data(sender, request))
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
            "OUTTYPE": "生产出库",
            "msgConut": "2",
            "SENDUSER": "GJ_001",
            "items": [
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
        }
        return "1", "生产出库", "2", "GJ_001", json.dumps(data_json, ensure_ascii=False)

    # 出库
    def post(self, request):
        sender = self.KJJGUploader()
        ret = sender.request(*self.get_base_data(sender))
        return Response(ret)

@method_decorator([api_recorder], name="dispatch")
class PutPlanManagement(ModelViewSet):
    queryset = DeliveryPlan.objects.filter().order_by("-created_date")
    serializer_class = PutPlanManagementSerializer
    filter_backends = [DjangoFilterBackend]
    filter_class = PutPlanManagementFilter


    # def create(self, request, *args, **kwargs):
    #     data = request.data
    #     if not isinstance(data, list):
    #         raise ValidationError('参数错误')
    #     for item in data:
    #         s = PutPlanManagementSerializer(data=item, context={'request': request})
    #         if not s.is_valid():
    #             raise ValidationError(s.errors)
    #         s.save()
    #     return Response('新建成功')


@method_decorator([api_recorder], name="dispatch")
class OverdueMaterialManagement(ModelViewSet):
    queryset = MaterialInventory.objects.filter()
    serializer_class = OverdueMaterialManagementSerializer
    filter_backends = [DjangoFilterBackend]




class MaterialInventoryManageViewSet(viewsets.ReadOnlyModelViewSet):
    """物料库存信息|线边库|终炼胶库|原材料库"""

    MODEL, SERIALIZER = 0, 1
    INVENTORY_MODEL_BY_NAME = {
        '线边库': [XBMaterialInventory, XBKMaterialInventorySerializer],
        '终炼胶库': [BzFinalMixingRubberInventory, BzFinalMixingRubberInventorySerializer],
        '原材料库': [WmsInventoryStock, WmsInventoryStockSerializer]
    }
    permission_classes = (permissions.IsAuthenticated,)

    # filter_backends = (DjangoFilterBackend,)

    def divide_tool(self, index):
        warehouse_name = self.request.query_params.get('warehouse_name', None)
        if warehouse_name and warehouse_name in self.INVENTORY_MODEL_BY_NAME:
            return self.INVENTORY_MODEL_BY_NAME[warehouse_name][index]
        else:
            raise ValidationError('无此仓库名')

    def get_query_params(self):
        for query in 'material_type', 'container_no', 'material_no':
            yield self.request.query_params.get(query, None)

    def get_queryset(self):
        model = self.divide_tool(self.MODEL)
        queryset = None
        material_type, container_no, material_no = self.get_query_params()
        if model == XBMaterialInventory:
            queryset = model.objects.all()
        elif model == BzFinalMixingRubberInventory:
            queryset = model.objects.using('bz').all()
        if queryset:
            if material_type and model != BzFinalMixingRubberInventory:
                queryset = queryset.filter(material_type__icontains=material_type)
            if material_no:
                queryset = queryset.filter(material_no__icontains=material_no)
            if container_no:
                queryset = queryset.filter(container_no__icontains=container_no)
            return queryset
        if model == WmsInventoryStock:
            queryset = model.objects.using('wms').raw(WmsInventoryStock.get_sql(material_type, material_no))
        return queryset

    def get_serializer_class(self):
        return self.divide_tool(self.SERIALIZER)
