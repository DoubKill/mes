import re

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import mixins
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from basics.models import PlanSchedule
from mes.common_code import get_day_plan_class_set
from plan.models import ProductClassesPlan
from production.filters import TrainsFeedbacksFilter, PalletFeedbacksFilter, QualityControlFilter, EquipStatusFilter, \
    PlanStatusFilter, ExpendMaterialFilter
from production.models import TrainsFeedbacks, PalletFeedbacks, EquipStatus, PlanStatus, ExpendMaterial, OperationLog, \
    QualityControl
from production.serializers import QualityControlSerializer, OperationLogSerializer, ExpendMaterialSerializer, \
    PlanStatusSerializer, EquipStatusSerializer, PalletFeedbacksSerializer, TrainsFeedbacksSerializer


class TrainsFeedbacksViewSet(mixins.CreateModelMixin,
                             mixins.RetrieveModelMixin,
                             mixins.ListModelMixin,
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


class PalletFeedbacksViewSet(mixins.CreateModelMixin,
                             mixins.RetrieveModelMixin,
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
    queryset = PalletFeedbacks.objects.filter(delete_flag=False)
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = PalletFeedbacksSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ('id',)
    filter_class = PalletFeedbacksFilter


class EquipStatusViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
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
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = EquipStatusSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ('id',)
    filter_class = EquipStatusFilter


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


class ProductProcess(APIView):

    def get(self, request):
        params = request.query_params
        # search_time_str = params.get("search_time")
        # target_equip_no = params.get('equip_no')
        target_equip_no = None
        # if not re.compile(r"[0-9]{4}\-[0-9]{1,2}\-[0-9]{1,2}", search_time_str):
        #     return Response("bad search_time", status=400)
        # plan_schedule = PlanSchedule.objects.filter(day_time=search_time_str).first()
        plan_schedule = PlanSchedule.objects.filter(id=9).first()
        # day_plan_id_list = plan_schedule.ps_day_plan.filter(delete_flag=False).values_list("id", flat=True)
        day_plan_set = plan_schedule.ps_day_plan.filter(delete_flag=False)
        return_data = {
            "datas": []
        }
        day_plan_actual = []
        plan_weight = 0
        product_no = ""
        equip_no = ""
        for day_plan in list(day_plan_set):
            instance = {}
            plan_trains = 0
            actual_trains = 0
            class_plan_set = ProductClassesPlan.objects.filter(product_day_plan=day_plan.id)
            # plan_uid_list = class_plan_set.values_list("plan_classes_uid", flat=True)
            for class_plan in list(class_plan_set):
                day_plan_actual = []
                plan_weight = 0
                if target_equip_no:
                    temp_ret_set = TrainsFeedbacks.objects.filter(plan_classes_uid=class_plan.plan_classes_uid, equip_no=target_equip_no)
                else:
                    temp_ret_set = TrainsFeedbacks.objects.filter(plan_classes_uid=class_plan.plan_classes_uid)
                if temp_ret_set:
                    actual = temp_ret_set.order_by("-created_date").first()
                    day_plan_actual.append({
                        "plan_trains": actual.plan_trains,
                        "actual_trains": actual.actual_trains,
                        "classes": actual.classes
                    })
                    plan_weight += actual.plan_weight
                    product_no = actual.product_no
                    equip_no = actual.equip_no
                    plan_trains += actual.plan_trains
                    actual_trains += actual.actual_trains
            instance.update(classes_data=day_plan_actual, plan_weight=plan_weight,
                            product_no=product_no, equip_no=equip_no,
                            plan_trains=plan_trains, actual_trains=actual_trains)
            return_data["datas"].append(instance)
        return Response(return_data)



        # temp_set = ProductClassesPlan.objects.filter(product_day_plan__in=day_plan_id_list)
        # plan_classes_uid_list = temp_set.values_list('plan_classes_uid', flat=True)
        # plan_ret_set = TrainsFeedbacks.objects.filter(plan_classes_uid__in=plan_classes_uid_list, equip_no=equip_no)
        # return_list = []
        # for instance in temp_set:
        #     return_instance = {}
        #     uid = instance.plan_classes_uid
        #     if equip_no:
        #         temp_ret_set = TrainsFeedbacks.objects.filter(plan_classes_uid=uid, equip_no=equip_no)
        #     else:
        #         temp_ret_set = TrainsFeedbacks.objects.filter(plan_classes_uid=uid)
        #     if temp_ret_set:
        #         actual = temp_ret_set.order_by("-created_date").first().values()