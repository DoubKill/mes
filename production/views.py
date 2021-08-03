import json
import datetime
import re

import math
import time

import requests
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.db.models import Max, Sum, Count, Min, F, Q
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
from rest_framework.viewsets import GenericViewSet
from basics.models import PlanSchedule, Equip, GlobalCode, WorkSchedulePlan
from equipment.models import EquipMaintenanceOrder
from mes.common_code import OSum
from mes.conf import EQUIP_LIST
from mes.derorators import api_recorder
from mes.paginations import SinglePageNumberPagination
from mes.permissions import PermissionClass
from plan.models import ProductClassesPlan
from production.filters import TrainsFeedbacksFilter, PalletFeedbacksFilter, QualityControlFilter, EquipStatusFilter, \
    PlanStatusFilter, ExpendMaterialFilter, CollectTrainsFeedbacksFilter, UnReachedCapacityCause
from production.models import TrainsFeedbacks, PalletFeedbacks, EquipStatus, PlanStatus, ExpendMaterial, OperationLog, \
    QualityControl, ProcessFeedback, AlarmLog, MaterialTankStatus
from production.serializers import QualityControlSerializer, OperationLogSerializer, ExpendMaterialSerializer, \
    PlanStatusSerializer, EquipStatusSerializer, PalletFeedbacksSerializer, TrainsFeedbacksSerializer, \
    ProductionRecordSerializer, TrainsFeedbacksBatchSerializer, CollectTrainsFeedbacksSerializer, \
    ProductionPlanRealityAnalysisSerializer, UnReachedCapacityCauseSerializer, TrainsFeedbacksSerializer2, \
    CurveInformationSerializer, MixerInformationSerializer2, WeighInformationSerializer2, AlarmLogSerializer, \
    ProcessFeedbackSerializer, TrainsFixSerializer
from rest_framework.generics import ListAPIView, GenericAPIView, ListCreateAPIView, CreateAPIView, UpdateAPIView, \
    get_object_or_404
from datetime import timedelta

from quality.models import BatchProductNo, BatchDay, Batch, BatchMonth, BatchYear, MaterialTestOrder, \
    MaterialDealResult, MaterialTestResult
from quality.serializers import BatchProductNoDateZhPassSerializer, BatchProductNoClassZhPassSerializer


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
        if request.data:
            data = dict(request.data)
        else:
            data = dict(request.query_params)
        lot_no = data.pop("lot_no", None)
        if not lot_no:
            raise ValidationError("请传入lot_no")
        instance, flag = PalletFeedbacks.objects.update_or_create(defaults=data, **{"lot_no": lot_no})
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
            day_plan_dict[day_plan_id]["plan_weight"] += pcp.get('weight', 0)
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
        search_time_str = params.get("search_time")
        target_equip_no = params.get('equip_no')
        if search_time_str:
            if not re.search(r"[0-9]{4}\-[0-9]{1,2}\-[0-9]{1,2}", search_time_str):
                raise ValidationError("查询时间格式异常")
        else:
            search_time_str = str(datetime.date.today())
        if target_equip_no:
            pcp_set = ProductClassesPlan.objects.filter(work_schedule_plan__plan_schedule__day_time=search_time_str,
                                                        work_schedule_plan__plan_schedule__work_schedule__work_procedure__global_name="密炼",
                                                        equip__equip_no=target_equip_no,
                                                        delete_flag=False).select_related('equip__equip_no',
                                                                                          'product_batching__stage_product_batch_no',
                                                                                          'work_schedule_plan__classes__global_name',
                                                                                          'product_day_plan_id',
                                                                                          "work_schedule_plan__plan_schedule__plan_schedule_no")
        else:
            pcp_set = ProductClassesPlan.objects.filter(work_schedule_plan__plan_schedule__day_time=search_time_str,
                                                        work_schedule_plan__plan_schedule__work_schedule__work_procedure__global_name="密炼",
                                                        delete_flag=False).select_related('equip__equip_no',
                                                                                          'product_batching__stage_product_batch_no',
                                                                                          'work_schedule_plan__classes__global_name',
                                                                                          'product_day_plan_id',
                                                                                          "work_schedule_plan__plan_schedule__plan_schedule_no")
        uid_list = pcp_set.values_list("plan_classes_uid", flat=True)
        day_plan_list_temp = pcp_set.values_list("product_batching__stage_product_batch_no", "equip__equip_no")
        day_plan_list = list(set([x[0] + x[1] for x in day_plan_list_temp]))
        tf_set = TrainsFeedbacks.objects.values('plan_classes_uid').filter(plan_classes_uid__in=uid_list).annotate(
            actual_trains=Max('actual_trains'), actual_weight=Max('actual_weight'), classes=Max('classes'))
        tf_dict = {x.get("plan_classes_uid"): [x.get("actual_trains"), x.get("actual_weight"), x.get("classes")] for x
                   in tf_set}
        day_plan_dict = {x: {"plan_weight": 0, "plan_trains": 0, "actual_trains": 0, "actual_weight": 0,
                             "classes_data": [{"plan_trains": 0, "actual_trains": 0, "classes": "早班"},
                                              {"plan_trains": 0, "actual_trains": 0, "classes": "中班"},
                                              {"plan_trains": 0, "actual_trains": 0, "classes": "夜班"}
                                              ]}
                         for x in day_plan_list}
        pcp_data = pcp_set.values("plan_classes_uid", "weight", "plan_trains", 'equip__equip_no',
                                  'product_batching__stage_product_batch_no',
                                  'product_day_plan_id',
                                  'work_schedule_plan__classes__global_name',
                                  "work_schedule_plan__plan_schedule__plan_schedule_no")
        for pcp in pcp_data:
            class_name = pcp.get("work_schedule_plan__classes__global_name")
            day_plan_id = pcp.get("product_batching__stage_product_batch_no") + pcp.get("equip__equip_no")
            plan_classes_uid = pcp.get('plan_classes_uid')
            day_plan_dict[day_plan_id].update(
                equip_no=pcp.get('equip__equip_no'),
                product_no=pcp.get('product_batching__stage_product_batch_no'))
            day_plan_dict[day_plan_id]["plan_weight"] += pcp.get('weight', 0)
            day_plan_dict[day_plan_id]["plan_trains"] += pcp.get('plan_trains', 0)
            if not tf_dict.get(plan_classes_uid):
                if class_name == "早班":
                    day_plan_dict[day_plan_id]["classes_data"][0] = {
                        "plan_trains": pcp.get('plan_trains'),
                        "actual_trains": 0,
                        "classes": "早班"
                    }
                if class_name == "中班":
                    day_plan_dict[day_plan_id]["classes_data"][1] = {
                        "plan_trains": pcp.get('plan_trains'),
                        "actual_trains": 0,
                        "classes": "中班"
                    }
                if class_name == "夜班":
                    day_plan_dict[day_plan_id]["classes_data"][2] = {
                        "plan_trains": pcp.get('plan_trains'),
                        "actual_trains": 0,
                        "classes": "夜班"
                    }
                continue
            day_plan_dict[day_plan_id]["actual_trains"] += tf_dict[plan_classes_uid][0]
            day_plan_dict[day_plan_id]["actual_weight"] += tf_dict[plan_classes_uid][1]
            if tf_dict[plan_classes_uid][2] == "早班":
                day_plan_dict[day_plan_id]["classes_data"][0]["plan_trains"] += pcp.get('plan_trains')
                day_plan_dict[day_plan_id]["classes_data"][0]["actual_trains"] += tf_dict[pcp.get("plan_classes_uid")][
                    0]
            if tf_dict[plan_classes_uid][2] == "中班":
                day_plan_dict[day_plan_id]["classes_data"][1]["plan_trains"] += pcp.get('plan_trains')
                day_plan_dict[day_plan_id]["classes_data"][1]["actual_trains"] += tf_dict[pcp.get("plan_classes_uid")][
                    0]
            if tf_dict[plan_classes_uid][2] == "夜班":
                day_plan_dict[day_plan_id]["classes_data"][2]["plan_trains"] += pcp.get('plan_trains')
                day_plan_dict[day_plan_id]["classes_data"][2]["actual_trains"] += tf_dict[pcp.get("plan_classes_uid")][
                    0]
        ret_list = [_ for _ in day_plan_dict.values()]
        ret_list.sort(key=lambda x: x.get("equip_no"))
        ret = {"data": ret_list}
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
    """获取托盘开始车次-结束车次的数据，过滤字段：equip_no=设备编码&factory_date=工厂日期&classes=班次&product_no=胶料编码"""

    def get(self, request):
        equip_no = self.request.query_params.get('equip_no')
        factory_date = self.request.query_params.get('factory_date')
        classes = self.request.query_params.get('classes')
        product_no = self.request.query_params.get('product_no')
        if not all([equip_no, factory_date, classes, product_no]):
            raise ValidationError('缺少参数')
        pallet_feed_backs = PalletFeedbacks.objects.filter(
            equip_no=equip_no,
            factory_date=factory_date,
            classes=classes,
            product_no=product_no
        )
        ret = []
        for pallet_feed_back in pallet_feed_backs:
            begin_trains = pallet_feed_back.begin_trains
            end_trains = pallet_feed_back.end_trains
            for i in range(begin_trains, end_trains + 1):
                data = {
                    'product_no': pallet_feed_back.product_no,
                    'lot_no': pallet_feed_back.lot_no,
                    'classes': pallet_feed_back.classes,
                    'equip_no': pallet_feed_back.equip_no,
                    'actual_trains': i,
                    'plan_classes_uid': pallet_feed_back.plan_classes_uid,
                    'factory_date': pallet_feed_back.end_time
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
class IntervalOutputStatisticsView(APIView):

    def get(self, request, *args, **kwargs):
        hour_step, classes, factory_date = get_trains_feed_backs_query_params(self)

        if not TrainsFeedbacks.objects.filter(factory_date=factory_date).exists():
            return Response({})

        day_start_end_times = TrainsFeedbacks.objects \
            .filter(factory_date=factory_date) \
            .aggregate(day_end_time=Max('end_time'),
                       day_start_time=Min('end_time'))
        day_start_time = day_start_end_times.get('day_start_time')
        day_end_time = day_start_end_times.get('day_end_time')
        time_spans = []
        end_time = day_start_time
        while end_time < day_end_time:
            time_spans.append(end_time)
            end_time = end_time + datetime.timedelta(hours=hour_step)
        time_spans.append(day_end_time)

        data = {
            'equips': sorted(
                TrainsFeedbacks.objects.filter(factory_date=factory_date).values_list('equip_no', flat=True).distinct(),
                key=lambda e: int(e.lower()[1:]))
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

    def list(self, request, *args, **kwargs):
        params = request.query_params
        trains = params.get("trains")
        queryset = self.filter_queryset(self.get_queryset())
        st = params.get('begin_time')
        et = params.get('end_time')
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
        for _ in data:
            equip_trains[_.get("equip_no")][0] += _.get("actual_trains")
            temp_dict = {"equip_no": _.get("equip_no"),
                         "product_no": _.get("product_no"),
                         "plan_trains": plan_data.get(_.get("equip_no") + _.get("product_no")),
                         "actual_trains": _.get("actual_trains"),
                         "achieve_rate": round(
                             _.get("actual_trains") / plan_data.get(_.get("equip_no") + _.get("product_no")), 4),
                         "put_user": "unknown",
                         "product_time": (_.get("end_time") - _.get("begin_time")).total_seconds(),
                         "trains_sum": equip_trains.get(_.get("equip_no")),
                         "start_rate": (24 * 60 * 60 - equip_data.get(_.get("equip_no"))) / 60 if equip_data.get(
                             _.get("equip_no")) else 1.0
                         }
            results.append(temp_dict)
        return Response({"results": results})


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