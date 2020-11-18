# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/10/14
name: 
"""
import datetime
import json
import time

from django.db.models import Sum
from django.db.transaction import atomic
from rest_framework import serializers

from basics.models import GlobalCode
from recipe.models import MaterialAttribute
from .models import MaterialInventory, BzFinalMixingRubberInventory, WmsInventoryStock, WmsInventoryMaterial, \
    WarehouseInfo, Station, WarehouseMaterialType, DeliveryPlanLB

from inventory.models import DeliveryPlan, DeliveryPlanStatus, InventoryLog, MaterialInventory
from inventory.utils import OUTWORKUploader, OUTWORKUploaderLB
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
    name = serializers.CharField(source="warehouse_info.name", read_only=True)
    actual = serializers.SerializerMethodField(read_only=True)
    order_no = serializers.CharField(required=False)
    quality_status = serializers.CharField(required=False)

    def get_actual(self, object):
        order_no = object.order_no
        actual = InventoryLog.objects.filter(order_no=order_no).aggregate(actual_qty=Sum('qty'),
                                                                          actual_weight=Sum('weight'))
        actual_qty = actual['actual_qty']
        actual_weight = actual['actual_weight']
        # 无法合计
        # actual_wegit = InventoryLog.objects.values('wegit').annotate(actual_wegit=Sum('wegit')).filter(order_no=order_no)
        items = {'actual_qty': actual_qty, 'actual_wegit': actual_weight}
        return items

    @atomic()
    def create(self, validated_data):
        order_no = time.strftime("%Y%m%d%H%M%S", time.localtime())
        inventory_type = validated_data.get('inventory_type') #  出入库类型

        material_no = validated_data['material_no']
        need_qty = validated_data['need_qty']
        warehouse_info = validated_data['warehouse_info']
        status = validated_data['status']
        pallet_no = validated_data.get('pallet_no')
        unit = validated_data.get('unit')
        need_weight = validated_data.get('need_weight')
        location = validated_data.get('location')
        created_user = self.context['request'].user.username
        order_type = validated_data.get('order_type','出库')  # 订单类型
        inventory_reason = validated_data.get('quality_status')      # 出入库原因

        deliveryplan = DeliveryPlan.objects.create(order_no=order_no,
                                                   inventory_type=inventory_type,
                                                   material_no=material_no,
                                                   need_qty=need_qty,
                                                   warehouse_info=warehouse_info,
                                                   status=status,
                                                   order_type=order_type,
                                                   pallet_no=pallet_no,
                                                   unit=unit,
                                                   need_weight=need_weight,
                                                   created_user=created_user,
                                                   location=location,
                                                   inventory_reason=inventory_reason #出库原因
                                                   )
        DeliveryPlanStatus.objects.create(warehouse_info=warehouse_info,
                                          order_no=order_no,
                                          order_type=order_type,
                                          status=status,
                                          created_user=created_user,
                                          )
        # dps_dict = {'warehouse_info': warehouse_info,
        #             'order_no': order_no,
        #             "order_type": order_type,
        #             "status": status}
        #
        # self.create_dps(DeliveryPlan, dps_dict)
        return deliveryplan


    def update(self, instance, validated_data):
        out_type = validated_data.get('inventory_type')
        status = validated_data.get('status')
        inventory_reason = validated_data.get('inventory_reason')
        if (inventory_reason == '一等品'):
            djjg = "一等品"
        elif (inventory_reason == '三等品'):
            djjg = "三等品"
        else:
            djjg = "三等品"
        if out_type == "正常出库" or out_type == "指定出库":
            msg_id = validated_data['order_no']
            str_user = self.context['request'].user.username
            material_no = validated_data['material_no']
            pallet_no = validated_data.get('pallet_no', "20120001")  # 托盘号
            pici = "1"  # 批次号
            num = validated_data.get('need_qty', '1')
            msg_count = "1"
            location = "二层后端"
            # 发起时间
            time = validated_data.get('created_date', datetime.datetime.now())
            created_time = time.strftime('%Y%m%d %H:%M:%S')
            WORKID = time.strftime("%Y%m%d%H%M%S")
            dict1 = {}
            if out_type == "指定出库":
                dict1 = {'WORKID': WORKID, 'MID': material_no, 'PICI': pici, 'RFID': pallet_no,
                         'STATIONID': location, 'SENDDATE': created_time}
            elif out_type == "正常出库":
                dict1 = {'WORKID': WORKID, 'MID': material_no, 'PICI': pici, 'NUM': num,'DJJG':djjg,
                         'STATIONID': location, 'SENDDATE': created_time}

        # 北自接口类型区分
                # 出库类型  一等品 = 生产出库   三等品 = 快检异常出库
            if inventory_reason =='一等品':
                bz_out_type = "生产出库"
            elif inventory_reason =='三等品':
                bz_out_type = "快检出库"
            else:
                bz_out_type = "生产出库"
            items = []
            items.append(dict1)
            json_data = {
                'msgId': msg_id,
                'OUTTYPE': bz_out_type,
                "msgConut": msg_count,
                "SENDUSER": str_user,
                "items": items
            }
            json_data = json.dumps(json_data, ensure_ascii=False)
            sender = OUTWORKUploader(end_type=out_type)
            result = sender.request(msg_id, out_type, msg_count, str_user, json_data)
            if result is not None:
                try:
                    items = result['items']
                    msg = items[0]['msg']
                except:
                    msg = result[0]['msg']
                warehouse_info = validated_data['warehouse_info']
                order_no = validated_data['order_no']
                order_type = validated_data['inventory_type']
                created_user = self.context['request'].user.username
                created_date = datetime.datetime.now()
                if "TRUE" in msg:
                    instance.status = 2
                    instance.last_updated_date = datetime.datetime.now()
                    instance.save()
                    status = instance.status
                    DeliveryPlanStatus.objects.create(warehouse_info=warehouse_info,
                                                      order_no=order_no,
                                                      order_type=order_type,
                                                      status=status,
                                                      created_user=created_user,
                                                      created_date=created_date
                                                      )
                    return instance
                else:
                    instance.status = 3
                    DeliveryPlanStatus.objects.create(warehouse_info=warehouse_info,
                                                      order_no=order_no,
                                                      order_type=order_type,
                                                      status=3,
                                                      created_user=created_user,
                                                      created_date=created_date
                                                      )
                    instance.save()
                    if "不足" in msg:
                        raise serializers.ValidationError('库存不足, 出库失败')
                    elif "json错误" in msg:
                        raise serializers.ValidationError(f'出库接口调用失败,提示: {msg}')
                    else:
                        raise serializers.ValidationError(msg)
        else:
            if status == 5:
                instance.status = status
                instance.save()
                return instance
            else:
                need_qty = validated_data['need_qty']
                instance.need_qty = need_qty
                instance.save()
                return instance


    class Meta:
        model = DeliveryPlan
        fields = '__all__'
        # read_only_fields = COMMON_READ_ONLY_FIELDS


class PutPlanManagementSerializerLB(serializers.ModelSerializer):
    no = serializers.CharField(source="warehouse_info.no", read_only=True)
    name = serializers.CharField(source="warehouse_info.name", read_only=True)
    actual = serializers.SerializerMethodField(read_only=True)
    order_no = serializers.CharField(required=False)
    quality_status = serializers.CharField(required=False)

    def get_actual(self, object):
        order_no = object.order_no
        actual = InventoryLog.objects.filter(order_no=order_no).aggregate(actual_qty=Sum('qty'),
                                                                          actual_weight=Sum('weight'))
        actual_qty = actual['actual_qty']
        actual_weight = actual['actual_weight']
        # 无法合计
        # actual_wegit = InventoryLog.objects.values('wegit').annotate(actual_wegit=Sum('wegit')).filter(order_no=order_no)
        items = {'actual_qty': actual_qty, 'actual_wegit': actual_weight}
        return items

    @atomic()
    def create(self, validated_data):
        order_no = time.strftime("%Y%m%d%H%M%S", time.localtime())
        inventory_type = validated_data.get('inventory_type') #  出入库类型

        material_no = validated_data['material_no']
        need_qty = validated_data['need_qty']
        warehouse_info = validated_data['warehouse_info']
        status = validated_data['status']
        pallet_no = validated_data.get('pallet_no')
        unit = validated_data.get('unit')
        need_weight = validated_data.get('need_weight')
        location = validated_data.get('location')
        created_user = self.context['request'].user.username
        order_type = validated_data.get('order_type','出库')  # 订单类型
        inventory_reason = validated_data.get('quality_status')      # 出入库原因

        deliveryplan = DeliveryPlan.objects.create(order_no=order_no,
                                                   inventory_type=inventory_type,
                                                   material_no=material_no,
                                                   need_qty=need_qty,
                                                   warehouse_info=warehouse_info,
                                                   status=status,
                                                   order_type=order_type,
                                                   pallet_no=pallet_no,
                                                   unit=unit,
                                                   need_weight=need_weight,
                                                   created_user=created_user,
                                                   location=location,
                                                   inventory_reason=inventory_reason #出库原因
                                                   )
        DeliveryPlanStatus.objects.create(warehouse_info=warehouse_info,
                                          order_no=order_no,
                                          order_type=order_type,
                                          status=status,
                                          created_user=created_user,
                                          )
        # dps_dict = {'warehouse_info': warehouse_info,
        #             'order_no': order_no,
        #             "order_type": order_type,
        #             "status": status}
        #
        # self.create_dps(DeliveryPlan, dps_dict)
        return deliveryplan


    def update(self, instance, validated_data):
        out_type = validated_data.get('inventory_type')
        status = validated_data.get('status')
        inventory_reason = validated_data.get('inventory_reason')
        if "不" in inventory_reason:
            djjg = "不合格品"
        else:
            djjg = "合格品"
        if out_type == "正常出库" or out_type == "指定出库":
            msg_id = validated_data['order_no']
            str_user = self.context['request'].user.username
            material_no = validated_data['material_no']
            pallet_no = validated_data.get('pallet_no', "20120001")  # 托盘号
            pici = "1"  # 批次号
            num = validated_data.get('need_qty', '1')
            msg_count = "1"
            location = "二层后端"
            # 发起时间
            time = validated_data.get('created_date', datetime.datetime.now())
            created_time = time.strftime('%Y%m%d %H:%M:%S')
            WORKID = time.strftime("%Y%m%d%H%M%S")
            dict1 = {}
            if out_type == "指定出库":
                dict1 = {'WORKID': WORKID, 'MID': material_no, 'PICI': pici, 'RFID': pallet_no,
                         'STATIONID': location, 'SENDDATE': created_time}
            elif out_type == "正常出库":
                dict1 = {'WORKID': WORKID, 'MID': material_no, 'PICI': pici, 'NUM': num, 'DJJG': djjg,
                         'STATIONID': location, 'SENDDATE': created_time}

            # 北自接口类型区分
            # 出库类型  一等品 = 生产出库   三等品 = 快检异常出库
            if inventory_reason =='一等品':
                bz_out_type = "生产出库"
            elif inventory_reason =='三等品':
                bz_out_type = "快检出库"
            else:
                bz_out_type = "生产出库"
            items = []
            items.append(dict1)
            json_data = {
                'msgId': msg_id,
                'OUTTYPE': bz_out_type,
                "msgConut": msg_count,
                "SENDUSER": str_user,
                "items": items
            }
            json_data = json.dumps(json_data, ensure_ascii=False)
            sender = OUTWORKUploaderLB(end_type=out_type)
            result = sender.request(msg_id, out_type, msg_count, str_user, json_data)
            if result is not None:
                try:
                    items = result['items']
                    msg = items[0]['msg']
                except:
                    msg = result[0]['msg']
                warehouse_info = validated_data['warehouse_info']
                order_no = validated_data['order_no']
                order_type = validated_data['inventory_type']
                created_user = self.context['request'].user.username
                created_date = datetime.datetime.now()
                if "TRUE" in msg:
                    instance.status = 2
                    instance.last_updated_date = datetime.datetime.now()
                    instance.save()
                    status = instance.status
                    DeliveryPlanStatus.objects.create(warehouse_info=warehouse_info,
                                                      order_no=order_no,
                                                      order_type=order_type,
                                                      status=status,
                                                      created_user=created_user,
                                                      created_date=created_date
                                                      )
                    return instance
                else:
                    instance.status = 3
                    DeliveryPlanStatus.objects.create(warehouse_info=warehouse_info,
                                                      order_no=order_no,
                                                      order_type=order_type,
                                                      status=3,
                                                      created_user=created_user,
                                                      created_date=created_date
                                                      )
                    instance.save()
                    if "不足" in msg:
                        raise serializers.ValidationError('库存不足, 出库失败')
                    elif "json错误" in msg:
                        raise serializers.ValidationError(f'出库接口调用失败,提示: {msg}')
                    else:
                        raise serializers.ValidationError(msg)
        else:
            if status == 5:
                instance.status = status
                instance.save()
                return instance
            else:
                need_qty = validated_data['need_qty']
                instance.need_qty = need_qty
                instance.save()
                return instance

    class Meta:
        model = DeliveryPlanLB
        fields = '__all__'
        # read_only_fields = COMMON_READ_ONLY_FIELDS


class OverdueMaterialManagementSerializer(serializers.ModelSerializer):
    # quality_status 检测结果
    material_no = serializers.CharField(source="material.material_no", read_only=True)  # 物料编码
    pf_obj = serializers.SerializerMethodField(read_only=True)  # 班次 机台号 生产时间
    material_obj = serializers.SerializerMethodField(read_only=True)  # 等级 保质期 超时时间

    def get_pf_obj(self, object):
        lot_no = object.lot_no
        pf_obj = PalletFeedbacks.objects.filter(lot_no=lot_no).first()
        if not pf_obj:
            return None
        else:
            classes = pf_obj.classes  # 班次
            equip_no = pf_obj.equip_no  # 机台号
            product_time = pf_obj.product_time  # 生产日期
            items = {'classes': classes, 'equip_no': equip_no, 'product_time': product_time}
            return items

    def get_material_obj(self, object):
        material_no = object.material_no
        mate_atr_obj = MaterialAttribute.objects.filter(material_no=material_no).first()
        if not mate_atr_obj:
            return None
        else:
            period_of_validity = mate_atr_obj.period_of_validity  # 保质期
            safety_inventory = mate_atr_obj.safety_inventory  # 等级
            items = {'period_of_validity': period_of_validity, 'safety_inventory': safety_inventory}
            return items

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


class BzFinalMixingRubberLBInventorySerializer(serializers.ModelSerializer):

    """终炼胶|帘布库共用序列化器"""
    class Meta:
        model = BzFinalMixingRubberInventory
        fields = "__all__"


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


class InventoryLogSerializer(serializers.ModelSerializer):
    initiator = serializers.ReadOnlyField(source='initiator.username')

    class Meta:
        model = InventoryLog
        fields = ['order_type',
                  'order_no',
                  # 'warehouse_type',
                  'pallet_no',
                  'material_no',
                  'inout_reason',
                  'inout_num_type',
                  'qty',
                  'unit',
                  'weight',
                  'initiator',
                  'start_time',
                  'fin_time'
                  ]


class WarehouseInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = WarehouseInfo
        fields = ['id', 'name', 'no', 'use_flag']
        read_only_fields = ['use_flag']


class StationSerializer(serializers.ModelSerializer):
    warehouse_no = serializers.ReadOnlyField(source='warehouse_info.no', default='')
    type_name = serializers.ReadOnlyField(source='type.global_name', default='')
    type = serializers.PrimaryKeyRelatedField(queryset=GlobalCode.objects.filter(use_flag=True,
                                                                                global_type__type_name='站点类型'))
    warehouse_info = serializers.PrimaryKeyRelatedField(queryset=WarehouseInfo.objects.all(), write_only=True)

    class Meta:
        model = Station
        fields = ['id', 'warehouse_info', 'warehouse_no', 'name', 'no', 'type_name', 'use_flag', 'type']
        read_only_fields = ['use_flag']


class WarehouseMaterialTypeSerializer(serializers.ModelSerializer):
    warehouse_no = serializers.ReadOnlyField(source='warehouse_info.no', default='')
    material_type_name = serializers.ReadOnlyField(source='material_type.global_name', default='')
    material_type = serializers.PrimaryKeyRelatedField(queryset=GlobalCode.objects.filter(use_flag=True,
                                                                                          global_type__type_name='物料类型'))
    warehouse_info = serializers.PrimaryKeyRelatedField(queryset=WarehouseInfo.objects.all(), write_only=True)

    class Meta:
        model = WarehouseMaterialType
        fields = ['id', 'warehouse_info', 'warehouse_no', 'material_type_name', 'use_flag', 'material_type']
        read_only_fields = ['use_flag']