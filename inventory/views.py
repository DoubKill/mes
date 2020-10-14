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
from recipe.models import Material


class MaterialInventory(GenericViewSet,
                        mixins.ListModelMixin, ):

    def get_queryset(self):
        return

    def list(self, request, *args, **kwargs):
        ret = requests.get("http://49.235.45.128:8169/storageSpace/GetInventoryCount")
        ret_json = json.loads(ret.text)
        obj = Material.objects.get(material_no='L7125')
        results = []
        for i in ret_json.get("datas"):
            results = [{
                "sn": 1,
                "id": 1,
                "material_id": obj.id,
                "material_no": i.get('materialCode'),
                "material_name": i.get('materialName'),
                "material_type_id": obj.material_type_id,
                "material_type": obj.material_type.global_type.type_name,
                "qty": i.get('quantity'),
                "unit": "吨",
                "unit_weight": 1,
                "total_weight": 1,
                "need_weight": 1,
                "site": i.get('productionAddress'),
                "standard_flag": True,
            }]
        return Response({'results': results})


class ProductInventory(GenericViewSet,
                       mixins.ListModelMixin, ):

    def get_queryset(self):
        return

    # TODO
    def list(self, request, *args, **kwargs):
        # TODO 补充
        params = request.query_params
        page = params.get("page", 1)
        page_size = params.get("page_size", 10)
        stage = params.get("stage")
        try:
            st = (int(page) - 1) * int(page_size) + 1
            et = int(page) * int(page_size)
        except:
            raise ValidationError("page/page_size异常，请修正后重试")
        else:
            if st not in range(1, 99999):
                raise ValidationError("page/page_size值异常")
            if st not in range(1, 99999):
                raise ValidationError("page/page_size值异常")
        stage_list = GlobalCode.objects.filter(use_flag=True, global_type__use_flag=True,
                                               global_type__type_name="胶料段次").values_list("global_name", flat=True)
        if stage:
            if stage not in stage_list:
                raise ValidationError("胶料段次异常请修正后重试")
            sql = f"""select * from (SELECT *, Row_Number() OVER (order by 库存索引) id FROM v_ASRS_STORE_MESVIEW where 
                物料编码 like '%{stage}%') as temp where temp.id between {st} and {et}"""
            sql_count = f"""select count(*) from v_ASRS_STORE_MESVIEW where 物料编码 like '%{stage}%'"""
        else:
            sql = f"""select * from (SELECT *, Row_Number() OVER (order by 库存索引) id FROM v_ASRS_STORE_MESVIEW) as temp  \
                              where temp.id between {st} and {et}"""
            sql_count = f"""select count(*) from v_ASRS_STORE_MESVIEW"""
        sc = SqlClient(sql=sql)
        temp = sc.all()
        count = sc.count(sql_count)
        # sz = ProductInventorySerializer(temp, many=True)
        result = []
        for instance in temp:
            try:
                material_type = instance[10].split("-")[1]
            except:
                material_type = instance[10]
            material = instance[10].rstrip()
            temp_dict = {
                "sn": instance[11],
                "material_no": material,
                "material_name": material,
                "material_type": material_type,
                "qty": instance[5],
                "unit": "kg",
                "unit_weight": round(instance[6] / instance[5], 2),
                "total_weight": instance[6],
                "need_weight": instance[6],
                "standard_flag": True,
                "site": instance[1]
            }
            result.append(temp_dict)
        sc.close()
        return Response({'results': result, "count": count})
