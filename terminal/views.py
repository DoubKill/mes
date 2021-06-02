import datetime

from django.db.models import Max
from django.db.utils import ConnectionDoesNotExist
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.mixins import CreateModelMixin, ListModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from basics.models import WorkSchedulePlan
from mes.common_code import CommonDeleteMixin, TerminalCreateAPIView, response
from mes.derorators import api_recorder
from plan.models import ProductClassesPlan, BatchingClassesPlan, BatchingClassesEquipPlan
from recipe.models import ProductBatchingDetail
from terminal.filters import FeedingLogFilter, WeightPackageLogFilter, \
    WeightTankStatusFilter, WeightBatchingLogListFilter, BatchingClassesEquipPlanFilter
from terminal.models import TerminalLocation, EquipOperationLog, WeightBatchingLog, FeedingLog, \
    WeightTankStatus, WeightPackageLog, Version, FeedingMaterialLog, LoadMaterialLog, MaterialInfo, Bin, RecipePre, \
    RecipeMaterial, ReportBasic, ReportWeight, Plan
from terminal.serializers import LoadMaterialLogCreateSerializer, \
    EquipOperationLogSerializer, BatchingClassesEquipPlanSerializer, WeightBatchingLogSerializer, \
    WeightBatchingLogCreateSerializer, FeedingLogSerializer, WeightTankStatusSerializer, \
    WeightPackageLogSerializer, WeightPackageLogCreateSerializer, WeightPackageUpdateLogSerializer, \
    LoadMaterialLogListSerializer, WeightBatchingLogListSerializer, \
    WeightPackagePartialUpdateLogSerializer, WeightPackageRetrieveLogSerializer, LoadMaterialLogSerializer, \
    MaterialInfoSerializer, BinSerializer, PlanSerializer, PlanUpdateSerializer


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
        if not mac_address:
            raise ValidationError('参数缺失')
        terminal_location = TerminalLocation.objects.filter(terminal__no=mac_address).first()
        if not terminal_location:
            raise ValidationError('该终端位置点不存在')
        equip_no = terminal_location.equip.equip_no

        # 获取当前时间的工厂日期
        now = datetime.datetime.now()
        current_work_schedule_plan = WorkSchedulePlan.objects.filter(
            start_time__lte=now,
            end_time__gte=now,
            plan_schedule__work_schedule__work_procedure__global_name='密炼'
        ).first()
        if current_work_schedule_plan:
            date_now = str(current_work_schedule_plan.plan_schedule.day_time)
        else:
            date_now = str(now.date())

        plan_actual_data = []  # 计划对比实际数据
        current_product_data = {}  # 当前生产数据
        classes_plans = ProductClassesPlan.objects.filter(
            work_schedule_plan__plan_schedule__day_time=date_now,
            equip__equip_no=equip_no,
            delete_flag=False)
        if classes:
            classes_plans = classes_plans.filter(work_schedule_plan__classes__global_name=classes)
        for plan in classes_plans:
            last_feed_log = FeedingMaterialLog.objects.using('SFJ').filter(plan_classes_uid=plan.plan_classes_uid,
                                                                           feed_end_time__isnull=False).last()
            if last_feed_log:
                actual_trains = last_feed_log.trains
            else:
                actual_trains = 0
            plan_actual_data.append(
                {
                    'product_no': plan.product_batching.stage_product_batch_no,
                    'plan_trains': plan.plan_trains,
                    'actual_trains': actual_trains,
                    'plan_classes_uid': plan.plan_classes_uid,
                    'status': plan.status,
                    'classes': plan.work_schedule_plan.classes.global_name
                }
            )
            if plan.status == '运行中':
                max_feed_log_id = LoadMaterialLog.objects.using('SFJ').filter(
                    feed_log__plan_classes_uid=plan.plan_classes_uid).aggregate(
                    max_feed_log_id=Max('feed_log_id'))['max_feed_log_id']
                if max_feed_log_id:
                    max_feed_log = FeedingMaterialLog.objects.using('SFJ').filter(id=max_feed_log_id).first()
                    if max_feed_log.feed_begin_time:
                        trains = max_feed_log.trains + 1
                    else:
                        trains = max_feed_log.trains
                else:
                    trains = 1
                current_product_data['product_no'] = plan.product_batching.stage_product_batch_no
                current_product_data['weight'] = 0
                current_product_data['trains'] = trains

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
            # 生产计划配方详情
            classes_plan = ProductClassesPlan.objects.filter(plan_classes_uid=plan_classes_uid).first()
            if not classes_plan:
                raise ValidationError('该计划不存在')
            ret = list(ProductBatchingDetail.objects.filter(
                product_batching=classes_plan.product_batching,
                delete_flag=False,
                type=1
            ).values('material__material_name', 'actual_weight'))
            for weight_cnt_type in classes_plan.product_batching.weight_cnt_types.filter(delete_flag=False):
                ret.append({
                    'material__material_name': weight_cnt_type.name,
                    'actual_weight': weight_cnt_type.total_weight
                })
        else:
            # 配料计划详情
            batching_class_plan = BatchingClassesPlan.objects.filter(plan_batching_uid=plan_batching_uid).first()
            if not batching_class_plan:
                raise ValidationError('配料计划uid不存在')
            ret = batching_class_plan.weigh_cnt_type.weight_details.filter(
                delete_flag=False).values('material__material_no', 'material__material_name', 'standard_weight')
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class LoadMaterialLogViewSet(TerminalCreateAPIView, mixins.ListModelMixin, GenericViewSet):
    """
    list:
        投料履历
    create:
        新增投料履历
    """
    pagination_class = None
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]
    queryset = LoadMaterialLog.objects.using('SFJ').all().order_by('-id')

    def get_queryset(self):
        queryset = self.queryset
        plan_classes_uid = self.request.query_params.get('plan_classes_uid')
        production_factory_date = self.request.query_params.get('production_factory_date')
        equip_no = self.request.query_params.get('equip_no')
        production_classes = self.request.query_params.get('production_classes')
        material_no = self.request.query_params.get('material_no')
        if plan_classes_uid:
            queryset = queryset.filter(feed_log__plan_classes_uid=plan_classes_uid)
        if production_factory_date:
            queryset = queryset.filter(feed_log__production_factory_date=production_factory_date)
        if equip_no:
            queryset = queryset.filter(feed_log__equip_no=equip_no)
        if production_classes:
            queryset = queryset.filter(feed_log__production_classes=production_classes)
        if material_no:
            queryset = queryset.filter(material_no__icontains=material_no)
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return LoadMaterialLogSerializer
        else:
            return LoadMaterialLogCreateSerializer


@method_decorator([api_recorder], name="dispatch")
class EquipOperationLogView(CreateAPIView):
    """机台停机/恢复停机"""
    queryset = EquipOperationLog.objects.all()
    serializer_class = EquipOperationLogSerializer
    permission_classes = (IsAuthenticated,)


@method_decorator([api_recorder], name="dispatch")
class BatchingClassesEquipPlanView(ListAPIView):
    """配料日班次计划列表"""
    queryset = BatchingClassesEquipPlan.objects.all()
    serializer_class = BatchingClassesEquipPlanSerializer
    permission_classes = (IsAuthenticated,)
    filter_class = BatchingClassesEquipPlanFilter
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return response(
                success=False,
                message=list(serializer.errors.values())[0][0])  # 只返回一条错误信息
        self.perform_create(serializer)
        return response(success=True, data=serializer.data)

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
    serializer_class = LoadMaterialLogListSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        queryset = LoadMaterialLog.objects.using('SFJ').all().order_by('-id')
        mixing_finished = self.request.query_params.get('mixing_finished', None)
        plan_classes_uid = self.request.query_params.get('plan_classes_uid')
        production_factory_date = self.request.query_params.get('production_factory_date')
        equip_no = self.request.query_params.get('equip_no')
        production_classes = self.request.query_params.get('production_classes')
        material_no = self.request.query_params.get('material_no')
        if plan_classes_uid:
            queryset = queryset.filter(feed_log__plan_classes_uid=plan_classes_uid)
        if production_factory_date:
            queryset = queryset.filter(feed_log__production_factory_date=production_factory_date)
        if equip_no:
            queryset = queryset.filter(feed_log__equip_no=equip_no)
        if production_classes:
            queryset = queryset.filter(feed_log__production_classes=production_classes)
        if material_no:
            queryset = queryset.filter(material_no__icontains=material_no)
        if mixing_finished:
            if mixing_finished == "终炼":
                queryset = queryset.filter(feed_log__product_no__icontains="FM").all()
            elif mixing_finished == "混炼":
                queryset = queryset.exclude(feed_log__product_no__icontains="FM").all()
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
class ForceFeedStock(APIView):
    def post(self, request):
        feedstock = self.request.query_params.get('plan_classes_uid')
        if not feedstock:
            raise ValidationError('缺失参数')
        try:
            pass
        except Exception:
            return response(success=False)


@method_decorator([api_recorder], name="dispatch")
class ProductExchange(APIView):
    # 规格切换
    def get(self, request):
        plan_classes_uid = self.request.query_params.get('plan_classes_uid')
        if plan_classes_uid:
            plan = ProductClassesPlan.objects.filter(plan_classes_uid=plan_classes_uid).first()
            if plan:
                ProductClassesPlan.objects.filter(equip=plan.equip,
                                                  work_schedule_plan=plan.work_schedule_plan,
                                                  status='运行中').update(status='完成')
                plan.status = '运行中'
                plan.save()
        return response(success=True)


"""
小料称量管理
"""


@method_decorator([api_recorder], name="dispatch")
class XLMaterialVIewSet(GenericViewSet,
                        CreateModelMixin,
                        ListModelMixin):
    """
    list:
        小料原材料列表，参数：equip_no=设备&name=原材料名称&code=原材料编号&use_not=是否使用(0使用，1不使用)
    create:
        新建小料原材料
    """
    queryset = MaterialInfo.objects.all()
    serializer_class = MaterialInfoSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]

    def list(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no')
        name = self.request.query_params.get('name')
        code = self.request.query_params.get('code')
        use_not = self.request.query_params.get('use_not')
        filter_kwargs = {}
        if not equip_no:
            raise ValidationError('参数缺失')
        if name:
            filter_kwargs['name__icontains'] = name
        if code:
            filter_kwargs['code__icontains'] = code
        if use_not:
            filter_kwargs['use_not'] = use_not
        try:
            ret = list(MaterialInfo.objects.using(equip_no).filter(**filter_kwargs).values())
        except Exception:
            raise ValidationError('称量机台{}服务错误！'.format(equip_no))
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class XLBinVIewSet(GenericViewSet, ListModelMixin):
    """
    list:
        料仓列表，参数：equip_no=设备
    update:
        修改料仓原材料
    """
    queryset = Bin.objects.all()
    serializer_class = BinSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]

    def list(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no')
        if not equip_no:
            raise ValidationError('参数缺失')
        try:
            data = list(Bin.objects.using(equip_no).values())
        except Exception:
            raise ValidationError('称量机台{}服务错误！'.format(equip_no))
        ret = {'A': [], 'B': []}
        for item in data:
            if item['name'] == '0':
                item['name'] = None
            if 'A' in item['bin']:
                ret['A'].append(item)
            else:
                ret['B'].append(item)
        return Response(ret)

    @action(methods=['put'],
            detail=False,
            permission_classes=[IsAuthenticated],
            url_path='save_bin',
            url_name='save_bin')
    def save_bin(self, request):
        data = self.request.data.get('bin_data')
        equip_no = self.request.data.get('equip_no')
        queryset = Bin.objects.using(equip_no).all()
        if not all([data, equip_no]):
            raise ValidationError('参数不足')
        if not isinstance(data, list):
            raise ValidationError('参数错误')
        for item in data:
            filter_kwargs = {'id': item.get('id')}
            try:
                obj = get_object_or_404(queryset, **filter_kwargs)
            except ConnectionDoesNotExist:
                raise ValidationError('称量机台{}服务错误！'.format(equip_no))
            except Exception:
                raise
            s = BinSerializer(instance=obj, data=item)
            s.is_valid(raise_exception=True)
            s.save()
        return Response('更新成功！')


@method_decorator([api_recorder], name="dispatch")
class RecipePreVIew(APIView):
    """
    小料配方列表，参数：equip_no=设备&name=配方名称&ver=版本&remark1=备注&use_not=是否使用(0使用，1不使用)&st=开始时间&et=结束时间
    """

    def get(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no')
        name = self.request.query_params.get('name')
        ver = self.request.query_params.get('ver')
        remark1 = self.request.query_params.get('remark1')
        use_not = self.request.query_params.get('use_not')
        st = self.request.query_params.get('st')
        et = self.request.query_params.get('et')

        filter_kwargs = {}
        if not equip_no:
            raise ValidationError('参数缺失')
        if name:
            filter_kwargs['name__icontains'] = name
        if ver:
            filter_kwargs['ver__icontains'] = ver
        if remark1:
            filter_kwargs['remark1__icontains'] = remark1
        if use_not:
            filter_kwargs['use_not'] = use_not
        if st:
            filter_kwargs['time__gte'] = st
        if et:
            filter_kwargs['time__lte'] = et
        try:
            ret = list(RecipePre.objects.using(equip_no).filter(**filter_kwargs).values())
        except Exception:
            raise ValidationError('称量机台{}服务错误！'.format(equip_no))
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class RecipeMaterialVIew(APIView):
    """
    小料配方详情，参数：equip_no=设备&recipe_name=配方名称
    """

    def get(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no')
        recipe_name = self.request.query_params.get('recipe_name')

        if not all([equip_no, recipe_name]):
            raise ValidationError('参数缺失')
        try:
            ret = list(RecipeMaterial.objects.using(equip_no).filter(recipe_name=recipe_name).values())
        except ConnectionDoesNotExist:
            raise ValidationError('称量机台{}服务错误！'.format(equip_no))
        except Exception:
            raise
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class XLPlanVIewSet(ModelViewSet):
    """
    list:
        小料计划，参数：equip_no=设备
    create:
        新建小料计划
    """
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]

    def get_serializer_class(self):
        if self.action in ('list', 'create'):
            return PlanSerializer
        else:
            return PlanUpdateSerializer

    def list(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no')
        date_time = self.request.query_params.get('date_time')
        grouptime = self.request.query_params.get('grouptime')
        recipe = self.request.query_params.get('recipe_id')

        filter_kwargs = {}
        if not equip_no:
            raise ValidationError('参数缺失')
        if date_time:
            filter_kwargs['date_time'] = date_time
        if grouptime:
            filter_kwargs['grouptime'] = grouptime
        if recipe:
            filter_kwargs['recipe_id'] = recipe
        try:
            ret = list(Plan.objects.using(equip_no).filter(**filter_kwargs).values())
        except ConnectionDoesNotExist:
            raise ValidationError('称量机台{}服务错误！'.format(equip_no))
        except Exception:
            raise
        return Response(ret)

    def get_object(self):
        """
        Returns the object the view is displaying.

        You may want to override this if you need to provide non-standard
        queryset lookups.  Eg if objects are referenced using multiple
        keyword arguments in the url conf.
        """
        equip_no = self.request.data.get('equip_no')
        if not equip_no:
            raise ValidationError('称量机台参数缺失！')
        queryset = Plan.objects.using(equip_no).all()
        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        try:
            obj = get_object_or_404(queryset, **filter_kwargs)
        except ConnectionDoesNotExist:
            raise ValidationError('称量机台{}服务错误！'.format(equip_no))
        except Exception:
            raise
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj


@method_decorator([api_recorder], name="dispatch")
class ReportBasicView(APIView):
    """
    称量车次报表列表，参数：equip_no=设备&planid=计划uid&s_st=开始时间&s_et=结束时间&c_st=创建开始时间&c_et=创建结束时间&recipe=配方
    """

    def get(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no')
        planid = self.request.query_params.get('planid')
        s_st = self.request.query_params.get('s_st')
        s_et = self.request.query_params.get('s_et')
        c_st = self.request.query_params.get('c_st')
        c_et = self.request.query_params.get('c_et')
        recipe = self.request.query_params.get('recipe')

        if not equip_no:
            raise ValidationError('参数缺失')

        filter_kwargs = {}
        if not equip_no:
            raise ValidationError('参数缺失')
        if planid:
            filter_kwargs['planid__icontains'] = planid
        if s_st:
            filter_kwargs['starttime__gte'] = s_st
        if s_et:
            filter_kwargs['starttime__lte'] = s_et
        if c_st:
            filter_kwargs['savetime__gte'] = c_st
        if c_et:
            filter_kwargs['savetime__lte'] = c_et
        if recipe:
            filter_kwargs['recipe__icontains'] = recipe
        try:
            ret = list(ReportBasic.objects.using(equip_no).filter(**filter_kwargs).values())
        except ConnectionDoesNotExist:
            raise ValidationError('称量机台{}服务错误！'.format(equip_no))
        except Exception:
            raise
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class ReportWeightView(APIView):
    """
    物料消耗报表，参数：equip_no=设备&planid=计划uid&recipe=配方&st=计划开始时间&et=计划结束时间
    """

    def get(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no')
        planid = self.request.query_params.get('planid')
        recipe = self.request.query_params.get('recipe')
        st = self.request.query_params.get('st')
        et = self.request.query_params.get('et')

        if not equip_no:
            raise ValidationError('参数缺失')

        filter_kwargs = {}
        if not equip_no:
            raise ValidationError('参数缺失')
        if planid:
            filter_kwargs['planid__icontains'] = planid
        if recipe:
            filter_kwargs['recipe__icontains'] = recipe
        if st or et:
            plan_queryset = Plan.objects.using(equip_no).all()
            if st:
                plan_queryset = plan_queryset.filter(addtime__gte=st)
            if et:
                plan_queryset = plan_queryset.filter(addtime__lte=et)
            try:
                plan_ids = plan_queryset.values_list('id', flat=True)
            except Exception:
                raise ValidationError('称量机台{}服务错误！'.format(equip_no))
            filter_kwargs['planid__in'] = list(plan_ids)
        try:
            ret = list(ReportWeight.objects.using(equip_no).filter(**filter_kwargs).values())
        except ConnectionDoesNotExist:
            raise ValidationError('称量机台{}服务错误！'.format(equip_no))
        except Exception:
            raise
        return Response(ret)