from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import mixins, status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from basics.views import CommonDeleteMixin
from mes.derorators import api_recorder
from plan.filters import ProductDayPlanFilter, MaterialDemandedFilter, ProductBatchingDayPlanFilter, \
    MaterialRequisitionFilter
from plan.serializers import ProductDayPlanSerializer, MaterialDemandedSerializer, ProductBatchingDayPlanSerializer, \
    MaterialRequisitionSerializer, ProductDayPlanCopySerializer, ProductBatchingDayPlanCopySerializer, \
    MaterialRequisitionCopySerializer
from plan.models import ProductDayPlan, ProductClassesPlan, MaterialDemanded, ProductBatchingDayPlan, \
    MaterialRequisition, ProductBatchingClassesPlan, MaterialRequisitionClasses
from plan.paginations import LimitOffsetPagination


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
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filter_class = ProductDayPlanFilter
    ordering_fields = ['id', 'equip__category__equip_type__global_name']

    # pagination_class = LimitOffsetPagination

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        ProductClassesPlan.objects.filter(product_day_plan=instance).update(delete_flag=True, delete_user=request.user)
        MaterialDemanded.objects.filter(product_day_plan=instance).update(delete_flag=True, delete_user=request.user)
        instance.delete_flag = True
        instance.delete_user = request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filter_class = MaterialDemandedFilter
    ordering_fields = ['id', 'product_day_plan__plan_schedule__work_schedule__schedule_name']

    # pagination_class = LimitOffsetPagination

    def perform_create(self, serializer):
        serializer.save(created_user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(last_updated_user=self.request.user)


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
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filter_class = ProductBatchingDayPlanFilter
    ordering_fields = ['id', 'equip__category__equip_type__global_name']

    # pagination_class = LimitOffsetPagination

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        ProductBatchingClassesPlan.objects.filter(product_batching_day_plan=instance).update(delete_flag=True,
                                                                                             delete_user=request.user)
        MaterialDemanded.objects.filter(product_batching_day_plan=instance).update(delete_flag=True,
                                                                                   delete_user=request.user)
        instance.delete_flag = True
        instance.delete_user = request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filter_class = MaterialRequisitionFilter
    ordering_fields = ['id']

    # pagination_class = LimitOffsetPagination

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        MaterialRequisitionClasses.objects.filter(material_requisition=instance).update(delete_flag=True,
                                                                                        delete_user=request.user)
        instance.delete_flag = True
        instance.delete_user = request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


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


@method_decorator([api_recorder], name="dispatch")
class MaterialRequisitionCopyView(CreateAPIView):
    """复制领料日计划"""
    serializer_class = MaterialRequisitionCopySerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
