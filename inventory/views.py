import json

import requests
from django.shortcuts import render

# Create your views here.
from rest_framework import mixins
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

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
        results = [{
            "sn": 1,
            "material_no": "c-1MB-C9001-01",
            "material_name": "c-1MB-C9001-01",
            "material_type": "1MB",
            "qty": 11,
            "unit": "吨",
            "unit_weight": 1,
            "total_weight": 1,
            "need_weight": 1,
            "standard_flag": True,
            "site": "立库"
        }]
        return Response({'results': results})
