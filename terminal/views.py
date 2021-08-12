import datetime
import json

from datetime import timedelta
from django.db.models import Max, Sum, Q
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

from basics.models import WorkSchedulePlan, Equip
from inventory.models import MaterialOutHistory
from mes.common_code import CommonDeleteMixin, TerminalCreateAPIView, response
from mes.derorators import api_recorder
from mes.settings import DATABASES
from plan.models import ProductClassesPlan, BatchingClassesPlan, BatchingClassesEquipPlan
from production.models import PalletFeedbacks
from recipe.models import ProductBatchingDetail, ZCMaterial
from terminal.filters import FeedingLogFilter, WeightPackageLogFilter, \
    WeightTankStatusFilter, WeightBatchingLogListFilter, BatchingClassesEquipPlanFilter
from terminal.models import TerminalLocation, EquipOperationLog, WeightBatchingLog, FeedingLog, \
    WeightTankStatus, WeightPackageLog, Version, FeedingMaterialLog, LoadMaterialLog, MaterialInfo, Bin, RecipePre, \
    RecipeMaterial, ReportBasic, ReportWeight, Plan, LoadTankMaterialLog, PackageExpire
from terminal.serializers import LoadMaterialLogCreateSerializer, \
    EquipOperationLogSerializer, BatchingClassesEquipPlanSerializer, WeightBatchingLogSerializer, \
    WeightBatchingLogCreateSerializer, FeedingLogSerializer, WeightTankStatusSerializer, \
    WeightPackageLogSerializer, WeightPackageLogCreateSerializer, WeightPackageUpdateLogSerializer, \
    LoadMaterialLogListSerializer, WeightBatchingLogListSerializer, \
    WeightPackagePartialUpdateLogSerializer, WeightPackageRetrieveLogSerializer, LoadMaterialLogSerializer, \
    MaterialInfoSerializer, BinSerializer, PlanSerializer, PlanUpdateSerializer, RecipePreSerializer, \
    ReportBasicSerializer, ReportWeightSerializer, LoadMaterialLogUpdateSerializer, WeightPackagePlanSerializer, \
    WeightPackageLogUpdateSerializer, XLPlanCSerializer, XLPromptSerializer
from terminal.utils import TankStatusSync


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
                'actual_weight': weight_cnt_type.package_cnt
            })
        # 加载物料标准信息
        add_materials = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, useup_time__year='1970')\
            .values('id', 'material_name', 'bra_code', 'scan_material', 'init_weight', 'actual_weight', 'adjust_left_weight')
        # 未进料(所有原材料数量均为0);
        if not add_materials:
            list(map(lambda x: x.update({'bra_code': '', 'init_weight': 0, 'used_weight': 0, 'scan_material': '',
                                         'adjust_left_weight': 0}), ret))
            return Response(ret)
        # 已扫码进料: 进料部分正常显示,未进料显示为0,同物料多条码显示最新
        material_info = {i['material_name']: i for i in add_materials}
        for single_material in ret:
            material_name = single_material['material__material_name']
            plan_weight = single_material['actual_weight']
            load_data = material_info.get(material_name)
            # 不存在则说明当前只完成了一部分的进料,数量置为0
            if not load_data:
                single_material.update(
                    {'bra_code': '', 'init_weight': 0, 'used_weight': 0, 'adjust_left_weight': 0, 'scan_material': ''})
                continue
            # 全部完成进料
            single_material.update({'bra_code': load_data['bra_code'], 'init_weight': load_data['init_weight'],
                                    'used_weight': load_data['actual_weight'], 'scan_material': load_data['scan_material'],
                                    'adjust_left_weight': load_data['adjust_left_weight'], 'id': load_data['id']
                                    })
            # 判断物料是否够一车
            left = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, material_name=material_name) \
                .aggregate(left_weight=Sum('real_weight'))['left_weight']
            if left < plan_weight:
                single_material.update(
                    {'msg': '物料：{}不足, 请扫码添加物料'.format(material_name)})
            else:
                single_material.update({'msg': ''})
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class LoadMaterialLogViewSet(TerminalCreateAPIView,
                             mixins.ListModelMixin,
                             mixins.UpdateModelMixin,
                             GenericViewSet):
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
        elif self.action == 'update':
            return LoadMaterialLogUpdateSerializer
        else:
            return LoadMaterialLogCreateSerializer

    def update(self, request, *args, **kwargs):
        self.queryset = LoadTankMaterialLog.objects.all()
        left_weight = request.data.get('adjust_left_weight')
        batch_material = self.get_object()
        serializer = self.get_serializer(batch_material, data=request.data)
        if not serializer.is_valid():
            return response(success=False, message=list(serializer.errors.values())[0][0])
        if batch_material.unit == '包' and isinstance(left_weight, float):
            return response(success=False, message='包数应为整数')
        if left_weight > batch_material.init_weight or left_weight < 0:
            return response(success=False, message='请输入正确的剩余修正量数值')
        # 获得本次修正量,修改真正计算的总量
        change_num = float(batch_material.adjust_left_weight) - left_weight
        batch_material.real_weight = float(batch_material.real_weight) - change_num
        batch_material.adjust_left_weight = batch_material.real_weight
        self.perform_update(serializer)
        batch_material.save()
        return response(success=True, message='修正成功')


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
        查询投料履历
    create:
        扫码新增投料履历
    """
    queryset = WeightBatchingLog.objects.all().order_by('-created_date')
    pagination_class = None
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]

    def get_serializer_class(self):
        if self.action == 'list':
            return WeightBatchingLogSerializer
        else:
            return WeightBatchingLogCreateSerializer

    def list(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no')
        batch_time = datetime.datetime.now().date()
        batch_classes = self.request.query_params.get('batch_classes')
        queryset = self.get_queryset().filter(equip_no=equip_no, batch_time__date=batch_time, batch_classes=batch_classes)
        serializer = self.get_serializer(queryset, many=True)
        return response(success=True, data=serializer.data)

    def create(self, request, *args, **kwargs):
        equip_no = self.request.data.get('equip_no')
        serializer = self.get_serializer(data=self.request.data)
        # ERP与MES物料未绑定
        if not serializer.is_valid():
            return response(success=False, message=list(serializer.errors.values())[0][0])
        instance = serializer.save()
        if instance.status == 2:
            return response(success=False, message=instance.failed_reason)
        # 开门
        try:
            tank_status_sync = TankStatusSync(equip_no=equip_no)
            tank_no = instance.tank_no
            tank_num = tank_no[:len(tank_no) - 1]
            kwargs = {'signal_a': tank_num} if tank_no.endswith('A') else {'signal_b': tank_num}
            tank_status_sync.sync(**kwargs)
        except:
            return response(success=False, message='打开料罐门失败！')
        # WeightTankStatus.objects.filter(tank_no=instance.tank_no).update(open_flag=1)
        return response(success=True, data={"tank_no": tank_no}, message='{}号料罐门已打开'.format(tank_no))


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
                material_nos = batching_class_plan.weigh_cnt_type.weight_details.filter(
                    delete_flag=False).values_list('material__material_no', flat=True)
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
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return response(success=True, data=serializer.data)

    def list(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no') if self.request.query_params.get('equip_no') else 'F01'
        batch_time = self.request.query_params.get('batch_time') if self.request.query_params.get('batch_time') else\
            datetime.datetime.now().strftime('%Y-%m-%d')
        product_no = self.request.query_params.get('product_no')
        status = self.request.query_params.get('status', 'all')
        db_config = [k for k, v in DATABASES.items() if v['NAME'].startswith('YK_XL')]
        if equip_no not in db_config:
            return Response([])
        # mes网页请求
        # 筛选配料时间为当天的记录
        report_basic_records = list(ReportBasic.objects.using(equip_no).filter(
            planid__startswith=''.join(batch_time.split('-'))[2:]).values_list('planid', 'savetime'))
        if not report_basic_records:
            return Response([])
        plan_ids = set([i[0] for i in report_basic_records])
        plan_filter_kwargs = {'planid__in': plan_ids, 'state__in': ['运行中', '完成']}
        weight_filter_kwargs = {'equip_no': equip_no, 'batch_time__date': batch_time}
        if product_no:
            weight_filter_kwargs.update({'product_no': product_no})
            plan_filter_kwargs.update({'recipe': product_no})
        # 获取称量系统生产计划数据
        equip_plan_info = Plan.objects.using(equip_no).filter(**plan_filter_kwargs)
        # 履历表中已生成的record(plan表主键)
        ids = list(set(self.queryset.filter(**weight_filter_kwargs).values_list('record', flat=True)))
        # 打印履历表为空(全是未打印数据)
        if not self.queryset:
            if status == 'Y':
                return Response([])
            else:
                page = self.paginate_queryset(list(equip_plan_info))
                if page:
                    serializer = WeightPackagePlanSerializer(page, many=True)
                    for i in serializer.data:
                        recipe_pre = RecipePre.objects.using(equip_no).filter(name=i['product_no'])
                        dev_type = recipe_pre.first().ver if recipe_pre else ''
                        plan_weight = recipe_pre.first().weight if recipe_pre else 0
                        # 配料时间
                        actual_batch_time = [j for j in report_basic_records if j[0] == i['plan_weight_uid']][0][1]
                        i.update({'plan_weight': plan_weight, 'equip_no': equip_no, 'dev_type': dev_type,
                                  'batch_time': actual_batch_time})
                    return self.get_paginated_response(serializer.data)
                return Response([])
        # 履历表不为空
        if status == 'all':
            # 已打印信息
            already_print = self.queryset.filter(**weight_filter_kwargs)
            # 未打印(剔除已打印)
            no_print_data = equip_plan_info.exclude(id__in=ids)
            # 分页返回
            page = self.paginate_queryset(list(already_print) + list(no_print_data))
            if page:
                data = []
                for k in page:
                    try:
                        y_or_n = k.status
                        if k.package_fufil != k.package_plan_count:
                            get_status = Plan.objects.using(equip_no).filter(planid=k.plan_weight_uid).first()
                            k.package_fufil = get_status.actno
                            k.noprint_count = get_status.actno - k.package_count
                            k.save()
                        data.append(WeightPackageLogSerializer(k).data)
                    except:
                        serializer = WeightPackagePlanSerializer(k).data
                        recipe_pre = RecipePre.objects.using(equip_no).filter(name=serializer['product_no'])
                        dev_type = recipe_pre.first().ver if recipe_pre else ''
                        plan_weight = recipe_pre.first().weight if recipe_pre else 0
                        actual_batch_time = [j for j in report_basic_records if j[0] == serializer['plan_weight_uid']][0][1]
                        serializer.update({'equip_no': equip_no, 'dev_type': dev_type, 'plan_weight': plan_weight,
                                           'batch_time': actual_batch_time})
                        data.append(serializer)
                return self.get_paginated_response(data)
            return Response([])
        # 未打印(剔除已打印)
        elif status == 'N':
            weight_filter_kwargs.update({'status': status})
            # 履历表中状态为未打印
            weight_no_print = self.queryset.filter(**weight_filter_kwargs)
            # 生产中剔除履历表中已经打印的
            plan_no_print = equip_plan_info.exclude(id__in=ids)
            # 分页返回
            page = self.paginate_queryset(list(weight_no_print) + list(plan_no_print))
            if page:
                data = []
                for k in page:
                    try:
                        y_or_n = k.status
                        if k.package_fufil != k.package_plan_count:
                            get_status = Plan.objects.using(equip_no).filter(planid=k.plan_weight_uid).first()
                            k.package_fufil = get_status.actno
                            k.noprint_count = get_status.actno - k.package_count
                            k.save()
                        data.append(WeightPackageLogSerializer(k).data)
                    except:
                        serializer = WeightPackagePlanSerializer(k).data
                        recipe_pre = RecipePre.objects.using(equip_no).filter(name=serializer['product_no'])
                        dev_type = recipe_pre.first().ver if recipe_pre else ''
                        plan_weight = recipe_pre.first().weight if recipe_pre else 0
                        actual_batch_time = [j for j in report_basic_records if j[0] == serializer['plan_weight_uid']][0][1]
                        serializer.update({'equip_no': equip_no, 'dev_type': dev_type, 'plan_weight': plan_weight,
                                           'batch_time': actual_batch_time})
                        data.append(serializer)
                return self.get_paginated_response(data)
            return Response([])
        # 已打印
        else:
            weight_filter_kwargs.update({'status': status})
            already_print = self.queryset.filter(**weight_filter_kwargs)
            for k in already_print:
                if k.package_fufil != k.package_plan_count:
                    get_status = Plan.objects.using(equip_no).filter(planid=k.plan_weight_uid).first()
                    k.package_fufil = get_status.actno
                    k.noprint_count = get_status.actno - k.package_count
                    k.save()
            page = self.paginate_queryset(already_print)
            if page is not None:
                serializer = WeightPackageLogSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.WeightPackageLogSerializer(already_print, many=True)
            return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        bra_code = self.request.query_params.get('bra_code')
        plan_weight = self.request.query_params.get('plan_weight')
        begin_trains = self.request.query_params.get('begin_trains')
        end_trains = self.request.query_params.get('end_trains')
        batch_time = self.request.query_params.get('batch_time')
        # 履历表中数据详情
        if bra_code:
            single_print_record = self.queryset.get(bra_code=bra_code)
            data = {'print_begin_trains': single_print_record.print_begin_trains, 'package_count': single_print_record.package_count,
                    'product_no': single_print_record.product_no, 'dev_type': single_print_record.dev_type,
                    'plan_weight': single_print_record.plan_weight, 'equip_no': single_print_record.equip_no,
                    'batch_time': single_print_record.batch_time, 'batch_group': single_print_record.batch_group,
                    'batch_classes': single_print_record.batch_classes, 'begin_trains': single_print_record.begin_trains,
                    'end_trains': single_print_record.end_trains, 'print_count': 1}
            return Response(data)
        # 生产计划表中未打印数据详情
        id = self.request.query_params.get('id')
        equip_no = self.request.query_params.get('equip_no')
        plan_obj = Plan.objects.using(equip_no).get(id=id)
        recipe_pre = RecipePre.objects.using(equip_no).filter(name=plan_obj.recipe)
        dev_type = recipe_pre.first().ver if recipe_pre else ''
        batch_group = self.request.query_params.get('batch_group')
        same_batch_print = self.queryset.filter(plan_weight_uid=plan_obj.planid, equip_no=equip_no,
                                                product_no=plan_obj.recipe) # 删除status='Y'判断
        # 同批次第一次打印
        if not same_batch_print:
            data = {'print_begin_trains': 1, 'package_count': '',
                    'product_no': plan_obj.recipe, 'dev_type': dev_type,
                    'plan_weight': plan_weight, 'equip_no': equip_no,
                    'batch_time': batch_time, 'batch_group': batch_group,
                    'batch_classes': plan_obj.grouptime, 'begin_trains': begin_trains,
                    'end_trains': end_trains, 'print_count': 1}
            return Response(data)
        # 同批次非第一次打印
        last_same_batch = same_batch_print.first()
        data = {'print_begin_trains': last_same_batch.print_begin_trains + last_same_batch.package_count,
                'package_count': last_same_batch.package_count, 'product_no': last_same_batch.product_no,
                'dev_type': dev_type, 'plan_weight': plan_weight, 'equip_no': equip_no,
                'batch_time': last_same_batch.batch_time, 'batch_group': batch_group,
                'batch_classes': last_same_batch.batch_classes, 'begin_trains': begin_trains,
                'end_trains': end_trains, 'print_count': 1}
        return Response(data)

    def get_serializer_class(self):
        if self.action == 'create':
            return WeightPackageLogCreateSerializer
        else:
            return WeightPackageLogSerializer


@method_decorator([api_recorder], name="dispatch")
class WeightPackageCViewSet(ListModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = WeightPackageLog.objects.all().order_by('-created_date')
    serializer_class = WeightPackageLogUpdateSerializer

    def list(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no')
        equip_no_list = equip_no.split(',')
        print_data = self.get_queryset().filter(equip_no__in=equip_no_list, print_flag=1).values(
            'id', 'product_no', 'dev_type', 'plan_weight', 'equip_no', 'package_count', 'print_begin_trains', 'print_count',
            'batch_time', 'expire_days', 'batch_group', 'batch_classes', 'begin_trains', 'end_trains', 'bra_code')
        for data in print_data:
            expire_date = datetime.datetime.strftime(data['batch_time'] + timedelta(days=data['expire_days']),
                                                     '%Y-%m-%d %H:%M:%S') \
                if data['expire_days'] != 0 else '9999' + str(data['batch_time'])[4:]
            batch_time = data['batch_time'].strftime('%Y-%m-%d')
            data.update({'expire_days': expire_date, 'batch_time': batch_time})
        return Response(print_data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


@method_decorator([api_recorder], name="dispatch")
class PackageExpireView(APIView):
    """料包有效期"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        product_no = self.request.query_params.get('product_no')
        product_name = self.request.query_params.get('product_name')
        filter_kwargs = {}
        if product_no:
            filter_kwargs['product_no__icontains'] = product_no
        if product_name:
            filter_kwargs['product_name__icontains'] = product_name
        package_expire_recipe = PackageExpire.objects.all().values_list('product_name', flat=True).distinct()
        all_product_no = []
        # 获取所有称量系统配方号
        equip_list = [k for k, v in DATABASES.items() if v.get('NAME') == 'YK_XL']
        for equip in equip_list:
            try:
                single_equip_recipe = list(Plan.objects.using(equip).all().values_list('recipe', flat=True).distinct())
            except:
                # 机台连不上
                continue
            all_product_no.extend(single_equip_recipe)
        # 取plan表配方和有效期表配方差集新增数据
        set_product_no = set(all_product_no) - set(package_expire_recipe)
        for single_product_no in set_product_no:
            PackageExpire.objects.create(product_no=single_product_no, product_name=single_product_no,
                                         update_user=self.request.user.username, update_date=datetime.datetime.now().date())
        # 读取数据
        data = PackageExpire.objects.all() if not filter_kwargs else PackageExpire.objects.filter(**filter_kwargs)
        res = list(data.values('id', 'product_no', 'product_name', 'package_fine_usefullife', 'package_sulfur_usefullife'))
        return Response(res)

    def post(self, request):
        record_id = self.request.data.pop('id', '')
        f_expire_time = self.request.data.get('package_fine_usefullife', '')
        s_expire_time = self.request.data.get('package_sulfur_usefullife', '')
        if not isinstance(record_id, int) or record_id < 0 or \
                not isinstance(f_expire_time, int) or f_expire_time < 0 or\
                not isinstance(s_expire_time, int) or s_expire_time < 0:
            raise ValidationError('参数错误')
        try:
            self.request.data.update({'update_user': self.request.user.username, 'update_date': datetime.datetime.now().date()})
            PackageExpire.objects.filter(id=record_id).update(**self.request.data)
        except Exception as e:
            raise ValidationError('更新数据失败：{}'.format(e.args[0]))
        return Response('更新成功')


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
            if plan and plan.status != '完成':
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
        for v in ret.values():
            v.sort(key=lambda x: int(x['bin'][:-1]), reverse=False)

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
class RecipePreVIew(ListAPIView):
    """
    小料配方列表，参数：equip_no=设备&name=配方名称&ver=版本&remark1=备注&use_not=是否使用(0使用，1不使用)&st=开始时间&et=结束时间
    """
    serializer_class = RecipePreSerializer
    queryset = RecipePre.objects.all()

    def list(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no')
        name = self.request.query_params.get('name')
        ver = self.request.query_params.get('ver')
        remark1 = self.request.query_params.get('remark1')
        use_not = self.request.query_params.get('use_not')
        st = self.request.query_params.get('st')
        et = self.request.query_params.get('et')
        if self.request.query_params.get('all'):
            try:
                return Response(RecipePre.objects.using(equip_no).values('id', 'name', 'ver'))
            except ConnectionDoesNotExist:
                raise ValidationError('称量机台{}服务错误！'.format(equip_no))
            except Exception:
                raise

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
        queryset = RecipePre.objects.using(equip_no).filter(**filter_kwargs)
        try:
            page = self.paginate_queryset(queryset)
            serializer = self.get_serializer(page, many=True)
        except ConnectionDoesNotExist:
            raise ValidationError('称量机台{}服务错误！'.format(equip_no))
        except Exception:
            raise
        return self.get_paginated_response(serializer.data)


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
        date_time = self.request.query_params.get('date_time', datetime.datetime.now().strftime('%Y-%m-%d'))
        grouptime = self.request.query_params.get('grouptime')
        recipe = self.request.query_params.get('recipe')
        state = self.request.query_params.get('state')
        batch_time = self.request.query_params.get('batch_time')

        filter_kwargs = {}
        if not equip_no:
            raise ValidationError('参数缺失')
        if date_time:
            filter_kwargs['date_time'] = date_time
        if grouptime:
            filter_kwargs['grouptime'] = grouptime
        if recipe:
            filter_kwargs['recipe'] = recipe
        if state:
            filter_kwargs['state__in'] = state.split(',')
        if batch_time:
            filter_kwargs['planid__startswith'] = ''.join(batch_time.split('-'))[2:]
        queryset = Plan.objects.using(equip_no).filter(**filter_kwargs).order_by('-id')
        if not state:
            try:
                page = self.paginate_queryset(queryset)
                serializer = self.get_serializer(page, many=True)
            except ConnectionDoesNotExist:
                raise ValidationError('称量机台{}服务错误！'.format(equip_no))
            except Exception:
                raise
            return self.get_paginated_response(serializer.data)
        else:
            filter_kwargs.pop('date_time')
            new_queryset = Plan.objects.using(equip_no).filter(**filter_kwargs).values('recipe').distinct()
            serializer = self.get_serializer(new_queryset, many=True)
            return Response(serializer.data)

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
class ReportBasicView(ListAPIView):
    """
    称量车次报表列表，参数：equip_no=设备&planid=计划uid&s_st=开始时间&s_et=结束时间&c_st=创建开始时间&c_et=创建结束时间&recipe=配方
    """
    serializer_class = ReportBasicSerializer
    queryset = ReportBasic.objects.all()

    def list(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no')
        planid = self.request.query_params.get('planid')
        s_st = self.request.query_params.get('s_st', datetime.datetime.now().strftime('%Y-%m-%d'))
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
            filter_kwargs['starttime__gte'] = s_st + ' 00:00:00'
        if s_et:
            filter_kwargs['starttime__lte'] = s_et + ' 23:59:59'
        if c_st:
            filter_kwargs['savetime__gte'] = c_st
        if c_et:
            filter_kwargs['savetime__lte'] = c_et
        if recipe:
            filter_kwargs['recipe__icontains'] = recipe

        queryset = ReportBasic.objects.using(equip_no).filter(**filter_kwargs)
        try:
            page = self.paginate_queryset(queryset)
            serializer = self.get_serializer(page, many=True)
        except ConnectionDoesNotExist:
            raise ValidationError('称量机台{}服务错误！'.format(equip_no))
        except Exception:
            raise
        return self.get_paginated_response(serializer.data)


@method_decorator([api_recorder], name="dispatch")
class ReportWeightView(ListAPIView):
    """
    物料消耗报表，参数：equip_no=设备&planid=计划uid&recipe=配方&st=计划开始时间&et=计划结束时间
    """
    serializer_class = ReportWeightSerializer
    queryset = ReportWeight.objects.all()

    def list(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no')
        planid = self.request.query_params.get('planid')
        recipe = self.request.query_params.get('recipe')
        st = self.request.query_params.get('st', datetime.datetime.now().strftime('%Y-%m-%d'))
        et = self.request.query_params.get('et')

        if not equip_no:
            raise ValidationError('参数缺失')

        filter_kwargs = {}
        if not equip_no:
            raise ValidationError('参数缺失')
        if planid:
            filter_kwargs['planid'] = planid
        if recipe:
            filter_kwargs['recipe'] = recipe
        if st or et:
            plan_queryset = Plan.objects.using(equip_no).all()
            if st:
                plan_queryset = plan_queryset.filter(date_time__gte=st)
            if et:
                plan_queryset = plan_queryset.filter(date_time__lte=et)
            try:
                plan_ids = plan_queryset.values_list('planid', flat=True)
            except Exception:
                raise ValidationError('称量机台{}服务错误！'.format(equip_no))
            filter_kwargs['planid__in'] = list(plan_ids)

        queryset = ReportWeight.objects.using(equip_no).filter(**filter_kwargs)
        try:
            page = self.paginate_queryset(queryset)
            serializer = self.get_serializer(page, many=True)
        except ConnectionDoesNotExist:
            raise ValidationError('称量机台{}服务错误！'.format(equip_no))
        except Exception:
            raise
        return self.get_paginated_response(serializer.data)


@method_decorator([api_recorder], name="dispatch")
class XLPlanCViewSet(ListModelMixin, GenericViewSet):
    """
    list:
        料罐防错称量计划-C#查询
    """
    queryset = Plan.objects.all()
    serializer_class = XLPlanCSerializer
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no')
        date_now = datetime.datetime.now().date()
        date_before = date_now - timedelta(days=1)
        date_now_planid = ''.join(str(date_now).split('-'))[2:]
        date_before_planid = ''.join(str(date_before).split('-'))[2:]
        try:
            all_filter_plan = Plan.objects.using(equip_no).filter(
                Q(planid__startswith=date_now_planid) | Q(planid__startswith=date_before_planid),
                state__in=['运行中', '等待']).all()
        except:
            return response(success=False, message='称量机台{}错误'.format(equip_no))
        if not all_filter_plan:
            return response(success=False, message='机台{}无进行中或已完成的配料计划'.format(equip_no))
        serializer = self.get_serializer(all_filter_plan, many=True)
        for i in serializer.data:
            recipe_pre = RecipePre.objects.using(equip_no).filter(name=i['recipe'])
            dev_type = recipe_pre.first().ver if recipe_pre else ''
            i.update({'dev_type': dev_type})
        return response(success=True, data=serializer.data)


@method_decorator([api_recorder], name='dispatch')
class XLPromptViewSet(ListModelMixin, GenericViewSet):
    """
    list:
        获取投料提示信息
    """
    serializer_class = XLPromptSerializer
    queryset = WeightTankStatus.objects.filter(use_flag=True, status=1)
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no')
        date_now = datetime.datetime.now().date()
        date_before = date_now - timedelta(days=1)
        date_now_planid = ''.join(str(date_now).split('-'))[2:]
        date_before_planid = ''.join(str(date_before).split('-'))[2:]
        # 从称量系统同步料罐状态到mes表中
        tank_status_sync = TankStatusSync(equip_no=equip_no)
        try:
            tank_status_sync.sync()
        except:
            return response(success=False, message='mes同步称量系统料罐状态失败')
        try:
            # 当天称量计划的所有配方名称
            all_recipe = Plan.objects.using(equip_no).filter(
                Q(planid__startswith=date_now_planid) | Q(planid__startswith=date_before_planid),
                state__in=['运行中', '等待']).all().values_list('recipe', flat=True)
        except:
            return response(success=False, message='称量机台{}错误'.format(equip_no))
        if not all_recipe:
            return response(success=False, message='机台{}无进行中或已完成的配料计划'.format(equip_no))
        # 获取所有配方中的原料信息
        materials = set(RecipeMaterial.objects.using(equip_no).filter(recipe_name__in=set(all_recipe))
                        .values_list('name', flat=True))
        # 当前设备料罐信息
        queryset = self.get_queryset().filter(equip_no=equip_no, material_name__in=materials)
        serializer = self.get_serializer(queryset, many=True)
        return response(success=True, data=serializer.data)


@method_decorator([api_recorder], name='dispatch')
class WeightingTankStatus(APIView):
    """C#端获取料罐信息接口"""
    permission_classes = (IsAuthenticated, )

    def get(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no')
        # 从称量系统同步料罐状态到mes表中
        tank_status_sync = TankStatusSync(equip_no=equip_no)
        try:
            tank_status_sync.sync()
        except Exception as e:
            return response(success=False, message='mes同步称量系统料罐状态失败:{}'.format(e.args[0]))
        # 获取该机台号下所有料罐信息
        tanks_info = WeightTankStatus.objects.filter(equip_no=equip_no, use_flag=True)\
            .values('id', 'tank_no', 'tank_name', 'status', 'material_name', 'material_no', 'open_flag')
        return response(success=True, data=list(tanks_info))
