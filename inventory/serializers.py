# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/10/14
name: 
"""
import json
import time

from django.db.models import Sum
from rest_framework import serializers
from .models import MaterialInventory, BzFinalMixingRubberInventory, WmsInventoryStock, WmsInventoryMaterial


from inventory.models import DeliveryPlan, DeliveryPlanStatus, InventoryLog, MaterialInventory
from inventory.utils import OUTWORKUploader
from production.models import PalletFeedbacks


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


class PutPlanManagementSerializer(serializers.ModelSerializer):
    no = serializers.CharField(source="warehouse_info.no", read_only=True)
    name = serializers.CharField(source="warehouse_info.name",read_only=True)
    actual = serializers.SerializerMethodField(read_only=True)

    def get_actual(self, object):
        order_no = object.order_no
        actual = InventoryLog.objects.filter(order_no=order_no).aggregate(actual_qty=Sum('qty'), actual_weight=Sum('wegit'))
        actual_qty = actual['actual_qty']
        actual_wegit = actual['actual_weight']
        # 无法合计
        # actual_wegit = InventoryLog.objects.values('wegit').annotate(actual_wegit=Sum('wegit')).filter(order_no=order_no)
        items = {'actual_qty':actual_qty,'actual_wegit':actual_wegit}
        return items


    def create(self, validated_data):


        deliveryplan = DeliveryPlan.objects.create(**validated_data)
        warehouse_info = validated_data['warehouse_info']
        order_no = validated_data['order_no']
        order_type = validated_data['order_type']
        status = validated_data['status']
        DeliveryPlanStatus.objects.create(warehouse_info = warehouse_info,
                                                               order_no = order_no,
                                                               order_type = order_type,
                                                               status = status
                                                               )

        return deliveryplan

    def update(self, instance, validated_data):
        msg_id = validated_data['order_no']
        out_type = validated_data['inventory_type']
        str_user = self.context['request'].user.username
        material_no = validated_data['material_no']
        # wegit = validated_data['need_weight']
        wegit = "1"
        msg_count = "1"
        # location = validated_data['location']
        location = "二层后端"
        # created_date = validated_data['created_date']
        created_date = "20200513 09:22:22"
        WORKID = time.strftime("%Y%m%d%H%M%S", time.localtime())
        # 无批次号
        dict1 = {'WORKID':WORKID,'MID':material_no,'PICI':1,'NUM':wegit,
                 'STATIONID':location,'SENDDATE':created_date}
        items =[]
        items.append(dict1)
        json_data = {
            'msgId': msg_id,
            'OUTTYPE': out_type,
            "msgConut": msg_count,
            "SENDUSER": str_user,
            "items": items
        }
        # msg_count = len(json_data["items"])
        # json_data["msgConut"] = msg_count
        json_data = json.dumps(json_data, ensure_ascii=False)
        sender = OUTWORKUploader()
        result = sender.request(msg_id, out_type, msg_count, str_user, json_data)
        if result is not None:
            items = result['items']
            msg = items[0]['msg']
            msg = "TRUE"
            if msg:
                instance.status = 2
                validated_data['status'] = instance.status
                instance = super().update(instance,validated_data)
                warehouse_info = validated_data['warehouse_info']
                order_no = validated_data['order_no']
                order_type = validated_data['order_type']
                status = instance.status
                DeliveryPlanStatus.objects.create(warehouse_info=warehouse_info,
                                                  order_no=order_no,
                                                  order_type=order_type,
                                                  status=status
                                                  )
                return instance
            else:
                instance.status = 3
                warehouse_info = validated_data['warehouse_info']
                order_no = validated_data['order_no']
                order_type = validated_data['order_type']
                status = instance.status
                DeliveryPlanStatus.objects.create(warehouse_info=warehouse_info,
                                                  order_no=order_no,
                                                  order_type=order_type,
                                                  status=status
                                                  )
                instance.save()
                raise serializers.ValidationError('出库失败')

    # def update_planStatus(self):

    class Meta:
        model = DeliveryPlan
        fields = '__all__'
        # read_only_fields = COMMON_READ_ONLY_FIELDS

class OverdueMaterialManagementSerializer(serializers.ModelSerializer):

    material_no = serializers.CharField(source="material.material_no", read_only=True) # 物料编码
    pf_obj = serializers.SerializerMethodField(read_only=True) # 班次 机台号 生产时间
    # material_obj = serializers.SerializerMethodField(read_only=True) # 物料属性

    def get_pf_obj(self, object):
        lot_no = object.lot_no
        pf_obj = PalletFeedbacks.objects.filter(lot_no=lot_no).first()
        if not pf_obj:
            return None
        else:
            classes =  pf_obj.classes
            equip_no = pf_obj.equip_no
            product_time = pf_obj.product_time
            items = {'classes': classes, 'equip_no': equip_no,'product_time':product_time}
            return items

    # def get_material_obj(self,object):
    #     material_no = object.material_no
    #
    #     pass


    class Meta:
        model = MaterialInventory
        fields = '__all__'


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



