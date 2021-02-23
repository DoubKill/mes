import datetime
import logging
import random

from django.db.models import Sum
from django.db.transaction import atomic

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

from basics.models import GlobalCode
from inventory.filters import StationFilter, PutPlanManagementLBFilter, PutPlanManagementFilter, \
    DispatchPlanFilter, DispatchLogFilter, DispatchLocationFilter, InventoryFilterBackend, PutPlanManagementFinalFilter, \
    MaterialPlanManagementFilter
from inventory.models import InventoryLog, WarehouseInfo, Station, WarehouseMaterialType, DeliveryPlanStatus, \
    BzFinalMixingRubberInventoryLB, DeliveryPlanLB, DispatchPlan, DispatchLog, DispatchLocation, \
    MixGumOutInventoryLog, MixGumInInventoryLog, DeliveryPlanFinal, MaterialOutPlan
from inventory.models import DeliveryPlan, MaterialInventory
from inventory.serializers import PutPlanManagementSerializer, \
    OverdueMaterialManagementSerializer, WarehouseInfoSerializer, StationSerializer, WarehouseMaterialTypeSerializer, \
    PutPlanManagementSerializerLB, BzFinalMixingRubberLBInventorySerializer, DispatchPlanSerializer, \
    DispatchLogSerializer, DispatchLocationSerializer, DispatchLogCreateSerializer, PutPlanManagementSerializerFinal, \
    InventoryLogOutSerializer, MixGumOutInventoryLogSerializer, MixGumInInventoryLogSerializer, \
    MaterialPlanManagementSerializer
from inventory.models import WmsInventoryStock
from inventory.serializers import BzFinalMixingRubberInventorySerializer, \
    WmsInventoryStockSerializer, InventoryLogSerializer
from mes.common_code import SqlClient
from mes.conf import WMS_CONF
from mes.derorators import api_recorder
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions

from mes.paginations import SinglePageNumberPagination
from recipe.models import Material, MaterialAttribute
from .models import MaterialInventory as XBMaterialInventory
from .models import BzFinalMixingRubberInventory
from .serializers import XBKMaterialInventorySerializer

logger = logging.getLogger('send.log')


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
        if material_type:
            sql = f"""select sum(tis.Quantity) qty, max(tis.MaterialName) material_name,
                           sum(tis.WeightOfActual) weight,tis.MaterialCode material_no,
                           max(tis.ProductionAddress) address, sum(tis.WeightOfActual)/sum(tis.Quantity) unit_weight,
                           max(tis.WeightUnit) unit, max(tim.MaterialGroupName) material_type,
                           Row_Number() OVER (order by tis.MaterialCode) sn, tis.StockDetailState status
                                from t_inventory_stock tis left join t_inventory_material tim on tim.MaterialCode=tis.MaterialCode
                            where tim.MaterialGroupName='{material_type}'
                            group by tis.MaterialCode, tis.StockDetailState;"""
        else:
            sql = f"""select sum(tis.Quantity) qty, max(tis.MaterialName) material_name,
                                       sum(tis.WeightOfActual) weight,tis.MaterialCode material_no,
                                       max(tis.ProductionAddress) address, sum(tis.WeightOfActual)/sum(tis.Quantity) unit_weight,
                                       max(tis.WeightUnit) unit, max(tim.MaterialGroupName) material_type,
                                       Row_Number() OVER (order by tis.MaterialCode) sn, tis.StockDetailState status
                                            from t_inventory_stock tis left join t_inventory_material tim on tim.MaterialCode=tis.MaterialCode
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
        if stage:
            if stage not in stage_list:
                raise ValidationError("胶料段次异常请修正后重试")
            sql = f"""SELECT max(库房名称) as 库房名称, sum(数量) as 数量, sum(重量) as 重量, max(品质状态) as 品质状态, 物料编码, Row_Number() OVER (order by 物料编码) sn
                FROM v_ASRS_STORE_MESVIEW where 物料编码 like '%{stage}%' group by 物料编码"""
        else:
            sql = f"""SELECT max(库房名称) as 库房名称, sum(数量) as 数量, sum(重量) as 重量, max(品质状态) as 品质状态, 物料编码, Row_Number() OVER (order by 物料编码) sn
                FROM v_ASRS_STORE_MESVIEW group by 物料编码"""
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
            data.pop("status", None)
            order_no = data.get('order_no')
            if order_no:
                temp = InventoryLog.objects.filter(order_no=order_no).aggregate(all_qty=Sum('qty'))
                all_qty = temp.get("all_qty")
                if all_qty:
                    all_qty += int(data.get("qty"))
                else:
                    all_qty = int(data.get("qty"))
                dp_obj = DeliveryPlan.objects.filter(order_no=order_no).first()
                if dp_obj:
                    need_qty = dp_obj.need_qty
                else:
                    return Response({"99": "FALSE", "message": "该订单非mes下发订单"})
                if int(all_qty) >= need_qty:  # 若加上当前反馈后出库数量已达到订单需求数量则改为(1:完成)
                    dp_obj.status = 1
                    dp_obj.finish_time = datetime.datetime.now()
                    dp_obj.save()
                    DeliveryPlanStatus.objects.create(warehouse_info=dp_obj.warehouse_info,
                                                      order_no=order_no,
                                                      order_type=dp_obj.order_type if dp_obj.order_type else "出库",
                                                      status=1,
                                                      created_user=dp_obj.created_user,
                                                      )
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
                InventoryLog.objects.create(**data, **il_dict)
                MaterialInventory.objects.create(**material_inventory_dict)
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
        '终炼胶库': [BzFinalMixingRubberInventory, BzFinalMixingRubberInventorySerializer],
        '帘布库': [BzFinalMixingRubberInventoryLB, BzFinalMixingRubberLBInventorySerializer],
        '原材料库': [WmsInventoryStock, WmsInventoryStockSerializer],
        '混炼胶库': [BzFinalMixingRubberInventory, BzFinalMixingRubberInventorySerializer],
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
        for query in 'material_type', 'container_no', 'material_no', "order_no", "location":
            yield self.request.query_params.get(query, None)

    def get_queryset(self):
        # 终炼胶，帘布库区分 货位地址开头1-4终炼胶   5-6帘布库
        model = self.divide_tool(self.MODEL)
        queryset = None
        material_type, container_no, material_no, order_no, location = self.get_query_params()
        quality_status = self.request.query_params.get('quality_status', None)
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
            return queryset
        if model == WmsInventoryStock:
            queryset = model.objects.using('wms').raw(WmsInventoryStock.get_sql(material_type, material_no))
        return queryset

    def get_serializer_class(self):
        return self.divide_tool(self.SERIALIZER)


class NewList(list):

    @property
    @classmethod
    def model(self):
        return InventoryLog.objects.model


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
        if start_time:
            filter_dict.update(start_time__gte=start_time)
        if end_time:
            filter_dict.update(start_time__lte=end_time)
        if location:
            filter_dict.update(location__icontains=location)
        if material_no:
            filter_dict.update(material_no__icontains=material_no)
        if order_no:
            filter_dict.update(order_no__icontains=order_no)
        if store_name == "混炼胶库":
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
                filter_dict.pop("inout_num_type", None)
                temp_set += list(InventoryLog.objects.filter(warehouse_name=store_name, inventory_type=actual_type,
                                                             **filter_dict).order_by('-start_time'))
                return temp_set
            else:
                return MixGumInInventoryLog.objects.using('bz').filter(**filter_dict)
        else:
            return InventoryLog.objects.filter(**filter_dict).order_by('-start_time')

    # def get_serializer_class(self):
    #     store_name = self.request.query_params.get("store_name", "混炼胶库")
    #     order_type = self.request.query_params.get("order_type", "出库")
    #     if store_name == "混炼胶库":
    #         if order_type == "出库":
    #             return MixGumOutInventoryLogSerializer
    #         else:
    #             return MixGumInInventoryLogSerializer
    #     else:
    #         return InventoryLogSerializer


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
            # TODO 暂时这么写
            try:
                ret = BzFinalMixingRubberInventory.objects.using('bz').filter(**filter_dict).values(
                    'material_no').annotate(
                    all_qty=Sum('qty')).values('material_no', 'all_qty')
            except:
                raise ValidationError("终炼胶库连接失败")
        elif store_name == "混炼胶库":
            try:
                ret = BzFinalMixingRubberInventory.objects.using('bz').filter(**filter_dict).values(
                    'material_no').annotate(
                    all_qty=Sum('qty')).values('material_no', 'all_qty')
            except:
                raise ValidationError("混炼胶库连接失败")
        elif store_name == "帘布库":
            try:
                ret = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(**filter_dict).values(
                    'material_no').annotate(
                    all_qty=Sum('qty')).values('material_no', 'all_qty')
            except:
                raise ValidationError("帘布库连接失败")
        elif store_name == "原材料库":
            status_map = {"合格":1, "不合格":2}
            try:
                ret = WmsInventoryStock.objects.using('wms').filter(quality_status=status_map.get(status, 1)).values(
                    'material_no').annotate(
                    all_qty=Sum('qty')).values('material_no', 'all_qty')
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