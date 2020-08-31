import json

import requests
from django.db.models import Sum
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from basics.views import CommonDeleteMixin
from mes.derorators import api_recorder
from mes.sync import ProductDayPlanSyncInterface
from plan.filters import ProductDayPlanFilter, MaterialDemandedFilter
from plan.serializers import ProductDayPlanSerializer
from plan.models import ProductDayPlan, ProductClassesPlan, MaterialDemanded
from rest_framework.views import APIView


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
class MaterialDemandedAPIView(ListAPIView):
    """原材料需求量展示，plan_date参数必填"""

    queryset = MaterialDemanded.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialDemandedFilter

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

    def post(self, request):
        product_day_id = self.request.query_params.get('product_day_id')
        print(product_day_id)
        if not product_day_id:
            raise ValidationError('缺失参数')
        try:
            product_day = ProductDayPlan.objects.get(id=int(product_day_id))
        except Exception:
            raise ValidationError('该计划不存在')
        interface = ProductDayPlanSyncInterface(instance=product_day)
        try:
            interface.request()
        except Exception as e:
            raise ValidationError(e)
        return Response('发送成功', status=status.HTTP_200_OK)


@method_decorator([api_recorder], name="dispatch")
class MaterialDemandedView(APIView):
    """计划原材料需求列表"""

    def get(self, request):
        # 条件筛选
        params = request.query_params
        filter_dict = {}
        plan_date = params.get('plan_date')
        classes = params.get('classes')
        product_no = params.get('product_no')
        if plan_date:
            filter_dict['work_schedule_plan__plan_schedule__day_time'] = plan_date  # TODO 前端必须一开始就穿一个日期
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

        md_list = MaterialDemanded.objects.filter(**filter_dict).values(
            'product_classes_plan__product_day_plan__product_batching__stage_product_batch_no',
            'work_schedule_plan__classes__global_name',
            'material__material_no',
            'material__material_name',
            'material__material_type__global_name',
        ).annotate(demanded=Sum('material_demanded'))
        res = []
        for md_detail_list in md_list:
            md = {}
            md['product_no'] = md_detail_list[
                'product_classes_plan__product_day_plan__product_batching__stage_product_batch_no']
            md['classes'] = md_detail_list['work_schedule_plan__classes__global_name']
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
        return Response({'results': res})
