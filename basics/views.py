from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from basics.filters import EquipFilter, GlobalCodeTypeFilter, WorkScheduleFilter
from basics.models import GlobalCodeType, GlobalCode, WorkSchedule, Equip, SysbaseEquipLevel, \
    WorkSchedulePlan, ClassesDetail, PlanSchedule
from basics.serializers import GlobalCodeTypeSerializer, GlobalCodeSerializer, \
    WorkScheduleSerializer, EquipSerializer, SysbaseEquipLevelSerializer, WorkSchedulePlanSerializer, \
    WorkScheduleUpdateSerializer, ClassesDetailSerializer, PlanScheduleSerializer
from mes.common_fun import return_permission_params
from mes.derorators import api_recorder
from mes.permissions import PermissionClass
from mes.paginations import SinglePageNumberPagination


class CommonDeleteMixin(object):
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete_flag = True
        instance.delete_user = request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
    filter_backends = (DjangoFilterBackend, )
    filter_class = GlobalCodeTypeFilter


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
    filter_backends = (DjangoFilterBackend, )
    pagination_class = SinglePageNumberPagination
    filter_fields = ('global_type_id', 'global_type__type_no', )


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
    filter_backends = (DjangoFilterBackend, )
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

    queryset = ClassesDetail.objects.filter(delete_flag=False)
    serializer_class = ClassesDetailSerializer
    model_name = queryset.model.__name__.lower()
    permission_classes = (IsAuthenticatedOrReadOnly,
                          PermissionClass(permission_required=return_permission_params(model_name)))


@method_decorator([api_recorder], name="dispatch")
class PlanScheduleViewSet(CommonDeleteMixin, ModelViewSet):

    queryset = PlanSchedule.objects.filter()
    serializer_class = PlanScheduleSerializer
    model_name = queryset.model.__name__.lower()
    permission_classes = (IsAuthenticatedOrReadOnly,
                          PermissionClass(permission_required=return_permission_params(model_name)))