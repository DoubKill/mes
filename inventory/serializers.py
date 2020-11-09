# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/10/14
name: 
"""
from rest_framework import serializers
from .models import MaterialInventory, BzFinalMixingRubberInventory, WmsInventoryStock, WmsInventoryMaterial


class ProductInventorySerializer(serializers.Serializer):
    库房编号 = serializers.CharField(read_only=True)
    库房名称 = serializers.CharField(read_only=True)
    订单号 = serializers.CharField(read_only=True)
    托盘号 = serializers.CharField(read_only=True)
    货位地址 = serializers.CharField(read_only=True)
    数量 = serializers.DecimalField(decimal_places=3, max_digits=15)
    重量 = serializers.DecimalField(decimal_places=3, max_digits=15)
    品质状态 = serializers.CharField(read_only=True)
    车号 = serializers.CharField(read_only=True)
    库存索引 = serializers.IntegerField(read_only=True)
    物料编码 = serializers.CharField(read_only=True)


class XBKMaterialInventorySerializer(serializers.ModelSerializer):
    material_type = serializers.CharField(source='material.material_type.global_name', default='')
    material_no = serializers.CharField(source='material.material_no', default='')

    class Meta:
        model = MaterialInventory
        fields = ['material_type',
                  'material_no',
                  'lot_no'
                  'container_no',
                  'location',
                  'qty',
                  'unit',
                  'unit_weight',
                  'total_weight',
                  'quality_status']


class BzFinalMixingRubberInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BzFinalMixingRubberInventory
        fields = [
                  'id',
                  'material_type',
                  'material_no',
                  'lot_no',
                  'container_no',
                  'location',
                  'qty',
                  'unit',
                  'unit_weight',
                  'total_weight',
                  'quality_status',
                  'memo'
                  ]


class WmsInventoryStockSerializer(serializers.ModelSerializer):

    class Meta:
        model = WmsInventoryStock
        fields = ['material_type',
                  'material_no',
                  'lot_no',
                  'container_no',
                  'location',
                  'qty',
                  'unit',
                  'unit_weight',
                  'total_weight',
                  'quality_status']



