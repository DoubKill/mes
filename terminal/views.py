import datetime

from django.db.models import Max, Min
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from basics.models import WorkSchedulePlan
from mes.common_code import CommonDeleteMixin, TerminalCreateAPIView
from mes.derorators import api_recorder
from plan.models import ProductClassesPlan, BatchingClassesPlan
from recipe.models import ProductBatchingDetail
from terminal.filters import BatchingClassesPlanFilter, FeedingLogFilter, WeightPackageLogFilter, \
    WeightTankStatusFilter, BatchChargeLogListFilter, WeightBatchingLogListFilter
from terminal.models import TerminalLocation, EquipOperationLog, BatchChargeLog, WeightBatchingLog, FeedingLog, \
    WeightTankStatus, WeightPackageLog, Version, MaterialSupplierCollect
from terminal.serializers import BatchChargeLogSerializer, BatchChargeLogCreateSerializer, \
    EquipOperationLogSerializer, BatchingClassesPlanSerializer, WeightBatchingLogSerializer, \
    WeightBatchingLogCreateSerializer, FeedingLogSerializer, WeightTankStatusSerializer, \
    WeightPackageLogSerializer, WeightPackageLogCreateSerializer, WeightPackageUpdateLogSerializer, \
    BatchChargeLogListSerializer, WeightBatchingLogListSerializer, MaterialSupplierCollectSerializer, \
    WeightPackagePartialUpdateLogSerializer, WeightPackageRetrieveLogSerializer


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
    """根据mac地址、班次， 获取生产计划信息和当前生产的规格；参数：?mac_address=xxx&classes=xxx"""
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
        now = datetime.datetime.now()
        work_schedule_plan = WorkSchedulePlan.objects.filter(
            classes__global_name=classes,
            start_time__lte=now,
            end_time__gte=now,
            plan_schedule__work_schedule__work_procedure__global_name='密炼')
        plan_actual_data = []  # 计划对比实际数据
        current_product_data = {}  # 当前生产数据
        classes_plans = ProductClassesPlan.objects.filter(
            work_schedule_plan__in=work_schedule_plan,
            equip__equip_no=equip_no,
            delete_flag=False)
        for plan in classes_plans:
            max_min_train_data = BatchChargeLog.objects.filter(
                plan_classes_uid=plan.plan_classes_uid,
                status=1).aggregate(max_train=Max('trains'),
                                    min_train=Min('trains'))
            max_train = max_min_train_data['max_train'] if max_min_train_data['max_train'] else 0
            min_train = max_min_train_data['min_train'] if max_min_train_data['min_train'] else 0
            plan_actual_data.append(
                {
                    'product_no': plan.product_batching.stage_product_batch_no,
                    'plan_trains': plan.plan_trains,
                    'actual_trains': max_train - min_train,
                    'plan_classes_uid': plan.plan_classes_uid,
                    'status': plan.status
                }
            )
            if plan.status == '运行中':
                current_product_data['product_no'] = plan.product_batching.stage_product_batch_no
                current_product_data['weight'] = 0
                max_trains = BatchChargeLog.objects.filter(
                        plan_classes_uid=plan.plan_classes_uid,
                        status=1).aggregate(max_train=Max('trains'))['max_train']

                # 投料成功次数小于等于该配方的标准数量，则车次为1
                if BatchChargeLog.objects.filter(
                        plan_classes_uid=plan.plan_classes_uid,
                        status=1
                ).count() < len(plan.product_batching.batching_material_nos):
                    current_product_data['trains'] = 1

                # 如果配方的标准都投入成功则当前车次为最大车次加1，否则当前车次就是最大车次
                else:
                    if max_trains == plan.plan_trains:
                        current_product_data['trains'] = max_trains
                    else:
                        current_train = max_trains + 1
                        for material_no in plan.product_batching.batching_material_nos:
                            if not BatchChargeLog.objects.filter(
                                    plan_classes_uid=plan.plan_classes_uid,
                                    status=1,
                                    material_no=material_no,
                                    trains=max_trains):
                                current_train = max_trains
                        current_product_data['trains'] = current_train

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
            ret = []
            material_ids = []
            classes_plan = ProductClassesPlan.objects.filter(plan_classes_uid=plan_classes_uid).first()
            if not classes_plan:
                raise ValidationError('该计划不存在')
            if hasattr(classes_plan.product_batching, 'weighbatching'):
                weight_batching = classes_plan.product_batching.weighbatching
                weight_cnt_types = weight_batching.weighcnttype_set.all()
                for item in weight_cnt_types:
                    if item.weighbatchingdetail_set.filter():
                        cnt_type_mat_ids = item.weighbatchingdetail_set.values_list('material_id', flat=True)
                        material_ids.extend(cnt_type_mat_ids)
                        if item.weigh_type == 1:
                            ret.append({
                                'material__material_name': classes_plan.product_batching.stage_product_batch_no + '-a',
                                'actual_weight': weight_batching.a_weight
                            })
                        elif item.weigh_type == 2:
                            ret.append({
                                'material__material_name': classes_plan.product_batching.stage_product_batch_no + '-b',
                                'actual_weight': weight_batching.b_weight
                            })
                        else:
                            ret.append({
                                'material__material_name': classes_plan.product_batching.stage_product_batch_no + '-s',
                                'actual_weight': weight_batching.sulfur_weight
                            })
                ret.extend(ProductBatchingDetail.objects.exclude(material_id__in=material_ids).filter(
                    product_batching=classes_plan.product_batching, delete_flag=False
                    ).values('material__material_name', 'actual_weight'))
            else:
                ret = ProductBatchingDetail.objects.filter(
                    product_batching=classes_plan.product_batching,
                    delete_flag=False
                ).values('material__material_name',  'actual_weight')
        else:
            batching_class_plan = BatchingClassesPlan.objects.filter(plan_batching_uid=plan_batching_uid).first()
            if not batching_class_plan:
                raise ValidationError('配料计划uid不存在')
            ret = batching_class_plan.weigh_cnt_type.weighbatchingdetail_set.values('material__material_no',
                                                                                    'material__material_name',
                                                                                    'standard_weight')
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class BatchChargeLogViewSet(TerminalCreateAPIView, mixins.ListModelMixin, GenericViewSet):
    """
    list:
        投料履历
    create:
        新增投料履历
    """
    queryset = BatchChargeLog.objects.all().order_by('-created_date')
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
class WeightBatchingLogViewSet(TerminalCreateAPIView, mixins.ListModelMixin, GenericViewSet):
    """
    list:
        称量履历
    create:
        新增称量履历
    """
    queryset = WeightBatchingLog.objects.all().order_by('-created_date')
    pagination_class = None
    permission_classes = (IsAuthenticated,)
    filter_fields = ('plan_batching_uid',)
    filter_backends = [DjangoFilterBackend]

    def get_serializer_class(self):
        if self.action == 'list':
            return WeightBatchingLogSerializer
        else:
            return WeightBatchingLogCreateSerializer


@method_decorator([api_recorder], name="dispatch")
class FeedingLogViewSet(TerminalCreateAPIView, mixins.ListModelMixin, GenericViewSet):
    """
    list:
        投料履历
    create:
        新增投料履历
    """
    queryset = FeedingLog.objects.all().order_by('-created_date')
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
class WeightPackageLogViewSet(TerminalCreateAPIView,
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
    queryset = WeightPackageLog.objects.all().order_by('-created_date')
    permission_classes = (IsAuthenticated,)
    filter_class = WeightPackageLogFilter
    filter_backends = [DjangoFilterBackend]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('pagination'):
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_serializer_class(self):
        if self.action == 'list':
            return WeightPackageLogSerializer
        if self.action == 'retrieve':
            return WeightPackageRetrieveLogSerializer
        if self.action == 'update':  # 重新打印（终端使用，修改打印次数）
            return WeightPackageUpdateLogSerializer
        if self.action == 'partial_update':  # 重新打印（mes页面操作，修改条形码）
            return WeightPackagePartialUpdateLogSerializer
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
            for i in range(begin_trains, end_trains + 1):
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
                return Response(list(new_version.values())[-1])  # 每次只找最新的更新包
            else:
                return Response({})
        else:
            raise ValidationError('暂无当前软件版本信息！！！')


class BarCodeTank(APIView):
    """根据物料条形码获取物料罐信息，参数：bar_code=xxx"""

    def get(self, request):
        bar_code = self.request.query_params.get('bar_code')
        return Response(WeightTankStatus.objects.filter().values('tank_no')[0])


@method_decorator([api_recorder], name="dispatch")
class BatchChargeLogListViewSet(ListAPIView):
    """密炼投入履历
    """
    queryset = BatchChargeLog.objects.all()
    serializer_class = BatchChargeLogListSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]
    filter_class = BatchChargeLogListFilter

    def get_queryset(self):
        queryset = super(BatchChargeLogListViewSet, self).get_queryset()
        mixing_finished = self.request.query_params.get('mixing_finished', None)
        if mixing_finished:
            if mixing_finished == "终炼":
                queryset = queryset.filter(product_no__icontains="FM").all()
            elif mixing_finished == "混炼":
                queryset = queryset.exclude(product_no__icontains="FM").all()
        return queryset


@method_decorator([api_recorder], name="dispatch")
class WeightBatchingLogListViewSet(ListAPIView):
    """药品投入统计
    """
    queryset = WeightBatchingLog.objects.all()
    serializer_class = WeightBatchingLogListSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]
    filter_class = WeightBatchingLogListFilter

    def get_queryset(self):
        queryset = super(WeightBatchingLogListViewSet, self).get_queryset()
        interval = self.request.query_params.get('interval', "日")  # 班次 日 周 月  年
        production_factory_date = self.request.query_params.get('production_factory_date',None)
        if interval and production_factory_date:
            from datetime import timedelta
            production_factory_date = datetime.datetime.strptime(production_factory_date, "%Y-%m-%d")
            this_week_start = production_factory_date - timedelta(days=production_factory_date.weekday())  # 当天坐在的周的周一
            this_week_end = production_factory_date + timedelta(days=6 - production_factory_date.weekday())  # 当天所在周的周日
            if interval == "班次":
                bcp_set = BatchingClassesPlan.objects.filter(
                    work_schedule_plan__plan_schedule__work_schedule__work_procedure__global_name='密炼',
                    work_schedule_plan__plan_schedule__day_time=production_factory_date).values_list(
                    'plan_batching_uid', flat=True)
                plan_batching_uid_list = list(bcp_set)
                queryset = queryset.filter(plan_batching_uid__in=plan_batching_uid_list).all()
            elif interval == "日":
                bcp_set = BatchingClassesPlan.objects.filter(
                    work_schedule_plan__plan_schedule__work_schedule__work_procedure__global_name='密炼',
                    work_schedule_plan__plan_schedule__day_time=production_factory_date).values_list(
                    'plan_batching_uid', flat=True)
                plan_batching_uid_list = list(bcp_set)
                queryset = queryset.filter(plan_batching_uid__in=plan_batching_uid_list).all()
            elif interval == "周":
                bcp_set = BatchingClassesPlan.objects.filter(
                    work_schedule_plan__plan_schedule__work_schedule__work_procedure__global_name='密炼',
                    work_schedule_plan__plan_schedule__day_time__gte=this_week_start.date(),
                    work_schedule_plan__plan_schedule__day_time__lte=this_week_end.date()).values_list(
                    'plan_batching_uid', flat=True)
                plan_batching_uid_list = list(bcp_set)
                queryset = queryset.filter(plan_batching_uid__in=plan_batching_uid_list).all()
            elif interval == "月":
                bcp_set = BatchingClassesPlan.objects.filter(
                    work_schedule_plan__plan_schedule__work_schedule__work_procedure__global_name='密炼',
                    work_schedule_plan__plan_schedule__day_time__year=production_factory_date.year,
                    work_schedule_plan__plan_schedule__day_time__month=production_factory_date.month).values_list(
                    'plan_batching_uid', flat=True)
                plan_batching_uid_list = list(bcp_set)
                queryset = queryset.filter(plan_batching_uid__in=plan_batching_uid_list).all()
            elif interval == "年":
                bcp_set = BatchingClassesPlan.objects.filter(
                    work_schedule_plan__plan_schedule__work_schedule__work_procedure__global_name='密炼',
                    work_schedule_plan__plan_schedule__day_time__year=production_factory_date.year).values_list(
                    'plan_batching_uid', flat=True)
                plan_batching_uid_list = list(bcp_set)
                queryset = queryset.filter(plan_batching_uid__in=plan_batching_uid_list).all()
        else:
            raise ValidationError('参数不全')
        return queryset


@method_decorator([api_recorder], name="dispatch")
class MaterialSupplierCollectViewSet(mixins.CreateModelMixin,
                                     mixins.ListModelMixin,
                                     mixins.UpdateModelMixin,
                                     mixins.RetrieveModelMixin,
                                     GenericViewSet):
    queryset = MaterialSupplierCollect.objects.filter(delete_flag=False)
    serializer_class = MaterialSupplierCollectSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]
    filter_fields = ('material_id', )

    def get_queryset(self):
        if self.request.query_params.get('mes_system'):
            # mes生成的条码
            return self.queryset.filter(child_system__isnull=True)
        else:
            # 没有绑定原材料则认为是子系统的数据
            return self.queryset.filter(child_system__isnull=False)