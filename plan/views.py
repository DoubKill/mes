
from django.db.models import Sum
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework import status
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from basics.views import CommonDeleteMixin
from mes.derorators import api_recorder
from plan.filters import ProductDayPlanFilter, ProductBatchingDayPlanFilter, MaterialDemandedFilter
from plan.serializers import ProductDayPlanSerializer, ProductBatchingDayPlanSerializer, \
    ProductDayPlanCopySerializer, ProductBatchingDayPlanCopySerializer, MaterialRequisitionClassesSerializer
from plan.models import ProductDayPlan, ProductClassesPlan, MaterialDemanded, ProductBatchingDayPlan, \
    ProductBatchingClassesPlan, MaterialRequisitionClasses
from rest_framework.views import APIView
from plan.uuidfield import UUidTools


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
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filter_class = ProductDayPlanFilter
    ordering_fields = ['id', 'equip__category__equip_type__global_name']

    def destroy(self, request, *args, **kwargs):
        """"胶料计划删除 先删除胶料计划，随后删除胶料计划对应的班次日计划和原材料需求量表"""
        instance = self.get_object()
        for pcp_obj in instance.pdp_product_classes_plan.all():
            MaterialDemanded.objects.filter(
                plan_classes_uid=pcp_obj.plan_classes_uid).update(delete_flag=True,
                                                                  delete_user=request.user)
        ProductClassesPlan.objects.filter(product_day_plan=instance).update(delete_flag=True, delete_user=request.user)

        instance.delete_flag = True
        instance.delete_user = request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name="dispatch")
class ProductBatchingDayPlanViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        配料小料日计划列表
    create:
        新建配料小料日计划(这里的增是单增)
    update:
        修改配料小料日计划
    destroy:
        删除配料小料日计划
    """
    queryset = ProductBatchingDayPlan.objects.filter(delete_flag=False)
    serializer_class = ProductBatchingDayPlanSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filter_class = ProductBatchingDayPlanFilter
    ordering_fields = ['id', 'equip__category__equip_type__global_name']

    def destroy(self, request, *args, **kwargs):
        """"删除配料小料计划  随后还要删除配料小料的日班次计划和原材料需求量计划"""
        instance = self.get_object()
        for pbcp_obj in instance.pdp_product_batching_classes_plan.all():
            MaterialDemanded.objects.filter(
                plan_classes_uid=pbcp_obj.plan_classes_uid).update(delete_flag=True,
                                                                   delete_user=request.user)
        ProductBatchingClassesPlan.objects.filter(product_batching_day_plan=instance).update(delete_flag=True,
                                                                                             delete_user=request.user)

        instance.delete_flag = True
        instance.delete_user = request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name="dispatch")
class ProductBatchingDayPlanManyCreate(APIView):
    """配料小料计划群增接口"""

    def post(self, request, *args, **kwargs):
        if isinstance(request.data, dict):
            many = False
        elif isinstance(request.data, list):
            many = True
        else:
            return Response(data={'detail': '数据有误'}, status=400)
        s = ProductBatchingDayPlanSerializer(data=request.data, many=many, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.validated_data)


@method_decorator([api_recorder], name="dispatch")
class ProductDayPlanManyCreate(APIView):
    """胶料计划群增接口"""

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
class MaterialRequisitionClassesViewSet(CommonDeleteMixin, ModelViewSet):
    """暂时都没用得到 先留着
    list:
        领料日班次计划列表
    create:
        新建领料日班次计划
    update:
        修改领料日班次计划
    destroy:
        删除领料日班次计划
    """
    queryset = MaterialRequisitionClasses.objects.filter(delete_flag=False)
    serializer_class = MaterialRequisitionClassesSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend, OrderingFilter)

    def perform_create(self, serializer):
        serializer.save(created_user=self.request.user, plan_classes_uid=UUidTools.uuid1_hex())

    def perform_update(self, serializer):
        serializer.save(last_updated_user=self.request.user)


@method_decorator([api_recorder], name="dispatch")
class MaterialDemandedAPIView(ListAPIView):
    """原材料需求量展示，plan_date参数必填"""

    queryset = MaterialDemanded.objects.all()
    filter_backends = (DjangoFilterBackend, )
    filter_class = MaterialDemandedFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        data = queryset.filter(**kwargs).select_related('material', 'classes__classes').\
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
class ProductDayPlanCopyView(CreateAPIView):
    """复制胶料日计划"""
    serializer_class = ProductDayPlanCopySerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)


@method_decorator([api_recorder], name="dispatch")
class ProductBatchingDayPlanCopyView(CreateAPIView):
    """复制配料小料日计划"""
    serializer_class = ProductBatchingDayPlanCopySerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
