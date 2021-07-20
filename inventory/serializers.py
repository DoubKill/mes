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
from mes.base_serializer import BaseModelSerializer
from mes.conf import STATION_LOCATION_MAP
from recipe.models import MaterialAttribute
from .conf import wms_ip, wms_port, cb_ip, cb_port
from .models import MaterialInventory, BzFinalMixingRubberInventory, WmsInventoryStock, WmsInventoryMaterial, \
    WarehouseInfo, Station, WarehouseMaterialType, DeliveryPlanLB, DispatchPlan, DispatchLog, DispatchLocation, \
    DeliveryPlanFinal, MixGumOutInventoryLog, MixGumInInventoryLog, MaterialOutPlan, BzFinalMixingRubberInventoryLB, \
    BarcodeQuality, CarbonOutPlan, MixinRubberyOutBoundOrder, FinalRubberyOutBoundOrder

from inventory.models import DeliveryPlan, DeliveryPlanStatus, InventoryLog, MaterialInventory
from inventory.utils import OUTWORKUploader, OUTWORKUploaderLB, wms_out
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
    destination = serializers.SerializerMethodField(read_only=True)

    def get_actual(self, object):
        order_no = object.order_no
        actual = InventoryLog.objects.filter(order_no=order_no).aggregate(actual_qty=Sum('qty'),
                                                                          actual_weight=Sum('weight'))
        actual_qty = actual['actual_qty']
        actual_weight = actual['actual_weight']
        items = {'actual_qty': actual_qty, 'actual_wegit': actual_weight}
        return items

    def get_destination(self, object):
        equip_list = list(object.equip.all().values_list("equip_no", flat=True))
        dispatch_list = list(object.dispatch.all().values_list("dispatch_location__name", flat=True))
        destination = ",".join(set(equip_list + dispatch_list))
        return destination

    def create(self, validated_data):
        location = validated_data.get("location")
        if DeliveryPlan.objects.filter(location=location, status=4).exists():
            raise serializers.ValidationError('该库存位{}出库计划已存在，请勿重复添加！'.format(location))
        station = validated_data.get("station")
        # try:
        #     inventory = BzFRuinalMixingbberInventory.objects.using('bz').get(location=location)
        # except:
        #     raise serializers.ValidationError("未查到此货位信息，请刷新后重试")
        # if inventory.location_status not in ["有货货位"]:
        #     raise serializers.ValidationError(f"{location} 货位异常，请使用wms进行处理")
        if not station:
            raise serializers.ValidationError(f"请选择出库口")
        if location:
            if not location[0] in STATION_LOCATION_MAP[station]:
                raise serializers.ValidationError(f"货架:{location} 无法从{station}口出库，请检查")

            temp_location = BzFinalMixingRubberInventory.objects.using('bz').filter(location=location).last()
            if not temp_location:
                raise serializers.ValidationError(f"无{location}货架")
            else:
                if temp_location.location_status != "有货货位":
                    raise serializers.ValidationError(f"{location}货架为异常货架，请操作wms")
        # else:
        #     material_no = validated_data.get("material_no")
        #     location_set = BzFinalMixingRubberInventory.objects.using('bz').filter(material_no=material_no).values_list("location", flat=True)
        #     for location in location_set:
        #         if not location[0] in STATION_LOCATION_MAP[station]:
        #             raise serializers.ValidationError(f"货架:{location} 无法从{station}口出库，请检查")
        order_no = ''.join(str(time.time()).split('.'))
        validated_data["order_no"] = order_no
        warehouse_info = validated_data['warehouse_info']
        status = validated_data['status']
        created_user = self.context['request'].user
        validated_data["created_user"] = created_user
        validated_data['order_type'] = "出库"
        order_type = '出库'  # 订单类型
        validated_data["inventory_reason"] = validated_data.pop('quality_status')  # 出入库原因
        #

        DeliveryPlanStatus.objects.create(warehouse_info=warehouse_info,
                                          order_no=order_no,
                                          order_type=order_type,
                                          status=status,
                                          created_user=created_user,
                                          )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        out_type = validated_data.get('inventory_type')
        status = validated_data.get('status')
        inventory_reason = instance.inventory_reason
        if inventory_reason in ['一等品', '合格品']:
            djjg = "一等品"
        elif inventory_reason in ['三等品', '不合格品']:
            djjg = "三等品"
        else:
            djjg = "一等品"
        if out_type == "正常出库" or out_type == "指定出库":
            msg_id = validated_data['order_no']
            user = self.context['request'].user
            str_user = user.username
            material_no = validated_data['material_no']
            pallet_no = validated_data.get('pallet_no', "20120001")  # 托盘号
            pallet = PalletFeedbacks.objects.filter(pallet_no=pallet_no).last()
            pici = pallet.bath_no if pallet else "1"  # 批次号
            num = instance.need_qty
            msg_count = "1"
            station = instance.station if instance.station else ""
            # 发起时间
            time = validated_data.get('created_date', datetime.datetime.now())
            created_time = time.strftime('%Y%m%d %H:%M:%S')
            WORKID = msg_id
            if out_type == "指定出库":
                dict1 = {'WORKID': WORKID, 'MID': material_no, 'PICI': pici, 'RFID': pallet_no,
                         'STATIONID': station, 'SENDDATE': created_time}
                bz_out_type = "快检出库"
            elif out_type == "正常出库":
                dict1 = {'WORKID': WORKID, 'MID': material_no, 'PICI': pici, 'NUM': num, 'DJJG': djjg,
                         'STATIONID': station, 'SENDDATE': created_time}
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
            print(json_data)
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
    destination = serializers.SerializerMethodField(read_only=True)

    def get_actual(self, object):
        order_no = object.order_no
        actual = InventoryLog.objects.filter(order_no=order_no).aggregate(actual_qty=Sum('qty'),
                                                                          actual_weight=Sum('weight'))
        actual_qty = actual['actual_qty']
        actual_weight = actual['actual_weight']
        items = {'actual_qty': actual_qty, 'actual_wegit': actual_weight}
        return items

    def get_destination(self, object):
        equip_list = list(object.equip.all().values_list("equip_no", flat=True))
        dispatch_list = list(object.dispatch.all().values_list("dispatch_location__name", flat=True))
        destination = ",".join(set(equip_list + dispatch_list))
        return destination

    @atomic()
    def create(self, validated_data):
        location = validated_data.get("location")
        station = validated_data.get("station")
        if not station:
            raise serializers.ValidationError(f"请选择出库口")
        if location:
            # if not location[0] in STATION_LOCATION_MAP[station]:
            #     raise serializers.ValidationError(f"货架:{location} 无法从{station}口出库，请检查")

            temp_location = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(location=location).last()
            if not temp_location:
                raise serializers.ValidationError(f"无{location}货架")
            else:
                if temp_location.location_status != "有货货位":
                    raise serializers.ValidationError(f"{location}货架为异常货架，请操作wms")
        order_no = time.strftime("%Y%m%d%H%M%S", time.localtime())
        validated_data["order_no"] = order_no
        warehouse_info = validated_data['warehouse_info']
        status = validated_data['status']
        created_user = self.context['request'].user
        validated_data["created_user"] = created_user
        order_type = validated_data.get('order_type', '出库')  # 订单类型
        validated_data["inventory_reason"] = validated_data.pop('quality_status')  # 出入库原因
        if not validated_data.get("material_name"):
            validated_data["material_name"] = validated_data.get("material_no")
        DeliveryPlanStatus.objects.create(warehouse_info=warehouse_info,
                                          order_no=order_no,
                                          order_type=order_type,
                                          status=status,
                                          created_user=created_user,
                                          )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        out_type = validated_data.get('inventory_type')
        status = validated_data.get('status')
        inventory_reason = instance.inventory_reason
        if inventory_reason in ['一等品', '合格品']:
            djjg = "一等品"
        elif inventory_reason in ['三等品', '不合格品']:
            djjg = "三等品"
        else:
            djjg = "一等品"
        if out_type not in ["正常出库", "指定出库"]:
            if status == 5:
                instance.status = status
                instance.save()
                return instance
            else:
                need_qty = validated_data['need_qty']
                instance.need_qty = need_qty
                instance.save()
                return instance
        if out_type == "正常出库" or out_type == "指定出库":
            msg_id = validated_data['order_no']
            str_user = self.context['request'].user.username
            material_no = validated_data['material_no']
            pallet_no = validated_data.get('pallet_no', "20120001")  # 托盘号
            pallet = PalletFeedbacks.objects.filter(pallet_no=pallet_no).last()
            pici = pallet.bath_no if pallet else "1"  # 批次号
            num = instance.need_qty
            msg_count = "1"
            station = instance.station if instance.station else ""
            # 发起时间
            time = validated_data.get('created_date', datetime.datetime.now())
            created_time = time.strftime('%Y%m%d %H:%M:%S')
            WORKID = msg_id
            if out_type == "指定出库":
                dict1 = {'WORKID': WORKID, 'MID': material_no, 'PICI': pici, 'RFID': pallet_no,
                         'STATIONID': station, 'SENDDATE': created_time, 'STOREDEF_ID': 4}
                bz_out_type = "快检出库"
            elif out_type == "正常出库":
                dict1 = {'WORKID': WORKID, 'MID': material_no, 'PICI': pici, 'NUM': num, 'DJJG': djjg,
                         'STATIONID': station, 'SENDDATE': created_time, 'STOREDEF_ID': 4}

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
            print(json_data)
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
    destination = serializers.SerializerMethodField(read_only=True)

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

    def get_destination(self, object):
        equip_list = list(object.equip.all().values_list("equip_no", flat=True))
        dispatch_list = list(object.dispatch.all().values_list("dispatch_location__name", flat=True))
        destination = ",".join(set(equip_list + dispatch_list))
        return destination

    def create(self, validated_data):
        location = validated_data.get("location")
        station = validated_data.get("station")
        if DeliveryPlanFinal.objects.filter(location=location, status=4).exists():
            raise serializers.ValidationError('该库存位{}出库计划已存在，请勿重复添加！'.format(location))
        if not station:
            raise serializers.ValidationError(f"请选择出库口")
        if location:
            # if not location[0] in STATION_LOCATION_MAP[station]:
            #     raise serializers.ValidationError(f"货架:{location} 无法从{station}口出库，请检查")

            temp_location = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(location=location).last()
            if not temp_location:
                raise serializers.ValidationError(f"无{location}货架")
            else:
                if temp_location.location_status != "有货货位":
                    raise serializers.ValidationError(f"{location}货架为异常货架，请操作wms")
        order_no = ''.join(str(time.time()).split('.'))
        validated_data["order_no"] = order_no
        warehouse_info = validated_data['warehouse_info']
        status = validated_data['status']
        created_user = self.context['request'].user
        validated_data["created_user"] = created_user
        order_type = validated_data.get('order_type', '出库')  # 订单类型
        validated_data["inventory_reason"] = validated_data.pop('quality_status')  # 出入库原因
        DeliveryPlanStatus.objects.create(warehouse_info=warehouse_info,
                                          order_no=order_no,
                                          order_type=order_type,
                                          status=status,
                                          created_user=created_user,
                                          )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        out_type = validated_data.get('inventory_type')
        status = validated_data.get('status')
        inventory_reason = instance.inventory_reason
        if inventory_reason in ['一等品', '合格品']:
            djjg = "一等品"
        elif inventory_reason in ['三等品', '不合格品']:
            djjg = "三等品"
        else:
            djjg = "一等品"
        if out_type not in ["正常出库", "指定出库"]:
            if status == 5:
                instance.status = status
                instance.save()
                return instance
            else:
                need_qty = validated_data['need_qty']
                instance.need_qty = need_qty
                instance.save()
                return instance
        if out_type == "正常出库" or out_type == "指定出库":
            msg_id = validated_data['order_no']
            str_user = self.context['request'].user.username
            material_no = validated_data['material_no']
            pallet_no = validated_data.get('pallet_no', "20120001")  # 托盘号
            pallet = PalletFeedbacks.objects.filter(pallet_no=pallet_no).last()
            pici = pallet.bath_no if pallet else "1"  # 批次号
            num = instance.need_qty
            msg_count = "1"
            station = instance.station if instance.station else ""
            # 发起时间
            time = validated_data.get('created_date', datetime.datetime.now())
            created_time = time.strftime('%Y%m%d %H:%M:%S')
            WORKID = msg_id
            if out_type == "指定出库":
                dict1 = {'WORKID': WORKID, 'MID': material_no, 'PICI': pici, 'RFID': pallet_no,
                         'STATIONID': station, 'SENDDATE': created_time, 'STOREDEF_ID': 1}
                bz_out_type = "快检出库"
            elif out_type == "正常出库":
                dict1 = {'WORKID': WORKID, 'MID': material_no, 'PICI': pici, 'NUM': num, 'DJJG': djjg,
                         'STATIONID': station, 'SENDDATE': created_time, 'STOREDEF_ID': 1}
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
            print(json_data)
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
        fields = '__all__'


class BzFinalMixingRubberInventorySerializer(serializers.ModelSerializer):
    product_info = serializers.SerializerMethodField(read_only=True)
    equip_no = serializers.SerializerMethodField(read_only=True)
    unit = serializers.SerializerMethodField(read_only=True)
    unit_weight = serializers.SerializerMethodField(read_only=True)
    material_type = serializers.SerializerMethodField(read_only=True)
    quality_status = serializers.CharField(read_only=True, source='quality_level')

    def get_material_type(self, object):
        try:
            mt = object.material_no.split("-")[1]
        except:
            mt = object.material_no
        return mt

    def get_unit(self, object):
        return 'kg'

    def get_unit_weight(self, object):
        try:
            unit_weight = round(object.total_weight / object.qty,3)
        except:
            unit_weight = "数据异常"
        return unit_weight


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

    def get_equip_no(self, obj):
        try:
            equip_no = obj.bill_id[-3:]
        except:
            equip_no = ""
        return equip_no

    class Meta:
        model = BzFinalMixingRubberInventory
        fields = "__all__"


class BzFinalMixingRubberLBInventorySerializer(serializers.ModelSerializer):
    """终炼胶|帘布库共用序列化器"""
    material_type = serializers.SerializerMethodField(read_only=True)
    unit = serializers.SerializerMethodField(read_only=True)
    unit_weight = serializers.SerializerMethodField(read_only=True)
    product_info = serializers.SerializerMethodField(read_only=True)
    equip_no = serializers.SerializerMethodField(read_only=True)
    quality_status = serializers.SerializerMethodField(read_only=True)

    def get_material_type(self, object):
        try:
            mt = object.material_no.split("-")[1]
        except:
            mt = object.material_no
        return mt

    def get_unit(self, object):
        return 'kg'

    def get_unit_weight(self, object):
        try:
            unit_weight = round(object.total_weight / object.qty,3)
        except:
            unit_weight = "数据异常"
        return unit_weight


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

    def get_equip_no(self, obj):
        try:
            equip_no = obj.bill_id[-3:]
        except:
            equip_no = ""
        return equip_no

    def get_quality_status(self, obj):
        temp = obj.quality_level
        if "M" in obj.material_no:
            return temp
        else:
            return {"一等品": "合格品",
                    "三等品": "不合格品"}.get(temp, temp)


    class Meta:
        model = BzFinalMixingRubberInventoryLB
        fields = "__all__"


class WmsInventoryStockSerializer(serializers.ModelSerializer):
    unit_weight = serializers.SerializerMethodField(read_only=True)
    quality_status = serializers.SerializerMethodField(read_only=True)


    def get_unit_weight(self, object):
        try:
            unit_weight = object.total_weight / object.qty
        except:
            unit_weight = "数据异常"
        return unit_weight

    def get_quality_status(self, object):
        status_map = {1: "合格品", 2: "不合格品"}
        return status_map.get(object.quality_status, "不合格品")

    class Meta:
        model = WmsInventoryStock
        fields = "__all__"


class InventoryLogSerializer(serializers.ModelSerializer):
    product_info = serializers.SerializerMethodField(read_only=True)
    inout_num_type = serializers.SerializerMethodField(read_only=True)
    fin_time = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = InventoryLog
        fields = "__all__"

    def get_inout_num_type(self, obj):
        if obj.inout_num_type == "快检出库":
            return "指定出库"
        elif obj.inout_num_type == "生产出库":
            return "正常出库"
        else:
            return obj.inout_num_type

    def get_product_info(self, obj):
        if obj.lot_no:
            pf = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).last()
            if pf:
                return {
                    "equip_no": pf.equip_no,
                    "classes": f"{pf.factory_date}/{pf.classes}",
                    "memo": f"{pf.begin_trains},{pf.end_trains}"
                }
            else:
                return {
                    "equip_no": "",
                    "classes": "",
                    "memo": "",
                }
        else:
            return {
                "equip_no": "",
                "classes": "",
                "memo": "",
            }

    def get_fin_time(self, obj):
        return (obj.start_time + datetime.timedelta(minutes=3)).strftime('%Y-%m-%d %H:%M:%S')


class MixGumOutInventoryLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = MixGumOutInventoryLog
        fields = "__all__"


class MixGumInInventoryLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = MixGumInInventoryLog
        fields = "__all__"


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


# 原材料出库管理序列化器

class MaterialPlanManagementSerializer(serializers.ModelSerializer):
    no = serializers.CharField(source="warehouse_info.no", read_only=True)
    name = serializers.CharField(source="warehouse_info.name", read_only=True)
    actual = serializers.SerializerMethodField(read_only=True)
    destination = serializers.SerializerMethodField(read_only=True)
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

    def get_destination(self, object):
        equip_list = list(object.equip.all().values_list("equip_no", flat=True))
        dispatch_list = list(object.dispatch.all().values_list("dispatch_location__name", flat=True))
        destination = ",".join(set(equip_list + dispatch_list))
        return destination

    @atomic()
    def create(self, validated_data):
        location = validated_data.get("location")
        station = validated_data.get("station")
        if not station:
            raise serializers.ValidationError(f"请选择出库口")
        order_no = time.strftime("%Y%m%d%H%M%S", time.localtime())
        validated_data["order_no"] = order_no
        warehouse_info = validated_data['warehouse_info']
        status = validated_data['status']
        created_user = self.context['request'].user
        validated_data["created_user"] = created_user
        order_type = validated_data.get('order_type', '出库')  # 订单类型
        validated_data["inventory_reason"] = validated_data.pop('quality_status')  # 出入库原因
        DeliveryPlanStatus.objects.create(warehouse_info=warehouse_info,
                                          order_no=order_no,
                                          order_type=order_type,
                                          status=status,
                                          created_user=created_user,
                                          )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        out_type = validated_data.get('inventory_type')
        status = validated_data.get('status')
        # 该代码用于处理页面上上编辑订单状态与需求量
        if out_type not in ["指定出库", "正常出库"]:
            if status == 5:
                instance.status = status
                instance.save()
                return instance
            else:
                need_weight = validated_data['need_weight']
                instance.need_weight = need_weight
                instance.save()
                return instance
        inventory_reason = validated_data.get('inventory_reason')
        body_dict = {
            "指定出库": {
                "taskNumber": instance.order_no,
                "entranceCode": instance.station_no,
                "allocationInventoryDetails": [{
                    "taskDetailNumber": instance.order_no + "w1",
                    "materialCode": instance.material_no,
                    "materialName": instance.material_name if instance.material_name else "",
                    # "batchNo": instance.batch_no,
                    "spaceCode": instance.location,
                    "quantity": instance.need_qty
                        }]
                },
            "正常出库": {
                "taskNumber": instance.order_no,
                "entranceCode": instance.station_no,
                "allocationInventoryDetails": [{
                    "materialCode": instance.material_no,
                    "materialName": instance.material_name if instance.material_name else "",
                    "weightOfActual ": instance.need_weight
                }]
            }
        }
        url_dict = {
            "指定出库": f"http://{wms_ip}:{wms_port}/MESApi/AllocateSpaceDelivery",
            "正常出库": f"http://{wms_ip}:{wms_port}/MESApi/AllocateWeightDelivery"
        }
        body = body_dict[out_type]
        url = url_dict[out_type]
        try:
            rep_dict =  wms_out(url, body)
        except Exception as e:
            raise serializers.ValidationError(f"原材料wms调用失败，请联系wms维护人员: {e}")
        warehouse_info = validated_data['warehouse_info']
        order_no = validated_data['order_no']
        order_type = validated_data['inventory_type']
        created_user = self.context['request'].user
        created_date = datetime.datetime.now()
        # 用于出库计划状态变更
        if rep_dict.get("state") == 1:
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
            raise serializers.ValidationError(f"原材料{out_type}失败，详情: {rep_dict.get('msg')}")


    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["created_user"] = instance.created_user.username
        return ret

    class Meta:
        model = MaterialOutPlan
        fields = '__all__'
        extra_kwargs = {
            'order_no': {
                'required': False
            },
            'station': {
                'required': False
            },
            'station_no': {
                'required': False
            },
        }


class CarbonPlanManagementSerializer(serializers.ModelSerializer):
    no = serializers.CharField(source="warehouse_info.no", read_only=True)
    name = serializers.CharField(source="warehouse_info.name", read_only=True)
    actual = serializers.SerializerMethodField(read_only=True)
    destination = serializers.SerializerMethodField(read_only=True)
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

    def get_destination(self, object):
        equip_list = list(object.equip.all().values_list("equip_no", flat=True))
        dispatch_list = list(object.dispatch.all().values_list("dispatch_location__name", flat=True))
        destination = ",".join(set(equip_list + dispatch_list))
        return destination

    @atomic()
    def create(self, validated_data):
        location = validated_data.get("location")
        station = validated_data.get("station")
        if not station:
            raise serializers.ValidationError(f"请选择出库口")
        order_no = time.strftime("%Y%m%d%H%M%S", time.localtime())
        validated_data["order_no"] = order_no
        warehouse_info = validated_data['warehouse_info']
        status = validated_data['status']
        created_user = self.context['request'].user
        validated_data["created_user"] = created_user
        order_type = validated_data.get('order_type', '出库')  # 订单类型
        validated_data["inventory_reason"] = validated_data.pop('quality_status', "合格品")  # 出入库原因
        DeliveryPlanStatus.objects.create(warehouse_info=warehouse_info,
                                          order_no=order_no,
                                          order_type=order_type,
                                          status=status,
                                          created_user=created_user,
                                          )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        out_type = validated_data.get('inventory_type')
        status = validated_data.get('status')
        # 该代码用于处理页面上上编辑订单状态与需求量
        if out_type not in ["指定出库", "正常出库"]:
            if status == 5:
                instance.status = status
                instance.save()
                return instance
            else:
                need_weight = validated_data['need_weight']
                instance.need_weight = need_weight
                instance.save()
                return instance
        inventory_reason = validated_data.get('inventory_reason')
        body_dict = {
            "指定出库": {
                "taskNumber": instance.order_no,
                "entranceCode": instance.station_no,
                "allocationInventoryDetails": [{
                    "taskDetailNumber": instance.order_no + "cb1",
                    "materialCode": instance.material_no,
                    "materialName": instance.material_name if instance.material_name else "",
                    # "batchNo": instance.batch_no,
                    "spaceCode": instance.location,
                    "quantity": instance.need_qty
                        }]
                },
            "正常出库": {
                "taskNumber": instance.order_no,
                "entranceCode": instance.station_no,
                "allocationInventoryDetails": [{
                    "materialCode": instance.material_no,
                    "materialName": instance.material_name if instance.material_name else "",
                    "weightOfActual ": instance.need_weight
                }]
            }
        }
        url_dict = {
            "指定出库": f"http://{cb_ip}:{cb_port}/MESApi/AllocateSpaceDelivery",
            "正常出库": f"http://{cb_ip}:{cb_port}/MESApi/AllocateWeightDelivery"
        }
        body = body_dict[out_type]
        url = url_dict[out_type]
        try:
            rep_dict =  wms_out(url, body)
        except:
            raise serializers.ValidationError("原材料wms调用失败，请联系wms维护人员")
        warehouse_info = validated_data['warehouse_info']
        order_no = validated_data['order_no']
        order_type = validated_data['inventory_type']
        created_user = self.context['request'].user
        created_date = datetime.datetime.now()
        # 用于出库计划状态变更
        if rep_dict.get("state") == 1:
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
            raise serializers.ValidationError(f"原材料{out_type}失败，详情: {rep_dict.get('msg')}")


    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["created_user"] = instance.created_user.username
        return ret

    class Meta:
        model = CarbonOutPlan
        fields = '__all__'
        extra_kwargs = {
            'order_no': {
                'required': False
            },
            'station': {
                'required': False
            },
            'station_no': {
                'required': False
            },
        }


class BarcodeQualitySerializer(BaseModelSerializer):

    class Meta:
        model = BarcodeQuality
        fields = '__all__'


class WmsStockSerializer(BaseModelSerializer):
    quality= serializers.SerializerMethodField(read_only=True)
    unit_weight = serializers.SerializerMethodField(read_only=True)

    def get_quality(self, obj):
        quality_dict = self.context.get("quality_dict")
        return quality_dict.get(obj.lot_no) if quality_dict.get(obj.lot_no) else None

    def get_unit_weight(self, obj):
        try:
            unit_weight = str(round(obj.total_weight / obj.qty, 2))
        except:
            return str(0.00)
        return unit_weight


    class Meta:
        model = WmsInventoryStock
        exclude = ('sn', 'in_storage_time', 'quality_status')


class InOutCommonSerializer(serializers.Serializer):
    """库存库表均不统一,只读序列化器"""
    id = serializers.IntegerField(read_only=True)
    order_no = serializers.CharField(max_length=64, read_only=True)
    pallet_no = serializers.CharField(max_length=64, read_only=True)
    location = serializers.CharField(max_length=64, read_only=True)
    qty = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    weight = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    unit = serializers.CharField(read_only=True, max_length=50)
    lot_no = serializers.CharField(max_length=64, read_only=True)
    inout_type = serializers.IntegerField(read_only=True)
    material_no = serializers.CharField(max_length=64, read_only=True)
    material_name = serializers.CharField(max_length=64, read_only=True)
    initiator = serializers.CharField(source='task.initiator', read_only=True)
    start_time = serializers.DateTimeField(source='task.start_time', read_only=True)
    fin_time = serializers.DateTimeField(source='task.fin_time', read_only=True)
    order_type = serializers.SerializerMethodField()

    def get_order_type(self, obj):
        if obj.inout_type == 1:
            return "入库"
        else:
            return "出库"


class MixinRubberyOutBoundOrderSerializer(BaseModelSerializer):

    def update(self, instance, validated_data):
        status = validated_data.get('status')
        if status == 2:  # 调用北自出库接口
            username = self.context['request'].user.username
            items = []
            for plan in instance.mixin_plans.all():
                pallet = PalletFeedbacks.objects.filter(pallet_no=plan.pallet_no).last()
                dict1 = {'WORKID': plan.order_no,
                         'MID': plan.material_no,
                         'PICI': pallet.bath_no if pallet else "1",
                         'RFID': plan.pallet_no,
                         'STATIONID': plan.station if plan.station else "",
                         'SENDDATE': datetime.datetime.now().strftime('%Y%m%d %H:%M:%S')}
                items.append(dict1)
            json_data = {
                'msgId': instance.order_no,
                'OUTTYPE': '快检出库',
                "msgConut": '1',
                "SENDUSER": username,
                "items": items
            }
            json_data = json.dumps(json_data, ensure_ascii=False)
            sender = OUTWORKUploader(end_type="指定出库")
            result = sender.request(instance.order_no, '指定出库', '1', username, json_data)
            if result is not None:
                try:
                    items = result['items']
                    msg = items[0]['msg']
                except:
                    msg = result[0]['msg']
                if "TRUE" in msg:  # 成功
                    instance.status = 2
                    task_status = 2
                    instance.mixin_plans.filter().update(status=2)
                else:  # 失败
                    instance.status = 5
                    instance.mixin_plans.filter().update(status=3)
                    task_status = 3
                instance.save()
                for plan in instance.mixin_plans.all():
                    DeliveryPlanStatus.objects.create(warehouse_info=plan.warehouse_info,
                                                      order_no=plan.order_no,
                                                      order_type='指定出库',
                                                      status=task_status)
                if not task_status == 2:
                    if "不足" in msg:
                        raise serializers.ValidationError('库存不足, 出库失败')
                    elif "json错误" in msg:
                        raise serializers.ValidationError(f'出库接口调用失败,提示: {msg}')
                    else:
                        raise serializers.ValidationError(msg)
        elif status == 4:
            instance.status = 4
            instance.save()
            instance.mixin_plans.filter().update(status=5)
        return validated_data

    class Meta:
        model = MixinRubberyOutBoundOrder
        fields = '__all__'
        read_only_fields = ('order_no', 'warehouse_name', 'order_type')


class FinalRubberyOutBoundOrderSerializer(BaseModelSerializer):

    def update(self, instance, validated_data):
        status = validated_data.get('status')
        if status == 2:  # 调用北自出库接口
            username = self.context['request'].user.username
            items = []
            for plan in instance.final_plans.all():
                pallet = PalletFeedbacks.objects.filter(pallet_no=plan.pallet_no).last()
                dict1 = {'WORKID': plan.order_no,
                         'MID': plan.material_no,
                         'PICI': pallet.bath_no if pallet else "1",
                         'RFID': plan.pallet_no,
                         'STATIONID': plan.station if plan.station else "",
                         'SENDDATE': datetime.datetime.now().strftime('%Y%m%d %H:%M:%S'),
                         'STOREDEF_ID': 1}
                items.append(dict1)
            json_data = {
                'msgId': instance.order_no,
                'OUTTYPE': '快检出库',
                "msgConut": '1',
                "SENDUSER": username,
                "items": items
            }
            json_data = json.dumps(json_data, ensure_ascii=False)
            sender = OUTWORKUploaderLB(end_type="指定出库")
            result = sender.request(instance.order_no, '指定出库', '1', username, json_data)
            if result is not None:
                try:
                    items = result['items']
                    msg = items[0]['msg']
                except:
                    msg = result[0]['msg']
                if "TRUE" in msg:  # 成功
                    instance.status = 2
                    task_status = 2
                    instance.final_plans.filter().update(status=2)
                else:  # 失败
                    instance.status = 5
                    instance.final_plans.filter().update(status=3)
                    task_status = 3
                instance.save()
                for plan in instance.final_plans.all():
                    DeliveryPlanStatus.objects.create(warehouse_info=plan.warehouse_info,
                                                      order_no=plan.order_no,
                                                      order_type='指定出库',
                                                      status=task_status)
                if not task_status == 2:
                    if "不足" in msg:
                        raise serializers.ValidationError('库存不足, 出库失败')
                    elif "json错误" in msg:
                        raise serializers.ValidationError(f'出库接口调用失败,提示: {msg}')
                    else:
                        raise serializers.ValidationError(msg)
        elif status == 4:
            instance.status = 4
            instance.save()
            instance.final_plans.filter().update(status=5)
        return validated_data

    class Meta:
        model = FinalRubberyOutBoundOrder
        fields = '__all__'
        read_only_fields = ('order_no', 'warehouse_name', 'order_type')
