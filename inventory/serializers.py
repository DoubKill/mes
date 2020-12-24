# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/10/14
name: 
"""
import datetime
import json
import random
import time

from django.db.models import Sum
from django.db.transaction import atomic
from rest_framework import serializers

from basics.models import GlobalCode
from mes.base_serializer import BaseModelSerializer
from recipe.models import MaterialAttribute
from .models import MaterialInventory, BzFinalMixingRubberInventory, WmsInventoryStock, WmsInventoryMaterial, \
    WarehouseInfo, Station, WarehouseMaterialType, DeliveryPlanLB, DispatchPlan, DispatchLog, DispatchLocation, \
    DeliveryPlanFinal, MixGumOutInventoryLog

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
        validated_data["order_no"] = order_no
        warehouse_info = validated_data['warehouse_info']
        status = validated_data['status']
        created_user = self.context['request'].user
        validated_data["created_user"] = created_user
        order_type = validated_data.get('order_type', '出库')  # 订单类型
        validated_data["inventory_reason"] = validated_data.pop('quality_status')  # 出入库原因
        #
        # deliveryplan = DeliveryPlan.objects.create(order_no=order_no,
        #                                            inventory_type=inventory_type,
        #                                            material_no=material_no,
        #                                            need_qty=need_qty,
        #                                            warehouse_info=warehouse_info,
        #                                            status=status,
        #                                            order_type=order_type,
        #                                            pallet_no=pallet_no,
        #                                            unit=unit,
        #                                            need_weight=need_weight,
        #                                            created_user=created_user,
        #                                            location=location,
        #                                            inventory_reason=inventory_reason  # 出库原因
        #                                            )
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
        return super().create(validated_data)

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
            user = self.context['request'].user
            str_user = user.username
            material_no = validated_data['material_no']
            pallet_no = validated_data.get('pallet_no', "20120001")  # 托盘号
            pallet = PalletFeedbacks.objects.filter(pallet_no=pallet_no).last()
            pici = pallet.bath_no if pallet else "1"  # 批次号
            num = validated_data.get('need_qty', '1')
            msg_count = "1"
            location = instance.location if instance.location else ""
            # 发起时间
            time = validated_data.get('created_date', datetime.datetime.now())
            created_time = time.strftime('%Y%m%d %H:%M:%S')
            WORKID = msg_id
            if out_type == "指定出库":
                dict1 = {'WORKID': WORKID, 'MID': material_no, 'PICI': pici, 'RFID': pallet_no,
                         'STATIONID': location, 'SENDDATE': created_time}
                bz_out_type = "快检出库"
            elif out_type == "正常出库":
                dict1 = {'WORKID': WORKID, 'MID': material_no, 'PICI': pici, 'NUM': num, 'DJJG': djjg,
                         'STATIONID': location, 'SENDDATE': created_time}
                bz_out_type = "生产出库"
            else:
                dict1 = {}
                bz_out_type = "生产出库"
            # 北自接口类型区分
            # 出库类型  一等品 = 生产出库   三等品 = 快检异常出库
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
                created_user = self.context['request'].user
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

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["created_user"] = instance.created_user.username
        return ret

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
        validated_data["order_no"] = order_no
        warehouse_info = validated_data['warehouse_info']
        status = validated_data['status']
        created_user = self.context['request'].user
        validated_data["created_user"] = created_user
        order_type = validated_data.get('order_type', '出库')  # 订单类型
        validated_data["inventory_reason"] = validated_data.pop('quality_status')  # 出入库原因

        # deliveryplan = DeliveryPlanLB.objects.create(order_no=order_no,
        #                                            inventory_type=inventory_type,
        #                                            material_no=material_no,
        #                                            need_qty=need_qty,
        #                                            warehouse_info=warehouse_info,
        #                                            status=status,
        #                                            order_type=order_type,
        #                                            pallet_no=pallet_no,
        #                                            unit=unit,
        #                                            need_weight=need_weight,
        #                                            created_user=created_user,
        #                                            location=location,
        #                                            inventory_reason=inventory_reason  # 出库原因
        #                                            )
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
        return super().create(validated_data)

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
            pallet = PalletFeedbacks.objects.filter(pallet_no=pallet_no).last()
            pici = pallet.bath_no if pallet else "1"  # 批次号
            num = validated_data.get('need_qty', '1')
            msg_count = "1"
            location = instance.location if instance.location else ""
            # 发起时间
            time = validated_data.get('created_date', datetime.datetime.now())
            created_time = time.strftime('%Y%m%d %H:%M:%S')
            WORKID = msg_id
            if out_type == "指定出库":
                dict1 = {'WORKID': WORKID, 'MID': material_no, 'PICI': pici, 'RFID': pallet_no,
                         'STATIONID': location, 'SENDDATE': created_time}
                bz_out_type = "快检出库"
            elif out_type == "正常出库":
                dict1 = {'WORKID': WORKID, 'MID': material_no, 'PICI': pici, 'NUM': num, 'DJJG': djjg,
                         'STATIONID': location, 'SENDDATE': created_time}

                bz_out_type = "生产出库"
            else:
                dict1 = {}
                bz_out_type = "生产出库"
            # 北自接口类型区分
            # 出库类型  一等品 = 生产出库   三等品 = 快检异常出库
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
                created_user = self.context['request'].user
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

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["created_user"] = instance.created_user.username
        return ret

    class Meta:
        model = DeliveryPlanLB
        fields = '__all__'
        # read_only_fields = COMMON_READ_ONLY_FIELDS


class PutPlanManagementSerializerFinal(serializers.ModelSerializer):
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
        validated_data["order_no"] = order_no
        warehouse_info = validated_data['warehouse_info']
        status = validated_data['status']
        created_user = self.context['request'].user
        validated_data["created_user"] = created_user
        order_type = validated_data.get('order_type', '出库')  # 订单类型
        validated_data["inventory_reason"] = validated_data.pop('quality_status')  # 出入库原因

        # deliveryplan = DeliveryPlanLB.objects.create(order_no=order_no,
        #                                            inventory_type=inventory_type,
        #                                            material_no=material_no,
        #                                            need_qty=need_qty,
        #                                            warehouse_info=warehouse_info,
        #                                            status=status,
        #                                            order_type=order_type,
        #                                            pallet_no=pallet_no,
        #                                            unit=unit,
        #                                            need_weight=need_weight,
        #                                            created_user=created_user,
        #                                            location=location,
        #                                            inventory_reason=inventory_reason  # 出库原因
        #                                            )
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
        return super().create(validated_data)

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
            pallet = PalletFeedbacks.objects.filter(pallet_no=pallet_no).last()
            pici = pallet.bath_no if pallet else "1"  # 批次号
            num = validated_data.get('need_qty', '1')
            msg_count = "1"
            location = instance.location if instance.location else ""
            # 发起时间
            time = validated_data.get('created_date', datetime.datetime.now())
            created_time = time.strftime('%Y%m%d %H:%M:%S')
            WORKID = msg_id
            if out_type == "指定出库":
                dict1 = {'WORKID': WORKID, 'MID': material_no, 'PICI': pici, 'RFID': pallet_no,
                         'STATIONID': location, 'SENDDATE': created_time}
                bz_out_type = "快检出库"
            elif out_type == "正常出库":
                dict1 = {'WORKID': WORKID, 'MID': material_no, 'PICI': pici, 'NUM': num, 'DJJG': djjg,
                         'STATIONID': location, 'SENDDATE': created_time}

                bz_out_type = "生产出库"
            else:
                dict1 = {}
                bz_out_type = "生产出库"
            # 北自接口类型区分
            # 出库类型  一等品 = 生产出库   三等品 = 快检异常出库
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
                created_user = self.context['request'].user
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

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["created_user"] = instance.created_user.username
        return ret

    class Meta:
        model = DeliveryPlanFinal
        fields = '__all__'


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
    product_info = serializers.SerializerMethodField(read_only=True)

    def get_product_info(self, obj):
        lot_no = obj.lot_no
        pf = PalletFeedbacks.objects.filter(lot_no=lot_no).last()
        product_time = ""
        if pf:
            try:
                product_time = pf.product_time.strftime('%Y-%m-%d %H:%M:%S')
            except:
                product_time = ""
        return {
            "equip_no": pf.equip_no if pf else "",
            "classes": pf.classes if pf else "",
            "product_time": product_time
        }

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
                  'quality_status',
                  'product_info']


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
                                                                                          global_type__type_name='原材料类别'))
    warehouse_info = serializers.PrimaryKeyRelatedField(queryset=WarehouseInfo.objects.all(), write_only=True)

    class Meta:
        model = WarehouseMaterialType
        fields = ['id', 'warehouse_info', 'warehouse_no', 'material_type_name', 'use_flag', 'material_type']
        read_only_fields = ['use_flag']


class DispatchPlanSerializer(BaseModelSerializer):
    """发货计划管理"""
    '''发货日期前端页面删除'''
    dispatch_type_name = serializers.ReadOnlyField(source='dispatch_type.global_name', help_text='发货类型', )
    dispatch_location_name = serializers.ReadOnlyField(source='dispatch_location.name', help_text='目的地', )
    material_name = serializers.ReadOnlyField(source='material.material_no', help_text='物料编码', )
    status_name = serializers.ReadOnlyField(source='get_status_display', help_text="状态")

    class Meta:
        model = DispatchPlan
        fields = (
            'id', 'dispatch_location', 'order_no', 'dispatch_type', 'material', 'need_qty', 'actual_qty',
            'need_weight', 'actual_weight', 'status', 'dispatch_user', 'start_time', 'fin_time', 'dispatch_type_name',
            'dispatch_location_name', 'material_name', 'status_name', 'created_date')


class DispatchLocationSerializer(BaseModelSerializer):
    """目的地"""
    create_user_name = serializers.ReadOnlyField(source='created_user.username')
    update_user_name = serializers.ReadOnlyField(source='last_updated_user.username')

    class Meta:
        model = DispatchLocation
        fields = '__all__'


class DispatchLogSerializer(BaseModelSerializer):
    """发货履历"""

    class Meta:
        model = DispatchLog
        fields = '__all__'


class DispatchLogCreateSerializer(BaseModelSerializer):
    """发货履历"""

    def validate(self, attrs):
        order_no = attrs['order_no']
        lot_no = attrs['lot_no']
        status = attrs['status']
        dispatch_plan = DispatchPlan.objects.filter(order_no=order_no).first()
        if not dispatch_plan:
            raise serializers.ValidationError('error order_no')
        pallet = PalletFeedbacks.objects.filter(lot_no=lot_no).first()
        if not pallet:
            raise serializers.ValidationError('error lot_no')
        if not dispatch_plan.material.material_no == pallet.product_no:
            raise serializers.ValidationError('该托盘胶料与发货单计划胶料不一致')
        if status == 1:  # 发货防止扫描重复
            last_dispatch_log = DispatchLog.objects.filter(order_no=order_no, lot_no=lot_no).last()
            if last_dispatch_log:
                if last_dispatch_log.status == 1:
                    raise serializers.ValidationError('请勿重复扫描')
        attrs['pallet_no'] = pallet.pallet_no
        attrs['need_weight'] = dispatch_plan.need_weight
        attrs['need_qty'] = dispatch_plan.need_qty
        attrs['dispatch_type'] = dispatch_plan.dispatch_type
        attrs['material_no'] = dispatch_plan.material.material_no
        attrs['quality_status'] = '合格'
        attrs['order_type'] = dispatch_plan.order_type
        attrs['qty'] = pallet.end_trains - pallet.begin_trains + 1
        attrs['weight'] = pallet.actual_weight
        attrs['dispatch_location'] = dispatch_plan.dispatch_location.name
        attrs['pallet_no'] = pallet.pallet_no
        attrs['dispatch_plan'] = dispatch_plan
        attrs['dispatch_user'] = self.context['request'].user.username
        return attrs

    @atomic()
    def create(self, validated_data):
        dispatch_plan = validated_data.pop('dispatch_plan')
        status = validated_data['status']
        if status == 1:  # 完成
            dispatch_plan.actual_qty += validated_data['qty']
            dispatch_plan.actual_weight += validated_data['weight']
        else:  # 撤销
            dispatch_plan.actual_qty -= validated_data['qty']
            dispatch_plan.actual_weight -= validated_data['weight']
        dispatch_plan.save()
        return super().create(validated_data)

    class Meta:
        model = DispatchLog
        fields = ('order_no', 'lot_no', 'status')


class DispatchPlanUpdateSerializer(BaseModelSerializer):

    def update(self, instance, validated_data):
        instance.status = 1
        instance.fin_time = datetime.datetime.now()
        instance.save()
        DispatchLog.objects.filter(order_no=instance.order_no).update(fin_time=datetime.datetime.now())
        return instance

    class Meta:
        model = DispatchPlan
        fields = ('id',)


class TerminalDispatchPlanUpdateSerializer(BaseModelSerializer):

    def update(self, instance, validated_data):
        status = validated_data['status']
        instance.status = status
        if status == 1:
            instance.fin_time = datetime.datetime.now()
            DispatchLog.objects.filter(order_no=instance.order_no).update(fin_time=datetime.datetime.now())
        instance.save()
        return instance

    class Meta:
        model = DispatchPlan
        fields = ('id', 'status')


class InventoryLogOutSerializer(BaseModelSerializer):
    class Meta:
        model = InventoryLog
        fields = '__all__'
