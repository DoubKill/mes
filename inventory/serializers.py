# -*- coding: UTF-8 -*-
"""
auther:
datetime: 2020/10/14
name:
"""
import datetime
import json
import time

from django.db import IntegrityError
from django.db.models import Sum
from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from basics.models import GlobalCode
from mes import settings
from mes.base_serializer import BaseModelSerializer
from mes.conf import STATION_LOCATION_MAP, COMMON_READ_ONLY_FIELDS
from quality.models import WMSMooneyLevel, MaterialSingleTypeExamineResult, UnqualifiedDealOrderDetail, \
    MaterialDealResult
from quality.utils import update_wms_quality_result
from recipe.models import MaterialAttribute
from .conf import wms_ip, wms_port, cb_ip, cb_port
from .models import MaterialInventory, BzFinalMixingRubberInventory, WmsInventoryStock, WmsInventoryMaterial, \
    WarehouseInfo, Station, WarehouseMaterialType, DeliveryPlanLB, DispatchPlan, DispatchLog, DispatchLocation, \
    DeliveryPlanFinal, MixGumOutInventoryLog, MixGumInInventoryLog, MaterialOutPlan, BzFinalMixingRubberInventoryLB, \
    BarcodeQuality, CarbonOutPlan, MixinRubberyOutBoundOrder, FinalRubberyOutBoundOrder, Depot, DepotSite, DepotPallt, \
    SulfurDepotSite, Sulfur, SulfurDepot, OutBoundDeliveryOrder, OutBoundDeliveryOrderDetail, WMSMaterialSafetySettings, \
    WmsNucleinManagement, WMSExceptHandle, MaterialOutboundOrder, MaterialOutHistoryOther, MaterialOutHistory, \
    FinalGumOutInventoryLog, FinalGumInInventoryLog, THOutHistory, THOutHistoryOther

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
    production_info = serializers.SerializerMethodField(read_only=True)

    def get_production_info(self, obj):
        pallet = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        if pallet:
            return {'equip_no': pallet.equip_no,
                    'factory_date': pallet.factory_date,
                    'classes': pallet.classes,
                    }
        else:
            return {'equip_no': "",
                    'factory_date': "",
                    'classes': "",
                    }

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
        if DeliveryPlan.objects.filter(location=location, status__in=(2, 4)).exists():
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
    production_info = serializers.SerializerMethodField(read_only=True)

    def get_production_info(self, obj):
        pallet = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        if pallet:
            return {'equip_no': pallet.equip_no,
                    'factory_date': pallet.factory_date,
                    'classes': pallet.classes,
                    }
        else:
            return {'equip_no': "",
                    'factory_date': "",
                    'classes': "",
                    }

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
        if DeliveryPlanFinal.objects.filter(location=location, status__in=(2, 4)).exists():
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
    begin_end_trains = serializers.SerializerMethodField(read_only=True)

    def get_material_type(self, obj):
        try:
            mt = obj.material_no.split("-")[1]
        except:
            mt = obj.material_no
        return mt

    def get_begin_end_trains(self, obj):
        try:
            trains = obj.memo.split(",")
            if len(trains) == 1:
                return [int(trains[0]), int(trains[0])]
            elif len(trains) == 2:
                return [int(trains[0]), int(trains[1])]
            else:
                return [0, 0]
        except:
            return [0, 0]

    def get_unit(self, obj):
        return 'kg'

    def get_unit_weight(self, obj):
        try:
            unit_weight = round(obj.total_weight / obj.qty,3)
        except:
            unit_weight = "数据异常"
        return unit_weight

    def get_product_info(self, obj):
        return {
            "equip_no": "",
            "classes": "",
            "product_time": ""
        }
        # if not obj.lot_no:
        #     return {
        #         "equip_no": "",
        #         "classes": "",
        #         "product_time": ""
        #     }
        # else:
        #     pf = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).last()
        #     if not pf:
        #         return {
        #             "equip_no": "",
        #             "classes": "",
        #             "product_time": ""
        #         }
        #     else:
        #         return {
        #             "equip_no": pf.equip_no,
        #             "classes": pf.classes,
        #             "product_time": pf.product_time.strftime('%Y-%m-%d %H:%M:%S')
        #         }

    def get_equip_no(self, obj):
        try:
            equip_no = obj.bill_id[-3:]
        except:
            equip_no = ""
        return equip_no

    class Meta:
        model = BzFinalMixingRubberInventory
        fields = "__all__"


class BzMixingRubberInventorySearchSerializer(BzFinalMixingRubberInventorySerializer):
    deal_suggestion = serializers.SerializerMethodField(read_only=True)
    yx_state = serializers.SerializerMethodField(read_only=True)
    locked_status = serializers.SerializerMethodField()

    def get_locked_status(self, obj):
        locked_lot_data = self.context['locked_lot_data']
        return locked_lot_data.get(obj.lot_no)

    def get_deal_suggestion(self, obj):
        if obj.lot_no:
            deal_result = MaterialDealResult.objects.filter(
                lot_no=obj.lot_no).first()
            if deal_result:
                if deal_result.deal_user:
                    return deal_result.deal_suggestion
                else:
                    return 'PASS' if deal_result.test_result == 'PASS' else None
            return ''
        return ''

    def get_yx_state(self, obj):
        product_validity_data = self.context['product_validity_data']
        period_of_validity = product_validity_data.get(obj.material_no)
        if not period_of_validity:
            return None
        now_time = datetime.datetime.now()
        min_expire_inventory_time = now_time - datetime.timedelta(days=period_of_validity)
        min_yj_inventory_et_time = min_expire_inventory_time + datetime.timedelta(days=3)
        if obj.in_storage_time < min_expire_inventory_time:
            return 'expired'
        if obj.in_storage_time > min_yj_inventory_et_time:
            return 'normal'
        else:
            return 'warning'


class BzFinalMixingRubberLBInventorySerializer(serializers.ModelSerializer):
    """终炼胶|帘布库共用序列化器"""
    material_type = serializers.SerializerMethodField(read_only=True)
    unit = serializers.SerializerMethodField(read_only=True)
    unit_weight = serializers.SerializerMethodField(read_only=True)
    product_info = serializers.SerializerMethodField(read_only=True)
    equip_no = serializers.SerializerMethodField(read_only=True)
    quality_status = serializers.SerializerMethodField(read_only=True)
    begin_end_trains = serializers.SerializerMethodField(read_only=True)

    def get_begin_end_trains(self, obj):
        try:
            trains = obj.memo.split(",")
            if len(trains) == 1:
                return [int(trains[0]), int(trains[0])]
            elif len(trains) == 2:
                return [int(trains[0]), int(trains[1])]
            else:
                return [0, 0]
        except:
            return [0, 0]

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
        return {
            "equip_no": "",
            "classes": "",
            "product_time": ""
        }
        # if not obj.lot_no:
        #     return {
        #         "equip_no": "",
        #         "classes": "",
        #         "product_time": ""
        #     }
        # else:
        #     pf = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).last()
        #     if not pf:
        #         return {
        #             "equip_no": "",
        #             "classes": "",
        #             "product_time": ""
        #         }
        #     else:
        #         return {
        #             "equip_no": pf.equip_no,
        #             "classes": pf.classes,
        #             "product_time": pf.product_time.strftime('%Y-%m-%d %H:%M:%S')
        #         }

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


class BzFinalRubberInventorySearchSerializer(BzFinalMixingRubberLBInventorySerializer):
    deal_suggestion = serializers.SerializerMethodField(read_only=True)
    yx_state = serializers.SerializerMethodField(read_only=True)
    locked_status = serializers.SerializerMethodField()

    def get_locked_status(self, obj):
        locked_lot_data = self.context['locked_lot_data']
        return locked_lot_data.get(obj.lot_no)

    def get_deal_suggestion(self, obj):
        if obj.lot_no:
            deal_result = MaterialDealResult.objects.filter(
                lot_no=obj.lot_no).first()
            if deal_result:
                if deal_result.deal_user:
                    return deal_result.deal_suggestion
                else:
                    return 'PASS' if deal_result.test_result == 'PASS' else None
            return ''
        return ''

    def get_yx_state(self, obj):
        product_validity_data = self.context['product_validity_data']
        period_of_validity = product_validity_data.get(obj.material_no)
        if not period_of_validity:
            return None
        now_time = datetime.datetime.now()
        min_expire_inventory_time = now_time - datetime.timedelta(days=period_of_validity)
        min_yj_inventory_et_time = min_expire_inventory_time + datetime.timedelta(days=3)
        if obj.in_storage_time < min_expire_inventory_time:
            return 'expired'
        if obj.in_storage_time > min_yj_inventory_et_time:
            return 'normal'
        else:
            return 'warning'

class WmsInventoryStockSerializer(serializers.ModelSerializer):
    unit_weight = serializers.SerializerMethodField(read_only=True)
    quality_status = serializers.SerializerMethodField(read_only=True)
    is_entering = serializers.SerializerMethodField(read_only=True)
    in_charged_tag = serializers.SerializerMethodField(read_only=True)
    mn_level = serializers.SerializerMethodField()

    def get_mn_level(self, obj):
        # 门尼等级信息
        wms_mooney_level = WMSMooneyLevel.objects.filter(
            h_upper_limit_value__isnull=False,
            material_no=obj.material_no).first()
        if not wms_mooney_level:
            return ""
        # 物料检测信息
        examine_data = MaterialSingleTypeExamineResult.objects.filter(
            type__name__icontains='门尼',
            material_examine_result__material__batch=obj.batch_no,
            material_examine_result__material__wlxxid=obj.material_no).first()
        if not examine_data:
            return ""
        ml_test_value = examine_data.value
        h_lower_limit_value = wms_mooney_level.h_lower_limit_value if wms_mooney_level.h_lower_limit_value else 0
        h_upper_limit_value = wms_mooney_level.h_upper_limit_value if wms_mooney_level.h_upper_limit_value else 0
        m_lower_limit_value = wms_mooney_level.m_lower_limit_value if wms_mooney_level.m_lower_limit_value else 0
        m_upper_limit_value = wms_mooney_level.m_upper_limit_value if wms_mooney_level.m_upper_limit_value else 0
        l_lower_limit_value = wms_mooney_level.l_lower_limit_value if wms_mooney_level.l_lower_limit_value else 0
        l_upper_limit_value = wms_mooney_level.l_upper_limit_value if wms_mooney_level.l_upper_limit_value else 0
        if h_lower_limit_value <= ml_test_value <= h_upper_limit_value:
            return '高门尼'
        elif m_lower_limit_value <= ml_test_value <= m_upper_limit_value:
            return '标准门尼'
        elif l_lower_limit_value <= ml_test_value <= l_upper_limit_value:
            return '低门尼'
        else:
            return ""

    def get_is_entering(self, obj):
        if obj.container_no.startswith('5'):
            return 'Y'
        else:
            return 'N'

    def get_in_charged_tag(self, obj):
        try:
            return self.context['ncm_data'].get(obj.batch_no.strip(), '未管控')
        except Exception:
            return "未管控"

    def get_unit_weight(self, obj):
        try:
            unit_weight = obj.total_weight / obj.qty
        except:
            unit_weight = "数据异常"
        return unit_weight

    def get_quality_status(self, obj):
        status_map = {1: "合格品", 2: "抽检中", 3: "不合格品", 4: "过期", 5: "待检"}
        return status_map.get(obj.quality_status, "不合格品")

    class Meta:
        model = WmsInventoryStock
        fields = "__all__"


class InventoryLogSerializer(serializers.ModelSerializer):
    product_info = serializers.SerializerMethodField(read_only=True)
    inout_num_type = serializers.SerializerMethodField(read_only=True)
    fin_time = serializers.SerializerMethodField(read_only=True)
    initiator = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = InventoryLog
        fields = "__all__"

    def get_initiator(self, obj):
        if obj.order_type == '入库':
            return obj.initiator
        if hasattr(obj, 'initiator'):
            task = OutBoundDeliveryOrderDetail.objects.filter(order_no=obj.order_no).first()
            if task:
                return task.created_user.username
            return obj.initiator
        return None

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
    initiator = serializers.SerializerMethodField()
    start_time = serializers.DateTimeField(source='task.start_time', read_only=True)
    fin_time = serializers.DateTimeField(source='task.fin_time', read_only=True)
    last_time = serializers.DateTimeField(source='task.last_time', read_only=True)
    task_no = serializers.CharField(source='task.order_no', read_only=True)
    order_type = serializers.SerializerMethodField()
    batch_no = serializers.CharField(max_length=64, read_only=True)
    is_entering = serializers.SerializerMethodField()
    sl = serializers.DecimalField(max_digits=18, decimal_places=4, read_only=True)
    zl = serializers.DecimalField(max_digits=18, decimal_places=4, read_only=True)
    task_status_name = serializers.SerializerMethodField()

    def get_initiator(self, obj):
        try:
            if obj.task.initiator == 'MES':
                order = MaterialOutboundOrder.objects.filter(order_no=obj.task.order_no).first()
                if order:
                    return order.created_username
                return obj.task.initiator
            return obj.task.initiator
        except Exception:
            return ""

    def get_is_entering(self, object):
        if object.pallet_no.startswith('5'):
            return 'Y'
        else:
            return 'N'

    def get_order_type(self, obj):
        if obj.inout_type == 1:
            return "入库"
        else:
            return "出库"

    def get_task_status_name(self, obj):
        status_dict = {1: '待处理',
                       2: '处理中',
                       3: '完成',
                       4: '已解绑',
                       5: '取消',
                       6: '异常',
                       12: '强制完成'}
        try:
            return status_dict.get(obj.task_status, '未知')
        except Exception:
            return ""


class THInOutCommonSerializer(serializers.Serializer):
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
    initiator = serializers.SerializerMethodField()
    start_time = serializers.DateTimeField(source='task.start_time', read_only=True)
    # fin_time = serializers.DateTimeField(source='task.fin_time', read_only=True)
    last_time = serializers.DateTimeField(source='task.last_time', read_only=True)
    task_no = serializers.CharField(source='task.order_no', read_only=True)
    order_type = serializers.SerializerMethodField()
    batch_no = serializers.CharField(max_length=64, read_only=True)
    is_entering = serializers.SerializerMethodField()
    sl = serializers.DecimalField(max_digits=18, decimal_places=4, read_only=True)
    zl = serializers.DecimalField(max_digits=18, decimal_places=4, read_only=True)
    task_status_name = serializers.SerializerMethodField()

    def get_initiator(self, obj):
        try:
            if obj.task.initiator == 'MES':
                order = MaterialOutboundOrder.objects.filter(order_no=obj.task.order_no).first()
                if order:
                    return order.created_username
                return obj.task.initiator
            return obj.task.initiator
        except Exception:
            return ""

    def get_is_entering(self, object):
        if object.pallet_no.startswith('5'):
            return 'Y'
        else:
            return 'N'

    def get_order_type(self, obj):
        if obj.inout_type == 1:
            return "入库"
        else:
            return "出库"

    def get_task_status_name(self, obj):
        status_dict = {1: '待处理',
                       2: '处理中',
                       3: '完成',
                       4: '已解绑',
                       5: '取消',
                       6: '异常',
                       12: '强制完成'}
        try:
            return status_dict.get(obj.task_status, '未知')
        except Exception:
            return ""


class DepotModelSerializer(serializers.ModelSerializer):
    """线边库 库区"""
    depot_name = serializers.CharField(max_length=64, help_text='库区',
                                       validators=[UniqueValidator(queryset=Depot.objects.filter(is_use=True), message='该库区已存在')])

    class Meta:
        model = Depot
        fields = '__all__'


class DepotSiteModelSerializer(serializers.ModelSerializer):
    """线边库 库位"""
    depot_site_name = serializers.CharField(max_length=64, help_text='库位',
                                       validators=[UniqueValidator(queryset=DepotSite.objects.filter(is_use=True), message='该库位已存在')])
    class Meta:
        model = DepotSite
        fields = ['depot_name', 'depot_site_name', 'description', 'depot', 'id']


class DepotPalltModelSerializer(serializers.ModelSerializer):
    """线边库库存查询"""

    product_no = serializers.ReadOnlyField(source='pallet_data.product_no')

    begin_trains = serializers.ReadOnlyField(source='pallet_data.begin_trains')
    end_trains = serializers.ReadOnlyField(source='pallet_data.end_trains')
    actual_weight = serializers.ReadOnlyField(source='pallet_data.actual_weight')
    class Meta:
        model = DepotPallt
        fields = ['product_no', 'begin_trains', 'end_trains', 'actual_weight']


class DepotPalltInfoModelSerializer(serializers.ModelSerializer):
    product_no = serializers.ReadOnlyField(source='pallet_data.product_no')
    depot_site_name = serializers.ReadOnlyField(source='depot_site.depot_site_name')
    lot_no = serializers.ReadOnlyField(source='pallet_data.lot_no')
    class Meta:
        model = DepotPallt
        fields = ['enter_time', 'depot_name', 'depot_site_name',
                  'product_no', 'outer_time', 'lot_no']


class PalletDataModelSerializer(serializers.ModelSerializer):
    """线边库出入库管理"""
    depot_site_name = serializers.ReadOnlyField(source='palletfeedbacks.depot_site.depot_site_name')
    pallet_status = serializers.ReadOnlyField(source='palletfeedbacks.pallet_status')
    depot_name = serializers.ReadOnlyField(source='palletfeedbacks.depot_site.depot.depot_name')
    enter_time = serializers.DateTimeField(source='palletfeedbacks.enter_time')
    outer_time = serializers.DateTimeField(source='palletfeedbacks.outer_time')
    depot_pallet_id = serializers.ReadOnlyField(source='palletfeedbacks.id')

    class Meta:
        model = PalletFeedbacks
        fields = ['factory_date', 'product_no', 'classes', 'equip_no', 'begin_trains', 'end_trains', 'plan_classes_uid',
                  'enter_time','outer_time', 'pallet_status', 'depot_site_name', 'depot_name', 'id', 'lot_no', 'depot_pallet_id']


class DepotResumeModelSerializer(serializers.ModelSerializer):
    """线边库出入库履历"""
    factory_date = serializers.ReadOnlyField(source='pallet_data.factory_date')
    classes = serializers.ReadOnlyField(source='pallet_data.classes')
    equip_no = serializers.ReadOnlyField(source='pallet_data.equip_no')
    product_no = serializers.ReadOnlyField(source='pallet_data.product_no')
    begin_trains = serializers.ReadOnlyField(source='pallet_data.begin_trains')
    end_trains = serializers.ReadOnlyField(source='pallet_data.end_trains')
    lot_no = serializers.ReadOnlyField(source='pallet_data.lot_no')
    plan_classes_uid = serializers.ReadOnlyField(source='pallet_data.plan_classes_uid')

    class Meta:
        model = DepotPallt
        fields = ['factory_date', 'classes', 'equip_no', 'product_no', 'begin_trains', 'lot_no', 'plan_classes_uid',
                  'end_trains', 'pallet_status', 'enter_time', 'outer_time', 'depot_name', 'depot_site_name']


class SulfurDepotModelSerializer(serializers.ModelSerializer):
    """硫磺库 库区"""
    depot_name = serializers.CharField(max_length=64, help_text='库区',
                                       validators=[UniqueValidator(queryset=SulfurDepot.objects.filter(is_use=True), message='该库区已存在')])
    class Meta:
        model = SulfurDepot
        fields = '__all__'


class SulfurDepotSiteModelSerializer(serializers.ModelSerializer):
    """硫磺库 库位"""
    depot_site_name = serializers.CharField(max_length=64, help_text='库位',
                                       validators=[UniqueValidator(queryset=SulfurDepotSite.objects.filter(is_use=True), message='该库位已存在')])
    depot_name = serializers.ReadOnlyField(source='depot.depot_name')
    class Meta:
        model = SulfurDepotSite
        fields = ['depot_name', 'depot_site_name', 'description', 'depot', 'id']


class SulfurDataModelSerializer(serializers.ModelSerializer):
    """硫磺库出入库管理"""
    depot = serializers.ReadOnlyField(source='depot_site.depot.id')
    depot_site = serializers.ReadOnlyField(source='depot_site.id')
    depot_name = serializers.ReadOnlyField(source='depot_site.depot.depot_name')
    depot_site_name = serializers.ReadOnlyField(source='depot_site.depot_site_name')
    enter_time = serializers.DateTimeField(read_only=True, help_text='入库时间')

    class Meta:
        model = Sulfur
        fields = ['id', 'name', 'product_no', 'provider', 'lot_no', 'depot_name', 'depot_site_name', 'enter_time', 'sulfur_status',
                  'weight', 'num', 'depot', 'depot_site']


class DepotSulfurModelSerializer(serializers.ModelSerializer):
    """硫磺库库存查询"""

    class Meta:
        model = Sulfur
        fields = ['name', 'product_no', 'provider', 'lot_no', 'num']


class DepotSulfurInfoModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = Sulfur
        fields = ['depot_name', 'depot_site_name']


class SulfurResumeModelSerializer(serializers.ModelSerializer):
    """硫磺库履历"""

    class Meta:
        model = Sulfur
        fields = ['name', 'product_no', 'provider', 'lot_no', 'sulfur_status', 'enter_time', 'outer_time',
                  'depot_site', 'depot_name', 'depot_site_name']


class SulfurAutoPlanSerializer(serializers.ModelSerializer):
    lot_no = serializers.CharField(help_text='物料条码')
    product_no = serializers.CharField(read_only=True)
    weight = serializers.CharField(read_only=True)
    depot_name = serializers.ReadOnlyField(source='depot_site.depot.depot_name')
    depot_site_name = serializers.ReadOnlyField(source='depot_site.depot_site_name')
    state = serializers.IntegerField(write_only=True)

    class Meta:
        model = Sulfur
        fields = ['lot_no', 'depot_site', 'state', 'depot_name', 'depot_site_name', 'product_no', 'weight']


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
                "msgConut": str(len(items)),
                "SENDUSER": username,
                "items": items
            }
            json_data = json.dumps(json_data, ensure_ascii=False)
            sender = OUTWORKUploader(end_type="指定出库")
            result = sender.request(instance.order_no, '指定出库', str(len(items)), username, json_data)
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
            instance.mixin_plans.filter(status__gt=1).update(status=5)
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
                "msgConut": str(len(items)),
                "SENDUSER": username,
                "items": items
            }
            json_data = json.dumps(json_data, ensure_ascii=False)
            sender = OUTWORKUploaderLB(end_type="指定出库")
            result = sender.request(instance.order_no, '指定出库', str(len(items)), username, json_data)
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
            instance.final_plans.filter(status__gt=1).update(status=5)
        return validated_data

    class Meta:
        model = FinalRubberyOutBoundOrder
        fields = '__all__'
        read_only_fields = ('order_no', 'warehouse_name', 'order_type')


class OutBoundDeliveryOrderUpdateSerializer(BaseModelSerializer):

    def update(self, instance, validated_data):
        if 'status' in validated_data:
            if validated_data['status'] == 4:
                instance.outbound_delivery_details.exclude(status=3).update(status=4)
        return super().update(instance, validated_data)

    class Meta:
        model = OutBoundDeliveryOrder
        fields = '__all__'
        read_only_fields = ('created_date', 'last_updated_date', 'delete_date',
                            'delete_flag', 'created_user', 'last_updated_user',
                            'delete_user', 'order_no', 'need_qty',
                            'work_qty', 'finished_qty', 'need_weight', 'finished_weight',
                            'inventory_type', 'inventory_reason')


class OutBoundDeliveryOrderSerializer(BaseModelSerializer):
    work_qty = serializers.SerializerMethodField(read_only=True)
    finished_qty = serializers.SerializerMethodField(read_only=True)
    period_of_validity = serializers.SerializerMethodField(read_only=True)
    latest_task_time = serializers.SerializerMethodField(read_only=True)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['need_qty'] = ret['order_qty'] - ret['work_qty'] - ret['finished_qty']
        return ret

    def get_period_of_validity(self, obj):
        material_detail = MaterialAttribute.objects.filter(material__material_no=obj.product_no).first()
        if material_detail:
                return material_detail.period_of_validity
        else:
            return None

    def get_work_qty(self, obj):
        work_qty = obj.outbound_delivery_details.filter(status=2).aggregate(work_qty=Sum('qty'))['work_qty']
        return work_qty if work_qty else 0

    def get_finished_qty(self, obj):
        finished_qty = obj.outbound_delivery_details.filter(status=3).aggregate(finished_qty=Sum('qty'))['finished_qty']
        return finished_qty if finished_qty else 0

    def get_latest_task_time(self, obj):
        last_task = obj.outbound_delivery_details.order_by('id').last()
        if last_task:
            return last_task.created_date.strftime('%Y-%m-%d %H:%M:%S')
        return ""

    def validate(self, attrs):
        order_type = attrs.get('order_type', 1)
        if order_type == 3:  # 指定托盘出库
            attrs.pop('factory_date', '')
            attrs.pop('product_no', '')
            attrs.pop('equip_no', '')
            attrs.pop('classes', '')
            attrs.pop('begin_trains', '')
            attrs.pop('end_trains', '')
            attrs.pop('quality_status', '')
            attrs['order_qty'] = 99999
            if not attrs.get('pallet_no'):
                raise serializers.ValidationError('请填写托盘号！')
            if attrs['warehouse'] == '混炼胶库':
                station = attrs['station']
                bz_obj = BzFinalMixingRubberInventory.objects.using('bz').filter(container_no=attrs['pallet_no']).last()
                if not bz_obj:
                    raise serializers.ValidationError('此托盘不存在该库区内！')
                if station == '一层前端':
                    if bz_obj.location[0] not in ('3', '4'):
                        raise serializers.ValidationError('此托盘无法从该出库口出库！')
                elif station == '二层前端':
                    if bz_obj.location[0] not in ('1', '2'):
                        raise serializers.ValidationError('此托盘无法从该出库口出库！')
                elif station == '一层后端':
                    raise serializers.ValidationError('该出库口不可用！')
            else:
                bz_obj = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(container_no=attrs['pallet_no']).last()
                if not bz_obj:
                    raise serializers.ValidationError('此托盘不存在该库区内！')
                if bz_obj.store_name != '炼胶库':
                    raise serializers.ValidationError('非承放胶块托盘！')
        elif order_type == 2:  # 指定胶料生产信息
            attrs.pop('pallet_no', '')
            attrs.pop('quality_status', '')
            if not all([attrs.get('factory_date'),
                        attrs.get('product_no'),
                        attrs.get('equip_no'),
                        attrs.get('classes'),
                        attrs.get('begin_trains'),
                        attrs.get('end_trains')]):
                raise serializers.ValidationError('请输入完整的的胶料生产信息！')
            attrs['order_qty'] = attrs.get('end_trains') - attrs.get('begin_trains') + 1
        else:  # 普通出库
            if not all([attrs.get('product_no'), attrs['quality_status']]):
                raise serializers.ValidationError('参数缺失！')
            return {'order_qty': attrs.get('order_qty', 0),
                    'product_no': attrs['product_no'],
                    'quality_status': attrs['quality_status'],
                    'station': attrs['station'],
                    'warehouse': attrs['warehouse']}
        return attrs

    def create(self, validated_data):
        warehouse = validated_data.get('warehouse')
        last_order = OutBoundDeliveryOrder.objects.filter(
            created_date__date=datetime.datetime.now().date()
        ).order_by('created_date').last()
        if last_order:
            last_ordering = str(int(last_order.order_no[12:])+1)
            if len(last_ordering) <= 5:
                ordering = last_ordering.zfill(5)
            else:
                ordering = last_ordering.zfill(len(last_ordering))
        else:
            ordering = '00001'
        validated_data['order_no'] = 'MES{}{}{}'.format('Z' if warehouse == '终炼胶库' else 'H',
                                                         datetime.datetime.now().date().strftime('%Y%m%d'),
                                                         ordering)
        return super(OutBoundDeliveryOrderSerializer, self).create(validated_data)

    class Meta:
        model = OutBoundDeliveryOrder
        fields = '__all__'
        read_only_fields = ('created_date', 'last_updated_date', 'delete_date',
                            'delete_flag', 'created_user', 'last_updated_user',
                            'delete_user', 'order_no', 'need_qty',
                            'work_qty', 'finished_qty', 'need_weight', 'finished_weight',
                            'inventory_type', 'inventory_reason')


class OutBoundDeliveryOrderDetailSerializer(BaseModelSerializer):

    def create(self, validated_data):
        warehouse = validated_data['outbound_delivery_order'].warehouse
        while 1:
            last_order = OutBoundDeliveryOrderDetail.objects.filter(
                created_date__date=datetime.datetime.now().date()
            ).order_by('id').last()
            if last_order:
                last_ordering = str(int(last_order.order_no[12:]) + 1)
                if len(last_ordering) <= 5:
                    ordering = last_ordering.zfill(5)
                else:
                    ordering = last_ordering.zfill(len(last_ordering))
            else:
                ordering = '00001'
            order_no = 'CHD{}{}{}'.format('Z' if warehouse == '终炼胶库' else 'H',
                                          datetime.datetime.now().date().strftime('%Y%m%d'),
                                          ordering)
            validated_data['order_no'] = order_no
            validated_data['created_user'] = self.context['request'].user
            try:
                instance = OutBoundDeliveryOrderDetail.objects.create(**validated_data)
                break
            except IntegrityError:
                pass
        return instance

    class Meta:
        model = OutBoundDeliveryOrderDetail
        fields = '__all__'
        read_only_fields = ('created_date', 'last_updated_date', 'delete_date',
                            'delete_flag', 'created_user', 'last_updated_user',
                            'delete_user', 'order_no', 'equip', 'dispatch', 'finish_time')


class OutBoundDeliveryOrderDetailListSerializer(BaseModelSerializer):
    warehouse = serializers.CharField(source='outbound_delivery_order.warehouse', help_text='库区', read_only=True)
    station = serializers.CharField(source='outbound_delivery_order.station', help_text='出库口', read_only=True)
    product_no = serializers.CharField(source='outbound_delivery_order.product_no', help_text='胶料名称', read_only=True)

    class Meta:
        model = OutBoundDeliveryOrderDetail
        fields = '__all__'


class OutBoundTasksSerializer(BaseModelSerializer):
    created_user = serializers.CharField(source='created_user.username')
    material_no = serializers.CharField(source='outbound_delivery_order.product_no')
    inventory_reason = serializers.CharField(source='quality_status')
    production_info = serializers.SerializerMethodField()

    def get_production_info(self, obj):
        pallet = PalletFeedbacks.objects.filter(lot_no=obj.lot_no).first()
        if pallet:
            return {'equip_no': pallet.equip_no,
                    'factory_date': pallet.factory_date,
                    'classes': pallet.classes,
                    }
        else:
            return {'equip_no': "",
                    'factory_date': "",
                    'classes': "",
                    }

    class Meta:
        model = OutBoundDeliveryOrderDetail
        fields = '__all__'


class WmsInventoryMaterialSerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        ins = WMSMaterialSafetySettings.objects.filter(wms_material_code=data['material_no']).first()
        if ins:
            data['avg_consuming_weight'] = ins.avg_consuming_weight
            data['avg_setting_weight'] = ins.avg_setting_weight
            data['type'] = ins.type
            data['warning_days'] = ins.warning_days
            data['created_username'] = ins.created_user.username
            data['created_time'] = ins.created_date.strftime('%Y-%m-%d %H:%M:%S')
            data['warning_weight'] = ins.warning_weight
        else:
            data['avg_consuming_weight'] = None
            data['avg_setting_weight'] = None
            data['type'] = None
            data['warning_days'] = None
            data['created_username'] = None
            data['created_time'] = None
            data['warning_weight'] = None
        return data

    class Meta:
        model = WmsInventoryMaterial
        fields = '__all__'


class WmsNucleinManagementSerializer(BaseModelSerializer):

    def create(self, validated_data):
        if WmsNucleinManagement.objects.filter(
                batch_no=validated_data['batch_no'],
                material_no=validated_data['material_no']).exists():
            raise serializers.ValidationError('请勿重复添加批次号为{}的物料信息'.format(validated_data['batch_no']))
        return super().create(validated_data)

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        if 'locked_status' in validated_data:
            if validated_data['locked_status'] == '已锁定' and not settings.DEBUG:
                data_list = [{
                    "BatchNo": instance.batch_no,
                    "MaterialCode": instance.material_no,
                    "CheckResult": 2}]
                update_wms_quality_result(data_list)
        return validated_data

    class Meta:
        model = WmsNucleinManagement
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class WMSExceptHandleSerializer(BaseModelSerializer):

    class Meta:
        model = WMSExceptHandle
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialOutHistoryOtherSerializer(serializers.ModelSerializer):
    initiator = serializers.SerializerMethodField()
    qty = serializers.SerializerMethodField()
    task_type_name = serializers.SerializerMethodField()
    task_status_name = serializers.SerializerMethodField()

    def get_initiator(self, obj):
        db = self.context['db']
        order_type = 1 if db == 'wms' else 2
        if obj.initiator == 'MES':
            order = MaterialOutboundOrder.objects.filter(order_no=obj.order_no,
                                                         order_type=order_type).first()
            if order:
                return order.created_username
            return obj.initiator
        return obj.initiator

    def get_qty(self, obj):
        try:
            qty = obj.moh.aggregate(qty=Sum('qty'))['qty']
            return qty if qty else 0
        except Exception:
            return 0

    def get_task_status_name(self, obj):
        return obj.get_task_status_display()

    def get_task_type_name(self, obj):
        return obj.get_task_type_display()

    class Meta:
        model = MaterialOutHistoryOther
        fields = '__all__'


class THOutHistoryOtherSerializer(serializers.ModelSerializer):
    initiator = serializers.SerializerMethodField()
    qty = serializers.SerializerMethodField()
    task_type_name = serializers.SerializerMethodField()
    task_status_name = serializers.SerializerMethodField()

    def get_initiator(self, obj):
        db = self.context['db']
        order_type = 1 if db == 'wms' else 2
        if obj.initiator == 'MES':
            order = MaterialOutboundOrder.objects.filter(order_no=obj.order_no,
                                                         order_type=order_type).first()
            if order:
                return order.created_username
            return obj.initiator
        return obj.initiator

    def get_qty(self, obj):
        try:
            qty = obj.moh.aggregate(qty=Sum('qty'))['qty']
            return qty if qty else 0
        except Exception:
            return 0

    def get_task_status_name(self, obj):
        return obj.get_task_status_display()

    def get_task_type_name(self, obj):
        return obj.get_task_type_display()

    class Meta:
        model = THOutHistoryOther
        fields = '__all__'


class MaterialOutHistorySerializer(serializers.ModelSerializer):
    created_time = serializers.CharField(source='task.start_time')
    initiator = serializers.SerializerMethodField()
    task_order_no = serializers.CharField(source='task.order_no')
    entrance_name = serializers.SerializerMethodField()
    tunnel = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    def get_initiator(self, obj):
        db = self.context['db']
        order_type = 1 if db == 'wms' else 2
        if obj.task.initiator == 'MES':
            order = MaterialOutboundOrder.objects.filter(order_no=obj.task.order_no,
                                                         order_type=order_type).first()
            if order:
                return order.created_username
            return obj.task.initiator
        return obj.task.initiator

    def get_entrance_name(self, obj):
        return self.context['entrance_data'].get(obj.entrance)

    def get_tunnel(self, obj):
        return obj.location.split('-')[1]

    def get_status(self, obj):
        status_dict = {1: '待处理',
                       2: '处理中',
                       3: '完成',
                       4: '已解绑',
                       5: '取消',
                       6: '异常',
                       12: '强制完成'}
        return status_dict.get(obj.task_status)

    class Meta:
        model = MaterialOutHistory
        fields = '__all__'


class THOutHistorySerializer(serializers.ModelSerializer):
    created_time = serializers.CharField(source='task.start_time')
    initiator = serializers.SerializerMethodField()
    task_order_no = serializers.CharField(source='task.order_no')
    entrance_name = serializers.SerializerMethodField()
    tunnel = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    def get_initiator(self, obj):
        db = self.context['db']
        order_type = 1 if db == 'wms' else 2
        if obj.task.initiator == 'MES':
            order = MaterialOutboundOrder.objects.filter(order_no=obj.task.order_no,
                                                         order_type=order_type).first()
            if order:
                return order.created_username
            return obj.task.initiator
        return obj.task.initiator

    def get_entrance_name(self, obj):
        return self.context['entrance_data'].get(obj.entrance)

    def get_tunnel(self, obj):
        return obj.location.split('-')[1]

    def get_status(self, obj):
        status_dict = {1: '待处理',
                       2: '处理中',
                       3: '完成',
                       4: '已解绑',
                       5: '取消',
                       6: '异常',
                       12: '强制完成'}
        return status_dict.get(obj.task_status)

    class Meta:
        model = THOutHistory
        fields = '__all__'


class ProductInOutHistorySerializer(serializers.ModelSerializer):

    def to_representation(self, instance):
        ware_house = self.context['ware_house']
        inout_type = self.context['inout_type']
        ret = super().to_representation(instance)
        lot_no = ret['lot_no']
        memo = ''
        outbound_user = ''
        equip_no = ''
        order_no = ''
        if lot_no and lot_no != '88888888':
            equip_no = lot_no[4:7] if lot_no[4:7].startswith('Z') else ""
            pallet_data = PalletFeedbacks.objects.filter(lot_no=lot_no).first()
            if pallet_data:
                memo = '{}-{}'.format(pallet_data.begin_trains, pallet_data.end_trains) if pallet_data.begin_trains != pallet_data.end_trains else pallet_data.begin_trains
        if ware_house == '混炼胶库':
            if inout_type == 'in':
                inbound_order_no = ret['order_no']
                inbound_time = ret['start_time']
                out_history = MixGumOutInventoryLog.objects.using('bz').filter(lot_no=lot_no,
                                                                               pallet_no=ret['pallet_no'],
                                                                               material_no=ret['material_no'],
                                                                               location=ret['location']
                                                                               ).first()
                if out_history:
                    outbound_order_no = out_history.order_no
                    outbound_time = out_history.start_time.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    outbound_order_no = ''
                    outbound_time = ''
            else:
                outbound_order_no = ret['order_no']
                outbound_time = ret['start_time']
                in_history = MixGumInInventoryLog.objects.using('bz').filter(lot_no=lot_no,
                                                                             pallet_no=ret['pallet_no'],
                                                                             material_no=ret['material_no'],
                                                                             location=ret['location']
                                                                             ).first()
                if in_history:
                    inbound_order_no = in_history.order_no
                    inbound_time = in_history.start_time.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    inbound_order_no = ''
                    inbound_time = ''
        else:
            if inout_type == 'in':
                inbound_order_no = ret['order_no']
                inbound_time = ret['start_time']
                out_history = FinalGumOutInventoryLog.objects.using('lb').filter(lot_no=lot_no,
                                                                                 pallet_no=ret['pallet_no'],
                                                                                 material_no=ret['material_no'],
                                                                                 location=ret['location']
                                                                                 ).first()
                if out_history:
                    outbound_order_no = out_history.order_no
                    outbound_time = out_history.start_time.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    outbound_order_no = ''
                    outbound_time = ''
            else:
                outbound_order_no = ret['order_no']
                outbound_time = ret['start_time']
                in_history = FinalGumInInventoryLog.objects.using('lb').filter(lot_no=lot_no,
                                                                               pallet_no=ret['pallet_no'],
                                                                               material_no=ret['material_no'],
                                                                               location=ret['location']
                                                                               ).first()
                if in_history:
                    inbound_order_no = in_history.order_no
                    inbound_time = in_history.start_time.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    inbound_order_no = ''
                    inbound_time = ''
        if outbound_order_no:
            if outbound_order_no.startswith('CHD'):
                out_order = OutBoundDeliveryOrderDetail.objects.filter(order_no=outbound_order_no).first()
                if out_order:
                    outbound_user = out_order.created_user.username
                    order_no = out_order.outbound_delivery_order.order_no
        ret['inbound_time'] = inbound_time
        ret['inbound_order_no'] = inbound_order_no
        ret['outbound_order_no'] = outbound_order_no
        ret['outbound_user'] = outbound_user
        ret['outbound_time'] = outbound_time
        ret['product_no'] = ret['material_no']
        ret['equip_no'] = equip_no
        ret['memo'] = memo
        ret['order_no'] = order_no
        return ret

    class Meta:
        model = InventoryLog
        fields = ('lot_no', 'order_no', 'pallet_no', 'location', 'qty', 'weight', 'material_no', 'start_time')