from django.db.models import Prefetch
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from basics.filters import EquipFilter, GlobalCodeTypeFilter, WorkScheduleFilter, GlobalCodeFilter, \
    EquipCategoryFilter, ClassDetailFilter, PlanScheduleFilter, LocationFilter
from basics.models import GlobalCodeType, GlobalCode, WorkSchedule, Equip, SysbaseEquipLevel, \
    WorkSchedulePlan, ClassesDetail, PlanSchedule, EquipCategoryAttribute, Location
from basics.serializers import GlobalCodeTypeSerializer, GlobalCodeSerializer, WorkScheduleSerializer, \
    EquipSerializer, SysbaseEquipLevelSerializer, WorkSchedulePlanSerializer, WorkScheduleUpdateSerializer, \
    PlanScheduleSerializer, EquipCategoryAttributeSerializer, ClassesSimpleSerializer, LocationSerializer
from mes.common_code import CommonDeleteMixin
from mes.derorators import api_recorder
from mes.paginations import SinglePageNumberPagination
from rest_framework.decorators import action
from rest_framework import status

from spareparts.models import MaterialLocationBinding


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
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = GlobalCodeTypeFilter


@method_decorator([api_recorder], name="dispatch")  # 本来是删除，现在改为是启用就改为禁用 是禁用就改为启用
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
    queryset = GlobalCode.objects.filter(delete_flag=False, global_type__use_flag=1)
    serializer_class = GlobalCodeSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    pagination_class = SinglePageNumberPagination
    filter_class = GlobalCodeFilter

    def get_permissions(self):
        if self.request.query_params.get('all'):
            return ()
        else:
            return (IsAuthenticated(),)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.filter(use_flag=1, global_type__use_flag=1).values('id', 'global_no', 'global_name',
                                                                               'global_type__type_name')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)


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
    queryset = WorkSchedule.objects.filter(delete_flag=False
                                           ).prefetch_related(
        Prefetch('classesdetail_set', queryset=ClassesDetail.objects.filter(delete_flag=False))
    )
    serializer_class = WorkScheduleSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = WorkScheduleFilter

    def get_permissions(self):
        if self.request.query_params.get('all'):
            return ()
        else:
            return (IsAuthenticated(),)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            serializer = self.get_serializer(queryset.filter(use_flag=1), many=True)
            return Response({'results': serializer.data})
        else:
            return super().list(request, *args, **kwargs)

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
    queryset = EquipCategoryAttribute.objects.filter(delete_flag=False).select_related('equip_type', 'process')
    serializer_class = EquipCategoryAttributeSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipCategoryFilter

    def get_permissions(self):
        if self.request.query_params.get('all'):
            return ()
        else:
            return (IsAuthenticated(),)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            queryset = queryset.filter(use_flag=True)
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})
        else:
            return super().list(request, *args, **kwargs)


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
    queryset = Equip.objects.filter(delete_flag=False).select_related('category__equip_type',
                                                                      'category__process',
                                                                      'equip_level').order_by('equip_no')
    serializer_class = EquipSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = EquipFilter

    def get_permissions(self):
        if self.request.query_params.get('all'):
            return ()
        else:
            return (IsAuthenticated(),)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.filter(use_flag=1).values('id', 'equip_no', 'equip_name', 'category')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)


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
    permission_classes = (IsAuthenticated,)


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
    permission_classes = (IsAuthenticated,)


@method_decorator([api_recorder], name="dispatch")
class ClassesDetailViewSet(mixins.ListModelMixin,
                           GenericViewSet):
    """
    list:
        班次条目列表
    """
    queryset = ClassesDetail.objects.filter(delete_flag=False).select_related('classes')
    serializer_class = ClassesSimpleSerializer
    pagination_class = SinglePageNumberPagination
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ClassDetailFilter


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
    queryset = PlanSchedule.objects.filter(
        delete_flag=False).select_related('work_schedule').prefetch_related('work_schedule_plan__classes',
                                                                            'work_schedule_plan__group')
    serializer_class = PlanScheduleSerializer
    filter_fields = ('day_time',)
    filter_backends = (DjangoFilterBackend,)
    filter_class = PlanScheduleFilter

    def get_permissions(self):
        if self.request.query_params.get('all'):
            return ()
        else:
            return (IsAuthenticated(),)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'work_schedule__schedule_name', 'day_time')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class PlanScheduleManyCreate(APIView):
    """[{"work_schedule_plan": [{"classes": '班次id', "rest_flag": 0, "group": '班组id'}],
     'day_time': '日期',
     'work_schedule': '倒班id'}...]"""
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        if not isinstance(request.data, list):
            raise ValidationError('参数错误')
        for item in request.data:
            s = PlanScheduleSerializer(data=item, context={'request': request})
            if not s.is_valid():
                raise ValidationError(s.errors)
            s.save()
        return Response('新建成功')


@method_decorator([api_recorder], name="dispatch")
class LocationViewSet(ModelViewSet):
    """位置点"""
    queryset = Location.objects.filter(delete_flag=False).all()
    serializer_class = LocationSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = LocationFilter

    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated], url_path='name_list',
            url_name='name_list')
    def name_list(self, request, pk=None):
        """展示Location所以的name"""
        name_list = Location.objects.filter(delete_flag=False).all().values('id', 'name', 'used_flag')
        # names = list(set(name_list))
        return Response(name_list)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.used_flag:
            mlb_obj = MaterialLocationBinding.objects.filter(location=instance, delete_flag=False).first()
            if mlb_obj:
                raise ValidationError('此站点已经绑定了物料，无法禁用！')
            instance.used_flag = 0
        else:
            instance.used_flag = 1
        instance.last_updated_user = request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        query_params = self.request.query_params
        type_name = query_params.getlist('type_name[]')
        if not type_name:
            return super().get_queryset()
        l_set = Location.objects.filter(type__global_name__in=type_name).all()
        return l_set
