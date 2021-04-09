import datetime
import json

import requests
from django.db import connection
from django.db.models import Sum, Max
from django.db.transaction import atomic
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, mixins
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, GenericAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from basics.models import WorkSchedulePlan
from basics.views import CommonDeleteMixin
from mes.common_code import get_weekdays
from mes.derorators import api_recorder
from mes.paginations import SinglePageNumberPagination
from mes.sync import ProductClassesPlanSyncInterface
from plan.filters import ProductDayPlanFilter, MaterialDemandedFilter, PalletFeedbacksFilter, BatchingClassesPlanFilter
from plan.models import ProductDayPlan, ProductClassesPlan, MaterialDemanded, BatchingClassesPlan, \
    BatchingClassesEquipPlan
from plan.serializers import ProductDayPlanSerializer, ProductClassesPlanManyCreateSerializer, \
    ProductBatchingSerializer, ProductBatchingDetailSerializer, ProductDayPlansySerializer, \
    ProductClassesPlansySerializer, MaterialsySerializer, BatchingClassesPlanSerializer, \
    IssueBatchingClassesPlanSerializer, BatchingClassesEquipPlanSerializer, PlantImportSerializer
from production.models import PlanStatus, TrainsFeedbacks
from recipe.models import ProductBatching, ProductBatchingDetail, Material
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
            return Response("请求库存失败", status=400)
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
    filter_class = PalletFeedbacksFilter


@method_decorator([api_recorder], name="dispatch")
class IndexView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        # 当前一周的日期
        dates = get_weekdays(7)

        # 计划数据
        plan_data = ProductClassesPlan.objects.filter(
            work_schedule_plan__plan_schedule__day_time__in=dates,
            delete_flag=False).values(
            'work_schedule_plan__plan_schedule__day_time').annotate(plan_trains=Sum('plan_trains'))
        plan_data_dict = {str(item['work_schedule_plan__plan_schedule__day_time']): item for item in plan_data}

        # 计划uid列表
        plan_uid_list = list(ProductClassesPlan.objects.filter(
            work_schedule_plan__plan_schedule__day_time__in=dates,
            delete_flag=False).values_list('plan_classes_uid', flat=True))
        max_actual_ids = TrainsFeedbacks.objects.filter(
            plan_classes_uid__in=plan_uid_list
        ).values('plan_classes_uid').annotate(max_id=Max('id')).values_list('max_id', flat=True)
        if max_actual_ids:
            sql = """select
                       sum(actual_trains) as actual_trains,
                       ps.day_time
                from
                    trains_feedbacks tf
                inner join product_classes_plan pcp on pcp.plan_classes_uid=tf.plan_classes_uid
                inner join work_schedule_plan wsp on pcp.work_schedule_plan_id = wsp.id
                inner join plan_schedule ps on wsp.plan_schedule_id = ps.id
                where
                      tf.id in ({}) 
                group by ps.day_time;""".format(','.join([str(i) for i in max_actual_ids]))
            cursor = connection.cursor()
            cursor.execute(sql)
            actual_data = cursor.fetchall()
            actual_data_dict = {str(item[1])[:10]: int(item[0]) for item in actual_data}
        else:
            actual_data_dict = {}
        ret = {}
        cur_month_plan = cur_month_actual = 0
        for date in dates:
            ret[date] = {'plan_trains': 0, 'actual_trains': 0}
            if date in plan_data_dict:
                ret[date]['plan_trains'] = plan_data_dict[date]['plan_trains']
                cur_month_plan += plan_data_dict[date]['plan_trains']
            if date in actual_data_dict:
                ret[date]['actual_trains'] = actual_data_dict[date]
                cur_month_actual += actual_data_dict[date]

        return Response({'cur_month_plan': cur_month_plan,
                         'cur_month_actual': cur_month_actual,
                         'result': ret})


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
    permission_classes = (IsAuthenticated,)
