import decimal
import json
import datetime
import re

import math
import time
from io import BytesIO
from itertools import groupby, count
from itertools import count as c

import requests
import xlrd
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
from plan.models import ProductClassesPlan, SchedulingEquipShutDownPlan
from basics.models import Equip
from production.filters import TrainsFeedbacksFilter, PalletFeedbacksFilter, QualityControlFilter, EquipStatusFilter, \
    PlanStatusFilter, ExpendMaterialFilter, CollectTrainsFeedbacksFilter, UnReachedCapacityCause, \
    ProductInfoDingJiFilter, SubsidyInfoFilter, PerformanceJobLadderFilter, AttendanceGroupSetupFilter, Equip190EFilter, \
    AttendanceClockDetailFilter
from production.models import TrainsFeedbacks, PalletFeedbacks, EquipStatus, PlanStatus, ExpendMaterial, OperationLog, \
    QualityControl, ProcessFeedback, AlarmLog, MaterialTankStatus, ProductionDailyRecords, ProductionPersonnelRecords, \
    RubberCannotPutinReason, MachineTargetYieldSettings, EmployeeAttendanceRecords, PerformanceJobLadder, \
    PerformanceUnitPrice, ProductInfoDingJi, SetThePrice, SubsidyInfo, IndependentPostTemplate, AttendanceGroupSetup, \
    FillCardApply, ApplyForExtraWork, EquipMaxValueCache, Equip190EWeight, OuterMaterial, Equip190E, \
    AttendanceClockDetail, AttendanceResultAudit, ManualInputTrains
from production.serializers import QualityControlSerializer, OperationLogSerializer, ExpendMaterialSerializer, \
    PlanStatusSerializer, EquipStatusSerializer, PalletFeedbacksSerializer, TrainsFeedbacksSerializer, \
    ProductionRecordSerializer, TrainsFeedbacksBatchSerializer, CollectTrainsFeedbacksSerializer, \
    ProductionPlanRealityAnalysisSerializer, UnReachedCapacityCauseSerializer, TrainsFeedbacksSerializer2, \
    CurveInformationSerializer, MixerInformationSerializer2, WeighInformationSerializer2, AlarmLogSerializer, \
    ProcessFeedbackSerializer, TrainsFixSerializer, PalletFeedbacksBatchModifySerializer, ProductPlanRealViewSerializer, \
    RubberCannotPutinReasonSerializer, PerformanceJobLadderSerializer, ProductInfoDingJiSerializer, \
    SetThePriceSerializer, SubsidyInfoSerializer, AttendanceGroupSetupSerializer, EmployeeAttendanceRecordsSerializer, \
    FillCardApplySerializer, ApplyForExtraWorkSerializer, Equip190EWeightSerializer, OuterMaterialSerializer, \
    Equip190ESerializer, EquipStatusBatchSerializer, AttendanceClockDetailSerializer
from rest_framework.generics import ListAPIView, GenericAPIView, ListCreateAPIView, CreateAPIView, UpdateAPIView, \
    get_object_or_404
from datetime import timedelta

from quality.models import BatchProductNo, BatchDay, Batch, BatchMonth, BatchYear, MaterialTestOrder, \
    MaterialDealResult, MaterialTestResult, MaterialDataPointIndicator
from quality.serializers import BatchProductNoDateZhPassSerializer, BatchProductNoClassZhPassSerializer
from quality.utils import get_cur_sheet, get_sheet_data
from system.models import User, Section
from terminal.models import Plan
from equipment.utils import DinDinAPI


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
        for item in request.data:
            p = item['pallet_no']
            b = re.sub(u'\u0000', "", p)
            item['pallet_no'] = b
        serializer = PalletFeedbacksSerializer(data=request.data, many=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("sync success", status=201)


@method_decorator([api_recorder], name="dispatch")
class EquipStatusBatch(APIView):
    """批量同步设备生产数据接口"""

    @atomic
    def post(self, request):
        serializer = EquipStatusBatchSerializer(data=request.data, many=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
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
        'AI值': 'ai_value',
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
        auto = self.request.query_params.get('auto', False)
        manual = self.request.query_params.get('manual', False)
        day_time = self.request.query_params.get('day_time', datetime.datetime.now().date())
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.filter(work_schedule_plan__plan_schedule__day_time=day_time)
        if manual:
            add_data = ManualInputTrains.objects.filter(factory_date=day_time).values(
                'factory_date', 'equip_no', 'product_no', 'classes', 'actual_trains')
        else:
            add_data = []
        for classes in ['早班', '中班', '夜班']:
            page = queryset.filter(work_schedule_plan__classes__global_name=classes)
            data = self.get_serializer(page, many=True).data
            data = list(filter(lambda x: x['begin_time'] is not None, data))
            data.sort(key=lambda x: x['begin_time'])
            ret[classes] = data if auto else []

        for item in add_data:
            tfb_obj = TrainsFeedbacks.objects.filter(product_no=item['product_no'],
                                                     factory_date=item['factory_date']).order_by('id').first()
            if tfb_obj:
                plan_obj = self.queryset.filter(plan_classes_uid=tfb_obj.plan_classes_uid).first()
            else:
                plan_obj = None
            last_obj = TrainsFeedbacks.objects.filter(product_no=item['product_no'],
                                                     factory_date=item['factory_date']).order_by('id').last()
            begin_time = tfb_obj.begin_time.strftime("%Y-%m-%d %H:%M:%S") if tfb_obj else None
            kwargs = {
                'classes': item['classes'],
                'plan_trains': plan_obj.plan_trains if plan_obj else None,
                'actual_trains': last_obj.actual_trains if last_obj else None,
                'product_no': item['product_no'],
                'begin_time': begin_time
            }
            if kwargs in ret[item['classes']]:
                index = ret[item['classes']].index(kwargs)
                ret[item['classes']][index] = kwargs.update({'actual_trains': kwargs['actual_trains'] + item['actual_trains']})
            else:
                ret[item['classes']].append(kwargs.update({'actual_trains': item['actual_trains']}))

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
    queryset = TrainsFeedbacks.objects.filter(Q(~Q(equip_no='Z04')) | Q(equip_no='Z04', operation_user='Mixer1'))
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
        a = datetime.datetime.strptime(st, '%Y-%m-%d')
        b = datetime.datetime.strptime(et, '%Y-%m-%d')
        ds = (b - a).days + 1
        state = self.request.query_params.get('state')  # 段数
        equip = self.request.query_params.get('equip')
        space = self.request.query_params.get('space', '')  # 规格    C-FM-C101-02
        if state:
            kwargs = {'equip_no': equip, 'product_no__icontains': f"-{state}-{space}"} if equip else \
                {'product_no__icontains': f"-{state}-{space}"}
            spare_weight = self.queryset.filter(**kwargs, factory_date__lte=et,
                                                factory_date__gte=st,
                                                ).aggregate(spare_weight=Sum('actual_weight'))['spare_weight']
            queryset = self.queryset.filter(**kwargs, factory_date__lte=et, factory_date__gte=st,
                                            ).values('equip_no', 'product_no', 'factory_date')\
                .annotate(value=Count('id'), weight=Sum('actual_weight'))

            dic = {}
            for item in queryset:
                space_equip = f"{item['product_no'].split('-')[2]}-{item['equip_no']}-{datetime.datetime.strftime(item['factory_date'], '%Y%m%d')}"
                if dic.get(space_equip):
                    dic[space_equip]['value'] += item['value']
                    dic[space_equip]['weight'] += round(item['weight'] / 100000, 2)
                    dic[space_equip]['ratio'] += round(item['weight'] / spare_weight, 2)
                else:
                    dic[space_equip] = {'space': item['product_no'].split('-')[2],
                                        'equip_no': item['equip_no'],
                                        'time': datetime.datetime.strftime(item['factory_date'], '%m/%d'),
                                        'value': item['value'],
                                        'weight': round(item['weight'] / 100000, 2),
                                        'ratio': round(item['weight'] / spare_weight, 2)
                                        }
            result = sorted(dic.values(), key=lambda x: (x['space'], x['equip_no'], x['time']))
            return Response({'result': result})
        else:
            # 取每个机台的历史最大值
            dic = {}
            equip_max_value = TrainsFeedbacks.objects.filter(Q(~Q(equip_no='Z04')) |
                                                             Q(equip_no='Z04', operation_user='Mixer1')).\
                values('equip_no', 'factory_date').annotate(
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
                item['weight'] = round(item['weight'] / 100000, 2)
                item['max_value'] = dic[item['equip_no']] if dic.get(item['equip_no']) else None
                if settings_value:
                    item['settings_value'] = settings_value.__dict__.get('E190') if item['equip_no'] == '190E' else\
                        settings_value.__dict__.get(item['equip_no'])
                    item['settings_value'] *= ds * 2
                else:
                    item['settings_value'] = None
            # 获取不同段次的总重量
            state_value = self.queryset.filter(factory_date__gte=st, factory_date__lte=et).values('product_no').annotate(weight=Sum('actual_weight'))
            jl = {'jl': 0}
            wl = {'wl': 0}

            for item in state_value:
                if item['product_no'].split('-')[1] in ['RE', 'FM', 'RFM']:
                    if jl.get(item['product_no'].split('-')[1]):
                        jl[item['product_no'].split('-')[1]] += round(item['weight'] / 100000, 2)
                    else:
                        jl[item['product_no'].split('-')[1]] = round(item['weight'] / 100000, 2)
                    jl['jl'] += round(item['weight'] / 100000, 2)
                else:
                    if wl.get(item['product_no'].split('-')[1]):
                        wl[item['product_no'].split('-')[1]] += round(item['weight'] / 100000, 2)
                    else:
                        wl[item['product_no'].split('-')[1]] = round(item['weight'] / 100000, 2)
                    wl['wl'] += round(item['weight'] / 100000, 2)

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


@method_decorator([api_recorder], name="dispatch")
class DailyProductionCompletionReport(APIView):
    permission_classes = (IsAuthenticated,)
    pagination_class = None

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
            'name_1': {'name': '混炼胶实际完成(吨)', 'weight': 0},
            'name_2': {'name': '终炼胶实际完成(吨)', 'weight': 0},
            'name_3': {'name': '外发无硫料(吨)', 'weight': 0},
            'name_4': {'name': '实际完成数-1(吨)', 'weight': 0},
            'name_5': {'name': '实际完成数-2(吨)', 'weight': 0},
            'name_6': {'name': '实际生产工作日数', 'weight': 0},
            'name_7': {'name': '日均完成率1', 'weight': None},
            'name_8': {'name': '日均完成率2', 'weight': None},
        }
        # 混炼实际完成吨  CMB HMB 1MB~4MB
        queryset1 = TrainsFeedbacks.objects.filter(Q(factory_date__year=year, factory_date__month=month) &
                                                  Q(Q(product_no__icontains='-CMB-') |
                                                    Q(product_no__icontains='-HMB-') |
                                                    Q(product_no__icontains='-1MB-') |
                                                    Q(product_no__icontains='-2MB-') |
                                                    Q(product_no__icontains='-3MB-') |
                                                    Q(product_no__icontains='-4MB-')))
        mix_queryset = queryset1.values('factory_date__day').annotate(weight=Sum('actual_weight'))
        # 终炼实际完成（吨）  FM
        queryset2 = TrainsFeedbacks.objects.filter(Q(factory_date__year=year, factory_date__month=month) &
                                                Q(product_no__icontains='-FM-'))
        fin_queryset = queryset2.values('factory_date__day').annotate(weight=Sum('actual_weight'))
        equip_190e_weight = Equip190EWeight.objects.filter(factory_date__year=year, factory_date__month=month).\
            values('factory_date__day', 'setup__weight', 'qty')
        for item in mix_queryset:
            results['name_1']['weight'] += round(item['weight'] / 100000, 2)
            results['name_1'][f"{item['factory_date__day']}日"] = round(item['weight'] / 100000, 2)
        for item in equip_190e_weight:
            weight = round(item['setup__weight'] / 1000 * item['qty'], 2)
            results['name_2']['weight'] += weight
            results['name_2'][f"{item['factory_date__day']}日"] = results['name_2'].get(f"{item['factory_date__day']}日", 0) + weight
        for item in fin_queryset:
            results['name_2']['weight'] += round(item['weight'] / 100000, 2)
            results['name_4']['weight'] += round(item['weight'] / 100000, 2)
            results['name_5']['weight'] += round(item['weight'] / 100000, 2)
            results['name_2'][f"{item['factory_date__day']}日"] = round(item['weight'] / 100000, 2)
            results['name_4'][f"{item['factory_date__day']}日"] = round(item['weight'] / 100000, 2)
            results['name_5'][f"{item['factory_date__day']}日"] = round(item['weight'] / 100000, 2)
        # 外发无硫料（吨）
        out_queryset = OuterMaterial.objects.filter(factory_date__year=year,
                                                    factory_date__month=month).values('factory_date__day', 'weight')
        for item in out_queryset:
            results['name_3'][f"{item['factory_date__day']}日"] = round(item['weight'], 2)
            results['name_4'][f"{item['factory_date__day']}日"] = results['name_4'].get(f"{item['factory_date__day']}日", 0) + round((item['weight']) * decimal.Decimal(0.7), 2)
            results['name_5'][f"{item['factory_date__day']}日"] = results['name_5'].get(f"{item['factory_date__day']}日", 0) + round(item['weight'], 2)
            results['name_3']['weight'] += round(item['weight'], 2)
            results['name_4']['weight'] += round((item['weight']) * decimal.Decimal(0.7), 2)
            results['name_5']['weight'] += round(item['weight'], 2)
        shot_down_dic = {}
        shot_down = SchedulingEquipShutDownPlan.objects.filter(begin_time__year=year, begin_time__month=month).\
            values('begin_time__day', 'equip_no', 'duration')
        for item in shot_down:
            if shot_down_dic.get(item['begin_time__day']):
                if shot_down_dic[item['begin_time__day']].get(item['equip_no']):
                    shot_down_dic[item['begin_time__day']][item['equip_no']] += item['duration']
                else:
                    shot_down_dic[item['begin_time__day']][item['equip_no']] = item['duration']
            else:
                shot_down_dic[item['begin_time__day']] = {item['equip_no']: item['duration']}
        # 开机机台
        equip_queryset1 = queryset1.values('equip_no', 'factory_date__day').annotate(a=Count('id')).values('equip_no', 'factory_date__day')
        equip_queryset2 = queryset2.values('equip_no', 'factory_date__day').annotate(a=Count('id')).values_list('equip_no', 'factory_date__day')
        equip_queryset = equip_queryset1 | equip_queryset2
        equip_dic = {
            #  day: []
        }
        for item in equip_queryset:
            day = int(item['factory_date__day'])
            equip_no = item['equip_no']
            if equip_dic.get(day):
                if equip_no not in equip_dic[day]:
                    equip_dic[day].append(equip_no)
            else:
                equip_dic[day] = [equip_no]
        for day, lst in equip_dic.items():
            equip_lst = shot_down_dic.get(day)
            # 相交的为发生故障的机台
            down_equip = list(set(lst).intersection(set(equip_lst))) if equip_lst else []
            down_time = sum([shot_down_dic[day].get(e, 0) for e in down_equip]) if shot_down_dic.get(day) else 0
            results['name_6'][f"{day}日"] = round(((24 * len(equip_dic.get(day))) - down_time) / (24 * len(equip_dic.get(day))), 2)
        if len(results['name_6']) - 2 != 0:
            results['name_6']['weight'] = round(sum([v for k, v in results['name_6'].items() if k[0].isdigit()]) / (len(results['name_6']) - 2), 2)
            for key, value in results['name_4'].items():
                if key[0].isdigit():
                    if results['name_6'].get(key):
                        results['name_7'][key] = round(results['name_4'][key] / decimal.Decimal(results['name_6'][key]), 2)
                        results['name_8'][key] = round(results['name_5'][key] / decimal.Decimal(results['name_6'][key]), 2)
            results['name_7']['weight'] = round(results['name_4']['weight'] / decimal.Decimal(results['name_6']['weight']), 2)
            results['name_8']['weight'] = round(results['name_5']['weight'] / decimal.Decimal(results['name_6']['weight']), 2)
        return Response({'results': results.values()})

    def post(self, request):
        # 190E机台产量录入
        factory_date = self.request.data.get('factory_date', None)
        classes = self.request.data.get('classes', None)
        data = self.request.data.get('data', [])
        date = self.request.data.get('date')
        outer_data = self.request.data.get('outer_data', [])  # 外发无硫料
        if data:
            serializer = Equip190EWeightSerializer(data=data, many=True)
            serializer.is_valid(raise_exception=True)
            Equip190EWeight.objects.filter(factory_date=factory_date, classes=classes).delete()
            for item in serializer.validated_data:
                Equip190EWeight.objects.create(
                    **{'setup': item['setup'],
                       'factory_date': factory_date,
                        'classes': classes,
                        'qty': item['qty']})
        if data == []:
            Equip190EWeight.objects.filter(factory_date=factory_date, classes=classes).delete()

        if date:
            year, month = int(date.split('-')[0]), int(date.split('-')[1])
            OuterMaterial.objects.filter(factory_date__year=year, factory_date__month=month).delete()
            for item in outer_data:
                OuterMaterial.objects.create(factory_date=item['factory_date'],
                                             weight=item['weight'])
        return Response('ok')


@method_decorator([api_recorder], name="dispatch")
class Equip190EViewSet(ModelViewSet):
    queryset = Equip190E.objects.order_by('id')
    serializer_class = Equip190ESerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = Equip190EFilter
    pagination_class = None

    def list(self, request, *args, **kwargs):
        if self.request.query_params.get('search'):
            return Response({'results': list(set(self.queryset.values_list('specification', flat=True)))})
        if self.request.query_params.get('detail'):
            factory_date = self.request.query_params.get('factory_date')
            classes = self.request.query_params.get('classes')
            instance = Equip190EWeight.objects.filter(factory_date=factory_date, classes=classes)
            serializer = Equip190EWeightSerializer(instance=instance, many=True)
            return Response({'results': serializer.data})
        return super().list(request, *args, **kwargs)

    @action(methods=['post'], detail=False, permission_classes=[], url_path='import_xlsx',
            url_name='import_xlsx')
    def import_xlsx(self, request):
        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        if cur_sheet.ncols != 3:
            raise ValidationError('导入文件数据错误！')
        data = get_sheet_data(cur_sheet)
        parts_list = []
        for item in data:
            if not item[0]:
                raise ValidationError('规格不可为空')
            if not item[1]:
                raise ValidationError('段数不可为空')
            if not item[2]:
                raise ValidationError('重量不可为空')
            parts_list.append({
                'specification': item[0],
                'state': item[1],
                'weight': item[2]
            })

        s = Equip190ESerializer(data=parts_list, many=True, context={'request': request})
        if s.is_valid(raise_exception=False):
            if len(s.validated_data) < 1:
                raise ValidationError('没有可导入的数据')
            data = s.validated_data
            for item in data:
                Equip190E.objects.update_or_create(defaults=item,
                                                   specification=item['specification'],
                                                   state=item['state'])
        else:
            raise ValidationError('导入的数据类型有误')
        return Response(f'成功导入{len(s.validated_data)}条数据')


@method_decorator([api_recorder], name="dispatch")
class SummaryOfMillOutput(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        factory_date = self.request.query_params.get('factory_date')
        auto = self.request.query_params.get('auto', False)
        manual = self.request.query_params.get('manual', False)
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
        if auto:
            data1 = TrainsFeedbacks.objects.filter(factory_date=factory_date).values('equip_no',
                                                                                    'product_no', 'classes').annotate(
                actual_trains=Count('actual_trains')).values('equip_no', 'product_no', 'classes', 'actual_trains')
        else:
            data1 = []
        if manual:
            data2 = ManualInputTrains.objects.filter(factory_date=factory_date).values(
                'equip_no', 'product_no', 'classes', 'actual_trains')
        else:
            data2 = []
        data = data1 | data2
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
                count[f"{state}-{classes}"] += actual_trains
                count['count'] += actual_trains
        for dic in results.values():
            for key, value in dic.items():
                dic[key] = None if not dic[key] else dic[key]
        return Response({'results': results.values(), 'count': count, 'state_list': state_list})


@method_decorator([api_recorder], name="dispatch")
class SummaryOfWeighingOutput(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        factory_date = self.request.query_params.get('factory_date')
        year = int(factory_date.split('-')[0])
        month = int(factory_date.split('-')[1])
        equip_list = Equip.objects.filter(category__equip_type__global_name='称量设备').values_list('equip_no', flat=True)
        result = []
        result1 = {}
        group_dic = {}
        users = {}
        work_times = {}
        user_result = {}
        group = WorkSchedulePlan.objects.filter(start_time__year=year,
                                                start_time__month=month).values_list('group__global_name', 'classes__global_name', 'start_time__day')
        for item in group:
            group_dic[f'{item[2]}-{item[0]}'] = item[1]
        # 查询称量分类下当前月上班的所有员工
        user_list = EmployeeAttendanceRecords.objects.filter(
            Q(factory_date__year=year, factory_date__month=month, equip__in=equip_list) &
            Q(Q(end_date__isnull=False, begin_date__isnull=False) | Q(end_date__isnull=True, begin_date__isnull=True)) &
            ~Q(is_use='废弃')).values('user__username', 'factory_date__day', 'group', 'section', 'equip')

        # 岗位系数
        section_dic = {}
        section_info = PerformanceJobLadder.objects.filter(delete_flag=False, type__in=['细料称量', '硫磺称量']).values('type', 'name', 'coefficient', 'post_standard', 'post_coefficient')
        for item in section_info:
            section_dic[f"{item['name']}_{item['type']}"] = [item['coefficient'], item['post_standard'], item['post_coefficient']]

        for item in user_list:
            classes = group_dic.get(f"{item['factory_date__day']}-{item['group']}")
            key = f"{item['factory_date__day']}-{classes}-{item['equip']}"
            if users.get(key):
                work_times[key][item['user__username']] = item['actual_time']
                users[key][item['user__username']] = item['section']
            else:
                work_times[key] = {item['user__username']: item['actual_time']}
                users[key] = {item['user__username']: item['section']}

        # 机台产量统计
        price_obj = SetThePrice.objects.first()
        if not price_obj:
            raise ValidationError('请先去添加细料/硫磺单价')
        for equip_no in equip_list:
            dic = {'equip_no': equip_no, 'hj': 0}
            data = Plan.objects.using(equip_no).filter(actno__gt=1, state='完成',
                                                       date_time__istartswith=factory_date
                                                       ).values('date_time', 'grouptime').annotate(count=Sum('actno'))
            for item in data:
                date = item['date_time']
                day = int(date.split('-')[2])    # 2  早班
                classes = item['grouptime']  # 早班/ 中班 / 夜班
                dic[f'{day}{classes}'] = item['count']
                dic['hj'] += item['count']
                names = users.get(f'{day}-{classes}-{equip_no}')
                if names:
                    for name, section in names.items():
                        key = f"{name}_{day}_{classes}_{section}"
                        work_time = work_times.get(f'{day}-{classes}-{equip_no}').get(name)
                        if user_result.get(key):
                            # user_result[key][equip_no] = item['count']
                            user_result[key][equip_no] = int(item['count'] / 12 * work_time)
                        else:
                            # user_result[key] = {equip_no: item['count']}
                            user_result[key] = {equip_no: int(item['count'] / 12 * work_time)}
            result.append(dic)
        for key, value in user_result.items():  # value {'F03': 109, 'F02': 100,},
            name, day, classes, section = key.split('_')
            equip = list(value.keys())[0]
            type = '细料称量' if equip in ['F01', 'F02', 'F03'] else '硫磺称量'
            if section_dic[f"{section}_{type}"][1] == 1:  # 最大值
                equip, count_ = sorted(value.items(), key=lambda kv: (kv[1], kv[0]))[-1]
                # 细料/硫磺单价'
                unit_price = price_obj.xl if equip in ['F01', 'F02', 'F03'] else price_obj.lh
                coefficient = section_dic[f"{section}_{type}"][0] / 100
                post_coefficient = section_dic[f"{section}_{type}"][2] / 100
                price = round(count_ * coefficient * post_coefficient * unit_price, 2)
                xl = price if equip in ['F01', 'F02', 'F03'] else 0
                lh = price if equip in ['S01', 'S02'] else 0
            else:  # 平均值
                equip = list(value.keys())[0]
                count_ = sum(value.values()) / len(value)
                unit_price = price_obj.xl if equip in ['F01', 'F02', 'F03'] else price_obj.lh
                coefficient = section_dic[f"{section}_{type}"][0] / 100
                post_coefficient = section_dic[f"{section}_{type}"][2] / 100
                price = round(count_ * coefficient * post_coefficient * unit_price, 2)
                xl = price if equip in ['F01', 'F02', 'F03'] else 0
                lh = price if equip in ['S01', 'S02'] else 0

            if result1.get(name):
                result1[name][f"{day}{classes}"] = price
                result1[name]['xl'] += xl
                result1[name]['lh'] += lh
            else:
                result1[name] = {'name': name, f"{day}{classes}": price, 'xl': xl, 'lh': lh}
        return Response({'results': result, 'users': result1.values()})


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
        data = EmployeeAttendanceRecords.objects.filter(
            Q(Q(end_date__isnull=True, begin_date__isnull=True) | Q(begin_date__isnull=False, end_date__isnull=False)) &
            Q(factory_date__year=year, factory_date__month=month, user__username__icontains=name) &
            ~Q(is_use='废弃')
            ).values(
            'equip', 'section', 'group', 'factory_date__day', 'user__username', 'actual_time')
        for item in data:
            equip = item['equip']
            section = item['section']
            if not results.get(f'{equip}_{section}'):
                results[f'{equip}_{section}'] = {'equip': equip, 'section': section}
            value = item['user__username'] if item['actual_time'] == 12 else '%s(%.1f)' % (item['user__username'], item['actual_time'])
            if results[f'{equip}_{section}'].get(f"{item['factory_date__day']}{item['group']}"):
                results[f'{equip}_{section}'][f"{item['factory_date__day']}{item['group']}"].append(value)
            else:
                results[f'{equip}_{section}'][f"{item['factory_date__day']}{item['group']}"] = [value]
        res = list(results.values())
        for item in res:
            item['equip'] = '' if not item.get('equip') else item['equip']
            item['sort'] = 2 if not item.get('equip') else 1
        results_sort = sorted(list(results.values()), key=lambda x: (x['sort'], x['equip']))
        audit_obj = AttendanceResultAudit.objects.filter(date=date, audit_user__isnull=False).last()
        approve_obj = AttendanceResultAudit.objects.filter(date=date, approve_user__isnull=False).last()
        return Response({'results': results_sort, 'group_list': group_list,
                         'audit_user':  audit_obj.audit_user if audit_obj else None,
                         'approve_user': approve_obj.approve_user if approve_obj else None})



    # 导入出勤记录
    @atomic
    def post(self, request):
        date = self.request.data.get('date')  # 2022-02
        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        rows = cur_sheet.nrows
        cols = cur_sheet.ncols
        if cur_sheet.row_values(0)[1] != '日期' or cur_sheet.row_values(1)[1] != '班次' or cur_sheet.row_values(2)[1] != '班别':
            raise ValidationError("导入的格式有误")
        # 获取班组
        year = int(date.split('-')[0])
        month = int(date.split('-')[1])
        if (datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)).day != (cols - 2) / 2:
            raise ValidationError("导入的格式有误")
        this_month_start = datetime.datetime(year, month, 1)
        if month == 12:
            this_month_end = datetime.datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            this_month_end = datetime.datetime(year, month + 1, 1) - timedelta(days=1)

        group = WorkSchedulePlan.objects.filter(start_time__date__gte=this_month_start,
                                                start_time__date__lte=this_month_end).values('group__global_name', 'classes__global_name', 'start_time__day').order_by('start_time')
        group_dic = {}
        classes_dic = {}
        for item in group:
            day = item['start_time__day']
            if group_dic.get(day):
                group_dic[day].append(item['group__global_name'])
            else:
                group_dic[day] = [item['group__global_name']]
            if classes_dic.get(day):
                classes_dic[day].append(item['classes__global_name'])
            else:
                classes_dic[day] = [item['classes__global_name']]
        group_list, classes_list = list(group_dic.values()), list(classes_dic.values())
        start_row = 3
        equip_list = []
        for i in range(start_row, rows):
            equip_list.append(cur_sheet.cell(i, 0).value)
        for i in equip_list:
            index = equip_list.index(i)
            if not equip_list[index]:
                equip_list[index] = equip_list[index - 1]
        section_list = []
        for i in range(start_row, rows):
            section_list.append(cur_sheet.cell(i, 1).value)
        rows_num = cur_sheet.nrows  # sheet行数
        if rows_num <= start_row:
            raise ValidationError('没有可导入的数据')
        ret = [None] * (rows_num - start_row)
        for i in range(start_row, rows_num):
            ret[i - start_row] = cur_sheet.row_values(i)[2:]
        data = ret
        records_lst = []
        # 判断出勤记录是否存在，存在就更新
        records = list(EmployeeAttendanceRecords.objects.filter(factory_date__year=year, factory_date__month=month).values(
            'user', 'section', 'factory_date', 'group', 'equip'))
        for names in data:
            index = data.index(names)
            for i, name in enumerate(names):
                if name:
                    day = (i // 2) + 1
                    date_ = f'{date}-{day}'
                    user = User.objects.filter(username=name).first()
                    if not user:
                        raise ValidationError(f'系统中不存在{name}用户')
                    section = section_list[index]
                    group = group_list[day - 1][i % 2]
                    classes = classes_list[day - 1][i % 2]
                    equip = equip_list[index]
                    if equip in ['辅助', '班长']:
                        equips = [None]
                    elif ',' in equip:
                        equips = equip.split(',')
                    else:
                        equips = [equip]
                    for equip in equips:
                        dic = {'user': user, 'section': section, 'factory_date': date_, 'group': group, 'classes': classes, 'equip': equip, 'work_time': 12, 'actual_time': 12}
                        if dic in records:
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
                                                start_time__date__lte=this_month_end).values('group__global_name', 'classes__global_name', 'start_time__day').order_by('start_time')
        group_dic = {}
        classes_dic = {}
        for item in group:
            day = item['start_time__day']
            if group_dic.get(day):
                group_dic[day].append(item['group__global_name'])
            else:
                group_dic[day] = [item['group__global_name']]
            if classes_dic.get(day):
                classes_dic[day].append(item['classes__global_name'])
            else:
                classes_dic[day] = [item['classes__global_name']]
        group_list, classes_list = list(group_dic.values()), list(classes_dic.values())


        # 添加标题
        # sheet.write_merge(开始行, 结束行, 开始列, 结束列, 'My merge', style)
        sheet.write_merge(0, 2, 0, 0, '机台', style)
        sheet.write_merge(0, 0, 1, 1, '日期', style)
        sheet.write_merge(1, 1, 1, 1, '班次', style)
        sheet.write_merge(2, 2, 1, 1, '班别', style)
        for i in range(len(group_list)):
            sheet.write_merge(0, 0, 2 * (i + 1), 2 * (i + 1) + 1, f'{i+1}日', style)
            sheet.write_merge(1, 1, 2 * (i + 1), 2 * (i + 1), group_list[i][0], style)
            sheet.write_merge(1, 1, 2 * (i + 1) + 1, 2 * (i + 1) + 1, group_list[i][1], style)

            sheet.write_merge(2, 2, 2 * (i + 1), 2 * (i + 1), classes_list[i][0], style)
            sheet.write_merge(2, 2, 2 * (i + 1) + 1, 2 * (i + 1) + 1, classes_list[i][1], style)

        # index = 2
        # for i in equip_list:
        #     sheet.write_merge(index, index, 0, 0, i['equip_no'], style)
        #     for section in section_list:
        #         if i['equip_no'].startswith('Z') and section['type'] == '密炼':
        #             sheet.write_merge(index, index, 1, 1, section['name'], style)
        #             index += 1
        #         if i['equip_no'].startswith('S') and section['type'] == '硫磺称量':
        #             sheet.write_merge(index, index, 1, 1, section['name'], style)
        #             index += 1
        #         if i['equip_no'].startswith('F') and section['type'] == '细料称量':
        #             sheet.write_merge(index, index, 1, 1, section['name'], style)
        #             index += 1

                # 从几个开始 （）
            # index = (list(equip_list).index(i) + 1) * 4      :  4,  8, 12
            # sheet.write_merge(index - 2, index - 2, 0, 0, i['equip_no'] + f"({dic.get(i['equip_no'], '')})", style)
            # sheet.write_merge(index - 2, index - 2, 0, 0, i['equip_no'], style)
            # sheet.write_merge(index - 2, index - 2, 1, 1, '主投', style)
            # sheet.write_merge(index - 1, index - 1, 1, 1, '辅投', style)
            # sheet.write_merge(index, index, 1, 1, '挤出', style)
            # sheet.write_merge(index + 1, index + 1, 1, 1, '收皮', style)

        # 写出到IO
        output = BytesIO()
        wb.save(output)
        # 重新定位到开始
        output.seek(0)
        response.write(output.getvalue())
        return response


@method_decorator([api_recorder], name="dispatch")
class PerformanceJobLadderViewSet(ModelViewSet):
    queryset = PerformanceJobLadder.objects.filter(delete_flag=False).order_by('code')
    serializer_class = PerformanceJobLadderSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = PerformanceJobLadderFilter

    def list(self, request, *args, **kwargs):
        if self.request.query_params.get('all'):
            res = PerformanceJobLadder.objects.filter(delete_flag=False).values('id', 'type', 'name')
            return Response({'results': res})
        return super().list(request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class PerformanceUnitPriceView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        results = {}
        state_lst = GlobalCode.objects.filter(global_type__type_name='胶料段次').values('global_name')
        # category_lst = EquipCategoryAttribute.objects.filter(delete_flag=False).values('category_no')
        category_lst = ['E580', 'F370', 'GK320', 'GK255', 'GK400', 'fz']

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
        category_lst = ['E580', 'F370', 'GK320', 'GK255', 'GK400', 'fz']
        for item in data:
            for category in category_lst:
                pt = item[f"{category}_pt"]
                dj = item[f"{category}_dj"]
                PerformanceUnitPrice.objects.update_or_create(defaults={'state': item['state'],
                                                                        'equip_type': category,
                                                                        'pt': pt,
                                                                        'dj': dj}, state=item['state'], equip_type=category)

        return Response('添加成功')


@method_decorator([api_recorder], name="dispatch")
class ProductInfoDingJiViewSet(ModelViewSet):
    queryset = ProductInfoDingJi.objects.filter(delete_flag=False)
    serializer_class = ProductInfoDingJiSerializer
    permission_classes = (IsAuthenticated,)
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
    permission_classes = (IsAuthenticated,)

    def get_equip_max_value(self):
        max_value = {}
        now_date = datetime.date.today() - datetime.timedelta(days=1)
        equip_value_cache = EquipMaxValueCache.objects.all()
        if equip_value_cache.exists():
            date = equip_value_cache.last().date_time
            query = equip_value_cache.values('equip_no', 'value')
            for item in query:
                max_value[item['equip_no']] = item['value']
            equip_max_value = TrainsFeedbacks.objects.filter(Q(factory_date__gte=date, factory_date__lte=now_date) &
                                                      Q(Q(~Q(equip_no='Z04')) | Q(equip_no='Z04', operation_user='Mixer1'))).\
                values('equip_no', 'factory_date', 'classes').annotate(qty=Count('id')).order_by('-qty')
        else:
            equip_max_value = TrainsFeedbacks.objects.values('equip_no', 'factory_date', 'classes').annotate(
                qty=Count('id')).order_by('-qty')

        for item in equip_max_value:
            if not max_value.get(f"{item['equip_no']}"):
                max_value[item['equip_no']] = item['qty']
            else:
                if max_value[item['equip_no']] < item['qty']:
                    max_value[item['equip_no']] = item['qty']
        for key, value in max_value.items():
            EquipMaxValueCache.objects.update_or_create(defaults={'equip_no': key,
                                                                  'value': value,
                                                                  'date_time': now_date
                                                                  }, equip_no=key)
        return max_value

    def get(self, request):
        date = self.request.query_params.get('date')
        name_d = self.request.query_params.get('name_d')
        day_d = self.request.query_params.get('day_d')
        group_d = self.request.query_params.get('group_d')
        ccjl = self.request.query_params.get('ccjl')
        year = int(date.split('-')[0])
        month = int(date.split('-')[1])
        state_list = GlobalCode.objects.filter(global_type__type_name='胶料段次').values_list('global_name', flat=True)
        # 员工独立上岗系数
        coefficient = GlobalCode.objects.filter(global_type__type_name='是否独立上岗系数').values('global_no', 'global_name')
        coefficient_dic = {dic['global_no']: dic['global_name'] for dic in coefficient}
        # 员工类别
        employee_type = GlobalCode.objects.filter(global_type__type_name='员工类别').values('global_no', 'global_name')
        employee_type_dic = {dic['global_no']: dic['global_name'] for dic in employee_type}
        # 超产奖励系数
        coefficient1 = GlobalCode.objects.filter(global_type__type_name='超产单价').values('global_no', 'global_name')
        coefficient1_dic = {dic['global_no']: dic['global_name'] for dic in coefficient1}
        if not coefficient or not coefficient1:
            raise ValidationError('请先去添加独立上岗或超产奖励系数')
        # 员工考勤记录 (考勤记录)
        section_list = PerformanceJobLadder.objects.filter(delete_flag=False, type='密炼').values_list('name', flat=True)
        kwargs = {
            'factory_date__year': year,
            'factory_date__month': month,
            'section__in': section_list
        }
        kwargs2 = {
            'factory_date__year': year,
            'factory_date__month': month,
        }
        if name_d:
            # user = User.objects.filter(username=name_d).first()
            kwargs['user__username__icontains'] = name_d
        if day_d:
            kwargs['factory_date__day'] = day_d
            kwargs2['factory_date__day'] = day_d
        user_query = EmployeeAttendanceRecords.objects.filter(Q(**kwargs) & ~Q(is_use='废弃') &
                                                             Q(Q(end_date__isnull=False, begin_date__isnull=False) |
                                                               Q(end_date__isnull=True, begin_date__isnull=True)))
        queryset = user_query.values_list('user__username', 'section', 'factory_date__day', 'group', 'equip', 'actual_time', 'classes')
        user_dic = {}
        equip_shut_down_dic = {}
        equip_shut_down = SchedulingEquipShutDownPlan.objects.filter(begin_time__year=year, begin_time__month=month).values(
            'begin_time__day', 'equip_no')
        for item in equip_shut_down:
            if equip_shut_down_dic.get(item['begin_time__day']):
                equip_shut_down_dic[item['begin_time__day']].append(item['equip_no'])
            else:
                equip_shut_down_dic[item['begin_time__day']] = [item['equip_no']]
        for item in queryset:
            if not item[4]:  # 机台为空，按照15个机台的平均值计算， 去除故障停机的机台
                e_list = Equip.objects.filter(category__equip_type__global_name='密炼设备').values_list('equip_no', flat=True)
                move_equip = equip_shut_down_dic.get(int(item[2]), [])
                if move_equip and len(e_list) > len(move_equip):
                    e_list = list(set(e_list).difference(set(move_equip)))
            else:
                e_list = [item[4]]
            for equip in e_list:
                key = f"{item[2]}_{item[3]}_{item[1]}_{equip}_{item[6]}"  # 1_A班_挤出_Z01_早班
                user_dic[key] = {'name': item[0], 'section': item[1], 'day': item[2], 'group': item[3], 'equip': equip, 'actual_time': item[5], 'classes': item[6]}
        group = WorkSchedulePlan.objects.filter(start_time__year=year,
                                                start_time__month=month).values_list('group__global_name', 'classes__global_name', 'start_time__day').order_by('start_time')
        group_list = []
        for key, g in groupby(list(group), key=lambda x: x[2]):
            group_list.append([item[0] for item in g])

        # 密炼的产量
        queryset = TrainsFeedbacks.objects.filter(Q(~Q(equip_no='Z04')) | Q(equip_no='Z04', operation_user='Mixer1'))
        product_qty = list(queryset.filter(**kwargs2
                                                     ).values('classes', 'equip_no', 'factory_date__day', 'product_no').\
            annotate(actual_trains=Count('id')).values('actual_trains', 'classes', 'equip_no', 'factory_date__day', 'product_no'))
        # 人工录入产量
        add_qty = ManualInputTrains.objects.filter(**kwargs2).values('actual_trains', 'classes', 'equip_no', 'factory_date__day', 'product_no')
        product_qty = product_qty | add_qty
        price_dic = {}
        price_list = PerformanceUnitPrice.objects.values('equip_type', 'state', 'pt', 'dj')
        for item in price_list:
            price_dic[f"{item['equip_type']}_{item['state']}"] = {'pt': item['pt'], 'dj': item['dj']}
        equip_dic = {}
        equip_list = Equip.objects.filter(category__equip_type__global_name='密炼设备').values('category__category_no', 'equip_no')
        for item in equip_list:
            equip_dic[item['equip_no']] = item['category__category_no']
        dj_list = ProductInfoDingJi.objects.filter(is_use=True).values_list('product_name', flat=True)
        for key in user_dic.keys():
            day, group, section, equip, classes = key.split('_')
            for item in product_qty:
                if item['equip_no'] == equip and str(item['factory_date__day']) == day and classes == item['classes']:
                    equip_type = equip_dic.get(equip)
                    try:
                        state = item['product_no'].split('-')[1]
                        if state in ['XCJ', 'DJXCJ']:
                            if item['product_no'].split('-')[0] == 'FM':
                                state = 'RFM'
                            elif item['product_no'].split('-')[0] == 'WL':
                                state = 'RMB'
                            else: continue
                    except: continue
                    if not price_dic.get(f"{equip_type}_{state}"):
                        PerformanceUnitPrice.objects.create(state=state, equip_type=equip_type, dj=1.2, pt=1.1)
                        price_dic[f"{equip_type}_{state}"] = {'pt': 1.2, 'dj': 1.1}
                    # 判断是否是丁基胶
                    if item['product_no'] in dj_list:
                        # 根据工作时长求机台的产量
                        work_time = user_dic[key]['actual_time']
                        if '叉车' in section:
                            unit = price_dic.get(f"fz_{state}").get('dj')
                        else:
                            unit = price_dic.get(f"{equip_type}_{state}").get('dj')
                        user_dic[key][f"{state}_dj_qty"] = user_dic[key].get(f"{state}_dj_qty", 0) + int(
                            item['qty'] / 12 * work_time)
                        user_dic[key][f"{state}_dj_unit"] = unit
                    else:
                        work_time = user_dic[key]['actual_time']
                        if '叉车' in section:
                            unit = price_dic.get(f"fz_{state}").get('pt')
                        else:
                            unit = price_dic.get(f"{equip_type}_{state}").get('pt')
                        user_dic[key][f"{state}_pt_qty"] = user_dic[key].get(f"{state}_pt_qty", 0) + int(
                            item['qty'] / 12 * work_time)
                        user_dic[key][f"{state}_pt_unit"] = unit
        results1 = {}
        # 是否独立上岗
        independent = {}
        independent_lst = IndependentPostTemplate.objects.filter(date_time=date).values('name', 'status', 'work_type')
        for item in independent_lst:
            independent[item['name']] = {'status': item['status'], 'work_type': item['work_type']}
        # 取机台历史最大值
        max_value = self.get_equip_max_value()
        # 取每个机台设定的目标值
        settings_value = MachineTargetYieldSettings.objects.filter(input_datetime__year=year,
                                                                   input_datetime__month=month).last()
        if not settings_value:
            settings_value = MachineTargetYieldSettings.objects.last()
        # 计算薪资
        section_info = {}
        for item in PerformanceJobLadder.objects.filter(type='密炼').values('name', 'coefficient', 'post_standard', 'post_coefficient', 'type'):
            section_info[item['name']] = {'coefficient': item['coefficient'],
                                          'post_standard': item['post_standard'],
                                          'post_coefficient': item['post_coefficient'],
                                          'type': item['type']}
        for k, v in user_dic.items():
            name, day, group, section = v['name'], v['day'], v['group'], v['section']
            key = f"{name}_{day}_{group}_{section}"  # 合并岗位
            if results1.get(key):
                results1[key].append(v)
            else:
                results1[key] = [v]
        # 绩效详情
        if day_d and group_d:
            start_with = f"{name_d}_{day_d}_{group_d}"
            results1 = {k: v for k, v in results1.items() if k.startswith(start_with)}
            ccjl_dic = {}
            results = {}
            results_sort = {}
            equip_qty = {}
            equip_price = {}
            hj = {'name': '产量工资合计', 'price': 0}
            for item in results1.values():
                for dic in item:
                    section, equip = dic['section'], dic['equip']
                    if len(dic) == 7:
                        continue
                    for k in dic.keys():
                        if k.split('_')[-1] == 'qty':
                            state = k.split('_')[0]
                            type1 = k.split('_')[1]
                            qty = dic.get(f"{state}_{type1}_qty")  # 数量
                            unit = dic.get(f"{state}_{type1}_unit")  # 单价
                            equip_qty[f'{equip}_{section}'] = equip_qty.get(f'{equip}_{section}', 0) + qty
                            equip_price[f'{equip}_{section}'] = equip_price.get(f'{equip}_{section}', 0) + round(qty * unit, 2)
                            hj[state] = round(hj.get(state, 0) + qty * unit, 2)
                            hj['price'] += round(qty * unit, 2)
                            type2 = '普通' if type1 == 'pt' else '丁基'
                            if results.get(f"{equip}_{type2}_{section}_1"):
                                results[f"{equip}_{type2}_{section}_1"].update({state: dic[k]})
                                results[f"{equip}_{type2}_{section}_2"].update({state: dic[f"{state}_{type1}_unit"]})
                                results[f"{equip}_{type2}_{section}_3"].update({state: section})
                            else:
                                results[f"{equip}_{type2}_{section}_1"] = {'name': f"{equip}{type2}-车数", state: dic[k]}
                                results[f"{equip}_{type2}_{section}_2"] = {'name': f"{equip}{type2}-单价", state: dic[f"{state}_{type1}_unit"]}
                                results[f"{equip}_{type2}_{section}_3"] = {'name': f"{equip}{type2}-岗位", state: section}

            for i in sorted(results):
                results_sort[i] = results.pop(i)
            # 是否定岗
            a = float(coefficient_dic.get('是'))
            if independent.get(name_d, 1) == False:
                a = float(coefficient_dic.get('否'))
            coefficient = section_info[section]['coefficient'] / 100
            post_coefficient = section_info[section]['post_coefficient'] / 100
            post_standard = section_info[section]['post_standard']  # 1最大值 2 平均值
            # 计算超产奖励
            for equip_section, qty in equip_qty.items():
                equip, section = equip_section.split('_')
                coefficient = section_info[section]['coefficient'] / 100
                post_coefficient = section_info[section]['post_coefficient'] / 100
                post_standard = section_info[section]['post_standard']  # 1最大值 2 平均值
                price = 0
                if max_value.get(equip) and settings_value.__dict__.get(equip):
                    m = max_value.get(equip)
                    s = settings_value.__dict__.get(equip)
                    if qty < s:
                        price = 0
                    elif qty > m:
                        price = (m - s) * float(coefficient1_dic.get('超过目标产量部分')) + (qty - m) * float(
                            coefficient1_dic.get('超过最高值部分'))
                    elif qty < m and qty > s:
                        price = (qty - s) * float(coefficient1_dic.get('超过目标产量部分'))
                    ccjl_dic[equip] = price
            post_coefficient = post_coefficient if len(list(results1.values())[0]) > 1 else 1

            if section in ['班长', '机动']:
                hj['ccjl'] = round(sum(ccjl_dic.values()) * 0.15, 2) if ccjl_dic.values() else 0
            elif section in ['三楼粉料', '吊料', '出库叉车', '叉车', '一楼叉车', '密炼叉车', '二楼出库']:
                hj['ccjl'] = round(sum(ccjl_dic.values()) * 0.2 * coefficient, 2) if ccjl_dic.values() else 0
            else:
                if post_standard == 1:  # 最大值
                    hj['ccjl'] = round(max(ccjl_dic.values()), 2) if ccjl_dic.values() else 0
                else:
                    hj['ccjl'] = round(sum(ccjl_dic.values()) / (len(results_sort) // 3), 2) if ccjl_dic.values() else 0
            if post_standard == 1:
                hj['price'] = round(int(max(equip_price.values())) * post_coefficient * coefficient * a, 2) if equip_price.values() else 0
            else:
                hj['price'] = round(hj['price'] / (len(results_sort) // 3) * post_coefficient * coefficient * a, 2) if equip_price.values() else 0

            return Response({'results': results_sort.values(), 'hj': hj, 'all_price': hj['price'], '超产奖励': hj['ccjl'], 'group_list': group_list})

        results = {}
        ccjl_dic = {}
        equip_qty = {}
        equip_price = {}
        for item in list(results1.values()):
            if len(item) > 1:
                section, name = item[0].get('section'), item[0].get('name')
                a = float(coefficient_dic.get('是'))
                aa = '是'
                if independent.get(name, 1) == False:
                    a = float(coefficient_dic.get('否'))
                    aa = '否'
                coefficient = section_info[section]['coefficient'] / 100
                post_coefficient = section_info[section]['post_coefficient'] / 100
                post_standard = section_info[section]['post_standard']  # 1最大值 2 平均值
                for dic in item:
                    section, name, day, group, equip = dic.get('section'), dic.get('name'), dic.get('day'), dic.get(
                        'group'), dic.get('equip')
                    for k in dic.keys():
                        if k.split('_')[-1] == 'qty':
                            state = k.split('_')[0]
                            type1 = k.split('_')[1]
                            qty = dic.get(f"{state}_{type1}_qty")  # 数量
                            unit = dic.get(f"{state}_{type1}_unit")  # 单价
                            # 统计车数
                            key = f"{name}_{day}"
                            if equip_qty.get(key):
                                equip_qty[key][equip] = equip_qty[key].get(equip, 0) + qty
                            else:
                                equip_qty[key] = {equip: qty}
                            if equip_price.get(key):
                                equip_price[key][equip] = equip_price[key].get(equip, 0) + qty * unit
                            else:
                                equip_price[key] = {equip: qty * unit}
                # 计算薪资
                if not equip_price.get(f"{name}_{day}"):
                    price = 0
                else:
                    if post_standard == 1:  # 最大值
                        price = max(equip_price.get(f"{name}_{day}").values())
                    else:  # 平均值
                        price = round(
                            sum(equip_price.get(f"{name}_{day}").values()) / len(equip_price.get(f"{name}_{day}")), 2)
                    price = round(price * coefficient * a * post_coefficient, 2)
                if results.get(name):
                    results[name][f"{day}_{group}"] = results[name].get(f"{day}_{group}", 0) + price
                    results[name]['hj'] += price
                    results[name]['all'] += price
                else:
                    results[name] = {'name': name, '超产奖励': 0, '是否定岗': aa, 'hj': price, 'all': price,
                                     f"{day}_{group}": price}
            else:
                dic = item[0]
                section, name, day, group, equip = dic.get('section'), dic.get('name'), dic.get('day'), dic.get(
                    'group'), dic.get('equip')
                coefficient = section_info[section]['coefficient'] / 100
                post_coefficient = 1
                a = float(coefficient_dic.get('是'))
                aa = '是'
                if independent.get(name, 1) == False:
                    a = float(coefficient_dic.get('否'))
                    aa = '否'
                for k in dic.keys():
                    if k.split('_')[-1] == 'qty':
                        state = k.split('_')[0]
                        type1 = k.split('_')[1]
                        qty = dic.get(f"{state}_{type1}_qty")  # 数量
                        unit = dic.get(f"{state}_{type1}_unit")  # 单价
                        # 统计车数
                        key = f"{name}_{day}"
                        if equip_qty.get(key):
                            equip_qty[key][equip] = equip_qty[key].get(equip, 0) + qty
                        else:
                            equip_qty[key] = {equip: qty}
                        if equip_price.get(key):
                            equip_price[key][equip] = equip_price[key].get(equip, 0) + qty * unit
                        else:
                            equip_price[key] = {equip: qty * unit}
                # 计算薪资
                if equip_price.get(f"{name}_{day}"):
                    price = max(equip_price.get(f"{name}_{day}").values())
                    price = round(price * coefficient * a * post_coefficient, 2)
                else:
                    price = 0
                if results.get(name):
                    results[name][f"{day}_{group}"] = round(results[name].get(f"{day}_{group}", 0) + price, 2)
                    results[name]['hj'] = round(results[name]['hj'] + price, 2)
                    results[name]['all'] = round(results[name]['all'] + price, 2)
                else:
                    results[name] = {'name': name, '超产奖励': 0, '是否定岗': aa, 'hj': price, 'all': price,
                                     f"{day}_{group}": price}
        # 计算超产奖励
        for key, dic in equip_qty.items():
            price = 0
            name, day = key.split('_')
            section = EmployeeAttendanceRecords.objects.filter(user__username=name).first().section
            post_standard = section_info[section]['post_standard']
            coefficient = section_info[section]['coefficient'] / 100
            p_dic = {}
            for equip, qty in dic.items():
                if max_value.get(equip) and settings_value.__dict__.get(equip):
                    m = max_value.get(equip)
                    s = settings_value.__dict__.get(equip)
                    if qty < s:
                        price = 0
                    elif qty > m:
                        price = (m - s) * float(coefficient1_dic.get('超过目标产量部分')) + (qty - m) * float(
                            coefficient1_dic.get('超过最高值部分'))
                    elif qty < m and qty > s:
                        price = (qty - s) * float(coefficient1_dic.get('超过目标产量部分'))
                    p_dic[equip] = price
            if section in ['班长', '机动']:
                p = round(sum(p_dic.values()) * 0.15, 2) if p_dic.values() else 0
            elif section in ['三楼粉料', '吊料', '出库叉车', '叉车', '一楼叉车', '密炼叉车', '二楼出库']:
                p = round(sum(p_dic.values()) * 0.2 * coefficient, 2) if p_dic.values() else 0
            else:
                if len(dic.values()) > 1:
                    if post_standard == 1:
                        p = max(p_dic.values()) if p_dic.values() else 0
                    else:
                        p = round(sum(p_dic.values()) / len(dic.values()), 2) if p_dic.values() else 0
                else:
                    p = max(p_dic.values()) if p_dic.values() else 0
            results[name]['超产奖励'] += p
            results[name]['all'] = round(results[name]['all'] + p, 2)
            if p > 0:
                if ccjl_dic.get(name):
                    ccjl_dic[name].append({'date': f"{year}-{month}-{day}", 'price': p})
                else:
                    ccjl_dic[name] = [{'date': f"{year}-{month}-{day}", 'price': p}]
        if ccjl:  # 超产奖励详情
            return Response({'results': ccjl_dic.get(name_d, None)})
        for item in list(results.values()):
            if independent.get(item['name']):
                work_type = independent[item['name']].get('work_type')
            else:
                work_type = '正常'
            v = float(employee_type_dic.get(work_type, 1))
            item['work_type'] = work_type
            item['all'] = round(item['all'] * v, 2)
        return Response({'results': results.values(), 'group_list': group_list})


@method_decorator([api_recorder], name="dispatch")
class PerformanceSubsidyViewSet(ModelViewSet):
    queryset = SubsidyInfo.objects.order_by('id')
    serializer_class = SubsidyInfoSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = SubsidyInfoFilter
    pagination_class = None

    @atomic
    def create(self, request, *args, **kwargs):
        for data in request.data:
            price = data.get('price') if data.get('price') else 0
            desc = data.get('desc') if data.get('desc') else None
            if data.get('id'):
                SubsidyInfo.objects.filter(id=data.get('id')).update(price=price, desc=desc)
            else:
                serializer = SubsidyInfoSerializer(data=data)
                serializer.is_valid(raise_exception=True)
                serializer.save()
        return Response(status=status.HTTP_200_OK)


@method_decorator([api_recorder], name="dispatch")
class IndependentPostTemplateView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        date = self.request.query_params.get('date')
        export = self.request.query_params.get('export')
        year = int(date.split('-')[0])
        month = int(date.split('-')[1])
        # 导出是否独立上岗模版

        if export:
            names = EmployeeAttendanceRecords.objects.filter(factory_date__year=year, factory_date__month=month).values_list('user__username', flat=True).distinct()
            if names:
                data = [{'name': name, 'work_type': '正常', 'state': '是'} for name in list(names)]
                return gen_template_response({'姓名': 'name', '员工类别': 'work_type', '是否独立上岗': 'state'}, data, '是否独立上岗模版')
            raise ValidationError('当月没有考勤记录')
        return Response()

    @atomic
    def post(self, request):
        date = self.request.data.get('date')
        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        rows = cur_sheet.nrows
        lst = []
        for i in range(1, rows):
            name = cur_sheet.cell(i, 0).value
            work_type = cur_sheet.cell(i, 1).value
            value = cur_sheet.cell(i, 2).value
            if value == '是':
                status = 1
            elif value == '否':
                status = 0
            else:
                raise ValidationError('导入的格式有误')

            if IndependentPostTemplate.objects.filter(date_time=date, name=name).exists():
                IndependentPostTemplate.objects.filter(date_time=date, name=name).update(status=status, work_type=work_type)
            else:
                lst.append(IndependentPostTemplate(name=name, status=status, date_time=date, work_type=work_type))
        IndependentPostTemplate.objects.bulk_create(lst)
        return Response(f'导入成功')


@method_decorator([api_recorder], name="dispatch")
class AttendanceGroupSetupViewSet(ModelViewSet):
    queryset = AttendanceGroupSetup.objects.all()
    serializer_class = AttendanceGroupSetupSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = AttendanceGroupSetupFilter
    option = True

    def get_section(self, section_name, section_id=None):  # 判断用户是不是设备科或生产科的成员
        if not self.option:
            return True
        if section_id:
            if Section.objects.filter(pk=section_id, name=section_name).exists():
                self.option = False
                return True
            a = Section.objects.filter(pk=section_id).first()
            if a:
                parent_id = a.parent_section_id
                self.get_section(section_name, parent_id)
        else:
            return False

    @action(methods=['get'], detail=False, permission_classes=[], url_path='in_group', url_name='in_group')
    def in_group(self, request):  # 判断用户是否在考勤组
        name = self.request.user.username
        res = AttendanceGroupSetup.objects.filter(Q(attendance_users__icontains=name) | Q(principal__icontains=name)).exists()
        return Response({'status': res})

    @action(methods=['get'], detail=False, permission_classes=[], url_path='is_section', url_name='is_section')
    def is_section(self, request):  # 判断用户是否是设备科门或生产科
        section_id = self.request.user.section_id
        for section in ['设备科', '生产科']:
            self.option = True
            self.get_section(section, section_id)
            if not self.option:
                return Response({'section': section})
        return Response({'section': None})


@method_decorator([api_recorder], name="dispatch")
class AttendanceClockViewSet(ModelViewSet):
    queryset = EmployeeAttendanceRecords.objects.all()
    serializer_class = EmployeeAttendanceRecordsSerializer
    permission_classes = (IsAuthenticated,)

    def save_attendance_clock_detail(self, name, equip_list, data):
        AttendanceClockDetail.objects.create(
            name=name,
            equip=','.join(equip_list),
            group=data.get('group'),
            classes=data.get('classes'),
            section=data.get('section'),
            work_type=data.get('status')
        )

    def send_message(self, user, content):
        phone = user.phone_number
        ding_api = DinDinAPI()
        ding_uid = ding_api.get_user_id(phone)
        ding_api.send_message([ding_uid], content)

    def get_user_group(self, user_obj, now=None):
        username =user_obj.username
        # 获取登陆用户所在考勤组
        attendance_group_obj = AttendanceGroupSetup.objects.filter(Q(attendance_users__icontains=username) | Q(principal=username)).first()
        if not attendance_group_obj:
            raise ValidationError('当前用户未添加至考勤组')
        group_type = attendance_group_obj.type   # 密炼/细料称量/硫磺称量
        if group_type == '密炼':
            equip_type = '密炼设备'
            equip_list = Equip.objects.filter(category__equip_type__global_name=equip_type).values_list('equip_no', flat=True)
        else:
            equip_type = '称量设备'
            if group_type == '细料称量':
                startswith = 'F'
            else:
                startswith = 'S'
            equip_list = Equip.objects.filter(category__equip_type__global_name=equip_type,
                                              equip_no__startswith=startswith).values_list('equip_no',  flat=True)
        section_list = PerformanceJobLadder.objects.filter(type=group_type).values_list('name', flat=True)

        # 获取当前时间的工厂日期
        now = now if now else datetime.datetime.now()
        current_work_schedule_plan = WorkSchedulePlan.objects.filter(
            start_time__lte=now,
            end_time__gte=now,
            plan_schedule__work_schedule__work_procedure__global_name='密炼'
        ).first()
        if current_work_schedule_plan:
            date_now = str(current_work_schedule_plan.plan_schedule.day_time)
        else:
            date_now = str(now.date())
        # 获取班次班组
        queryset = WorkSchedulePlan.objects.filter(plan_schedule__day_time=date_now).values('group__global_name',
                                                                                     'classes__global_name')
        group_list = [{'group': item['group__global_name'], 'classes': item['classes__global_name']} for item in queryset]
        return attendance_group_obj, list(section_list), list(equip_list), date_now, group_list

    def list(self, request, *args, **kwargs):
        username = self.request.user.username
        id_card_num = self.request.user.id_card_num
        apply = self.request.query_params.get('apply', None)
        time_now = datetime.datetime.now()
        attendance_group_obj, section_list, equip_list, date_now, group_list = self.get_user_group(self.request.user)
        equip_list.sort()
        results = {
            # 'ids': ids,  # 进行中的id，前端打卡传这个过来
            'username': username,
            'id_card_num': id_card_num,
            'group_list': group_list,
            'equip_list': equip_list,
            'section_list': section_list,
            'principal': attendance_group_obj.principal,  # 前端根据这个判断是否显示审批
        }
        if apply:  # 补卡/加班
            return Response({'results': results})

        # 判断最后一条的工厂时间是不是当天，是的话说明是正在进行中的
        last_obj = EmployeeAttendanceRecords.objects.filter(user=self.request.user).last()
        if last_obj:
            flat = False
            report = EmployeeAttendanceRecords.objects.filter(begin_date=last_obj.begin_date,
                                                              user_id=last_obj.user_id).values_list('equip', 'id')
            ids, equips = [item[1] for item in report], [item[0] for item in report]
            results['equips'] = equips

            if str(last_obj.factory_date) == date_now:
                date_now = datetime.datetime.strptime(date_now, '%Y-%m-%d')
                if attendance_group_obj.attendance_et.hour > 12:  # 白班
                    if time_now < date_now + datetime.timedelta(days=1, hours=2):  # 直到明天凌晨两点，显示当前的打卡记录
                        results['state'] = 3  # 进行中的
                        results['ids'] = ids
                        results['begin_date'] = datetime.datetime.strftime(last_obj.begin_date, '%H:%M:%S') if last_obj.begin_date else None
                        results['end_date'] = datetime.datetime.strftime(last_obj.end_date, '%H:%M:%S') if last_obj.end_date else None
                        results['section_list'].remove(last_obj.section)
                        results['section_list'].insert(0, last_obj.section)  # 放到第一位显示
                        group, classes = last_obj.group, last_obj.classes
                        results['group_list'].remove({'group': group, 'classes': classes})
                        results['group_list'].insert(0, {'group': group, 'classes': classes})
                    else:
                        flat = True
                else:  # 夜班
                    if time_now < date_now + datetime.timedelta(days=1, hours=14):
                        results['state'] = 3
                        results['ids'] = ids
                        results['begin_date'] = datetime.datetime.strftime(last_obj.begin_date, '%H:%M:%S') if last_obj.begin_date else None
                        results['end_date'] = datetime.datetime.strftime(last_obj.end_date, '%H:%M:%S') if last_obj.end_date else None
                        results['section_list'].remove(last_obj.section)
                        results['section_list'].insert(0, last_obj.section)  # 放到第一位显示
                        group, classes = last_obj.group, last_obj.classes
                        results['group_list'].remove({'group': group, 'classes': classes})
                        results['group_list'].insert(0, {'group': group, 'classes': classes})
                    else:
                        flat = True
            else:
                flat = True
            if flat:
                # 默认返回前一条的打卡记录，默认显示
                results['state'] = 2  # 默认显示
                results['section_list'].remove(last_obj.section)
                results['section_list'].insert(0, last_obj.section)  # 放到第一位显示
                group, classes = last_obj.group, last_obj.classes
                results['group_list'].remove({'group': group, 'classes': classes})
                results['group_list'].insert(0, {'group': group, 'classes': classes})
        else:
            results['state'] = 1  # 没有打卡记录
        return Response(results)

    @atomic
    def create(self, request, *args, **kwargs):
        user = self.request.user
        data = self.request.data  # {classes group equip_list ids section status}
        attendance_group_obj, section_list, equip_list, date_now, group_list = self.get_user_group(user)
        time_now = datetime.datetime.now()
        ids = data.pop('ids', None)
        equip_list = data.pop('equip_list', None)
        status = data.get('status')
        results = {
            'ids': [],
        }
        if status == '上岗':
            begin_date = time_now
            attendance_st = datetime.datetime.strptime(f"{date_now} {str(attendance_group_obj.attendance_st)}", '%Y-%m-%d %H:%M:%S')
            lead_time = datetime.timedelta(minutes=attendance_group_obj.lead_time)
            if time_now < attendance_st - lead_time:
                raise ValidationError('未到可打卡时间')
            # 本次上岗打卡操作自动补上上次离岗打卡
            last_date = datetime.datetime.strptime(date_now, '%Y-%m-%d') - datetime.timedelta(days=1)
            last_date = datetime.datetime.strftime(last_date, '%Y-%m-%d')
            if attendance_group_obj.attendance_et.hour > 12:  # 白班
                end_date = f"{str(last_date)} {str(attendance_group_obj.attendance_et)}"
            else:
                end_date = f"{str(date_now)} {str(attendance_group_obj.attendance_et)}"
            EmployeeAttendanceRecords.objects.filter(
                user=user,
                end_date__isnull=True,
                factory_date=last_date
            ).update(end_date=end_date)
            for equip in equip_list:
                obj = EmployeeAttendanceRecords.objects.create(
                    user=user,
                    equip=equip,
                    begin_date=begin_date,
                    factory_date=date_now,
                    **data
                )
                results['ids'].append(obj.id)
        elif status == '下岗':  # 可重复打卡
            attendance_st = datetime.datetime.strptime(f"{date_now} {str(attendance_group_obj.attendance_st)}", '%Y-%m-%d %H:%M:%S')
            range_time = datetime.timedelta(minutes=attendance_group_obj.range_time)
            # if time_now < attendance_st + range_time:
            #     raise ValidationError('未到可打卡时间')
            begin_date = EmployeeAttendanceRecords.objects.filter(id__in=ids).first().begin_date
            if time_now < begin_date + range_time:
                raise ValidationError(f'上班{attendance_group_obj.range_time}分钟内不能打下班卡')
            end_date = time_now
            work_time = round((end_date - begin_date).seconds / 3600, 2)
            EmployeeAttendanceRecords.objects.filter(id__in=ids).update(
                end_date=end_date, work_time=work_time, actual_time=work_time
            )
            results['ids'] = ids
        elif status == '换岗':
            if EmployeeAttendanceRecords.objects.filter(id__in=ids, end_date__isnull=True).exists():
                begin_date = EmployeeAttendanceRecords.objects.filter(id__in=ids).first().begin_date
                end_date = time_now
                work_time = round((end_date - begin_date).seconds / 3600, 2)
                EmployeeAttendanceRecords.objects.filter(id__in=ids).update(
                    end_date=end_date, work_time=work_time, actual_time=work_time
                )
            for equip in equip_list:
                obj = EmployeeAttendanceRecords.objects.create(
                    user=user,
                    equip=equip,
                    begin_date=time_now,
                    factory_date=date_now,
                    **data
                )
                results['ids'].append(obj.id)
        # 记录考勤打卡详情
        self.save_attendance_clock_detail(user.username, equip_list, data)
        return Response({'results': results})

    @action(methods=['post'], detail=False, permission_classes=[], url_path='reissue_card', url_name='reissue_card')
    def reissue_card(self, request):
        data = self.request.data
        user = self.request.user
        username = user.username
        status = data.get('status')
        now_time = datetime.datetime.now()
        bk_date = data.get('bk_date', None)
        now = datetime.datetime.strptime(f'{bk_date}:00', '%Y-%m-%d %H:%M:%S')

        attendance_group_obj, section_list, equip_list, date_now, group_list = self.get_user_group(user, now)
        principal = attendance_group_obj.principal  # 考勤负责人
        # 下岗时间
        equip_list = data.pop('equip_list')
        print(date_now)
        if attendance_group_obj.attendance_et.hour > 12:  # 白班
            attendance_et = datetime.datetime.strptime(f"{date_now} {str(attendance_group_obj.attendance_et)}", '%Y-%m-%d %H:%M:%S')
            factory_date = date_now
        else:  # 夜班
            hours = datetime.datetime.strptime(now_time, '%H:%M:%S')
            if attendance_group_obj.attendance_et < hours < attendance_group_obj.attendance_st:
                factory_date = now_time - datetime.timedelta(days=1)
            else:
                factory_date = date_now
            factory_date1 = str(datetime.datetime.strptime(factory_date, '%Y-%m-%d') + datetime.timedelta(days=1))
            attendance_et = datetime.datetime.strptime(f"{factory_date1} {str(attendance_group_obj.attendance_et)}", '%Y-%m-%d %H:%M:%S')
        if now_time > attendance_et + datetime.timedelta(days=1):
            raise ValidationError('不可提交超过24小时的申请')

        if status == '上岗':
            # 判断是否有打卡记录
            if EmployeeAttendanceRecords.objects.filter(user=user, factory_date=factory_date, status=status).exists():
                raise ValidationError('当天存在上岗打卡记录')
        elif status == '换岗':
            if not EmployeeAttendanceRecords.objects.filter(user=user, factory_date=factory_date,
                                                            status__in=['上岗', '换岗'], end_date__isnull=True).exists():
                raise ValidationError('请先提交当天的上岗申请')
        elif status == '下岗':
            obj = EmployeeAttendanceRecords.objects.filter(
                user=user,
                factory_date=factory_date,
                end_date__isnull=True,
                section=data.get('section'),
                classes=data.get('classes'),
                group=data.get('group'),
                status__in=['上岗', '换岗']
            )
            if not obj:
                raise ValidationError('提交的补卡申请有误')

        # 记录补卡申请记录
        apply = FillCardApply.objects.create(
            user=self.request.user,
            equip=','.join(equip_list),
            apply_date=now_time,
            factory_date=factory_date,
            **data
        )
        # 钉钉提醒
        principal_obj = User.objects.filter(username=principal).first()
        if not principal_obj:
            raise ValidationError('考勤负责人不存在')
        serializer_data = FillCardApplySerializer(apply).data
        content = {
            "title": f"{username}的补卡申请",
            "form": [
                {"key": "姓名:", "value": username},
                {"key": "班组:", "value": apply.group},
                {"key": "班次:", "value": apply.classes},
                {"key": "岗位:", "value": apply.section},
                {"key": "机台:", "value": apply.equip},
                {"key": "补卡时间:", "value": serializer_data.get('bk_date')},
                {"key": "补卡理由:", "value": apply.desc},
            ],
        }
        self.send_message(principal_obj, content)
        return Response('消息发送给审批人')

    @action(methods=['post'], detail=False, permission_classes=[], url_path='overtime', url_name='overtime')
    def overtime(self, request):
        # 加班也存在换岗的情况
        user = self.request.user
        data = self.request.data
        equip_list = data.pop('equip_list', None)
        equip = ','.join(equip_list)
        attendance_group_obj, section_list, equip_list, date_now, group_list = self.get_user_group(user)
        principal = attendance_group_obj.principal  # 考勤负责人
        apply = ApplyForExtraWork.objects.create(
            user=self.request.user,
            equip=equip,
            factory_date=date_now,
            **data
        )
        # 钉钉提醒
        principal_obj = User.objects.filter(username=principal).first()
        if not principal_obj:
            raise ValidationError('考勤负责人不存在')
        serializer_data = ApplyForExtraWorkSerializer(apply).data
        content = {
            "title": f"{user.username}的补卡申请",
            "form": [
                {"key": "姓名:", "value": user.username},
                {"key": "班组:", "value": apply.group},
                {"key": "班次:", "value": apply.classes},
                {"key": "岗位:", "value": apply.section},
                {"key": "机台:", "value": apply.equip},
                {"key": "加班开始时间:", "value": serializer_data.get('begin_date')},
                {"key": "加班结束时间:", "value": serializer_data.get('end_date')},
                {"key": "加班理由:", "value": apply.desc},
            ],
        }
        self.send_message(principal_obj, content)
        return Response('消息发送给审批人')


@method_decorator([api_recorder], name="dispatch")
class ReissueCardView(APIView):
    permission_classes = (IsAuthenticated,)
    queryset = FillCardApply.objects.order_by('-id')
    queryset2 = ApplyForExtraWork.objects.order_by('-id')

    def send_message(self, user, content):
        phone = user.phone_number
        ding_api = DinDinAPI()
        ding_uid = ding_api.get_user_id(phone)
        ding_api.send_message([ding_uid], content)

    def get(self, request):
        # 分页
        page = self.request.query_params.get("page", 1)
        page_size = self.request.query_params.get("page_size", 10)
        state = self.request.query_params.get('state', 0)
        name = self.request.query_params.get('name', None)
        try:
            st = (int(page) - 1) * int(page_size)
            et = int(page) * int(page_size)
        except:
            raise ValidationError("page/page_size异常，请修正后重试")
        group_setup = AttendanceGroupSetup.objects.filter(principal=self.request.user.username).first()
        if self.request.query_params.get('apply'):  # 查看自己的补卡申请
            user_list = [self.request.user.username]
            if group_setup:
                user_list += group_setup.attendance_users.split(',')
            data = self.queryset.filter(user__username__in=user_list).order_by('-id')
            # data2 = self.queryset2.filter(user=self.request.user).order_by('-id')
            data2 = None
        else:  # 审批补卡申请
            attendance_users = group_setup.attendance_users
            principal = group_setup.principal
            attendance_users_list = attendance_users.split(',')
            attendance_users_list.append(principal)
            # 列表中找出和name想象的
            if name:
                attendance_users_list = [user for user in attendance_users_list if name in user]
            data = self.queryset.filter(user__username__in=attendance_users_list)
            data2 = self.queryset2.filter(user__username__in=attendance_users_list)
        serializer = FillCardApplySerializer(data, many=True)
        serializer2 = ApplyForExtraWorkSerializer(data2, many=True)
        res = serializer.data + serializer2.data
        if int(state) == 1:  # 未审批
            res = [item for item in res if item.get('handling_result') == None]
        elif int(state) == 2:
            res = [item for item in res if item.get('handling_result') != None]
        count = len(res)
        results = sorted(list(res), key=lambda x: x['apply_date'])
        return Response({'results': results[st:et], 'count': count})

    @atomic
    def post(self, request):  # 处理补卡申请
        data = self.request.data
        FillCardApply.objects.filter(id=data.get('id')).update(
            handling_suggestion=data.get('handling_suggestion', None),
            handling_result=data.get('handling_result', None)
        )
        obj = FillCardApply.objects.filter(id=data.get('id')).first()
        serializer_data = FillCardApplySerializer(obj).data
        user = obj.user
        content = {
            "title": "补卡申请",
            "form": [
                {"key": "姓名:", "value": user.username},
                {"key": "班组:", "value": serializer_data.get('group')},
                {"key": "班次:", "value": serializer_data.get('classes')},
                {"key": "岗位:", "value": serializer_data.get('section')},
                {"key": "机台:", "value": serializer_data.get('equip')},
                {"key": "补卡时间:", "value": serializer_data.get('bk_date')},
                {"key": "补卡理由:", "value": serializer_data.get('desc')},
                {"key": "处理意见:", "value": serializer_data.get('handling_suggestion')},
                {"key": "处理结果:", "value": serializer_data.get('handling_result')}
            ],
        }
        self.send_message(user, content)
        if data.get('handling_result'):  # 审批通过
            status = obj.status
            equips = serializer_data.get('equip')
            equip_list = equips.split(',')
            if status == '上岗':
                lst = []
                for equip in equip_list:
                    lst.append(
                        EmployeeAttendanceRecords(
                            user=user,
                            section=serializer_data.get('section'),
                            factory_date=serializer_data.get('factory_date'),
                            begin_date=serializer_data.get('bk_date'),
                            classes=serializer_data.get('classes'),
                            group=serializer_data.get('group'),
                            equip=equip,
                            status=status
                        ))
                EmployeeAttendanceRecords.objects.bulk_create(lst)
            elif status == '换岗':
                EmployeeAttendanceRecords.objects.filter(
                    factory_date=serializer_data.get('factory_date'),
                    end_date__isnull=True,
                    status__in=['上岗', '换岗']
                ).update(end_date=serializer_data.get('bk_date'))
                lst = []
                for equip in equip_list:
                    lst.append(
                        EmployeeAttendanceRecords(
                            user=user,
                            section=serializer_data.get('section'),
                            factory_date=serializer_data.get('factory_date'),
                            begin_date=serializer_data.get('bk_date'),
                            classes=serializer_data.get('classes'),
                            group=serializer_data.get('group'),
                            equip=equip,
                            status=status
                        ))
                EmployeeAttendanceRecords.objects.bulk_create(lst)
            elif status == '下岗':
                end_date = obj.bk_date
                dic = {
                    'factory_date': serializer_data.get('factory_date'),
                    'end_date__isnull': True,
                    'section': serializer_data.get('section'),
                    'classes': serializer_data.get('classes'),
                    'group': serializer_data.get('group'),
                    'status__in': ['上岗', '换岗']
                }
                obj = EmployeeAttendanceRecords.objects.filter(**dic).first()
                begin_date = obj.begin_date
                work_time = round((end_date - begin_date).seconds / 3600, 2)
                EmployeeAttendanceRecords.objects.filter(**dic).update(end_date=end_date,
                                                                       work_time=work_time,
                                                                       actual_time=work_time)
        return Response({'results': serializer_data})


@method_decorator([api_recorder], name="dispatch")
class OverTimeView(APIView):
    permission_classes = (IsAuthenticated,)
    queryset = ApplyForExtraWork.objects.order_by('-id')

    def send_message(self, user, content):
        phone = user.phone_number
        ding_api = DinDinAPI()
        ding_uid = ding_api.get_user_id(phone)
        ding_api.send_message([ding_uid], content)

    def get(self, request):
        # 分页
        page = self.request.query_params.get("page", 1)
        page_size = self.request.query_params.get("page_size", 10)
        try:
            st = (int(page) - 1) * int(page_size)
            et = int(page) * int(page_size)
        except:
            raise ValidationError("page/page_size异常，请修正后重试")
        group_setup = AttendanceGroupSetup.objects.filter(principal=self.request.user.username).first()
        if self.request.query_params.get('apply'):  # 查看自己的加班申请
            user_list = [self.request.user.username]
            if group_setup:
                user_list += group_setup.attendance_users.split(',')
            data = self.queryset.filter(user__username__in=user_list).order_by('-id')
        else:  # 审批加班申请
            attendance_users = group_setup.attendance_users
            attendance_users_list = attendance_users.split(',')
            data = self.queryset.filter(user__username__in=attendance_users_list)
        serializer = ApplyForExtraWorkSerializer(data, many=True)
        count = len(serializer.data)
        result = serializer.data[st:et]
        return Response({'results': result, 'count': count})

    @atomic
    def post(self, request):  # 处理加班申请
        data = self.request.data
        ApplyForExtraWork.objects.filter(id=data.get('id')).update(
            handling_suggestion=data.get('handling_suggestion', None),
            handling_result=data.get('handling_result', None)
        )
        obj = ApplyForExtraWork.objects.filter(id=data.get('id')).first()
        serializer_data = ApplyForExtraWorkSerializer(obj).data
        user = obj.user
        date_time = obj.begin_date
        content = {
            "title": "加班申请",
            "form": [
                {"key": "姓名:", "value": user.username},
                {"key": "班组:", "value": serializer_data.get('group')},
                {"key": "班次:", "value": serializer_data.get('classes')},
                {"key": "岗位:", "value": serializer_data.get('section')},
                {"key": "机台:", "value": serializer_data.get('equip')},
                {"key": "加班开始时间:", "value": serializer_data.get('begin_date')},
                {"key": "加班结束时间:", "value": serializer_data.get('end_date')},
                {"key": "加班理由:", "value": serializer_data.get('desc')},
                {"key": "处理意见:", "value": serializer_data.get('handling_suggestion')},
                {"key": "处理结果:", "value": serializer_data.get('handling_result')}
            ],
        }
        self.send_message(user, content)
        if data.get('handling_result'):  # 申请通过
            begin_date = obj.begin_date
            end_date = obj.end_date
            work_time = round((end_date - begin_date).seconds / 3600, 2)
            equips = serializer_data.get('equip')
            for equip in equips.split(','):
                EmployeeAttendanceRecords.objects.create(
                    user=obj.user,
                    section=obj.section,
                    factory_date=serializer_data.get('factory_date'),
                    begin_date=serializer_data.get('begin_date'),
                    end_date=serializer_data.get('end_date'),
                    work_time=work_time,
                    actual_time=work_time,
                    classes=serializer_data.get('classes'),
                    group=serializer_data.get('group'),
                    equip=equip,
                    status='加班'
                )
            # 记录考勤打卡详情
            AttendanceClockDetail.objects.create(
                name=user.username,
                equip=obj.equip,
                group=obj.group,
                classes=obj.classes,
                section=obj.section,
                work_type='加班',
                date=datetime.date(date_time.year, date_time.month, date_time.day),
                date_time=date_time
            )
        return Response({'results': serializer_data})


@method_decorator([api_recorder], name="dispatch")
class AttendanceRecordSearch(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        username = self.request.user.username
        detail = self.request.query_params.get("detail")
        date = self.request.query_params.get('date')
        day = self.request.query_params.get('day')
        year = int(date.split('-')[0])
        month = int(date.split('-')[1])
        queryset = EmployeeAttendanceRecords.objects.filter(
            Q(Q(begin_date__isnull=False, end_date__isnull=False) | Q(begin_date__isnull=True, end_date__isnull=True))
            & ~Q(is_use='废弃') & Q(user=self.request.user)).order_by('id')
        if day:  # 当前的上下班时间
            record = EmployeeAttendanceRecords.objects.filter(
                ~Q(is_use='废弃') & Q(user=self.request.user, factory_date=f"{date}-{day}")).order_by('begin_date')
            group_setup = AttendanceGroupSetup.objects.filter(Q(attendance_users__icontains=username) | Q(principal=username)).first()
            results = {
                'attendance_st': group_setup.attendance_st,
                'attendance_et': group_setup.attendance_et
            }
            if record:
                begin_date = record.first().begin_date
                end_date = record.last().end_date
                all_time = record.filter(Q(Q(begin_date__isnull=False, end_date__isnull=False) |
                                            Q(begin_date__isnull=True, end_date__isnull=True))).\
                    aggregate(Sum('actual_time'))['actual_time__sum']
                if begin_date:
                    work_time = [{'title': f"上班: {datetime.datetime.strftime(begin_date, '%Y-%m-%d %H:%M:%S')}"}]
                else:
                    work_time = []
                if record.filter(status='换岗'):
                    times = record.filter(status='换岗').values_list('begin_date', flat=True).order_by('begin_date')
                    if times:
                        lst = list(set(times))
                        lst.sort()
                        for t in lst:
                            work_time.append({'title': f"换岗: {datetime.datetime.strftime(t, '%Y-%m-%d %H:%M:%S')}"})
                if end_date:
                    work_time.append({'title': f"下班: {datetime.datetime.strftime(end_date, '%Y-%m-%d %H:%M:%S')}"})
                results['work_time'] = round(all_time, 2) if all_time else 0
                results['time'] = work_time
                return Response(results)
            return Response(results)
        # 汇总数据
        results = {
            'days': [],
            'work_times': 0,  # 总工时
            'cd': 0,  # 迟到
            'zt': 0,  # 早退
        }
        for item in queryset.filter(factory_date__year=year, factory_date__month=month):
            day = int(str(item.factory_date).split('-')[-1])
            record = queryset.filter(factory_date=item.factory_date)
            if day not in results.get('days'):
                results['days'].append(day)
                attendance_group_obj = AttendanceGroupSetup.objects.filter(Q(attendance_users__icontains=username) | Q(principal=username)).first()
                begin_date = record.first().begin_date
                end_date = record.last().end_date
                work_time = record.aggregate(Sum('actual_time'))['actual_time__sum']
                results['work_times'] += work_time
                if begin_date and end_date:  # 导入的没有上岗和下岗时间
                    if begin_date > datetime.datetime.strptime(f"{str(item.factory_date)} {str(attendance_group_obj.attendance_st)}", '%Y-%m-%d %H:%M:%S'):
                        results['cd'] += 1
                    if end_date and end_date < datetime.datetime.strptime(f"{str(item.factory_date)} {str(attendance_group_obj.attendance_et)}", '%Y-%m-%d %H:%M:%S'):
                        results['zt'] += 1
        if detail:
            equip_list = queryset.filter(factory_date__year=year, factory_date__month=month
                                         ).values('equip', 'section').annotate(work_times=Sum('actual_time')).values(
                'equip', 'section', 'actual_time')
            results['equip_list'] = equip_list
            work_detail = queryset.filter(factory_date__year=year, factory_date__month=month
                                          ).values('factory_date', 'classes', 'group', 'equip', 'section', 'actual_time')
            results['work_detail'] = work_detail
        else:
            days = queryset.values('factory_date').annotate(Count('id')).count()
            if days != 0:
                results['avg_times'] = round(results['work_times'] / days, 2)
        results['work_times'] = round(results['work_times'], 2)
        return Response({'results': results})


@method_decorator([api_recorder], name="dispatch")
class AttendanceTimeStatisticsViewSet(ModelViewSet):
    queryset = EmployeeAttendanceRecords.objects.filter(
        Q(end_date__isnull=False, begin_date__isnull=False) |
        Q(end_date__isnull=True, begin_date__isnull=True)).order_by('begin_date')
    serializer_class = EmployeeAttendanceRecordsSerializer
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        name = self.request.query_params.get('name')
        date = self.request.query_params.get('date')
        year, month = int(date.split('-')[0]), int(date.split('-')[-1])
        queryset = self.get_queryset().filter(factory_date__year=year,
                                              factory_date__month=month, user__username=name)
        data = self.get_serializer(queryset, many=True).data
        if data:
            user = User.objects.filter(username=name).first()
            id_card_num = user.id_card_num
            principal_obj = AttendanceGroupSetup.objects.filter(Q(attendance_users__icontains=user.username) |
                                                                Q(principal__icontains=user.username)).first()
            principal = principal_obj.principal if principal_obj else None
        return Response({'results': data, 'principal': principal if data else None,
                     'id_card_num': id_card_num if data else None})

    def create(self, request, *args, **kwargs):
        report_list = self.request.data.get('report_list', [])
        confirm_list = self.request.data.get('confirm_list', [])
        if report_list:
            serializer = self.get_serializer(data=report_list, many=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        elif confirm_list:
            for item in confirm_list:
                EmployeeAttendanceRecords.objects.filter(pk=item['id']).update(actual_time=item['actual_time'])
        return Response('ok')


@method_decorator([api_recorder], name="dispatch")
class AttendanceClockDetailViewSet(ModelViewSet):
    queryset = AttendanceClockDetail.objects.order_by('id')
    serializer_class = AttendanceClockDetailSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = AttendanceClockDetailFilter
    pagination_class = None
    permission_classes = (IsAuthenticated,)


class AttendanceResultAuditView(APIView):
    permission_classes = (IsAuthenticated, )

    def get(self, request):
        date = self.request.query_params.get('date')
        audit = self.request.query_params.get('audit', None)
        approve = self.request.query_params.get('approve', None)
        kwargs = {}
        if audit:
            kwargs['audit_user__isnull'] = False
        if approve:
            kwargs['approve_user__isnull'] = False
        if not date:
            raise ValidationError('缺少参数date')
        last = AttendanceResultAudit.objects.filter(date=date, **kwargs).last()
        data = {'audit_user': last.audit_user,
                'approve_user': last.approve_user,
                'result': last.result,
                'result_desc': last.result_desc} if last else {}
        return Response({"results": data})

    def post(self, request):
        data = self.request.data
        audit = data.pop('audit', None)
        approve = data.pop('approve', None)
        try:
            is_user = Section.objects.get(name='生产科').in_charge_user
        except:
            is_user = None
        if self.request.user != is_user:
            raise ValidationError('当前账号不是生产科负责人')
        if audit:
            data['audit_user'] = is_user.username
        if approve:
            data['approve_user'] = is_user.username
        AttendanceResultAudit.objects.create(**data)
        return Response('ok')
