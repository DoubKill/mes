import json

import requests
from django.shortcuts import render

# Create your views here.
from rest_framework import mixins
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from basics.models import GlobalCode
from inventory.serializers import ProductInventorySerializer
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
                "standard_flag": True,
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
                           Row_Number() OVER (order by tis.MaterialCode) sn
                                from t_inventory_stock tis left join t_inventory_material tim on tim.MaterialCode=tis.MaterialCode
                            where tim.MaterialGroupName={material_type}
                            group by tis.MaterialCode;"""
        else:
            sql = f"""select sum(tis.Quantity) qty, max(tis.MaterialName) material_name,
                                       sum(tis.WeightOfActual) weight,tis.MaterialCode material_no,
                                       max(tis.ProductionAddress) address, sum(tis.WeightOfActual)/sum(tis.Quantity) unit_weight,
                                       max(tis.WeightUnit) unit, max(tim.MaterialGroupName) material_type,
                                       Row_Number() OVER (order by tis.MaterialCode) sn
                                            from t_inventory_stock tis left join t_inventory_material tim on tim.MaterialCode=tis.MaterialCode
                                        group by tis.MaterialCode;"""
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
