from django.db.transaction import atomic
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from django.http import HttpResponse
from django.db.models import Q
import json

from basics.filters import EquipFilter, GlobalCodeTypeFilter, WorkScheduleFilter, GlobalCodeFilter, EquipCategoryFilter
from basics.models import GlobalCodeType, GlobalCode, WorkSchedule, Equip, SysbaseEquipLevel, \
    WorkSchedulePlan, ClassesDetail, PlanSchedule, EquipCategoryAttribute
from basics.serializers import GlobalCodeTypeSerializer, GlobalCodeSerializer, WorkScheduleSerializer, \
    EquipSerializer, SysbaseEquipLevelSerializer, WorkSchedulePlanSerializer, WorkScheduleUpdateSerializer, \
    ClassesDetailSerializer, PlanScheduleSerializer, EquipCategoryAttributeSerializer
from mes.common_code import return_permission_params, CommonDeleteMixin
from mes.derorators import api_recorder
from mes.permissions import PermissionClass
from mes.paginations import SinglePageNumberPagination


@method_decorator([api_recorder], name="dispatch")
class GlobalCodeTypeViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        公共代码类型列表
    create:
        创建公共代码类型
    update:
        修改公共代码类型
    destroy:
        删除公共代码类型
    """
    queryset = GlobalCodeType.objects.filter(delete_flag=False)
    serializer_class = GlobalCodeTypeSerializer
    model_name = queryset.model.__name__.lower()
    permission_classes = (IsAuthenticatedOrReadOnly,
                          PermissionClass(permission_required=return_permission_params(model_name)))
    filter_backends = (DjangoFilterBackend,)
    filter_class = GlobalCodeTypeFilter

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.global_codes.filter().update(delete_flag=True, delete_user=request.user)
        return super().destroy(request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class GlobalCodeViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        公共代码列表
    create:
        创建公共代码
    update:
        修改公共代码
    destroy:
        删除公共代码
    """
    queryset = GlobalCode.objects.filter(delete_flag=False)
    serializer_class = GlobalCodeSerializer
    model_name = queryset.model.__name__.lower()
    permission_classes = (IsAuthenticatedOrReadOnly,
                          PermissionClass(permission_required=return_permission_params(model_name)))
    filter_backends = (DjangoFilterBackend,)
    pagination_class = SinglePageNumberPagination
    filter_class = GlobalCodeFilter


@method_decorator([api_recorder], name="dispatch")
class WorkScheduleViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        工作日程列表
    create:
        创建工作日程
    update:
        修改工作日程
    destroy:
        删除工作日程
    """
    queryset = WorkSchedule.objects.filter(delete_flag=False)
    serializer_class = WorkScheduleSerializer
    model_name = queryset.model.__name__.lower()
    permission_classes = (IsAuthenticatedOrReadOnly,
                          PermissionClass(permission_required=return_permission_params(model_name)))
    filter_backends = (DjangoFilterBackend,)
    filter_class = WorkScheduleFilter

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return WorkScheduleUpdateSerializer
        else:
            return WorkScheduleSerializer


@method_decorator([api_recorder], name="dispatch")
class EquipCategoryViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        设备种类列表
    create:
        创建设备种类
    update:
        修改设备种类
    destroy:
        删除设备种类
    """
    queryset = EquipCategoryAttribute.objects.filter(delete_flag=False)
    serializer_class = EquipCategoryAttributeSerializer
    model_name = queryset.model.__name__.lower()
    permission_classes = (IsAuthenticatedOrReadOnly,
                          PermissionClass(permission_required=return_permission_params(model_name)))
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipCategoryFilter


# @method_decorator([api_recorder], name="dispatch")
# class EquipCategoryListViewSet(APIView):
#     def get(self, request):
#         category_name = request.GET.get("category_name", None)
#         equip_type = request.GET.get("equip_type", None)
#
#         queryset = EquipCategoryAttribute.objects.filter(delete_flag=False)
#         if category_name:
#             queryset = queryset.filter(category_name__icontains=category_name)
#         if equip_type:
#             queryset = EquipCategoryAttribute.objects.filter(delete_flag=False).filter(
#                 equip_type__global_name__icontains=equip_type)
#
#         result_list = []
#         for ele in queryset:
#             result_list.append({
#                 "id": ele.id,
#                 "category_no": ele.category_no,
#                 "category_name": ele.category_name,
#                 "volume": ele.volume,
#                 "equip_type_name": ele.equip_type.global_name,
#                 "global_no": ele.process.global_no,
#                 "global_name": ele.process.global_name,
#                 "equip_type": ele.equip_type.id,
#                 "process": ele.process.id,
#             })
#         resp = {"results": result_list}
#         return HttpResponse(json.dumps(resp), status=200)
#
#
# class EquipListViewSet(APIView):
#     def get(self, request):
#         process = request.GET.get("process", None)
#         equip = request.GET.get("equip", None)
#
#         queryset = Equip.objects.filter(delete_flag=False)
#         if process:
#             queryset = queryset.filter(Q(category__process__global_no__icontains=process) | Q(
#                 category__process__global_name__icontains=process))
#         if equip:
#             queryset = Equip.objects.filter(delete_flag=False).filter(
#                 Q(equip_name__icontains=equip) | Q(equip_no__icontains=equip))
#
#         result_list = []
#         for ele in queryset:
#             result_list.append({
#                 "id": ele.id,
#                 "process_no": ele.category.process.global_no,
#                 "process_name": ele.category.process.global_name,
#                 "category_no": ele.category.category_no,
#                 "category_name": ele.category.category_name,
#                 "equip_no": ele.equip_no,
#                 "equip_name": ele.equip_name,
#                 "equip_type": ele.category.equip_type.global_name,
#                 "equip_level_name": ele.equip_level.global_name,
#                 "count_flag": ele.count_flag,
#                 "used_flag": ele.used_flag,
#                 "description": ele.description,
#                 "category": ele.category.id,
#                 "equip_level": ele.equip_level.id
#             })
#         resp = {"results": result_list}
#         return HttpResponse(json.dumps(resp), status=200)


@method_decorator([api_recorder], name="dispatch")
class EquipViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        设备列表
    create:
        创建设备
    update:
        修改设备
    destroy:
        删除设备
    """
    queryset = Equip.objects.filter(delete_flag=False)
    serializer_class = EquipSerializer
    model_name = queryset.model.__name__.lower()
    permission_classes = (IsAuthenticatedOrReadOnly,
                          PermissionClass(permission_required=return_permission_params(model_name)))
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipFilter


@method_decorator([api_recorder], name="dispatch")
class SysbaseEquipLevelViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        设备层次列表
    create:
        创建设备层次
    update:
        修改设备层次
    destroy:
        删除设备层次
    """
    queryset = SysbaseEquipLevel.objects.filter(delete_flag=False)
    serializer_class = SysbaseEquipLevelSerializer
    model_name = queryset.model.__name__.lower()
    permission_classes = (IsAuthenticatedOrReadOnly,
                          PermissionClass(permission_required=return_permission_params(model_name)))


@method_decorator([api_recorder], name="dispatch")
class WorkSchedulePlanViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        工作日程计划列表
    create:
        创建工作日程计划
    update:
        修改工作日程计划
    destroy:
        删除工作日程计划
    """
    queryset = WorkSchedulePlan.objects.filter(delete_flag=False)
    serializer_class = WorkSchedulePlanSerializer
    model_name = queryset.model.__name__.lower()
    permission_classes = (IsAuthenticatedOrReadOnly,
                          PermissionClass(permission_required=return_permission_params(model_name)))


@method_decorator([api_recorder], name="dispatch")
class ClassesDetailViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        班次条目列表
    create:
        创建班次条目
    update:
        修改班次条目
    destroy:
        删除班次条目
    """
    queryset = ClassesDetail.objects.filter(delete_flag=False)
    serializer_class = ClassesDetailSerializer
    model_name = queryset.model.__name__.lower()
    permission_classes = (IsAuthenticatedOrReadOnly,
                          PermissionClass(permission_required=return_permission_params(model_name)))


@method_decorator([api_recorder], name="dispatch")
class PlanScheduleViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        计划时间列表
    create:
        创建计划时间
    update:
        修改计划时间
    destroy:
        删除计划时间
    """
    queryset = PlanSchedule.objects.filter()
    serializer_class = PlanScheduleSerializer
    model_name = queryset.model.__name__.lower()
    permission_classes = (IsAuthenticatedOrReadOnly,
                          PermissionClass(permission_required=return_permission_params(model_name)))

    @atomic()
    def create(self, request, *args, **kwargs):
        body = request.data
        for plan in body:
            serializer = self.get_serializer(data=plan)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response({"message": "create success"}, status=status.HTTP_201_CREATED)