import datetime
import re
import time
from datetime import timedelta
from decimal import Decimal

from django.db.models import Max, Sum, Q, F
from django.db.transaction import atomic
from django.db.utils import ConnectionDoesNotExist
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
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
from mes import settings
from mes.common_code import CommonDeleteMixin, TerminalCreateAPIView, response, SqlClient
from mes.conf import TH_CONF
from mes.derorators import api_recorder
from mes.settings import DATABASES
from plan.models import ProductClassesPlan, BatchingClassesPlan, BatchingClassesEquipPlan
from production.models import PlanStatus, MaterialTankStatus, TrainsFeedbacks
from recipe.models import ProductBatchingDetail, ProductBatching, ERPMESMaterialRelation, Material, WeighCntType, \
    WeighBatchingDetail
from terminal.filters import FeedingLogFilter, WeightTankStatusFilter, WeightBatchingLogListFilter, \
    BatchingClassesEquipPlanFilter, CarbonTankSetFilter, \
    FeedingOperationLogFilter, ReplaceMaterialFilter, ReturnRubberFilter, WeightPackageManualFilter, \
    WeightPackageSingleFilter
from terminal.models import TerminalLocation, EquipOperationLog, WeightBatchingLog, FeedingLog, \
    WeightTankStatus, WeightPackageLog, Version, FeedingMaterialLog, LoadMaterialLog, MaterialInfo, Bin, RecipePre, \
    RecipeMaterial, ReportBasic, ReportWeight, Plan, LoadTankMaterialLog, PackageExpire, MaterialChangeLog, \
    FeedingOperationLog, CarbonTankFeedingPrompt, OilTankSetting, PowderTankSetting, CarbonTankFeedWeightSet, \
    ReplaceMaterial, ReturnRubber, ToleranceDistinguish, ToleranceProject, ToleranceHandle, ToleranceRule, \
    WeightPackageManual, WeightPackageSingle, WeightPackageWms
from terminal.serializers import LoadMaterialLogCreateSerializer, \
    EquipOperationLogSerializer, BatchingClassesEquipPlanSerializer, WeightBatchingLogSerializer, \
    WeightBatchingLogCreateSerializer, FeedingLogSerializer, WeightTankStatusSerializer, \
    WeightPackageLogSerializer, WeightPackageLogCreateSerializer, LoadMaterialLogListSerializer, \
    WeightBatchingLogListSerializer, \
    LoadMaterialLogSerializer, \
    MaterialInfoSerializer, BinSerializer, PlanSerializer, PlanUpdateSerializer, RecipePreSerializer, \
    ReportBasicSerializer, ReportWeightSerializer, LoadMaterialLogUpdateSerializer, WeightPackagePlanSerializer, \
    WeightPackageLogUpdateSerializer, XLPlanCSerializer, XLPromptSerializer, CarbonTankSetSerializer, \
    CarbonTankSetUpdateSerializer, FeedingOperationLogSerializer, CarbonFeedingPromptSerializer, \
    CarbonFeedingPromptCreateSerializer, PowderTankSettingSerializer, OilTankSettingSerializer, \
    ReplaceMaterialSerializer, ReturnRubberSerializer, ToleranceRuleSerializer, WeightPackageManualSerializer, \
    WeightPackageSingleSerializer, WeightPackageLogCUpdateSerializer
from terminal.utils import TankStatusSync, CarbonDeliverySystem, out_task_carbon, get_tolerance, material_out_barcode, \
    get_manual_materials


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
            # 任务状态
            plan_status_info = PlanStatus.objects.using("SFJ").filter(
                plan_classes_uid=plan.plan_classes_uid).order_by('created_date').last()
            plan_status = plan_status_info.status if plan_status_info else plan.status
            if plan_status not in ['运行中', '等待']:
                continue
            actual_trains = 0
            if plan_status == '运行中':
                max_trains = TrainsFeedbacks.objects.filter(plan_classes_uid=plan.plan_classes_uid).aggregate(max_trains=Max('actual_trains'))['max_trains']
                current_product_data['product_no'] = plan.product_batching.stage_product_batch_no
                actual_trains = actual_trains if not max_trains else max_trains
            plan_actual_data.append(
                {
                    'product_no': plan.product_batching.stage_product_batch_no,
                    'plan_trains': plan.plan_trains,
                    'actual_trains': actual_trains,
                    'plan_classes_uid': plan.plan_classes_uid,
                    'status': plan_status,
                    'classes': plan.work_schedule_plan.classes.global_name
                }
            )
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
        # 配方信息
        ret_info = classes_plan.product_batching.get_product_batch
        ret = ret_info['material_name_weight']
        if not ret:
            raise ValidationError(f'mes中未找到该机型配方:{classes_plan.product_batching.stage_product_batch_no}')
        # 加载物料标准信息
        add_materials = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, useup_time__year='1970') \
            .order_by('id').values('id', 'material_name', 'bra_code', 'scan_material', 'init_weight', 'actual_weight',
                                   'adjust_left_weight')
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
                # 存在物料, 但是已经使用完
                used_up = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid,
                                                             material_name=material_name).last()
                if used_up:
                    single_material.update({'bra_code': used_up.bra_code, 'init_weight': used_up.init_weight,
                                            'used_weight': used_up.actual_weight,
                                            'scan_material': used_up.scan_material,
                                            'adjust_left_weight': used_up.adjust_left_weight, 'id': used_up.id,
                                            'msg': '物料：{}不足, 请扫码添加物料'.format(material_name)
                                            })
                else:
                    single_material.update(
                        {'bra_code': '', 'init_weight': 0, 'used_weight': 0, 'adjust_left_weight': 0,
                         'scan_material': ''})
                continue
            # 全部完成进料
            single_material.update({'bra_code': load_data['bra_code'], 'init_weight': load_data['init_weight'],
                                    'used_weight': load_data['actual_weight'],
                                    'scan_material': load_data['scan_material'],
                                    'adjust_left_weight': load_data['adjust_left_weight'], 'id': load_data['id']
                                    })
            # 判断物料是否够一车
            left = LoadTankMaterialLog.objects.filter(plan_classes_uid=plan_classes_uid, material_name=material_name) \
                .aggregate(left_weight=Sum('real_weight'))['left_weight']
            if not left:
                left = 0
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

    @atomic
    def update(self, request, *args, **kwargs):
        self.queryset = LoadTankMaterialLog.objects.all()
        left_weight = request.data.get('adjust_left_weight')
        batch_material = self.get_object()
        # 修改数量机台和使用机台不相同时, 不可修改
        last_bra_code_info = LoadTankMaterialLog.objects.filter(bra_code=batch_material.bra_code)
        if last_bra_code_info.last().plan_classes_uid != batch_material.plan_classes_uid:
            return response(success=False, message='该物料(条码)已在其他计划中使用, 本计划不可修改')
        if batch_material.unit == '包' and int(left_weight) != left_weight:
            return response(success=False, message='包数应为整数')
        update_records = last_bra_code_info.filter(plan_classes_uid=batch_material.plan_classes_uid)
        for records in update_records:
            serializer = self.get_serializer(records, data=request.data)
            if not serializer.is_valid():
                return response(success=False, message=list(serializer.errors.values())[0][0])
            # 获得本次修正量,修改真正计算的总量
            change_num = float(records.adjust_left_weight) - left_weight
            variety = float(records.variety) - change_num
            # 数量变换取值[累加](包数：[负整框:10], 重量：[负整框:100])
            beyond = 10 if records.unit == '包' else 100
            if variety > beyond or variety + float(records.init_weight) < 0:
                return response(success=False, message='修改值达到上限,不可修改')
            records.variety = float(records.variety) - change_num
            records.real_weight = float(records.real_weight) - change_num
            records.adjust_left_weight = records.real_weight
            records.useup_time = datetime.datetime.now() if left_weight == 0 else '1970-01-01 00:00:00'
            records.save()
            # 增加修改履历
            MaterialChangeLog.objects.create(**{'bra_code': records.bra_code,
                                                'material_name': records.material_name,
                                                'created_time': datetime.datetime.now(),
                                                'qty_change': -change_num})
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
        queryset = self.get_queryset().filter(equip_no=equip_no, batch_time__date=batch_time,
                                              batch_classes=batch_classes)
        serializer = self.get_serializer(queryset, many=True)
        return response(success=True, data=serializer.data)

    def create(self, request, *args, **kwargs):
        equip_no = self.request.data.get('equip_no')
        serializer = self.get_serializer(data=self.request.data, context={'request': request})
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
    filter_backends = [DjangoFilterBackend]

    def get_serializer_class(self):
        if self.action == 'create':
            return WeightPackageLogCreateSerializer
        elif self.action == 'update':
            return WeightPackageLogUpdateSerializer
        else:
            return WeightPackageLogSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return response(success=True, data=serializer.data)

    def list(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no') if self.request.query_params.get('equip_no') else 'F01'
        batch_time = self.request.query_params.get('batch_time') if self.request.query_params.get('batch_time') else \
            datetime.datetime.now().strftime('%Y-%m-%d')
        product_no = self.request.query_params.get('product_no')
        status = self.request.query_params.get('status', 'all')
        now_date = datetime.datetime.now().replace(microsecond=0)
        db_config = [k for k, v in DATABASES.items() if 'YK_XL' in v['NAME']]
        if equip_no not in db_config:
            return Response([])
        # mes网页请求
        plan_filter_kwargs = {'date_time': batch_time, 'actno__gte': 1}
        weight_filter_kwargs = {'equip_no': equip_no, 'batch_time__date': batch_time}
        if product_no:
            weight_filter_kwargs.update({'product_no': re.split(r'\(|\（|\[', product_no)[0]})
            plan_filter_kwargs.update({'recipe': product_no})
        # 获取称量系统生产计划数据
        equip_plan_info = Plan.objects.using(equip_no).filter(**plan_filter_kwargs)
        # 履历表中已生成的record(plan表主键)
        ids = list(set(self.get_queryset().filter(**weight_filter_kwargs).values_list('record', flat=True)))
        # 打印履历表为空(全是未打印数据)
        if not self.get_queryset():
            if status == 'Y':
                return Response([])
            else:
                page = self.paginate_queryset(list(equip_plan_info))
                if page:
                    serializer = WeightPackagePlanSerializer(page, many=True)
                    for i in serializer.data:
                        recipe_pre = RecipePre.objects.using(equip_no).filter(name=i['product_no'])
                        dev_type = recipe_pre.first().ver.upper().strip() if recipe_pre else ''
                        plan_weight = recipe_pre.first().weight if recipe_pre else 0
                        split_count = 1 if not recipe_pre else recipe_pre.first().split_count
                        # 配料时间
                        actual_batch_time = equip_plan_info.filter(planid=i['plan_weight_uid']).first().starttime
                        # 计算有效期
                        single_expire_record = PackageExpire.objects.filter(product_no=i['product_no'])
                        if not single_expire_record:
                            single_date = PackageExpire.objects.create(**{'product_no': i['product_no'],
                                                                          'product_name': i['product_no'],
                                                                          'update_user': 'system',
                                                                          'update_date': str(now_date.date())})
                        else:
                            single_date = single_expire_record.first()
                        expire_days = single_date.package_fine_usefullife if equip_no.startswith(
                            'F') else single_date.package_sulfur_usefullife
                        expire_datetime = datetime.datetime.strptime(actual_batch_time,
                                                                     '%Y-%m-%d %H:%M:%S') + timedelta(
                            days=expire_days) if expire_days != 0 else '9999-09-09 00:00:00'
                        total_weight = plan_weight
                        product_no_dev = re.split(r'\(|\（|\[', i['product_no'])[0]
                        if i['merge_flag']:
                            # 配方中料包重量
                            prod = ProductBatching.objects.filter(delete_flag=False, used_type=4,
                                                                  stage_product_batch_no=product_no_dev,
                                                                  dev_type__category_name=dev_type).first()
                            if prod and prod.weight_cnt_types.first():
                                total_weight = prod.weight_cnt_types.first().total_weight
                        # 公差查询
                        machine_tolerance = get_tolerance(batching_equip=equip_no, standard_weight=total_weight, project_name='all')
                        i.update({'plan_weight': plan_weight, 'equip_no': equip_no, 'dev_type': dev_type,
                                  'batch_time': actual_batch_time, 'product_no': product_no_dev,
                                  'batching_type': '机配', 'machine_weight': round(plan_weight / split_count, 3), 'manual_weight': 0,
                                  'batch_user': i['oper'], 'print_datetime': now_date.strftime('%Y-%m-%d %H:%M:%S'),
                                  'expire_datetime': expire_datetime, 'split_count': split_count,
                                  'machine_manual_weight': total_weight, 'machine_manual_tolerance': machine_tolerance,
                                  'expire_days': expire_days})
                    return self.get_paginated_response(serializer.data)
                return Response([])
        # 履历表不为空
        if status == 'all':
            # 已打印信息
            already_print = self.get_queryset().filter(**weight_filter_kwargs)
            # 未打印(剔除已打印)
            no_print_data = equip_plan_info.exclude(id__in=ids)
            # 分页返回
            page = self.paginate_queryset(list(already_print) + list(no_print_data))
            if page:
                data = []
                for k in page:
                    try:
                        # 已打印数据
                        y_or_n = k.status
                    except:
                        # 计划表中未打印数据
                        serializer = WeightPackagePlanSerializer(k).data
                        recipe_pre = RecipePre.objects.using(equip_no).filter(name=serializer['product_no'])
                        dev_type = recipe_pre.first().ver.upper().strip() if recipe_pre else ''
                        plan_weight = recipe_pre.first().weight if recipe_pre else 0
                        split_count = 1 if not recipe_pre else recipe_pre.first().split_count
                        actual_batch_time = equip_plan_info.filter(
                            planid=serializer['plan_weight_uid']).first().starttime
                        # 计算有效期
                        single_expire_record = PackageExpire.objects.filter(product_no=serializer['product_no'])
                        if not single_expire_record:
                            single_date = PackageExpire.objects.create(**{'product_no': serializer['product_no'],
                                                                          'product_name': serializer['product_no'],
                                                                          'update_user': 'system',
                                                                          'update_date': str(now_date.date())})
                        else:
                            single_date = single_expire_record.first()
                        expire_days = single_date.package_fine_usefullife if equip_no.startswith(
                            'F') else single_date.package_sulfur_usefullife
                        expire_datetime = datetime.datetime.strptime(actual_batch_time,
                                                                     '%Y-%m-%d %H:%M:%S') + timedelta(
                            days=expire_days) if expire_days != 0 else '9999-09-09 00:00:00'
                        total_weight = plan_weight
                        product_no_dev = re.split(r'\(|\（|\[', serializer['product_no'])[0]
                        if serializer['merge_flag']:
                            # 配方中料包重量
                            prod = ProductBatching.objects.filter(delete_flag=False, used_type=4,
                                                                  stage_product_batch_no=product_no_dev,
                                                                  dev_type__category_name=dev_type).first()
                            if prod and prod.weight_cnt_types.first():
                                total_weight = prod.weight_cnt_types.first().total_weight
                        # 公差查询
                        machine_tolerance = get_tolerance(batching_equip=equip_no, standard_weight=total_weight, project_name='all')
                        serializer.update({'equip_no': equip_no, 'dev_type': dev_type, 'plan_weight': plan_weight,
                                           'batch_time': actual_batch_time, 'product_no': product_no_dev,
                                           'batching_type': '机配', 'machine_weight': round(plan_weight / split_count, 3),
                                           'manual_weight': 0, 'batch_user': serializer['oper'],
                                           'print_datetime': now_date.strftime('%Y-%m-%d %H:%M:%S'),
                                           'expire_datetime': expire_datetime, 'expire_days': expire_days,
                                           'machine_manual_weight': total_weight, 'split_count': split_count,
                                           'machine_manual_tolerance': machine_tolerance})
                        data.append(serializer)
                    else:
                        # 已经打印数据数据更新(打印时完成了50包, 最终计划完成100包)
                        if k.package_fufil != k.package_plan_count:
                            get_status = Plan.objects.using(equip_no).filter(planid=k.plan_weight_uid).first()
                            k.package_fufil = get_status.actno
                            k.noprint_count = get_status.actno - k.package_count
                            k.save()
                        data.append(WeightPackageLogSerializer(k).data)
                return self.get_paginated_response(data)
            return Response([])
        # 未打印(剔除已打印)
        elif status == 'N':
            weight_filter_kwargs.update({'status': status})
            # 履历表中状态为未打印
            weight_no_print = self.get_queryset().filter(**weight_filter_kwargs)
            # 生产中剔除履历表中已经打印的
            plan_no_print = equip_plan_info.exclude(id__in=ids)
            # 分页返回
            page = self.paginate_queryset(list(weight_no_print) + list(plan_no_print))
            if page:
                data = []
                for k in page:
                    try:
                        # 已打印数据
                        y_or_n = k.status
                    except:
                        # 计划表中未打印数据
                        serializer = WeightPackagePlanSerializer(k).data
                        recipe_pre = RecipePre.objects.using(equip_no).filter(name=serializer['product_no'])
                        dev_type = recipe_pre.first().ver.upper().strip() if recipe_pre else ''
                        plan_weight = recipe_pre.first().weight if recipe_pre else 0
                        split_count = 1 if not recipe_pre else recipe_pre.first().split_count
                        actual_batch_time = equip_plan_info.filter(
                            planid=serializer['plan_weight_uid']).first().starttime
                        # 计算有效期
                        single_expire_record = PackageExpire.objects.filter(product_no=serializer['product_no'])
                        if not single_expire_record:
                            single_date = PackageExpire.objects.create(**{'product_no': serializer['product_no'],
                                                                          'product_name': serializer['product_no'],
                                                                          'update_user': 'system',
                                                                          'update_date': str(now_date.date())})
                        else:
                            single_date = single_expire_record.first()
                        expire_days = single_date.package_fine_usefullife if equip_no.startswith(
                            'F') else single_date.package_sulfur_usefullife
                        expire_datetime = datetime.datetime.strptime(actual_batch_time,
                                                                     '%Y-%m-%d %H:%M:%S') + timedelta(
                            days=expire_days) if expire_days != 0 else '9999-09-09 00:00:00'
                        total_weight = plan_weight
                        product_no_dev = re.split(r'\(|\（|\[', serializer['product_no'])[0]
                        if serializer['merge_flag']:
                            # 配方中料包重量
                            prod = ProductBatching.objects.filter(delete_flag=False, used_type=4,
                                                                  stage_product_batch_no=product_no_dev,
                                                                  dev_type__category_name=dev_type).first()
                            if prod and prod.weight_cnt_types.first():
                                total_weight = prod.weight_cnt_types.first().total_weight
                        # 公差查询
                        machine_tolerance = get_tolerance(batching_equip=equip_no, standard_weight=total_weight, project_name='all')
                        serializer.update({'equip_no': equip_no, 'dev_type': dev_type, 'plan_weight': plan_weight,
                                           'batch_time': actual_batch_time, 'product_no': product_no_dev,
                                           'batching_type': '机配', 'expire_days': expire_days,
                                           'machine_weight': round(plan_weight / split_count, 3), 'manual_weight': 0,
                                           'batch_user': serializer['oper'], 'split_count': split_count,
                                           'print_datetime': now_date.strftime('%Y-%m-%d %H:%M:%S'),
                                           'expire_datetime': expire_datetime, 'machine_manual_weight': total_weight,
                                           'machine_manual_tolerance': machine_tolerance})
                        data.append(serializer)
                    else:
                        # 已经打印数据数据更新(打印时完成了50包, 最终计划完成100包)
                        if k.package_fufil != k.package_plan_count:
                            get_status = Plan.objects.using(equip_no).filter(planid=k.plan_weight_uid).first()
                            k.package_fufil = get_status.actno
                            k.noprint_count = get_status.actno - k.package_count
                            k.save()
                        data.append(WeightPackageLogSerializer(k).data)
                return self.get_paginated_response(data)
            return Response([])
        # 已打印
        else:
            weight_filter_kwargs.update({'status': status})
            already_print = self.get_queryset().filter(**weight_filter_kwargs)
            for k in already_print:
                # 已经打印数据数据更新(打印时完成了50包, 最终计划完成100包)
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

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.print_flag not in [2, 3]:
            raise ValidationError('标签打印尚未完成, 请稍后重试')
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @atomic
    @action(methods=['post'], detail=False, permission_classes=[IsAuthenticated], url_path='manual_post',
            url_name='manual_post')
    def manual_post(self, request):
        """人工单配物料是否能扫入"""
        data = self.request.data
        merge_flag = data.get('merge_flag')
        product_no = data.get('product_no')
        dev_type = data.get('dev_type')
        scan_bra_code = data.get('scan_bra_code')
        machine_split_count = data.get('split_count')
        batching_equip = data.get('batching_equip', 'S01')
        machine_package_count = data.get('package_count')
        already_scan_info = data.get('manual_infos', [])
        if not merge_flag:
            raise ValidationError('称量计划未设置合包, 不可扫码')
        # 手工配料(配方)
        if scan_bra_code.startswith('MM'):
            manual = WeightPackageManual.objects.filter(bra_code=scan_bra_code).first()
            if not manual:
                raise ValidationError('未找到该人工配料条码')
            if manual.split_num != machine_split_count:
                raise ValidationError('分包数不一致, 无法合入')
            if manual.real_count == 0:
                raise ValidationError('该人工配料条码配置数量已经用完')
            # 判断物料配方是否一致
            if manual.product_no != product_no or manual.dev_type.category_name != dev_type:
                raise ValidationError('单种手工配料机型或配方不符合')
            # 返回人工配料id，关联使用
            try:
                manual_type, manual_id = self.scan_check(product_no, batching_equip, dev_type, machine_package_count, manual, already_scan_info)
            except Exception as e:
                raise ValidationError(e)
            details = WeightPackageManualSerializer(manual).data
        else:  # 原材料扫码
            try:
                res = material_out_barcode(scan_bra_code)
            except Exception as e:
                raise ValidationError(e)
            # res = {'ZL': 25, 'SM_CREATE': '2021-11-29 14:55:03', 'SL': 100, 'WLXXID': 'WLXX20100210111511609'} 测试数据
            if res:
                # 查询配方中人工配物料
                recipe_manual = get_manual_materials(product_no, dev_type, batching_equip)
                materials = set(recipe_manual.values_list('material_name', flat=True))
                # ERP绑定关系
                material_name_set = set(ERPMESMaterialRelation.objects.filter(zc_material__wlxxid=res['WLXXID'], use_flag=True).values_list('material__material_name', flat=True))
                if not material_name_set:
                    raise ValidationError('该物料未与MES原材料建立绑定关系！')
                comm_material = list(material_name_set & materials)
                if not comm_material:
                    raise ValidationError('未找到该物料在mes配方中对应的名称')
                # 获取配方中该物料重量
                detail = WeighBatchingDetail.objects.filter(material__material_name=comm_material[0]).first()
                if not detail:
                    raise ValidationError('配方中不存在该物料')
                standard_weight = detail.standard_weight
                # 新建记录
                record = WeightPackageWms.objects.filter(bra_code=scan_bra_code).last()
                single_weight = str(round(standard_weight / machine_split_count, 3))
                if not record:
                    record = WeightPackageWms.objects.create(**{'bra_code': scan_bra_code, 'material_name': comm_material[0],
                                                                'single_weight': single_weight, 'split_num': machine_split_count,
                                                                'package_count': machine_package_count,
                                                                'batch_time': res.get('SM_CREATE'),
                                                                'real_count': machine_package_count, 'now_package': res.get('SL')})
                    obj = record  # 原材料条码实例
                else:
                    obj = record
                    ids = [i['manual_id'] for i in already_scan_info if i['manual_type'] == 'manual_single' and {comm_material[0]} == set(i['names'])]
                    if record.id in ids:
                        raise ValueError('该条码已经扫过')
                    if record.now_package == 0:
                        raise ValidationError('该人工配料条码配置数量已经用完')
                    if record.package_count != machine_package_count:
                        new_record = WeightPackageWms.objects.create(**{'bra_code': scan_bra_code, 'material_name': comm_material[0],
                                                                        'single_weight': single_weight, 'split_num': machine_split_count,
                                                                        'package_count': machine_package_count,
                                                                        'batch_time': res.get('SM_CREATE'),
                                                                        'real_count': machine_package_count, 'now_package': record.now_package})
                        record.now_package = 0
                        record.save()
                        obj = new_record
                    # 判断是否足量
                    counts = WeightPackageWms.objects.filter(id__in=ids).aggregate(packages=Sum('now_package'))['packages']
                    already_count = 0 if not counts else counts
                    # 已经扫码的物料配置数量大于机配，不可扫码
                    if already_count >= machine_package_count * machine_split_count:
                        raise ValidationError('该人工条码内的物料配置数量已经足够')
                manual_type = 'manual_single'
                manual_id = obj.id
                details = {'material_name': comm_material[0], "single_weight": single_weight, 'batch_class': '',
                           'batch_group': '', 'created_username': '原材料', 'created_date': res.get('SM_CREATE')[:10],
                           'batch_type': '人工配', 'split_num': machine_split_count, 'package_count': machine_package_count,
                           'batch_time': res.get('SM_CREATE')[:10]}
            else:
                raise ValidationError('条码未找到对应信息')
        single_weight = Decimal(details['single_weight'].split('±')[0])
        # 手工配料总重
        detail_manual = sum([i['standard_weight'] for i in details['manual_details'] if
                             i['batch_type'] == '人工配']) if 'manual_details' in details else single_weight
        # 手工配料详情中的机配总重
        detail_machine = single_weight - detail_manual
        details.update({'detail_manual': detail_manual, 'detail_machine': detail_machine})
        results = {'manual_type': manual_type, 'manual_id': manual_id, 'details': details}
        return Response({'results': results})

    def scan_check(self, product_no, batching_equip, dev_type, machine_package_count, manual, already_scan_info, check_type='manual'):
        recipe_manual = get_manual_materials(product_no, dev_type, batching_equip)
        recipe_manual_names = recipe_manual.values_list('material_name', flat=True)
        scan_info = list(manual.package_details.all().values_list('material_name', flat=True))
        if set(scan_info) - set(recipe_manual_names):
            raise ValueError('手工条码内部分物料不在配方中')
        # 重量比较
        for item in manual.package_details.all():
            name, weight = item.material_name, item.standard_weight * manual.split_num
            info = recipe_manual.filter(material_name=name).first()
            if info.get('standard_weight') != weight:
                raise ValueError(f'手工条码中物料重量与配方不符:{name}')
        # 查找已经扫码物料中配料内容一致的总配置数量
        already_count = 0
        for i in already_scan_info:
            if i['manual_type'] == check_type:
                if set(scan_info) & set(i['names']) and set(scan_info) != set(i['names']):
                    raise ValueError('物料种类与之前扫入重叠但不一致')
                if set(scan_info) == set(i['names']):
                    if i['manual_id'] == manual.id:
                        raise ValueError('该条码已经扫过')
                    already_count += i['package_count']
        # 已经扫码的物料配置数量大于机配，不可扫码
        if already_count >= machine_package_count:
            raise ValidationError('该人工条码内的物料配置数量已经足够')
        return check_type, manual.id


@method_decorator([api_recorder], name="dispatch")
class WeightPackageManualViewSet(ModelViewSet):
    """
    list: 人工单配详情
    create: 新增人工单配
    retrieve: 打印详情
    update: 打印
    """
    queryset = WeightPackageManual.objects.all().order_by('-created_date')
    serializer_class = WeightPackageManualSerializer
    permission_classes = ()
    filter_backends = [DjangoFilterBackend]
    filter_class = WeightPackageManualFilter

    def get_permissions(self):
        if self.request.query_params.get('client'):
            return ()
        else:
            return (IsAuthenticated(),)

    @action(methods=['put'], detail=False, url_path='update_print_flag', url_name='update_print_flag')
    def update_print_flag(self, request):
        data = self.request.data
        self.get_queryset().filter(id=data.get('id')).update(**{'print_flag': data.get('print_flag', False)})
        return response(success=True, message='重置打印状态成功')


@method_decorator([api_recorder], name="dispatch")
class WeightPackageSingleViewSet(ModelViewSet):
    """
    list: 人工单配(单一物料:配方和通用)
    create: 新增人工单配(单一物料:配方和通用)
    retrieve: 打印详情
    update: 打印
    """
    queryset = WeightPackageSingle.objects.all().order_by('-created_date')
    serializer_class = WeightPackageSingleSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]
    filter_class = WeightPackageSingleFilter

    def get_permissions(self):
        if self.request.query_params.get('client'):
            return ()
        else:
            return (IsAuthenticated(),)

    @action(methods=['put'], detail=False, url_path='update_print_flag', url_name='update_print_flag')
    def update_print_flag(self, request):
        data = self.request.data
        self.get_queryset().filter(id=data.get('id')).update(**{'print_flag': data.get('print_flag', False)})
        return response(success=True, message='重置打印状态成功')


@method_decorator([api_recorder], name="dispatch")
class GetMaterialTolerance(APIView):
    """获取单个物料重量对应公差"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        data = self.request.query_params
        batching_equip = data.get('batching_equip')
        material_name = data.get('material_name')
        standard_weight = data.get('standard_weight')
        project_name = data.get('project_name', '单个化工重量')
        type_name = '硫磺' if batching_equip.startswith('S') else '细料'
        # 人工单配细料硫磺包
        if batching_equip:
            if '单个' not in project_name:
                project_name = f"整包{type_name}重量"
            rule = ToleranceRule.objects.filter(distinguish__keyword_name=f"{type_name}称量",
                                                project__keyword_name=project_name,
                                                small_num__lt=standard_weight, big_num__gte=standard_weight).first()
        # 人工单配配方或通用(所有量程)
        else:
            rule = ToleranceRule.objects.filter(distinguish__re_str__icontains=material_name).first()
        tolerance = f"{rule.handle.keyword_name}{rule.standard_error}{rule.unit}" if rule else ""
        return Response(tolerance)


@method_decorator([api_recorder], name="dispatch")
class GetManualInfo(APIView):
    """查询配方小料包中人工配物料种类与重量信息"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        data = self.request.query_params
        product_no, dev_type, batching_equip = data.get('product_no'), data.get('dev_type'), data.get('batching_equip')
        results = get_manual_materials(product_no, int(dev_type), batching_equip)
        return Response({'results': list(results)})


@method_decorator([api_recorder], name="dispatch")
class WeightPackageCViewSet(ListModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = WeightPackageLog.objects.all().order_by('-created_date')
    serializer_class = WeightPackageLogCUpdateSerializer

    def list(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no')
        equip_no_list = equip_no.split(',')
        print_data = self.get_queryset().filter(equip_no__in=equip_no_list, print_flag=1)
        serializer = []
        if print_data:
            serializer = WeightPackageLogSerializer(print_data, many=True).data
        return Response({"results": serializer})

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
        equip_list = [k for k, v in DATABASES.items() if 'YK_XL' in v.get('NAME')]
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
                                         update_user=self.request.user.username,
                                         update_date=datetime.datetime.now().date())
        # 读取数据
        data = PackageExpire.objects.all() if not filter_kwargs else PackageExpire.objects.filter(**filter_kwargs)
        res = list(
            data.values('id', 'product_no', 'product_name', 'package_fine_usefullife', 'package_sulfur_usefullife'))
        return Response(res)

    def post(self, request):
        record_id = self.request.data.pop('id', '')
        f_expire_time = self.request.data.get('package_fine_usefullife', '')
        s_expire_time = self.request.data.get('package_sulfur_usefullife', '')
        if not isinstance(record_id, int) or record_id < 0 or \
                not isinstance(f_expire_time, int) or f_expire_time < 0 or \
                not isinstance(s_expire_time, int) or s_expire_time < 0:
            raise ValidationError('参数错误')
        try:
            self.request.data.update(
                {'update_user': self.request.user.username, 'update_date': datetime.datetime.now().date()})
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

    def post(self, request):
        equip_no = self.request.data.get('equip_no')  # 机台
        recipe_name = self.request.data.get('recipe_name')  # 配方名称
        total_standard_error = self.request.data.get('total_standard_error')  # 总误差
        if not all([equip_no, recipe_name, total_standard_error]):
            raise ValidationError('参数缺失！')
        ret = re.match(r"(.*)[（|(](.*)[）|)]", recipe_name)
        if not ret:
            raise ValidationError('该配方名称不规范，请联系工艺员修改！')
        try:
            total_standard_error = float(total_standard_error)
        except Exception:
            raise ValidationError('误差值错误！')
        product_name = ret.group(1)
        dev_type = ret.group(2)
        product_batching = ProductBatching.objects.exclude(
            used_type=6).filter(stage_product_batch_no=product_name,
                                dev_type__category_no=dev_type,
                                batching_type=2).first()
        if not product_batching:
            raise ValidationError('该配方MES不存在或已废弃！')

        detail_list = []
        try:
            ret = list(RecipeMaterial.objects.using(equip_no).filter(recipe_name=recipe_name).values())
            for item in ret:
                m = Material.objects.filter(material_name=item['name'], delete_flag=0).first()
                if not m:
                    raise ValidationError('MES不存在此物料：{}'.format(item['name']))
                detail_list.append({"material": m,
                                    "standard_weight": item['weight'],
                                    "standard_error": round(item['error'], 2)}
                                   )
        except ConnectionDoesNotExist:
            raise ValidationError('称量机台{}服务错误！'.format(equip_no))
        except Exception:
            raise
        if 'S' in equip_no:
            cl_material = ProductBatchingDetail.objects.filter(product_batching=product_batching,
                                                               material__material_name='硫磺',
                                                               delete_flag=False).first()
        else:
            cl_material = ProductBatchingDetail.objects.filter(product_batching=product_batching,
                                                               material__material_name='细料',
                                                               delete_flag=False).first()
        if cl_material:
            qk_weight = float(cl_material.actual_weight)
            cl_weight = float(sum([i['standard_weight'] for i in detail_list]))
            if qk_weight // cl_weight == 1 and 0.98 * qk_weight < cl_weight < 1.02 * qk_weight:
                package_cnt = 1
            elif qk_weight // cl_weight == 1 and 0.5 * qk_weight < cl_weight < 0.85 * qk_weight:
                package_cnt = 1
            elif qk_weight // cl_weight == 2 and 0.98 * qk_weight < cl_weight * 2 < 1.02 * qk_weight:
                package_cnt = 2
            elif qk_weight // cl_weight == 2 and 0.65 * qk_weight < cl_weight * 2 < 0.85 * qk_weight:
                package_cnt = 2
            elif qk_weight // cl_weight == 2 and 0.98 * qk_weight < cl_weight * 2 < 1.02 * qk_weight:
                package_cnt = 2
            elif qk_weight // cl_weight == 3 and 0.65 * qk_weight < cl_weight * 3 < 0.85 * qk_weight:
                package_cnt = 3
            elif qk_weight // cl_weight == 3 and 0.65 * qk_weight < cl_weight * 3 < 0.85 * qk_weight:
                package_cnt = 3
            else:
                package_cnt = 1
                # raise ValidationError('小料配方重量错误，请联系工艺员确认！')
            cl_material.delete_flag = 1
            cl_material.save()
        else:
            package_cnt = 1

        defaults = {"package_cnt": package_cnt,
                    "total_standard_error": round(total_standard_error, 2),
                    "weigh_type": 1 if 'S' in equip_no else 2,
                    }
        kwargs = {"name": '硫磺' if 'S' in equip_no else '细料',
                  "product_batching": product_batching,
                  "delete_flag": False}
        weigh_cnt_type, _ = WeighCntType.objects.update_or_create(defaults=defaults, **kwargs)
        weigh_cnt_type.weight_details.all().delete()
        for detail in detail_list:
            detail['standard_weight'] *= package_cnt
            detail['weigh_cnt_type'] = weigh_cnt_type
            WeighBatchingDetail.objects.create(**detail)
        product_batching.used_type = 1
        product_batching.save()
        return Response('上传成功！')


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
            filter_kwargs['actno__gte'] = 1
        if batch_time:
            filter_kwargs['date_time'] = batch_time
        queryset = Plan.objects.using(equip_no).filter(**filter_kwargs).order_by('order_by')
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
class UpdateFlagCountView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        rid = self.request.data.get('id')
        oper_type = self.request.data.get('oper_type')
        equip_no = self.request.data.get('equip_no')
        merge_flag = self.request.data.get('merge_flag')
        split_count = self.request.data.get('split_count')
        filter_kwargs = {}
        if merge_flag is not None:
            filter_kwargs['merge_flag'] = merge_flag
        if split_count:
            filter_kwargs['split_count'] = split_count
        db_name = Plan if oper_type == '计划' else RecipePre
        instance = db_name.objects.using(equip_no).filter(id=rid)
        if not instance:
            raise ValidationError('未找到编号对应的数据')
        instance.update(**filter_kwargs)
        return Response('操作成功')


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
            dev_type = recipe_pre.first().ver.upper().strip() if recipe_pre else ''
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
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        equip_no = self.request.query_params.get('equip_no')
        # 从称量系统同步料罐状态到mes表中
        tank_status_sync = TankStatusSync(equip_no=equip_no)
        try:
            tank_status_sync.sync()
        except Exception as e:
            return response(success=False, message='mes同步称量系统料罐状态失败:{}'.format(e.args[0]))
        # 获取该机台号下所有料罐信息
        tanks_info = WeightTankStatus.objects.filter(equip_no=equip_no, use_flag=True) \
            .values('id', 'tank_no', 'tank_name', 'status', 'material_name', 'material_no', 'open_flag')
        return response(success=True, data=list(tanks_info))


@method_decorator([api_recorder], name='dispatch')
class CarbonTankSetViewSet(ModelViewSet):
    """
    list:
        炭黑罐投料重量设定信息
    update:
        炭黑罐投料重量设定
    """
    queryset = CarbonTankFeedWeightSet.objects.all()
    permission_classes = (IsAuthenticated,)
    pagination_class = None
    filter_class = CarbonTankSetFilter
    filter_backends = [DjangoFilterBackend]

    def get_serializer_class(self, *args, **kwargs):
        if self.action == 'list':
            return CarbonTankSetSerializer
        else:
            return CarbonTankSetUpdateSerializer


class PowderTankSettingViewSet(GenericViewSet, UpdateModelMixin, ListModelMixin):
    queryset = PowderTankSetting.objects.all()
    pagination_class = None
    serializer_class = PowderTankSettingSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        equip_no = self.request.query_params.get('equip_no')
        if equip_no:
            queryset = PowderTankSetting.objects.filter(equip_no=equip_no)
        else:
            queryset = super(PowderTankSettingViewSet, self).get_queryset()
        return queryset


@method_decorator([api_recorder], name='dispatch')
class PowderTankBatchingView(APIView):
    """
        粉料罐投料相关
    """

    def get(self, request):
        """根据料罐条形码获取料罐设定的物料信息"""
        tank_bar_code = self.request.query_params.get('tank_bar_code')
        try:
            tank = PowderTankSetting.objects.get(bar_code=tank_bar_code)
        except Exception:
            return response(success=False, message='未找到该粉料罐！')
        if not tank.material:
            return response(success=False, message='该料罐未设定原材料！')
        return response(success=True, data={"tank_no": tank.tank_no,
                                            "material_no": tank.material.material_no,
                                            "material_name": tank.material.material_name,
                                            "equip_no": tank.equip_no,
                                            'tank_bar_code': tank.bar_code
                                            })

    def post(self, request):
        """粉料罐投料"""
        tank_bar_code = self.request.data.get('tank_bar_code')  # 料罐条码
        material_bar_code = self.request.data.get('material_bar_code')  # 物料条码

        try:
            tank = PowderTankSetting.objects.get(bar_code=tank_bar_code)
        except Exception:
            return response(success=False, message='未找到该粉料罐！')

        if not tank.material:
            return response(success=False, message='该料罐未设定原材料！')

        try:
            # 查原材料出库履历查到原材料物料编码
            wms_stock = MaterialOutHistory.objects.using('wms').filter(
                lot_no=material_bar_code).values('material_no', 'material_name', 'weight', 'qty')
        except Exception:
            return response(success=False, message='连接WMS库失败，请联系管理员！')

        if not wms_stock:
            return response(success=False, message='未找到该物料出库记录，请联系管理员！')

        material_name_set = list(ERPMESMaterialRelation.objects.filter(
            zc_material__wlxxid=wms_stock[0]['material_no'],
            use_flag=True
        ).values_list('material__material_name', flat=True))

        if not material_name_set:
            return response(success=False, message='该物料未与MES原材料建立绑定关系！')
        if tank.material.material_name not in material_name_set:
            FeedingOperationLog.objects.create(
                feeding_type=1,
                feeding_time=datetime.datetime.now(),
                tank_bar_code=tank_bar_code,
                tank_material_name=tank.material.material_name,
                feeding_bar_code=material_bar_code,
                feeding_material_name=material_name_set[0],
                weight=wms_stock[0]['weight'],
                qty=wms_stock[0]['qty'],
                result=2
            )
            return response(success=False,
                            message='未找到符合料罐，不可以投料！',
                            data={'material_name': material_name_set[0]})
        else:
            # TODO 通知戴工那边的程序打开料罐门
            FeedingOperationLog.objects.create(
                feeding_type=1,
                feeding_time=datetime.datetime.now(),
                tank_bar_code=tank_bar_code,
                tank_material_name=tank.material.material_name,
                feeding_bar_code=material_bar_code,
                feeding_material_name=material_name_set[0],
                weight=wms_stock[0]['weight'],
                qty=wms_stock[0]['qty'],
                result=1
            )
            return response(success=True,
                            message='物料匹配，可以投料!',
                            data={'material_name': tank.material.material_name})


class OilTankSettingViewSet(GenericViewSet, UpdateModelMixin, ListModelMixin):
    queryset = OilTankSetting.objects.all()
    serializer_class = OilTankSettingSerializer
    pagination_class = None
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]


@method_decorator([api_recorder], name='dispatch')
class FeedCheckOperationViewSet(ModelViewSet):
    """
    list:
        查询投料防错操作履历
    """
    queryset = FeedingOperationLog.objects.all().order_by('id')
    serializer_class = FeedingOperationLogSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]
    filter_class = FeedingOperationLogFilter


@method_decorator([api_recorder], name='dispatch')
class FeedCapacityPlanView(APIView):
    """炭黑投料提示-计划显示"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        # 获取当前时间的工厂日期
        now = datetime.datetime.now()
        current_work_schedule_plan = WorkSchedulePlan.objects.filter(
            start_time__lte=now, end_time__gte=now,
            plan_schedule__work_schedule__work_procedure__global_name='密炼').first()
        date_now = str(current_work_schedule_plan.plan_schedule.day_time) if current_work_schedule_plan else str(
            now.date())
        classes_plans = ProductClassesPlan.objects.filter(~Q(status='完成'), delete_flag=False,
                                                          work_schedule_plan__plan_schedule__day_time=date_now) \
            .order_by('equip__equip_no')

        plan_actual_data = []
        for plan in classes_plans:
            # 获取机型配方
            product_batch = ProductBatching.objects.filter(
                stage_product_batch_no=plan.product_batching.stage_product_batch_no,
                used_type=4, batching_type=2).first()
            if not product_batch:
                continue
            # 任务状态
            plan_status_info = PlanStatus.objects.using("SFJ").filter(
                plan_classes_uid=plan.plan_classes_uid).order_by('created_date').last()
            plan_status = plan_status_info.status if plan_status_info else plan.status
            plan_actual_data.append(
                {
                    'id': plan.id,
                    'date_now': date_now,
                    'classes': plan.work_schedule_plan.classes.global_name,
                    'equip_no': plan.equip.equip_no,
                    'product_no': plan.product_batching.stage_product_batch_no,
                    'plan_trains': plan.plan_trains,
                    'status': plan_status
                }
            )
        return Response(plan_actual_data)


@method_decorator([api_recorder], name='dispatch')
class CarbonFeedingPromptViewSet(ModelViewSet):
    """
    list:
        展示炭黑罐投料提示信息
    retrieve:
        修改投料状态
    create:
        保存设定的投料信息
    """
    queryset = CarbonTankFeedingPrompt.objects.all()
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]

    def get_serializer_class(self):
        if self.action == 'create':
            return CarbonFeedingPromptCreateSerializer
        else:
            return CarbonFeedingPromptSerializer

    def list(self, request, *args, **kwargs):
        all = self.request.query_params.get('all')
        equip_ids = [self.request.query_params.get('equip_id')] if not all else Equip.objects.filter(
            delete_flag=False, use_flag=1, category__equip_type__global_name='密炼设备') \
            .values_list('equip_no', flat=True).order_by('equip_no')
        # 获取计划信息
        now = datetime.datetime.now()
        current_work_schedule_plan = WorkSchedulePlan.objects.filter(
            start_time__lte=now, end_time__gte=now,
            plan_schedule__work_schedule__work_procedure__global_name='密炼').first()
        date_now = str(current_work_schedule_plan.plan_schedule.day_time) if current_work_schedule_plan else str(
            now.date())
        classes_plans = ProductClassesPlan.objects.filter(
            ~Q(status='完成'), delete_flag=False, work_schedule_plan__plan_schedule__day_time=date_now)
        try:
            carbon_obj = CarbonDeliverySystem()
            tank_infos = carbon_obj.carbon_info()
        except Exception as e:
            raise ValidationError(f'同步炭黑罐信息失败: {e.args[0]}')
        res = {}
        # 加载炭黑设定
        carbon_set_info_list = CarbonTankFeedWeightSet.objects.all().values('tank_no', 'tank_capacity_type',
                                                                            'feed_capacity_low', 'feed_capacity_mid')
        for equip_id in equip_ids:
            if not tank_infos.get(equip_id):
                res[equip_id] = []
                continue
            # 加载罐料位信息
            tank_info = sorted(tank_infos.get(equip_id), key=lambda x: x['tank_no'])
            pre_tank_info = {i['tank_no']: i for i in tank_info}
            # 炭黑罐设定信息
            carbon_set_info = carbon_set_info_list.filter(equip_id=equip_id)
            if not carbon_set_info:
                raise ValidationError(f'机台未设定炭黑补料值：{equip_id}')
            pre_data = {i['tank_no']: i for i in carbon_set_info}
            recipes = set(classes_plans.filter(equip__equip_no=equip_id).values_list(
                'product_batching__stage_product_batch_no', flat=True))
            carbons = set(ProductBatchingDetail.objects.filter(product_batching__stage_product_batch_no__in=recipes,
                                                               product_batching__used_type=4,
                                                               product_batching__batching_type=2, delete_flag=False,
                                                               type=2)
                          .values_list('material__material_name', flat=True))
            # 提示有无数据变化不同
            query_set = self.get_queryset().filter(equip_id=equip_id).order_by('tank_no', 'id')
            data = self.get_serializer(query_set, many=True).data if query_set else tank_info
            for single_data in data:
                tank_no = single_data['tank_no']
                recv_tank = pre_tank_info[tank_no]
                set_tank = pre_data[tank_no]
                level = recv_tank['tank_level_status']
                if not query_set:
                    set_value = set_tank['feed_capacity_low'] if level == '低位' else (
                        set_tank['feed_capacity_mid'] if level == '中位' else 0)
                else:
                    if not single_data['feedcapacity_weight_set']:
                        set_value = set_tank['feed_capacity_low'] if level == '低位' else (
                            set_tank['feed_capacity_mid'] if level == '中位' else 0)
                    else:
                        set_value = single_data['feedcapacity_weight_set'] if level in ['低位', '中位'] else 0
                # 增加是否计划使用标识
                is_plan_used = {'is_plan_used': True} if recv_tank['tank_material_name'] in carbons else {
                    'is_plan_used': False}
                update_data = {'tank_material_name': recv_tank['tank_material_name'],
                               'feedcapacity_weight_set': set_value,
                               'tank_level_status': recv_tank['tank_level_status']} \
                    if query_set else {'id': 0, 'tank_capacity_type': set_tank['tank_capacity_type'], 'feed_status': 2,
                                       'feedcapacity_weight_set': set_value, 'feed_material_name': '', 'feed_change': 1,
                                       'feedport_code': ''}
                update_data.update(is_plan_used)
                single_data.update(update_data)
            res[equip_id] = sorted(data, key=lambda x: (x['tank_no'], x['id']))
        return Response(res)

    def create(self, request, *args, **kwargs):
        check_status = [i['feed_status'] for i in self.request.data]
        # 存在投料中状态放弃本次操作
        if 0 in check_status:
            raise ValidationError('有正在投料中的料罐, 本次操作不成功')
        # 保存的补料设定值不可大于炭黑罐重量设定的值
        for data in self.request.data:
            equip_id = data.get('equip_id')
            tank_no = data.get('tank_no')
            tank_level_status = data.get('tank_level_status')
            feedcapacity_weight_set = data.get('feedcapacity_weight_set')
            # 当前补料设定值
            set_info = CarbonTankFeedWeightSet.objects.filter(equip_id=equip_id, tank_no=tank_no).first()
            if not set_info:
                raise ValidationError(f'炭黑设定中无该机台信息:{equip_id}')
            set_value = set_info.feed_capacity_low if tank_level_status == '低位' else (
                set_info.feed_capacity_mid if tank_level_status == '中位' else 0)
            if feedcapacity_weight_set < 0 or feedcapacity_weight_set > set_value:
                raise ValidationError('保存的补料设定值不可大于炭黑罐重量设定的值')
        serializer = self.get_serializer(data=self.request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response('保存成功')

    def update(self, request, *args, **kwargs):
        status = self.request.data.get('feed_status')
        # 停止炭黑出库任务
        instance = self.get_object()
        # 非投料中不可操作
        if status == 1 and instance.feed_status != 0:
            raise ValidationError('非投料中状态不可操作')
        instance.feed_status = status
        instance.save()
        return Response('操作成功')


@method_decorator([api_recorder], name='dispatch')
class CarbonOutCheckView(APIView):
    """炭黑出库开始确认判定"""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        feed_status = self.request.data.get('feed_status')
        tank_no = self.request.data.get('tank_no')
        equip_id = self.request.data.get('equip_id')
        feedport_code = self.request.data.get('feedport_code')
        feed_material_name = self.request.data.get('feed_material_name')
        ex_warehouse_flag = self.request.data.get('ex_warehouse_flag')
        feedcapacity_weight_set = self.request.data.get('feedcapacity_weight_set')
        wlxxid = self.request.data.get('wlxxid')
        if feed_status == 0:
            raise ValidationError('该罐号正在投料中.')
        if not feedport_code or not feed_material_name:
            raise ValidationError('投料口或投入物料未选择')
        if feedcapacity_weight_set == 0:
            raise ValidationError('设定值为0不需要投料')
        record = CarbonTankFeedingPrompt.objects.filter(equip_id=equip_id, tank_no=tank_no, feedport_code=feedport_code)
        if not record or record.values()[0] != self.request.data:
            raise ValidationError('请先保存再点击开始')
        # 未选择出库, 更新投料状态即可
        if not ex_warehouse_flag:
            record.update(**{'feed_status': 1})
            return Response('NO')
        # 获取物料库存数量
        extra_where_str = " and c.MaterialCode like '%{}%'".format(wlxxid)
        sql = """SELECT
                         a.StockDetailState,
                         c.MaterialCode,
                         c.Name AS MaterialName,
                         a.BatchNo,
                         a.SpaceId,
                         a.Sn,
                         a.WeightOfActual,
                         a.WeightUnit,
                         a.CreaterTime
                        FROM
                         dbo.t_inventory_stock AS a
                         INNER JOIN t_inventory_space b ON b.Id = a.StorageSpaceEntityId
                         INNER JOIN t_inventory_material c ON c.MaterialCode= a.MaterialCode
                         INNER JOIN t_inventory_tunnel d ON d.TunnelCode= a.TunnelId 
                        WHERE
                         NOT EXISTS ( 
                             SELECT 
                                    tp.TrackingNumber 
                             FROM t_inventory_space_plan tp 
                             WHERE tp.TrackingNumber = a.TrackingNumber ) 
                         AND d.State= 1 
                         AND b.SpaceState= 1 
                         AND a.TunnelId IN ( 
                             SELECT 
                                    ab.TunnelCode 
                             FROM t_inventory_entrance_tunnel ab INNER JOIN t_inventory_entrance ac ON ac.Id= ab.EntranceEntityId 
                             ) {} order by a.CreaterTime""".format(extra_where_str)
        sc = SqlClient(sql=sql, **TH_CONF)
        temp = sc.all()
        if not temp:
            raise ValidationError(f'炭黑库存中无该物料: wlxxid {wlxxid}')
        # 托数
        pallets = len(temp)
        # 总重量
        total_weight = sum([i[6] for i in temp])
        return Response({'pallets': pallets, 'total_weight': total_weight})


@method_decorator([api_recorder], name='dispatch')
class CarbonOutTaskView(APIView):
    """下发炭黑出库任务"""

    def post(self, request):
        # 炭黑出库和解包房线体对应关系
        line_port = {'白炭黑': '库后出库站台6', '炭黑': '库后出库站台5', '掺混2-2号口': '库后出库站台4', '掺混2-1号口': '库后出库站台3',
                     '掺混1-2号口': '库后出库站台2', '掺混1-1号口': '库后出库站台1'}
        record_id = self.request.data.get('id')
        inventory_weight = self.request.data.get('total_weight')
        material_no = self.request.data.get('wlxxid')
        material_name = self.request.data.get('material_name')
        feedport_code = self.request.data.get('feedport_code')
        feedcapacity_weight_set = self.request.data.get('feedcapacity_weight_set')
        entrance_code = line_port.get(feedport_code)
        # 数量判断
        if feedcapacity_weight_set <= 0 or feedcapacity_weight_set > inventory_weight:
            raise ValidationError('投料重量应在已有库存范围内')
        # 下出库任务
        task_id = 'Mes' + str(int(round(time.time() * 1000)))
        rep_dict = out_task_carbon(task_id, entrance_code, material_no, material_name, feedcapacity_weight_set)
        if rep_dict.get("state") != 1:
            raise ValidationError(f'下发出库任务失败：{rep_dict.get("msg")}')
        # 更新状态
        CarbonTankFeedingPrompt.objects.filter(id=record_id).update(**{"feed_status": 0})
        return Response('下发出库任务成功')


@method_decorator([api_recorder], name='dispatch')
class FeedingErrorLampForCarbonView(APIView):
    """炭黑解包方请求mes防错结果"""

    def post(self, request):
        data = self.request.data
        line = data.get('LineNumber')
        task_id = data.get('MaterialBarCode')
        material_name = data.get('MaterialName')
        now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 线体与投料口关系
        line_port = {6: '白炭黑', 5: '炭黑', 4: '掺混2-2号口', 3: '掺混2-1号口', 2: '掺混1-2号口', 1: '掺混1-1号口'}
        feed_port = line_port.get(line)
        # 获取班次班组
        group = '早班' if '08:00:00' < now_time[-8:] < '20:00:00' else '夜班'
        record = WorkSchedulePlan.objects.filter(plan_schedule__day_time=now_time[:10], classes__global_name=group,
                                                 plan_schedule__work_schedule__work_procedure__global_name='密炼').first()
        classes_now = '' if not record else record.group.global_name
        feeding_class = f"{group}/{classes_now}"
        data = {'feeding_type': 2, 'feeding_port_no': feed_port, 'feeding_time': now_time,
                'feeding_material_name': material_name, 'feeding_username': self.request.user.username,
                'feed_reason': '', 'feeding_classes': feeding_class, 'feed_result': 'N'}
        # 通过物料条码获取炭黑数量与重量
        carbon_out_info = MaterialOutHistory.objects.using('cb').filter(order_no=task_id).first()
        if not carbon_out_info:
            data.update({'feed_reason': f'任务信息未找到{task_id}'})
            FeedingOperationLog.objects.create(**data)
            return Response({'state': 0, 'msg': f'任务信息未找到{task_id}', 'FeedingResult': 2})
        if carbon_out_info.lot_no:
            data['weight'] = carbon_out_info.weight
            data['qty'] = carbon_out_info.qty
            data['feeding_bar_code'] = carbon_out_info.lot_no
        else:
            data['weight'] = 0
            data['qty'] = 0
            data['feeding_bar_code'] = '99999999'
        # 获取当前输送线与炭黑罐关系
        try:
            carbon_obj = CarbonDeliverySystem()
            line_tank_info = carbon_obj.line_info()
        except Exception as e:
            data.update({'feed_reason': '获取输送线与炭黑罐信息失败'})
            FeedingOperationLog.objects.create(**data)
            return Response({'state': 0, 'msg': f'获取输送线与炭黑罐信息失败: {e.args[0]}', 'FeedingResult': 2})
        # 获取解包房信息(输送线与炭黑罐信息)
        unpack_room_info = {k: v for k, v in line_tank_info.items() if '解包房' in k and k.startswith(feed_port[:3])}
        # 判断该投入物料是否与输送线对应炭黑罐物料一致
        equip_id = unpack_room_info.get(feed_port[:3] + '解包房equip_id')
        tank_no = unpack_room_info.get(feed_port[:3] + '解包房tank_no')
        if equip_id == 0:
            data.update({'feed_reason': f'线路未设定机台号: {line}: {feed_port[:3]}'})
            FeedingOperationLog.objects.create(**data)
            return Response({'state': 0, 'msg': f'线路未设定机台号: {line}: {feed_port[:3]}', 'FeedingResult': 2})
        record = MaterialTankStatus.objects.using('SFJ').filter(delete_flag=False, tank_type="1", tank_no=tank_no,
                                                                use_flag=1, equip_no='Z%02d' % equip_id).first()
        if record.material_name != material_name:
            data.update({'tank_material_name': record.material_name,
                         'feed_reason': f'所投物料{material_name}与罐中{record.material_name}不一致'})
            FeedingOperationLog.objects.create(**data)
            return Response({'state': 0, 'msg': f'所投物料{material_name}与罐中{record.material_name}不一致', 'FeedingResult': 2})
        # 添加防错履历
        data.update({'tank_material_name': material_name, 'feed_result': 'Y'})
        FeedingOperationLog.objects.create(**data)
        return Response({'state': 0, 'msg': '防错合格', 'FeedingResult': 1})


@method_decorator([api_recorder], name='dispatch')
class FeedingOperateResultForCarbonView(APIView):
    """炭黑解包方回传投料结果"""

    def post(self, request):
        data = self.request.data
        line = data.get('LineNumber')
        task_id = data.get('MaterialBarCode')
        operate_result = data.get('OperateResult')
        # 线体与投料口关系
        line_port = {6: '白炭黑', 5: '炭黑', 4: '掺混2-2号口', 3: '掺混2-1号口', 2: '掺混1-2号口', 1: '掺混1-1号口'}
        feed_port = line_port.get(line)
        # 通过物料条码获取炭黑数量与重量
        carbon_out_info = MaterialOutHistory.objects.using('cb').filter(order_no=task_id).first()
        material_code = carbon_out_info.lot_no if carbon_out_info.lot_no else '99999999'
        # 更新任务状态
        CarbonTankFeedingPrompt.objects.filter(wlxxid=carbon_out_info.material_no,
                                               feedport_code=feed_port).update(**{'feed_status': 1})

        # 更新投料履历
        instance = FeedingOperationLog.objects.filter(feeding_type=2, feeding_bar_code=material_code,
                                                      feeding_port_no=feed_port).last()
        if not instance:
            return Response({'state': 0, 'msg': '未在履历中找到对应信息'})
        instance.result = operate_result
        instance.save()
        return Response({'state': 0, 'msg': '更新投料状态成功'})


@method_decorator([api_recorder], name='dispatch')
class MaterialInfoIssue(APIView):

    def post(self, request):
        equip_nos = self.request.data.get('equip_nos')
        material_id = self.request.data.get('material_id')
        try:
            m = Material.objects.get(id=material_id)
        except Exception:
            raise ValidationError('object does not exit!')
        error_equip = []
        for equip_no in equip_nos:
            try:
                if MaterialInfo.objects.using(equip_no).filter(name=m.material_name):
                    continue
                last_m_info = MaterialInfo.objects.using(equip_no).order_by('id').last()
                if last_m_info:
                    m_id = last_m_info.id + 1
                else:
                    m_id = 1
                MaterialInfo.objects.using(equip_no).create(
                    id=m_id,
                    name=m.material_name,
                    code=m.material_name,
                    remark='MES',
                    use_not=0,
                    time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
            except Exception:
                error_equip.append(equip_no)
        if error_equip:
            raise ValidationError('称量机台{}网络错误！'.format('、'.join(error_equip)))
        return Response('成功')


@method_decorator([api_recorder], name='dispatch')
class ReplaceMaterialViewSet(ModelViewSet):
    """
    list: 展示密炼投料替换物料信息(工艺确认)
    multi_update: 批量更新处理结果
    """
    queryset = ReplaceMaterial.objects.all().order_by('-last_updated_date', 'equip_no')
    serializer_class = ReplaceMaterialSerializer
    pagination_class = None
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ReplaceMaterialFilter

    def list(self, request, *args, **kwargs):
        choice = self.request.query_params.get('id')
        queryset = self.filter_queryset(self.get_queryset())
        if not choice:
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        else:
            instance = queryset.first()
            classes_plan = ProductClassesPlan.objects.filter(plan_classes_uid=instance.plan_classes_uid).first()
            if not classes_plan:
                raise ValidationError('该计划不存在')
            # 配方信息
            filter_kwargs = {}
            if instance.material_type == '胶块':
                filter_kwargs['material__material_type__global_name__in'] = ['合成胶', '天然胶', '再生胶']
            else:
                filter_kwargs['material__material_type__global_name'] = '料包'
            ret = classes_plan.product_batching.batching_details.filter(delete_flag=False, type=1,
                                                                        **filter_kwargs).values_list(
                'material__material_name', flat=True)
            if not ret:
                raise ValidationError(f'mes中未找到可选物料:{classes_plan.product_batching.stage_product_batch_no}')
            return Response({'results': list(ret)})

    @atomic
    @action(methods=['post'], detail=False, permission_classes=(IsAuthenticated,), url_path='multi_update',
            url_name='multi_update')
    def multi_update(self, request):
        opera_type = self.request.data.get('opera_type')
        data = self.request.data.get('update_material_list')
        for item in data:
            uid, recipe_material = item.pop('id'), item.get('recipe_material')
            if opera_type == "可投料":
                if not recipe_material:
                    raise ValidationError('选择配方物料才可投料')
                item['result'] = 1
            else:
                item['result'] = 0
            item['status'] = '已处理'
            self.get_queryset().filter(id=uid).update(**item)
        return Response('处理成功')


@method_decorator([api_recorder], name='dispatch')
class ReturnRubberViewSet(ModelViewSet):
    """
    list: 展示退回胶料打印
    multi_update: 批量更新处理结果
    """
    queryset = ReturnRubber.objects.all().order_by('-id')
    serializer_class = ReturnRubberSerializer
    pagination_class = None
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ReturnRubberFilter

    @action(methods=['post'], detail=False, url_path='print_return_rubber', url_name='print_return_rubber')
    def print_return_rubber(self, request):
        rid = self.request.data.get('id')
        status = self.request.data.get('status')
        self.get_queryset().filter(id=rid).update(status=status)
        return response(success=True, message='回正打印状态成功')


@method_decorator([api_recorder], name='dispatch')
class ToleranceKeyword(APIView):
    """公差标准[处理关键字定义、项目关键字定义、区分关键字定义]"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        data = self.request.query_params
        keyword_type = data.get('work_type')
        all = data.get('all')
        single = data.get('single')
        model_name = ToleranceDistinguish if keyword_type == '区分' else (
            ToleranceProject if keyword_type == '项目' else ToleranceHandle)
        if all:
            results = model_name.objects.all().values('id', 'keyword_name')
        elif single:
            results = model_name.objects.filter(keyword_name__in=['<', '≤', '<=']).values('id', 'keyword_name')
        else:
            results = model_name.objects.all().values()
        return Response({'results': list(results)})

    @atomic
    def post(self, request):
        data = self.request.data
        keyword_type = data.get('work_type')
        create_data = {'keyword_code': data.get('keyword_code'), 'keyword_name': data.get('keyword_name'),
                       'desc': data.get('desc'), 'created_user': self.request.user}
        if keyword_type == '区分':
            create_data.update({'re_str': data.get('re_str')})
            model_name = ToleranceDistinguish
        elif keyword_type == '项目':
            create_data.update({'special_standard': data.get('special_standard')})
            model_name = ToleranceProject
        else:
            model_name = ToleranceHandle
        instance = model_name.objects.create(**create_data)
        return Response(f'添加{keyword_type}关键字定义成功')

    @atomic
    def delete(self, request):
        data = self.request.data
        keyword_type = data.get('work_type')
        model_name = ToleranceDistinguish if keyword_type == '区分' else (
            ToleranceProject if keyword_type == '项目' else ToleranceHandle)
        instance = model_name.objects.filter(id=data.get('id')).first()
        flag = False
        for i in dir(instance):
            if i.endswith('_set') and eval(f'instance.{i}.all()'):
                flag = True
        if flag:
            raise ValidationError('该关键字定义已被引用, 无法删除')
        instance.delete()
        return Response(f'删除{keyword_type}关键字定义成功')


@method_decorator([api_recorder], name='dispatch')
class ToleranceRuleViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list: 技术标准-公差录入规则展示
    create: 技术标准-公差录入规则新增
    retrieve: 技术标准-公差录入规则详情
    update: 技术标准-公差录入规则修改
    destroy: 技术标准-公差录入规则停用
    """
    queryset = ToleranceRule.objects.all()
    serializer_class = ToleranceRuleSerializer
    pagination_class = None
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)


@method_decorator([api_recorder], name='dispatch')
class MaterialDetailsAux(APIView):
    """提供一个接口返回mes配方详情"""

    def get(self, request):
        plan_classes_uid = self.request.query_params.get('plan_classes_uid')
        from_mes = self.request.query_params.get('from_mes')
        classes_plan = ProductClassesPlan.objects.filter(plan_classes_uid=plan_classes_uid).first()
        if not classes_plan:
            return Response(f'未找到计划{plan_classes_uid}对应的配方详情')
        recipe_info = classes_plan.product_batching.get_product_batch.get('material_name_weight')
        res = [item.get('material__material_name') for item in recipe_info] if from_mes else recipe_info
        return Response(res)
