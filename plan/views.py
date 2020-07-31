from django.shortcuts import render
from django.db.models import Sum
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from collections import OrderedDict

from basics.models import GlobalCode
from basics.views import CommonDeleteMixin
from mes.derorators import api_recorder
from plan.filters import ProductDayPlanFilter, MaterialDemandedFilter, ProductBatchingDayPlanFilter
from plan.serializers import ProductDayPlanSerializer, MaterialDemandedSerializer, ProductBatchingDayPlanSerializer, \
    MaterialRequisitionSerializer, ProductDayPlanCopySerializer, ProductBatchingDayPlanCopySerializer,MaterialRequisitionCopySerializer
from plan.models import ProductDayPlan, ProductClassesPlan, MaterialDemanded, ProductBatchingDayPlan, \
    MaterialRequisition


# Create your views here.

@method_decorator([api_recorder], name="dispatch")
class ProductDayPlanViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        胶料日计划列表
    create:
        新建胶料日计划
    update:
        修改原胶料日计划
    destroy:
        删除胶料日计划
    """
    queryset = ProductDayPlan.objects.filter(delete_flag=False)
    serializer_class = ProductDayPlanSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductDayPlanFilter


@method_decorator([api_recorder], name="dispatch")
class MaterialDemandedViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        原材料需求量列表
    create:
        新建原材料需求量
    update:
        修改原材料需求量
    destroy:
        删除原材料需求量
    """
    queryset = MaterialDemanded.objects.filter(delete_flag=False)
    serializer_class = MaterialDemandedSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialDemandedFilter


@method_decorator([api_recorder], name="dispatch")
class ProductBatchingDayPlanViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        配料小料日计划列表
    create:
        新建配料小料日计划
    update:
        修改配料小料日计划
    destroy:
        删除配料小料日计划
    """
    queryset = ProductBatchingDayPlan.objects.filter(delete_flag=False)
    serializer_class = ProductBatchingDayPlanSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductBatchingDayPlanFilter


# TODO:暂时是错的 等待明天讨论
@method_decorator([api_recorder], name="dispatch")
class MaterialRequisitionViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        领料日计划列表
    create:
        新建领料日计划
    update:
        修改领料日计划
    destroy:
        删除领料日计划
    """
    queryset = MaterialRequisition.objects.filter(delete_flag=False)
    serializer_class = MaterialRequisitionSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    # filter_backends = (DjangoFilterBackend,)
    # filter_class = MaterialDemandedFilter


@method_decorator([api_recorder], name="dispatch")
class ProductDayPlanCopyView(CreateAPIView):
    """复制胶料日计划"""
    serializer_class = ProductDayPlanCopySerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)


@method_decorator([api_recorder], name="dispatch")
class ProductBatchingDayPlanCopyView(CreateAPIView):
    """复制胶料日计划"""
    serializer_class = ProductBatchingDayPlanCopySerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

@method_decorator([api_recorder], name="dispatch")
class MaterialRequisitionCopyView(CreateAPIView):
    """复制胶料日计划"""
    serializer_class = MaterialRequisitionCopySerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
