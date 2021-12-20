import datetime
import decimal
import json
import logging
import random
import re
import time
from io import BytesIO, StringIO

import requests
import xlwt
from itertools import chain
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q, F
from django.db.transaction import atomic
from django.forms import model_to_dict
from django.http import HttpResponse

from django.utils.decorators import method_decorator
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.mixins import CreateModelMixin, ListModelMixin, UpdateModelMixin, RetrieveModelMixin
from rest_framework.generics import ListAPIView, GenericAPIView
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from basics.models import GlobalCode, WorkSchedulePlan
from inventory.filters import StationFilter, PutPlanManagementLBFilter, PutPlanManagementFilter, \
    DispatchPlanFilter, DispatchLogFilter, DispatchLocationFilter, PutPlanManagementFinalFilter, \
    MaterialPlanManagementFilter, BarcodeQualityFilter, CarbonPlanManagementFilter, \
    MixinRubberyOutBoundOrderFilter, FinalRubberyOutBoundOrderFilter, DepotSiteDataFilter, DepotDataFilter, \
    SulfurResumeFilter, DepotSulfurFilter, PalletDataFilter, DepotResumeFilter, SulfurDepotSiteFilter, SulfurDataFilter, \
    OutBoundDeliveryOrderFilter, OutBoundDeliveryOrderDetailFilter

from inventory.models import InventoryLog, WarehouseInfo, Station, WarehouseMaterialType, \
    BzFinalMixingRubberInventoryLB, DeliveryPlanLB, DispatchPlan, DispatchLog, DispatchLocation, \
    MixGumOutInventoryLog, MixGumInInventoryLog, DeliveryPlanFinal, MaterialOutPlan, BarcodeQuality, \
    MaterialOutHistory, FinalGumOutInventoryLog, Depot, \
    DepotSite, DepotPallt, Sulfur, SulfurDepot, SulfurDepotSite, MaterialInHistory, MaterialInventoryLog, \
    CarbonOutPlan, FinalRubberyOutBoundOrder, MixinRubberyOutBoundOrder, FinalGumInInventoryLog, OutBoundDeliveryOrder, \
    OutBoundDeliveryOrderDetail, WMSReleaseLog, WmsInventoryMaterial, WMSMaterialSafetySettings
from inventory.models import DeliveryPlan, MaterialInventory
from inventory.serializers import PutPlanManagementSerializer, \
    OverdueMaterialManagementSerializer, WarehouseInfoSerializer, StationSerializer, WarehouseMaterialTypeSerializer, \
    PutPlanManagementSerializerLB, BzFinalMixingRubberLBInventorySerializer, DispatchPlanSerializer, \
    DispatchLogSerializer, DispatchLocationSerializer, PutPlanManagementSerializerFinal, \
    InventoryLogOutSerializer, MixinRubberyOutBoundOrderSerializer, FinalRubberyOutBoundOrderSerializer, \
    MaterialPlanManagementSerializer, BarcodeQualitySerializer, WmsStockSerializer, InOutCommonSerializer, \
    CarbonPlanManagementSerializer, DepotModelSerializer, DepotSiteModelSerializer, DepotPalltModelSerializer, \
    SulfurResumeModelSerializer, DepotSulfurInfoModelSerializer, PalletDataModelSerializer, DepotResumeModelSerializer, \
    SulfurDepotModelSerializer, SulfurDepotSiteModelSerializer, SulfurDataModelSerializer, DepotSulfurModelSerializer, \
    DepotPalltInfoModelSerializer, OutBoundDeliveryOrderSerializer, OutBoundDeliveryOrderDetailSerializer, \
    OutBoundTasksSerializer, WmsInventoryMaterialSerializer
from inventory.models import WmsInventoryStock
from inventory.serializers import BzFinalMixingRubberInventorySerializer, \
    WmsInventoryStockSerializer, InventoryLogSerializer
from mes.common_code import SqlClient, OSum
from mes.conf import WMS_CONF, TH_CONF, WMS_URL, TH_URL
from mes.derorators import api_recorder
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions

from mes.paginations import SinglePageNumberPagination
from mes.permissions import PermissionClass
from mes.settings import DEBUG
from plan.models import ProductClassesPlan, ProductBatchingClassesPlan, BatchingClassesPlan
from production.models import PalletFeedbacks, TrainsFeedbacks
from quality.deal_result import receive_deal_result
from quality.models import LabelPrint, Train, MaterialDealResult, LabelPrintLog, ExamineMaterial
from quality.serializers import MaterialDealResultListSerializer
from recipe.models import Material, MaterialAttribute
from system.models import User
from terminal.models import LoadMaterialLog, WeightBatchingLog, WeightPackageLog
from .conf import wms_ip, wms_port, IS_BZ_USING
from .conf import wms_ip, wms_port, cb_ip, cb_port
from .models import MaterialInventory as XBMaterialInventory
from .models import BzFinalMixingRubberInventory
from .serializers import XBKMaterialInventorySerializer
from .utils import export_xls, OUTWORKUploader, OUTWORKUploaderLB

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
            "standard_flag": instance[3],
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
        sql = f"""SELECT max(库房名称) as 库房名称, sum(数量) as 数量, sum(重量) as 重量, 品质等级, 物料编码, Row_Number() OVER (order by 物料编码) sn
            FROM v_ASRS_STORE_MESVIEW {filter_str} group by 物料编码, 品质等级 order by 物料编码"""
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
    """{"order_no": "ZJO202109060057",
     "pallet_no": "20104101",
     "location": "2-3-5-1",
     "qty": 1,
     "weight": 700.0,
     "quality_status": "2",
     "lot_no": "88888888",
     "inventory_type": "生产出库",
     "fin_time": "2021-09-07T00: 32:27.4085235Z",
     "status": "- 无 - "}"""

    # 出库反馈
    def post(self, request):
        logger.info('北自出库反馈数据：{}'.format(request.data))
        data = self.request.data
        if data:
            lot_no = data.get("lot_no", "99999999")  # 给一个无法查到的lot_no
            order_no = data.get('order_no')
            if order_no:
                dp_obj = OutBoundDeliveryOrderDetail.objects.filter(order_no=order_no).first()
                if dp_obj:
                    dp_obj.status = 3
                    dp_obj.finish_time = datetime.datetime.now()
                    dp_obj.save()
                    try:
                        depot_name = '混炼线边库区' if dp_obj.outbound_delivery_order.warehouse == '混炼胶库' else "终炼线边库区"
                        depot_site_name = '混炼线边库位' if dp_obj.outbound_delivery_order.warehouse == '混炼胶库' else "终炼线边库位"
                        depot, _ = Depot.objects.get_or_create(depot_name=depot_name,
                                                               description=depot_name)
                        depot_site, _ = DepotSite.objects.get_or_create(depot=depot,
                                                                        depot_site_name=depot_site_name,
                                                                        description=depot_site_name)
                        DepotPallt.objects.create(enter_time=datetime.datetime.now(),
                                                  pallet_status=1,
                                                  pallet_data=PalletFeedbacks.objects.filter(lot_no=dp_obj.lot_no).first(),
                                                  depot_site=depot_site
                                                  )
                    except Exception:
                        pass
                else:
                    return Response({"99": "FALSE", "message": "该订单非mes下发订单"})
                station = dp_obj.outbound_delivery_order.station
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
                        try:
                            LabelPrintLog.objects.create(
                                result=MaterialDealResult.objects.filter(lot_no=lot_no).first(),
                                created_user=dp_obj.outbound_delivery_order.created_user.username,
                                location=station)
                        except Exception:
                            pass
                except AttributeError as a:
                    logger.error(f"条码错误{a}")
                except Exception as e:
                    logger.error(f"未知错误{e}")
                return Response({"01": "TRUES", "message": "反馈成功，OK"})
            else:
                raise ValidationError("订单号不能为空")
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
        lot_existed = self.request.query_params.get('lot_existed')
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
            queryset = model.objects.using('bz').all().order_by('in_storage_time')
            if quality_status:
                queryset = queryset.filter(quality_level=quality_status)
        elif model == BzFinalMixingRubberInventoryLB:
            # 出库计划弹框展示的库位数据需要更具库位状态进行筛选其他页面不需要
            # if self.request.query_params.get("location_status"):
            #     queryset = model.objects.using('lb').filter(location_status=self.request.query_params.get("location_status"))
            # else:
            queryset = model.objects.using('lb').order_by('in_storage_time')
            if lot_existed:
                if lot_existed == '1':
                    queryset = queryset.exclude(lot_no__isnull=True)
                else:
                    queryset = queryset.filter(lot_no__isnull=True)
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

    def get_queryset(self):
        filter_dict = {}
        store_name = self.request.query_params.get("warehouse_name", '混炼胶库')
        start_time = self.request.query_params.get("start_time")
        end_time = self.request.query_params.get("end_time")
        location = self.request.query_params.get("location")
        material_no = self.request.query_params.get("material_no")
        material_name = self.request.query_params.get("material_name")
        quality_status = self.request.query_params.get("quality_status")
        order_no = self.request.query_params.get("order_no")
        lot_no = self.request.query_params.get("lot_no")
        pallet_no = self.request.query_params.get("pallet_no")
        order_type = self.request.query_params.get("order_type")
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
                temp_set = list(FinalGumOutInventoryLog.objects.using('lb').filter(**filter_dict).filter(
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
        elif store_name in ("原材料库", '炭黑库'):
            database = 'wms' if store_name == '原材料库' else 'cb'
            if order_type == "出库":
                queryset = MaterialOutHistory.objects.using(database).all()
            else:
                queryset = MaterialInHistory.objects.using(database).all()
            if start_time:
                filter_dict.update(task__start_time__gte=start_time)
            if end_time:
                filter_dict.update(task__start_time__lte=end_time)
            if material_name:
                filter_dict.update(material_name__icontains=material_name)
            if quality_status:
                if quality_status == '1':
                    batch_nos = list(ExamineMaterial.objects.filter(qualified=True).values_list('batch', flat=True))
                elif quality_status == '3':
                    batch_nos = list(ExamineMaterial.objects.filter(qualified=False).values_list('batch', flat=True))
                else:
                    batch_nos = list(ExamineMaterial.objects.values_list('batch', flat=True))
                    return queryset.filter(~Q(batch_no__in=batch_nos) | Q(batch_no__isnull=True)).filter(**filter_dict)
                filter_dict.update(batch_no__in=batch_nos)
            return queryset.filter(**filter_dict)
        else:
            return []

    def get_serializer_class(self):
        store_name = self.request.query_params.get("warehouse_name", "混炼胶库")
        serializer_dispatch = {
            "混炼胶库": InventoryLogSerializer,
            "终炼胶库": InventoryLogSerializer,
            "原材料库": InOutCommonSerializer,
            "炭黑库": InOutCommonSerializer,
            "帘布库": InventoryLogSerializer
        }
        return serializer_dispatch.get(store_name)

    def export_xls(self, result):
        response = HttpResponse(content_type='application/vnd.ms-excel')
        filename = '物料出入库履历'
        response['Content-Disposition'] = u'attachment;filename= ' + filename.encode('gbk').decode(
            'ISO-8859-1') + '.xls'
        # 创建一个文件对象
        wb = xlwt.Workbook(encoding='utf8')
        # 创建一个sheet对象
        sheet = wb.add_sheet('出入库信息', cell_overwrite_ok=True)
        style = xlwt.XFStyle()
        style.alignment.wrap = 1

        columns = ['No', '类型', '出入库单号', '质检条码', '托盘号', '机台', '时间/班次', '车号', '物料编码', '出入库原因',
                   '出入库类型', '出入库数', '单位', '重量', '发起人', '发起时间', '完成时间']
        # 写入文件标题
        for col_num in range(len(columns)):
            sheet.write(0, col_num, columns[col_num])
            # 写入数据
        data_row = 1
        for i in result:
            sheet.write(data_row, 0, result.index(i) + 1)
            sheet.write(data_row, 1, i['order_type'])
            sheet.write(data_row, 2, i['order_no'])
            sheet.write(data_row, 3, i['lot_no'])
            sheet.write(data_row, 4, i['pallet_no'])
            sheet.write(data_row, 5, i['product_info']['equip_no'])
            sheet.write(data_row, 6, i['product_info']['classes'])
            sheet.write(data_row, 7, i['product_info']['memo'])
            sheet.write(data_row, 8, i['material_no'])
            sheet.write(data_row, 9, i['inout_reason'])
            sheet.write(data_row, 10, i['inout_num_type'])
            sheet.write(data_row, 11, i['qty'])
            sheet.write(data_row, 12, i['unit'])
            sheet.write(data_row, 13, i['weight'])
            sheet.write(data_row, 14, i['initiator'])
            sheet.write(data_row, 15, i['start_time'])
            sheet.write(data_row, 16, i['fin_time'])
            data_row = data_row + 1
        # 写出到IO
        output = BytesIO()
        wb.save(output)
        # 重新定位到开始
        output.seek(0)
        response.write(output.getvalue())
        return response

    def export_xls2(self, result):
        response = HttpResponse(content_type='application/vnd.ms-excel')
        filename = '物料出入库履历'
        response['Content-Disposition'] = u'attachment;filename= ' + filename.encode('gbk').decode(
            'ISO-8859-1') + '.xls'
        # 创建一个文件对象
        wb = xlwt.Workbook(encoding='utf8')
        # 创建一个sheet对象
        sheet = wb.add_sheet('出入库信息', cell_overwrite_ok=True)
        style = xlwt.XFStyle()
        style.alignment.wrap = 1

        columns = ['No', '类型', '出入库单号', '质检条码', '托盘号', '物料编码', '出入库数', '单位', '重量', '发起人', '发起时间', '完成时间']
        # 写入文件标题
        for col_num in range(len(columns)):
            sheet.write(0, col_num, columns[col_num])
            # 写入数据
        data_row = 1
        for i in result:
            sheet.write(data_row, 0, result.index(i) + 1)
            sheet.write(data_row, 1, i['order_type'])
            sheet.write(data_row, 2, i['order_no'])
            sheet.write(data_row, 3, i['lot_no'])
            sheet.write(data_row, 4, i['pallet_no'])
            sheet.write(data_row, 5, i['material_no'])
            sheet.write(data_row, 6, i['qty'])
            sheet.write(data_row, 7, i['unit'])
            sheet.write(data_row, 8, i['weight'])
            sheet.write(data_row, 9, i['initiator'])
            sheet.write(data_row, 10, i['start_time'])
            sheet.write(data_row, 11, i['fin_time'])
            data_row = data_row + 1
        # 写出到IO
        output = BytesIO()
        wb.save(output)
        # 重新定位到开始
        output.seek(0)
        response.write(output.getvalue())
        return response

    def list(self, request, *args, **kwargs):
        export = self.request.query_params.get('export', None)
        store_name = self.request.query_params.get("warehouse_name", "混炼胶库")
        queryset = self.filter_queryset(self.get_queryset())
        if export:
            serializer = self.get_serializer(self.get_queryset(), many=True)
            if store_name in ('混炼胶库', '终炼胶库', '帘布库'):
                return self.export_xls(serializer.data)
            else:
                return self.export_xls2(serializer.data)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            if store_name in ('原材料库', '炭黑库'):
                test_data = dict(ExamineMaterial.objects.values_list('batch', 'qualified'))
                for item in serializer.data:
                    item['is_qualified'] = test_data.get(item['batch_no'], None)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@method_decorator([api_recorder], name="dispatch")
class AdditionalPrintDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        data = self.request.query_params
        location = data.get('location')
        material_no = data.get('material_no')
        start_time = data.get('start_time')
        initiator = data.get('initiator')
        weight = data.get('weight')
        pallet_no = data.get('pallet_no')
        type = data.get('type')
        lot_no = data.get('lot_no') if data.get('lot_no') != '88888888' else \
            re.sub('-| |:', '', start_time[2:]) + type + location.replace('-', '')
        label = receive_deal_result(lot_no)
        if not label:
            label = {
                "id": None, "day_time": start_time[:10], "product_no": material_no, "equip_no": "", "lot_no": lot_no,
                "residual_weight": None, "actual_weight": weight, "operation_user": initiator, "actual_trains": "",
                "classes_group": "", "valid_time": "", "range_showed": 0, "deal_suggestion": "", "deal_user": "",
                "deal_time": "", "production_factory_date": start_time[:10], "deal_result": "",
                "test": {"test_status": "", "test_factory_date": "", "test_class": "", "pallet_no": pallet_no,
                         "test_user": ""},
                "print_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "mtr_list": {"trains": [], "table_head": []}
            }
            # 未快检的正常条码
            data = PalletFeedbacks.objects.filter(lot_no=lot_no).first()
            if data:
                # 获取班组
                record = ProductClassesPlan.objects.filter(plan_classes_uid=data.plan_classes_uid).first()
                group = '' if not record else record.work_schedule_plan.group.global_name
                label.update({'equip_no': data.equip_no, 'classes_group': f'{data.classes}/{group}',
                              'actual_trains': f'{data.begin_trains}/{data.end_trains}'})
        else:
            label = json.loads(label)
        return Response(label)


@method_decorator([api_recorder], name="dispatch")
class AdditionalPrintView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    # 补打印
    def post(self, request):
        """WMS->MES:任务编号、物料信息ID、物料名称、PDM号（促进剂以外为空）、批号、条码、重量、重量单位、
        生产日期、使用期限、托盘RFID、工位（出库口）、MES->WMS:信息接收成功or失败"""
        data = self.request.data
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
        for single_data in data:
            # 有条码直接打印, 无条码生成新码
            location = single_data.get('location')
            station = single_data.get('station')
            material_no = single_data.get('material_no')
            start_time = single_data.get('start_time')
            initiator = single_data.get('initiator')
            weight = single_data.get('weight')
            pallet_no = single_data.get('pallet_no')
            type = single_data.get('type')
            lot_no = single_data.get('lot_no') if single_data.get('lot_no') != '88888888' else \
                re.sub('-| |:', '', single_data["start_time"][2:]) + type + location.replace('-', '')
            label = receive_deal_result(lot_no)
            if not label:
                label = {
                    "id": None, "day_time": start_time[:10], "product_no": material_no, "equip_no": "",
                    "residual_weight": None, "actual_weight": weight, "operation_user": initiator, "actual_trains": "",
                    "classes_group": "", "valid_time": "", "range_showed": 0, "deal_suggestion": "", "deal_user": "",
                    "deal_time": "", "production_factory_date": start_time[:10], "deal_result": "", "lot_no": lot_no,
                    "test": {"test_status": "", "test_factory_date": "", "test_class": "", "pallet_no": pallet_no,
                             "test_user": ""},
                    "print_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "mtr_list": {"trains": [], "table_head": []}
                }
                # 未快检的正常条码
                data = PalletFeedbacks.objects.filter(lot_no=lot_no).first()
                if data:
                    # 获取班组
                    record = ProductClassesPlan.objects.filter(plan_classes_uid=data.plan_classes_uid).first()
                    group = '' if not record else record.work_schedule_plan.group.global_name
                    label.update({"equip_no": data.equip_no, "classes_group": f"{data.classes}/{group}",
                                  "actual_trains": f"{data.begin_trains}/{data.end_trains}"})
                label = json.dumps(label)
            LabelPrint.objects.create(label_type=station_dict.get(station), lot_no=lot_no, status=0, data=label)
        return Response('下发打印完成')


@method_decorator([api_recorder], name="dispatch")
class MaterialCount(APIView):

    def get(self, request):
        params = request.query_params
        store_name = params.get('store_name')
        status = params.get("status")
        if not store_name:
            raise ValidationError("缺少立库名参数，请检查后重试")
        filter_dict = {}
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
                ret = BzFinalMixingRubberInventory.objects.using('bz').filter(
                    **filter_dict).values(
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
    # permission_classes = (permissions.IsAuthenticated,)
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
class MixinRubberyOutBoundOrderViewSet(GenericViewSet, ListModelMixin, UpdateModelMixin, RetrieveModelMixin):
    """
    list:
        混炼胶出库单列表
    update
         出库/关闭出库
    """
    queryset = MixinRubberyOutBoundOrder.objects.filter().order_by("-created_date")
    serializer_class = MixinRubberyOutBoundOrderSerializer
    filter_backends = [DjangoFilterBackend]
    filter_class = MixinRubberyOutBoundOrderFilter
    permission_classes = (IsAuthenticated,)


@method_decorator([api_recorder], name="dispatch")
class FinalRubberyOutBoundOrderViewSet(GenericViewSet, ListModelMixin, UpdateModelMixin, RetrieveModelMixin):
    """
    list:
        终炼胶出库单列表
    update
         出库/关闭出库
    """
    queryset = FinalRubberyOutBoundOrder.objects.filter().order_by("-created_date")
    serializer_class = FinalRubberyOutBoundOrderSerializer
    filter_backends = [DjangoFilterBackend]
    filter_class = FinalRubberyOutBoundOrderFilter
    permission_classes = (IsAuthenticated,)


@method_decorator([api_recorder], name="dispatch")
class PutPlanManagement(ModelViewSet):
    """
    list:
        混炼胶出库计划列表
    create:
        新建出库计划
    update:
        人工出库/修改出库数据/关闭出库订单
    """
    queryset = DeliveryPlan.objects.filter().order_by("-created_date")
    serializer_class = PutPlanManagementSerializer
    filter_backends = [DjangoFilterBackend]
    filter_class = PutPlanManagementFilter
    permission_classes = (IsAuthenticated,)

    @atomic()
    def create(self, request, *args, **kwargs):
        data = request.data
        order = MixinRubberyOutBoundOrder.objects.create(warehouse_name='混炼胶库',
                                                         order_type='指定出库',
                                                         order_no=''.join(str(time.time()).split('.')),
                                                         created_user=self.request.user)
        if isinstance(data, list):
            for item in data:
                item['outbound_order'] = order.id
            s = PutPlanManagementSerializer(data=data, context={'request': request}, many=True)
            if not s.is_valid():
                raise ValidationError(s.errors)
            s.save()
        elif isinstance(data, dict):
            data['outbound_order'] = order.id
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
    """
    list:
        终炼胶出库计划列表
    create:
        新建出库计划
    update:
        人工出库/修改出库数据/关闭出库订单
    """

    queryset = DeliveryPlanFinal.objects.filter().order_by("-created_date")
    serializer_class = PutPlanManagementSerializerFinal
    filter_backends = [DjangoFilterBackend]
    filter_class = PutPlanManagementFinalFilter
    permission_classes = (IsAuthenticated,)

    @atomic()
    def create(self, request, *args, **kwargs):
        data = request.data
        order = FinalRubberyOutBoundOrder.objects.create(warehouse_name='混炼胶库',
                                                         order_type='指定出库',
                                                         order_no=''.join(str(time.time()).split('.')),
                                                         created_user=self.request.user)
        if isinstance(data, list):
            for item in data:
                item['outbound_order'] = order.id
            s = PutPlanManagementSerializerFinal(data=data, context={'request': request}, many=True)
            if not s.is_valid():
                raise ValidationError(s.errors)
            s.save()
        elif isinstance(data, dict):
            data['outbound_order'] = order.id
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
        trains_temp = TrainsFeedbacks.objects.filter(plan_classes_uid=plan_no).order_by('id')
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
    # permission_classes = (IsAuthenticated, PermissionClass({'view': 'view_product_stock_detail'}))

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

    def single(self, model, filter_key="material__material_no__icontains", db="default"):
        temp_set = model.objects.using(db).filter(**{filter_key: self.product_type,
                                                     }).values(filter_key.split('__icontains')[0]).annotate(
            qty=Sum('qty'), weight=Sum('total_weight')).values(filter_key.split('__icontains')[0], 'qty', 'weight')

        return temp_set

    def get_sections(self, s_time, e_time):
        main_titles = []
        edge_titles = []
        product_set = set(
            BzFinalMixingRubberInventory.objects.filter(material_no__icontains=self.product_type,
                                                        in_storage_time__gte=s_time,
                                                        in_storage_time__lte=e_time
                                                        ).using('bz').values(
                'material_no').annotate().values_list('material_no', flat=True))

        for x in product_set:
            try:
                t = x.split('-')[1]
            except:
                pass
            else:
                main_titles.append(t)
        edge_set = set(MaterialInventory.objects.filter(material__material_no=self.product_type,
                                                        created_date__gte=s_time,
                                                        created_date__lte=e_time
                                                        ).values(
            'material__material_no').annotate().values_list('material__material_no', flat=True))

        for x in edge_set:
            try:
                t = x.split('-')[1]
            except:
                pass
            else:
                edge_titles.append(t)
        return list(main_titles), list(edge_titles)

    def get(self, request):
        product_type = request.query_params.get("name")
        s_time = request.query_params.get("s_time")
        e_time = request.query_params.get("e_time")
        page = request.query_params.get("page", 1)
        if not s_time and not e_time:
            s_time, e_time = '1111-11-11', '9999-11-11'

        self.product_type = product_type
        main_titles, edge_titles = self.get_sections(s_time, e_time)
        # st = (int(page) - 1) * 10
        # et = int(page) * 10

        a = MaterialInventory.objects.using('default').filter(material__material_no__icontains=self.product_type,
                                                              created_date__gte=s_time,
                                                              created_date__lte=e_time
                                                              ).values('material__material_no').annotate(
            qty=Sum('qty'), weight=Sum('total_weight')).values('material__material_no', 'qty', 'weight').order_by('material')
        aa = []
        if len(a) > 0:
            for i in a:
                aa.append({'material_no': i['material__material_no'], 'qty': i['qty'], 'weight': i['weight']})

        bz = BzFinalMixingRubberInventory.objects.using('bz').filter(material_no__icontains=self.product_type,
                                                                     in_storage_time__gte=s_time,
                                                                     in_storage_time__lte=e_time
                                                                     ).values('material_no').annotate(
            qty=Sum('qty'), weight=Sum('total_weight')).values('material_no', 'qty', 'weight').order_by('material_no')

        lb = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(material_no__icontains=self.product_type,
                                                                       store_name='炼胶库',
                                                                       in_storage_time__gte=s_time,
                                                                       in_storage_time__lte=e_time
                                                                       ).values('material_no').annotate(
            qty=Sum('qty'), weight=Sum('total_weight')).values('material_no', 'qty', 'weight').order_by('material_no')

        edge = list(aa)  # 车间
        subject = list(bz) + list(lb)  # 立库

        results = {}

        for i in subject:
            try:
                res = {
                    i['material_no'].split('-')[2]: {
                        'subject': {i['material_no'].split('-')[1]: {'qty': i['qty'], 'weight': i['weight']}},
                        'edge': {},
                        'error': 0,
                        'fm_all': 0,
                        'ufm_all': 0  # 不加硫
                    }
                }

                if results.get(i['material_no'].split('-')[2]):
                    if results[i['material_no'].split('-')[2]]['subject'].get(i['material_no'].split('-')[1]):
                        results[i['material_no'].split('-')[2]]['subject'][i['material_no'].split('-')[1]]['qty'] += i[
                            'qty']
                        results[i['material_no'].split('-')[2]]['subject'][i['material_no'].split('-')[1]]['weight'] += \
                        i['weight']
                    else:
                        results[i['material_no'].split('-')[2]]['subject'].update(
                            {i['material_no'].split('-')[1]: {'qty': i['qty'], 'weight': i['weight']}})
                else:
                    results.update(res)
            except:
                pass

        for i in edge:
            try:
                res = {i['material_no'].split('-')[2]: {
                    'subject': {},
                    'edge': {i['material_no'].split('-')[1]: {'qty': i['qty'], 'weight': i['weight']}},
                    'error': 0,
                    'fm_all': 0,
                    'ufm_all': 0  # 不加硫
                }}

                if results.get(i['material_no'].split('-')[2]):
                    if results[i['material_no'].split('-')[2]]['subject'].get(i['material_no'].split('-')[1]):
                        results[i['material_no'].split('-')[2]]['subject'][i['material_no'].split('-')[1]]['qty'] += i['qty']
                        results[i['material_no'].split('-')[2]]['subject'][i['material_no'].split('-')[1]]['weight'] += i['weight']
                    else:
                        results[i['material_no'].split('-')[2]]['subject'].update(
                            {i['material_no'].split('-')[1]: {'qty': i['qty'], 'weight': i['weight']}})
                else:
                    results.update(res)
            except:
                pass

        for i in results:
            if "RFM" in main_titles and "FM" in main_titles:  # ['1MB', 'HMB']
                fm1_weight = results[i]['subject'].get("FM", {}).get("weight")
                rfm1_weight = results[i]['subject'].get("RFM", {}).get("weight")
                fm1_qty = results[i]['subject'].get("FM", {}).get("qty")
                rfm1_qty = results[i]['subject'].get("RFM", {}).get("qty")
                results[i]['subject']["FM"]["weight"] = self.my_cut(fm1_weight, rfm1_weight)
                results[i]['subject']["FM"]["qty"] = self.my_cut(fm1_qty, rfm1_qty)
            if "RFM" in main_titles and "FM" in main_titles:
                fm2_weight = results[i]['edge'].get("FM", {}).get("weight")
                rfm2_weight = results[i]['edge'].get("RFM", {}).get("weight")
                fm2_qty = results[i]['edge'].get("FM", {}).get("qty")
                rfm2_qty = results[i]['edge'].get("RFM", {}).get("qty")
                results[i]['edge']["FM"]["weight"] = self.my_cut(fm2_weight, rfm2_weight)
                results[i]['edge']["FM"]["qty"] = self.my_cut(fm2_qty, rfm2_qty)

        # 不合格加硫计算/ 加硫总量计算
        s = ["FM", 'RE', 'RFM']
        for station in s:
            edge_error = MaterialInventory.objects.filter(material__material_no__icontains=self.product_type).filter(
                material__material_no__icontains=f'-{station}').values('material__material_no',
                                                                       'quality_status').annotate(
                weight=Sum("total_weight")).values('material__material_no', 'weight', 'quality_status')
            if len(edge_error) > 0:
                for i in edge_error:
                    try:
                        if results.get(i['material__material_no'].split('-')[2]) and i['quality_status'] == '三等品':
                            results[i['material__material_no'].split('-')[2]]['error'] += i['weight']
                        if results.get(i['material__material_no'].split('-')[2]):
                            results[i['material__material_no'].split('-')[2]]['fm_all'] += i['weight']
                    except:
                        pass

            inventory_error = BzFinalMixingRubberInventory.objects.using('bz').filter(
                in_storage_time__gte=s_time,
                in_storage_time__lte=e_time,
                material_no__icontains=self.product_type).filter(material_no__icontains=f'-{station}',
                                                                 ).values('material_no', 'quality_level'). \
                annotate(weight=Sum("total_weight")).values('material_no', 'weight', 'quality_level')
            if len(inventory_error) > 0:
                for i in inventory_error:
                    try:
                        if results.get(i['material_no'].split('-')[2]) and i['quality_level'] == '三等品':
                            results[i['material_no'].split('-')[2]]['error'] += i['weight']
                        if results.get(i['material_no'].split('-')[2]):
                            results[i['material_no'].split('-')[2]]['fm_all'] += i['weight']
                    except:
                        pass

            lb_error = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(
                in_storage_time__gte=s_time,
                in_storage_time__lte=e_time,
                material_no__icontains=self.product_type).filter(material_no__icontains=f'-{station}',
                                                                 ).values('material_no', 'quality_level'). \
                annotate(weight=Sum("total_weight")).values('material_no', 'weight', 'quality_level')
            if len(lb_error) > 0:
                for i in lb_error:
                    try:
                        if results.get(i['material_no'].split('-')[2]) and i['quality_level'] == '三等品':
                            results[i['material_no'].split('-')[2]]['error'] += i['weight']
                        if results.get(i['material_no'].split('-')[2]):
                            results[i['material_no'].split('-')[2]]['fm_all'] += i['weight']
                    except:
                        pass

        # 无硫总量计算
        ws = ["CMB", 'HMB', 'NF', 'RMB', '1MB', '2MB', '3MB']
        for station in ws:
            product_mi = MaterialInventory.objects.filter(material__material_no__icontains=self.product_type,
                                                          created_date__gte=s_time,
                                                          created_date__lte=e_time
                                                          ).filter(
                material__material_no__icontains=station).values('material__material_no'). \
                annotate(weight=Sum("total_weight")).values('material__material_no', 'weight')
            if len(product_mi) > 0:
                for i in product_mi:
                    try:
                        if results.get(i['material__material_no'].split('-')[2]):
                            results[i['material__material_no'].split('-')[2]]['ufm_all'] += i['weight']
                    except:
                        pass

            product_bz = BzFinalMixingRubberInventory.objects.using('bz').filter(
                material_no__icontains=self.product_type,
                in_storage_time__gte=s_time,
                in_storage_time__lte=e_time,
                ).filter(
                material_no__icontains=station).values('material_no').annotate(weight=Sum("total_weight")).values(
                'material_no', 'weight')
            if len(product_bz) > 0:
                for i in product_bz:
                    try:
                        if results.get(i['material_no'].split('-')[2]):
                            results[i['material_no'].split('-')[2]]['ufm_all'] += i['weight']
                    except:
                        pass

            product_lb = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(
                material_no__icontains=self.product_type,
                in_storage_time__gte=s_time,
                in_storage_time__lte=e_time,
                ).filter(
                material_no__icontains=station).values('material_no').annotate(weight=Sum("total_weight")).values(
                'material_no', 'weight')
            if len(product_lb) > 0:
                for i in product_lb:
                    try:
                        if results.get(i['material_no'].split('-')[2]):
                            results[i['material_no'].split('-')[2]]['ufm_all'] += i['weight']
                    except:
                        pass

        for i in results:
            lst = ["CMB", 'HMB', 'NF', 'RMB', '1MB', '2MB', '3MB', "FM", 'RE', 'RFM']
            for j in lst:
                try:
                    results[i]['subject'][j]['weight'] = round(results[i]['subject'][j]['weight'] / 1000, 3) if \
                    results[i]['subject'].get(j) else None
                except:
                    pass
                try:
                    results[i]['edge'][j]['weight'] = round(results[i]['edge'][j]['weight'] / 1000, 3) if results[i][
                        'edge'].get(j) else None
                except:
                    pass
            results[i]['error'] = round(results[i]['error'] / 1000, 3)
            results[i]['fm_all'] = round(results[i]['fm_all'] / 1000, 3)
            results[i]['ufm_all'] = round(results[i]['ufm_all'] / 1000, 3)

        return Response({'results': results, 'count': len(results)})


@method_decorator([api_recorder], name="dispatch")
class ProductDetailsView(APIView):
    permission_classes = (IsAuthenticated, PermissionClass({'view': 'view_workshop_stock_detail'}))

    def export_xls(self, result):
        response = HttpResponse(content_type='application/vnd.ms-excel')
        filename = '车间库存明细'
        response['Content-Disposition'] = u'attachment;filename= ' + filename.encode('gbk').decode(
            'ISO-8859-1') + '.xls'
        # 创建一个文件对象
        wb = xlwt.Workbook(encoding='utf8')
        # 创建一个sheet对象
        sheet = wb.add_sheet('库存信息', cell_overwrite_ok=True)

        style = xlwt.XFStyle()
        style.alignment.wrap = 1

        columns = ['No', '胶料类型', '胶料编码', '胶料名称', '数量', '重量/kg', '数量/kg', '重量', '数量', '重量/kg']
        # 写入文件标题
        sheet.write_merge(0, 0, 0, 3, '基础信息')
        sheet.write_merge(0, 0, 4, 5, '立库库存量')
        sheet.write_merge(0, 0, 6, 7, '线边库库存量')
        sheet.write_merge(0, 0, 8, 9, '总量')

        for col_num in range(len(columns)):
            sheet.write(1, col_num, columns[col_num])
            # 写入数据
        data_row = 2
        for i in result:
            sheet.write(data_row, 0, result.index(i) + 1)
            sheet.write(data_row, 1, i['material_type'])
            sheet.write(data_row, 2, i['material_no'])
            sheet.write(data_row, 3, i['material_name'])
            sheet.write(data_row, 4, i['qty'])
            sheet.write(data_row, 5, i['weight'])
            sheet.write(data_row, 6, i['other_qty'])
            sheet.write(data_row, 7, i['other_weight'])
            sheet.write(data_row, 8, i['all_qty'])
            sheet.write(data_row, 9, i['all_weight'])
            data_row = data_row + 1
        # 写出到IO
        output = BytesIO()
        wb.save(output)
        # 重新定位到开始
        output.seek(0)
        response.write(output.getvalue())
        return response

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
        export = params.get("export")
        filters = dict()
        other_filters = dict()
        filters.update(material_no__icontains=material_no, material_no__contains=material_type)
        other_filters.update(material__material_no__icontains=material_no,
                             material__material_no__contains=material_type)

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
        if export:
            return self.export_xls(list(data))
        return Response({"results": data})


"""原材料库出库接口"""


class WmsStorageSummaryView(APIView):
    """
        原材料库存统计列表（按物料编码、品质状态、单位、批次号分组统计）
        参数：?material_name=物料名称&material_no=物料编码&zc_material_code=中策物料编码&batch_no=批次号&pdm_no=PDM号&st=入库开始时间&et=入库结束时间&quality_status=# 品质状态 1：合格 3：不合格
    """
    DATABASE_CONF = WMS_CONF

    def get(self, request):
        material_name = self.request.query_params.get('material_name')  # 物料名称
        material_no = self.request.query_params.get('material_no')  # 物料编码
        zc_material_code = self.request.query_params.get('zc_material_code')  # 中策物料编码
        batch_no = self.request.query_params.get('batch_no')  # 批次号
        pdm_no = self.request.query_params.get('pdm_no')  # PDM号
        inventory_st = self.request.query_params.get('st')  # 入库开始时间
        inventory_et = self.request.query_params.get('et')  # 入库结束时间
        quality_status = self.request.query_params.get('quality_status')  # 品质状态 1：合格  3：不合格
        page = self.request.query_params.get('page', 1)
        page_size = self.request.query_params.get('page_size', 15)
        st = (int(page) - 1) * int(page_size)
        et = int(page) * int(page_size)
        extra_where_str = inventory_where_str = ""
        if material_name:
            extra_where_str += "where temp.Name like '%{}%'".format(material_name)
        if material_no:
            if extra_where_str:
                extra_where_str += " and temp.MaterialCode like '%{}%'".format(material_no)
            else:
                extra_where_str += "where temp.MaterialCode like '%{}%'".format(material_no)
        if zc_material_code:
            if extra_where_str:
                extra_where_str += " and m.ZCMaterialCode='{}'".format(zc_material_code)
            else:
                extra_where_str += "where m.ZCMaterialCode='{}'".format(zc_material_code)
        if batch_no:
            if extra_where_str:
                extra_where_str += " and temp.BatchNo='{}'".format(batch_no)
            else:
                extra_where_str += "where temp.BatchNo='{}'".format(batch_no)
        if quality_status:
            if extra_where_str:
                extra_where_str += " and temp.StockDetailState='{}'".format(quality_status)
            else:
                extra_where_str += "where temp.StockDetailState='{}'".format(quality_status)
        if pdm_no:
            if extra_where_str:
                extra_where_str += " and m.Pdm='{}'".format(pdm_no)
            else:
                extra_where_str += "where m.Pdm='{}'".format(pdm_no)
        if inventory_st:
            if inventory_where_str:
                inventory_where_str += " and a.CreaterTime>='{}'".format(inventory_st)
            else:
                inventory_where_str += "where a.CreaterTime>='{}'".format(inventory_st)
        if inventory_et:
            if inventory_where_str:
                inventory_where_str += " and a.CreaterTime<='{}'".format(inventory_et)
            else:
                inventory_where_str += "where a.CreaterTime<='{}'".format(inventory_et)
        sql = """
                select
            temp.MaterialName,
            temp.MaterialCode,
            m.ZCMaterialCode,
            temp.WeightUnit,
            m.Pdm,
            temp.quantity,
            temp.WeightOfActual,
            temp.BatchNo,
            temp.StockDetailState
        from (
            select
                a.MaterialCode,
                a.BatchNo,
                a.WeightUnit,
                a.StockDetailState,
                a.MaterialName,
                SUM ( a.WeightOfActual ) AS WeightOfActual,
                SUM ( a.Quantity ) AS quantity
            from dbo.t_inventory_stock AS a
            {}
            group by
                 a.MaterialCode,
                 a.MaterialName,
                 a.BatchNo,
                 a.WeightUnit,
                 a.StockDetailState
            ) temp
        left join t_inventory_material m on m.MaterialCode=temp.MaterialCode 
        {}
        order by m.MaterialCode
        """.format(inventory_where_str, extra_where_str)
        sc = SqlClient(sql=sql, **self.DATABASE_CONF)
        temp = sc.all()
        count = len(temp)
        temp = temp[st:et]
        result = []
        for item in temp:
            result.append(
                {'material_name': item[0],
                 'material_no': item[1],
                 'zc_material_code': item[2],
                 'unit': item[3],
                 'pdm_no': item[4],
                 'quantity': item[5],
                 'weight': item[6],
                 'batch_no': item[7],
                 'quality_status': item[8]
                 })
        sc.close()
        return Response({'results': result, "count": count})


@method_decorator([api_recorder], name="dispatch")
class WmsStorageView(ListAPIView):
    queryset = WmsInventoryStock.objects.order_by('in_storage_time')
    serializer_class = WmsInventoryStockSerializer
    permission_classes = (IsAuthenticated,)
    DATABASE_CONF = 'wms'
    FILE_NAME = '原材料库位明细'
    EXPORT_FIELDS_DICT = {"物料名称": "material_name", "物料编码": "material_no", "质检条码": "lot_no",
                          "托盘号": "container_no", "库位地址": "location", "单位": "unit",
                          "单位重量": "unit_weight", "总重量": "total_weight", "品质状态": "quality_status"}

    def list(self, request, *args, **kwargs):
        filter_kwargs = {}
        # 模糊查询字段
        container_no = self.request.query_params.get('pallet_no')
        material_name = self.request.query_params.get('material_name')
        material_no = self.request.query_params.get('material_no')
        # 等于查询
        e_material_no = self.request.query_params.get('e_material_no')
        unit = self.request.query_params.get('unit')
        batch_no = self.request.query_params.get('batch_no')
        st = self.request.query_params.get('st')
        et = self.request.query_params.get('et')
        quality_status = self.request.query_params.get('quality_status')
        export = self.request.query_params.get('export')  # 1：当前页面  2：所有
        if material_no:
            filter_kwargs['material_no__icontains'] = material_no
        if material_name:
            filter_kwargs['material_name__icontains'] = material_name
        if container_no:
            filter_kwargs['container_no__icontains'] = container_no
        if e_material_no:
            filter_kwargs['material_no'] = e_material_no
        if unit:
            filter_kwargs['unit'] = unit
        if batch_no:
            filter_kwargs['batch_no'] = batch_no
        if quality_status:
            filter_kwargs['quality_status'] = quality_status
        if st:
            filter_kwargs['in_storage_time__gte'] = st
        if et:
            filter_kwargs['in_storage_time__lte'] = et
        queryset = WmsInventoryStock.objects.using(self.DATABASE_CONF).filter(**filter_kwargs)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        if export:
            if export == '1':
                data = serializer.data
            else:
                data = self.get_serializer(queryset, many=True).data
            return export_xls(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        data = self.get_paginated_response(serializer.data).data
        sum_data = queryset.aggregate(total_weight=Sum('total_weight'),
                                      total_trains=Sum('qty'))
        data['total_weight'] = sum_data['total_weight']
        data['total_trains'] = sum_data['total_trains']
        return Response(data)


@method_decorator([api_recorder], name="dispatch")
class WmsInventoryStockView(APIView):
    """WMS库存货位信息，参数：material_name=原材料名称&material_no=原材料编号&quality_status=品质状态1合格3不合格&entrance_name=出库口名称"""
    DATABASE_CONF = WMS_CONF

    def get(self, request, *args, **kwargs):
        material_name = self.request.query_params.get('material_name')
        material_no = self.request.query_params.get('material_no')
        quality_status = self.request.query_params.get('quality_status')
        entrance_name = self.request.query_params.get('entrance_name')
        position = self.request.query_params.get('position')
        page = self.request.query_params.get('page', 1)
        page_size = self.request.query_params.get('page_size', 15)
        st = (int(page) - 1) * int(page_size)
        et = int(page) * int(page_size)
        extra_where_str = ""
        if not entrance_name:
            raise ValidationError('请选择出库口！')
        if material_name:
            extra_where_str += " and c.Name like '%{}%'".format(material_name)
        if material_no:
            extra_where_str += " and c.MaterialCode like '%{}%'".format(material_no)
        if quality_status:
            extra_where_str += " and a.StockDetailState={}".format(quality_status)
        sql = """SELECT
                 a.StockDetailState,
                 c.MaterialCode,
                 c.Name AS MaterialName,
                 a.BatchNo,
                 a.SpaceId,
                 a.Sn,
                 a.WeightUnit,
                 a.CreaterTime
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
                     WHERE ac.name= '{}' ) {} order by a.CreaterTime""".format(entrance_name, extra_where_str)
        sc = SqlClient(sql=sql, **self.DATABASE_CONF)
        temp = sc.all()
        if position == '内':
            temp = list(filter(lambda x: x[4][6] in ('1', '2'), temp))
        elif position == '外':
            temp = list(filter(lambda x: x[4][6] in ('3', '4'), temp))
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
                 'Sn': item[5],
                 'unit': item[6],
                 'inventory_time': item[7],
                 'position': '内' if item[4][6] in ('1', '2') else '外'
                 })
        sc.close()
        return Response({'results': result, "count": count})


@method_decorator([api_recorder], name="dispatch")
class WmsInStockView(APIView):
    """根据当前货物外伸位地址获取内伸位数据, 参数：entrance_name=出库口名称&space_id=货位地址"""
    DATABASE_CONF = WMS_CONF

    def get(self, request):
        out_space_id = self.request.query_params.get('space_id')
        entrance_name = self.request.query_params.get('entrance_name')
        if not all([out_space_id, entrance_name]):
            raise ValidationError('参数缺失！')
        out_space_id_list = out_space_id.split('-')
        if out_space_id_list[2] == '3':
            out_space_id_list[2] = '1'
        elif out_space_id_list[2] == '4':
            out_space_id_list[2] = '2'
        else:
            return Response([])
        in_space_id = '-'.join(out_space_id_list)
        sql = """
            SELECT
                 a.StockDetailState,
                 c.MaterialCode,
                 c.Name AS MaterialName,
                 a.BatchNo,
                 a.SpaceId,
                 a.Sn,
                 a.WeightUnit,
                 a.CreaterTime
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
                 WHERE ac.name= '{}')
             and a.SpaceId in ('{}', '{}');""".format(
            entrance_name, in_space_id, out_space_id)
        sc = SqlClient(sql=sql, **self.DATABASE_CONF)
        temp = sc.all()
        if len(temp) <= 1:
            return Response([])
        result = []
        for item in temp:
            result.append(
                {'StockDetailState': item[0],
                 'MaterialCode': item[1],
                 'MaterialName': item[2],
                 'BatchNo': item[3],
                 'SpaceId': item[4],
                 'Sn': item[5],
                 'unit': item[6],
                 'inventory_time': item[7],
                 'position': '内' if item[4][6] in ('1', '2') else '外'
                 })
        sc.close()
        return Response(result)


@method_decorator([api_recorder], name="dispatch")
class WMSRelease(APIView):
    permission_classes = (IsAuthenticated, )
    REQUEST_URL = WMS_URL

    def post(self, request):
        operation_type = self.request.data.get('operation_type')  # 1:放行 2:合格
        tracking_nums = self.request.data.get('tracking_nums')
        if not all([operation_type, tracking_nums]):
            raise ValidationError('参数不足！')
        if not isinstance(tracking_nums, list):
            raise ValidationError('参数错误！')
        data = {
            "TestingType": 1,
            "AllCheckDetailList": []
        }
        release_log_list = []
        for tracking_num in tracking_nums:
            if not tracking_num:
                continue
            data['AllCheckDetailList'].append({
                "TrackingNumber": tracking_num,
                "CheckResult": 1
            })
            release_log_list.append(WMSReleaseLog(**{'tracking_num': tracking_num,
                                                     'operation_type': operation_type,
                                                     'created_user': self.request.user}))
        headers = {"Content-Type": "application/json ;charset=utf-8"}
        try:
            r = requests.post(self.REQUEST_URL + '/MESApi/UpdateTestingResult', json=data, headers=headers,
                              timeout=5)
            r = r.json()
        except Exception as e:
            raise ValidationError('服务错误！')
        resp_status = r.get('state')
        if not resp_status == 1:
            raise ValidationError('请求失败！{}'.format(r.get('msg')))
        WMSReleaseLog.objects.bulk_create(release_log_list)
        return Response('更新成功！')


@method_decorator([api_recorder], name="dispatch")
class WMSExpireListView(APIView):
    permission_classes = (IsAuthenticated,)
    DATABASE_CONF = WMS_CONF

    def get(self, request):
        expire_days = self.request.query_params.get('expire_days', 30)
        page = self.request.query_params.get('page', 1)
        page_size = self.request.query_params.get('page_size', 15)
        st = (int(page) - 1) * int(page_size)
        et = int(page) * int(page_size)
        sql = """select
       m.MaterialCode,
       m.Name,
       sum(a.WeightOfActual) as weight,
       count(a.Quantity) as quality,
       a.StockDetailState,
       m.StandardUnit
from t_inventory_stock a
inner join t_inventory_material m on m.MaterialCode=a.MaterialCode
where m.IsValidity=1 and m.Validity - datediff(day ,a.CreaterTime, getdate()) <={}
group by m.MaterialCode,
         m.Name,
         m.StandardUnit,
         a.StockDetailState
order by m.MaterialCode;""".format(expire_days)
        sc = SqlClient(sql=sql, **self.DATABASE_CONF)
        temp = sc.all()
        count = len(temp)
        result = []
        data = temp[st:et]
        total_weight = sum([i[2] for i in temp])
        total_quantity = sum([i[3] for i in temp])
        for item in data:
            result.append(
                {'MaterialCode': item[0],
                 'MaterialName': item[1],
                 'WeightOfActual': item[2],
                 'quantity': item[3],
                 'quality_status': item[4],
                 'unit': item[5]
                 })
        sc.close()
        return Response({'results': result, "count": count, 'total_weight': total_weight, 'total_quantity': total_quantity})


@method_decorator([api_recorder], name="dispatch")
class WMSExpireDetailView(APIView):
    permission_classes = (IsAuthenticated,)
    DATABASE_CONF = WMS_CONF
    FILE_NAME = '库位明细'

    def export_xls(self, result):
        response = HttpResponse(content_type='application/vnd.ms-excel')
        filename = self.FILE_NAME
        response['Content-Disposition'] = u'attachment;filename= ' + filename.encode('gbk').decode(
            'ISO-8859-1') + '.xls'
        # 创建一个文件对象
        wb = xlwt.Workbook(encoding='utf8')
        # 创建一个sheet对象
        sheet = wb.add_sheet('出入库信息', cell_overwrite_ok=True)
        style = xlwt.XFStyle()
        style.alignment.wrap = 1
        columns = ['序号', '物料名称', '物料编码', '质检条码', '托盘号', '库存位', '库存数',
                   '单位', '单位重量', '总重量', '品质状态', '入库时间', '有效期至', '剩余有效天数']
        for col_num in range(len(columns)):
            sheet.write(0, col_num, columns[col_num])
            # 写入数据
        data_row = 1
        for i in result:
            sheet.write(data_row, 0, result.index(i) + 1)
            sheet.write(data_row, 1, i[0])
            sheet.write(data_row, 2, i[1])
            sheet.write(data_row, 3, i[2])
            sheet.write(data_row, 4, i[3])
            sheet.write(data_row, 5, i[4])
            sheet.write(data_row, 6, i[5])
            sheet.write(data_row, 7, i[6])
            sheet.write(data_row, 8, i[7])
            sheet.write(data_row, 9, i[7])
            sheet.write(data_row, 10, i[8])
            sheet.write(data_row, 11, i[9])
            sheet.write(data_row, 12, i[10])
            sheet.write(data_row, 13, i[11])
            data_row = data_row + 1
        # 写出到IO
        output = BytesIO()
        wb.save(output)
        # 重新定位到开始
        output.seek(0)
        response.write(output.getvalue())
        return response

    def get(self, request):
        expire_days = self.request.query_params.get('expire_days', 30)
        quality_status = self.request.query_params.get('quality_status')
        material_code = self.request.query_params.get('material_code')
        export = self.request.query_params.get('export')
        page = self.request.query_params.get('page', 1)
        page_size = self.request.query_params.get('page_size', 15)
        st = (int(page) - 1) * int(page_size)
        et = int(page) * int(page_size)
        if not all([expire_days, quality_status, material_code]):
            raise ValidationError('参数不足！')
        sql = """select
       a.MaterialName,
       a.MaterialCode,
       a.TrackingNumber,
       a.LadenToolNumber,
       a.SpaceId,
       a.Quantity,
       a.WeightUnit,
       a.WeightOfActual,
       a.StockDetailState,
       a.CreaterTime,
       dateadd(dd,m.Validity,a.CreaterTime) as expire_time,
       m.Validity - datediff(day ,a.CreaterTime, getdate()) as left_days
from t_inventory_stock a
inner join t_inventory_material m on m.MaterialCode=a.MaterialCode
where m.IsValidity=1
  and m.Validity - datediff(day ,a.CreaterTime, getdate()) <= {}
  and m.MaterialCode='{}'
  and a.StockDetailState={}
order by left_days;""".format(expire_days, material_code, quality_status)
        sc = SqlClient(sql=sql, **self.DATABASE_CONF)
        temp = sc.all()
        if export == '2':
            return self.export_xls(list(temp))
        elif export == '1':
            return self.export_xls(list(temp[st:et]))

        count = len(temp)
        result = []
        data = temp[st:et]
        total_weight = sum([i[7] for i in temp])
        total_quantity = sum([i[5] for i in temp])
        for item in data:
            result.append(
                {
                 'material_name': item[0],
                 'material_no': item[1],
                 'lot_no': item[2],
                 'container_no': item[3],
                 'location': item[4],
                 'qty': item[5],
                 'unit': item[6],
                 'total_weight': item[7],
                 'quality_status': item[8],
                 'in_storage_time': item[9],
                 'expire_time': item[10],
                 'left_days': item[11],
                 })
        sc.close()
        return Response({'results': result, "count": count, 'total_weight': total_weight, 'total_quantity': total_quantity})


@method_decorator([api_recorder], name="dispatch")
class WmsInventoryWeightStockView(APIView):
    """WMS库存货位信息，参数：material_name=原材料名称&material_no=原材料编号&quality_status=品质状态1合格3不合格&entrance_name=出库口名称"""
    DATABASE_CONF = WMS_CONF

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
                 SUM ( a.WeightOfActual ) AS WeightOfActual,
                 SUM ( a.Quantity ) AS quantity,
                 Min ( a.WeightOfActual ) AS min_quantity,
                 a.StockDetailState
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
                 c.Name,
                 a.StockDetailState
                 order by c.MaterialCode;""".format(entrance_name, extra_where_str)
        sc = SqlClient(sql=sql, **self.DATABASE_CONF)
        temp = sc.all()
        count = len(temp)
        result = []
        for item in temp:
            if item[3] <= 1:
                avg_weight = round(item[2] / item[3], 2)
            else:
                avg_weight = round((item[2] - item[4]) / (item[3] - 1), 2)
            result.append(
                {'MaterialCode': item[0],
                 'MaterialName': item[1],
                 'WeightOfActual': item[2],
                 'quantity': item[3],
                 'avg_weight': avg_weight,
                 'quality_status': item[5]
                 })
        sc.close()
        return Response({'results': result, "count": count})


@method_decorator([api_recorder], name="dispatch")
class InventoryEntranceView(APIView):
    """获取所有出库口名称"""
    DATABASE_CONF = WMS_CONF

    def get(self, request):
        sql = 'select name, EntranceCode from t_inventory_entrance where Type=2;'
        sc = SqlClient(sql=sql, **self.DATABASE_CONF)
        temp = sc.all()
        result = []
        for item in temp:
            result.append(
                {'name': item[0],
                 'code': item[1],
                 })
        sc.close()
        return Response(result)


@method_decorator([api_recorder], name="dispatch")
class WMSMaterialGroupNameView(APIView):
    """获取所有原材料库物料组名称"""
    DATABASE_CONF = WMS_CONF

    def get(self, request):
        sql = 'select Name from t_inventory_material_group;'
        sc = SqlClient(sql=sql, **self.DATABASE_CONF)
        temp = sc.all()
        result = []
        for item in temp:
            result.append(
                {'name': item[0]})
        sc.close()
        return Response(result)


@method_decorator([api_recorder], name="dispatch")
class WMSTunnelView(APIView):
    """获取所有原材料库巷道名称"""
    DATABASE_CONF = WMS_CONF

    def get(self, request):
        sql = 'select TunnelName from t_inventory_tunnel;'
        sc = SqlClient(sql=sql, **self.DATABASE_CONF)
        temp = sc.all()
        result = []
        for item in temp:
            result.append(
                {'name': item[0]})
        sc.close()
        return Response(result)


@method_decorator([api_recorder], name="dispatch")
class WMSInventoryView(APIView):
    """原材料库存信息，material_name=原材料名称&material_no=原材料编号&material_group_name=物料组名称&tunnel_name=巷道名称&page=页数&page_size=每页数量"""
    DATABASE_CONF = WMS_CONF
    FILE_NAME = '原材料库存统计'

    def export_xls(self, result):
        response = HttpResponse(content_type='application/vnd.ms-excel')
        filename = self.FILE_NAME
        response['Content-Disposition'] = u'attachment;filename= ' + filename.encode('gbk').decode(
            'ISO-8859-1') + '.xls'
        # 创建一个文件对象
        wb = xlwt.Workbook(encoding='utf8')
        # 创建一个sheet对象
        sheet = wb.add_sheet('出入库信息', cell_overwrite_ok=True)
        style = xlwt.XFStyle()
        style.alignment.wrap = 1
        columns = ['序号', '物料名称', '物料编码', '中策物料编码', '批次号', '单位', 'PDM',
                   '物料组', '巷道', '可用数量', '重量']
        for col_num in range(len(columns)):
            sheet.write(0, col_num, columns[col_num])
            # 写入数据
        data_row = 1
        for i in result:
            sheet.write(data_row, 0, result.index(i) + 1)
            sheet.write(data_row, 1, i[0])
            sheet.write(data_row, 2, i[1])
            sheet.write(data_row, 3, i[2])
            sheet.write(data_row, 4, i[9])
            sheet.write(data_row, 5, i[3])
            sheet.write(data_row, 6, i[4])
            sheet.write(data_row, 7, i[5])
            sheet.write(data_row, 8, i[6])
            sheet.write(data_row, 9, i[7])
            sheet.write(data_row, 10, i[8])
            data_row = data_row + 1
        # 写出到IO
        output = BytesIO()
        wb.save(output)
        # 重新定位到开始
        output.seek(0)
        response.write(output.getvalue())
        return response

    def get(self, request):
        material_name = self.request.query_params.get('material_name')
        material_no = self.request.query_params.get('material_no')
        material_group_name = self.request.query_params.get('material_group_name')
        tunnel_name = self.request.query_params.get('tunnel_name')
        page = self.request.query_params.get('page', 1)
        page_size = self.request.query_params.get('page_size', 15)
        export = self.request.query_params.get('export')
        st = (int(page) - 1) * int(page_size)
        et = int(page) * int(page_size)
        extra_where_str = ""
        if material_name:
            extra_where_str += "where temp.Name like '%{}%'".format(material_name)
        if material_no:
            if extra_where_str:
                extra_where_str += " and temp.MaterialCode like '%{}%'".format(material_no)
            else:
                extra_where_str += "where temp.MaterialCode like '%{}%'".format(material_no)
        if material_group_name:
            if extra_where_str:
                extra_where_str += " and m.MaterialGroupName='{}'".format(material_group_name)
            else:
                extra_where_str += "where m.MaterialGroupName='{}'".format(material_group_name)
        if tunnel_name:
            if extra_where_str:
                extra_where_str += " and temp.TunnelName='{}'".format(tunnel_name)
            else:
                extra_where_str += "where temp.TunnelName='{}'".format(tunnel_name)
        sql = """
                select
            temp.MaterialName,
            temp.MaterialCode,
            m.ZCMaterialCode,
            temp.WeightUnit,
            m.Pdm,
            m.MaterialGroupName,
            temp.TunnelName,
            temp.quantity,
            temp.WeightOfActual,
            temp.BatchNo
        from (
            select
                a.MaterialCode,
                a.MaterialName,
                a.BatchNo,
                d.TunnelName,
                a.WeightUnit,
                SUM ( a.WeightOfActual ) AS WeightOfActual,
                SUM ( a.Quantity ) AS quantity
            from dbo.t_inventory_stock AS a
            INNER JOIN t_inventory_tunnel d ON d.TunnelCode= a.TunnelId
            group by
                 a.MaterialCode,
                 a.MaterialName,
                 d.TunnelName,
                 a.BatchNo,
                 a.WeightUnit
            ) temp
        left join t_inventory_material m on m.MaterialCode=temp.MaterialCode {}""".format(extra_where_str)
        sc = SqlClient(sql=sql, **self.DATABASE_CONF)
        temp = sc.all()

        if export == '2':
            return self.export_xls(list(temp))
        elif export == '1':
            return self.export_xls(list(temp[st:et]))

        count = len(temp)
        total_quantity = total_weight = 0
        for i in temp:
            total_quantity += i[7]
            total_weight += i[8]
        temp = temp[st:et]
        result = []
        for item in temp:
            result.append(
                {'name': item[0],
                 'code': item[1],
                 'zc_material_code': item[2],
                 'unit': item[3],
                 'pdm': item[4],
                 'group_name': item[5],
                 'tunnel_name': item[6],
                 'quantity': item[7],
                 'weight': item[8],
                 'batch_no': item[9]
                 })
        sc.close()
        return Response(
            {'results': result, "count": count, 'total_quantity': total_quantity, 'total_weight': total_weight})


@method_decorator([api_recorder], name="dispatch")
class THStorageSummaryView(WmsStorageSummaryView):
    """
        炭黑库存统计列表（按物料编码、品质状态、单位、批次号分组统计）
        参数：?material_name=物料名称&material_no=物料编码&zc_material_code=中策物料编码&batch_no=批次号&pdm_no=PDM号&st=入库开始时间&et=入库结束时间&quality_status=# 品质状态 1：合格 3：不合格
    """
    DATABASE_CONF = TH_CONF


@method_decorator([api_recorder], name="dispatch")
class THStorageView(WmsStorageView):
    DATABASE_CONF = 'cb'
    FILE_NAME = '炭黑库位明细'


@method_decorator([api_recorder], name="dispatch")
class THInventoryStockView(WmsInventoryStockView):
    """炭黑库存货位信息，参数：material_name=原材料名称&material_no=原材料编号&quality_status=品质状态1合格3不合格&entrance_name=出库口名称"""
    DATABASE_CONF = TH_CONF


@method_decorator([api_recorder], name="dispatch")
class THInStockView(WmsInStockView):
    """炭黑库根据当前货物外伸位地址获取内伸位数据, 参数：material_no=原材料编号&entrance_name=出库口名称&space_id=货位地址"""
    DATABASE_CONF = TH_CONF


@method_decorator([api_recorder], name="dispatch")
class THInventoryWeightStockView(WmsInventoryWeightStockView):
    """炭黑库存货位信息，参数：material_name=原材料名称&material_no=原材料编号&quality_status=品质状态1合格3不合格&entrance_name=出库口名称"""
    DATABASE_CONF = TH_CONF


@method_decorator([api_recorder], name="dispatch")
class THInventoryEntranceView(InventoryEntranceView):
    """获取所有炭黑出库口名称"""
    DATABASE_CONF = TH_CONF


@method_decorator([api_recorder], name="dispatch")
class THMaterialGroupNameView(WMSMaterialGroupNameView):
    """获取炭黑库所有物料组名称"""
    DATABASE_CONF = TH_CONF


@method_decorator([api_recorder], name="dispatch")
class THTunnelView(WMSTunnelView):
    """获取炭黑库所有巷道名称"""
    DATABASE_CONF = TH_CONF


@method_decorator([api_recorder], name="dispatch")
class THInventoryView(WMSInventoryView):
    """炭黑库存信息"""
    DATABASE_CONF = TH_CONF
    FILE_NAME = '炭黑库存统计'


@method_decorator([api_recorder], name="dispatch")
class THRelease(WMSRelease):
    REQUEST_URL = TH_URL


@method_decorator([api_recorder], name="dispatch")
class THExpireListView(WMSExpireListView):
    DATABASE_CONF = TH_CONF


@method_decorator([api_recorder], name="dispatch")
class THExpireDetailView(WMSExpireDetailView):
    DATABASE_CONF = TH_CONF


@method_decorator([api_recorder], name="dispatch")
class DepotModelViewSet(ModelViewSet):
    """线边库库区"""
    queryset = Depot.objects.filter(is_use=True)
    serializer_class = DepotModelSerializer
    permission_classes = [IsAuthenticated, ]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'depot_name')
            return Response({'results': data})
        return super().list(self, request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        s = DepotPallt.objects.filter(depot_site__depot=instance, pallet_status=1).first()  # True不能删
        if not s:
            instance.is_use = 0
            DepotSite.objects.filter(depot=instance).update(is_use=0)
            instance.save()
        else:
            raise ValidationError('该库区下存在物料,不能删除!')
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name="dispatch")
class DepotSiteModelViewSet(ModelViewSet):
    """线边库库位"""
    queryset = DepotSite.objects.filter(is_use=True)
    serializer_class = DepotSiteModelSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]
    filter_class = DepotSiteDataFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'depot_site_name', 'description', 'depot', 'depot__depot_name')
            return Response({'results': data})
        elif request.query_params.get('depot_site'):
            data = DepotSite.objects.filter(is_use=True).values('id', 'depot_site_name', 'depot')
            return Response({'results': data})
        return super().list(self, request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        s = DepotPallt.objects.filter(depot_site=instance, pallet_status=1).first()  # True不能删
        if not s:
            instance.is_use = 0
            instance.save()
        else:
            raise ValidationError('该库位下存在物料,不能删除!')
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name="dispatch")
class DepotPalltModelViewSet(ModelViewSet):
    """线边库库存查询"""
    queryset = DepotPallt.objects.filter(pallet_status=1).order_by('-enter_time')
    serializer_class = DepotPalltModelSerializer
    permission_classes = [IsAuthenticated, ]
    filter_backends = [DjangoFilterBackend]
    filter_class = DepotDataFilter

    def list(self, request, *args, **kwargs):
        results = PalletFeedbacks.objects.filter(palletfeedbacks__pallet_status=1).values('product_no').annotate(
            num=Count('product_no'),
            trains=Sum(F('end_trains') - F('begin_trains') + 1),
            actual_weight=Sum('actual_weight')
        )
        return Response({'results': results})


@method_decorator([api_recorder], name="dispatch")
class DepotPalltInfoModelViewSet(ModelViewSet):
    """库存查询详情"""
    queryset = DepotPallt.objects.filter(pallet_status=1)
    serializer_class = DepotPalltInfoModelSerializer
    permission_classes = [IsAuthenticated, ]
    filter_backends = [DjangoFilterBackend]
    filter_class = DepotDataFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@method_decorator([api_recorder], name='dispatch')
class PalletTestResultView(APIView):
    """查询某拖收皮数据的检测结果，参数:lot_no=xxx"""

    def get(self, request):
        lot_no = self.request.query_params.get('lot_no')
        if not lot_no:
            raise ValidationError('参数缺失')
        # {
        #     '门尼': ['ML(1+4)'],
        #     '流变': ['MH', 'ML', 'TC10'],
        #     '比重': ['比重值']
        # }
        # [
        #     {
        #         'trains': 1,
        #         'level': 1,  # 等级
        #         'test_data': {
        #                     '门尼': {
        #                         'ML(1+4)': 66,
        #
        #                     },
        #                     '流变': {
        #                         'MH': 55,
        #                         'ML': 99,
        #                         'TC10': 12,
        #                     }
        #                 }
        #     },
        #     {
        #         'trains': 2,
        #         'level': 1,
        #         'test_data': {
        #             '门尼': {
        #                 'ML(1+4)': 66,
        #
        #             },
        #         }
        #     }
        # ]
        ret = []
        mdr_obj = MaterialDealResult.objects.filter(lot_no=lot_no).exclude(status='复测').last()
        if mdr_obj:
            serializers = MaterialDealResultListSerializer(instance=mdr_obj)
            deal_result = serializers.data
        else:
            return Response([])
        table_head = deal_result['mtr_list']['table_head']
        mtr_list = deal_result['mtr_list']
        mtr_list.pop('table_head', None)
        test_result = deal_result['test_result']
        for item in mtr_list['trains']:
            data = {}
            data['trains'] = item['train']
            data['test_data'] = {}
            for j in item['content']:
                data['status'] = j.get('status')
                test_indicator_name = j['test_indicator_name']
                data_point_name = j['data_point_name']
                value = j['value']
                if test_indicator_name in data['test_data']:
                    data['test_data'][test_indicator_name][data_point_name] = value
                else:
                    data['test_data'][test_indicator_name] = {data_point_name: value}
            ret.append(data)

        return Response({'table_head': table_head, 'results': ret, 'test_result': test_result})


@method_decorator([api_recorder], name="dispatch")
class PalletDataModelViewSet(ModelViewSet):
    """线边库出入库管理"""
    queryset = PalletFeedbacks.objects.exclude(palletfeedbacks__pallet_status=2).order_by('-product_time')
    serializer_class = PalletDataModelSerializer
    permission_classes = [IsAuthenticated, ]
    filter_backends = [DjangoFilterBackend]
    filter_class = PalletDataFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            for i in serializer.data:
                s = ProductClassesPlan.objects.filter(plan_classes_uid=i['plan_classes_uid']).values(
                    'work_schedule_plan__group__global_name').first()
                i.update({'group': s['work_schedule_plan__group__global_name']})
            if request.query_params.get('group'):
                group = request.query_params.get('group')
                data = [i for i in serializer.data if i['group'].startswith(group)]
                return self.get_paginated_response(data)
            elif request.query_params.get('all'):
                data = PalletFeedbacks.objects.filter(delete_flag=False).values('product_no').distinct()
                return Response({'results': data})
            else:
                return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        pallet_id = request.data.get('id')
        pallet_status = request.data.get('status')
        enter_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        depot_site = request.data.get('depot_site')
        depot_pallet_id = request.data.get('depot_pallet_id')
        depot_site_obj = DepotSite.objects.filter(id=depot_site).first()
        pallet_data_obj = PalletFeedbacks.objects.get(pk=pallet_id)

        if pallet_status == 1:  # 入库
            data_obj = DepotPallt.objects.create(pallet_data=pallet_data_obj, depot_site=depot_site_obj,
                                                 enter_time=enter_time,
                                                 pallet_status=pallet_status)
            data = PalletFeedbacks.objects.filter(palletfeedbacks=data_obj).first()
        elif pallet_status == 2:  # 出库
            DepotPallt.objects.filter(id=depot_pallet_id).update(pallet_status=2, outer_time=datetime.datetime.now())
            data_obj = DepotPallt.objects.filter(id=depot_pallet_id).first()
            data = PalletFeedbacks.objects.filter(palletfeedbacks=data_obj).first()
        serializer = PalletDataModelSerializer(instance=data)
        return Response({"result": serializer.data})


@method_decorator([api_recorder], name="dispatch")
class DepotResumeModelViewSet(ModelViewSet):
    """线边库出入库履历"""
    queryset = DepotPallt.objects.all().order_by('-enter_time')
    serializer_class = DepotResumeModelSerializer
    permission_classes = [IsAuthenticated, ]
    filter_backends = [DjangoFilterBackend]
    filter_class = DepotResumeFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            for i in serializer.data:
                s = ProductClassesPlan.objects.filter(plan_classes_uid=i['plan_classes_uid']).values(
                    'work_schedule_plan__group__global_name').first()
                i.update({'group': s['work_schedule_plan__group__global_name']})

            if request.query_params.get('group'):
                group = request.query_params.get('group')
                data = [i for i in serializer.data if i['group'].startswith(group)]
                return self.get_paginated_response(data)

            elif request.query_params.get('all'):
                data = DepotPallt.objects.values('pallet_data__product_no').annotate(
                    num=Count('pallet_data__product_no'))
                return Response({'results': data})
            else:
                return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@method_decorator([api_recorder], name="dispatch")
class SulfurDepotModelViewSet(ModelViewSet):
    """硫磺库库区"""
    queryset = SulfurDepot.objects.filter(is_use=True)
    serializer_class = SulfurDepotModelSerializer
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'depot_name')
            return Response({'results': data})
        return super().list(self, request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        s = Sulfur.objects.filter(depot_site__depot=instance, sulfur_status=1).first()
        if not s:
            instance.is_use = 0
            SulfurDepotSite.objects.filter(depot=instance).update(is_use=0)
            instance.save()
        else:
            raise ValidationError('该库区下存在物料,不能删除!')
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name="dispatch")
class SulfurDepotSiteModelViewSet(ModelViewSet):
    """硫磺库库位"""
    queryset = SulfurDepotSite.objects.filter(is_use=True)
    serializer_class = SulfurDepotSiteModelSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]
    filter_class = SulfurDepotSiteFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'depot_site_name', 'depot', 'depot__depot_name', 'description')
            return Response({'results': data})
        elif request.query_params.get('depot_site'):
            data = SulfurDepotSite.objects.filter(is_use=True).values('id', 'depot_site_name', 'depot')
            return Response({'results': data})
        return super().list(self, request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        s = Sulfur.objects.filter(depot_site=instance, sulfur_status=1).first()
        if not s:
            instance.is_use = 0
            instance.save()
        else:
            raise ValidationError('该库区下存在物料,不能删除!')
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name="dispatch")
class SulfurDataModelViewSet(ModelViewSet):
    """硫磺库出入库管理"""
    queryset = Sulfur.objects.filter(sulfur_status=1).order_by('-enter_time')
    serializer_class = SulfurDataModelSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]
    filter_class = SulfurDataFilter

    def list(self, request, *args, **kwargs):
        name = self.request.query_params.get('_name')
        product_no = self.request.query_params.get('_product_no')
        provider = self.request.query_params.get('_provider')
        if name:
            queryset = Sulfur.objects.filter(name__icontains=name).values('name').distinct()
        elif product_no:
            queryset = Sulfur.objects.filter(product_no__icontains=product_no).values('product_no').distinct()
        elif provider:
            queryset = Sulfur.objects.filter(provider__icontains=provider).values('provider').distinct()
        else:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        return Response(queryset)

    # 硫磺人工入库
    def create(self, request, *args, **kwargs):
        if request.data.get('sulfur_status') == 1:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            try:
                depot_site_obj = SulfurDepotSite.objects.get(pk=request.data.get('depot_site'))
            except:
                raise ValidationError('该库位不存在')

            enter_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            data = Sulfur.objects.filter(depot_site=depot_site_obj, lot_no=serializer.data.get('lot_no'),
                                         name=serializer.data.get('name'),
                                         product_no=serializer.data.get('product_no'),
                                         provider=serializer.data.get('provider'),
                                         ).first()
            weight = float(serializer.data.get('weight'))
            num = int(serializer.data.get('num'))
            if data:
                data.num += num
                data.weight += decimal.Decimal(weight * num)
                data.enter_time = enter_time
                data.save()
            else:
                serializer.data.update({'weight': weight * num})
                data = Sulfur.objects.create(**serializer.data, depot_site=depot_site_obj, enter_time=enter_time)

            serializer = SulfurDataModelSerializer(instance=data)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif request.data.get('sulfur_status') == 2:
            num = request.data.get('num')
            try:
                num = int(num)
            except:
                raise ValidationError('您输入的数量有误')
            obj = Sulfur.objects.filter(id=request.data.get('id')).first()
            if num > obj.num:
                raise ValidationError(f"库存数量为{obj.num}！")
            outer_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            obj.sulfur_status = 1 if num < obj.num else 2
            obj.num -= num
            obj.outer_time = outer_time
            obj.save()
            return Response({'results': '出库成功'})


@method_decorator([api_recorder], name="dispatch")
class DepotSulfurModelViewSet(ModelViewSet):
    """硫磺库库存查询"""
    queryset = Sulfur.objects.filter(sulfur_status=1)
    serializer_class = DepotSulfurModelSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]
    filter_class = DepotSulfurFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        lst = []
        for i in serializer.data:
            lst.append(
                {'name': i['name'], 'product_no': i['product_no'], 'provider': i['provider'], 'lot_no': i['lot_no'],
                 'num': i['num']})
        c = {i['name']: {} for i in lst}
        for i in lst:
            if not c[i['name']]:
                c[i['name']].update(i)
            else:
                c[i['name']]['num'] += i['num']
        return Response({'results': c.values()})


@method_decorator([api_recorder], name="dispatch")
class DepotSulfurInfoModelViewSet(ModelViewSet):
    """硫磺库库存查询详情"""
    queryset = Sulfur.objects.filter(sulfur_status=1)
    serializer_class = DepotSulfurInfoModelSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]
    filter_class = DepotSulfurFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@method_decorator([api_recorder], name="dispatch")
class SulfurResumeModelViewSet(ModelViewSet):
    """硫磺库出入库履历"""
    queryset = Sulfur.objects.all().order_by('-enter_time')
    serializer_class = SulfurResumeModelSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]
    filter_class = SulfurResumeFilter


@method_decorator([api_recorder], name="dispatch")
class BzMixingRubberInventory(ListAPIView):
    """
        北自混炼胶库存列表，参数：?material_no=物料编码&container_no=托盘号&lot_no=收皮条码&location=库存位
                            &tunnel=巷道&quality_status=品质状态&lot_existed=收皮条码有无（1：有，0：无）
                            &station=出库口名称&st=入库开始时间&et=入库结束时间
    """
    serializer_class = BzFinalMixingRubberInventorySerializer
    permission_classes = (IsAuthenticated,)
    queryset = BzFinalMixingRubberInventory.objects.all()

    def export_xls(self, result):
        response = HttpResponse(content_type='application/vnd.ms-excel')
        filename = '库位明细'
        response['Content-Disposition'] = u'attachment;filename= ' + filename.encode('gbk').decode(
            'ISO-8859-1') + '.xls'
        # 创建一个文件对象
        wb = xlwt.Workbook(encoding='utf8')
        # 创建一个sheet对象
        sheet = wb.add_sheet('库存信息', cell_overwrite_ok=True)

        style = xlwt.XFStyle()
        style.alignment.wrap = 1
        columns = ['No', '胶料类型', '胶料编码', '质检条码', '货位状态', '生产机台', '生产班次',
                   '托盘号', '库位地址', '数库存量', '单位', '单位重量', '总重量', '品质状态']
        for col_num in range(len(columns)):
            sheet.write(0, col_num, columns[col_num])
            # 写入数据
        data_row = 1
        for i in result:
            sheet.write(data_row, 0, data_row)
            sheet.write(data_row, 1, i['material_type'])
            sheet.write(data_row, 2, i['material_no'])
            sheet.write(data_row, 3, i['lot_no'])
            sheet.write(data_row, 4, i['location_status'])
            sheet.write(data_row, 5, i['product_info']['equip_no'])
            sheet.write(data_row, 6, i['product_info']['classes'])
            sheet.write(data_row, 7, i['container_no'])
            sheet.write(data_row, 8, i['location'])
            sheet.write(data_row, 9, i['qty'])
            sheet.write(data_row, 10, 'kg')
            sheet.write(data_row, 11, i['unit_weight'])
            sheet.write(data_row, 12, i['total_weight'])
            sheet.write(data_row, 13, i['quality_status'])
            data_row = data_row + 1
        # 写出到IO
        output = BytesIO()
        wb.save(output)
        # 重新定位到开始
        output.seek(0)
        response.write(output.getvalue())
        return response

    def list(self, request, *args, **kwargs):
        material_no = self.request.query_params.get('material_no')  # 物料编码
        container_no = self.request.query_params.get('container_no')  # 托盘号
        lot_no = self.request.query_params.get('lot_no')  # 收皮条码
        location = self.request.query_params.get('location')  # 库存位
        tunnel = self.request.query_params.get('tunnel')  # 巷道
        quality_status = self.request.query_params.get('quality_status')  # 品质状态
        lot_existed = self.request.query_params.get('lot_existed')  # 收皮条码有无（1：有，0：无）
        station = self.request.query_params.get('station')  # 出库口名称
        location_status = self.request.query_params.get('location_status')  # 货位状态
        st = self.request.query_params.get('st')  # 入库开始时间
        et = self.request.query_params.get('et')  # 入库结束时间
        export = self.request.query_params.get('export')  # 1：当前页面  2：所有
        queryset = BzFinalMixingRubberInventory.objects.using('bz').all().order_by('in_storage_time')
        if material_no:
            queryset = queryset.filter(material_no=material_no)
        if container_no:
            queryset = queryset.filter(container_no__icontains=container_no)
        if location:
            queryset = queryset.filter(location__icontains=location)
        if tunnel:
            queryset = queryset.filter(location__istartswith=tunnel)
        if lot_no:
            queryset = queryset.filter(lot_no__icontains=lot_no)
        if quality_status:
            queryset = queryset.filter(quality_level=quality_status)
        if location_status:
            queryset = queryset.filter(location_status=location_status)
        if st:
            queryset = queryset.filter(in_storage_time__gte=st)
        if et:
            queryset = queryset.filter(in_storage_time__lte=et)
        if lot_existed:
            if lot_existed == '1':
                queryset = queryset.exclude(lot_no__isnull=True)
            else:
                queryset = queryset.filter(lot_no__isnull=True)
        if station:
            if station == '一层前端':
                queryset = queryset.filter(Q(location__startswith='3') | Q(location__startswith='4'))
                # queryset = queryset.extra(where=["substring(货位地址, 0, 2) in (3, 4)"])
            elif station == '二层前端':
                queryset = queryset.filter(Q(location__startswith='1') | Q(location__startswith='2'))
                # queryset = queryset.extra(where=["substring(货位地址, 0, 2) in (1, 2)"])
            elif station == '一层后端':
                raise ValidationError('该出库口不可用！')
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        if export:
            if export == '1':
                return self.export_xls(serializer.data)
            elif export == '2':
                return self.export_xls(self.get_serializer(queryset, many=True).data)
        data = self.get_paginated_response(serializer.data).data
        sum_data = queryset.aggregate(total_weight=Sum('total_weight'),
                                      total_trains=Sum('qty'))
        data['total_weight'] = sum_data['total_weight']
        data['total_trains'] = sum_data['total_trains']
        return Response(data)


@method_decorator([api_recorder], name="dispatch")
class BzMixingRubberInventorySummary(APIView):
    """根据出库口获取混炼胶库存统计列表。参数：quality_status=品质状态&station=出库口名称&location_status=货位状态&lot_existed="""

    def get(self, request):
        params = request.query_params
        quality_status = params.get("quality_status")
        station = params.get("station")
        location_status = params.get("location_status")
        lot_existed = params.get("lot_existed")
        queryset = BzFinalMixingRubberInventory.objects.using('bz').all()
        if location_status:
            queryset = queryset.filter(location_status=location_status)
        if station:
            if station == '一层前端':
                queryset = queryset.filter(Q(location__startswith='3') | Q(location__startswith='4'))
                # queryset = queryset.extra(where=["substring(货位地址, 0, 2) in (3, 4)"])
            elif station == '二层前端':
                queryset = queryset.filter(Q(location__startswith='1') | Q(location__startswith='2'))
                # queryset = queryset.extra(where=["substring(货位地址, 0, 2) in (1, 2)"])
            elif station == '一层后端':
                return Response([])
        if quality_status:
            queryset = queryset.filter(quality_level=quality_status)
        if lot_existed:
            if lot_existed == '1':
                queryset = queryset.filter(lot_no__isnull=False)
            else:
                queryset = queryset.filter(lot_no__isnull=True)
        try:
            ret = queryset.values('material_no').annotate(all_qty=Sum('qty'),
                                                          all_weight=Sum('total_weight')
                                                          ).values('material_no', 'all_qty', 'all_weight')
        except Exception as e:
            raise ValidationError(f"混炼胶库连接失败:{e}")
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class BzMixingRubberInventorySearch(ListAPIView):
    """根据出库口、搜索指定数量的混炼胶库存信息.参数：?material_no=物料编码&quality_status=品质状态&station=出库口名称&need_qty=出库数量"""
    queryset = BzFinalMixingRubberInventory.objects.all()
    serializer_class = BzFinalMixingRubberInventorySerializer
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        material_no = self.request.query_params.get('material_no')  # 物料编码
        quality_status = self.request.query_params.get('quality_status')  # 品质状态
        station = self.request.query_params.get('station')  # 出库口名称
        need_qty = self.request.query_params.get('need_qty')  # 出库数量
        tunnel = self.request.query_params.get('tunnel')  # 巷道
        st = self.request.query_params.get('st')  # 入库开始时间
        et = self.request.query_params.get('et')  # 入库结束时间
        if not all([material_no, need_qty]):
            raise ValidationError('参数缺失！')
        try:
            need_qty = int(need_qty)
        except Exception:
            raise ValidationError('参数错误！')
        queryset = BzFinalMixingRubberInventory.objects.using('bz').filter(
            material_no=material_no,
            location_status="有货货位").order_by('in_storage_time')
        if station == '一层前端':
            queryset = queryset.filter(Q(location__startswith='3') | Q(location__startswith='4'))
            # queryset = queryset.extra(where=["substring(货位地址, 0, 2) in (3, 4)"])
        elif station == '二层前端':
            queryset = queryset.filter(Q(location__startswith='1') | Q(location__startswith='2'))
            # queryset = queryset.extra(where=["substring(货位地址, 0, 2) in (1, 2)"])
        elif station == '一层后端':
            raise ValidationError('该出库口不可用！')
        if quality_status:
            queryset = queryset.filter(quality_level=quality_status)
        if st:
            queryset = queryset.filter(in_storage_time__gte=st)
        if et:
            queryset = queryset.filter(in_storage_time__lte=et)
        if tunnel:
            queryset = queryset.filter(location__istartswith=tunnel)
        storage_quantity = 0
        ret = []
        for item in queryset:
            storage_quantity += item.qty
            ret.append(item)
            if storage_quantity >= need_qty:
                break
        serializer = self.get_serializer(ret, many=True)
        total_trains = queryset.aggregate(total_count=Sum('qty'))['total_count']
        return Response({'data': serializer.data, 'total_trains': total_trains if total_trains else 0})


@method_decorator([api_recorder], name="dispatch")
class BzFinalRubberInventory(ListAPIView):
    """
        终炼胶、帘布库存列表
    """
    serializer_class = BzFinalMixingRubberLBInventorySerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    queryset = BzFinalMixingRubberInventoryLB.objects.all()

    def export_xls(self, result):
        response = HttpResponse(content_type='application/vnd.ms-excel')
        filename = '库位明细'
        response['Content-Disposition'] = u'attachment;filename= ' + filename.encode('gbk').decode(
            'ISO-8859-1') + '.xls'
        # 创建一个文件对象
        wb = xlwt.Workbook(encoding='utf8')
        # 创建一个sheet对象
        sheet = wb.add_sheet('库存信息', cell_overwrite_ok=True)

        style = xlwt.XFStyle()
        style.alignment.wrap = 1
        columns = ['No', '胶料类型', '胶料编码', '质检条码', '货位状态', '生产机台', '生产班次',
                   '托盘号', '库位地址', '数库存量', '单位', '单位重量', '总重量', '品质状态']
        for col_num in range(len(columns)):
            sheet.write(0, col_num, columns[col_num])
            # 写入数据
        data_row = 1
        for i in result:
            sheet.write(data_row, 0, data_row)
            sheet.write(data_row, 1, i['material_type'])
            sheet.write(data_row, 2, i['material_no'])
            sheet.write(data_row, 3, i['lot_no'])
            sheet.write(data_row, 4, i['location_status'])
            sheet.write(data_row, 5, i['product_info']['equip_no'])
            sheet.write(data_row, 6, i['product_info']['classes'])
            sheet.write(data_row, 7, i['container_no'])
            sheet.write(data_row, 8, i['location'])
            sheet.write(data_row, 9, i['qty'])
            sheet.write(data_row, 10, 'kg')
            sheet.write(data_row, 11, i['unit_weight'])
            sheet.write(data_row, 12, i['total_weight'])
            sheet.write(data_row, 13, i['quality_status'])
            data_row = data_row + 1
        # 写出到IO
        output = BytesIO()
        wb.save(output)
        # 重新定位到开始
        output.seek(0)
        response.write(output.getvalue())
        return response

    def list(self, request, *args, **kwargs):
        filter_kwargs = {}
        store_name = self.request.query_params.get('store_name', '炼胶库')  # 仓库
        quality_status = self.request.query_params.get('quality_status', None)
        lot_existed = self.request.query_params.get('lot_existed')
        container_no = self.request.query_params.get('container_no')
        material_no = self.request.query_params.get('material_no')
        order_no = self.request.query_params.get('order_no')
        location = self.request.query_params.get('location')
        tunnel = self.request.query_params.get('tunnel')
        lot_no = self.request.query_params.get('lot_no')
        location_status = self.request.query_params.get('location_status')  # 货位状态
        st = self.request.query_params.get('st')  # 入库开始时间
        et = self.request.query_params.get('et')  # 入库结束时间
        export = self.request.query_params.get('export')  # 1：当前页面  2：所有
        if store_name:
            if store_name == '终炼胶库':
                store_name = "炼胶库"
            filter_kwargs['store_name'] = store_name
        if quality_status:
            filter_kwargs['quality_level'] = quality_status
        if lot_existed:
            if lot_existed == '1':
                filter_kwargs['lot_no__isnull'] = False
            else:
                filter_kwargs['lot_no__isnull'] = True
        if container_no:
            filter_kwargs['container_no__icontains'] = container_no
        if material_no:
            filter_kwargs['material_no'] = material_no
        if order_no:
            filter_kwargs['bill_id__icontains'] = container_no
        if location:
            filter_kwargs['location__icontains'] = location
        if tunnel:
            filter_kwargs['location__istartswith'] = tunnel
        if lot_no:
            filter_kwargs['lot_no__icontains'] = lot_no
        if location_status:
            filter_kwargs['location_status'] = location_status
        if st:
            filter_kwargs['in_storage_time__gte'] = st
        if et:
            filter_kwargs['in_storage_time__lte'] = et
        queryset = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(**filter_kwargs).order_by(
            'in_storage_time')

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        if export:
            if export == '1':
                return self.export_xls(serializer.data)
            elif export == '2':
                return self.export_xls(self.get_serializer(queryset, many=True).data)
        data = self.get_paginated_response(serializer.data).data
        sum_data = queryset.aggregate(total_weight=Sum('total_weight'),
                                      total_trains=Sum('qty'))
        data['total_weight'] = sum_data['total_weight']
        data['total_trains'] = sum_data['total_trains']
        return Response(data)


@method_decorator([api_recorder], name="dispatch")
class BzFinalRubberInventorySummary(APIView):
    """终炼胶库存、帘布库库存统计列表。参数：quality_status=品质状态&location_status=货位状态&store_name=炼胶库/帘布库&lot_existed=有无收皮条码"""

    def get(self, request):
        params = request.query_params
        quality_status = params.get("quality_status")
        location_status = params.get("location_status")
        store_name = params.get("store_name", '炼胶库')
        lot_existed = params.get("lot_existed")
        queryset = BzFinalMixingRubberInventoryLB.objects.using('lb').all()
        if location_status:
            queryset = queryset.filter(location_status="有货货位")
        if quality_status:
            queryset = queryset.filter(quality_level=quality_status)
        if store_name:
            if store_name == '终炼胶库':
                store_name = "炼胶库"
            queryset = queryset.filter(store_name=store_name)
        if lot_existed:
            if lot_existed == '1':
                queryset = queryset.filter(lot_no__isnull=False)
            else:
                queryset = queryset.filter(lot_no__isnull=True)
        try:
            ret = queryset.values('material_no').annotate(all_qty=Sum('qty'),
                                                          all_weight=Sum('total_weight')
                                                          ).values('material_no', 'all_qty', 'all_weight')
        except Exception as e:
            raise ValidationError(f"混炼胶库连接失败:{e}")
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class BzFinalRubberInventorySearch(ListAPIView):
    """根据出库口、搜索指定数量的终炼胶库存信息.参数：?material_no=物料编码&quality_status=品质状态&need_qty=出库数量"""
    queryset = BzFinalMixingRubberInventoryLB.objects.all()
    serializer_class = BzFinalMixingRubberLBInventorySerializer
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        material_no = self.request.query_params.get('material_no')  # 物料编码
        quality_status = self.request.query_params.get('quality_status')  # 品质状态
        need_qty = self.request.query_params.get('need_qty')  # 出库数量
        tunnel = self.request.query_params.get('tunnel')  # 巷道
        st = self.request.query_params.get('st')  # 入库开始时间
        et = self.request.query_params.get('et')  # 入库结束时间
        if not all([material_no, need_qty]):
            raise ValidationError('参数缺失！')
        try:
            need_qty = int(need_qty)
        except Exception:
            raise ValidationError('参数错误！')
        queryset = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(
            store_name="炼胶库",
            material_no=material_no,
            location_status="有货货位").order_by('in_storage_time')
        if quality_status:
            queryset = queryset.filter(quality_level=quality_status)
        if st:
            queryset = queryset.filter(in_storage_time__gte=st)
        if et:
            queryset = queryset.filter(in_storage_time__lte=et)
        if tunnel:
            queryset = queryset.filter(location__istartswith=tunnel)
        storage_quantity = 0
        ret = []
        for item in queryset:
            storage_quantity += item.qty
            ret.append(item)
            if storage_quantity >= need_qty:
                break
        serializer = self.get_serializer(ret, many=True)
        total_trains = queryset.aggregate(total_count=Sum('qty'))['total_count']
        return Response({'data': serializer.data, 'total_trains': total_trains if total_trains else 0})


@method_decorator([api_recorder], name="dispatch")
class OutBoundTasksListView(ListAPIView):
    """
        根据出库口过滤混炼、终炼出库任务列表，参数：warehouse_name=混炼胶库/终炼胶库&station_id=出库口id
    """
    serializer_class = OutBoundTasksSerializer

    def get_queryset(self):
        warehouse_name = self.request.query_params.get('warehouse_name')  # 库存名称
        station_id = self.request.query_params.get('station_id')  # 出库口名称
        try:
            station = Station.objects.get(id=station_id).name
        except Exception:
            raise ValidationError('参数错误')
        return OutBoundDeliveryOrderDetail.objects.filter(outbound_delivery_order__warehouse=warehouse_name,
                                                          outbound_delivery_order__station=station,
                                                          status=3
                                                          ).order_by('-finish_time')


@method_decorator([api_recorder], name="dispatch")
class InOutBoundSummaryView(APIView):
    """混炼终炼出库口出入库统计，参数：warehouse_name=混炼胶库/终炼胶库&station_id=出库口id"""

    def get(self, request):
        warehouse_name = self.request.query_params.get('warehouse_name')  # 库存名称
        station_id = self.request.query_params.get('station_id')  # 出库口名称
        try:
            station = Station.objects.get(id=station_id).name
        except Exception:
            raise ValidationError('参数错误')
        now = datetime.datetime.now()
        current_work_schedule_plan = WorkSchedulePlan.objects.filter(
            start_time__lte=now,
            end_time__gte=now,
            plan_schedule__work_schedule__work_procedure__global_name='密炼'
        ).first()
        if current_work_schedule_plan:
            date_now = str(current_work_schedule_plan.plan_schedule.day_time)
        else:
            date_now = str(now.date())
        date_begin_time = date_now + ' 08:00:00'
        if warehouse_name == '混炼胶库':
            if station == '一层前端':
                ret = [
                    {'tunnel': '3巷',
                     'in_bound_count': MixGumInInventoryLog.objects.using('bz').filter(
                         start_time__gte=date_begin_time,
                         location__startswith='3'
                     ).exclude(Q(material_no__icontains='-RE') |
                               Q(material_no__icontains='-FM') |
                               Q(material_no__icontains='-RFM')
                               ).aggregate(count=Sum('qty'))['count'],
                     "out_bound_count": MixGumOutInventoryLog.objects.using('bz').filter(
                         start_time__gte=date_begin_time,
                         location__startswith='3'
                     ).exclude(Q(material_no__icontains='-RE') |
                               Q(material_no__icontains='-FM') |
                               Q(material_no__icontains='-RFM')
                               ).aggregate(count=Sum('qty'))['count']
                     },
                    {'tunnel': '4巷',
                     'in_bound_count': MixGumInInventoryLog.objects.using('bz').filter(
                         start_time__gte=date_begin_time,
                         location__startswith='4'
                     ).exclude(Q(material_no__icontains='-RE') |
                               Q(material_no__icontains='-FM') |
                               Q(material_no__icontains='-RFM')
                               ).aggregate(count=Sum('qty'))['count'],
                     "out_bound_count": MixGumOutInventoryLog.objects.using('bz').filter(
                         start_time__gte=date_begin_time,
                         location__startswith='4'
                     ).exclude(Q(material_no__icontains='-RE') |
                               Q(material_no__icontains='-FM') |
                               Q(material_no__icontains='-RFM')
                               ).aggregate(count=Sum('qty'))['count']
                     },
                ]
                # 出库
            elif station == '二层前端':
                ret = [
                    {'tunnel': '1巷',
                     'in_bound_count': MixGumInInventoryLog.objects.using('bz').filter(
                         start_time__gte=date_begin_time,
                         location__startswith='1'
                     ).exclude(Q(material_no__icontains='-RE') |
                               Q(material_no__icontains='-FM') |
                               Q(material_no__icontains='-RFM')
                               ).aggregate(count=Sum('qty'))['count'],
                     "out_bound_count": MixGumOutInventoryLog.objects.using('bz').filter(
                         start_time__gte=date_begin_time,
                         location__startswith='1'
                     ).exclude(Q(material_no__icontains='-RE') |
                               Q(material_no__icontains='-FM') |
                               Q(material_no__icontains='-RFM')
                               ).aggregate(count=Sum('qty'))['count']
                     },
                    {'tunnel': '2巷',
                     'in_bound_count': MixGumInInventoryLog.objects.using('bz').filter(
                         start_time__gte=date_begin_time,
                         location__startswith='2'
                     ).exclude(Q(material_no__icontains='-RE') |
                               Q(material_no__icontains='-FM') |
                               Q(material_no__icontains='-RFM')
                               ).aggregate(count=Sum('qty'))['count'],
                     "out_bound_count": MixGumOutInventoryLog.objects.using('bz').filter(
                         start_time__gte=date_begin_time,
                         location__startswith='2'
                     ).exclude(Q(material_no__icontains='-RE') |
                               Q(material_no__icontains='-FM') |
                               Q(material_no__icontains='-RFM')
                               ).aggregate(count=Sum('qty'))['count']
                     },
                ]
            elif station == '二层后端':
                ret = [
                    {'tunnel': '1巷',
                     'in_bound_count': MixGumInInventoryLog.objects.using('bz').filter(
                         start_time__gte=date_begin_time,
                         location__startswith='1'
                     ).exclude(Q(material_no__icontains='-RE') |
                               Q(material_no__icontains='-FM') |
                               Q(material_no__icontains='-RFM')
                               ).aggregate(count=Sum('qty'))['count'],
                     "out_bound_count": MixGumOutInventoryLog.objects.using('bz').filter(
                         start_time__gte=date_begin_time,
                         location__startswith='1'
                     ).exclude(Q(material_no__icontains='-RE') |
                               Q(material_no__icontains='-FM') |
                               Q(material_no__icontains='-RFM')
                               ).aggregate(count=Sum('qty'))['count']
                     },
                    {'tunnel': '2巷',
                     'in_bound_count': MixGumInInventoryLog.objects.using('bz').filter(
                         start_time__gte=date_begin_time,
                         location__startswith='2'
                     ).exclude(Q(material_no__icontains='-RE') |
                               Q(material_no__icontains='-FM') |
                               Q(material_no__icontains='-RFM')
                               ).aggregate(count=Sum('qty'))['count'],
                     "out_bound_count": MixGumOutInventoryLog.objects.using('bz').filter(
                         start_time__gte=date_begin_time,
                         location__startswith='2'
                     ).exclude(Q(material_no__icontains='-RE') |
                               Q(material_no__icontains='-FM') |
                               Q(material_no__icontains='-RFM')
                               ).aggregate(count=Sum('qty'))['count']
                     },
                    {'tunnel': '3巷',
                     'in_bound_count': MixGumInInventoryLog.objects.using('bz').filter(
                         start_time__gte=date_begin_time,
                         location__startswith='3'
                     ).exclude(Q(material_no__icontains='-RE') |
                               Q(material_no__icontains='-FM') |
                               Q(material_no__icontains='-RFM')
                               ).aggregate(count=Sum('qty'))['count'],
                     "out_bound_count": MixGumOutInventoryLog.objects.using('bz').filter(
                         start_time__gte=date_begin_time,
                         location__startswith='3'
                     ).exclude(Q(material_no__icontains='-RE') |
                               Q(material_no__icontains='-FM') |
                               Q(material_no__icontains='-RFM')
                               ).aggregate(count=Sum('qty'))['count']
                     },
                    {'tunnel': '4巷',
                     'in_bound_count': MixGumInInventoryLog.objects.using('bz').filter(
                         start_time__gte=date_begin_time,
                         location__startswith='4'
                     ).exclude(Q(material_no__icontains='-RE') |
                               Q(material_no__icontains='-FM') |
                               Q(material_no__icontains='-RFM')
                               ).aggregate(count=Sum('qty'))['count'],
                     "out_bound_count": MixGumOutInventoryLog.objects.using('bz').filter(
                         start_time__gte=date_begin_time,
                         location__startswith='4'
                     ).exclude(Q(material_no__icontains='-RE') |
                               Q(material_no__icontains='-FM') |
                               Q(material_no__icontains='-RFM')
                               ).aggregate(count=Sum('qty'))['count']
                     },
                ]
            else:
                ret = []
            # 混炼胶总入库车数
            total_inbound_count = MixGumInInventoryLog.objects.using('bz').filter(
                start_time__gte=date_begin_time).exclude(Q(material_no__icontains='-RE') |
                                                         Q(material_no__icontains='-FM') |
                                                         Q(material_no__icontains='-RFM')
                                                         ).aggregate(count=Sum('qty'))['count']
            # 混炼胶总出库数量
            total_outbound_count = MixGumOutInventoryLog.objects.using('bz').filter(
                start_time__gte=date_begin_time).exclude(Q(material_no__icontains='-RE') |
                                                         Q(material_no__icontains='-FM') |
                                                         Q(material_no__icontains='-RFM')
                                                         ).aggregate(count=Sum('qty'))['count']
            # 混炼胶总生产车次
            production_count = TrainsFeedbacks.objects.filter(
                factory_date=date_now).exclude(
                Q(product_no__icontains='-RE') |
                Q(product_no__icontains='-FM') |
                Q(product_no__icontains='-RFM')).count()
        else:
            ret = [
                {'tunnel': '1巷',
                 'in_bound_count': FinalGumInInventoryLog.objects.using('lb').filter(
                     start_time__gte=date_begin_time,
                     location__startswith='1').aggregate(count=Sum('qty'))['count'],
                 "out_bound_count": FinalGumOutInventoryLog.objects.using('lb').filter(
                     start_time__gte=date_begin_time, location__startswith='1').aggregate(count=Sum('qty'))['count']
                 },
                {'tunnel': '2巷',
                 'in_bound_count': FinalGumInInventoryLog.objects.using('lb').filter(
                     start_time__gte=date_begin_time,
                     location__startswith='2').aggregate(count=Sum('qty'))['count'],
                 "out_bound_count": FinalGumOutInventoryLog.objects.using('lb').filter(
                     start_time__gte=date_begin_time, location__startswith='2').aggregate(count=Sum('qty'))['count']
                 },
                {'tunnel': '3巷',
                 'in_bound_count': FinalGumInInventoryLog.objects.using('lb').filter(
                     start_time__gte=date_begin_time,
                     location__startswith='3').aggregate(count=Sum('qty'))['count'],
                 "out_bound_count": FinalGumOutInventoryLog.objects.using('lb').filter(
                     start_time__gte=date_begin_time, location__startswith='3').aggregate(count=Sum('qty'))['count']
                 },
                {'tunnel': '4巷',
                 'in_bound_count': FinalGumInInventoryLog.objects.using('lb').filter(
                     start_time__gte=date_begin_time,
                     location__startswith='4').aggregate(count=Sum('qty'))['count'],
                 "out_bound_count": FinalGumOutInventoryLog.objects.using('lb').filter(
                     start_time__gte=date_begin_time, location__startswith='4').aggregate(count=Sum('qty'))['count']
                 },
            ]
            # 终炼库区终炼胶入库总车数
            final_inbound_count = FinalGumInInventoryLog.objects.using('lb').filter(
                start_time__gte=date_begin_time).filter(Q(location__startswith='1') |
                                                        Q(location__startswith='2') |
                                                        Q(location__startswith='3') |
                                                        Q(location__startswith='4')
                                                        ).aggregate(count=Sum('qty'))['count']
            # 混炼库区终炼胶入库总车数
            mixin_inbound_count = MixGumInInventoryLog.objects.using('bz').filter(
                start_time__gte=date_begin_time).filter(Q(material_no__icontains='-RE') |
                                                        Q(material_no__icontains='-FM') |
                                                        Q(material_no__icontains='-RFM')
                                                        ).aggregate(count=Sum('qty'))['count']
            # 终炼总入库车数
            if not final_inbound_count:
                final_inbound_count = 0
            if not mixin_inbound_count:
                mixin_inbound_count = 0
            total_inbound_count = final_inbound_count + mixin_inbound_count

            # 终炼库区终炼胶出库总车数
            final_outbound_count = FinalGumOutInventoryLog.objects.using('lb').filter(
                start_time__gte=date_begin_time).filter(Q(location__startswith='1') |
                                                        Q(location__startswith='2') |
                                                        Q(location__startswith='3') |
                                                        Q(location__startswith='4')
                                                        ).aggregate(count=Sum('qty'))['count']
            # 混炼库区终炼胶出库总车数
            mixin_outbound_count = MixGumOutInventoryLog.objects.using('bz').filter(
                start_time__gte=date_begin_time).filter(Q(material_no__icontains='-RE') |
                                                        Q(material_no__icontains='-FM') |
                                                        Q(material_no__icontains='-RFM')
                                                        ).aggregate(count=Sum('qty'))['count']
            # 终炼总出库车数
            if not final_outbound_count:
                final_outbound_count = 0
            if not mixin_outbound_count:
                mixin_outbound_count = 0
            total_outbound_count = final_outbound_count + mixin_outbound_count
            # 终炼总车次
            production_count = TrainsFeedbacks.objects.filter(
                factory_date=date_now).filter(
                Q(product_no__icontains='-RE') |
                Q(product_no__icontains='-FM') |
                Q(product_no__icontains='-RFM')).count()
        return Response({"data": ret,
                         "total_inbound_count": total_inbound_count,
                         "total_outbound_count": total_outbound_count,
                         "production_count": production_count
                         })


@method_decorator([api_recorder], name="dispatch")
class LIBRARYINVENTORYView(ListAPIView):

    def get_result(self, model, db, store_name, warehouse_name, location_status, **kwargs):
        # 各胶料封闭货位数据
        fb = model.objects.using(db).filter(**kwargs).filter(location_status='封闭货位').values('material_no').annotate(
            qty=Sum('qty'),
            total_weight=Sum('total_weight')
            ).values('material_no', 'qty', 'total_weight')
        # 胶料品质状态数据
        query_set = model.objects.using(db).filter(store_name=store_name).filter(**kwargs)
        if location_status:
            if location_status == 'Y':
                query_set = query_set.filter(location_status='封闭货位')
            else:
                query_set = query_set.exclude(location_status='封闭货位')
                fb = []
        result = query_set.values('material_no', 'quality_level').annotate(qty=Sum('qty'),
                                                                           total_weight=Sum('total_weight')).values(
            'material_no', 'quality_level', 'qty', 'total_weight').order_by('material_no')

        res = {}
        for i in result:
            if i['material_no'] not in res:
                try:
                    stage = i['material_no'].split('-')[1]
                except Exception:
                    stage = i['material_no']
                res[i['material_no']] = {
                    'material_no': i['material_no'],
                    'warehouse_name': warehouse_name,
                    'location': kwargs.get('location__startswith'),
                    'stage': stage,
                    'all_qty': i['qty'],
                    'total_weight': i['total_weight'],
                    i['quality_level']: {'qty': i['qty'], 'total_weight': i['total_weight']},
                }
            else:
                res[i['material_no']][i['quality_level']] = {
                    'qty': i['qty'],
                    'total_weight': i['total_weight']}
                res[i['material_no']]['all_qty'] += i['qty']
                res[i['material_no']]['total_weight'] += i['total_weight']
            res[i['material_no']]['active_qty'] = res[i['material_no']]['all_qty']

        for i in fb:
            if res.get(i['material_no']):
                res[i['material_no']].update({'封闭': {'qty': i['qty'], 'total_weight': i['total_weight']}})
                res[i['material_no']]['active_qty'] -= res[i['material_no']]['封闭']['qty']

        return list(res.values())

    def get_queryset(self):
        return

    def export_xls(self, result):
        response = HttpResponse(content_type='application/vnd.ms-excel')
        filename = '库内库存明细'
        response['Content-Disposition'] = u'attachment;filename= ' + filename.encode('gbk').decode(
            'ISO-8859-1') + '.xls'
        # 创建一个文件对象
        wb = xlwt.Workbook(encoding='utf8')
        # 创建一个sheet对象
        sheet = wb.add_sheet('库存信息', cell_overwrite_ok=True)
        style = xlwt.XFStyle()
        style.alignment.wrap = 1

        columns = ['No', '胶料类型', '物料编码', '物料名称', '库区', '巷道', '一等品库存数(车)', '重量(kg)', '三等品库存数(车)', '重量(kg)',
                   '待检品库存数(车)', '重量(kg)', '总库存数(车)', '总重量(kg)', '封闭库存数(车)', '重量(kg)', '有效库存数']
        # 写入文件标题
        for col_num in range(len(columns)):
            sheet.write(0, col_num, columns[col_num])
            # 写入数据
            data_row = 1
            for i in result:
                try:
                    product_no_split_list = i['material_no'].split('-')
                    if product_no_split_list[1] in ('RE', 'FM', 'RFM'):
                        product_no = product_no_split_list[2]
                    else:
                        product_no = '-'.join(product_no_split_list[1:3])
                except Exception:
                    product_no = i['material_no']
                sheet.write(data_row, 0, result.index(i) + 1)
                sheet.write(data_row, 1, i['stage'])
                sheet.write(data_row, 2, product_no)
                sheet.write(data_row, 3, product_no)
                sheet.write(data_row, 4, i['warehouse_name'])
                sheet.write(data_row, 5, i['location'])
                sheet.write(data_row, 6, i['一等品']['qty'] if i.get('一等品') else None)
                sheet.write(data_row, 7, i['一等品']['total_weight'] if i.get('一等品') else None)
                sheet.write(data_row, 8, i['三等品']['qty'] if i.get('三等品') else None)
                sheet.write(data_row, 9, i['三等品']['total_weight'] if i.get('三等品') else None)
                sheet.write(data_row, 10, i['待检品']['qty'] if i.get('待检品') else None)
                sheet.write(data_row, 11, i['待检品']['total_weight'] if i.get('待检品') else None)
                sheet.write(data_row, 12, i['all_qty'])
                sheet.write(data_row, 13, i['total_weight'])
                sheet.write(data_row, 14, i['封闭']['qty'] if i.get('封闭') else None)
                sheet.write(data_row, 15, i['封闭']['total_weight'] if i.get('封闭') else None)
                sheet.write(data_row, 16, i['active_qty'])
                data_row = data_row + 1
        # 写出到IO
        output = BytesIO()
        wb.save(output)
        # 重新定位到开始
        output.seek(0)
        response.write(output.getvalue())
        return response

    def list(self, request, *args, **kwargs):
        params = request.query_params
        page = params.get("page", 1)
        page_size = params.get("page_size", 10)
        warehouse_name = params.get("warehouse_name", '')  # 库区
        stage = params.get("stage", '')  # 段次
        material_no = params.get("material_no", '')  # 物料编码
        location = params.get('location', '')  # 巷道
        location_status = params.get('location_status', '')  # 有无封闭货位
        export = params.get("export", None)

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

        filter_kwargs = {}
        if material_no:
            filter_kwargs['material_no__icontains'] = material_no
        if stage:
            filter_kwargs['material_no__contains'] = f'-{stage}'
        if location:
            filter_kwargs['location__startswith'] = location

        if warehouse_name == '混炼胶库':
            model = BzFinalMixingRubberInventory
            store_name = '立体库'
            temp = self.get_result(model, 'bz', store_name, warehouse_name, location_status, **filter_kwargs)

        elif warehouse_name == '终炼胶库':
            model = BzFinalMixingRubberInventoryLB
            store_name = '炼胶库'
            temp = self.get_result(model, 'lb', store_name, warehouse_name, location_status, **filter_kwargs)

        else:
            model1 = BzFinalMixingRubberInventory
            store_name1 = '立体库'
            warehouse_name1 = '混炼胶库'
            temp1 = self.get_result(model1, 'bz', store_name1, warehouse_name1, location_status, **filter_kwargs)
            model2 = BzFinalMixingRubberInventoryLB
            store_name2 = '炼胶库'
            warehouse_name2 = '终炼胶库'
            temp2 = self.get_result(model2, 'lb', store_name2, warehouse_name2, location_status, **filter_kwargs)
            temp = list(temp1) + list(temp2)
        temp = sorted(temp, key=lambda x: x['material_no'])

        weight_1 = qty_1 = weight_3 = qty_3 = weight_dj = qty_dj = weight_fb = qty_fb = 0

        for i in temp:
            weight_1 += i['一等品']['total_weight'] if i.get('一等品') else 0
            qty_1 += i['一等品']['qty'] if i.get('一等品') else 0
            weight_3 += i['三等品']['total_weight'] if i.get('三等品') else 0
            qty_3 += i['三等品']['qty'] if i.get('三等品') else 0
            weight_dj += i['待检品']['total_weight'] if i.get('待检品') else 0
            qty_dj += i['待检品']['qty'] if i.get('待检品') else 0
            weight_fb += i['封闭']['total_weight'] if i.get('封闭') else 0
            qty_fb += i['封闭']['qty'] if i.get('封闭') else 0

        total_qty = qty_1 + qty_3 + qty_dj
        total_weight = weight_1 + weight_3 + weight_dj
        count = len(temp)
        if export == 'all':
            result = temp
        else:
            result = temp[st:et]
        if export:
            return self.export_xls(result)

        if warehouse_name == '终炼胶库':
            total_goods_num = 1428
            used_goods_num = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(store_name='炼胶库').count()
        elif warehouse_name == '混炼胶库':
            total_goods_num = 1952
            used_goods_num = BzFinalMixingRubberInventory.objects.using('bz').all().count()
        else:
            total_goods_num = 1428 + 1952
            used_goods_num = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(store_name='炼胶库').count() \
                             + BzFinalMixingRubberInventory.objects.using('bz').all().count()

        return Response({'results': result,
                         "total_count": total_qty,
                         "total_weight": total_weight,
                         'weight_1': weight_1,
                         'qty_1': qty_1,
                         'weight_3': weight_3,
                         'qty_3': qty_3,
                         'weight_dj': weight_dj,
                         'qty_dj': qty_dj,
                         'weight_fb': weight_fb,
                         'qty_fb': qty_fb,
                         'count': count,
                         'total_goods_num': total_goods_num,
                         'used_goods_num': used_goods_num,
                         'empty_goods_num': total_goods_num - used_goods_num
                         })


@method_decorator([api_recorder], name="dispatch")
class OutBoundDeliveryOrderViewSet(ModelViewSet):
    queryset = OutBoundDeliveryOrder.objects.all().order_by("-created_date")
    serializer_class = OutBoundDeliveryOrderSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = OutBoundDeliveryOrderFilter

    @action(methods=['get'], detail=False, permission_classes=[], url_path='export',
            url_name='export')
    def export(self, request):
        order_ids = self.request.query_params.get('order_ids', '')
        order_id_list = order_ids.split(',')
        try:
            orders = OutBoundDeliveryOrder.objects.filter(id__in=order_id_list)
        except Exception:
            raise ValidationError('参数错误')
        ws = xlwt.Workbook(encoding='utf-8')
        for order in orders:
            # 创建工作薄
            w = ws.add_sheet("{}".format(order.order_no))
            w.write(0, 0, "订单子编号")
            w.write(0, 1, "胶料编码")
            w.write(0, 2, "lot_no")
            w.write(0, 3, "托盘号")
            w.write(0, 4, "车次")
            w.write(0, 5, "库位编号")
            w.write(0, 6, "出库时间")
            w.write(0, 7, "状态")
            # 写入数据
            excel_row = 1
            for obj in order.outbound_delivery_details.all():
                w.write(excel_row, 0, obj.order_no)
                w.write(excel_row, 1, order.product_no)
                w.write(excel_row, 2, obj.lot_no)
                w.write(excel_row, 3, obj.pallet_no)
                w.write(excel_row, 4, obj.memo)
                w.write(excel_row, 5, obj.location)
                w.write(excel_row, 6, obj.finish_time)
                w.write(excel_row, 7, obj.get_status_display())
                excel_row += 1
        response = HttpResponse(content_type='application/vnd.ms-excel')
        filename = '备品备件信息导入模板'
        response['Content-Disposition'] = 'attachment;filename= ' + filename.encode('gbk').decode('ISO-8859-1') + '.xls'
        output = BytesIO()
        ws.save(output)
        # 重新定位到开始
        output.seek(0)
        response.write(output.getvalue())
        return response


@method_decorator([api_recorder], name="dispatch")
class OutBoundDeliveryOrderDetailViewSet(ModelViewSet):
    queryset = OutBoundDeliveryOrderDetail.objects.all().order_by('-created_date')
    serializer_class = OutBoundDeliveryOrderDetailSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = OutBoundDeliveryOrderDetailFilter

    def get_queryset(self):
        queryset = self.queryset
        statuses = self.request.query_params.get('status')
        if statuses:
            try:
                queryset = queryset.filter(status__in=statuses.split(','))
            except Exception:
                raise ValidationError('参数错误')
        return queryset

    def create(self, request, *args, **kwargs):
        data = self.request.data
        if not isinstance(data, list):
            raise ValidationError('参数错误！')
        if not data:
            raise ValidationError('请选择货物出库！')
        try:
            instance = OutBoundDeliveryOrder.objects.get(id=data[0]['outbound_delivery_order'])
        except Exception:
            raise ValidationError('出库单据号不存在')

        last_order_detail = instance.outbound_delivery_details.order_by('created_date').last()
        if not last_order_detail:
            sub_no = '00001'
        else:
            if last_order_detail.sub_no:
                last_sub_no = str(int(last_order_detail.sub_no) + 1)
                if len(last_sub_no) <= 5:
                    sub_no = last_sub_no.zfill(5)
                else:
                    sub_no = last_sub_no.zfill(len(last_sub_no))
            else:
                sub_no = '00001'

        detail_ids = []
        for item in data:
            item['sub_no'] = sub_no
            s = self.serializer_class(data=item, context={'request': request})
            s.is_valid(raise_exception=True)
            detail = s.save()
            detail_ids.append(detail.id)
        if not DEBUG:
            # 出库
            username = self.request.user.username
            items = []
            for detail in OutBoundDeliveryOrderDetail.objects.filter(id__in=detail_ids):
                pallet = PalletFeedbacks.objects.filter(pallet_no=detail.pallet_no).last()
                dict1 = {'WORKID': detail.order_no,
                         'MID': instance.product_no,
                         'PICI': pallet.bath_no if pallet else "1",
                         'RFID': detail.pallet_no,
                         'STATIONID': instance.station,
                         'SENDDATE': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                if instance.warehouse == '终炼胶库':
                    dict1['STOREDEF_ID'] = 1
                items.append(dict1)
            json_data = {
                'msgId': instance.order_no,
                'OUTTYPE': '快检出库',
                "msgConut": str(len(items)),
                "SENDUSER": username,
                "items": items
            }
            json_data = json.dumps(json_data, ensure_ascii=False)
            if instance.warehouse == '混炼胶库':
                sender = OUTWORKUploader(end_type="指定出库")
            else:
                sender = OUTWORKUploaderLB(end_type="指定出库")
            result = sender.request(instance.order_no, '指定出库', str(len(items)), username, json_data)
            if result is not None:
                try:
                    items = result['items']
                    msg = items[0]['msg']
                except:
                    msg = result[0]['msg']
                if "TRUE" in msg:  # 成功
                    OutBoundDeliveryOrderDetail.objects.filter(id__in=detail_ids).update(status=2)
                else:  # 失败
                    OutBoundDeliveryOrderDetail.objects.filter(id__in=detail_ids).update(status=5)
                    raise ValidationError('出库失败：{}'.format(msg))
        return Response('ok')


@method_decorator([api_recorder], name="dispatch")
class OutBoundHistory(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        last_out_bound_order = OutBoundDeliveryOrder.objects.filter(
            created_user=self.request.user).order_by('created_date').last()
        if last_out_bound_order:
            data = {
                'warehouse': last_out_bound_order.warehouse,
                'station': last_out_bound_order.station,
                'order_qty': last_out_bound_order.order_qty
            }
        else:
            data = {}
        return Response(data)


@method_decorator([api_recorder], name="dispatch")
class WmsInventoryMaterialViewSet(GenericAPIView):
    DB = 'wms'
    queryset = WmsInventoryMaterial.objects.all()
    serializer_class = WmsInventoryMaterialSerializer

    def get(self, request, *args, **kwargs):
        queryset = WmsInventoryMaterial.objects.using(self.DB).all()
        material_no = self.request.query_params.get('material_no')
        material_name = self.request.query_params.get('material_name')
        unset_flag = self.request.query_params.get('unset_flag')
        if material_no:
            queryset = queryset.filter(material_no__icontains=material_no)
        if material_name:
            queryset = queryset.filter(material_name__icontains=material_name)
        if unset_flag:
            mt_codes = list(WMSMaterialSafetySettings.objects.values_list('wms_material_code', flat=True))
            queryset = queryset.exclude(material_no__in=mt_codes)
        page = self.paginate_queryset(queryset)
        serializer = WmsInventoryMaterialSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def post(self, request):
        material_nos = self.request.data.get('material_nos')
        avg_consuming_weight = self.request.data.get('avg_consuming_weight')
        avg_setting_weight = self.request.data.get('avg_setting_weight')
        warning_days = self.request.data.get('warning_days')
        if avg_consuming_weight:
            defaults = {'avg_consuming_weight': avg_consuming_weight,
                        'type': 1,
                        'created_user': self.request.user}
        elif avg_setting_weight:
            defaults = {'avg_setting_weight': avg_setting_weight,
                        'type': 2,
                        'created_user': self.request.user}
        else:
            defaults = {'warning_days': warning_days,
                        'created_user': self.request.user}
        for material_no in material_nos:
            obj, _ = WMSMaterialSafetySettings.objects.update_or_create(defaults=defaults, wms_material_code=material_no)
            obj.save()
        return Response('设置成功！')


@method_decorator([api_recorder], name="dispatch")
class WMSStockSummaryView(APIView):
    DATABASE_CONF = WMS_CONF

    def export_xls(self, result):
        response = HttpResponse(content_type='application/vnd.ms-excel')
        filename = '库存统计'
        response['Content-Disposition'] = u'attachment;filename= ' + filename.encode('gbk').decode(
            'ISO-8859-1') + '.xls'
        # 创建一个文件对象
        wb = xlwt.Workbook(encoding='utf8')
        # 创建一个sheet对象
        sheet = wb.add_sheet('库存信息', cell_overwrite_ok=True)

        style = xlwt.XFStyle()
        style.alignment.wrap = 1

        columns = ['No', '物料名称', '物料编码', '中策物料编码', '数单位量', 'PDM', '物料组',
                   '有效库存数量', '有效库存重量（kg）', '合格品数量', '合格品重量（kg）',
                   '待检品数量', '待检品重量（kg）', '不合格品数量', '不合格品重量（kg）', '总数量', '总重量（kg）', ]

        for col_num in range(len(columns)):
            sheet.write(1, col_num, columns[col_num])
            # 写入数据
        data_row = 2
        for i in result:
            sheet.write(data_row, 0, result.index(i) + 1)
            sheet.write(data_row, 1, i['name'])
            sheet.write(data_row, 2, i['code'])
            sheet.write(data_row, 3, i['zc_material_code'])
            sheet.write(data_row, 4, i['unit'])
            sheet.write(data_row, 5, i['pdm'])
            sheet.write(data_row, 6, i['group_name'])
            sheet.write(data_row, 7, i['quantity_1']+i['quantity_5'])
            sheet.write(data_row, 8, i['weight_1']+i['weight_5'])
            sheet.write(data_row, 9, i['quantity_1'])
            sheet.write(data_row, 10, i['weight_1'])
            sheet.write(data_row, 11, i['quantity_5'])
            sheet.write(data_row, 12, i['weight_5'])
            sheet.write(data_row, 13, i['quantity_3'])
            sheet.write(data_row, 14, i['weight_3'])
            sheet.write(data_row, 15, i['total_quantity'])
            sheet.write(data_row, 16, i['total_weight'])
            data_row = data_row + 1
        # 写出到IO
        output = BytesIO()
        wb.save(output)
        # 重新定位到开始
        output.seek(0)
        response.write(output.getvalue())
        return response

    def get(self, request):
        material_name = self.request.query_params.get('material_name')
        material_no = self.request.query_params.get('material_no')
        material_group_name = self.request.query_params.get('material_group_name')
        lower_only_flag = self.request.query_params.get('lower_only_flag')
        export = self.request.query_params.get('export')
        page = self.request.query_params.get('page', 1)
        page_size = self.request.query_params.get('page_size', 15)
        st = (int(page) - 1) * int(page_size)
        et = int(page) * int(page_size)
        extra_where_str = ""
        if material_name:
            extra_where_str += "where temp.MaterialName like '%{}%'".format(material_name)
        if material_no:
            if extra_where_str:
                extra_where_str += " and temp.MaterialCode like '%{}%'".format(material_no)
            else:
                extra_where_str += "where temp.MaterialCode like '%{}%'".format(material_no)
        if material_group_name:
            if extra_where_str:
                extra_where_str += " and m.MaterialGroupName='{}'".format(material_group_name)
            else:
                extra_where_str += "where m.MaterialGroupName='{}'".format(material_group_name)

        sql = """
                select
            temp.MaterialName,
            temp.MaterialCode,
            m.ZCMaterialCode,
            m.StandardUnit,
            m.Pdm,
            m.MaterialGroupName,
            temp.quantity,
            temp.WeightOfActual,
            temp.StockDetailState
        from (
            select
                a.MaterialCode,
                a.MaterialName,
                a.StockDetailState,
                SUM(a.WeightOfActual) AS WeightOfActual,
                SUM(a.Quantity ) AS quantity
            from t_inventory_stock AS a
            group by
                 a.MaterialCode,
                 a.MaterialName,
                 a.StockDetailState
            ) temp
        left join t_inventory_material m on m.MaterialCode=temp.MaterialCode {}""".format(extra_where_str)
        sc = SqlClient(sql=sql, **self.DATABASE_CONF)
        temp = sc.all()

        safety_data = dict(WMSMaterialSafetySettings.objects.values_list(
            F('wms_material_code'), F('warning_weight') * 1000))

        data_dict = {}

        for item in temp:
            quality_status = item[8]
            if quality_status == 2:
                quality_status = 5
            if item[1] not in data_dict:
                data = {'name': item[0],
                        'code': item[1],
                        'zc_material_code': item[2],
                        'unit': item[3],
                        'pdm': item[4],
                        'group_name': item[5],
                        'total_quantity': item[6],
                        'total_weight': item[7],
                        'quantity_1': 0,
                        'weight_1': 0,
                        'quantity_3': 0,
                        'weight_3': 0,
                        'quantity_4': 0,
                        'weight_4': 0,
                        'quantity_5': 0,
                        'weight_5': 0
                        }
                data['quantity_{}'.format(quality_status)] = item[6]
                data['weight_{}'.format(quality_status)] = item[7]
                data_dict[item[1]] = data
            else:
                data_dict[item[1]]['total_quantity'] += item[6]
                data_dict[item[1]]['total_weight'] += item[7]
                data_dict[item[1]]['quantity_{}'.format(quality_status)] = item[6]
                data_dict[item[1]]['weight_{}'.format(quality_status)] = item[7]
        result = []
        for item in data_dict.values():
            weighting = safety_data.get(item['code'])
            if weighting:
                if weighting < item['weight_1'] + item['weight_5']:
                    item['flag'] = 'H'
                else:
                    item['flag'] = 'L'
            else:
                item['flag'] = None
            result.append(item)
        sc.close()
        if lower_only_flag:
            result = list(filter(lambda x: x['flag'] == 'L', result))
        total_quantity = sum([item['total_quantity'] for item in result])
        total_weight = sum([item['total_weight'] for item in result])
        total_quantity1 = sum([item['quantity_1'] for item in result])
        total_weight1 = sum([item['weight_1'] for item in result])
        total_quantity3 = sum([item['quantity_3'] for item in result])
        total_weight3 = sum([item['weight_3'] for item in result])
        total_quantity5 = sum([item['quantity_5'] for item in result])
        total_weight5 = sum([item['weight_5'] for item in result])
        count = len(result)
        ret = result[st:et]
        if export:
            if export == '1':
                data = ret
            else:
                data = result
            return self.export_xls(data)
        return Response(
            {'results': ret, "count": count,
             'total_quantity': total_quantity, 'total_weight': total_weight,
             'total_quantity1': total_quantity1, 'total_weight1': total_weight1,
             'total_quantity3': total_quantity3, 'total_weight3': total_weight3,
             'total_quantity5': total_quantity5, 'total_weight5': total_weight5
             })


@method_decorator([api_recorder], name="dispatch")
class THInventoryMaterialViewSet(WmsInventoryMaterialViewSet):
    DB = 'cb'


@method_decorator([api_recorder], name="dispatch")
class THStockSummaryView(WMSStockSummaryView):
    DATABASE_CONF = TH_CONF