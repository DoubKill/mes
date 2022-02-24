import decimal
import json
import datetime
import re

import math
import time
from io import BytesIO
from itertools import groupby

import requests
import xlwt
from django.http import HttpResponse

from equipment.utils import gen_template_response
from inventory.models import FinalGumOutInventoryLog
from mes.common_code import SqlClient, OSum
from django.conf import settings
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.db.models import Max, Sum, Count, Min, F, Q, Avg
from django.db.transaction import atomic
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSet
from basics.models import PlanSchedule, Equip, GlobalCode, WorkSchedulePlan, EquipCategoryAttribute
from equipment.models import EquipMaintenanceOrder
from mes.common_code import OSum
from mes.conf import EQUIP_LIST
from mes.derorators import api_recorder
from mes.paginations import SinglePageNumberPagination
from mes.permissions import PermissionClass
from plan.filters import ProductClassesPlanFilter
from plan.models import ProductClassesPlan
from basics.models import Equip
from production.filters import TrainsFeedbacksFilter, PalletFeedbacksFilter, QualityControlFilter, EquipStatusFilter, \
    PlanStatusFilter, ExpendMaterialFilter, CollectTrainsFeedbacksFilter, UnReachedCapacityCause, \
    ProductInfoDingJiFilter
from production.models import TrainsFeedbacks, PalletFeedbacks, EquipStatus, PlanStatus, ExpendMaterial, OperationLog, \
    QualityControl, ProcessFeedback, AlarmLog, MaterialTankStatus, ProductionDailyRecords, ProductionPersonnelRecords, \
    RubberCannotPutinReason, MachineTargetYieldSettings, EmployeeAttendanceRecords, PerformanceJobLadder, \
    PerformanceUnitPrice, ProductInfoDingJi, SetThePrice
from production.serializers import QualityControlSerializer, OperationLogSerializer, ExpendMaterialSerializer, \
    PlanStatusSerializer, EquipStatusSerializer, PalletFeedbacksSerializer, TrainsFeedbacksSerializer, \
    ProductionRecordSerializer, TrainsFeedbacksBatchSerializer, CollectTrainsFeedbacksSerializer, \
    ProductionPlanRealityAnalysisSerializer, UnReachedCapacityCauseSerializer, TrainsFeedbacksSerializer2, \
    CurveInformationSerializer, MixerInformationSerializer2, WeighInformationSerializer2, AlarmLogSerializer, \
    ProcessFeedbackSerializer, TrainsFixSerializer, PalletFeedbacksBatchModifySerializer, ProductPlanRealViewSerializer, \
    RubberCannotPutinReasonSerializer, PerformanceJobLadderSerializer, ProductInfoDingJiSerializer, \
    SetThePriceSerializer
from rest_framework.generics import ListAPIView, GenericAPIView, ListCreateAPIView, CreateAPIView, UpdateAPIView, \
    get_object_or_404
from datetime import timedelta

from quality.models import BatchProductNo, BatchDay, Batch, BatchMonth, BatchYear, MaterialTestOrder, \
    MaterialDealResult, MaterialTestResult, MaterialDataPointIndicator
from quality.serializers import BatchProductNoDateZhPassSerializer, BatchProductNoClassZhPassSerializer
from quality.utils import get_cur_sheet, get_sheet_data
from terminal.models import Plan


@method_decorator([api_recorder], name="dispatch")
class TrainsFeedbacksViewSet(mixins.CreateModelMixin,
                             mixins.RetrieveModelMixin,
                             GenericViewSet):
    """
    list:
        车次/批次产出反馈列表
    retrieve:
        车次/批次产出反馈详情
    create:
        创建车次/批次产出反馈
    """
    queryset = TrainsFeedbacks.objects.filter(delete_flag=False)
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = TrainsFeedbacksSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ('id',)
    filter_class = TrainsFeedbacksFilter

    def list(self, request, *args, **kwargs):
        actual_trains = request.query_params.get("actual_trains", '')
        if "," in actual_trains:
            train_list = actual_trains.split(",")
            try:
                queryset = self.filter_queryset(self.get_queryset().filter(actual_trains__gte=train_list[0],
                                                                           actual_trains__lte=train_list[-1],
                                                                           ))
            except:
                return Response({"actual_trains": "请输入: <开始车次>,<结束车次>。这类格式"})
        else:
            queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@method_decorator([api_recorder], name="dispatch")
class PalletFeedbacksViewSet(mixins.CreateModelMixin,
                             mixins.ListModelMixin,
                             GenericViewSet):
    """
        list:
            托盘产出反馈列表
        retrieve:
            托盘产出反馈详情
        create:
            托盘产出反馈反馈
    """
    queryset = PalletFeedbacks.objects.filter(delete_flag=False).order_by("-plan_classes_uid")
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = PalletFeedbacksSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ('id', 'product_time')
    filter_class = PalletFeedbacksFilter

    @action(methods=['post'], detail=False, permission_classes=[], url_path='bind-rfid',
            url_name='bind-rfid')
    def bind_rfid(self, request):
        # {"plan_classes_uid": "2021102520011276Z11", "bath_no": 367, "equip_no": "Z11", "product_no": "C-FM-F978-04",
        #  "plan_weight": "669.66", "actual_weight": "670", "begin_time": "2021-10-26 00:18:20.436",
        #  "end_time": "2021-10-26 00:18:20.436", "operation_user": "人工", "begin_trains": 81, "end_trains": 82,
        #  "pallet_no": "20102905", "classes": "夜班", "lot_no": "AAJ1Z112021102630367",
        #  "product_time": "2021-10-26 00:18:20.436", "factory_date": "2021-10-26"}
        if request.data:
            data = dict(request.data)
        else:
            data = dict(request.query_params)
        validated_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                value = value.strip()
            validated_data[key] = value
        lot_no = validated_data.pop("lot_no", None)
        validated_data.pop("factory_date", None)
        if not lot_no:
            raise ValidationError("请传入lot_no")
        if MaterialTestOrder.objects.filter(lot_no=lot_no).exists():
            raise ValidationError("该批次数据已绑定快检数据，不可修改！")
        instance, flag = PalletFeedbacks.objects.update_or_create(defaults=validated_data, **{"lot_no": lot_no})
        if flag:
            message = "补充成功"
        else:
            message = "重新绑定成功"
        return Response(message)


@method_decorator([api_recorder], name="dispatch")
class EquipStatusViewSet(mixins.CreateModelMixin,
                         mixins.ListModelMixin,
                         GenericViewSet):
    """
    list:
        机台状况反馈列表
    retrieve:
        机台状况反馈详情
    create:
        创建机台状况反馈
    """
    queryset = EquipStatus.objects.filter(delete_flag=False)
    pagination_class = SinglePageNumberPagination
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = EquipStatusSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ('id',)
    filter_class = EquipStatusFilter

    def list(self, request, *args, **kwargs):
        actual_trains = request.query_params.get("actual_trains", '')
        if "," in actual_trains:
            train_list = actual_trains.split(",")
            try:
                queryset = self.filter_queryset(self.get_queryset().filter(current_trains__gte=train_list[0],
                                                                           current_trains__lte=train_list[-1]))
            except:
                return Response({"actual_trains": "请输入: <开始车次>,<结束车次>。这类格式"})
        else:
            queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@method_decorator([api_recorder], name="dispatch")
class PlanStatusViewSet(mixins.CreateModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        GenericViewSet):
    """
    list:
        计划状态变更列表
    retrieve:
        计划状态变更详情
    create:
        创建计划状态变更
    """
    queryset = PlanStatus.objects.filter(delete_flag=False)
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = PlanStatusSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ('id',)
    filter_class = PlanStatusFilter


@method_decorator([api_recorder], name="dispatch")
class ExpendMaterialViewSet(mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.ListModelMixin,
                            GenericViewSet):
    """
    list:
        原材料消耗列表
    retrieve:
        原材料消耗详情
    create:
        创建原材料消耗
    """
    queryset = ExpendMaterial.objects.filter(delete_flag=False)
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = ExpendMaterialSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ('id',)
    filter_class = ExpendMaterialFilter


@method_decorator([api_recorder], name="dispatch")
class OperationLogViewSet(mixins.CreateModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.ListModelMixin,
                          GenericViewSet):
    """
    list:
        操作日志列表
    retrieve:
        操作日志详情
    create:
        创建操作日志
    """
    queryset = OperationLog.objects.filter(delete_flag=False)
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = OperationLogSerializer


@method_decorator([api_recorder], name="dispatch")
class QualityControlViewSet(mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.ListModelMixin,
                            GenericViewSet):
    """
    list:
        质检结果列表
    retrieve:
        质检结果详情
    create:
        创建质检结果
    """
    queryset = QualityControl.objects.filter(delete_flag=False)
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = QualityControlSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ('id',)
    filter_class = QualityControlFilter


@method_decorator([api_recorder], name="dispatch")
class PlanRealityViewSet(mixins.ListModelMixin,
                         GenericViewSet):

    def list(self, request, *args, **kwargs):
        params = request.query_params
        search_time_str = params.get("search_time")
        target_equip_no = params.get('equip_no')
        time_now = datetime.datetime.now()
        if search_time_str:
            if not re.search(r"[0-9]{4}\-[0-9]{1,2}\-[0-9]{1,2}", search_time_str):
                raise ValidationError("查询时间格式异常")
        else:
            search_time_str = str(datetime.date.today())
        if target_equip_no:
            pcp_set = ProductClassesPlan.objects.filter(work_schedule_plan__plan_schedule__day_time=search_time_str,
                                                        work_schedule_plan__plan_schedule__work_schedule__work_procedure__global_name="密炼",
                                                        equip__equip_no=target_equip_no,
                                                        delete_flag=False).select_related(
                'equip__equip_no',
                'product_batching__stage_product_batch_no',
                'product_day_plan_id', 'time', 'product_batching__stage__global_name')
        else:
            pcp_set = ProductClassesPlan.objects.filter(work_schedule_plan__plan_schedule__day_time=search_time_str,
                                                        work_schedule_plan__plan_schedule__work_schedule__work_procedure__global_name="密炼",
                                                        delete_flag=False).select_related(
                'equip__equip_no',
                'product_batching__stage_product_batch_no',
                'product_day_plan_id', 'time', 'product_batching__stage__global_name')
        # 班次计划号列表
        uid_list = pcp_set.values_list("plan_classes_uid", flat=True)
        # 日计划号对比
        day_plan_list_temp = pcp_set.values_list("product_batching__stage_product_batch_no", "equip__equip_no")
        day_plan_list = list(set([x[0] + x[1] for x in day_plan_list_temp]))
        tf_set = TrainsFeedbacks.objects.values('plan_classes_uid').filter(plan_classes_uid__in=uid_list).annotate(
            actual_trains=Max('actual_trains'), actual_weight=Sum('actual_weight'), begin_time=Min('begin_time'),
            actual_time=Max('product_time'))
        tf_dict = {x.get("plan_classes_uid"): [x.get("actual_trains"), x.get("actual_weight"),
                                               x.get("begin_time", time_now), x.get("actual_time", time_now),
                                               (x.get("actual_time", time_now) - x.get("begin_time",
                                                                                       time_now)).total_seconds()] for x
                   in tf_set}
        day_plan_dict = {x: {"plan_weight": 0, "plan_trains": 0, "actual_trains": 0, "actual_weight": 0, "plan_time": 0,
                             "start_rate": None, "all_time": 0}
                         for x in day_plan_list}
        pcp_data = pcp_set.values("plan_classes_uid", "weight", "plan_trains", 'equip__equip_no',
                                  'product_batching__stage_product_batch_no',
                                  'product_day_plan_id', 'time', 'product_batching__stage__global_name')
        for pcp in pcp_data:
            day_plan_id = pcp.get("product_batching__stage_product_batch_no") + pcp.get("equip__equip_no")
            plan_classes_uid = pcp.get('plan_classes_uid')
            day_plan_dict[day_plan_id].update(
                equip_no=pcp.get('equip__equip_no'),
                product_no=pcp.get('product_batching__stage_product_batch_no'),
                stage=pcp.get('product_batching__stage__global_name'))
            day_plan_dict[day_plan_id]["plan_weight"] = pcp.get('weight', 0)
            day_plan_dict[day_plan_id]["plan_trains"] += pcp.get('plan_trains', 0)
            day_plan_dict[day_plan_id]["plan_time"] += pcp.get('time', 0)
            if not tf_dict.get(plan_classes_uid):
                day_plan_dict[day_plan_id]["actual_trains"] += 0
                day_plan_dict[day_plan_id]["actual_weight"] += 0
                continue
            day_plan_dict[day_plan_id]["actual_trains"] += tf_dict[plan_classes_uid][0]
            day_plan_dict[day_plan_id]["actual_weight"] += round(tf_dict[plan_classes_uid][1] / 100, 2)
            day_plan_dict[day_plan_id]["begin_time"] = tf_dict[plan_classes_uid][2].strftime('%Y-%m-%d %H:%M:%S') if \
                tf_dict[plan_classes_uid][2] else ""
            day_plan_dict[day_plan_id]["actual_time"] = tf_dict[plan_classes_uid][3].strftime('%Y-%m-%d %H:%M:%S')
            day_plan_dict[day_plan_id]["plan_time"] += pcp.get("time", 0)
            day_plan_dict[day_plan_id]["all_time"] += tf_dict[plan_classes_uid][4]
        temp_data = {}
        for equip_no in EQUIP_LIST:
            temp_data[equip_no] = []
            for temp in day_plan_dict.values():
                if temp.get("equip_no") == equip_no:
                    temp_data[equip_no].append(temp)
        datas = []
        for equip_data in temp_data.values():
            equip_data.sort(key=lambda x: (x.get("equip_no", ""), x.get("begin_time", "")))
            new_equip_data = []
            for _ in equip_data:
                _.update(sn=equip_data.index(_) + 1)
                _.update(ach_rate=round(_.get('actual_trains') / _.get('plan_trains') * 100, 2))
                new_equip_data.append(_)
            datas += new_equip_data
        return Response({"data": datas})


@method_decorator([api_recorder], name="dispatch")
class ProductActualViewSet(mixins.ListModelMixin,
                           GenericViewSet):
    """密炼实绩"""

    def list(self, request, *args, **kwargs):
        params = request.query_params
        day_time = params.get("search_time", datetime.datetime.now().date())
        target_equip_no = params.get('equip_no')
        plan_queryset = ProductClassesPlan.objects.filter(delete_flag=False,
                                                          work_schedule_plan__plan_schedule__day_time=day_time
                                                          ).order_by('equip__equip_no')
        if target_equip_no:
            plan_queryset = plan_queryset.filter(equip__equip_no=target_equip_no)
        plan_data = plan_queryset.values(
            'equip__equip_no',
            'product_batching__stage_product_batch_no',
            'work_schedule_plan__classes__global_name'
        ).annotate(plan_trains=Sum('plan_trains')).values(equip_no=F('equip__equip_no'),
                                                           product_no=F('product_batching__stage_product_batch_no'),
                                                           plan_trains=F('plan_trains'),
                                                           classes=F('work_schedule_plan__classes__global_name'))
        plan_data_dict = {item['equip_no']+item['product_no']+item['classes']: item for item in plan_data}

        plan_classes_uid_list = plan_queryset.values_list('plan_classes_uid', flat=True)
        tf_set = TrainsFeedbacks.objects.filter(
            plan_classes_uid__in=plan_classes_uid_list
        ).values('equip_no',
                 'product_no',
                 'classes'
                 ).annotate(
            actual_trains=Count('actual_trains'),
            actual_weight=Max('actual_weight'),
            plan_weight=Max('plan_weight')
        ).values('equip_no', 'product_no', 'classes', 'actual_trains', 'actual_weight', 'plan_weight')
        actual_data_dict = {item['equip_no']+item['product_no']+item['classes']: item for item in tf_set}
        ret = {}

        for key, value in plan_data_dict.items():
            if key in actual_data_dict:
                value['actual_trains'] = actual_data_dict[key]['actual_trains']
                value['actual_weight'] = actual_data_dict[key]['actual_weight']
                value['plan_weight'] = actual_data_dict[key]['plan_weight']
            else:
                value['actual_trains'] = 0
                value['actual_weight'] = 0
                value['plan_weight'] = 0
            equip_product_key = value['equip_no']+value['product_no']
            if equip_product_key not in ret:
                classes_data = {'早班': {'plan_trains': 0, 'actual_trains': 0, 'classes': '早班'},
                                '中班': {'plan_trains': 0, 'actual_trains': 0, 'classes': '中班'},
                                '夜班': {'plan_trains': 0, 'actual_trains': 0, 'classes': '夜班'}}
                classes_data[value['classes']] = {'plan_trains': value['plan_trains'],
                                                  'actual_trains': value['actual_trains'],
                                                  'classes': value['classes']}
                ret[equip_product_key] = {
                               'equip_no': value['equip_no'],
                               'product_no': value['product_no'],
                               'plan_trains': value['plan_trains'],
                               'actual_trains': value['actual_trains'],
                               'plan_weight': value['plan_weight'],
                               'actual_weight': value['actual_weight'],
                               'classes_data': classes_data,
                           }
            else:
                ret[equip_product_key]['plan_trains'] += value['plan_trains']
                ret[equip_product_key]['actual_trains'] += value['actual_trains']
                ret[equip_product_key]['classes_data'][value['classes']] = {
                    'plan_trains': value['plan_trains'],
                    'actual_trains': value['actual_trains'],
                    'classes': value['classes']}

        for item in ret.values():
            item['classes_data'] = item['classes_data'].values()
        ret = {"data": ret.values()}
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class ProductionRecordViewSet(mixins.ListModelMixin,
                              GenericViewSet):
    queryset = PalletFeedbacks.objects.filter(delete_flag=False).order_by("factory_date", 'equip_no', 'classes',
                                                                          'product_no', 'begin_trains')
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = ProductionRecordSerializer
    filter_backends = [DjangoFilterBackend, ]
    filter_class = PalletFeedbacksFilter

    def get_queryset(self):
        queryset = self.queryset
        st = self.request.query_params.get('st')
        et = self.request.query_params.get('et')
        if st:
            queryset = queryset.filter(factory_date__gte=st[:10])
        if et:
            queryset = queryset.filter(factory_date__lte=et[:10])
        return queryset


@method_decorator([api_recorder], name="dispatch")
class MaterialInventory(GenericViewSet,
                        mixins.ListModelMixin, ):

    def get_queryset(self):
        return

    def list(self, request, *args, **kwargs):
        ret = requests.get("http://49.235.45.128:8169/storageSpace/GetInventoryCount")
        ret_json = json.loads(ret.text)
        results = []
        for i in ret_json.get("datas"):
            results = [{
                "sn": 1,
                "material_no": i.get('material_no'),
                "material_name": i.get('materialName'),
                "material_type": "1MB",
                "qty": 11,
                "unit": "吨",
                "unit_weight": 1,
                "total_weight": 1,
                "need_weight": 1,
                "standard_flag": True,
                "site": "立库",
            }]
        return Response({'results': results})


@method_decorator([api_recorder], name="dispatch")
class ProductInventory(GenericViewSet,
                       mixins.ListModelMixin, ):

    def get_queryset(self):
        return

    def list(self, request, *args, **kwargs):
        results = [{"sn": 1,
                    "id": 1,
                    "material_id": 1,
                    "material_no": "C9001",
                    "material_name": "C9001",
                    "material_type_id": 1,
                    "material_type": "天然胶",
                    "qty": 11,
                    "unit": "吨",
                    "unit_weight": 1,
                    "total_weight": 1,
                    "need_weight": 1,
                    "site": "安吉仓库",
                    "standard_flag": True,
                    }, {"sn": 2,
                        "id": 2,
                        "material_id": 2,
                        "material_no": "C9002",
                        "material_name": "C9002",
                        "material_type_id": 1,
                        "material_type": "天然胶",
                        "qty": 11,
                        "unit": "吨",
                        "unit_weight": 1,
                        "total_weight": 1,
                        "need_weight": 1,
                        "site": "安吉仓库",
                        "standard_flag": False,
                        }]
        return Response({'results': results})


@method_decorator([api_recorder], name="dispatch")
class TrainsFeedbacksBatch(APIView):
    """批量同步车次生产数据接口"""

    @atomic
    def post(self, request):
        serializer = TrainsFeedbacksBatchSerializer(data=request.data, many=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("sync success", status=201)


@method_decorator([api_recorder], name="dispatch")
class PalletFeedbacksBatch(APIView):
    """批量同步托次生产数据接口"""

    @atomic
    def post(self, request):
        serializer = PalletFeedbacksSerializer(data=request.data, many=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("sync success", status=201)


@method_decorator([api_recorder], name="dispatch")
class EquipStatusBatch(APIView):
    """批量同步设备生产数据接口"""

    @atomic
    def post(self, request):
        data_list = request.data
        instance_list = []
        for x in data_list:
            x.pop("created_username")
            x.pop("delete_user")
            x.pop("last_updated_user")
            x.pop("created_user")
            instance_list.append(EquipStatus(**x))
        EquipStatus.objects.bulk_create(instance_list)
        return Response("sync success", status=201)


@method_decorator([api_recorder], name="dispatch")
class PlanStatusBatch(APIView):
    """批量同步计划状态数据接口"""

    @atomic
    def post(self, request):
        serializer = PlanStatusSerializer(data=request.data, many=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("sync success", status=201)


@method_decorator([api_recorder], name="dispatch")
class ExpendMaterialBatch(APIView):
    """批量同步原材料消耗数据接口"""

    @atomic
    def post(self, request):
        serializer = ExpendMaterialSerializer(data=request.data, many=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("sync success", status=201)


@method_decorator([api_recorder], name="dispatch")
class ProcessFeedbackBatch(APIView):
    """批量同步原材料消耗数据接口"""

    @atomic
    def post(self, request):
        serializer = ProcessFeedbackSerializer(data=request.data, many=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("sync success", status=201)


@method_decorator([api_recorder], name="dispatch")
class AlarmLogBatch(APIView):
    """批量同步原材料消耗数据接口"""

    @atomic
    def post(self, request):
        serializer = AlarmLogSerializer(data=request.data, many=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("sync success", status=201)


@method_decorator([api_recorder], name="dispatch")
class PalletTrainFeedback(APIView):
    """获取托盘开始车次-结束车次的数据，过滤字段：equip_no=设备编码&factory_date=工厂日期
        &classes=班次&product_no=胶料编码&stage=胶料段次&is_tested=是否已检测（Y已检测 N未检测）"""

    def get(self, request):
        equip_no = self.request.query_params.get('equip_no')
        factory_date = self.request.query_params.get('factory_date')
        classes = self.request.query_params.get('classes')
        product_no = self.request.query_params.get('product_no')
        stage = self.request.query_params.get('stage')
        if not all([equip_no, factory_date, classes, product_no]):
            raise ValidationError('缺少参数')
        pallet_feed_backs = PalletFeedbacks.objects.filter(
            equip_no=equip_no,
            factory_date=factory_date,
            classes=classes,
            product_no=product_no
        )
        if stage:
            pallet_feed_backs = pallet_feed_backs.filter(product_no__icontains=stage)
        ret = []
        trains = []
        for pallet_feed_back in pallet_feed_backs:
            begin_trains = pallet_feed_back.begin_trains
            end_trains = pallet_feed_back.end_trains
            for i in range(begin_trains, end_trains + 1):
                if i not in trains:
                    trains.append(i)
                else:
                    continue
                # test_order = MaterialTestOrder.objects.filter(product_no=product_no,
                #                                               production_equip_no=equip_no,
                #                                               production_factory_date=factory_date,
                #                                               actual_trains=i,
                #                                               production_class=classes).first()
                data = {
                    'product_no': pallet_feed_back.product_no,
                    'lot_no': pallet_feed_back.lot_no,
                    'classes': pallet_feed_back.classes,
                    'equip_no': pallet_feed_back.equip_no,
                    'actual_trains': i,
                    'plan_classes_uid': pallet_feed_back.plan_classes_uid,
                    # 'factory_date': pallet_feed_back.end_time,
                    'factory_date': pallet_feed_back.factory_date,
                    'is_tested': 'N'
                    # 'is_tested': 'Y' if test_order else 'N'
                }
                ret.append(data)
        ret.sort(key=lambda x: x.get('actual_trains'))
        return Response(ret)


class UpdateUnReachedCapacityCauseView(UpdateAPIView):
    queryset = UnReachedCapacityCause.objects.all()
    serializer_class = UnReachedCapacityCauseSerializer

    def get_object(self):
        data = dict(self.request.data)
        filter_kwargs = {
            'factory_date': data.get('factory_date'),
            'classes': data.get('classes'),
            'equip_no': data.get('equip_no')
        }
        obj = get_object_or_404(self.get_queryset(), **filter_kwargs)
        return obj


def get_trains_feed_backs_query_params(view):
    query_params = view.request.query_params
    hour_step = int(query_params.get('hour_step', 2))
    classes = query_params.getlist('classes[]')
    factory_date = query_params.get('factory_date', datetime.datetime.now().strftime('%Y-%m-%d'))
    return hour_step, classes, factory_date


def zno_(obj):
    return int(obj['equip_no'].lower()[1:])


# 产量计划实际分析
@method_decorator([api_recorder], name="dispatch")
class ProductionPlanRealityAnalysisView(ListAPIView):
    queryset = TrainsFeedbacks.objects.all()
    serializer_class = ProductionPlanRealityAnalysisSerializer

    def get_serializer_context(self):
        hour_step = get_trains_feed_backs_query_params(self)[0]
        context = super().get_serializer_context()
        context.update({'hour_step': hour_step})
        return context

    def list(self, request, *args, **kwargs):
        hour_step, classes, factory_date = get_trains_feed_backs_query_params(self)
        trains_feed_backs = TrainsFeedbacks.objects \
            .filter(factory_date=factory_date) \
            .values('factory_date',
                    'classes',
                    'equip_no',
                    'plan_classes_uid'
                    ) \
            .order_by('-factory_date') \
            .annotate(plan_train_sum=Max('plan_trains'),
                      finished_train_count=Max('actual_trains'))
        data = {
            'headers': list(range(hour_step, 13, hour_step))
        }
        for class_ in classes:
            feed_backs = trains_feed_backs.filter(classes=class_)
            feed_backs = sorted(feed_backs, key=zno_)
            train_count_group = {}
            for feed_back in feed_backs:
                train_counts = train_count_group.setdefault((feed_back['factory_date'],
                                                             feed_back['classes'],
                                                             feed_back['equip_no']), {
                                                                'plan_train_sum': 0,
                                                                'finished_train_count': 0
                                                            })
                train_counts['plan_train_sum'] += feed_back['plan_train_sum']
                train_counts['finished_train_count'] += feed_back['finished_train_count']
            group_feed_backs = []
            for key, value in train_count_group.items():
                feed_back = {
                    'factory_date': key[0],
                    'classes': key[1],
                    'equip_no': key[2],
                }
                feed_back.update(**value)
                group_feed_backs.append(feed_back)
            serializer = self.get_serializer(group_feed_backs, many=True)
            data[class_] = serializer.data
        return Response(data)


# 区间产量统计
@method_decorator([api_recorder], name="dispatch")
class IntervalOutputStatisticsView(APIView):

    def get(self, request, *args, **kwargs):
        hour_step, classes, factory_date = get_trains_feed_backs_query_params(self)

        if not TrainsFeedbacks.objects.filter(factory_date=factory_date).exists():
            return Response({})
        day_start_time = datetime.datetime.strptime(factory_date + ' 08:00:00', "%Y-%m-%d %H:%M:%S")
        factory_end_time = day_start_time + datetime.timedelta(days=1)

        day_end_time = (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        day_end_time = day_end_time[:14] + '00:00'
        day_end_time = datetime.datetime.strptime(day_end_time, "%Y-%m-%d %H:%M:%S")
        if day_end_time > factory_end_time:
            day_end_time = factory_end_time

        time_spans = []
        end_time = day_start_time
        while end_time < day_end_time:
            time_spans.append(end_time)
            end_time = end_time + datetime.timedelta(hours=hour_step)
        time_spans.append(day_end_time)

        data = {
            'equips': list(Equip.objects.filter(
                category__equip_type__global_name='密炼设备'
            ).order_by('equip_no').values_list('equip_no', flat=True))
        }

        for class_ in classes:
            data[class_] = []
            for i in range(len(time_spans) - 1):
                time_span_data = {}
                data[class_].append(time_span_data)
                interval_trains_feed_backs = None
                total_trains_feed_backs = None
                if class_ == '整日':
                    interval_trains_feed_backs = TrainsFeedbacks.objects \
                        .filter(factory_date=factory_date,
                                end_time__gte=time_spans[i],
                                end_time__lte=time_spans[i + 1]) \
                        .values('equip_no') \
                        .annotate(interval_finished_train_count=Count('id', distinct=True))

                    total_trains_feed_backs = TrainsFeedbacks.objects \
                        .filter(factory_date=factory_date,
                                end_time__gte=day_start_time,
                                end_time__lte=time_spans[i + 1]) \
                        .values('equip_no') \
                        .annotate(total_finished_train_count=Count('id', distinct=True))
                else:
                    interval_trains_feed_backs = TrainsFeedbacks.objects \
                        .filter(classes=class_,
                                factory_date=factory_date,
                                end_time__gte=time_spans[i],
                                end_time__lte=time_spans[i + 1]) \
                        .values('equip_no') \
                        .annotate(interval_finished_train_count=Count('id', distinct=True))

                    total_trains_feed_backs = TrainsFeedbacks.objects \
                        .filter(classes=class_,
                                factory_date=factory_date,
                                end_time__gte=day_start_time,
                                end_time__lte=time_spans[i + 1]) \
                        .values('equip_no') \
                        .annotate(total_finished_train_count=Count('id', distinct=True))

                time_span_data['time_span'] = "{0}:00-{1}:00".format(time_spans[i].hour,
                                                                     time_spans[i + 1].hour
                                                                     if time_spans[i + 1].hour != time_spans[i].hour
                                                                     else time_spans[i + 1].hour + hour_step)

                for total_trains_feed_back in total_trains_feed_backs:
                    equip_no = total_trains_feed_back.get('equip_no')
                    same_equip_no_interval_trains_feed_back = None
                    for interval_trains_feed_back in interval_trains_feed_backs:
                        if interval_trains_feed_back.get('equip_no') == equip_no:
                            same_equip_no_interval_trains_feed_back = interval_trains_feed_back
                            break
                    time_span_data[equip_no] = (total_trains_feed_back
                                                .get('total_finished_train_count'),
                                                same_equip_no_interval_trains_feed_back
                                                .get('interval_finished_train_count')
                                                if same_equip_no_interval_trains_feed_back else 0)
        return Response(data)


# 将群控的车次报表移植过来 （中间表就吗，没有用了 关于中间表的代码直接删除了）
@method_decorator([api_recorder], name="dispatch")
class TrainsFeedbacksAPIView(mixins.ListModelMixin,
                             GenericViewSet):
    """车次报表展示接口"""
    queryset = TrainsFeedbacks.objects.all().order_by('factory_date', 'equip_no', 'product_no', 'actual_trains')
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = TrainsFeedbacksSerializer2
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filter_class = TrainsFeedbacksFilter
    FILE_NAME = '车次报表'
    EXPORT_FIELDS_DICT = {
        'No': 'no',
        '机台': 'equip_no',
        '配方编号': 'product_no',
        '班次': 'classes',
        '计划编号': 'plan_classes_uid',
        '开始时间': 'begin_time',
        '结束时间': 'end_time',
        '设定车次': 'plan_trains',
        '实际车次': 'actual_trains',
        '本/远控': 'control_mode',
        '手/自动': 'operating_type',
        '总重量(kg)': 'actual_weight',
        '排胶时间(s)': 'evacuation_time',
        '排胶温度(°c)': 'evacuation_temperature',
        '排胶能量(J)': 'evacuation_energy',
        '操作人': 'operation_user',
        '存盘时间(s)': 'product_time',
        '密炼时间(s)': 'mixer_time',
        '间隔时间(s)': 'interval_time',
    }

    def list(self, request, *args, **kwargs):
        params = request.query_params
        trains = params.get("trains")
        queryset = self.filter_queryset(self.get_queryset())
        st = params.get('begin_time')
        et = params.get('end_time')
        export = params.get('export')
        if st:
            queryset = queryset.filter(factory_date__gte=st[:10])
        if et:
            queryset = queryset.filter(factory_date__lte=et[:10])
        if trains:
            try:
                train_range = trains.split(",")
            except:
                raise ValidationError("trains参数错误,参考: trains=5,10")
            queryset = queryset.filter(actual_trains__range=train_range)
        if export:
            data = list(self.get_serializer(queryset, many=True).data)
            [i.update({'no': data.index(i) + 1}) for i in data]
            return gen_template_response(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data_list = serializer.data
            data_list.append({'version': 'v2'})
            return self.get_paginated_response(data_list)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@method_decorator([api_recorder], name="dispatch")
class CurveInformationList(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                           GenericViewSet):
    """工艺曲线信息"""
    queryset = EquipStatus.objects.filter()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = SinglePageNumberPagination
    serializer_class = CurveInformationSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]

    def get_queryset(self):
        feed_back_id = self.request.query_params.get('feed_back_id')
        try:
            tfb_obk = TrainsFeedbacks.objects.get(id=feed_back_id)
            irc_queryset = EquipStatus.objects.filter(equip_no=tfb_obk.equip_no,
                                                      plan_classes_uid=tfb_obk.plan_classes_uid,
                                                      product_time__gte=tfb_obk.begin_time,
                                                      product_time__lte=tfb_obk.end_time).order_by('product_time')
        except:
            raise ValidationError('车次产出反馈或车次报表工艺曲线数据表没有数据')

        return irc_queryset


@method_decorator([api_recorder], name="dispatch")
class MixerInformationList(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                           GenericViewSet):
    """密炼信息"""
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    serializer_class = MixerInformationSerializer2

    def get_queryset(self):
        feed_back_id = self.request.query_params.get('feed_back_id')
        params = self.request.query_params
        equip_no = params.get("equip_no", None)
        try:
            tfb_obk = TrainsFeedbacks.objects.get(id=feed_back_id)
            irm_queryset = ProcessFeedback.objects.filter(plan_classes_uid=tfb_obk.plan_classes_uid,
                                                          equip_no=tfb_obk.equip_no,
                                                          product_no=tfb_obk.product_no,
                                                          current_trains=tfb_obk.actual_trains
                                                          )
        except:
            raise ValidationError('车次产出反馈或胶料配料标准步序详情没有数据')
        return irm_queryset


@method_decorator([api_recorder], name="dispatch")
class WeighInformationList(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                           GenericViewSet):
    """称量信息"""
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    serializer_class = WeighInformationSerializer2

    def get_queryset(self):
        params = self.request.query_params
        equip_no = params.get("equip_no", None)

        feed_back_id = self.request.query_params.get('feed_back_id')
        try:
            tfb_obk = TrainsFeedbacks.objects.get(id=feed_back_id)
            irw_queryset = ExpendMaterial.objects.filter(equip_no=tfb_obk.equip_no,
                                                         plan_classes_uid=tfb_obk.plan_classes_uid,
                                                         product_no=tfb_obk.product_no,
                                                         trains=tfb_obk.actual_trains, delete_flag=False)
        except:
            raise ValidationError('车次产出反馈或车次报表材料重量没有数据')
        return irw_queryset


@method_decorator([api_recorder], name="dispatch")
class AlarmLogList(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                   GenericViewSet):
    """报警信息"""
    queryset = AlarmLog.objects.filter()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = AlarmLogSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]

    def get_queryset(self):
        feed_back_id = self.request.query_params.get('feed_back_id')
        try:
            tfb_obk = TrainsFeedbacks.objects.get(id=feed_back_id)
            al_queryset = AlarmLog.objects.filter(equip_no=tfb_obk.equip_no,
                                                  product_time__gte=tfb_obk.begin_time,
                                                  product_time__lte=tfb_obk.end_time).order_by('product_time')
        except:
            raise ValidationError('报警日志没有数据')

        return al_queryset


@method_decorator([api_recorder], name="dispatch")
class MaterialOutputView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        param = request.query_params
        material_no = param.get('material_no')
        query_unit = param.get('query_unit')
        groups = ['product_no']
        filters = {'product_time__year': datetime.datetime.now().strftime('%Y')}
        unit = '吨/天'
        num = 365
        if material_no:
            filters.update(product_no=material_no)
        if not query_unit:
            query_unit = 'day'
            num = 365
            unit = '吨/天'
        if query_unit == 'year':
            num = 1
            unit = '吨/年'
        if query_unit == 'month':
            num = 12
            unit = '吨/月'
        if query_unit == 'classes':
            temp_set = TrainsFeedbacks.objects.values('classes').annotate().values_list('classes', flat=True).distinct()
            num = len(set([x if x in ['早班', '中班', '夜班'] else '夜班' for x in temp_set]))
            unit = '吨/班'
        if query_unit == 'hour':
            num = 365 * 24
            unit = '吨/小时'
        product_set = TrainsFeedbacks.objects.values(*groups).filter(**filters).annotate(
            all_weight=Sum('actual_weight'))
        data = [{"material_no": x.get("product_no"), 'output': round(x.get("all_weight", 0) / num, 2)} for x in
                product_set]
        ret = {
            "time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "unit": unit,
            "data": data
        }
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class EquipProductRealView(APIView):
    permission_classes = (IsAuthenticated,)

    def _instance_prepare(self, ret, equip_no):
        _ = EquipStatus.objects.filter(equip_no=equip_no).order_by('product_time').last()
        if not _:
            return
        plan_uid = _.plan_classes_uid
        try:
            plan = ProductClassesPlan.objects.filter(plan_classes_uid=plan_uid).last()
            plan_trains = plan.plan_trains
            product_no = plan.product_batching.stage_product_batch_no
        except:
            raise ValidationError(f"计划:{plan_uid}缺失")
        temp = {
            "equip_no": _.equip_no,
            "temperature": _.temperature,
            "rpm": _.rpm,
            "energy": _.energy,
            "power": _.power,
            "pressure": _.pressure,
            "status": _.status,
            "material_no": product_no,
            "current_trains": _.current_trains,
            "plan_trains": plan_trains,
            "actual_trains": _.current_trains,
            "product_time": _.product_time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        ret['data'].append(temp)

    def get(self, request, *args, **kwargs):
        equip_no = request.query_params.get("equip_no")
        ret = {
            "data": []
        }
        if equip_no:
            self._instance_prepare(ret, equip_no)
        else:
            self._another(ret)
        return Response(ret)

    def _another(self, ret):
        temp_set = EquipStatus.objects.values("equip_no").annotate(id=Max('id')).values('id', 'equip_no')
        for temp in temp_set:
            _ = EquipStatus.objects.get(id=temp.get('id'))
            try:
                plan = ProductClassesPlan.objects.filter(plan_classes_uid=_.plan_classes_uid).last()
                plan_trains = plan.plan_trains
                product_no = plan.product_batching.stage_product_batch_no
            except Exception as e:
                raise ValidationError(f"错误信息:{e}")
            new = {
                "equip_no": _.equip_no,
                "temperature": _.temperature,
                "rpm": _.rpm,
                "energy": _.energy,
                "power": _.power,
                "pressure": _.pressure,
                "status": _.status,
                "material_no": product_no,
                "current_trains": _.current_trains,
                "plan_trains": plan_trains,
                "actual_trains": _.current_trains,
                "product_time": _.product_time.strftime('%Y-%m-%d %H:%M:%S'),
            }
            ret["data"].append(new)


@method_decorator([api_recorder], name="dispatch")
class MaterialPassRealView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        data = None
        query_unit = self.request.query_params.get('query_unit', 'day')
        material_no = self.request.query_params.get('material_no')
        batch_product_nos = BatchProductNo.objects.all()
        if material_no:
            batch_product_nos = BatchProductNo.objects.filter(
                product_no=material_no)
        if query_unit == 'day':
            data = BatchProductNoDateZhPassSerializer(
                batch_product_nos,
                many=True,
                context={'batch_date_model': BatchDay}).data
        elif query_unit == 'month':
            data = BatchProductNoDateZhPassSerializer(
                batch_product_nos,
                many=True,
                context={'batch_date_model': BatchMonth}).data
        elif query_unit == 'year':
            data = BatchProductNoDateZhPassSerializer(
                batch_product_nos,
                many=True,
                context={'batch_date_model': BatchYear}).data
        elif query_unit == 'classes':
            data = BatchProductNoClassZhPassSerializer(
                batch_product_nos,
                many=True).data
        else:
            raise ValidationError('查询维度不支持')
        return Response({
            'time': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data': data
        })


@method_decorator([api_recorder], name="dispatch")
class MaterialTankStatusList(APIView):
    def get(self, request):
        """机台编号和罐编号"""
        mts_set = MaterialTankStatus.objects.values('equip_no', 'tank_no').distinct()
        return Response({"results": mts_set})


@method_decorator([api_recorder], name="dispatch")
class WeekdayProductStatisticsView(APIView):

    def get(self, request):
        """"""
        # 计算上一周是几号到几号
        params = request.query_params

        unit = params.get("unit")
        value = params.get("value")
        query_type = params.get("type")
        if params:
            if unit != "day" or query_type != "week" or value != "lastweek":
                raise ValidationError("暂不支持该粒度查询，敬请期待")
        temp = datetime.date.today().isoweekday()
        monday = datetime.date.today() - datetime.timedelta(days=(6 + temp))
        sunday = datetime.date.today() - datetime.timedelta(temp)
        # 相对简单的查询 存在脏数据会导致结果误差 另一种方案是先根据uid分类取最终值的id，再统计相对麻烦  后续补充
        temp_list = list(TrainsFeedbacks.objects.filter(factory_date__gte=monday, factory_date__lte=sunday).
                         values("equip_no", "factory_date"). \
                         annotate(all_weight=Sum("actual_weight")).order_by("factory_date").values("equip_no",
                                                                                                   "factory_date",
                                                                                                   "all_weight"))
        # __week=4查当周  3，2，1 上周 上上周， 上上上周
        # temp_list = list(
        #     TrainsFeedbacks.objects.filter(factory_date__week=3).values("equip_no", "factory_date"). \
        #         annotate(all_weight=Sum("actual_weight")).order_by("factory_date").values("equip_no", "factory_date",
        #                                                                                   "all_weight"))
        ret = {"Z%02d" % x: [] for x in range(1, 16)}
        day_week_map = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
        for data in temp_list:
            try:
                index = data["factory_date"].isoweekday()
            except:
                continue
            ret[data["equip_no"]].append({day_week_map[index]: str(data["all_weight"] / 1000)})
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class ProductionStatisticsView(APIView):

    def get(self, request):
        params = request.query_params
        unit = params.get("unit")
        value = params.get("value")
        query_type = params.get("type")
        ret = None
        if not value:
            raise ValidationError("value参数必传")
        try:
            if query_type == "year":
                my_key = value[0:4]
                value = datetime.datetime.strptime(value, "%Y-%m").year
                temp_set = TrainsFeedbacks.objects.filter(factory_date__year=value)
                if unit == "day":
                    middle_list = list(temp_set.values("factory_date").annotate(all_weight=Sum("actual_weight"))
                                       .order_by("factory_date").values("factory_date", "all_weight"))
                    ret = {my_key: [{_["factory_date"].strftime('%Y-%m-%d'): str(_["all_weight"] / 1000)} for _ in
                                    middle_list]}
                elif unit == "month":
                    middle_list = list(temp_set.annotate(month=TruncMonth('factory_date')).values("month")
                                       .annotate(all_weight=Sum("actual_weight") / 1000).order_by("factory_date")
                                       .values("month", "all_weight"))
                    ret = {value: [{_["month"].strftime('%Y-%m'): str(_["all_weight"])} for _ in middle_list]}
            elif query_type == "month":
                my_key = value[0:7]
                month = datetime.datetime.strptime(value, "%Y-%m").month
                year = datetime.datetime.strptime(value, "%Y-%m").year
                temp_set = TrainsFeedbacks.objects.filter(factory_date__month=month, factory_date__year=year)
                if unit == "day":
                    middle_list = list(temp_set.values("factory_date").annotate(all_weight=Sum("actual_weight"))
                                       .order_by("factory_date").values("factory_date", "all_weight"))
                    ret = {my_key: [{_["factory_date"].strftime('%Y-%m-%d'): str(_["all_weight"] / 1000)} for _ in
                                    middle_list]}
        except Exception as e:
            raise ValidationError(f"参数错误，请检查是否符合接口标准: {e}")
        if not ret:
            raise ValidationError("参数错误，请检查是否符合接口标准")
        else:
            return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class DayCapacityView(APIView):

    def get(self, request):
        params = request.query_params
        value = params.get("value")
        query_type = params.get("type")
        if not value:
            raise ValidationError("value值必传，")
        try:
            factory_date = datetime.datetime.strptime(value, "%Y-%m-%d")
        except:
            raise ValidationError("请输入%Y-%m-%d格式的日期")
        temp_set = None
        if query_type == "week":
            monday = factory_date - timedelta(days=factory_date.weekday())
            sunday = factory_date + timedelta(days=6 - factory_date.weekday())
            # __week=4查当周  3，2，1 上周 上上周， 上上上周
            temp_set = TrainsFeedbacks.objects.filter(factory_date__range=(monday, sunday))
        elif query_type == "month":
            month = factory_date.month
            temp_set = TrainsFeedbacks.objects.filter(factory_date__month=month, factory_date__year=factory_date.year)
        elif query_type == "day":
            temp_set = TrainsFeedbacks.objects.filter(factory_date=factory_date)
        elif query_type == "year":
            year = factory_date.year
            temp_set = TrainsFeedbacks.objects.filter(factory_date__year=year)
        if temp_set is None:
            raise ValidationError("参数错误")
        temp_list = list(temp_set.values("equip_no", "product_no").annotate(output=Sum("actual_weight")))
        temp_list.sort(key=lambda x: (x.get("equip_no", "product_no")))
        for x in temp_list:
            x["output"] = str(x["output"] / 1000)
        ret = {"results": temp_list}
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class PlanInfoReal(APIView):
    """密炼状态信息"""

    def get(self, request):
        type = self.request.query_params.get('type', None)
        value = self.request.query_params.get('value', None)
        if not all([type, value]):
            raise ValidationError('参数不全，type和value都得传')
        try:
            production_factory_date = datetime.datetime.strptime(value, "%Y-%m-%d")
        except:
            raise ValidationError('时间格式不正确')
        if type == 'day':
            filter_dict = {'factory_date': value, 'delete_flag': False}
        elif type == 'week':
            this_week_start = production_factory_date - timedelta(days=production_factory_date.weekday())  # 当天坐在的周的周一
            this_week_end = production_factory_date + timedelta(days=6 - production_factory_date.weekday())  # 当天所在周的周日
            filter_dict = {'factory_date__lte': this_week_end.date(), 'factory_date__gte': this_week_start.date(),
                           'delete_flag': False}
        elif type == 'month':
            filter_dict = {'factory_date__month': production_factory_date.month,
                           'factory_date__year': production_factory_date.year,
                           'delete_flag': False}
        elif type == 'year':
            filter_dict = {'factory_date__year': production_factory_date.year,
                           'delete_flag': False}
        else:
            raise ValidationError('type只能传day，week，month，year')
        tfb_set = TrainsFeedbacks.objects.filter(**filter_dict).values(
            'equip_no', 'plan_classes_uid', 'product_no').annotate(
            actual_trains=Max('actual_trains'), plan_trains=Max('plan_trains'), start_time=Min('begin_time'),
            end_time=Max('end_time'))
        for tfb_obj in tfb_set:
            tfb_obj['actual_trains'] = str(tfb_obj['actual_trains'])
            tfb_obj['plan_trains'] = str(tfb_obj['plan_trains'])
            tfb_obj['start_time'] = tfb_obj['start_time'].strftime('%Y-%m-%d %H:%M:%S')
            tfb_obj['end_time'] = tfb_obj['end_time'].strftime('%Y-%m-%d %H:%M:%S')
        return Response({'resluts': tfb_set})


# /api/v1/production/equip-info-real/
@method_decorator([api_recorder], name="dispatch")
class EquipInfoReal(APIView):
    """设备状态信息"""

    def get(self, request):
        type = self.request.query_params.get('type', None)
        value = self.request.query_params.get('value', None)
        if not all([type, value]):
            raise ValidationError('参数不全，type和value都得传')
        try:
            production_factory_date = datetime.datetime.strptime(value, "%Y-%m-%d")
        except:
            raise ValidationError('时间格式不正确')
        now = datetime.datetime.now()
        if type == 'day':
            work_schedule_plan = WorkSchedulePlan.objects.filter(
                plan_schedule__day_time=production_factory_date,
                plan_schedule__work_schedule__work_procedure__global_name='密炼').first()
            if not work_schedule_plan:
                raise ValidationError('日期传参不正确')
            if now <= work_schedule_plan.end_time:
                end_time = now
            else:
                end_time = work_schedule_plan.end_time
            total_time = end_time - work_schedule_plan.start_time
            filter_dict = {"factory_date": value, 'delete_flag': False}
        elif type == 'week':
            this_week_start = production_factory_date - timedelta(days=production_factory_date.weekday())  # 当天坐在的周的周一
            this_week_end = production_factory_date + timedelta(days=6 - production_factory_date.weekday())  # 当天所在周的周日
            work_schedule_plan = WorkSchedulePlan.objects.filter(
                plan_schedule__day_time__gte=this_week_start.date(),
                plan_schedule__day_time__lte=this_week_end.date(),
                plan_schedule__work_schedule__work_procedure__global_name='密炼').values().aggregate(
                start_times=Min('start_time'),
                end_times=Max('end_time'))
            if not work_schedule_plan['end_times'] or not work_schedule_plan['start_times']:
                raise ValidationError('日期传参不正确')
            if now <= work_schedule_plan['end_times']:
                end_time = now
            else:
                end_time = work_schedule_plan['end_times']
            total_time = end_time - work_schedule_plan['start_times']
            filter_dict = {"factory_date__gte": this_week_start.date(), "factory_date__lte": this_week_end.date(),
                           'delete_flag': False}
        elif type == 'month':
            work_schedule_plan = WorkSchedulePlan.objects.filter(
                plan_schedule__day_time__month=production_factory_date.month,
                plan_schedule__day_time__year=production_factory_date.year,
                plan_schedule__work_schedule__work_procedure__global_name='密炼').values().aggregate(
                start_times=Min('start_time'),
                end_times=Max('end_time'))
            if not work_schedule_plan['end_times'] or not work_schedule_plan['start_times']:
                raise ValidationError('日期传参不正确')
            if now <= work_schedule_plan['end_times']:
                end_time = now
            else:
                end_time = work_schedule_plan['end_times']
            total_time = end_time - work_schedule_plan['start_times']
            filter_dict = {'factory_date__month': production_factory_date.month,
                           'factory_date__year': production_factory_date.year,
                           'delete_flag': False}
        elif type == 'year':
            work_schedule_plan = WorkSchedulePlan.objects.filter(
                plan_schedule__day_time__year=production_factory_date.year,
                plan_schedule__work_schedule__work_procedure__global_name='密炼').values().aggregate(
                start_times=Min('start_time'),
                end_times=Max('end_time'))
            if not work_schedule_plan['end_times'] or not work_schedule_plan['start_times']:
                raise ValidationError('日期传参不正确')
            if now <= work_schedule_plan['end_times']:
                end_time = now
            else:
                end_time = work_schedule_plan['end_times']
            total_time = end_time - work_schedule_plan['start_times']
            filter_dict = {'factory_date__year': production_factory_date.year,
                           'delete_flag': False}
        else:
            raise ValidationError('type只能传day，week，month，year')
        e_set = Equip.objects.filter(delete_flag=False).all()
        resluts = []
        for e_obj in e_set:
            tfb_set = TrainsFeedbacks.objects.filter(equip_no=e_obj.equip_no, **filter_dict
                                                     ).values(
                'equip_no', 'plan_classes_uid').annotate(actual_trains=Max('actual_trains'),
                                                         plan_trains=Max('plan_trains')).aggregate(
                plan_trains_sum=Sum('plan_trains'), actual_trains_sum=Sum('actual_trains'))
            plan_trains = tfb_set.pop("plan_trains_sum", None)
            actual_trains = tfb_set.pop("actual_trains_sum", None)

            tfb_set["plan_trains"] = str(plan_trains) if plan_trains else "0"
            tfb_set["actual_trains"] = str(actual_trains) if actual_trains else "0"
            tfb_set["equip_no"] = e_obj.equip_no
            try:
                if e_obj.equip_current_status_equip.status in ['故障', '维修开始', '维修结束', '空转']:
                    tfb_set['status'] = '故障'
                else:
                    tfb_set['status'] = e_obj.equip_current_status_equip.status
            except:
                tfb_set['status'] = '未知'
            epe_set = e_obj.equip_part_equip.filter(delete_flag=False).all()
            if not epe_set:
                # continue
                tfb_set["fault_time"] = total_time
            for epe_obj in epe_set:
                emo_set = epe_obj.equip_maintenance_order_part.filter(affirm_time__isnull=False, **filter_dict).all()
                if not emo_set:
                    continue
                for emo_obj in emo_set:
                    if not emo_obj.begin_time:
                        continue
                    wx_time = emo_obj.affirm_time - emo_obj.begin_time
                    total_time = total_time - wx_time
            tfb_set["fault_time"] = str(total_time)
            resluts.append(tfb_set)
        return Response({'resluts': resluts})


@method_decorator([api_recorder], name="dispatch")
class RuntimeRecordView(APIView):
    permission_classes = (IsAuthenticated, PermissionClass({'view': 'view_production_record'}))

    def get(self, request, *args, **kwargs):
        params = request.query_params
        classes = params.get("classes")
        factory_date = params.get("date", datetime.date.today())
        if classes in ["早班", "夜班"]:
            filters = {"classes": classes}
        else:
            filters = {}
        queryset = TrainsFeedbacks.objects.filter(factory_date=factory_date).filter(**filters)
        id_list = queryset.values('plan_classes_uid').annotate(max_id=Max('id')).values_list("max_id", flat=True)
        queryset = queryset.filter(id__in=id_list)
        data = queryset.values("equip_no", "product_no").annotate(plan_trains=Sum('plan_trains'),
                                                                  actual_trains=Sum('actual_trains'),
                                                                  begin_time=Min('begin_time'),
                                                                  end_time=Max('end_time')).values(
            "equip_no", "product_no", "plan_trains", "actual_trains", "begin_time", "end_time").order_by('equip_no')

        # 计算获取设备停机时间
        equip_set = EquipMaintenanceOrder.objects.filter(factory_date=factory_date, down_flag=True).values(
            "equip_part__equip__equip_no").annotate(stop_time=OSum((F('end_time') - F('begin_time')))).values(
            "equip_part__equip__equip_no", "stop_time")
        equip_data = {x.get("equip_part__equip__equip_no"): x.get("stop_time") for x in equip_set}
        equip_no_list = Equip.objects.filter(category__equip_type__global_name="密炼设备").values_list("equip_no",
                                                                                                   flat=True)
        equip_trains = {_: [0] for _ in equip_no_list}

        equip_list = ['Z01', 'Z02', 'Z03', 'Z04', 'Z05', 'Z06', 'Z07', 'Z08', 'Z09', 'Z10', 'Z11', 'Z12', 'Z13', 'Z14',
                      'Z15']
        if classes:
            if not isinstance(factory_date, datetime.date):
                factory_date = datetime.datetime.strptime(factory_date, '%Y-%m-%d').date()

            if factory_date == datetime.date.today():
                if not ProductionDailyRecords.objects.filter(factory_date=factory_date, classes=classes).first():

                    production_daily = ProductionDailyRecords.objects.create(factory_date=factory_date, classes=classes,
                                                                            equip_error_record = None,
                                                                            process_shutdown_record = None,
                                                                            production_shutdown_record = None,
                                                                            auxiliary_positions_record = None,
                                                                            shift_leader = None,
                    )

                    # 获取上一天的人员姓名
                    last_date = (factory_date + datetime.timedelta(days=-1)).strftime("%Y-%m-%d")
                    for equip in equip_list:
                        last = ProductionPersonnelRecords.objects.filter(equip_no=equip,
                                                                         production_daily__factory_date=last_date,
                                                                         production_daily__classes=classes).first()
                        if last:
                            ProductionPersonnelRecords.objects.create(equip_no=equip, production_daily=production_daily,
                                                                      feeding_post=last.feeding_post,
                                                                      extrusion_post=last.extrusion_post,
                                                                      collection_post=last.collection_post,
                                                                      )
                        else:
                            ProductionPersonnelRecords.objects.create(equip_no=equip, production_daily=production_daily)

        # 获取计划表里的计划车次
        if filters:
            plan_filter = {"work_schedule_plan__classes__global_name": classes}
        else:
            plan_filter = {}
        plan_set = ProductClassesPlan.objects.filter(work_schedule_plan__plan_schedule__day_time=factory_date,
                                                     work_schedule_plan__plan_schedule__work_schedule__work_procedure__global_name="密炼",
                                                     delete_flag=False, **plan_filter).values('equip__equip_no',
                                                                                              'product_batching__stage_product_batch_no').annotate(
            plan_trains=Sum('plan_trains')).values('equip__equip_no',
                                                   'product_batching__stage_product_batch_no', 'plan_trains')
        plan_data = {_.get('equip__equip_no') + _.get('product_batching__stage_product_batch_no'): _.get('plan_trains')
                     for _ in plan_set}
        results = []
        users = None
        for _ in data:
            equip_trains[_.get("equip_no")][0] += _.get("actual_trains")
            achieve_rate = round(_.get("actual_trains") / plan_data.get(_.get("equip_no") + _.get("product_no")), 4) \
                if plan_data.get(_.get("equip_no") + _.get("product_no")) else None
            equip_no = _.get("equip_no")
            if classes:
                users = ProductionPersonnelRecords.objects.filter(production_daily__factory_date=factory_date,
                                                           production_daily__classes=classes, equip_no=equip_no).first()
            else:
                users = None
            temp_dict = {"id": users.id if users else None,
                         "equip_no": equip_no,
                         "product_no": _.get("product_no"),
                         "plan_trains": plan_data.get(_.get("equip_no") + _.get("product_no")),
                         "actual_trains": _.get("actual_trains"),
                         "achieve_rate": achieve_rate,
                         "put_user": users.feeding_post if users else None,
                         "extrusion_user": users.extrusion_post if users else None,
                         "collection_user": users.collection_post if users else None,
                         "product_time": (_.get("end_time") - _.get("begin_time")).total_seconds(),
                         "trains_sum": equip_trains.get(_.get("equip_no")),
                         "start_rate": (24 * 60 * 60 - equip_data.get(_.get("equip_no"))) / 60 if equip_data.get(
                             _.get("equip_no")) else 1.0
                         }
            results.append(temp_dict)
        return Response({"results": results, "shift_leader": users.production_daily.shift_leader if users else None,
})


@method_decorator([api_recorder], name="dispatch")
class RuntimeRecordDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    # 点击报表预览
    def get(self, request, *args, **kwargs):
        factory_date = self.request.query_params.get('date', datetime.date.today())
        classes = self.request.query_params.get('classes', None)
        if classes:
            obj = ProductionDailyRecords.objects.get(factory_date=factory_date, classes=classes)

            results = {
                'id': obj.id,
                'shift_leader': obj.shift_leader,
                'equip_error_record': obj.equip_error_record,
                'process_shutdown_record': obj.process_shutdown_record,
                'production_shutdown_record': obj.production_shutdown_record,
                'auxiliary_positions_record': obj.auxiliary_positions_record
            }

            try:
                obj = WorkSchedulePlan.objects.filter(start_time__startswith=factory_date,
                                                      classes__global_name=classes).first()
                group = obj.group.global_name
            except: group = None

            return Response({'group': group, 'results': results})
        return Response({})

    def post(self, request, *args, **kwargs):
        data = self.request.data
        main = data.get('main')
        detail = data.get('detail', None)
        shift_leader = data.get('shift_leader', None)
        feeding_post = data.get('feeding_post', None)
        extrusion_post = data.get('extrusion_post', None)
        collection_post = data.get('collection_post', None)
        equip_error_record = data.get('equip_error_record', None)
        process_shutdown_record = data.get('process_shutdown_record', None)
        production_shutdown_record = data.get('production_shutdown_record', None)
        auxiliary_positions_record = data.get('auxiliary_positions_record', None)
        if detail:
        # 修改人员姓名
            obj = ProductionPersonnelRecords.objects.filter(id=detail).first()
            if feeding_post:
                obj.feeding_post = feeding_post
            if extrusion_post:
                obj.extrusion_post = extrusion_post
            if collection_post:
                obj.collection_post = collection_post
            obj.save()
            results = {'feeding_post': obj.feeding_post,
                        'extrusion_post': obj.extrusion_post,
                        'collection_post': obj.collection_post}
            return Response(results)
        # 修改相关记录
        if main:
            obj1 = ProductionDailyRecords.objects.filter(id=main).first()
            if equip_error_record:
                obj1.equip_error_record = equip_error_record
            if process_shutdown_record:
                obj1.process_shutdown_record = process_shutdown_record
            if production_shutdown_record:
                obj1.production_shutdown_record = production_shutdown_record
            if auxiliary_positions_record:
                obj1.auxiliary_positions_record = auxiliary_positions_record
            obj1.save()
            results = {
                'shift_leader': obj1.shift_leader,
                'equip_error_record': obj1.equip_error_record,
                'process_shutdown_record': obj1.process_shutdown_record,
                'production_shutdown_record': obj1.production_shutdown_record,
                'auxiliary_positions_record': obj1.auxiliary_positions_record
                 }
            return Response(results)

        if shift_leader:
            factory_date = data.get("date")
            classes = data.get("classes")
            obj1 = ProductionDailyRecords.objects.filter(factory_date=factory_date, classes=classes).first()
            if factory_date and classes:
                obj1.shift_leader=shift_leader
                obj1.save()
            return Response({'shift_leader': obj1.shift_leader})


@method_decorator([api_recorder], name="dispatch")
class TrainsFixView(APIView):
    """修改收皮车次，支持指定托修改和批次修改"""
    # {"factory_date": "2021-07-14",
    #  "classes": "早班",
    #  "equip_no": "Z01",
    #  "product_no": "C-RE-J260-02",
    #  "begin_trains": 1,
    #  "end_trains": 6,
    #  "fix_num": 1,
    #  "lot_no": "AAJ1Z062021072313078"
    #  }

    def post(self, request):
        s = TrainsFixSerializer(data=self.request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        lot_no = data.get('lot_no')
        if lot_no:  # 修改特定托的车次
            pallet = PalletFeedbacks.objects.filter(lot_no=data['lot_no']).first()
            if not pallet:
                raise ValidationError('未找到收皮数据！')
            data['product_no'] = pallet.product_no
            data['classes'] = pallet.classes
            data['equip_no'] = pallet.equip_no
            data['factory_date'] = pallet.factory_date
            if PalletFeedbacks.objects.exclude(
                    lot_no=data['lot_no']).filter(equip_no=data['equip_no'],
                                                  product_no=data['product_no'],
                                                  classes=data['classes'],
                                                  factory_date=data['factory_date']
                                                  ).filter(Q(begin_trains__lte=data['begin_trains'],
                                                           end_trains__gte=data['begin_trains']) |
                                                           Q(begin_trains__lte=data['end_trains'],
                                                           end_trains__gte=data['end_trains']) |
                                                           Q(begin_trains__gte=data['begin_trains'],
                                                             end_trains__lte=data['end_trains'])):
                raise ValidationError('车次重复，请确认后重试！')
            pallet.begin_trains = data['begin_trains']
            pallet.end_trains = data['end_trains']
            pallet.save()
            MaterialTestOrder.objects.filter(lot_no=data['lot_no']).delete()
            lot_nos = [data['lot_no']]
        else:
            fix_num = data['fix_num']
            if data['begin_trains'] + fix_num <= 0:
                raise ValidationError('修改后车次不可为0！')
            if not PalletFeedbacks.objects.filter(equip_no=data['equip_no'],
                                                  product_no=data['product_no'],
                                                  classes=data['classes'],
                                                  factory_date=data['factory_date'],
                                                  begin_trains=data['begin_trains']):
                raise ValidationError('开始车次必须为一托开始车次！')
            if not PalletFeedbacks.objects.filter(equip_no=data['equip_no'],
                                                  product_no=data['product_no'],
                                                  classes=data['classes'],
                                                  factory_date=data['factory_date'],
                                                  end_trains=data['end_trains']):
                raise ValidationError('结束车次必须为一托结束车次！')
            pallet_data = PalletFeedbacks.objects.filter(equip_no=data['equip_no'],
                                                         product_no=data['product_no'],
                                                         classes=data['classes'],
                                                         factory_date=data['factory_date'],
                                                         ).filter(Q(begin_trains__lte=data['begin_trains'],
                                                                  end_trains__gte=data['begin_trains']) |
                                                                  Q(begin_trains__lte=data['end_trains'],
                                                                  end_trains__gte=data['end_trains']) |
                                                                  Q(begin_trains__gte=data['begin_trains'],
                                                                  end_trains__lte=data['end_trains'])
                                                                  ).order_by('begin_trains')
            if not pallet_data:
                raise ValidationError('未找到改批次收皮数据！')
            lot_nos = set(pallet_data.values_list('lot_no', flat=True))
            if PalletFeedbacks.objects.filter(equip_no=data['equip_no'],
                                              product_no=data['product_no'],
                                              classes=data['classes'],
                                              factory_date=data['factory_date']
                                              ).exclude(id__in=pallet_data.values_list('id', flat=True)).filter(
                    Q(begin_trains__lte=data['begin_trains']+fix_num, end_trains__gte=data['begin_trains']+fix_num) |
                    Q(begin_trains__lte=data['end_trains']+fix_num, end_trains__gte=data['end_trains']+fix_num) |
                    Q(begin_trains__gte=data['begin_trains']+fix_num, end_trains__lte=data['end_trains']+fix_num)
            ).exists():
                raise ValidationError('修改后车次信息重复！')
            for pallet in pallet_data:
                pallet.begin_trains += fix_num
                pallet.end_trains += fix_num
                pallet.save()

            MaterialTestOrder.objects.filter(lot_no__in=lot_nos).delete()
        MaterialDealResult.objects.filter(lot_no__in=lot_nos).delete()
        return Response('修改成功')


@method_decorator([api_recorder], name="dispatch")
class PalletTrainsBatchFixView(ListAPIView, UpdateAPIView):
    """
        收皮车次批量修改
    """
    queryset = PalletFeedbacks.objects.filter(delete_flag=False).order_by('begin_trains', 'begin_time')
    permission_classes = (IsAuthenticated,)
    serializer_class = PalletFeedbacksBatchModifySerializer
    filter_backends = [DjangoFilterBackend, ]
    filter_class = PalletFeedbacksFilter
    pagination_class = None

    @atomic()
    def put(self, request, *args, **kwargs):
        data = self.request.data
        if not isinstance(data, list):
            raise ValidationError('参数错误！')
        for item in data:
            instance = PalletFeedbacks.objects.get(id=item['id'])
            s = PalletFeedbacksBatchModifySerializer(instance=instance, data=item, context={'request': request})
            s.is_valid(raise_exception=True)
            s.save()
            MaterialTestOrder.objects.filter(lot_no=instance.lot_no).delete()
            MaterialDealResult.objects.filter(lot_no=instance.lot_no).delete()
        return Response('修改成功')


@method_decorator([api_recorder], name="dispatch")
class ProductPlanRealView(ListAPIView):
    queryset = ProductClassesPlan.objects.filter(delete_flag=False).order_by('id')
    serializer_class = ProductPlanRealViewSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend, ]
    filter_class = ProductClassesPlanFilter
    pagination_class = None

    def list(self, request, *args, **kwargs):
        ret = {}
        queryset = self.filter_queryset(self.get_queryset())
        for classes in ['早班', '中班', '夜班']:
            page = queryset.filter(work_schedule_plan__classes__global_name=classes)
            data = self.get_serializer(page, many=True).data
            data = list(filter(lambda x: x['begin_time'] is not None, data))
            data.sort(key=lambda x: x['begin_time'])
            ret[classes] = data
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class ProductBatchInfo(APIView):

    def get(self, request):
        lot_no = self.request.query_params.get('lot_no')
        if not lot_no:
            return Response({'success': False, 'data': {}, 'message': '请携带正确的条码号查询！'})
        pallet_feedback = PalletFeedbacks.objects.filter(lot_no=lot_no).first()
        if not pallet_feedback:
            return Response({'success': False, 'data': {}, 'message': '未找到该条码信息！'})

        pallet_data = PalletFeedbacks.objects.filter(lot_no=lot_no).first()
        plan = ProductClassesPlan.objects.filter(plan_classes_uid=pallet_data.plan_classes_uid).first()
        if not plan:
            group = ''
        else:
            group = plan.work_schedule_plan.group.global_name

        ins = MaterialDealResult.objects.filter(lot_no=lot_no).first()
        if not ins:
            data = {
                'product_no': pallet_data.product_no,
                'equip_no': pallet_data.equip_no,
                'classes': pallet_data.classes,
                'group': group,
                'factory_date': pallet_data.factory_date,
                'weight': pallet_feedback.actual_weight,
                'trains': '/'.join([str(i) for i in range(pallet_data.begin_trains, pallet_data.end_trains + 1)]),
                'test_result': '未检测',
            }
            return Response({'success': True, 'data': data, 'message': '查询成功！'})

        data = {
            'product_no': pallet_data.product_no,
            'equip_no': pallet_data.equip_no,
            'classes': pallet_data.classes,
            'group': group,
            'factory_date': pallet_data.factory_date,
            'weight': pallet_feedback.actual_weight,
            'trains': '/'.join([str(i) for i in range(pallet_data.begin_trains, pallet_data.end_trains + 1)]),
            'test_result': ins.test_result,
        }

        ret = []
        test_orders = MaterialTestOrder.objects.filter(lot_no=lot_no,
                                                       product_no=ins.product_no
                                                       ).order_by('actual_trains')
        for test_order in test_orders:
            max_result_ids = list(test_order.order_results.values(
                'test_indicator_name', 'data_point_name'
            ).annotate(max_id=Max('id')).values_list('max_id', flat=True))
            test_results = MaterialTestResult.objects.filter(id__in=max_result_ids,
                                                             is_judged=True).order_by('test_indicator_name',
                                                                                      'data_point_name')
            for test_result in test_results:
                if test_result.level == 1:
                    result = '合格'
                elif test_result.is_passed:
                    result = 'pass'
                else:
                    result = '不合格'
                indicator = MaterialDataPointIndicator.objects.filter(
                    data_point__name=test_result.data_point_name,
                    material_test_method__material__material_name=ins.product_no,
                    level=1).first()
                if indicator:
                    upper_limit = indicator.upper_limit
                    lower_limit = indicator.lower_limit
                else:
                    upper_limit = lower_limit = None
                ret.append(
                    {
                        'data_point_name': test_result.data_point_name,
                        'result': result,
                        'value': test_result.value,
                        'test_indicator_name': test_result.test_indicator_name,
                        'train': test_order.actual_trains,
                        'upper_limit': upper_limit,
                        'lower_limit': lower_limit
                    }
                )
        data['test_info'] = ret
        return Response({'success': True, 'data': data, 'message': '查询成功！'})


@method_decorator([api_recorder], name="dispatch")
class RubberCannotPutinReasonView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        s_time = self.request.query_params.get('s_time')
        e_time = self.request.query_params.get('e_time')
        factory_date = self.request.query_params.get('factory_date')
        equip = self.request.query_params.get('equip')
        equip_list = ['Z%.2d' % i for i in range(1, 16)]
        queryset = RubberCannotPutinReason.objects.all()
        if equip:
            result = RubberCannotPutinReasonSerializer(queryset.filter(factory_date__date=factory_date, machine_no=equip), many=True).data
        elif s_time:
            start = datetime.datetime.strptime(s_time, "%Y-%m-%d")
            end = datetime.datetime.strptime(e_time, "%Y-%m-%d")
            """获取两个日期之间的所有日期"""
            delta = end - start
            time_list = [(start + timedelta(days=i)).strftime("%Y年%m月%d日") for i in range(delta.days + 1)]
            dic = {}
            temp = queryset.filter(factory_date__date__range=(s_time, e_time)).values('reason_name', 'factory_date__date').annotate(
                num=Count('id'))
            for item in temp:
                t = item['factory_date__date'].strftime("%Y年%m月%d日")
                if dic.get(item['reason_name']):
                    if dic[item['reason_name']][t]:
                        dic[item['reason_name']][t] += item['num']
                    else:
                        dic[item['reason_name']][t] = item['num']
                    dic[item['reason_name']]['count'] += item['num']
                else:
                    dic[item['reason_name']] = {'不入库原因': item['reason_name'], 'count': 0}
                    for time in time_list:
                        dic[item['reason_name']].update({time: None})
                    dic[item['reason_name']][t] = item['num']
                    dic[item['reason_name']]['count'] += item['num']
            result = dic.values()
            # count = {}  # 底部数量统计
            # for i in result:
            #     for key, value in i.items():
            #         if key[1:2].isdecimal() and value:
            #             if count.get(key):
            #                 count[key] += value
            #             else:
            #                 count[key] = value
        elif factory_date:
            dic = {}
            temp = queryset.filter(factory_date__date=factory_date).values('reason_name', 'machine_no').annotate(
                num=Count('id'))
            for item in temp:
                if dic.get(item['reason_name']):
                    if dic[item['reason_name']][item['machine_no']]:
                        dic[item['reason_name']][item['machine_no']] += item['num']
                    else:
                        dic[item['reason_name']][item['machine_no']] = item['num']
                    dic[item['reason_name']]['count'] += item['num']
                else:
                    dic[item['reason_name']] = {'不入库原因': item['reason_name'], 'count': 0}
                    for equip in equip_list:
                        dic[item['reason_name']].update({equip: None})
                    dic[item['reason_name']][item['machine_no']] = item['num']
                    dic[item['reason_name']]['count'] += item['num']
            result = dic.values()
        return Response({'results': result})


@method_decorator([api_recorder], name="dispatch")
class MachineTargetValue(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        # 取最近90天，每天的最后一条数据
        time = self.request.query_params.get('time')
        this_begin_time = datetime.date.today() - datetime.timedelta(days=90)
        queryset = MachineTargetYieldSettings.objects.all()
        if not queryset.exists():
            equip_list = ['Z01', 'Z02', 'Z03', 'Z04', 'Z05',  'Z06',  'Z07',  'Z08',  'Z09',  'Z10',  'Z11', 'Z12', 'Z13', 'Z14', 'Z15', '190E']
            return Response({'date': [datetime.date.today()], 'results': [{'equip_no': equip, 'value': None} for equip in equip_list]})
        date = queryset.filter(input_datetime__gte=this_begin_time).values('input_datetime__date').order_by('id')
        if time:
            res = queryset.filter(input_datetime__date=time).order_by('-id').values()[0]
        else:
            res = queryset.order_by('-id').values()[0]
        res['190E'] = res.pop('E190')
        del res['id']
        del res['input_user_id']
        del res['input_datetime']
        results = [{'equip_no': key, 'value': value} for key, value in res.items()]

        return Response({'date': [i['input_datetime__date'] for i in date], 'results': results})

    def post(self, request):
        dic = {}
        data = self.request.data
        for i in data:
            if i['equip_no'] == '190E':
                dic['E190'] = i['value']
            else:
                dic[i['equip_no']] = i['value']
        user = self.request.user
        dic.update(input_user=user)
        MachineTargetYieldSettings.objects.update_or_create(defaults=dic, input_datetime__date=datetime.date.today())
        return Response('ok')


@method_decorator([api_recorder], name="dispatch")
class MonthlyOutputStatisticsReport(APIView):
    queryset = TrainsFeedbacks.objects.all()
    permission_classes = (IsAuthenticated,)

    def my_order(self, result, order):
        lst = []
        for dic in result:
            if dic['name'] in order:
                lst.append(dic)
        res = sorted(lst, key=lambda x: order.index(x['name']))
        return res

    def get(self, request, *args, **kwargs):
        st = self.request.query_params.get('st')
        et = self.request.query_params.get('et')
        state = self.request.query_params.get('state')  # 段数
        equip = self.request.query_params.get('equip')
        space = self.request.query_params.get('space', '')  # 规格    C-FM-C101-02
        if state:
            kwargs = {'equip_no': equip, 'product_no__icontains': f"-{state}-{space}"} if equip else \
                {'product_no__icontains': f"-{state}-{space}"}
            spare_weight = self.queryset.filter(**kwargs).aggregate(spare_weight=Sum('actual_weight'))['spare_weight']
            queryset = self.queryset.filter(**kwargs).values('equip_no', 'product_no', 'factory_date')\
                .annotate(value=Count('id'), weight=Sum('actual_weight'))

            dic = {}
            for item in queryset:
                space_equip = f"{item['product_no'].split('-')[2]}-{item['equip_no']}-{datetime.datetime.strftime(item['factory_date'], '%Y%m%d')}"
                if dic.get(space_equip):
                    dic[space_equip]['value'] += item['value']
                    dic[space_equip]['weight'] += round(item['weight'] / 1000, 2)
                    dic[space_equip]['ratio'] += round(item['weight'] / spare_weight, 2)
                else:
                    dic[space_equip] = {'space': item['product_no'].split('-')[2],
                                        'equip_no': item['equip_no'],
                                        'time': datetime.datetime.strftime(item['factory_date'], '%m/%d'),
                                        'value': item['value'],
                                        'weight': round(item['weight'] / 1000, 2),
                                        'ratio': f"{round(item['weight'] / spare_weight, 2)}%"
                                        }
            result = sorted(dic.values(), key=lambda x: (x['space'], x['equip_no'], x['time']))
            return Response({'result': result})
        else:
            # 取每个机台的历史最大值
            # equip_max_value = self.queryset.values('factory_date__year', 'factory_date__month',
            #                                           'equip_no').annotate(value=Count('id')).order_by('equip_no', 'value')
            # dic = {}
            # [dic.update({item['equip_no']: item['value']}) for item in equip_max_value]
            dic = {}
            equip_max_value = TrainsFeedbacks.objects.values('equip_no', 'factory_date').annotate(
            qty=Count('id')).order_by('-qty')
            for item in equip_max_value:
                if not dic.get(f"{item['equip_no']}"):
                    dic[f"{item['equip_no']}"] = item['qty']
            # 取每个机台设定的目标值
            settings_value = MachineTargetYieldSettings.objects.order_by('id').last()
            # 获取起止时间内总重量和总数量
            result = self.queryset.filter(factory_date__gte=st, factory_date__lte=et).values('equip_no').annotate(value=Count('id'),
                                                                 weight=Sum('actual_weight'))

            for item in result:
                item['weight'] = round(item['weight'] / 1000, 2)
                item['max_value'] = dic[item['equip_no']] if dic.get(item['equip_no']) else None
                if settings_value:
                    item['settings_value'] = settings_value.__dict__.get('E190') if item['equip_no'] == '190E' else\
                        settings_value.__dict__.get(item['equip_no'])
                else:
                    item['settings_value'] = None
            # 获取不同段次的总重量
            state_value = self.queryset.filter(factory_date__gte=st, factory_date__lte=et).values('product_no').annotate(weight=Sum('actual_weight'))
            jl = {'jl': 0}
            wl = {'wl': 0}

            for item in state_value:
                if item['product_no'].split('-')[1] in ['RE', 'FM', 'RFM']:
                    if jl.get(item['product_no'].split('-')[1]):
                        jl[item['product_no'].split('-')[1]] += round(item['weight'] / 1000, 2)
                    else:
                        jl[item['product_no'].split('-')[1]] = round(item['weight'] / 1000, 2)
                    jl['jl'] += round(item['weight'] / 1000, 2)
                else:
                    if wl.get(item['product_no'].split('-')[1]):
                        wl[item['product_no'].split('-')[1]] += round(item['weight'] / 1000, 2)
                    else:
                        wl[item['product_no'].split('-')[1]] = round(item['weight'] / 1000, 2)
                    wl['wl'] += round(item['weight'] / 1000, 2)

            jl = [{'name': key, 'value': value} for key, value in jl.items()]
            wl = [{'name': key, 'value': value} for key, value in wl.items()]
            # 按照机台和段次排序
            all_state = GlobalCode.objects.filter(global_type__type_name='胶料段次').values_list('global_name')
            state_list = [i[0] for i in all_state]
            jl_order = ['RE', 'FM', 'RFM', 'jl']
            # 去除加硫的
            ret = [i for i in state_list if i not in jl_order]
            wl_order = ['1MB', '2MB', '3MB', 'HMB', 'CMB', 'RMB']
            # 新增的添加到最后
            new_state = [i for i in ret if i not in wl_order]
            wl_order = wl_order + new_state + ['wl']
            equip_order = ['Z01', 'Z02', 'Z03', 'Z04', 'Z05', 'Z06', 'Z07', 'Z08', 'Z09', 'Z10', 'Z11', 'Z12', 'Z13', 'Z14', 'Z15', '190E']
            result = sorted(result, key=lambda x: equip_order.index(x['equip_no']))
            wl = self.my_order(wl, wl_order)
            jl = self.my_order(jl, jl_order)

            return Response({'result': result, 'wl': wl, 'jl': jl})


# @method_decorator([api_recorder], name="dispatch")
# class MonthlyOutputStatisticsAndPerformance(APIView):
#     permission_classes = (IsAuthenticated,)
#
#     def my_order(self, result, order):
#         lst = []
#         for dic in result:
#             if dic['state'] in order:
#                 lst.append(dic)
#         res = sorted(lst, key=lambda x: order.index(x['state']))
#         return res
#
#     def get_max_value(self, equip, last_date, group_list):
#         from django.db import connection
#         cursor = connection.cursor()
#         if equip:
#             filter_kwargs = f""" WHERE equip_no = '{equip}' AND to_char( FACTORY_DATE, 'YYYY-MM-DD' ) <= '{last_date}' GROUP BY CLASSES, FACTORY_DATE ) """
#         else:
#             filter_kwargs = f""" WHERE to_char( FACTORY_DATE, 'YYYY-MM-DD' ) <= '{last_date}' GROUP BY CLASSES, FACTORY_DATE ) """
#         cursor.execute(
#             # f"""
#             # SELECT
#             #     max( count ) count,
#             #     classes,
#             #     RIGHT ( days, 2 ) days
#             # FROM
#             #     (
#             #     SELECT count( id ) count, classes, DATE_FORMAT( factory_date, '%Y%m%d' ) days FROM trains_feedbacks
#             #     where equip_no='{equip}' and factory_date <= '{last_date}' GROUP BY classes, factory_date
#             #      ) AS a
#             # GROUP BY
#             #     RIGHT ( a.days, 2 ),
#             #     classes
#             # """
#             f"""
#             SELECT MAX( COUNT ) COUNT, classes, days
#             FROM
#                 (SELECT
#                     MAX( COUNT ) COUNT, CLASSES, TO_CHAR( FACTORY_DATE, 'dd' ) days
#                 FROM
#                     ( SELECT COUNT( id ) COUNT, CLASSES, FACTORY_DATE FROM TRAINS_FEEDBACKS
#                    {filter_kwargs}
#                 GROUP BY CLASSES, TO_CHAR( FACTORY_DATE, 'dd' )
#                 )
#             GROUP BY classes, days ORDER BY days
#             """
#         )
#
#         row = cursor.fetchall()
#         dic = {'state': '机台最高值', 'count': 0}
#         for i in row:
#             try:
#                 s = group_list[int(i[2]) - 1]
#             except:
#                 raise ValidationError('请先去添加排班计划')
#             classes = s[0] if i[1] == '早班' else s[1]
#             key = f'{int(i[2])}{classes}'
#
#             if dic.get(key):
#                 dic[key] += i[0]
#             else:
#                 dic[key] = i[0]
#             dic['count'] += i[0]
#         return dic
#
#     def get_settings_value(self, equip, settings_queryset, group_list):
#         dic = {'state': '机台目标值', 'count': 0}
#         group_index = [index + 1 for index in range(len(group_list))]
#         settings_index = [i['input_datetime__day'] for i in settings_queryset]
#         no_settings = list(set(group_index).difference(set(settings_index)))
#
#         for i in settings_queryset:
#             s = group_list[int(i['input_datetime__day']) - 1]
#             for classes in s:
#                 key = f"{int(i['input_datetime__day'])}{classes}"
#                 if dic.get(key):
#                     dic[key] += i[equip]
#                 else:
#                     dic[key] = i[equip]
#                 dic['count'] += i[equip]
#         # 当天没有设定值则取本月的最后一条
#         for i in no_settings:
#             value = settings_queryset[-1][equip]
#             group = group_list[i - 1]
#             for classes in group:
#                 key = f"{i}{classes}"
#                 dic[key] = value
#                 dic['count'] += value
#         return dic
#
#     def get(self, request):
#         params = self.request.query_params
#         unit = params.get('unit', '车')
#         date = params.get('date')
#         equip = params.get('equip')
#         year = int(date.split('-')[0]) if date else datetime.date.today().year
#         month = int(date.split('-')[1]) if date else datetime.date.today().month
#         equip_kwargs = {'equip_no': equip} if equip else {}
#         this_month_start = datetime.datetime(year, month, 1)
#         if month == 12:
#             this_month_end = datetime.datetime(year + 1, 1, 1) - timedelta(days=1)
#         else:
#             this_month_end = datetime.datetime(year, month + 1, 1) - timedelta(days=1)
#         last_date = datetime.datetime.strftime(datetime.datetime(year, month, 1) - datetime.timedelta(days=1), '%Y-%m-%d')
#         kwargs = {'count': Count('id')} if unit == '车' else {'count': Sum('actual_weight')}
#         # 获取班组
#         group = WorkSchedulePlan.objects.filter(start_time__date__gte=this_month_start,
#                                                 start_time__date__lte=this_month_end).values('group__global_name', 'start_time__date').order_by('start_time')
#         group_list = []
#         for key, group in groupby(list(group), key=lambda x: x['start_time__date']):
#             group_list.append([item['group__global_name'] for item in group])
#
#         queryset = TrainsFeedbacks.objects.filter(factory_date__gte=this_month_start, factory_date__lte=this_month_end, **equip_kwargs).values(
#             'classes', 'factory_date', 'product_no').annotate(**kwargs)
#         jl = {'jl': {'state': '加硫小计', 'count': 0}}
#         wl = {'wl': {'state': '无硫小计', 'count': 0}}
#         hj = {'hj': {'state': '无硫/加硫合计', 'count': 0}}
#         # 获取机台目标值
#         if equip == '190E':
#             equip = 'E190'
#         if equip:
#             settings_queryset = MachineTargetYieldSettings.objects.filter(input_datetime__year=year,
#                                                       input_datetime__month=month).values(f'{equip}','input_datetime__day').order_by('id')
#             if settings_queryset.exists():
#                 settings_value = self.get_settings_value(equip, list(settings_queryset), group_list)
#             else:
#                 settings_value = {'state': '机台目标值', 'count': 0}
#             # 获取历史每日生产最大值
#             max_value = self.get_max_value(equip, last_date, group_list)
#         else:
#             settings_value = {'state': '机台目标值', 'count': 0}
#             max_value = {'state': '机台最高值', 'count': 0}
#
#         for item in queryset:
#             state = item['product_no'].split('-')[1]
#             day = item['factory_date'].day
#             count = item['count'] if unit == '车' else item['count'] / 1000
#             classes = group_list[day - 1][0] if item['classes'] == '早班' else group_list[day - 1][1]
#             if hj['hj'].get(f'{day}{classes}'):
#                 hj['hj'][f'{day}{classes}'] += count
#             else:
#                 hj['hj'][f'{day}{classes}'] = count
#             hj['hj']['count'] += count
#             if state in ['RE', 'FM', 'RFM']:
#                 if jl.get(state):
#                     if jl[state].get(f'{day}{classes}'):
#                         jl[state][f'{day}{classes}'] += count
#                     else:
#                         jl[state][f'{day}{classes}'] = count
#                     jl[state]['count'] += count
#                 else:
#                     jl[state] = {'state': state, f'{day}{classes}': count, 'count': count}
#                 if jl['jl'].get(f'{day}{classes}'):
#                     jl['jl'][f'{day}{classes}'] += count
#                 else:
#                     jl['jl'][f'{day}{classes}'] = count
#                 jl['jl']['count'] += count
#             else:
#                 if wl.get(state):
#                     if wl[state].get(f'{day}{classes}'):
#                         wl[state][f'{day}{classes}'] += count
#                     else:
#                         wl[state][f'{day}{classes}'] = count
#                     wl[state]['count'] += count
#                 else:
#                     wl[state] = {'state': state, f'{day}{classes}': count, 'count': count}
#                 if wl['wl'].get(f'{day}{classes}'):
#                     wl['wl'][f'{day}{classes}'] += count
#                 else:
#                     wl['wl'][f'{day}{classes}'] = count
#                 wl['wl']['count'] += count
#
#         jl_order = ['RE', 'FM', 'RFM', '加硫小计']
#         wl_order = ['1MB', '2MB', '3MB', 'HMB', 'CMB', 'RMB', '无硫小计']
#         wl = self.my_order(list(wl.values()), wl_order)
#         jl = self.my_order(list(jl.values()), jl_order)
#         hj = list(hj.values())
#         hj.append(settings_value)
#         hj.append(max_value)
#
#         return Response({'wl': wl, 'jl': jl, 'hj': hj, 'group_list': group_list})


@method_decorator([api_recorder], name="dispatch")
class DailyProductionCompletionReport(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        params = self.request.query_params
        date = params.get('date')
        year = int(date.split('-')[0]) if date else datetime.date.today().year
        month = int(date.split('-')[1]) if date else datetime.date.today().month
        this_month_start = datetime.datetime(year, month, 1)
        if month == 12:
            this_month_end = datetime.datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            this_month_end = datetime.datetime(year, month + 1, 1) - timedelta(days=1)
        results = {
            'name_1': {'name': '计划目标', 'weight': 0},
            'name_2': {'name': '终炼实际完成(吨)', 'weight': 0},
            'name_3': {'name': '外发无硫料(吨)', 'weight': 0},
            'name_4': {'name': '实际完成数-1(吨)', 'weight': 0},
            'name_5': {'name': '实际完成数-2(吨)', 'weight': 0},
            'name_6': {'name': '实际生产工作日数', 'weight': 0},
            'name_7': {'name': '日均完成率', 'weight': 0},
        }
        # 终炼实际完成（吨）  FM , RFM , RE
        queryset = TrainsFeedbacks.objects.filter(Q(factory_date__year=year, factory_date__month=month) &
                                                Q(Q(product_no__icontains='-FM-') |
                                                  Q(product_no__icontains='-RFM-') |
                                                  Q(product_no__icontains='-RE-')))
        fin_queryset = queryset.values('factory_date__day').annotate(weight=Sum('actual_weight'))

        for item in fin_queryset:
            results['name_2']['weight'] += round(item['weight'] / 1000, 2)
            results['name_4']['weight'] += round(item['weight'] / 1000, 2)
            results['name_5']['weight'] += round(item['weight'] / 1000, 2)
            results['name_2'][f"{item['factory_date__day']}日"] = round(item['weight'] / 1000, 2)
            results['name_4'][f"{item['factory_date__day']}日"] = round(item['weight'] / 1000, 2)
            results['name_5'][f"{item['factory_date__day']}日"] = round(item['weight'] / 1000, 2)

        # 外发无硫料（吨）
        out_queryset = FinalGumOutInventoryLog.objects.using('lb').filter(inout_num_type__icontains='出库',
                                                           material_no__icontains="M",
                                                           start_time__gte=this_month_start,
                                                           start_time__lte=this_month_end).values('start_time__day').annotate(weight=Sum('weight'))

        for item in out_queryset:
            results['name_3']['weight'] += round(item['weight'] / 1000, 2)
            results['name_4']['weight'] += round((item['weight'] / 1000) * decimal.Decimal(0.7), 2)
            results['name_5']['weight'] += round(item['weight'] / 1000, 2)
            results['name_3'][f"{item['start_time__day']}日"] = round(item['weight'] / 1000, 2)
            if results['name_2'].get(f"{item['start_time__day']}日"):
                results['name_4'][f"{item['start_time__day']}日"] += round((item['weight'] / 1000) * decimal.Decimal(0.7), 2)
                results['name_5'][f"{item['start_time__day']}日"] += round(item['weight'] / 1000, 2)
            else:
                results['name_4'][f"{item['start_time__day']}日"] = round((item['weight'] / 1000) * decimal.Decimal(0.7), 2)
                results['name_5'][f"{item['start_time__day']}日"] = round(item['weight'] / 1000, 2)

        # 开机机台
        equip_queryset = list(queryset.values('equip_no', 'factory_date__day').distinct())
        #  [{'equip_no': 'Z03', 'factory_date__day': 7}, {'equip_no': 'Z03', 'factory_date__day': 8}, {'equip_no': 'Z02', 'factory_date__day': 8}]

        for item in equip_queryset:
            if results['name_6'].get(f"{item['factory_date__day']}日"):
                results['name_6'][f"{item['factory_date__day']}日"] += round(24 / 24, 2)  # 24h
            else:
                results['name_6'][f"{item['factory_date__day']}日"] = round(24 / 24, 2)

        return Response({'results': results.values()})


@method_decorator([api_recorder], name="dispatch")
class SummaryOfMillOutput(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        factory_date = self.request.query_params.get('factory_date')
        # 统计机台的机型

        queryset = Equip.objects.filter(category__equip_type__global_name='密炼设备').values('equip_no', 'category__category_name')
        dic = {item['equip_no']: item['category__category_name'] for item in queryset}
        state_list = GlobalCode.objects.filter(global_type__type_name='胶料段次').values('global_name')
        state_list = [item['global_name'] for item in state_list]
        equip_list = Equip.objects.filter(category__equip_type__global_name='密炼设备').order_by('equip_no').values('equip_no')

        results = {}
        count = {'equip_no': None, 'type': '合计', 'count': 0}
        for equip in equip_list:
            equip = equip['equip_no']
            results[f"{equip}_pt"] = {'equip_no': f"{equip}({dic.get(equip)})", 'type': '普通胶车数', 'count': 0}
            results[f"{equip}_dj"] = {'equip_no': f"{equip}({dic.get(equip)})", 'type': '丁基胶车数', 'count': 0}
            results[f"{equip}_xj"] = {'equip_no': f"{equip}({dic.get(equip)})", 'type': '小计', 'count': 0}

            for state in state_list:
                results[f"{equip}_pt"][f"{state}-早"] = 0
                results[f"{equip}_pt"][f"{state}-晚"] = 0
                results[f"{equip}_dj"][f"{state}-早"] = 0
                results[f"{equip}_dj"][f"{state}-晚"] = 0
                results[f"{equip}_xj"][f"{state}-早"] = 0
                results[f"{equip}_xj"][f"{state}-晚"] = 0
                count[f"{state}-早"] = 0
                count[f"{state}-晚"] = 0

        data = TrainsFeedbacks.objects.filter(factory_date=factory_date).values('equip_no',
                                                                                'product_no', 'classes').annotate(
            actual_trains=Count('actual_trains')).values('equip_no', 'product_no', 'classes', 'actual_trains')

        dj = ProductInfoDingJi.objects.filter(delete_flag=False, is_use=True).values('product_no')
        for item in data:
            equip = item['equip_no']
            state = item['product_no'].split('-')[1]
            classes = '早' if item['classes'] == '早班' else '晚'
            actual_trains = item['actual_trains']
            if state in state_list:
                # 判断是否是丁基胶
                if item['product_no'] in [item['product_no'] for item in dj]:
                    results[f"{equip}_dj"][f"{state}-{classes}"] += actual_trains
                    results[f"{equip}_dj"]['count'] += actual_trains
                else:
                    results[f"{equip}_pt"][f"{state}-{classes}"] += actual_trains
                    results[f"{equip}_pt"]['count'] += actual_trains
                results[f"{equip}_xj"][f"{state}-{classes}"] += actual_trains
                results[f"{equip}_xj"]['count'] += actual_trains
                count[f"{state}-{classes}"] = actual_trains
                count['count'] += actual_trains
        return Response({'results': results.values(), 'count': count, 'state_list': state_list})


@method_decorator([api_recorder], name="dispatch")
class SummaryOfWeighingOutput(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        factory_date = self.request.query_params.get('factory_date')
        year, month = factory_date.split('-')
        this_month_start = datetime.datetime(year, month, 1)
        if month == 12:
            this_month_end = datetime.datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            this_month_end = datetime.datetime(year, month + 1, 1) - timedelta(days=1)

        equip_list = Equip.objects.filter(category__equip_type__global_name='称量设备').values_list('equip_no', flat=True)

        result = []
        group_dic = {}
        users = {}  # {'1-早班'： '张三'}
        group = WorkSchedulePlan.objects.filter(start_time__year=year,
                                                start_time__month=month).values_list('group__global_name', 'classes__global_name', 'start_time__day')
        for item in group:
            group_dic[f'{item[2]}-{item[0]}'] = item[1]
        # 查询称量分类下当前月上班的所有员工
        user_list = EmployeeAttendanceRecords.objects.filter(date__year=year, date__month=month, equip__in=equip_list).values('name', 'date__day', 'group', 'section')
        # 岗位系数
        section_dic = {}
        section_info = PerformanceJobLadder.objects.filter(delete_flag=False).values('name', 'coefficient', 'post_standard', 'post_coefficient')
        for item in section_info:
            section_dic[item['name']] = [item['coefficient'], item['post_standard'], item['post_coefficient']]

        for item in user_list:
            classes = group.get(f"{item['date__day']}-{item['group']}")
            if users.get(f"{item['date__day']}-{classes}"):
                users[f"{item['date__day']}-{classes}"] = [item['name'],]
            else:
                users[f"{item['date__day']}-{classes}"] += item['name']

        user_result = {}
        price_obj = SetThePrice.objects.first()
        for equip_no in equip_list:
            # 细料/硫磺单价'
            price = price_obj.xl if equip_no in ['F01', 'F02', 'F03'] else price_obj.lh
            dic = {'equip_no': equip_no}
            data = Plan.objects.using(equip_no).filter(actno__gt=1, merge_flag=1,
                                                       date_time__get=this_month_start,
                                                       date_time__lte=this_month_end).values('date_time', 'grouptime').annotate(
                'date_time', 'grouptime', count=Avg('actno'))
            for item in data:
                date = item['date_time']
                day = date.split('-')[2]    # 2  早班
                classes = item['grouptime']  # 早班/ 中班 / 夜班
                dic[f'{date}{group}'] = item['count']
                names = users.get(f'{day}-{classes}')
                for name in names:
                    if user_result.get(name):
                        user_result[name][f"{day}{classes}"] = item['count'] * section_dic[name][1] * price
                    else:
                        user_result[name] = {f"{day}{classes}": item['count']}

            result.append(dic)
        result.append(user_result.values())
        return Response({'result': result})


@method_decorator([api_recorder], name="dispatch")
class EmployeeAttendanceRecordsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        date = self.request.query_params.get('date')
        name = self.request.query_params.get('name', '')
        year = int(date.split('-')[0])
        month = int(date.split('-')[1])
        # 获取班组
        this_month_start = datetime.datetime(year, month, 1)
        if month == 12:
            this_month_end = datetime.datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            this_month_end = datetime.datetime(year, month + 1, 1) - timedelta(days=1)
        group = WorkSchedulePlan.objects.filter(start_time__date__gte=this_month_start,
                                                start_time__date__lte=this_month_end).values('group__global_name', 'start_time__date').order_by('start_time')
        group_list = []
        for key, group in groupby(list(group), key=lambda x: x['start_time__date']):
            group_list.append([item['group__global_name'] for item in group])

        results = {}
        data = EmployeeAttendanceRecords.objects.filter(date__year=year, date__month=month, name__icontains=name).values(
            'equip', 'section', 'group', 'date__day', 'name')
        for item in data:
            equip = item['equip']
            section = item['section']
            if not results.get(f'{equip}_{section}'):
                results[f'{equip}_{section}'] = {'equip': equip, 'section': section}
            results[f'{equip}_{section}'][f"{item['date__day']}{item['group']}"] = item['name']
        results_sort = sorted(results.values(), key=lambda x: x['equip'])
        return Response({'results': results_sort, 'group_list': group_list})

    # 导入出勤记录
    @atomic
    def post(self, request):
        date = self.request.data.get('date')  # 2022-02
        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        rows = cur_sheet.nrows
        # 获取班组
        year = int(date.split('-')[0])
        month = int(date.split('-')[1])
        this_month_start = datetime.datetime(year, month, 1)
        if month == 12:
            this_month_end = datetime.datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            this_month_end = datetime.datetime(year, month + 1, 1) - timedelta(days=1)
        group = WorkSchedulePlan.objects.filter(start_time__date__gte=this_month_start,
                                                start_time__date__lte=this_month_end).values('group__global_name', 'start_time__date').order_by('start_time')
        group_list = []
        for key, group in groupby(list(group), key=lambda x: x['start_time__date']):
            group_list.append([item['group__global_name'] for item in group])

        equip_list = []
        for i in range(2, rows, 4):
            equip_list.append(cur_sheet.cell(i, 0).value[0:3])
        # ['Z01', 'Z02', 'Z03', 'Z04', 'Z05', 'Z06', 'Z07', 'Z08', 'Z09', 'Z10', 'Z11', 'Z12', 'Z13', 'Z14', 'Z15']
        section_list = []
        for i in range(2, rows):
            section_list.append(cur_sheet.cell(i, 1).value)
        start_row = 2
        rows_num = cur_sheet.nrows  # sheet行数
        if rows_num <= start_row:
            return []
        ret = [None] * (rows_num - start_row)
        for i in range(start_row, rows_num):
            ret[i - start_row] = cur_sheet.row_values(i)[2:]
        data = ret
        records_lst = []
        # 判断出勤记录是否存在，存在就更新
        records = list(EmployeeAttendanceRecords.objects.filter(date__year=year, date__month=month).values(
            'name', 'section', 'date', 'classes', 'equip'))
        for i in data:
            """
            ['王二', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
            """
            index = data.index(i)
            for name in i:
                if name:
                    name_index = i.index(name) + 1
                    if name_index // 2 == 0:
                        day = name_index
                    else:
                        day = (name_index + 1) // 2
                    date_ = f'{date}-{day}'
                    name = name
                    section = section_list[index]
                    classes = group_list[day - 1][i.index(name) % 2]
                    equip = equip_list[index // 4]
                    dic = {'name': name, 'section': section, 'date': date_, 'classes': classes, 'equip': equip}
                    dic2 = dic.copy()
                    dic2.pop('name')
                    if dic in records:
                        continue
                    if EmployeeAttendanceRecords.objects.filter(**dic2).exists():
                        EmployeeAttendanceRecords.objects.filter(**dic2).update(name=name)
                        continue
                    records_obj = EmployeeAttendanceRecords(**dic)
                    records_lst.append(records_obj)
        EmployeeAttendanceRecords.objects.bulk_create(records_lst)
        return Response(f'导入成功')


@method_decorator([api_recorder], name="dispatch")
class EmployeeAttendanceRecordsExport(ViewSet):
    permission_classes = (IsAuthenticated,)

    # 导出模板
    def export(self, request):
        response = HttpResponse(content_type='application/vnd.ms-excel')
        filename = '员工出勤记录表'
        response['Content-Disposition'] = u'attachment;filename= ' + filename.encode('gbk').decode(
            'ISO-8859-1') + '.xls'
        # 创建一个文件对象
        wb = xlwt.Workbook(encoding='utf8')
        # 创建一个sheet对象
        sheet = wb.add_sheet('sheet1', cell_overwrite_ok=True)
        alignment = xlwt.Alignment()
        alignment.horz = xlwt.Alignment.HORZ_CENTER
        alignment.vert = xlwt.Alignment.VERT_CENTER
        style = xlwt.XFStyle()
        style.alignment = alignment

        # 工厂排班计划
        date = self.request.query_params.get('date')
        year = int(date.split('-')[0])
        month = int(date.split('-')[1])
        this_month_start = datetime.datetime(year, month, 1)
        if month == 12:
            this_month_end = datetime.datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            this_month_end = datetime.datetime(year, month + 1, 1) - timedelta(days=1)
        # 获取班组
        group = WorkSchedulePlan.objects.filter(start_time__date__gte=this_month_start,
                                                start_time__date__lte=this_month_end).values('group__global_name', 'start_time__date').order_by('start_time')
        group_list = []
        for key, group in groupby(list(group), key=lambda x: x['start_time__date']):
            group_list.append([item['group__global_name'] for item in group])

        # 获取设备对应的机型
        equip_list = Equip.objects.filter(category__equip_type__global_name='密炼设备').order_by('equip_no').values('equip_no', 'category__category_name')
        dic = {item['equip_no']: item['category__category_name'] for item in equip_list}

        # 添加标题
        # sheet.write_merge(开始行, 结束行, 开始列, 结束列, 'My merge', style)
        sheet.write_merge(0, 1, 0, 0, '机台/时间', style)
        sheet.write_merge(0, 1, 1, 1, '岗位', style)
        for i in range(len(group_list)):
            group_list[i][0]
            sheet.write_merge(0, 0, 2 * (i + 1), 2 * (i + 1) + 1, f'{i+1}日', style)
            sheet.write_merge(1, 1, 2 * (i + 1), 2 * (i + 1), group_list[i][0], style)
            sheet.write_merge(1, 1, 2 * (i + 1) + 1, 2 * (i + 1) + 1, group_list[i][1], style)

        for i in equip_list:
            index = (list(equip_list).index(i) + 1) * 4
            sheet.write_merge(index - 2, index - 2, 0, 0, i['equip_no'] + f"({dic.get(i['equip_no'], '')})", style)
            sheet.write_merge(index - 2, index - 2, 1, 1, '主投', style)
            sheet.write_merge(index - 1, index - 1, 1, 1, '辅投', style)
            sheet.write_merge(index, index, 1, 1, '挤出', style)
            sheet.write_merge(index + 1, index + 1, 1, 1, '收皮', style)

        # 写出到IO
        output = BytesIO()
        wb.save(output)
        # 重新定位到开始
        output.seek(0)
        response.write(output.getvalue())
        return response


@method_decorator([api_recorder], name="dispatch")
class PerformanceJobLadderViewSet(ModelViewSet):
    queryset = PerformanceJobLadder.objects.filter(delete_flag=False)
    serializer_class = PerformanceJobLadderSerializer
    permission_classes = (IsAuthenticated,)
    filter_fields = ('name',)


@method_decorator([api_recorder], name="dispatch")
class PerformanceUnitPriceView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        results = {}
        state_lst = GlobalCode.objects.filter(global_type__type_name='胶料段次').values('global_name')
        # category_lst = EquipCategoryAttribute.objects.filter(delete_flag=False).values('category_no')
        category_lst = ['E580', 'F370', 'GK320', 'GK255', 'GK400']

        for state in state_lst:
            state = state['global_name']
            results[state] = {'state': state}
            for category in category_lst:
                results[state][f"{category}_pt"] = None
                results[state][f"{category}_dj"] = None

        queryset = PerformanceUnitPrice.objects.values('state', 'equip_type', 'pt', 'dj')
        for item in queryset:
            results[f"{item['state']}"][f"{item['equip_type']}_pt"] = item['pt']
            results[f"{item['state']}"][f"{item['equip_type']}_dj"] = item['dj']

        return Response({'result': results.values()})

    @atomic
    def post(self, request):
        data = self.request.data  # list
        unit_list = []
        category_lst = ['E580', 'F370', 'GK320', 'GK255', 'GK400']
        obj = PerformanceUnitPrice.objects
        for item in data:
            for category in category_lst:
                if item[f"{category}_pt"] or item[f"{category}_dj"]:
                    if obj.filter(state=item['state'], equip_type=category):
                        obj.filter(state=item['state'], equip_type=category).update(
                            pt=item[f"{category}_pt"], dj=item[f"{category}_dj"])
                    unit_list.append(PerformanceUnitPrice(
                        state=item['state'], equip_type=category, pt=item[f"{category}_pt"], dj=item[f"{category}_dj"]))
        obj.bulk_create(unit_list)
        return Response('添加成功')


@method_decorator([api_recorder], name="dispatch")
class ProductInfoDingJiViewSet(ModelViewSet):
    queryset = ProductInfoDingJi.objects.filter(delete_flag=False)
    serializer_class = ProductInfoDingJiSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductInfoDingJiFilter

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete_flag = True
        instance.delete_date = datetime.datetime.now()
        instance.delete_user = self.request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name="dispatch")
class SetThePriceViewSet(ModelViewSet):
    queryset = SetThePrice.objects.all()
    serializer_class = SetThePriceSerializer
    permission_classes = (IsAuthenticated,)


@method_decorator([api_recorder], name="dispatch")
class PerformanceSummaryView(APIView):

    # 其他补贴或惩罚
    def post(self, request):
        # SubsidyInfo.objects.create()
        pass

    def get(self, request):
        """
        results: [
            {'name': '张三',  '1A': 220, '1C': 230, '2A': 300, 'hj': 450, 'cc': '', qt': '', 'sc': ''}
            {'name': '李四',  '1A': 220, '1C': 230, '2A': 300, 'hj': 450, 'cc': '', qt': '', 'sc': ''}
        ]
        """
        date = self.request.get('date')
        name = self.request.query_params.get('name', '')
        year = int(date.split('-')[0])
        month = int(date.split('-')[1])
        this_month_start = datetime.datetime(year, month, 1)
        if month == 12:
            this_month_end = datetime.datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            this_month_end = datetime.datetime(year, month + 1, 1) - timedelta(days=1)

        # 员工考勤记录 (考勤记录)
        user_query = EmployeeAttendanceRecords.objects.filter(date__year=year, date__month=month)
        queryset = user_query.values_list('name', 'section', 'date__day', 'group', 'equip', flat=True)
        user_dic = {}
        for item in queryset:
            key = f"{item[2]}_{item[3]}_{item[1]}_{item[4]}"
            user_dic[key] = {'name': item[0], 'section': item[1], 'day': item[2], 'group': item[3], 'equip': item[4]}
        """
        1_a班_投料_Z01_早班 : {'name' : '张三'， 'section': '投料', 'equip_no': Z01}
        1_a班_挤出_Z02_早班：{'name: '张三', 'section': '挤出', 'equip_no': Z01}
        1_a班_投料_Z02_早班：{'name: '张三', 'section': '挤出', 'equip_no': Z01}
        
        name   section group  day  equip classes
        张三   投料   a班    1       Z01  早班
        张三   挤出   a班    1       Z01  早班
        张三   投料   a班    1       Z02  早班
        """

        # user_dic 中添加classes属性
        group = WorkSchedulePlan.objects.filter(start_time__year=year,
                                                start_time__month=month).values_list('group__global_name', 'classes__global_name', 'start_time__day', flat=True)
        for key in user_dic.keys():
            for item in group:
                if item[2] == key.split('_')[0] and item[0] == key.split('_')[1]:
                    user_dic[f"{key}_{item[1]}"] = user_dic[key]
                    user_dic[f"{key}_{item[1]}"]['classes'] = item[1]
                    user_dic.pop(key, None)
        # 1_a班_投料_Z02_早班：{'name: '张三', 'section': '挤出', 'equip_no': Z01, 'classes': '早班'}

        # 密炼的产量，
        product_qty = TrainsFeedbacks.objects.values('classes', 'equip_no', 'factory_date__day', 'product_no').\
            annotate(qty=Count('id')).values('qty', 'classes', 'equip_no', 'factory_date__day', 'product_no')
        for item in product_qty:
            equip_no = item['equip_no']
            equip_type = Equip.objects.filter(equip_no=equip_no).values('category__category_no')[0]['category__category_no']
            state = item['product_no'].split('-')[1]
            price_obj = PerformanceUnitPrice.objects.filter(equip_type=equip_type, state=state).first()
            # 判断是否是丁基胶
            if ProductInfoDingJi.objects.filter(is_use=True, product_no=item['product_no']).exists():
                for key in user_dic.keys():
                    if key.split('_')[0] == item['factory_date__day'] and key.split('_')[4] == item['classes']:
                        user_dic[key][f"{state}_pt_qty"] = user_dic[key].get(f"{state}_pt_qty", 0) + item['qty']
                        user_dic[key][f"{state}_pt_unit"] = price_obj.pt

            else:
                for key in user_dic.keys():
                    if key.split('_')[0] == item['factory_date__day'] and key.split('_')[4] == item['classes']:
                        user_dic[key][f"{state}_dj_qty"] = user_dic[key].get(f"{state}_dj_qty", 0) + item['qty']
                        user_dic[key][f"{state}_dj_unit"] = price_obj.dj

         # '1_a班_投料_Z02_早班': {'name: '张三', 'section': '挤出', 'equip_no': Z01, 'classes': '早班', '1MB_qty': 20, '1MB_unit': 1.10, ...}

        # 称量的产量
        equip_list = Equip.objects.filter(category__equip_type__global_name='称量设备').values_list('equip_no', flat=True)
        # 细料/硫磺单价
        price_obj = SetThePrice.objects.first()
        equip_data = {}
        for equip_no in equip_list:
            price = price_obj.xl if equip_no in ['F01', 'F02', 'F03'] else price_obj.lh
            equip_data[equip_no] = {'price': price}
            data = Plan.objects.using(equip_no).filter(actno__gt=1, state='完成',
                                                       date_time__get=this_month_start,
                                                       date_time__lte=this_month_end).values('date_time', 'grouptime').annotate(
                'date_time', 'grouptime', 'repice', count=Count('actno'))

            for item in data:
                day = int(item['date_time'].split('-')[-1])
                state = item['repice'].split('-')[1]
                for key in user_dic.keys():
                    if item['grouptime'] == key.split('_')[4] and day == key.split('_')[0] and equip_no == key.split('_')[3]:
                        user_dic[key][f"{state}_qty"] = user_dic[key].get(f"{state}_qty", 0) + item[0]
                        user_dic[key][price] = price

        # '1_a班_投料_F01_早班': {'name: '张三', 'section': '挤出', 'equip_no': F01, 'classes': '早班', '1MB_qty': 10, 'price': 1.10}

        """
        user_dic: {
            '1_a班_投料_Z01_早班': {'name: '张三', 'section': '挤出', 'equip_no': Z01, 'classes': '早班', '1MB_qty': 20, '1MB_unit': 1.10, ...}
            1_a班_挤出_Z02_早班：{'name: '张三', 'section': '挤出', 'equip_no': Z02, 'classes': '早班', '1MB_qty': 20, '1MB_unit': 1.10, ...}
            '1_a班_投料_F01_早班': {'name: '张三', 'section': '挤出', 'equip_no': F01, 'classes': '早班', '1MB_qty': 10, 'price': 1.10}
        }
        """


