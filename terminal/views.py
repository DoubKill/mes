
import datetime

from django.db.models import Max, Q
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from basics.models import EquipCategoryAttribute
from mes.common_code import CommonDeleteMixin
from mes.derorators import api_recorder
from plan.models import ProductClassesPlan, BatchingClassesPlan
from production.models import TrainsFeedbacks
from recipe.models import ProductBatchingDetail
from terminal.filters import BatchingClassesPlanFilter, FeedingLogFilter, WeightPackageLogFilter, WeightTankStatusFilter
from terminal.models import TerminalLocation, EquipOperationLog, BatchChargeLog, WeightBatchingLog, FeedingLog, \
    WeightTankStatus, WeightPackageLog, Version
from terminal.serializers import BatchChargeLogSerializer, BatchChargeLogCreateSerializer, \
    EquipOperationLogSerializer, BatchingClassesPlanSerializer, WeightBatchingLogSerializer, \
    WeightBatchingLogCreateSerializer, FeedingLogSerializer, WeightTankStatusSerializer, \
    WeightPackageLogSerializer, WeightPackageLogCreateSerializer, WeightPackageUpdateLogSerializer


@method_decorator([api_recorder], name="dispatch")
class BatchBasicInfoView(APIView):
    """根据mac地址获取分厂信息，密炼机名字，机台号，机台状态（停机/不停机）；参数：?mac_address=xxx"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        mac_address = self.request.query_params.get('mac_address')
        if not mac_address:
            raise ValidationError('参数缺失')
        terminal_location = TerminalLocation.objects.filter(terminal__no=mac_address).first()
        if not terminal_location:
            raise ValidationError('该终端位置点不存在')
        equip_operation_log = EquipOperationLog.objects.filter(
            equip_no=terminal_location.equip.equip_no).last()
        if not equip_operation_log:
            equip_status = 2
        else:
            equip_status = equip_operation_log.operation_type
        data = {
            'equip_no': terminal_location.equip.equip_no,
            'equip_name': terminal_location.equip.equip_name,
            'equip_status': equip_status
        }
        return Response(data)


@method_decorator([api_recorder], name="dispatch")
class BatchProductionInfoView(APIView):
    """根据mac地址、班次， 获取生产信息和当前生产的规格；参数：?mac_address=xxx&classes=xxx"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        mac_address = self.request.query_params.get('mac_address')
        classes = self.request.query_params.get('classes')
        if not all([mac_address, classes]):
            raise ValidationError('参数缺失')
        terminal_location = TerminalLocation.objects.filter(terminal__no=mac_address).first()
        if not terminal_location:
            raise ValidationError('该终端位置点不存在')
        equip_no = terminal_location.equip.equip_no
        classes_plans = ProductClassesPlan.objects.filter(
            Q(work_schedule_plan__start_time__date=datetime.datetime.now().date()) |
            Q(work_schedule_plan__end_time__date=datetime.datetime.now().date()),
            equip__equip_no=equip_no,
            work_schedule_plan__classes__global_name=classes,
            delete_flag=False
        )
        plan_actual_data = []  # 计划对比实际数据
        current_product_data = {}  # 当前生产数据
        for plan in classes_plans:
            actual_trains = TrainsFeedbacks.objects.filter(
                plan_classes_uid=plan.plan_classes_uid
            ).aggregate(max_trains=Max('actual_trains'))['max_trains']
            plan_actual_data.append(
                {
                    'product_no': plan.product_batching.stage_product_batch_no,
                    'plan_trains': plan.plan_trains,
                    'actual_trains': actual_trains if actual_trains else 0,
                    'plan_classes_uid': plan.plan_classes_uid,
                    'status': plan.status
                }
            )
            if plan.status == '运行中':
                current_product_data['product_no'] = plan.product_batching.stage_product_batch_no
                train_feedback = TrainsFeedbacks.objects.filter(plan_classes_uid=plan.plan_classes_uid).last()
                if train_feedback:
                    current_product_data['trains'] = train_feedback.actual_trains
                    current_product_data['weight'] = train_feedback.actual_weight
                else:
                    current_product_data['trains'] = 1
                    current_product_data['weight'] = 0

        return Response({'plan_actual_data': plan_actual_data,
                         'current_product_data': current_product_data})


@method_decorator([api_recorder], name="dispatch")
class BatchProductBatchingVIew(APIView):
    """根据计划号获取配方标准；参数：?plan_classes_uid=xxx"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        plan_classes_uid = self.request.query_params.get('plan_classes_uid')
        plan_batching_uid = self.request.query_params.get('plan_batching_uid')
        if plan_classes_uid:
            classes_plan = ProductClassesPlan.objects.filter(plan_classes_uid=plan_classes_uid).first()
            if not classes_plan:
                raise ValidationError('该计划不存在')
            ret = ProductBatchingDetail.objects.filter(
                product_batching=classes_plan.product_batching,
                delete_flag=False
            ).values('material__material_no',  'material__material_name',  'actual_weight')
        else:
            batching_class_plan = BatchingClassesPlan.objects.filter(plan_batching_uid=plan_batching_uid).first()
            if not batching_class_plan:
                raise ValidationError('配料计划uid不存在')
            ret = batching_class_plan.weigh_cnt_type.weighbatchingdetail_set.values('material__material_no',
                                                                                    'material__material_name',
                                                                                    'standard_weight')
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class BatchChargeLogViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, GenericViewSet):
    """
    list:
        投料履历
    create:
        新增投料履历
    """
    queryset = BatchChargeLog.objects.all()
    pagination_class = None
    permission_classes = (IsAuthenticated,)
    filter_fields = ('equip_no', 'production_classes', 'production_factory_date', 'plan_classes_uid')
    filter_backends = [DjangoFilterBackend]

    def get_serializer_class(self):
        if self.action == 'list':
            return BatchChargeLogSerializer
        else:
            return BatchChargeLogCreateSerializer


@method_decorator([api_recorder], name="dispatch")
class EquipOperationLogView(CreateAPIView):
    """机台停机/恢复停机"""
    queryset = EquipOperationLog.objects.all()
    serializer_class = EquipOperationLogSerializer
    permission_classes = (IsAuthenticated,)


@method_decorator([api_recorder], name="dispatch")
class BatchingClassesPlanView(ListAPIView):
    """配料日班次计划列表"""
    queryset = BatchingClassesPlan.objects.all()
    serializer_class = BatchingClassesPlanSerializer
    permission_classes = (IsAuthenticated,)
    filter_class = BatchingClassesPlanFilter
    filter_backends = [DjangoFilterBackend]
    pagination_class = None


@method_decorator([api_recorder], name="dispatch")
class WeightBatchingLogViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, GenericViewSet):
    """
    list:
        称量履历
    create:
        新增称量履历
    """
    queryset = WeightBatchingLog.objects.all()
    pagination_class = None
    permission_classes = (IsAuthenticated,)
    filter_fields = ('plan_batching_uid', )
    filter_backends = [DjangoFilterBackend]

    def get_serializer_class(self):
        if self.action == 'list':
            return WeightBatchingLogSerializer
        else:
            return WeightBatchingLogCreateSerializer


@method_decorator([api_recorder], name="dispatch")
class FeedingLogViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, GenericViewSet):
    """
    list:
        投料履历
    create:
        新增投料履历
    """
    queryset = FeedingLog.objects.all()
    pagination_class = None
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]
    serializer_class = FeedingLogSerializer
    filter_class = FeedingLogFilter


@method_decorator([api_recorder], name="dispatch")
class WeightTankStatusViewSet(CommonDeleteMixin, ModelViewSet):
    """
    物料罐列表
    """
    queryset = WeightTankStatus.objects.all()
    pagination_class = None
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]
    serializer_class = WeightTankStatusSerializer
    filter_class = WeightTankStatusFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        plan_batching_uid = self.request.query_params.get('plan_batching_uid')
        if plan_batching_uid:
            batching_class_plan = BatchingClassesPlan.objects.filter(plan_batching_uid=plan_batching_uid).first()
            if batching_class_plan:
                material_nos = batching_class_plan.weigh_cnt_type.weigh_batching \
                    .product_batching.batching_details.filter(delete_flag=False
                                                              ).values_list('material__material_no', flat=True)
                queryset = queryset.filter(material_no__in=material_nos)
            else:
                raise ValidationError('配料计划uid不存在')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@method_decorator([api_recorder], name="dispatch")
class WeightPackageLogViewSet(mixins.CreateModelMixin,
                              mixins.ListModelMixin,
                              mixins.UpdateModelMixin,
                              mixins.RetrieveModelMixin,
                              GenericViewSet):
    """
    list:
        称量打包履历
    create:
        新增称量打包履历
    update:
        重新打印
    """
    queryset = WeightPackageLog.objects.all()
    pagination_class = None
    permission_classes = (IsAuthenticated,)
    filter_class = WeightPackageLogFilter
    filter_backends = [DjangoFilterBackend]

    def get_serializer_class(self):
        if self.action == 'list':
            return WeightPackageLogSerializer
        if self.action == 'update':
            return WeightPackageUpdateLogSerializer
        else:
            return WeightPackageLogCreateSerializer


@method_decorator([api_recorder], name="dispatch")
class WeightPackageTrainsView(APIView):
    """称量打包车次列表"""

    def get(self, request):
        trains = set()
        plan_batching_uid = self.request.query_params.get('plan_batching_uid')
        logs = WeightPackageLog.objects.filter(plan_batching_uid=plan_batching_uid)
        for log in logs:
            begin_trains = log.begin_trains
            end_trains = log.end_trains
            for i in range(begin_trains, end_trains+1):
                trains.add(i)
        return Response(trains)


@method_decorator([api_recorder], name="dispatch")
class CheckVersion(APIView):
    """版本检查,参数：?type=区分（1:PDA  2:密炼投料 3:小料包产出 4:小料称量）&number=当前版本号"""

    def get(self, request):
        version_type = self.request.query_params.get('type')
        number = self.request.query_params.get('number')
        if not all([version_type, number]):
            raise ValidationError('参数缺失')
        try:
            version_type = int(version_type)
        except Exception:
            raise ValidationError('参数错误')
        current_version = Version.objects.filter(type=version_type, number=number).first()
        if current_version:
            new_version = Version.objects.filter(type=version_type, id__gt=current_version.id)
            if new_version:
                return Response(new_version.values()[0])
            else:
                return Response({})
        else:
            raise ValidationError('暂无当前软件版本信息！！！')


class BarCodeTank(APIView):
    """根据物料条形码获取物料罐信息，参数：bar_code=xxx"""

    def get(self, request):
        bar_code = self.request.query_params.get('bar_code')
        return Response(WeightTankStatus.objects.filter().values('tank_no')[0])


class DevTypeView(APIView):
    """获取所以机型下拉框"""

    def get(self, request):
        return Response(set(EquipCategoryAttribute.objects.values_list('category_name', flat=True)))
