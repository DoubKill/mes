from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import mixins, status
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from basics.views import CommonDeleteMixin
from mes.derorators import api_recorder
from plan.filters import ProductDayPlanFilter, MaterialDemandedFilter, ProductBatchingDayPlanFilter
from plan.serializers import ProductDayPlanSerializer, MaterialDemandedSerializer, ProductBatchingDayPlanSerializer, \
    ProductDayPlanCopySerializer, ProductBatchingDayPlanCopySerializer, MaterialRequisitionClassesSerializer
from plan.models import ProductDayPlan, ProductClassesPlan, MaterialDemanded, ProductBatchingDayPlan, \
    ProductBatchingClassesPlan, MaterialRequisitionClasses
from plan.paginations import LimitOffsetPagination
from rest_framework.views import APIView
from basics.models import Equip, PlanSchedule

# Create your views here.
from plan.uuidfield import UUidTools
from recipe.models import Material


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

    def destroy(self, request, *args, **kwargs):
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
class MaterialDemandedViewSet(ListAPIView):
    """
    list:
        原材料需求量列表
    """
    queryset = MaterialDemanded.objects.filter(delete_flag=False)
    serializer_class = MaterialDemandedSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend, OrderingFilter)
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
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filter_class = ProductBatchingDayPlanFilter
    ordering_fields = ['id', 'equip__category__equip_type__global_name']

    # pagination_class = LimitOffsetPagination

    def destroy(self, request, *args, **kwargs):
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
class MaterialRequisitionClassesViewSet(CommonDeleteMixin, ModelViewSet):
    """
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

    # pagination_class = LimitOffsetPagination

    def perform_create(self, serializer):
        serializer.save(created_user=self.request.user, plan_classes_uid=UUidTools.uuid1_hex())

    def perform_update(self, serializer):
        serializer.save(last_updated_user=self.request.user)


class MaterialDemandedAPIView(APIView):
    def get(self, request):
        filter_dict = {}
        if request.GET.get('plan_date', None):  # 日期
            plan_date = request.GET.get('plan_date')
            filter_dict['plan_schedule'] = PlanSchedule.objects.filter(day_time=plan_date).first()
        # material_type
        if request.GET.get('material_name', None):  # 原材料名称
            material_name = request.GET.get('material_name')
            filter_dict['material_demanded'] = Material.objects.filter(material_name=material_name).first()
        if request.GET.get('material_type', None):  # 公共代码GlobalCode原材料类别id
            material_type = request.GET.get('material_type')
            filter_dict['material_type'] = Material.objects.filter(material_type_id=material_type).first()
        if filter_dict:
            m_list = MaterialDemanded.objects.filter(**filter_dict).values('material', 'plan_schedule').distinct()
        else:
            m_list = MaterialDemanded.objects.filter().values('material', 'plan_schedule').distinct()
        response_list = []
        for m_dict in m_list:
            m_queryset = MaterialDemanded.objects.filter(material=m_dict['material'],
                                                         plan_schedule=m_dict['plan_schedule'])
            response_list.append(m_dict)
            md_obj = MaterialDemanded.objects.filter(material=m_dict['material']).first()
            response_list[-1]['material_type'] = md_obj.material.material_type.global_name
            response_list[-1]['material_no'] = md_obj.material.material_no
            response_list[-1]['material_name'] = md_obj.material.material_name
            response_list[-1]['md_material_requisition_classes'] = []
            for i in range(len(md_obj.md_material_requisition_classes.all())):
                dict_key = ['早', '中', '晚']
                user_dict = {dict_key[i]: md_obj.md_material_requisition_classes.all()[i].weight}
                response_list[-1]['md_material_requisition_classes'].append(user_dict)
            response_list[-1]['material_demanded_list'] = []
            i = 0
            for m_obj in m_queryset.values_list('id', 'material_demanded'):
                dict_key = ['id', 'material_demanded']
                user_dict = {}
                user_dict[dict_key[0]] = m_obj[0]
                user_dict[dict_key[1]] = m_obj[1]
                response_list[-1]['material_demanded_list'].append(user_dict)
                i += 1
        return JsonResponse(response_list, safe=False)


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


'''
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
'''
