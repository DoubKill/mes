import datetime
import json
import logging
import random
from io import BytesIO

import requests
import xlwt
from django.core.paginator import Paginator
from django.db.models import Sum
from django.db.transaction import atomic
from django.forms import model_to_dict
from django.http import HttpResponse

from django.utils.decorators import method_decorator
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from basics.models import GlobalCode, WorkSchedulePlan
from inventory.filters import StationFilter, PutPlanManagementLBFilter, PutPlanManagementFilter, \
    DispatchPlanFilter, DispatchLogFilter, DispatchLocationFilter, InventoryFilterBackend, PutPlanManagementFinalFilter, \
    MaterialPlanManagementFilter, BarcodeQualityFilter, CarbonPlanManagementFilter
from inventory.models import InventoryLog, WarehouseInfo, Station, WarehouseMaterialType, DeliveryPlanStatus, \
    BzFinalMixingRubberInventoryLB, DeliveryPlanLB, DispatchPlan, DispatchLog, DispatchLocation, \
    MixGumOutInventoryLog, MixGumInInventoryLog, DeliveryPlanFinal, MaterialOutPlan, BarcodeQuality, MaterialOutHistory, \
    MaterialInHistory, MaterialInventoryLog, FinalGumOutInventoryLog, \
    MaterialInHistory, MaterialInventoryLog, CarbonOutPlan
from inventory.models import DeliveryPlan, MaterialInventory
from inventory.serializers import PutPlanManagementSerializer, \
    OverdueMaterialManagementSerializer, WarehouseInfoSerializer, StationSerializer, WarehouseMaterialTypeSerializer, \
    PutPlanManagementSerializerLB, BzFinalMixingRubberLBInventorySerializer, DispatchPlanSerializer, \
    DispatchLogSerializer, DispatchLocationSerializer, DispatchLogCreateSerializer, PutPlanManagementSerializerFinal, \
    InventoryLogOutSerializer, MixGumOutInventoryLogSerializer, MixGumInInventoryLogSerializer, \
    MaterialPlanManagementSerializer, BarcodeQualitySerializer, WmsStockSerializer, InOutCommonSerializer, \
    CarbonPlanManagementSerializer
from inventory.models import WmsInventoryStock
from inventory.serializers import BzFinalMixingRubberInventorySerializer, \
    WmsInventoryStockSerializer, InventoryLogSerializer
from mes.common_code import SqlClient
from mes.conf import WMS_CONF
from mes.derorators import api_recorder
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions

from mes.paginations import SinglePageNumberPagination
from mes.permissions import PermissionClass
from plan.models import ProductClassesPlan, ProductBatchingClassesPlan, BatchingClassesPlan
from production.models import PalletFeedbacks, TrainsFeedbacks
from quality.deal_result import receive_deal_result
from quality.models import LabelPrint, Train
from recipe.models import Material, MaterialAttribute
from terminal.models import LoadMaterialLog, WeightBatchingLog, WeightPackageLog
from .conf import wms_ip, wms_port, IS_BZ_USING
from .conf import wms_ip, wms_port, cb_ip, cb_port
from .models import MaterialInventory as XBMaterialInventory
from .models import BzFinalMixingRubberInventory
from .serializers import XBKMaterialInventorySerializer

logger = logging.getLogger('send_log')


@method_decorator([api_recorder], name="dispatch")
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
        material_no = params.get("material_no")
        filter_str = ""
        if material_type:
            if filter_str:
                filter_str += f" and tim.MaterialGroupName like '%%{material_type}%%'"
            else:
                filter_str += f" where tim.MaterialGroupName like '%%{material_type}%%'"
        if material_no:
            if filter_str:
                filter_str += f" and tis.MaterialCode like '%%{material_no}%%'"
            else:
                filter_str += f" where tis.MaterialCode like '%%{material_no}%%'"
        sql = f"""select sum(tis.Quantity) qty, max(tis.MaterialName) material_name,
                       sum(tis.WeightOfActual) weight,tis.MaterialCode material_no,
                       max(tis.ProductionAddress) address, sum(tis.WeightOfActual)/sum(tis.Quantity) unit_weight,
                       max(tis.WeightUnit) unit, max(tim.MaterialGroupName) material_type,
                       Row_Number() OVER (order by tis.MaterialCode) sn, tis.StockDetailState status
                            from t_inventory_stock tis left join t_inventory_material tim on tim.MaterialCode=tis.MaterialCode
                        {filter_str}
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


@method_decorator([api_recorder], name="dispatch")
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
        material_no = params.get("material_no")
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
        filter_str = ""
        if stage:
            if stage not in stage_list:
                raise ValidationError("胶料段次异常请修正后重试")
            if filter_str:
                filter_str += f" AND 物料编码 like '%{stage}%'"
            else:
                filter_str += f" where 物料编码 like '%{stage}%'"
        if material_no:
            if filter_str:
                filter_str += f" AND 物料编码 like '%{material_no}%'"
            else:
                filter_str += f" where 物料编码 like '%{material_no}%'"
        sql = f"""SELECT max(库房名称) as 库房名称, sum(数量) as 数量, sum(重量) as 重量, max(品质状态) as 品质状态, 物料编码, Row_Number() OVER (order by 物料编码) sn
            FROM v_ASRS_STORE_MESVIEW {filter_str} group by 物料编码"""
        sql_all = """SELECT sum(数量) FROM v_ASRS_STORE_MESVIEW"""
        sql_fm = """SELECT sum(数量) FROM v_ASRS_STORE_MESVIEW where 物料编码 like '%FM%'"""
        sc = SqlClient(sql=sql)
        sc_fm = SqlClient(sql=sql_fm)
        sc_all = SqlClient(sql=sql_all)
        fm_count = sc_fm.all()[0][0]
        other_count = sc_all.all()[0][0] - fm_count
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
        return Response({'results': result, "count": count, "fm_count": fm_count, "other_count": other_count})


@method_decorator([api_recorder], name="dispatch")
class OutWorkFeedBack(APIView):

    # 出库反馈
    @atomic
    def post(self, request):
        """WMS->MES:任务编号、物料信息ID、物料名称、PDM号（促进剂以外为空）、批号、条码、重量、重量单位、
        生产日期、使用期限、托盘RFID、工位（出库口）、MES->WMS:信息接收成功or失败"""
        # 任务编号

        data = request.data
        # data = {'order_no':'20201114131845',"pallet_no":'20102494',
        #         'location':'二层前端','qty':'2','weight':'2.00',
        #         'quality_status':'合格','lot_no':'122222',
        #         'inout_num_type':'123456','fin_time':'2020-11-10 15:02:41'
        #         }
        if data:
            lot_no = data.get("lot_no", "99999999")  # 给一个无法查到的lot_no
            data = dict(data)
            data.pop("status", None)
            if data.get("inventory_type") == "生产出库":
                data["inout_num_type"] = "正常出库"
            elif data.get("inventory_type") == "快检出库":
                data["inout_num_type"] = "指定出库"
            else:
                data["inout_num_type"] = data.get("inventory_type")
            order_no = data.get('order_no')
            if order_no:
                if InventoryLog.objects.filter(order_no=order_no, pallet_no=data.get("pallet_no")).exists():
                    return Response({"99": "FALSE", "message": "该托盘已反馈"})
                temp = InventoryLog.objects.filter(order_no=order_no).aggregate(all_qty=Sum('qty'))
                all_qty = temp.get("all_qty")
                if all_qty:
                    all_qty += int(data.get("qty"))
                else:
                    all_qty = int(data.get("qty"))
                dp_obj = DeliveryPlan.objects.filter(order_no=order_no).first()

                # 这部分最开始做的时候没有设计好，也没有考虑全，目前只能按照一个库一个库去匹配这种方式去判断订单是否正确
                if dp_obj:
                    need_qty = dp_obj.need_qty
                else:
                    dp_obj = DeliveryPlanFinal.objects.filter(order_no=order_no).first()
                    if dp_obj:
                        need_qty = dp_obj.need_qty
                    else:
                        dp_obj = DeliveryPlanLB.objects.filter(order_no=order_no).first()
                        if dp_obj:
                            need_qty = dp_obj.need_qty
                        else:
                            return Response({"99": "FALSE", "message": "该订单非mes下发订单"})
                station = dp_obj.station
                station_dict = {
                    "一层前端": 3,
                    "一层后端": 4,
                    "二层前端": 5,
                    "二层后端": 6,
                    "炼胶#出库口#1": 7,
                    "炼胶#出库口#2": 8,
                    "炼胶#出库口#3": 9,
                    "帘布#出库口#0": 10
                }
                try:
                    label = receive_deal_result(lot_no)
                    if label:
                        LabelPrint.objects.create(label_type=station_dict.get(station), lot_no=lot_no, status=0,
                                                  data=label)
                except AttributeError as a:
                    logger.error(f"条码错误{a}")
                except Exception as e:
                    logger.error(f"未知错误{e}")

                if int(all_qty) >= need_qty:  # 若加上当前反馈后出库数量已达到订单需求数量则改为(1:完成)
                    dp_obj.status = 1
                    dp_obj.finish_time = datetime.datetime.now()
                    dp_obj.save()
                il_dict = {}
                il_dict['warehouse_no'] = dp_obj.warehouse_info.no
                il_dict['warehouse_name'] = dp_obj.warehouse_info.name
                il_dict['inout_reason'] = dp_obj.inventory_reason
                il_dict['unit'] = dp_obj.unit
                il_dict['initiator'] = dp_obj.created_user
                il_dict['material_no'] = dp_obj.material_no
                il_dict['start_time'] = dp_obj.created_date
                il_dict['order_type'] = dp_obj.order_type if dp_obj.order_type else "出库"
                material = Material.objects.filter(material_no=dp_obj.material_no).first()
                material_inventory_dict = {
                    "material": material,
                    "container_no": data.get("pallet_no"),
                    "site_id": 15,
                    "qty": data.get("qty"),
                    "unit": dp_obj.unit,
                    "unit_weight": float(data.get("weight")) / float(data.get("qty")),
                    "total_weight": data.get("weight"),
                    "quality_status": data.get("quality_status"),
                    "lot_no": data.get("lot_no"),
                    "location": "预留",
                    "warehouse_info": dp_obj.warehouse_info,
                }
            else:
                raise ValidationError("订单号不能为空")
            try:
                MaterialInventory.objects.create(**material_inventory_dict)
            except Exception as e:
                logger.error(str(e) + "data: " + json.dumps(material_inventory_dict))
            try:
                InventoryLog.objects.create(**data, **il_dict)
            except Exception as e:
                logger.error(e)
                result = {"99": "FALSE", f"message": f"反馈失败，原因: {e}"}
            else:
                result = {"01": "TRUES", "message": "反馈成功，OK"}
            return Response(result)
        return Response({"99": "FALSE", "message": "反馈失败，原因: 未收到具体的出库反馈信息，请检查请求体数据"})


@method_decorator([api_recorder], name="dispatch")
class OverdueMaterialManagement(ModelViewSet):
    queryset = MaterialInventory.objects.filter()
    serializer_class = OverdueMaterialManagementSerializer
    filter_backends = [DjangoFilterBackend]


@method_decorator([api_recorder], name="dispatch")
class MaterialInventoryManageViewSet(viewsets.ReadOnlyModelViewSet):
    """物料库存信息|线边库|终炼胶库|原材料库"""

    MODEL, SERIALIZER = 0, 1
    INVENTORY_MODEL_BY_NAME = {
        '线边库': [XBMaterialInventory, XBKMaterialInventorySerializer],
        '终炼胶库': [BzFinalMixingRubberInventoryLB, BzFinalMixingRubberLBInventorySerializer],
        '帘布库': [BzFinalMixingRubberInventoryLB, BzFinalMixingRubberLBInventorySerializer],
        '原材料库': [WmsInventoryStock, WmsInventoryStockSerializer],
        '混炼胶库': [BzFinalMixingRubberInventory, BzFinalMixingRubberInventorySerializer],
        '炭黑库': [WmsInventoryStock, WmsInventoryStockSerializer],
    }
    permission_classes = (permissions.IsAuthenticated,)

    # filter_backends = (DjangoFilterBackend,)

    def divide_tool(self, index):
        warehouse_name = self.request.query_params.get('warehouse_name', None)
        if warehouse_name and warehouse_name in self.INVENTORY_MODEL_BY_NAME:
            return self.INVENTORY_MODEL_BY_NAME[warehouse_name][index]
        else:
            raise ValidationError(f'该仓库请移步{warehouse_name}专项页面查看')

    def get_query_params(self):
        for query in ('material_type', 'container_no', 'material_no', "order_no", "location", 'tunnel', 'lot_no'):
            yield self.request.query_params.get(query, None)

    def get_queryset(self):
        warehouse_name = self.request.query_params.get('warehouse_name', None)
        quality_status = self.request.query_params.get('quality_status', None)
        # 终炼胶，帘布库区分 货位地址开头1-4终炼胶   5-6帘布库
        model = self.divide_tool(self.MODEL)
        queryset = None
        material_type, container_no, material_no, order_no, location, tunnel, lot_no = self.get_query_params()
        if model == XBMaterialInventory:
            queryset = model.objects.all()
        elif model == BzFinalMixingRubberInventory:
            # 出库计划弹框展示的库位数据需要更具库位状态进行筛选其他页面不需要
            # if self.request.query_params.get("location_status"):
            #     queryset = model.objects.using('bz').filter(location_status=self.request.query_params.get("location_status"))
            # else:
            queryset = model.objects.using('bz').all()
            if quality_status:
                queryset = queryset.filter(quality_level=quality_status)
        elif model == BzFinalMixingRubberInventoryLB:
            # 出库计划弹框展示的库位数据需要更具库位状态进行筛选其他页面不需要
            # if self.request.query_params.get("location_status"):
            #     queryset = model.objects.using('lb').filter(location_status=self.request.query_params.get("location_status"))
            # else:
            queryset = model.objects.using('lb').all()
            if warehouse_name == "帘布库":
                queryset = queryset.filter(store_name="帘布库")
                status_dict = {"合格品": "一等品", "不合格品": "三等品", "一等品": "一等品", "三等品": "三等品"}
                if quality_status:
                    queryset = queryset.filter(quality_level=status_dict.get(quality_status, "一等品"))
            else:
                queryset = queryset.filter(store_name="炼胶库")
                if quality_status:
                    queryset = queryset.filter(quality_level=quality_status)
        if queryset:
            if material_type and model not in [BzFinalMixingRubberInventory, XBMaterialInventory,
                                               BzFinalMixingRubberInventoryLB]:
                queryset = queryset.filter(material_type__icontains=material_type)
            if material_type and model == XBMaterialInventory:
                queryset = queryset.filter(material__material_type__global_name__icontains=material_type)
            if material_no:
                queryset = queryset.filter(material_no__icontains=material_no)
            if container_no:
                queryset = queryset.filter(container_no__icontains=container_no)
            if order_no and model in [BzFinalMixingRubberInventory, BzFinalMixingRubberInventoryLB]:
                queryset = queryset.filter(bill_id__icontains=order_no)
            if location:
                queryset = queryset.filter(location__icontains=location)
            if tunnel:
                queryset = queryset.filter(location__istartswith=tunnel)
            if lot_no:
                queryset = queryset.filter(lot_no__icontains=lot_no)
            return queryset
        if model == WmsInventoryStock:
            quality_status = {"合格品": 1, "不合格品": 2, None: 1, "": 1}[quality_status]
            if warehouse_name == "原材料库":
                queryset = model.objects.using('wms').raw(
                    WmsInventoryStock.get_sql(material_type, material_no, container_no, order_no, location, tunnel,
                                              quality_status, lot_no))
            else:
                queryset = model.objects.using('cb').raw(
                    WmsInventoryStock.get_sql(material_type, material_no, container_no, order_no, location, tunnel,
                                              quality_status, lot_no))
        return queryset

    def get_serializer_class(self):
        return self.divide_tool(self.SERIALIZER)


@method_decorator([api_recorder], name="dispatch")
class InventoryLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InventoryLog.objects.order_by('-start_time')
    serializer_class = InventoryLogSerializer
    permission_classes = (permissions.IsAuthenticated,)

    # filter_backends = (InventoryFilterBackend,)

    def get_queryset(self):
        filter_dict = {}
        store_name = self.request.query_params.get("store_name")
        if not store_name:
            store_name = "混炼胶库"
        order_type = self.request.query_params.get("order_type", "出库")
        start_time = self.request.query_params.get("start_time")
        end_time = self.request.query_params.get("end_time")
        location = self.request.query_params.get("location")
        material_no = self.request.query_params.get("material_no")
        order_no = self.request.query_params.get("order_no")
        lot_no = self.request.query_params.get("lot_no")
        pallet_no = self.request.query_params.get("pallet_no")
        if location:
            filter_dict.update(location__icontains=location)
        if material_no:
            filter_dict.update(material_no__icontains=material_no)
        if order_no:
            filter_dict.update(order_no__icontains=order_no)
        if lot_no:
            filter_dict.update(lot_no__icontains=lot_no)
        if pallet_no:
            filter_dict.update(pallet_no__icontains=pallet_no)
        if store_name == "混炼胶库":
            if start_time:
                filter_dict.update(start_time__gte=start_time)
            if end_time:
                filter_dict.update(start_time__lte=end_time)
            if order_type == "出库":
                if self.request.query_params.get("type") == "正常出库":
                    actual_type = "生产出库"
                    filter_dict.update(inout_num_type=actual_type)
                elif self.request.query_params.get("type") == "指定出库":
                    actual_type = "快检出库"
                    filter_dict.update(inout_num_type=actual_type)
                else:
                    actual_type = "生产出库"
                temp_set = list(MixGumOutInventoryLog.objects.using('bz').filter(**filter_dict).order_by('-start_time'))
                # 目前先只查北自出入库履历
                # filter_dict.pop("inout_num_type", None)
                # temp_set += list(InventoryLog.objects.filter(warehouse_name=store_name, inventory_type=actual_type,
                #                                              **filter_dict).order_by('-start_time'))
                return temp_set
            else:
                return MixGumInInventoryLog.objects.using('bz').filter(**filter_dict)
        elif store_name == "终炼胶库":
            if start_time:
                filter_dict.update(start_time__gte=start_time)
            if end_time:
                filter_dict.update(start_time__lte=end_time)
            if order_type == "出库":
                if self.request.query_params.get("type") == "正常出库":
                    actual_type = "生产出库"
                    filter_dict.update(inout_num_type=actual_type)
                elif self.request.query_params.get("type") == "指定出库":
                    actual_type = "快检出库"
                    filter_dict.update(inout_num_type=actual_type)
                else:
                    actual_type = "生产出库"
                temp_set = list(MixGumOutInventoryLog.objects.using('lb').filter(**filter_dict).filter(
                    material_no__icontains="M").order_by('-start_time'))
                # 目前先只查北自出入库履历
                # filter_dict.pop("inout_num_type", None)
                # temp_set += list(InventoryLog.objects.filter(warehouse_name=store_name, inventory_type=actual_type,
                #                                              **filter_dict).order_by('-start_time'))
                return temp_set
            else:
                return MixGumInInventoryLog.objects.using('lb').filter(**filter_dict).filter(material_no__icontains="M")
        elif store_name == "帘布库":
            if start_time:
                filter_dict.update(start_time__gte=start_time)
            if end_time:
                filter_dict.update(start_time__lte=end_time)
            if order_type == "出库":
                if self.request.query_params.get("type") == "正常出库":
                    actual_type = "生产出库"
                    filter_dict.update(inout_num_type=actual_type)
                elif self.request.query_params.get("type") == "指定出库":
                    actual_type = "快检出库"
                    filter_dict.update(inout_num_type=actual_type)
                else:
                    actual_type = "生产出库"
                temp_set = list(MixGumOutInventoryLog.objects.using('lb').filter(**filter_dict).exclude(
                    material_no__icontains="M").order_by('-start_time'))
                # 目前先只查北自出入库履历
                # filter_dict.pop("inout_num_type", None)
                # temp_set += list(InventoryLog.objects.filter(warehouse_name=store_name, inventory_type=actual_type,
                #                                              **filter_dict).order_by('-start_time'))
                return temp_set
            else:
                return MixGumInInventoryLog.objects.using('lb').filter(**filter_dict).exclude(
                    material_no__icontains="M")
        elif store_name == "原材料库":
            if start_time:
                filter_dict.update(task__start_time__gte=start_time)
            if end_time:
                filter_dict.update(task__start_time__lte=end_time)
            if order_type == "出库":
                return MaterialOutHistory.objects.using('wms').filter(**filter_dict)
            else:
                return MaterialInHistory.objects.using('wms').filter(**filter_dict)
        elif store_name == "炭黑库":
            if start_time:
                filter_dict.update(task__start_time__gte=start_time)
            if end_time:
                filter_dict.update(task__start_time__lte=end_time)
            if order_type == "出库":
                return MaterialOutHistory.objects.using('cb').filter(**filter_dict)
            else:
                return MaterialInHistory.objects.using('cb').filter(**filter_dict)

        else:
            return InventoryLog.objects.filter(**filter_dict).order_by('-start_time')

    def get_serializer_class(self):
        store_name = self.request.query_params.get("store_name", "混炼胶库")
        order_type = self.request.query_params.get("order_type", "出库")
        serializer_dispatch = {
            "混炼胶库": InventoryLogSerializer,
            "终炼胶库": InventoryLogSerializer,
            "原材料库": InOutCommonSerializer,
            "炭黑库": InOutCommonSerializer,
        }
        return serializer_dispatch.get(store_name, InventoryLogSerializer)


@method_decorator([api_recorder], name="dispatch")
class MaterialCount(APIView):

    def get(self, request):
        params = request.query_params
        store_name = params.get('store_name')
        status = params.get("status")
        if not store_name:
            raise ValidationError("缺少立库名参数，请检查后重试")
        filter_dict = dict(location_status="有货货位")
        if status:
            filter_dict.update(quality_level=status)
        if store_name == "终炼胶库":
            try:
                ret = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(**filter_dict).filter(
                    store_name="炼胶库").values(
                    'material_no').annotate(
                    all_qty=Sum('qty'), all_weight=Sum('total_weight')).values('material_no', 'all_qty', 'all_weight')
            except Exception as e:
                raise ValidationError(f"终炼胶库连接失败: {e}")
        elif store_name == "混炼胶库":
            try:
                ret = BzFinalMixingRubberInventory.objects.using('bz').filter(**filter_dict).values(
                    'material_no').annotate(
                    all_qty=Sum('qty'), all_weight=Sum('total_weight')).values('material_no', 'all_qty', 'all_weight')
            except Exception as e:
                raise ValidationError(f"混炼胶库连接失败:{e}")
        elif store_name == "帘布库":
            try:
                filter_dict.pop("quality_level", None)
                if status:
                    filter_dict["quality_status"] = status
                ret = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(**filter_dict).filter(
                    store_name="帘布库").values(
                    'material_no', 'material_name').annotate(
                    all_qty=Sum('qty'), all_weight=Sum('total_weight')).values('material_no', 'all_qty',
                                                                               'material_name', 'all_weight')
            except:
                raise ValidationError("帘布库连接失败")
        elif store_name == "原材料库":
            status_map = {"合格": 1, "不合格": 2}
            try:
                ret = WmsInventoryStock.objects.using('wms').filter(quality_status=status_map.get(status, 1)).values(
                    'material_no', 'material_name').annotate(
                    all_weight=Sum('total_weight')).values('material_no', 'material_name', 'all_weight')
            except:
                raise ValidationError("原材料库连接失败")
        elif store_name == "炭黑库":
            status_map = {"合格": 1, "不合格": 2}
            try:
                ret = WmsInventoryStock.objects.using('cb').filter(quality_status=status_map.get(status, 1)).values(
                    'material_no', 'material_name').annotate(
                    all_weight=Sum('total_weight')).values('material_no', 'material_name', 'all_weight')
            except:
                raise ValidationError("原材料库连接失败")
        else:
            ret = []
        return Response(ret)


class ReversalUseFlagMixin:

    @action(detail=True, methods=['put'])
    def reversal_use_flag(self, request, pk=None):
        obj = self.get_object()
        obj.use_flag = not obj.use_flag
        obj.save()
        serializer = self.serializer_class(obj)
        return Response(serializer.data)


class AllMixin:

    def list(self, request, *args, **kwargs):
        if 'all' in self.request.query_params:
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        return super().list(request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class WarehouseInfoViewSet(ReversalUseFlagMixin, AllMixin, viewsets.ModelViewSet):
    queryset = WarehouseInfo.objects.all()
    serializer_class = WarehouseInfoSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ['name']

    @action(detail=False)
    def warehouse_names(self, request):
        names = WarehouseInfo.objects.values_list('name', flat=True).distinct()
        return Response(names)


@method_decorator([api_recorder], name="dispatch")
class StationInfoViewSet(ReversalUseFlagMixin, AllMixin, viewsets.ModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = StationFilter


@method_decorator([api_recorder], name="dispatch")
class WarehouseMaterialTypeViewSet(ReversalUseFlagMixin, viewsets.ModelViewSet):
    queryset = WarehouseMaterialType.objects.all()
    serializer_class = WarehouseMaterialTypeSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ['warehouse_info']


@method_decorator([api_recorder], name="dispatch")
class DispatchPlanViewSet(ModelViewSet):
    """
    list:
        发货计划列表
    create:
        新建发货计划
    retrieve:
        发货计划详情
    update:
        修改发货计划
    destroy:
        关闭发货计划
    """
    queryset = DispatchPlan.objects.filter(delete_flag=False).order_by('-created_date')
    serializer_class = DispatchPlanSerializer
    filter_backends = [DjangoFilterBackend]
    filter_class = DispatchPlanFilter
    permission_classes = (IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        data = request.data
        data['dispatch_user'] = request.user.username
        data['order_no'] = 'FH' + datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(
            random.randint(1, 99))
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status in [2, 4]:
            instance.status = 5
            instance.last_updated_user = request.user
            instance.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationError('只有执行中和新建才可以关闭！')


@method_decorator([api_recorder], name="dispatch")
class DispatchLocationViewSet(ModelViewSet):
    """目的地"""
    queryset = DispatchLocation.objects.filter(delete_flag=False)
    serializer_class = DispatchLocationSerializer
    filter_backends = [DjangoFilterBackend]
    filter_class = DispatchLocationFilter
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'name', 'use_flag')
            return Response({'results': data})
        return super().list(self, request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.use_flag:
            instance.use_flag = False
        else:
            instance.use_flag = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name="dispatch")
class DispatchLogView(ListAPIView):
    """
    list:
        发货履历列表
    create:
        新建/撤销发货
    """
    queryset = DispatchLog.objects.filter(delete_flag=False)
    serializer_class = DispatchLogSerializer
    filter_backends = [DjangoFilterBackend]
    filter_class = DispatchLogFilter
    permission_classes = (IsAuthenticated,)


@method_decorator([api_recorder], name="dispatch")
class InventoryLogOutViewSet(ModelViewSet):
    """混炼胶库出库履历视图"""
    queryset = InventoryLog.objects.filter(order_type='出库').order_by('-fin_time')
    serializer_class = InventoryLogOutSerializer
    filter_backends = [DjangoFilterBackend]
    pagination_class = SinglePageNumberPagination
    # filter_class = MixGumOutInventoryLogFilter
    permission_classes = (IsAuthenticated,)

    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated], url_path='inventory-now',
            url_name='inventory-now')
    def inventory_now(self, request, pk=None):
        """当前出库信息"""
        mixing_finished = self.request.query_params.get('mixing_finished', None)
        if mixing_finished:
            if mixing_finished == "终炼":
                il_obj = InventoryLog.objects.filter(order_type='出库', material_no__icontains="FM").last()
            elif mixing_finished == "混炼":
                il_obj = InventoryLog.objects.exclude(material_no__icontains="FM").filter(order_type='出库').last()
        else:
            raise ValidationError('参数不全')
        if il_obj:
            result = {'order_no': il_obj.order_no, 'material_no': il_obj.material_no,
                      'lot_no': il_obj.lot_no, 'location': il_obj.location}
        else:
            result = None
        return Response({'results': result})

    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated], url_path='inventory-today',
            url_name='inventory-today')
    def inventory_today(self, request, pk=None):
        """今日出库量"""
        mixing_finished = self.request.query_params.get('mixing_finished', None)
        if mixing_finished:
            if mixing_finished == "终炼":
                il_set = InventoryLog.objects.filter(order_type='出库', fin_time__date=datetime.date.today(),
                                                     material_no__icontains="FM").values(
                    'material_no').annotate(sum_qty=Sum('qty'))
            elif mixing_finished == "混炼":
                il_set = InventoryLog.objects.exclude(material_no__icontains="FM").filter(order_type='出库',
                                                                                          fin_time__date=datetime.date.today()).values(
                    'material_no').annotate(sum_qty=Sum('qty'))
        else:
            raise ValidationError('参数不全')
        return Response({'results': il_set})

    def get_queryset(self):
        queryset = super(InventoryLogOutViewSet, self).get_queryset()
        mixing_finished = self.request.query_params.get('mixing_finished', None)
        if mixing_finished:
            if mixing_finished == "终炼":
                queryset = queryset.filter(material_no__icontains="FM").all()
            elif mixing_finished == "混炼":
                queryset = queryset.exclude(material_no__icontains="FM").all()
        else:
            raise ValidationError('参数不全')
        return queryset


@method_decorator([api_recorder], name="dispatch")
class MaterialInventoryAPIView(APIView):

    def get(self, request):
        """库存信息"""
        lot_no = self.request.query_params.get('lot_no', None)
        if not lot_no:
            raise ValidationError('lot_no参数必填')
        model_list = [XBMaterialInventory, BzFinalMixingRubberInventory, BzFinalMixingRubberInventoryLB,
                      WmsInventoryStock]
        # 线边库  炼胶库  帘布库  原材料库
        query_list = []
        for model in model_list:
            if model == XBMaterialInventory:
                queryset = model.objects.filter(lot_no=lot_no).values('material__material_type',
                                                                      'material__material_no',
                                                                      'lot_no', 'container_no', 'location', 'qty',
                                                                      'unit',
                                                                      'unit_weight', 'quality_status')
                for xbi_obj in queryset:
                    xbi_obj.update({'material_type': xbi_obj.pop("material__material_type")})
                    xbi_obj.update({'material_no': xbi_obj.pop("material__material_no")})
            elif model == BzFinalMixingRubberInventory:
                try:
                    queryset = model.objects.using('bz').filter(lot_no=lot_no).values(
                        'material_no',
                        'lot_no', 'container_no', 'location',
                        'qty',
                        'quality_status', 'total_weight')
                except:
                    raise ValidationError('bz混炼胶库连接失败')
                for bz_dict in queryset:
                    try:
                        mt = bz_dict['material_no'].split("-")[1]
                    except:
                        mt = bz_dict['material_no']
                    unit = 'kg'
                    unit_weight = str(round(bz_dict['total_weight'] / bz_dict['qty'], 3))
                    bz_dict['material_type'] = mt
                    bz_dict['unit'] = unit
                    bz_dict['unit_weight'] = unit_weight
            elif model == BzFinalMixingRubberInventoryLB:
                try:
                    queryset = model.objects.using('lb').filter(lot_no=lot_no).values('material_no',
                                                                                      'lot_no', 'container_no',
                                                                                      'location',
                                                                                      'qty',
                                                                                      'quality_status', 'total_weight')
                except:
                    raise ValidationError('bz帘布连接失败')
                for bz_dict in queryset:
                    try:
                        mt = bz_dict['material_no'].split("-")[1]
                    except:
                        mt = bz_dict['material_no']
                    unit = 'kg'
                    unit_weight = str(round(bz_dict['total_weight'] / bz_dict['qty'], 3))
                    bz_dict['material_type'] = mt
                    bz_dict['unit'] = unit
                    bz_dict['unit_weight'] = unit_weight

            elif model == WmsInventoryStock:
                try:
                    queryset = model.objects.using('wms').filter(lot_no=lot_no).values(
                        'material_no',
                        'lot_no', 'location',
                        'qty',
                        'unit',
                        'quality_status', )
                except:
                    raise ValidationError('wms原材料库连接失败')
                for bz_dict in queryset:
                    try:
                        mt = bz_dict['material_no'].split("-")[1]
                    except:
                        mt = bz_dict['material_no']
                    container_no = None
                    unit_weight = None
                    bz_dict['material_type'] = mt  # 表里是有的 但是加上这个字段就会报错
                    bz_dict['container_no'] = container_no
                    bz_dict['unit_weight'] = unit_weight
            if queryset:
                query_list.extend(queryset)

        # 分页
        page = self.request.query_params.get("page", 1)
        page_size = self.request.query_params.get("page_size", 10)
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
        count = len(query_list)
        result = query_list[st:et]
        return Response({'results': result, "count": count})


@method_decorator([api_recorder], name="dispatch")
class PutPlanManagement(ModelViewSet):
    queryset = DeliveryPlan.objects.filter().order_by("-created_date")
    serializer_class = PutPlanManagementSerializer
    filter_backends = [DjangoFilterBackend]
    filter_class = PutPlanManagementFilter

    def create(self, request, *args, **kwargs):
        data = request.data
        if isinstance(data, list):
            s = PutPlanManagementSerializer(data=data, context={'request': request}, many=True)
            if not s.is_valid():
                raise ValidationError(s.errors)
            s.save()
        elif isinstance(data, dict):
            s = PutPlanManagementSerializer(data=data, context={'request': request})
            if not s.is_valid():
                raise ValidationError(s.errors)
            s.save()
        else:
            raise ValidationError('参数错误')
        return Response('新建成功')


@method_decorator([api_recorder], name="dispatch")
class PutPlanManagementLB(ModelViewSet):
    queryset = DeliveryPlanLB.objects.filter().order_by("-created_date")
    serializer_class = PutPlanManagementSerializerLB
    filter_backends = [DjangoFilterBackend]
    filter_class = PutPlanManagementLBFilter
    permission_classes = (IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        data = request.data
        if isinstance(data, list):
            s = PutPlanManagementSerializerLB(data=data, context={'request': request}, many=True)
            if not s.is_valid():
                raise ValidationError(s.errors)
            s.save()
        elif isinstance(data, dict):
            s = PutPlanManagementSerializerLB(data=data, context={'request': request})
            if not s.is_valid():
                raise ValidationError(s.errors)
            s.save()
        else:
            raise ValidationError('参数错误')
        return Response('新建成功')


@method_decorator([api_recorder], name="dispatch")
class PutPlanManagementFianl(ModelViewSet):
    queryset = DeliveryPlanFinal.objects.filter().order_by("-created_date")
    serializer_class = PutPlanManagementSerializerFinal
    filter_backends = [DjangoFilterBackend]
    filter_class = PutPlanManagementFinalFilter
    permission_classes = (IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        data = request.data
        if isinstance(data, list):
            s = PutPlanManagementSerializerFinal(data=data, context={'request': request}, many=True)
            if not s.is_valid():
                raise ValidationError(s.errors)
            s.save()
        elif isinstance(data, dict):
            s = PutPlanManagementSerializerFinal(data=data, context={'request': request})
            if not s.is_valid():
                raise ValidationError(s.errors)
            s.save()
        else:
            raise ValidationError('参数错误')
        return Response('新建成功')


@method_decorator([api_recorder], name="dispatch")
class MaterialPlanManagement(ModelViewSet):
    queryset = MaterialOutPlan.objects.filter().order_by("-created_date")
    serializer_class = MaterialPlanManagementSerializer
    filter_backends = [DjangoFilterBackend]
    filter_class = MaterialPlanManagementFilter
    permission_classes = (IsAuthenticated,)

    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated], url_path='stations',
            url_name='stations')
    def get(self, request, *args, **kwargs):
        url = f"http://{cb_ip}:{cb_port}/entrance/GetOutEntranceInfo"
        ret = requests.get(url)
        data = ret.json()
        rep = [{"station_no": x.get("entranceCode"),
                "station": x.get("name")} for x in data.get("datas", {})]
        return Response(rep)

    def create(self, request, *args, **kwargs):
        data = request.data
        if isinstance(data, list):
            s = MaterialPlanManagementSerializer(data=data, context={'request': request}, many=True)
            if not s.is_valid():
                raise ValidationError(s.errors)
            s.save()
        elif isinstance(data, dict):
            s = MaterialPlanManagementSerializer(data=data, context={'request': request})
            if not s.is_valid():
                raise ValidationError(s.errors)
            s.save()
        else:
            raise ValidationError('参数错误')
        return Response('新建成功')


@method_decorator([api_recorder], name="dispatch")
class CarbonPlanManagement(ModelViewSet):
    queryset = CarbonOutPlan.objects.filter().order_by("-created_date")
    serializer_class = CarbonPlanManagementSerializer
    filter_backends = [DjangoFilterBackend]
    filter_class = CarbonPlanManagementFilter
    permission_classes = (IsAuthenticated,)

    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated], url_path='stations',
            url_name='stations')
    def get(self, request, *args, **kwargs):
        url = f"http://{wms_ip}:{wms_port}/entrance/GetOutEntranceInfo"
        ret = requests.get(url)
        data = ret.json()
        rep = [{"station_no": x.get("entranceCode"),
                "station": x.get("name")} for x in data.get("datas", {})]
        return Response(rep)

    def create(self, request, *args, **kwargs):
        data = request.data
        if isinstance(data, list):
            s = CarbonPlanManagementSerializer(data=data, context={'request': request}, many=True)
            if not s.is_valid():
                raise ValidationError(s.errors)
            s.save()
        elif isinstance(data, dict):
            s = CarbonPlanManagementSerializer(data=data, context={'request': request})
            if not s.is_valid():
                raise ValidationError(s.errors)
            s.save()
        else:
            raise ValidationError('参数错误')
        return Response('新建成功')


@method_decorator([api_recorder], name="dispatch")
class MateriaTypeNameToAccording(APIView):
    # materia_type_name_to_according
    """根据物料类型和编码找到存在的仓库表"""

    def get(self, request):
        material_type = self.request.query_params.get('material_type')
        material_no = self.request.query_params.get('material_no')
        if not all([material_no, material_type]):
            raise ValidationError('物料名称和物料类型都必传！')
        warehouse_name_list = WarehouseMaterialType.objects.filter(
            material_type__global_name=material_type).values_list(
            'warehouse_info__name', flat=True).distinct()
        if not warehouse_name_list:
            raise ValidationError('该物料类型没有对应的仓库')
        warehouse_name_according = {'线边库': MaterialInventory,
                                    '原材料库': WmsInventoryStock,
                                    '混炼胶库': BzFinalMixingRubberInventory,
                                    '帘布库': BzFinalMixingRubberInventoryLB,
                                    '终炼胶库': BzFinalMixingRubberInventory}
        according_list = []
        for warehouse_name in warehouse_name_list:
            materia_no_filte = {}
            if warehouse_name_according[warehouse_name] == MaterialInventory:
                materia_no_filte['material__material_no'] = material_no
            else:
                materia_no_filte['material_no'] = material_no
            if warehouse_name_according[warehouse_name].objects.filter(**materia_no_filte).exists():
                according_list.append(warehouse_name_according[warehouse_name].__name__)
        return Response(according_list)


@method_decorator([api_recorder], name="dispatch")
class SamplingRules(APIView):

    def get(self, request, *args, **kwargs):
        params = request.query_params
        material_no = params.get("material_no")
        material_name = params.get("material_name")
        filter_dict = {}
        if material_no:
            filter_dict.update(material__material_no=material_no)
        if material_name:
            filter_dict.update(material__material_name=material_name)
        queryset = MaterialAttribute.objects.filter(**filter_dict).order_by("id")
        if not queryset.exists():
            raise ValidationError(f"{material_no}|{material_name}未能在MES中检索到")
        instance = queryset.last()
        return Response({"result": {"material_no": material_no,
                                    "material_name": material_name,
                                    "sampling_rate": instance.sampling_rate}})


@method_decorator([api_recorder], name="dispatch")
class BarcodeQualityViewSet(ModelViewSet):
    queryset = BarcodeQuality.objects.filter()
    serializer_class = BarcodeQualitySerializer
    filter_backends = [DjangoFilterBackend]
    filter_class = (BarcodeQualityFilter)
    permission_classes = (IsAuthenticated,)
    pagination_class = SinglePageNumberPagination

    def list(self, request, *args, **kwargs):
        params = request.query_params
        material_type = params.get("material_type")
        material_no = params.get("material_no")
        lot_no = params.get("lot_no")
        page = params.get("page", 1)
        page_size = params.get("page_size", 10)
        mes_set = self.queryset.values('lot_no', 'quality_status')
        quality_dict = {_.get("lot_no"): _.get('quality_status') for _ in mes_set}
        try:
            wms_set = WmsInventoryStock.objects.using('wms').raw(
                WmsInventoryStock.quality_sql(material_type, material_no, lot_no))
            p = Paginator(wms_set, page_size)
            s = WmsStockSerializer(p.page(page), many=True, context={"quality_dict": quality_dict})
            data = s.data
            return Response({"results": data, "count": p.count})
        except AttributeError:
            raise ValidationError("网络拥堵，数据还未返回")
        except TypeError:
            raise ValidationError("网络拥堵，数据还未返回")

    def create(self, request, *args, **kwargs):
        data = dict(request.data)
        lot_no = data.pop("lot_no", None)
        obj, flag = self.queryset.update_or_create(defaults=data, lot_no=lot_no)
        if flag:
            return Response("补充条码状态成功")
        else:
            return Response("更新条码状态成功")

    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated], url_path='export',
            url_name='export')
    def export(self, request):
        """备品备件导入模板"""
        response = HttpResponse(content_type='application/vnd.ms-excel')
        filename = '物料条码信息数据导出'
        response['Content-Disposition'] = 'attachment;filename= ' + filename.encode('gbk').decode(
            'ISO-8859-1') + '.xls'
        # 创建工作簿
        style = xlwt.XFStyle()
        style.alignment.wrap = 1
        ws = xlwt.Workbook(encoding='utf-8')

        # 添加第一页数据表
        w = ws.add_sheet('物料条码信息')  # 新建sheet（sheet的名称为"sheet1"）
        # for j in [1, 4, 5, 7]:
        #     first_col = w.col(j)
        #     first_col.width = 256 * 20
        # 写入表头
        w.write(0, 0, u'该数据仅供参考')
        title_list = [u'No', u'物料类型', u'物料编码', u'物料名称', u'条码', u'托盘号', u'库存数', u'单位重量(kg)', u'总重量', u'品质状态']
        for title in title_list:
            w.write(1, title_list.index(title), title)
        temp_write_list = []
        count = 1
        mes_set = self.queryset.values('lot_no', 'quality_status')
        quality_dict = {_.get("lot_no"): _.get('quality_status') for _ in mes_set}
        try:
            wms_set = WmsInventoryStock.objects.using('wms').raw(WmsInventoryStock.quality_sql())
        except:
            raise ValidationError("网络拥堵，请稍后重试")
        s = WmsStockSerializer(wms_set, many=True, context={"quality_dict": quality_dict})
        for q in s.data:
            total_weight = q.get('total_weight')
            qty = q.get('qty')
            if total_weight and qty:
                unit_weight = float(total_weight) / float(qty)
            else:
                unit_weight = 0
            line_list = [count, q.get('material_type'), q.get('material_no'), q.get('material_name'),
                         q.get('lot_no'), q.get('container_no'), qty, round(unit_weight, 3),
                         total_weight, q.get('quality') if q.get('quality') else None]
            temp_write_list.append(line_list)
            count += 1
        n = 2  # 行数
        for y in temp_write_list:
            m = 0  # 列数
            for x in y:
                w.write(n, m, x)
                m += 1
            n += 1
        output = BytesIO()
        ws.save(output)
        # 重新定位到开始
        output.seek(0)
        response.write(output.getvalue())
        return response


@method_decorator([api_recorder], name="dispatch")
class MaterialTraceView(APIView):

    def get(self, request):
        lot_no = request.query_params.get("lot_no")
        if not lot_no:
            raise ValidationError("请输入条码进行查询")
        rep = {}
        # 采样
        rep["material_sample"] = None
        # 入库
        material_in = MaterialInHistory.objects.using('wms').filter(lot_no=lot_no). \
            values("lot_no", "material_no", "material_name", "location", "pallet_no",
                   "task__initiator", "supplier", "batch_no", "task__fin_time").last()
        if material_in:
            temp_time = material_in.pop("task__fin_time", datetime.datetime.now())
            work_schedule_plan = WorkSchedulePlan.objects.filter(
                start_time__lte=temp_time,
                end_time__gte=temp_time,
                plan_schedule__work_schedule__work_procedure__global_name='密炼').select_related(
                "classes",
                "plan_schedule"
            ).order_by("id").last()
            if work_schedule_plan:
                current_class = work_schedule_plan.classes.global_name
                material_in["classes_name"] = current_class
            else:
                material_in["classes_name"] = "早班"
            material_in["time"] = temp_time.strftime('%Y-%m-%d %H:%M:%S')
            rep["material_in"] = [material_in]
        else:
            rep["material_in"] = []
        # 出库
        material_out = MaterialOutHistory.objects.using('wms').filter(lot_no=lot_no). \
            values("lot_no", "material_no", "material_name", "location", "pallet_no",
                   "task__initiator", "supplier", "batch_no", "task__fin_time").last()
        if material_out:
            temp_time = material_out.pop("task__fin_time", datetime.datetime.now())
            work_schedule_plan = WorkSchedulePlan.objects.filter(
                start_time__lte=temp_time,
                end_time__gte=temp_time,
                plan_schedule__work_schedule__work_procedure__global_name='密炼').select_related(
                "classes",
                "plan_schedule"
            ).order_by("id").last()
            if work_schedule_plan:
                current_class = work_schedule_plan.classes.global_name
                material_in["classes_name"] = current_class
            else:
                material_in["classes_name"] = "早班"
            rep["material_out"] = [material_out]
        else:
            rep["material_out"] = []
        # 称量投入
        weight_log = WeightBatchingLog.objects.filter(bra_code=lot_no). \
            values("bra_code", "material_no", "equip_no", "tank_no", "created_user__username", "created_date",
                   "batch_classes").last()
        if weight_log:
            temp_time = weight_log.pop("created_date", datetime.datetime.now())
            weight_log["time"] = temp_time.strftime('%Y-%m-%d %H:%M:%S')
            weight_log["classes_name"] = weight_log.pop("batch_classes", "早班")
        else:
            weight_log = {}
        rep["material_weight"] = [weight_log]
        # 密炼投入
        load_material = LoadMaterialLog.objects.using("SFJ").filter(bra_code=lot_no) \
            .values("material_no", "bra_code", "weight_time", "feed_log__equip_no",
                    "feed_log__batch_group", "feed_log__batch_classes").last()
        if load_material:
            temp_time = load_material.pop("weight_time", datetime.datetime.now())
            load_material["time"] = temp_time.strftime('%Y-%m-%d %H:%M:%S')
            load_material["classes_name"] = load_material.pop("feed_log__batch_classes", "早班")
            rep["material_load"] = [load_material]
        else:
            rep["material_load"] = []
        return Response(rep)


@method_decorator([api_recorder], name="dispatch")
class ProductTraceView(APIView):
    inventory = {
        "终炼胶库": ('lb', []),
        "混炼胶库": ("bz", []),
    }

    def get(self, request):
        #  11个条目
        lot_no = request.query_params.get("lot_no")
        if not lot_no:
            raise ValidationError("请输入条码进行查询")
        rep = {"material_in": [], "material_out": []}
        product_trace = PalletFeedbacks.objects.filter(lot_no=lot_no).values()
        if not product_trace:
            raise ValidationError("无法查询到该追踪码对应的胶料数据")
        pallet_feed = product_trace.last()
        plan_no = pallet_feed.get("plan_classes_uid")
        product_no = pallet_feed.get("product_no")
        begin_trains = pallet_feed.get("begin_trains")
        end_trains = pallet_feed.get("end_trains")
        trains_list = [x for x in range(begin_trains, end_trains + 1)]
        lml_set = LoadMaterialLog.objects.using("SFJ").filter(feed_log__trains__in=trains_list,
                                                              feed_log__plan_classes_uid=plan_no).distinct()
        bra_code_list = list(lml_set.values_list("bra_code", flat=True))
        # 密炼投入
        material_load = lml_set.values("bra_code", "material_no", "feed_log__equip_no", "weight_time",
                                       "feed_log__batch_group", "feed_log__batch_classes")
        rep["material_load"] = list(material_load)
        # 料包产出
        weight_package = WeightPackageLog.objects.filter(bra_code__in=bra_code_list). \
            values("bra_code", "material_no", "equip_no", "batch_group", "created_date", "batch_classes")
        rep["weight_package"] = list(weight_package)
        # 称量投入
        weight_load = WeightBatchingLog.objects.filter(bra_code__in=bra_code_list). \
            values("bra_code", "material_no", "equip_no", "tank_no", "batch_group", "created_date", "batch_classes")
        rep["weight_load"] = list(weight_load)
        if "FM" in product_no:
            db_rubber = "bz"
        else:
            # db = "lb
            db_rubber = "bz"
        # 收皮产出追溯
        rep["pallet_feed"] = list(product_trace)
        if not product_trace:
            raise ValidationError("查不到该条码对应胶料")
        plan = ProductClassesPlan.objects.filter(plan_classes_uid=plan_no).last()
        if plan:
            product = plan.product_batching

            # 配方创建
            product_info = model_to_dict(product)
            temp_time = product_info.get("created_date", datetime.datetime.now())
            work_schedule_plan = WorkSchedulePlan.objects.filter(
                start_time__lte=temp_time,
                end_time__gte=temp_time,
                plan_schedule__work_schedule__work_procedure__global_name='密炼').select_related(
                "classes",
                "plan_schedule"
            ).order_by("id").last()
            if work_schedule_plan:
                current_class = work_schedule_plan.classes.global_name
                product_info["classes_name"] = current_class
            else:
                product_info["classes_name"] = "早班"
            product_info["created_date"] = temp_time
        else:
            product = None
            product_info = {}
        rep["product_info"] = [product_info]
        # 配料详情
        if product:
            product_details = product.batching_details.all().values("product_batching__stage_product_batch_no",
                                                                    "material__material_no", "actual_weight")
        else:
            product_details = []
        rep["product_details"] = list(product_details)
        # 胶料计划
        plan_info = ProductClassesPlan.objects.filter(plan_classes_uid=plan_no).values("plan_classes_uid",
                                                                                       "equip__equip_no",
                                                                                       "product_batching__stage_product_batch_no",
                                                                                       "plan_trains", "created_date",
                                                                                       "last_updated_date",
                                                                                       "work_schedule_plan__classes__global_name")
        trains_temp =  TrainsFeedbacks.objects.filter(plan_classes_uid=plan_no).order_by('id')
        start_time = trains_temp.first().begin_time if trains_temp.first() else None
        end_time = trains_temp.first().end_time if trains_temp.last() else None
        plan_info = plan_info.last()
        if plan_info:
            plan_info.update(start_time=start_time, end_time=end_time)
        rep["plan_info"] = [plan_info]
        # 小料计划
        batch_plan = BatchingClassesPlan.objects.filter(weigh_cnt_type__product_batching=product,
                                                        work_schedule_plan=plan.work_schedule_plan). \
            values("plan_batching_uid", "weigh_cnt_type__product_batching__equip__equip_no",
                   "created_date", "last_updated_date", "work_schedule_plan__classes__global_name")
        rep["batch_plan"] = list(batch_plan)
        # 收皮入库
        product_in = MixGumInInventoryLog.objects.using(db_rubber).filter(lot_no=lot_no).values()
        temp = product_in.last()
        if temp:
            temp_time = product_info.get("start_time", datetime.datetime.now())
            work_schedule_plan = WorkSchedulePlan.objects.filter(
                start_time__lte=temp_time,
                end_time__gte=temp_time,
                plan_schedule__work_schedule__work_procedure__global_name='密炼').select_related(
                "classes",
                "plan_schedule"
            ).order_by("id").last()
            if work_schedule_plan:
                current_class = work_schedule_plan.classes.global_name
                temp["classes_name"] = current_class
            else:
                temp["classes_name"] = "早班"
            rep["product_in"] = [temp]
        else:
            rep["product_in"] = []
        # 胶片发货
        dispatch_log = DispatchLog.objects.filter(lot_no=lot_no).values()
        temp = dispatch_log.last()
        if temp:
            temp_time = product_info.get("order_created_time", datetime.datetime.now())
            work_schedule_plan = WorkSchedulePlan.objects.filter(
                start_time__lte=temp_time,
                end_time__gte=temp_time,
                plan_schedule__work_schedule__work_procedure__global_name='密炼').select_related(
                "classes",
                "plan_schedule"
            ).order_by("id").last()
            if work_schedule_plan:
                current_class = work_schedule_plan.classes.global_name
                temp["classes_name"] = current_class
            else:
                temp["classes_name"] = "早班"
            rep["dispatch_log"] = [temp]
        else:
            rep["dispatch_log"] = []
        return Response(rep)


@method_decorator([api_recorder], name="dispatch")
class MaterialOutBack(APIView):

    # 出库反馈
    @atomic
    def post(self, request):
        """WMS->MES:任务编号、物料信息ID、物料名称、PDM号（促进剂以外为空）、批号、条码、重量、重量单位、
        生产日期、使用期限、托盘RFID、工位（出库口）、MES->WMS:信息接收成功or失败"""
        # 任务编号

        data = request.data
        # data = {'order_no':'20201114131845',"pallet_no":'20102494',
        #         'location':'二层前端','qty':'2','weight':'2.00',
        #         'quality_status':'合格','lot_no':'122222',
        #         'inout_num_type':'123456','fin_time':'2020-11-10 15:02:41'
        #         }
        data = dict(data)
        data.pop("status", None)
        order_no = data.get('order_no')
        if order_no:
            temp = MaterialInventoryLog.objects.filter(order_no=order_no).aggregate(all_weight=Sum('weight'))
            all_weight = temp.get("all_qty")
            if all_weight:
                all_weight += float(data.get("qty"))
            else:
                all_weight = float(data.get("qty"))
            order = MaterialOutPlan.objects.filter(order_no=order_no).first()
            if order:
                need_weight = order.need_weight
            else:
                return Response({"status": 0, "desc": "失败", "message": "该订单非mes下发订单"})
            if int(all_weight) >= need_weight:  # 若加上当前反馈后出库数量已达到订单需求数量则改为(1:完成)
                order.status = 1
                order.finish_time = datetime.datetime.now()
                order.save()
            temp_data = {}
            temp_data['warehouse_no'] = order.warehouse_info.no
            temp_data['warehouse_name'] = order.warehouse_info.name
            temp_data['inout_reason'] = order.inventory_reason
            temp_data['unit'] = order.unit
            temp_data['initiator'] = order.created_user
            temp_data['material_no'] = order.material_no
            temp_data['start_time'] = order.created_date
            temp_data['order_type'] = order.order_type if order.order_type else "出库"
            temp_data['station'] = order.station
            equip_list = list(set(order.equip.all().values_list("equip_no", flat=True)))
            temp_data["dst_location"] = ",".join(equip_list)
            material = Material.objects.filter(material_no=order.material_no).first()
            material_inventory_dict = {
                "material": material,
                "container_no": data.get("pallet_no"),
                "site_id": 15,
                "qty": data.get("qty"),
                "unit": order.unit,
                "unit_weight": float(data.get("weight")) / float(data.get("qty")),
                "total_weight": data.get("weight"),
                "quality_status": data.get("quality_status"),
                "lot_no": data.get("lot_no"),
                "location": "预留",
                "warehouse_info": order.warehouse_info,
            }
        else:
            raise ValidationError("订单号不能为空")
        MaterialInventory.objects.create(**material_inventory_dict)
        try:
            MaterialInventoryLog.objects.create(**data, **temp_data)
        except Exception as e:
            logger.error(e)
            result = {"status": 0, "desc": "失败", "message": f"反馈异常{e}"}
        else:
            result = {"status": 1, "desc": "成功", "message": "反馈成功"}
            if data.get("inventory_type"):  # 若加上当前反馈后出库数量已达到订单需求数量则改为(1:完成)
                order.status = 1
                order.finish_time = datetime.datetime.now()
                order.save()
        return Response(result)


# 出库大屏
# 分为混炼胶和终炼胶出库大屏
# 混炼胶出库大屏一共份三个接口
@method_decorator([api_recorder], name="dispatch")
class DeliveryPlanNow(APIView):
    """混炼胶 当前在出库口的胶料信息"""

    def get(self, request):
        dp_last_obj = DeliveryPlan.objects.filter(status=2).all().last()
        if dp_last_obj:
            try:
                location_name = dp_last_obj.dispatch.all().filter(
                    order_no=dp_last_obj.order_no).last().dispatch_location.name
            except:
                location_name = None
            try:
                if IS_BZ_USING:
                    mix_gum_out_obj = MixGumOutInventoryLog.objects.using('bz').filter(
                        order_no=dp_last_obj.order_no).last()
                else:
                    mix_gum_out_obj = MixGumOutInventoryLog.objects.filter(order_no=dp_last_obj.order_no).last()
            except Exception as e:
                raise ValidationError(f'连接北自数据库超时: {e}')
            if mix_gum_out_obj:
                lot_no = mix_gum_out_obj.lot_no
            else:
                lot_no = None
            result = {'order_no': dp_last_obj.order_no,
                      'material_no': dp_last_obj.material_no,
                      'location_name': location_name,
                      'lot_no': lot_no}

        else:
            result = None
        return Response({"result": result})


@method_decorator([api_recorder], name="dispatch")
class DeliveryPlanToday(APIView):
    """混炼胶  今日的总出库量"""

    def get(self, request):
        # 计划数量
        delivery_plan_qty = DeliveryPlan.objects.filter(finish_time__date=datetime.datetime.today()).values(
            'material_no').annotate(plan_qty=Sum('need_qty'))
        # 计划出库的order_no列表
        delivery_plan_set = DeliveryPlan.objects.filter(finish_time__date=datetime.datetime.today())
        delivery_plan_order_no_list = list(delivery_plan_set.values_list('order_no', flat=True))
        # 计划出库的material_no列表
        delivery_plan_material_no_list = list(delivery_plan_set.values_list('material_no', flat=True))
        try:

            if IS_BZ_USING:
                # 出库数量
                mix_gum_out_qty = MixGumOutInventoryLog.objects.using('bz').filter(
                    order_no__in=delivery_plan_order_no_list).values(
                    'material_no').annotate(out_qty=Sum('qty'))
                # 库存余量
                bz_inventory_qty = BzFinalMixingRubberInventory.objects.using('bz').filter(
                    material_no__in=delivery_plan_material_no_list).values(
                    'material_no').annotate(inventory_qty=Sum('qty'))
            else:
                mix_gum_out_qty = MixGumOutInventoryLog.objects.filter(order_no__in=delivery_plan_order_no_list).values(
                    'material_no').annotate(out_qty=Sum('qty'))

                bz_inventory_qty = BzFinalMixingRubberInventory.objects.filter(
                    material_no__in=delivery_plan_material_no_list).values(
                    'material_no').annotate(inventory_qty=Sum('qty'))
        except Exception as e:
            raise ValidationError(f'连接北自数据库超时: {e}')
        for delivery_plan in delivery_plan_qty:
            delivery_plan['out_qty'] = None
            delivery_plan['inventory_qty'] = None
            for mix_gum_out in mix_gum_out_qty:
                if delivery_plan['material_no'] == mix_gum_out['material_no']:
                    delivery_plan['out_qty'] = mix_gum_out['out_qty']
            for bz_inventory in bz_inventory_qty:
                if delivery_plan['material_no'] == bz_inventory['material_no']:
                    delivery_plan['inventory_qty'] = bz_inventory['inventory_qty']
        return Response({'result': delivery_plan_qty})


@method_decorator([api_recorder], name="dispatch")
class MixGumOutInventoryLogAPIView(APIView):
    """混炼胶  倒叙显示最近几条出库信息"""

    def get(self, request):
        try:
            if IS_BZ_USING:
                mix_gum_out_data = MixGumOutInventoryLog.objects.using('bz').filter(
                    start_time__date=datetime.datetime.today()).order_by(
                    '-start_time').values(
                    'order_no',
                    'start_time',
                    'location', 'pallet_no',
                    'lot_no', 'material_no',
                    'qty', 'weight',
                    'quality_status')

            else:
                mix_gum_out_data = MixGumOutInventoryLog.objects.filter(
                    start_time__date=datetime.datetime.today()).order_by('-start_time').values(
                    'order_no',
                    'start_time',
                    'location', 'pallet_no',
                    'lot_no', 'material_no',
                    'qty', 'weight',
                    'quality_status')

            for mix_gum_out_obj in mix_gum_out_data:
                dp_last_obj = DeliveryPlan.objects.filter(order_no=mix_gum_out_obj['order_no']).all().last()
                location_name = None
                if dp_last_obj:
                    try:
                        location_name = dp_last_obj.dispatch.all().filter(
                            order_no=dp_last_obj.order_no).last().dispatch_location.name
                    except:
                        location_name = None
                mix_gum_out_obj['location_name'] = location_name
                mix_gum_out_obj['start_time'] = mix_gum_out_obj['start_time'].strftime('%Y-%m-%d %H:%M:%S')
        except:
            raise ValidationError('连接北自数据库超时')
        return Response({'result': mix_gum_out_data})


# 终炼胶出库大屏一共份三个接口
@method_decorator([api_recorder], name="dispatch")
class DeliveryPlanFinalNow(APIView):
    """终炼胶 当前在出库口的胶料信息"""

    def get(self, request):
        dp_last_obj = DeliveryPlanFinal.objects.filter(status=2).all().last()
        if dp_last_obj:
            try:
                location_name = dp_last_obj.dispatch.all().filter(
                    order_no=dp_last_obj.order_no).last().dispatch_location.name
            except:
                location_name = None
            try:
                if IS_BZ_USING:
                    final_gum_out_obj = FinalGumOutInventoryLog.objects.using('lb').filter(
                        order_no=dp_last_obj.order_no).last()
                else:
                    final_gum_out_obj = FinalGumOutInventoryLog.objects.filter(order_no=dp_last_obj.order_no).last()
            except Exception as e:
                raise ValidationError(f'连接北自数据库超时: {e}')
            if final_gum_out_obj:
                lot_no = final_gum_out_obj.lot_no
            else:
                lot_no = None
            result = {'order_no': dp_last_obj.order_no,
                      'material_no': dp_last_obj.material_no,
                      'location_name': location_name,
                      'lot_no': lot_no}

        else:
            result = None
        return Response({"result": result})


@method_decorator([api_recorder], name="dispatch")
class DeliveryPlanFinalToday(APIView):
    """终炼胶  今日的总出库量"""

    def get(self, request):
        # 计划数量
        delivery_plan_qty = DeliveryPlanFinal.objects.filter(finish_time__date=datetime.datetime.today()).values(
            'material_no').annotate(plan_qty=Sum('need_qty'))
        # 计划出库的order_no列表
        deliver_plan_set = DeliveryPlanFinal.objects.filter(finish_time__date=datetime.datetime.today())
        delivery_plan_order_no_list = list(deliver_plan_set.values_list('order_no', flat=True))
        # 计划出库的material_no列表
        delivery_plan_material_no_list = list(deliver_plan_set.values_list('material_no', flat=True))
        try:
            if IS_BZ_USING:
                # 出库数量
                mix_gum_out_qty = FinalGumOutInventoryLog.objects.using('lb').filter(
                    order_no__in=delivery_plan_order_no_list).values(
                    'material_no').annotate(out_qty=Sum('qty'))
                # 库存余量
                bz_inventory_qty = BzFinalMixingRubberInventory.objects.using('lb').filter(
                    material_no__in=delivery_plan_material_no_list).values(
                    'material_no').annotate(inventory_qty=Sum('qty'))
            else:
                mix_gum_out_qty = FinalGumOutInventoryLog.objects.filter(
                    order_no__in=delivery_plan_order_no_list).values(
                    'material_no').annotate(out_qty=Sum('qty'))
                bz_inventory_qty = BzFinalMixingRubberInventory.objects.filter(
                    material_no__in=delivery_plan_material_no_list).values(
                    'material_no').annotate(inventory_qty=Sum('qty'))
            # print(delivery_plan_qty, mix_gum_out_qty, bz_inventory_qty)
        except:
            raise ValidationError('连接北自数据库超时')
        for delivery_plan in delivery_plan_qty:
            delivery_plan['out_qty'] = None
            delivery_plan['inventory_qty'] = None
            for mix_gum_out in mix_gum_out_qty:
                if delivery_plan['material_no'] == mix_gum_out['material_no']:
                    delivery_plan['out_qty'] = mix_gum_out['out_qty']
            for bz_inventory in bz_inventory_qty:
                if delivery_plan['material_no'] == bz_inventory['material_no']:
                    delivery_plan['inventory_qty'] = bz_inventory['inventory_qty']
        return Response({'result': delivery_plan_qty})


@method_decorator([api_recorder], name="dispatch")
class FinalGumOutInventoryLogAPIView(APIView):
    """终炼胶  倒叙显示最近几条出库信息"""

    def get(self, request):
        try:
            if IS_BZ_USING:
                final_gum_out_data = FinalGumOutInventoryLog.objects.using('lb').filter(
                    start_time__date=datetime.datetime.today()).order_by(
                    '-start_time').values(
                    'order_no',
                    'start_time',
                    'location', 'pallet_no',
                    'lot_no', 'material_no',
                    'qty', 'weight',
                    'quality_status')
            else:
                final_gum_out_data = FinalGumOutInventoryLog.objects.filter(
                    start_time__date=datetime.datetime.today()).order_by('-start_time').values(
                    'order_no',
                    'start_time',
                    'location', 'pallet_no',
                    'lot_no', 'material_no',
                    'qty', 'weight',
                    'quality_status')
            for mix_gum_out_obj in final_gum_out_data:
                dp_last_obj = DeliveryPlanFinal.objects.filter(order_no=mix_gum_out_obj['order_no']).all().last()
                location_name = None
                if dp_last_obj:
                    try:
                        location_name = dp_last_obj.dispatch.all().filter(
                            order_no=dp_last_obj.order_no).last().dispatch_location.name
                    except:
                        location_name = None
                mix_gum_out_obj['location_name'] = location_name
                mix_gum_out_obj['start_time'] = mix_gum_out_obj['start_time'].strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            raise ValidationError(f'连接北自数据库超时:{e}')
        return Response({'result': final_gum_out_data})


@method_decorator([api_recorder], name="dispatch")
class InventoryStaticsView(APIView):
    permission_classes = (IsAuthenticated, PermissionClass({'view': 'view_product_stock_detail'}))

    # def single_mix_inventory(self, product_type, model=BzFinalMixingRubberInventory):
    #     temp_set = model.objects.filter(material_no__icontains=product_type)
    #     data = {}
    #     for section in self.sections:
    #         data.update(**{section: temp_set.filter(material_no__icontains=section).aggregate(weight=Sum('total_weight')/1000)})
    #     return data
    #
    # def single_edge_inventory(self, product_type, model=MaterialInventory, filter_key="material"):
    #     temp_set = model.objects.filter(material__material_no__icontains=product_type)
    #     data = {}
    #     for section in self.sections:
    #         data.update(**{
    #             section: temp_set.filter(material__material_no__icontains=section).aggregate(weight=Sum('total_weight') / 1000)})
    #     return data
    def my_sum(self, x, y):
        if not x:
            x = 0
        if not y:
            y = 0
        return x + y

    def my_cut(self, x, y):
        if not x:
            x = 0
        if not y:
            y = 0
        return x - y

    def single(self, model, data, titles, filter_key="material__material_no__icontains", db="default"):
        temp_set = model.objects.using(db).filter(**{filter_key: self.product_type})
        for section in titles:
            temp = temp_set.filter(**{filter_key: section}).aggregate(
                weight=Sum('total_weight') / 1000, qty=Sum("qty"))
            if data.get(section):
                data[section]["weight"] += temp.get("weight") if temp.get("weight") else 0
                data[section]["qty"] += temp.get("qty") if temp.get("qty") else 0
            else:
                data.update(**{section: temp})
        return data

    def get_sections(self):
        main_titles = []
        edge_titles = []
        product_set = set(
            BzFinalMixingRubberInventory.objects.filter(material_no__icontains=self.product_type).using('bz').values(
                'material_no').annotate().values_list('material_no', flat=True))
        for x in product_set:
            try:
                t = x.split('-')[1]
            except:
                pass
            else:
                main_titles.append(t)
        edge_set = set(MaterialInventory.objects.filter(material__material_no=self.product_type).values(
            'material__material_no').annotate().values_list('material__material_no', flat=True))
        for x in edge_set:
            try:
                t = x.split('-')[1]
            except:
                pass
            else:
                edge_titles.append(t)
        return list(edge_titles), list(main_titles)

    def get(self, request):
        product_type = request.query_params.get("name")
        edge_data = {}
        main_data = {}
        inventory_data = {"subject": {}, "edge": {}, "error": None, "fm_all": None, "ufm_all": None}
        if product_type:
            self.product_type = product_type  # 当前胶料种类
            edge_titles, main_titles = self.get_sections()
            inventory_data["edge"] = self.single(MaterialInventory, edge_data, edge_titles,
                                                 filter_key="material__material_no__icontains")
            inventory_data["subject"] = self.single(BzFinalMixingRubberInventory, main_data, main_titles,
                                                    filter_key="material_no__icontains", db="bz")
            inventory_data["subject"] = self.single(BzFinalMixingRubberInventoryLB, inventory_data["subject"],
                                                    main_titles,
                                                    filter_key="material_no__icontains", db='lb')  # 终炼胶库暂未启用
            # RFM，FM 规格统计计算
            if "RFM" in main_titles and "FM" in main_titles:
                fm1_weight = inventory_data["subject"].get("FM", {}).get("weight")
                rfm1_weight = inventory_data["subject"].get("RFM", {}).get("weight")
                fm1_qty = inventory_data["subject"].get("FM", {}).get("qty")
                rfm1_qty = inventory_data["subject"].get("RFM", {}).get("qty")
                inventory_data["subject"]["FM"]["weight"] = self.my_cut(fm1_weight, rfm1_weight)
                inventory_data["subject"]["FM"]["qty"] = self.my_cut(fm1_qty, rfm1_qty)
            if "RFM" in main_titles and "FM" in main_titles:
                fm2_weight = inventory_data["edge"].get("FM", {}).get("weight")
                rfm2_weight = inventory_data["edge"].get("RFM", {}).get("weight")
                fm2_qty = inventory_data["edge"].get("FM", {}).get("qty")
                rfm2_qty = inventory_data["edge"].get("RFM", {}).get("qty")
                inventory_data["edge"]["FM"]["weight"] = self.my_cut(fm2_weight, rfm2_weight)
                inventory_data["edge"]["FM"]["qty"] = self.my_cut(fm2_qty, rfm2_qty)

        else:
            raise ValidationError("请传入胶料种类")

        # 不合格加硫计算
        edge_error = MaterialInventory.objects.filter(material__material_no__icontains=self.product_type).filter(
            material__material_no__icontains="FM",
            quality_status="三等品").aggregate(weight=Sum("total_weight") / 1000).get(
            "weight", 0)
        edge_error = edge_error if edge_error else 0

        inventory_error = BzFinalMixingRubberInventory.objects.using('bz').filter(
            material_no__icontains=self.product_type).filter(material_no__icontains="FM",
                                                             quality_level="三等品").aggregate(
            weight=Sum("total_weight") / 1000).get("weight", 0)
        inventory_error = inventory_error if inventory_error else 0
        lb_error = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(
            material_no__icontains=self.product_type).filter(material_no__icontains="FM",
                                                             quality_level="三等品").aggregate(
            weight=Sum("total_weight") / 1000).get("weight", 0)
        lb_error = lb_error if lb_error else 0
        inventory_error += lb_error

        # 加硫总量计算
        fm_mi = MaterialInventory.objects.filter(material__material_no__icontains=self.product_type, ).filter(
            material__material_no__icontains="FM",
            quality_status__in=["一等品", "三等品"]).aggregate(
            weight=Sum("total_weight") / 1000).get("weight", 0)
        fm_mi = fm_mi if fm_mi else 0

        fm_bz = BzFinalMixingRubberInventory.objects.using('bz').filter(
            material_no__icontains=self.product_type, ).filter(material_no__icontains="FM",
                                                               quality_level__in=["一等品", "三等品"]).aggregate(
            weight=Sum("total_weight") / 1000).get("weight", 0)
        fm_lb = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(
            material_no__icontains=self.product_type, ).filter(material_no__icontains="FM",
                                                               quality_level__in=["一等品", "三等品"]).aggregate(
            weight=Sum("total_weight") / 1000).get("weight", 0)
        fm_bz = fm_bz if fm_bz else 0
        fm_lb = fm_lb if fm_lb else 0
        fm_all = fm_mi + fm_bz + fm_lb

        # 胶总量计算
        product_mi = MaterialInventory.objects.filter(quality_status__in=["一等品", "三等品"],
                                                      material__material_no__icontains=self.product_type).aggregate(
            weight=Sum("total_weight") / 1000).get("weight", 0)
        product_mi = product_mi if product_mi else 0

        product_bz = BzFinalMixingRubberInventory.objects.using('bz').filter(quality_level__in=["一等品", "三等品"],
                                                                             material_no__icontains=self.product_type, ).aggregate(
            weight=Sum("total_weight") / 1000).get("weight", 0)

        product_lb = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(quality_level__in=["一等品", "三等品"],
                                                                               material_no__icontains=self.product_type, ).aggregate(
            weight=Sum("total_weight") / 1000).get("weight", 0)
        product_bz = product_bz if product_bz else 0
        product_lb = product_lb if product_lb else 0
        product_all = product_mi + product_bz + product_lb

        # 不加留
        ufm_all = product_all - fm_all
        inventory_data["error"] = edge_error + inventory_error
        inventory_data["ufm_all"] = ufm_all
        inventory_data["fm_all"] = fm_all
        inventory_data["edge_titles"] = edge_titles
        inventory_data["main_titles"] = main_titles
        return Response(inventory_data)

        # product_set = set(
        #     BzFinalMixingRubberInventory.objects.values('material_no').annotate().values_list('material_no'))
        # product_types = []
        # for x in product_set:
        #     try:
        #         product_type = x.split('-')[2]
        #     except:
        #         pass
        #     else:
        #         product_types.append(product_type)
        # product_types = set(product_types)


@method_decorator([api_recorder], name="dispatch")
class ProductDetailsView(APIView):
    permission_classes = (IsAuthenticated, PermissionClass({'view': 'view_workshop_stock_detail'}))

    def deal(self, datas):
        for x in datas:
            material_no = x.get("material_no").strip()
            if not material_no in self.data:
                self.data[material_no] = x
                self.data[material_no]["material_no"] = self.data[material_no]["material_no"].strip()
                self.data[material_no]["material_name"] = self.data[material_no]["material_no"]
                try:
                    self.data[material_no]["material_type"] = self.data[material_no]["material_no"].split("-")[1]
                except:
                    self.data[material_no]["material_type"] = self.data[material_no]["material_no"]
                self.data[material_no]["other_qty"] = 0
                self.data[material_no]["other_weight"] = 0.0
                self.data[material_no]["all_qty"] = self.data[material_no]["qty"]
                self.data[material_no]["all_weight"] = self.data[material_no]["weight"]
            else:
                self.data[material_no]["qty"] += x.get("qty")
                self.data[material_no]["weight"] += x.get("weight")

    def get(self, request):
        params = request.query_params
        material_type = params.get("material_type", "")
        material_no = params.get("material_no", "")
        filters = dict()
        other_filters = dict()
        if material_type:
            filters.update(material_no__icontains=material_type)
            other_filters.update(material__material_no__icontains=material_no)
        if material_no:
            filters.update(material_no__icontains=material_no)
            other_filters.update(material__material_no__icontains=material_type)
        mix_set = BzFinalMixingRubberInventory.objects.using('bz').filter(**filters)
        final_set = BzFinalMixingRubberInventory.objects.using('lb').filter(store_name='炼胶库').filter(**filters)
        mix_data = mix_set.values("material_no").annotate(qty=Sum('qty'), weight=Sum('total_weight')).values(
            "material_no", 'qty', 'weight')
        final_data = final_set.values("material_no").annotate(qty=Sum('qty'), weight=Sum('total_weight')).values(
            "material_no", 'qty', 'weight')
        self.data = {}
        self.deal(mix_data)
        self.deal(final_data)
        other_data = MaterialInventory.objects.filter(**other_filters).values("material__material_no").annotate(
            num=Sum('qty'), weight=Sum('total_weight')).values("material__material_no", 'num', 'weight')
        for x in other_data:
            material_no = x.get("material__material_no")
            if self.data.get(material_no):
                self.data[material_no]["other_qty"] = x.get("num")
                self.data[material_no]["other_weight"] = x.get("weight")
            else:
                self.data[material_no] = {}
                self.data[material_no]["other_qty"] = x.get("num")
                self.data[material_no]["other_weight"] = x.get("weight")
                self.data[material_no]["qty"] = 0.0
                self.data[material_no]["weight"] = 0.0
                self.data[material_no]["material_name"] = material_no
                self.data[material_no]["material_no"] = material_no
                self.data[material_no]["material_type"] = material_type
            if self.data[material_no].get("all_qty"):
                self.data[material_no]["all_qty"] += x.get("num")
            else:
                self.data[material_no]["all_qty"] = x.get("num")
            if self.data[material_no].get("all_weight"):
                self.data[material_no]["all_weight"] += x.get("weight")
            else:
                self.data[material_no]["all_weight"] = x.get("weight")
        data = self.data.values()
        return Response({"results": data})


class WmsInventoryStockView(APIView):
    """WMS库存货位信息，参数：material_name=原材料名称&material_no=原材料编号&quality_status=品质状态1合格3不合格&entrance_name=出库口名称"""

    def get(self, request, *args, **kwargs):
        material_name = self.request.query_params.get('material_name')
        material_no = self.request.query_params.get('material_no')
        quality_status = self.request.query_params.get('quality_status')
        entrance_name = self.request.query_params.get('entrance_name')
        page = self.request.query_params.get('page', 1)
        page_size = self.request.query_params.get('page_size', 15)
        st = (int(page) - 1) * int(page_size)
        et = int(page) * int(page_size)
        extra_where_str = ""
        if not entrance_name:
            raise ValidationError('请选择出库口！')
        if material_name:
            extra_where_str += "and c.Name like '%{}%'".format(material_name)
        if material_no:
            extra_where_str += "and c.MaterialCode like '%{}%'".format(material_no)
        if quality_status:
            extra_where_str += "and a.StockDetailState={}".format(quality_status)
        sql = """SELECT
                 a.StockDetailState,
                 c.MaterialCode,
                 c.Name AS MaterialName,
                 a.BatchNo,
                 a.SpaceId,
                 a.Sn
                FROM
                 dbo.t_inventory_stock AS a
                 INNER JOIN t_inventory_space b ON b.Id = a.StorageSpaceEntityId
                 INNER JOIN t_inventory_material c ON c.MaterialCode= a.MaterialCode
                 INNER JOIN t_inventory_tunnel d ON d.TunnelCode= a.TunnelId 
                WHERE
                 NOT EXISTS ( 
                     SELECT 
                            tp.TrackingNumber 
                     FROM t_inventory_space_plan tp 
                     WHERE tp.TrackingNumber = a.TrackingNumber ) 
                 AND d.State= 1 
                 AND b.SpaceState= 1 
                 AND a.TunnelId IN ( 
                     SELECT 
                            ab.TunnelCode 
                     FROM t_inventory_entrance_tunnel ab INNER JOIN t_inventory_entrance ac ON ac.Id= ab.EntranceEntityId 
                     WHERE ac.name= '{}' ) {}""".format(entrance_name, extra_where_str)
        sc = SqlClient(sql=sql, **WMS_CONF)
        temp = sc.all()
        count = len(temp)
        temp = temp[st:et]
        result = []
        for item in temp:
            result.append(
                {'StockDetailState': item[0],
                 'MaterialCode': item[1],
                 'MaterialName': item[2],
                 'BatchNo': item[3],
                 'SpaceId': item[4],
                 'Sn': item[5]
                 })
        sc.close()
        return Response({'results': result, "count": count})


class WmsInventoryWeightStockView(APIView):
    """WMS库存货位信息，参数：material_name=原材料名称&material_no=原材料编号&quality_status=品质状态1合格3不合格&entrance_name=出库口名称"""

    def get(self, request, *args, **kwargs):
        material_name = self.request.query_params.get('material_name')
        material_no = self.request.query_params.get('material_no')
        quality_status = self.request.query_params.get('quality_status')
        entrance_name = self.request.query_params.get('entrance_name')
        extra_where_str = ""
        if not entrance_name:
            raise ValidationError('请选择出库口！')
        if material_name:
            extra_where_str += "and c.Name like '%{}%'".format(material_name)
        if material_no:
            extra_where_str += "and c.MaterialCode like '%{}%'".format(material_no)
        if quality_status:
            extra_where_str += "and a.StockDetailState={}".format(quality_status)

        sql = """SELECT
                 c.MaterialCode,
                 c.Name AS MaterialName,
                 SUM ( a.WeightOfActual ) AS WeightOfActual
                FROM
                 dbo.t_inventory_stock AS a
                 INNER JOIN t_inventory_space b ON b.Id = a.StorageSpaceEntityId
                 INNER JOIN t_inventory_material c ON c.MaterialCode= a.MaterialCode
                 INNER JOIN t_inventory_tunnel d ON d.TunnelCode= a.TunnelId 
                WHERE
                 NOT EXISTS ( SELECT tp.TrackingNumber FROM t_inventory_space_plan tp WHERE tp.TrackingNumber = a.TrackingNumber ) 
                 AND d.State= 1 
                 AND b.SpaceState= 1 
                 AND a.TunnelId IN (
                     SELECT
                            ab.TunnelCode
                     FROM t_inventory_entrance_tunnel ab
                         INNER JOIN t_inventory_entrance ac ON ac.Id= ab.EntranceEntityId
                     WHERE ac.name= '{}' )
                 {}
                GROUP BY
                 c.MaterialCode,
                 c.Name;""".format(entrance_name, extra_where_str)
        sc = SqlClient(sql=sql, **WMS_CONF)
        temp = sc.all()
        count = len(temp)
        result = []
        for item in temp:
            result.append(
                {'MaterialCode': item[0],
                 'MaterialName': item[1],
                 'WeightOfActual': item[2],
                 })
        sc.close()
        return Response({'results': result, "count": count})


class InventoryEntranceView(APIView):
    """获取所有出库口名称"""

    def get(self, request):
        sql = 'select name, EntranceCode from t_inventory_entrance where Type=2;'
        sc = SqlClient(sql=sql, **WMS_CONF)
        temp = sc.all()
        result = []
        for item in temp:
            result.append(
                {'name': item[0],
                 'code': item[1],
                 })
        sc.close()
        return Response(result)
