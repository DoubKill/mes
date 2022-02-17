import datetime
import json
import re

import requests
from django.db import connection, IntegrityError
from django.db.models import Sum, Max
from django.db.transaction import atomic
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, GenericAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from basics.models import WorkSchedulePlan, GlobalCode, Equip
from basics.views import CommonDeleteMixin
from equipment.utils import gen_template_response
from inventory.models import ProductStockDailySummary
from mes.common_code import get_weekdays
from mes.derorators import api_recorder
from mes.paginations import SinglePageNumberPagination
from mes.permissions import PermissionClass
from mes.sync import ProductClassesPlanSyncInterface
from plan.filters import ProductDayPlanFilter, MaterialDemandedFilter, ProductClassesPlanFilter, \
    BatchingClassesPlanFilter, SchedulingRecipeMachineSettingFilter, SchedulingProductDemandedDeclareSummaryFilter, \
    SchedulingProductSafetyParamsFilter, SchedulingProductDemandedDeclareFilter, ProductStockDailySummaryFilter
from plan.models import ProductDayPlan, ProductClassesPlan, MaterialDemanded, BatchingClassesPlan, \
    BatchingClassesEquipPlan, SchedulingParamsSetting, SchedulingRecipeMachineSetting, SchedulingEquipCapacity, \
    SchedulingWashRule, SchedulingWashPlaceKeyword, SchedulingWashPlaceOperaKeyword, SchedulingProductDemandedDeclare, \
    SchedulingProductDemandedDeclareSummary, SchedulingProductSafetyParams, SchedulingResult, \
    SchedulingEquipShutDownPlan
from plan.serializers import ProductDayPlanSerializer, ProductClassesPlanManyCreateSerializer, \
    ProductBatchingSerializer, ProductBatchingDetailSerializer, ProductDayPlansySerializer, \
    ProductClassesPlansySerializer, MaterialsySerializer, BatchingClassesPlanSerializer, \
    IssueBatchingClassesPlanSerializer, BatchingClassesEquipPlanSerializer, PlantImportSerializer, \
    SchedulingParamsSettingSerializer, SchedulingRecipeMachineSettingSerializer, SchedulingEquipCapacitySerializer, \
    SchedulingWashRuleSerializer, SchedulingWashPlaceKeywordSerializer, SchedulingWashPlaceOperaKeywordSerializer, \
    RecipeMachineWeightSerializer, SchedulingProductDemandedDeclareSerializer, \
    SchedulingProductDemandedDeclareSummarySerializer, SchedulingProductSafetyParamsSerializer, \
    SchedulingResultSerializer, SchedulingEquipShutDownPlanSerializer, ProductStockDailySummarySerializer
from plan.utils import calculate_product_plan_trains, extend_last_aps_result, APSLink, \
    calculate_equip_recipe_avg_mixin_time
from production.models import PlanStatus, TrainsFeedbacks, MaterialTankStatus
from quality.utils import get_cur_sheet, get_sheet_data
from recipe.models import ProductBatching, ProductBatchingDetail, Material, MaterialAttribute
from system.serializers import PlanReceiveSerializer


@method_decorator([api_recorder], name="dispatch")
class ProductDayPlanViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        胶料日计划列表
    create:
        新建胶料日计划（单增），暂且不用，
    update:
        修改原胶料日计划
    destroy:
        删除胶料日计划
    """
    queryset = ProductDayPlan.objects.filter(delete_flag=False).select_related(
        'equip__category', 'plan_schedule', 'product_batching').prefetch_related(
        'pdp_product_classes_plan__work_schedule_plan', 'pdp_product_batching_day_plan')
    serializer_class = ProductDayPlanSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filter_class = ProductDayPlanFilter
    ordering_fields = ['id', 'equip__category__equip_type__global_name']

    def destroy(self, request, *args, **kwargs):
        """"胶料计划删除 先删除胶料计划，随后删除胶料计划对应的班次日计划和原材料需求量表"""
        instance = self.get_object()
        MaterialDemanded.objects.filter(
            product_classes_plan__product_day_plan=instance).delete()
        ProductClassesPlan.objects.filter(product_day_plan=instance).update(delete_flag=True, delete_user=request.user)
        instance.delete_flag = True
        instance.delete_user = request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name="dispatch")
class ProductDayPlanManyCreate(APIView):
    """胶料计划群增接口"""
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        if isinstance(request.data, dict):
            many = False
        elif isinstance(request.data, list):
            many = True
        else:
            return Response(data={'detail': '数据有误'}, status=400)
        s = ProductDayPlanSerializer(data=request.data, many=many, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response('新建成功')


@method_decorator([api_recorder], name="dispatch")
class MaterialDemandedAPIView(ListAPIView):
    """原材料需求量展示，plan_date参数必填"""

    queryset = MaterialDemanded.objects.filter(delete_flag=False).all()
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialDemandedFilter
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        data = queryset.filter(**kwargs).select_related('material', 'classes__classes'). \
            values('material__material_name', 'material__material_no',
                   'material__material_type__global_name', 'work_schedule_plan__classes__global_name'
                   ).annotate(num=Sum('material_demanded'))
        materials = []
        ret = {}
        for item in data:
            if item['material__material_name'] not in materials:
                ret[item['material__material_name']] = {
                    'material_no': item['material__material_no'],
                    'material_name': item['material__material_name'],
                    "material_type": item['material__material_type__global_name'],
                    "class_details": {item['work_schedule_plan__classes__global_name']: item['num']}}
                materials.append(item['material__material_name'])
            else:
                ret[item['material__material_name']
                ]['class_details'][item['work_schedule_plan__classes__global_name']] = item['num']
        page = self.paginate_queryset(list(ret.values()))
        return self.get_paginated_response(page)


@method_decorator([api_recorder], name="dispatch")
class ProductDayPlanAPiView(APIView):
    """计划数据下发至上辅机"""
    permission_classes = ()
    authentication_classes = ()

    @atomic()
    def post(self, request):
        equip = request.data.get('equip', None)
        work_schedule_plan = request.data.get('work_schedule_plan', None)
        if not equip or not work_schedule_plan:
            raise ValidationError('缺失参数')
        try:
            product_classes_plan_set = ProductClassesPlan.objects.filter(equip_id=equip,
                                                                         work_schedule_plan_id=work_schedule_plan,
                                                                         delete_flag=False)
        except Exception:
            raise ValidationError('该计划不存在')
        for product_classes_plan in product_classes_plan_set:

            # 当前班次之前的计划不准现在下发
            work_schedule_plan = product_classes_plan.work_schedule_plan
            end_time = work_schedule_plan.end_time
            now_time = datetime.datetime.now()
            if now_time > end_time:
                raise ValidationError(
                    f'{end_time.strftime("%Y-%m-%d")}的{work_schedule_plan.classes.global_name}的计划不允许现在下发给上辅机')

            if product_classes_plan.status not in ['已保存', '等待']:
                continue
            else:
                interface = ProductClassesPlanSyncInterface(instance=product_classes_plan)
                try:
                    interface.request()
                except Exception as e:
                    raise ValidationError(e)
                product_classes_plan.status = '等待'
                product_classes_plan.save()
                PlanStatus.objects.filter(plan_classes_uid=product_classes_plan.plan_classes_uid).update(status='等待')
        return Response('下达成功', status=status.HTTP_200_OK)


@method_decorator([api_recorder], name="dispatch")
class MaterialDemandedView(APIView):
    """计划原材料需求列表"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        # 条件筛选
        params = request.query_params
        filter_dict = {'delete_flag': False}
        plan_date = params.get('plan_date')
        classes = params.get('classes')
        product_no = params.get('product_no')
        if plan_date:
            filter_dict['work_schedule_plan__plan_schedule__day_time'] = plan_date
        if classes:
            filter_dict['work_schedule_plan__classes__global_name'] = classes
        if product_no:
            filter_dict[
                'product_classes_plan__product_day_plan__product_batching__stage_product_batch_no__icontains'] = product_no

        # 库存请求
        material_inventory_dict = {}
        try:
            ret = requests.get("http://49.235.45.128:8169/storageSpace/GetInventoryCount")
            ret_json = json.loads(ret.text)
            for i in ret_json.get("datas"):
                material_inventory_dict[i['materialCode']] = i
        except Exception as e:
            pass
        try:
            page = int(params.get("page", 1))
            page_size = int(params.get("page_size", 10))
        except Exception as e:
            return Response("page和page_size必须是int", status=400)
        md_list = MaterialDemanded.objects.filter(**filter_dict).values(
            'product_classes_plan__product_batching__stage_product_batch_no',
            'work_schedule_plan',
            'material__material_no',
            'material__material_name',
            'material__material_type__global_name',
        ).annotate(demanded=Sum('material_demanded'))
        counts = md_list.count()
        md_list = md_list[(page - 1) * page_size:page_size * page]
        res = []
        for md_detail_list in md_list:
            md = {}
            md['product_no'] = md_detail_list[
                'product_classes_plan__product_batching__stage_product_batch_no']
            md['classes'] = WorkSchedulePlan.objects.get(id=md_detail_list['work_schedule_plan']).classes.global_name
            md['material_no'] = md_detail_list['material__material_no']
            md['material_name'] = md_detail_list['material__material_name']
            md['material_type'] = md_detail_list['material__material_type__global_name']
            md['material_demanded'] = md_detail_list['demanded']
            # 库存
            inventory_detail = material_inventory_dict.get(md.get('material_no'))
            if inventory_detail:
                quantity = inventory_detail.get('quantity')
                weightOfActual = inventory_detail.get('weightOfActual')
                unit_weight = weightOfActual / quantity  # TODO 单位重量到底是总重量除以总数量还是计件数量 这个计件数量到底是什么意思
                md['qty'] = quantity
                md['total_weight'] = weightOfActual
                md['unit_weight'] = unit_weight
                md['need_unit_weight'] = unit_weight
                md['need_qty'] = md['material_demanded'] / unit_weight
            else:
                md['qty'] = None
                md['total_weight'] = None
                md['unit_weight'] = None
                md['need_unit_weight'] = None
                md['need_qty'] = None
            res.append(md)
        return Response({'results': res, 'count': counts})


@method_decorator([api_recorder], name="dispatch")
class ProductClassesPlanManyCreate(APIView):
    """胶料日班次计划群增接口"""

    permission_classes = (IsAuthenticated,)

    @atomic()
    def post(self, request, *args, **kwargs):
        if isinstance(request.data, dict):
            day_time = WorkSchedulePlan.objects.filter(
                id=request.data['work_schedule_plan']).first().plan_schedule.day_time
            schedule_no = WorkSchedulePlan.objects.filter(
                id=request.data['work_schedule_plan']).first().plan_schedule.work_schedule.schedule_no
            pcp_set = ProductClassesPlan.objects.filter(work_schedule_plan__plan_schedule__day_time=day_time,
                                                        equip_id=request.data['equip'], delete_flag=False,
                                                        work_schedule_plan__plan_schedule__work_schedule__schedule_no=schedule_no).all()
            for pcp_obj in pcp_set:
                pcp_obj.delete_flag = True
                pcp_obj.save()
                PlanStatus.objects.filter(plan_classes_uid=pcp_obj.plan_classes_uid).update(delete_flag=True)
                MaterialDemanded.objects.filter(product_classes_plan=pcp_obj).update(delete_flag=True)
            return Response('操作成功')
        elif isinstance(request.data, list):
            many = True
            work_list = []
            plan_list = []
            equip_list = []
            for class_dict in request.data:
                work_list.append(class_dict['work_schedule_plan'])
                schedule_no = WorkSchedulePlan.objects.filter(
                    id=class_dict['work_schedule_plan']).first().plan_schedule.work_schedule.schedule_no
                plan_list.append(class_dict['plan_classes_uid'])
                equip_list.append(class_dict['equip'])
                class_dict['status'] = '已保存'
                # 判断胶料日计划是否存在
                wsp_obj = WorkSchedulePlan.objects.filter(id=class_dict['work_schedule_plan']).first()
                pdp_obj = ProductDayPlan.objects.filter(equip_id=class_dict['equip'],
                                                        product_batching_id=class_dict['product_batching'],
                                                        plan_schedule=wsp_obj.plan_schedule, delete_flag=False).first()
                if pdp_obj:
                    class_dict['product_day_plan'] = pdp_obj.id

                else:
                    class_dict['product_day_plan'] = ProductDayPlan.objects.create(equip_id=class_dict['equip'],
                                                                                   product_batching_id=class_dict[
                                                                                       'product_batching'],
                                                                                   plan_schedule=wsp_obj.plan_schedule,
                                                                                   last_updated_date=datetime.datetime.now(),
                                                                                   created_date=datetime.datetime.now()).id
            # 举例说明：本来有四条 前端只传了三条 就会删掉多余的一条
            day_time = WorkSchedulePlan.objects.filter(
                id=class_dict['work_schedule_plan']).first().plan_schedule.day_time
            pcp_set = ProductClassesPlan.objects.filter(work_schedule_plan__plan_schedule__day_time=day_time,
                                                        equip_id__in=equip_list, delete_flag=False,
                                                        work_schedule_plan__plan_schedule__work_schedule__schedule_no=schedule_no).exclude(
                plan_classes_uid__in=plan_list)
            for pcp_obj in pcp_set:
                # 删除前要先判断该数据的状态是不是非等待，只要等待中的计划才可以删除
                plan_status = PlanStatus.objects.filter(plan_classes_uid=pcp_obj.plan_classes_uid,
                                                        delete_flag=False).order_by(
                    'created_date').last()
                if plan_status:
                    if plan_status.status not in ['等待', '已保存']:
                        raise ValidationError("只要等待中或者已保存的计划才可以删除")
                else:
                    pass

                # 删除多余的数据已经以及向关联的计划状态变更表和原材料需求量表需求量表
                pcp_obj.delete_flag = True
                pcp_obj.save()
                PlanStatus.objects.filter(plan_classes_uid=pcp_obj.plan_classes_uid).update(delete_flag=True)
                MaterialDemanded.objects.filter(product_classes_plan=pcp_obj).update(delete_flag=True)
            s = ProductClassesPlanManyCreateSerializer(data=request.data, many=many,
                                                       context={'request': request})
            s.is_valid(raise_exception=True)
            s.save()
            return Response('保存成功')
        else:
            return Response(data={'detail': '数据有误'}, status=400)


@method_decorator([api_recorder], name="dispatch")
class ProductClassesPlanList(mixins.ListModelMixin, GenericViewSet):
    """计划新增展示数据"""
    queryset = ProductClassesPlan.objects.filter(delete_flag=False).order_by('sn')
    serializer_class = ProductClassesPlanManyCreateSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = SinglePageNumberPagination
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductClassesPlanFilter


@method_decorator([api_recorder], name="dispatch")
class PlanReceive(CreateAPIView):
    """
        接受上辅机计划数据接口
        """
    # permission_classes = ()
    # authentication_classes = ()
    permission_classes = (IsAuthenticated,)
    serializer_class = PlanReceiveSerializer
    queryset = ProductDayPlan.objects.all()

    @atomic()
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


@method_decorator([api_recorder], name="dispatch")
class ProductBatchingReceive(CreateAPIView):
    """胶料配料标准同步"""
    serializer_class = ProductBatchingSerializer
    queryset = ProductBatching.objects.all()


@method_decorator([api_recorder], name="dispatch")
class ProductBatchingDetailReceive(CreateAPIView):
    """胶料配料标准详情同步"""
    serializer_class = ProductBatchingDetailSerializer
    queryset = ProductBatchingDetail.objects.all()


@method_decorator([api_recorder], name="dispatch")
class ProductDayPlanReceive(CreateAPIView):
    """胶料日计划表同步"""
    serializer_class = ProductDayPlansySerializer
    queryset = ProductDayPlan.objects.all()


@method_decorator([api_recorder], name="dispatch")
class ProductClassesPlanReceive(CreateAPIView):
    """胶料日班次计划表同步"""
    serializer_class = ProductClassesPlansySerializer
    queryset = ProductClassesPlan.objects.all()


@method_decorator([api_recorder], name="dispatch")
class MaterialReceive(CreateAPIView):
    """原材料表同步"""
    serializer_class = MaterialsySerializer
    queryset = Material.objects.all()


@method_decorator([api_recorder], name="dispatch")
class BatchingClassesPlanView(ModelViewSet):
    """配料日班次计划"""
    queryset = BatchingClassesPlan.objects.filter(delete_flag=False).order_by('-created_date')
    serializer_class = BatchingClassesPlanSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = BatchingClassesPlanFilter

    def perform_update(self, serializer):
        serializer.save(package_changed=True)


@method_decorator([api_recorder], name="dispatch")
class BatchingClassesEquipPlanViewSet(ModelViewSet):
    """配料日班次计划"""
    queryset = BatchingClassesEquipPlan.objects.order_by('-id')
    serializer_class = BatchingClassesEquipPlanSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('batching_class_plan', )
    pagination_class = None

    def create(self, request, *args, **kwargs):
        if not isinstance(request.data, list):
            raise ValidationError('参数错误')
        for item in request.data:
            s = BatchingClassesEquipPlanSerializer(data=item, context={'request': request})
            if not s.is_valid():
                raise ValidationError(s.errors)
            s.save()
        return Response('新建成功')

    def perform_update(self, serializer):
        serializer.save(package_changed=True)


@method_decorator([api_recorder], name="dispatch")
class IssueBatchingClassesPlanView(UpdateAPIView):
    queryset = BatchingClassesPlan.objects.filter(delete_flag=False)
    serializer_class = IssueBatchingClassesPlanSerializer
    permission_classes = (IsAuthenticated,)

    def perform_update(self, serializer):
        serializer.save(send_user=self.request.user)


@method_decorator([api_recorder], name="dispatch")
class PlantImportView(CreateAPIView):
    serializer_class = PlantImportSerializer
    queryset = ProductClassesPlan.objects.all()
    permission_classes = (IsAuthenticated, PermissionClass({'add': 'add_productdayplan'}))


@method_decorator([api_recorder], name="dispatch")
class LabelPlanInfo(APIView):
    """根据计划编号，获取工厂日期和班组"""

    def get(self, request):
        plan_classes_uid = self.request.query_params.get('planid')  # 计划uid
        produce_time = self.request.query_params.get('producetime')  # 生产时间
        try:
            produce_time = datetime.datetime.strptime(produce_time, "%Y-%m-%d %H:%M:%S")
        except Exception:
            raise ValidationError('produce_time日期格式错误')
        ret = {'factory_date': '', 'group': '', 'expire_time': ''}
        plan = ProductClassesPlan.objects.filter(plan_classes_uid=plan_classes_uid).first()
        if plan:
            ret['factory_date'] = plan.work_schedule_plan.plan_schedule.day_time
            ret['group'] = plan.work_schedule_plan.group.global_name
            material_detail = MaterialAttribute.objects.filter(
                material__material_no=plan.product_batching.stage_product_batch_no).first()
            if material_detail:
                unit = material_detail.validity_unit
                if unit in ["天", "days", "day"]:
                    param = {"days": material_detail.period_of_validity}
                elif unit in ["小时", "hours", "hour"]:
                    param = {"hours": material_detail.period_of_validity}
                else:
                    param = {"days": material_detail.period_of_validity}
                expire_time = (produce_time + datetime.timedelta(**param)).strftime('%Y-%m-%d %H:%M:%S')
                ret['expire_time'] = expire_time
        elif produce_time:
            current_work_schedule_plan = WorkSchedulePlan.objects.filter(
                start_time__lte=produce_time,
                end_time__gte=produce_time,
                plan_schedule__work_schedule__work_procedure__global_name='密炼'
            ).first()
            if current_work_schedule_plan:
                ret['factory_date'] = current_work_schedule_plan.plan_schedule.day_time
                ret['group'] = current_work_schedule_plan.group.global_name
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class SchedulingParamsSettingView(ModelViewSet):
    queryset = SchedulingParamsSetting.objects.all()
    serializer_class = SchedulingParamsSettingSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = None


@method_decorator([api_recorder], name="dispatch")
class SchedulingRecipeMachineSettingView(ModelViewSet):
    queryset = SchedulingRecipeMachineSetting.objects.order_by('rubber_type', 'stage', 'product_no')
    serializer_class = SchedulingRecipeMachineSettingSerializer
    pagination_class = None
    # permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = SchedulingRecipeMachineSettingFilter

    @action(methods=['post'], detail=False)
    def import_xlsx(self, request):
        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        # if cur_sheet.ncols != 7:
        #     raise ValidationError('导入文件数据错误！')
        data = get_sheet_data(cur_sheet, start_row=3)
        for item in data:
            if not all([item[0], item[1], item[2], item[3], item[5]]):
                raise ValidationError('必填数据缺失')
            try:
                SchedulingRecipeMachineSetting.objects.update_or_create(
                    defaults={"mixing_main_machine": item[3],
                              "mixing_vice_machine": item[4],
                              "final_main_machine": item[5],
                              "final_vice_machine": item[6]},
                    **{"rubber_type": item[0], "product_no": item[2], "stage": item[1]}
                )
            except Exception:
                raise
        return Response('ok')


@method_decorator([api_recorder], name="dispatch")
class RecipeMachineWeight(ListAPIView):
    queryset = ProductBatching.objects.all()
    serializer_class = RecipeMachineWeightSerializer

    def get_queryset(self):
        equip_no = self.request.query_params.get('equip_no')
        dev_type = self.request.query_params.get('dev_type')
        product_no = self.request.query_params.get('product_no')
        query_kwargs = {}
        if equip_no:
            query_kwargs['equip__equip_no'] = equip_no
        if dev_type:
            query_kwargs['dev_type__category_name'] = dev_type
        if product_no:
            query_kwargs['stage_product_batch_no__icontains'] = product_no
        return ProductBatching.objects.using('SFJ').exclude(
            used_type=6).filter(**query_kwargs).filter(
            batching_type=1, stage__global_name__in=['FM', '3MB', '2MB', '2MB', 'HMB']
        ).values('id', 'equip__equip_no', 'stage_product_batch_no', 'batching_weight').order_by('equip__equip_no')


@method_decorator([api_recorder], name="dispatch")
class MaterialTankStatusView(APIView):

    def get(self, request):
        tank_type = self.request.query_params.get('tank_type', '1')
        data = MaterialTankStatus.objects.filter(
            tank_no__in=[str(i) for i in range(11)],
            tank_type=tank_type,
            equip_no__in=['Z01', 'Z02', 'Z03', 'Z04', 'Z05', 'Z06', 'Z07', 'Z08', 'Z09', 'Z10']
        ).using('SFJ').values('equip_no', 'tank_no', 'material_name').order_by('equip_no', 'tank_no')
        ret = {}
        equip_nos = set()
        for item in data:
            equip_nos.add(item['equip_no'])
            if item['tank_no'] not in ret:
                ret[item['tank_no']] = {'tank_no': item['tank_no'], item['equip_no']: item['material_name']}
            else:
                ret[item['tank_no']][item['equip_no']] = item['material_name']
        return Response({'equip_nos': sorted(list(equip_nos)), 'data': list(ret.values())})


@method_decorator([api_recorder], name="dispatch")
class SchedulingEquipCapacityViewSet(ModelViewSet):
    queryset = SchedulingEquipCapacity.objects.order_by('equip_no', 'product_no')
    serializer_class = SchedulingEquipCapacitySerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filter_fields = ('equip_no', 'product_no')
    ordering_fields = ['avg_mixing_time', 'avg_interval_time', 'avg_rubbery_quantity']
    FILE_NAME = '机台设备生产能力'
    EXPORT_FIELDS_DICT = {'机台': 'equip_no',
                          '胶料编码': 'product_no',
                          '平均工作时间(秒）': 'avg_mixing_time',
                          '平均间隔时间(秒）': 'avg_interval_time',
                          '平均加胶量(kg)': 'avg_rubbery_quantity',
                          '录入者': 'created_username',
                          '录入时间': 'created_date',
                          }

    def list(self, request, *args, **kwargs):
        export = self.request.query_params.get('export')
        queryset = self.filter_queryset(self.get_queryset())
        if export:
            data = self.get_serializer(queryset, many=True).data
            return gen_template_response(self.EXPORT_FIELDS_DICT, data, self.FILE_NAME)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@method_decorator([api_recorder], name="dispatch")
class SchedulingWashRuleViewSet(CommonDeleteMixin, ModelViewSet):
    queryset = SchedulingWashRule.objects.order_by('-id')
    serializer_class = SchedulingWashRuleSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    pagination_class = None


@method_decorator([api_recorder], name="dispatch")
class SchedulingWashPlaceKeywordViewSet(ModelViewSet):
    queryset = SchedulingWashPlaceKeyword.objects.order_by('id')
    serializer_class = SchedulingWashPlaceKeywordSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    pagination_class = None


@method_decorator([api_recorder], name="dispatch")
class SchedulingWashPlaceOperaKeywordViewSet(ModelViewSet):
    queryset = SchedulingWashPlaceOperaKeyword.objects.order_by('id')
    serializer_class = SchedulingWashPlaceOperaKeywordSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    pagination_class = None


@method_decorator([api_recorder], name="dispatch")
class SchedulingProductDemandedDeclareViewSet(ModelViewSet):
    queryset = SchedulingProductDemandedDeclare.objects.order_by('id')
    serializer_class = SchedulingProductDemandedDeclareSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = SchedulingProductDemandedDeclareFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        data = self.get_paginated_response(serializer.data).data
        sum_data = queryset.aggregate(total_today_demanded=Sum('today_demanded'),
                                      total_tomorrow_demanded=Sum('tomorrow_demanded'),
                                      total_current_stock=Sum('current_stock'),
                                      total_underway_stock=Sum('underway_stock'))
        data['total_today_demanded'] = sum_data['total_today_demanded']
        data['total_tomorrow_demanded'] = sum_data['total_tomorrow_demanded']
        data['total_current_stock'] = sum_data['total_current_stock']
        data['total_underway_stock'] = sum_data['total_underway_stock']
        return Response(data)

    def create(self, request, *args, **kwargs):
        data = self.request.data
        order_no = 'FC{}'.format(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
        if not isinstance(data, list):
            raise ValidationError('data error')
        s = self.serializer_class(data=data, many=True, context={'request': request, 'order_no': order_no})
        s.is_valid(raise_exception=True)
        s.save()
        return Response('ok')


@method_decorator([api_recorder], name="dispatch")
class SchedulingProductSafetyParamsViewSet(CommonDeleteMixin, ModelViewSet):
    queryset = SchedulingProductSafetyParams.objects.order_by('id')
    serializer_class = SchedulingProductSafetyParamsSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = SchedulingProductSafetyParamsFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        data = self.get_paginated_response(serializer.data).data
        sum_data = queryset.aggregate(total_safety_stock=Sum('safety_stock'),
                                      total_daily_usage=Sum('daily_usage'))
        data['total_safety_stock'] = sum_data['total_safety_stock']
        data['total_daily_usage'] = sum_data['total_daily_usage']
        return Response(data)


@method_decorator([api_recorder], name="dispatch")
class ProductDeclareSummaryViewSet(ModelViewSet):
    queryset = SchedulingProductDemandedDeclareSummary.objects.order_by('sn')
    serializer_class = SchedulingProductDemandedDeclareSummarySerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = SchedulingProductDemandedDeclareSummaryFilter
    pagination_class = None

    @action(methods=['post'], detail=False, url_path='up-sequence')
    def up_sequence(self, request):
        try:
            instance = SchedulingProductDemandedDeclareSummary.objects.get(id=self.request.data.get('id'))
        except Exception:
            raise ValidationError('object does not exits!')
        sn = instance.sn
        previous_instance = SchedulingProductDemandedDeclareSummary.objects.filter(
            factory_date=instance.factory_date, sn__lt=instance.sn).order_by('sn').last()
        if previous_instance:
            instance.sn = previous_instance.sn
            previous_instance.sn = sn
            instance.save()
            previous_instance.save()
        return Response('成功')

    @action(methods=['post'], detail=False, url_path='down-sequence')
    def down_sequence(self, request):
        try:
            instance = SchedulingProductDemandedDeclareSummary.objects.get(id=self.request.data.get('id'))
        except Exception:
            raise ValidationError('object does not exits!')
        sn = instance.sn
        next_instance = SchedulingProductDemandedDeclareSummary.objects.filter(
            factory_date=instance.factory_date, sn__gt=instance.sn).order_by('sn').first()
        if next_instance:
            instance.sn = next_instance.sn
            next_instance.sn = sn
            instance.save()
            next_instance.save()
        return Response('成功')


class SchedulingResultViewSet(ModelViewSet):
    queryset = SchedulingResult.objects.order_by('id')
    serializer_class = SchedulingResultSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    pagination_class = None

    @atomic()
    def create(self, request, *args, **kwargs):
        schedule_no = self.request.data.get('schedule_no')
        plan_data = self.request.data.get('plan_data')
        if not all([schedule_no, plan_data]):
            raise ValidationError('参数缺失！')
        sr = SchedulingResult.objects.filter(schedule_no=schedule_no).first()
        factory_date = sr.factory_date
        SchedulingResult.objects.filter(schedule_no=schedule_no).delete()
        for key, value in plan_data.items():
            for idx, item in enumerate(value):
                if not item.get('recipe_name') or not item.get('plan_trains'):
                    continue
                SchedulingResult.objects.create(
                    factory_date=factory_date,
                    schedule_no=schedule_no,
                    equip_no=key,
                    sn=idx+1,
                    recipe_name=item['recipe_name'],
                    time_consume=item['time_consume'] if item['time_consume'] else 0,
                    plan_trains=item['plan_trains'],
                    desc=item['desc']
                )
        return Response('成功')

    @action(methods=['get'], detail=False)
    def schedule_nos(self, request):
        factory_date = self.request.query_params.get('factory_date')
        query_set = SchedulingResult.objects.all()
        if factory_date:
            query_set = query_set.filter(factory_date=factory_date)
        return Response(set(query_set.values_list('schedule_no', flat=True)))

    def list(self, request, *args, **kwargs):
        schedule_no = self.request.query_params.get('schedule_no')
        if not schedule_no:
            raise ValidationError('请输入排程单号！')
        ret = {}
        for equip in Equip.objects.filter(
                category__equip_type__global_name='密炼设备'
        ).order_by('equip_no'):
            ret[equip.equip_no] = {'data': [], 'dev_type': equip.category.category_name}
        queryset = self.get_queryset().filter(schedule_no=schedule_no)
        for instance in queryset:
            ret[instance.equip_no]['data'].append(self.get_serializer(instance).data)
        return Response(ret)

    @action(methods=['post'], detail=False)
    def import_xlx(self, request):
        factory_date = self.request.data.get('factory_date')
        schedule_no = 'APS1{}'.format(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        current_sheet = get_cur_sheet(excel_file)
        for j in range(2):
            i = 0
            while 1:
                col_index = i * 4 + 1
                if col_index >= 61:
                    break
                try:
                    equip_data = current_sheet.cell(0, col_index).value.strip()
                    if not equip_data:
                        break
                    ret = re.search(r'Z\d+', equip_data)
                    equip_no = ret.group()
                    if len(equip_no) < 3:
                        equip_no = 'Z' + '0{}'.format(equip_no[-1])
                except IndexError:
                    break
                except Exception:
                    raise ValidationError('机台格式错误')
                for rowNum in range(j * 25 + 2, 25 * (j + 1)):
                    try:
                        value = current_sheet.row_values(rowNum)[i * 4 + 1:(i + 1) * 4 + 1]
                    except IndexError:
                        continue
                    product_no = value[0].strip()
                    plan_trains = value[1]
                    if not all([product_no, plan_trains]):
                        continue
                    note = value[3].strip()
                    try:
                        plan_trains = int(plan_trains)
                    except ValueError:
                        raise ValidationError('机台：{}， 胶料规格:{}，车次信息错误，请修改后重试！'.format(equip_no, value[0]))
                    pb = ProductBatching.objects.exclude(used_type__in=[6, 7]).filter(stage_product_batch_no__icontains='-{}'.format(product_no)).first()
                    if pb:
                        product_no = pb.stage_product_batch_no
                    train_time_consume = calculate_equip_recipe_avg_mixin_time(equip_no, product_no)
                    SchedulingResult.objects.create(
                        factory_date=factory_date,
                        schedule_no=schedule_no,
                        equip_no=equip_no,
                        sn=1,
                        recipe_name=product_no,
                        time_consume=round(train_time_consume*plan_trains/3600, 1),
                        plan_trains=plan_trains,
                        desc=note
                    )
                i += 1
            j += 1
        return Response('ok')


@method_decorator([api_recorder], name="dispatch")
class SchedulingEquipShutDownPlanViewSet(ModelViewSet):
    queryset = SchedulingEquipShutDownPlan.objects.all()
    serializer_class = SchedulingEquipShutDownPlanSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)

    def get_queryset(self):
        queryset = self.queryset
        factory_date = self.request.query_params.get('factory_date')
        if factory_date:
            queryset = queryset.filter(begin_time__date=factory_date)
        return queryset


@method_decorator([api_recorder], name="dispatch")
class SchedulingProceduresView(APIView):

    @atomic()
    def post(self, request):
        factory_date = self.request.data.get('factory_date')
        if not factory_date:
            raise ValidationError('参数缺失！')
        try:
            factory_date = datetime.datetime.strptime(factory_date, "%Y-%m-%d")
        except Exception:
            raise ValidationError('参数错误！')
        while 1:
            schedule_no = 'APS1{}'.format(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
            if not SchedulingResult.objects.filter(schedule_no=schedule_no).exists():
                break

        # 继承前一天排程未完成的计划
        extend_last_aps_result(factory_date, schedule_no)

        equip_nos = Equip.objects.filter(category__equip_type__global_name='密炼设备').values_list('equip_no', flat=True).order_by('equip_no')
        links = [APSLink(equip_no, schedule_no) for equip_no in range(len(equip_nos))]
        link_dict = {equip_no: links[idx] for idx, equip_no in enumerate(equip_nos)}

        for instance in SchedulingProductDemandedDeclareSummary.objects.filter(factory_date=factory_date).order_by('sn'):
            need_weight = round(instance.plan_weight - instance.workshop_weight - instance.current_stock, 1)
            if need_weight <= 0:
                continue
            try:
                data = calculate_product_plan_trains(factory_date,
                                                     instance.product_no,
                                                     need_weight)
            except Exception as e:
                raise ValidationError(e)
            for item in data:
                instance = link_dict[item['equip_no']]
                instance.append(item)
        for i in links:
            ret = i.travel()
            for item in ret:
                # SchedulingRecipeMachineRelationHistory.objects.create(
                #     schedule_no=schedule_no,
                #     equip_no=item['equip_no'],
                #     recipe_name=item['product_no'],
                #     batching_weight=item['batching_weight'],
                #     devoted_weight=item['devoted_weight'],
                #     dev_type=item['dev_type'],
                # )
                SchedulingResult.objects.create(
                    sn=1,
                    factory_date=factory_date,
                    schedule_no=schedule_no,
                    equip_no=item['equip_no'],
                    recipe_name=item['product_no'],
                    time_consume=item['consume_time'],
                    plan_trains=item['plan_trains']
                )
        return Response('ok')


@method_decorator([api_recorder], name="dispatch")
class SchedulingStockSummary(ModelViewSet):
    queryset = ProductStockDailySummary.objects.filter(stage__in=('HMB', 'CMB', '1MB', '2MB', '3MB')).order_by('product_no')
    serializer_class = ProductStockDailySummarySerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductStockDailySummaryFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data
        ret = {}
        for item in data:
            if item['product_no'] not in ret:
                ret[item['product_no']] = {'product_no': item['product_no'],
                                           item['stage']: item['stock_weight']}
            else:
                ret[item['product_no']][item['stage']] = item['stock_weight']
        return Response(ret.values())