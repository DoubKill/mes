# Create your views here.
from django.db.models import Prefetch
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet, ReadOnlyModelViewSet

from basics.views import CommonDeleteMixin
from mes import settings
from mes.derorators import api_recorder
from mes.sync import ProductBatchingSyncInterface
from recipe.filters import MaterialFilter, ProductInfoFilter, ProductBatchingFilter, \
    MaterialAttributeFilter
from recipe.serializers import MaterialSerializer, ProductInfoSerializer, \
    ProductBatchingListSerializer, ProductBatchingCreateSerializer, MaterialAttributeSerializer, \
    ProductBatchingRetrieveSerializer, ProductBatchingUpdateSerializer, \
    ProductBatchingPartialUpdateSerializer, MaterialSupplierSerializer, \
    ProductBatchingDetailMaterialSerializer, WeighCntTypeSerializer
from recipe.models import Material, ProductInfo, ProductBatching, MaterialAttribute, \
    ProductBatchingDetail, MaterialSupplier, WeighCntType, WeighBatchingDetail


@method_decorator([api_recorder], name="dispatch")
class MaterialViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        原材料列表
    create:
        新建原材料
    update:
        修改原材料
    destroy:
        删除原材料
    """
    queryset = Material.objects.filter(delete_flag=False
                                       ).select_related('material_type'
                                                        ).prefetch_related('material_attr').order_by('-created_date')
    serializer_class = MaterialSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialFilter

    def get_queryset(self):
        material_type_ids = self.request.query_params.get('material_type_ids')
        if material_type_ids:
            material_type_ids = material_type_ids.split(',')
            return self.queryset.filter(material_type_id__in=material_type_ids)
        return self.queryset

    def get_permissions(self):
        if self.request.query_params.get('all'):
            return ()
        else:
            return (IsAuthenticated(),)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.filter(use_flag=1).values('id', 'material_no',
                                                      'material_name', 'material_type__global_name')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if ProductBatchingDetail.objects.filter(material=instance).exists():
            raise ValidationError('该原材料已关联配方，无法删除')
        else:
            return super().destroy(request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class MaterialAttributeViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        原材料属性列表
    create:
        新建原材料属性
    update:
        修改原材料属性
    destroy:
        删除原材料属性
    """
    queryset = MaterialAttribute.objects.filter(delete_flag=False).order_by('-created_date')
    serializer_class = MaterialAttributeSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialAttributeFilter


@method_decorator([api_recorder], name="dispatch")
class MaterialSupplierViewSet(CommonDeleteMixin, ModelViewSet):
    queryset = MaterialSupplier.objects.all().order_by('-created_date')
    serializer_class = MaterialSupplierSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ['material']


@method_decorator([api_recorder], name="dispatch")
class ValidateProductVersionsView(APIView):
    """验证版本号，创建胶料工艺信息前调用，
    参数：xxx/?factory=产地id&site=SITEid&product_info=胶料代码id&versions=版本号&stage=段次id&stage_product_batch_no=配方编码"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        factory = self.request.query_params.get('factory')
        site = self.request.query_params.get('site')
        product_info = self.request.query_params.get('product_info')
        stage = self.request.query_params.get('stage')
        versions = self.request.query_params.get('versions')
        stage_product_batch_no = self.request.query_params.get('stage_product_batch_no')
        if stage_product_batch_no:
            if ProductBatching.objects.exclude(
                    used_type=6).filter(stage_product_batch_no=stage_product_batch_no,
                                        factory__isnull=True,
                                        batching_type=2).exists():
                raise ValidationError('该配方已存在')
            return Response('OK')
        if not all([versions, factory, site, product_info, stage]):
            raise ValidationError('参数不足')
        try:
            stage = int(stage)
            site = int(site)
            product_info = int(product_info)
            factory = int(factory)
        except Exception:
            raise ValidationError('参数错误')
        product_batching = ProductBatching.objects.filter(factory_id=factory,
                                                          site_id=site,
                                                          stage_id=stage,
                                                          product_info_id=product_info,
                                                          batching_type=2
                                                          ).order_by('-versions').first()
        if product_batching:
            if product_batching.versions >= versions:
                raise ValidationError({'versions': '该配方版本号不得小于现有版本号'})
        return Response('OK')


@method_decorator([api_recorder], name="dispatch")
class ProductInfoViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.ListModelMixin,
                         GenericViewSet):
    """
    list:
        胶料代码列表
    retrieve:
        胶料代码标准详情
    create:
        新建胶料代码
    update:
        修改胶料代码
    partial_update:
        修改胶料代码
    """
    queryset = ProductInfo.objects.filter(delete_flag=False).order_by('-created_date')
    serializer_class = ProductInfoSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductInfoFilter

    def get_permissions(self):
        if self.request.query_params.get('all'):
            return ()
        else:
            return (IsAuthenticated(),)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'product_no', 'product_name')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class ProductBatchingViewSet(ModelViewSet):
    """
    list:
        胶料配料标准列表
    retrieve:
        胶料配料标准详情
    create:
        新建胶料配料标准
    update:
        配料
    partial_update:
        配料审批
    """
    queryset = ProductBatching.objects.filter(
        delete_flag=False, batching_type=2).select_related(
        "factory", "site", "dev_type", "stage", "product_info"
    ).prefetch_related(
        Prefetch('batching_details', queryset=ProductBatchingDetail.objects.filter(delete_flag=False)),
        Prefetch('weight_cnt_types', queryset=WeighCntType.objects.filter(delete_flag=False)),
        Prefetch('weight_cnt_types__weight_details', queryset=WeighBatchingDetail.objects.filter(delete_flag=False)),
    ).order_by('-created_date')
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductBatchingFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'stage_product_batch_no',
                                   'batching_weight',
                                   'production_time_interval',
                                   'used_type')
            return Response({'results': data})
        else:
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

    def get_permissions(self):
        if self.request.query_params.get('all'):
            return ()
        else:
            return (IsAuthenticated(),)

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductBatchingListSerializer
        elif self.action == 'create':
            return ProductBatchingCreateSerializer
        elif self.action == 'retrieve':
            return ProductBatchingRetrieveSerializer
        elif self.action == 'partial_update':
            return ProductBatchingPartialUpdateSerializer
        else:
            return ProductBatchingUpdateSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete_flag = True
        instance.delete_user = request.user
        instance.save()
        instance.batching_details.filter().update(delete_flag=True, delete_user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name="dispatch")
class RecipeNoticeAPiView(APIView):
    """配方数据下发至上辅机（只有应用状态的配方才可下发）"""
    permission_classes = ()
    authentication_classes = ()

    def post(self, request):
        product_batching_id = self.request.query_params.get('product_batching_id')
        try:
            product_batching_id = int(product_batching_id)
        except Exception:
            raise ValidationError('参数错误')
        product_batching = ProductBatching.objects.filter(id=product_batching_id).prefetch_related(
            Prefetch('batching_details', queryset=ProductBatchingDetail.objects.filter(delete_flag=False))).first()
        if not product_batching:
            raise ValidationError('该配方不存在')
        if not product_batching.used_type == 4:
            raise ValidationError('只有应用状态的配方才可下发至上辅机')
        if not product_batching.dev_type:
            raise ValidationError('请选择机型')
        interface = ProductBatchingSyncInterface(instance=product_batching)
        try:
            interface.request()
        except Exception as e:
            raise ValidationError(e)
        return Response(data={'auxiliary_url': settings.AUXILIARY_URL}, status=status.HTTP_200_OK)


# @method_decorator([api_recorder], name="dispatch")
# class WeighBatchingViewSet(ModelViewSet):
#     """小料称量配方标准"""
#     queryset = WeighBatching.objects.filter(delete_flag=False).order_by('-created_date')
#     serializer_class = WeighBatchingSerializer
#     permission_classes = (IsAuthenticated,)
#     filter_backends = (DjangoFilterBackend,)
#     filter_class = WeighBatchingFilter
#
#     def get_serializer_class(self):
#         if self.action == 'list':
#             return WeighBatchingSerializer
#         elif self.action == 'create':
#             return WeighBatchingCreateSerializer
#         elif self.action == 'retrieve':
#             return WeighBatchingRetrieveSerializer
#         elif self.action == 'partial_update':
#             return WeighBatchingChangeUsedTypeSerializer
#         else:
#             return WeighBatchingUpdateSerializer


@method_decorator([api_recorder], name="dispatch")
class WeighCntTypeViewSet(ModelViewSet):
    queryset = WeighCntType.objects.all()
    serializer_class = WeighCntTypeSerializer
    permission_classes = (IsAuthenticated,)


@method_decorator([api_recorder], name="dispatch")
class ProductBatchingDetailListView(ReadOnlyModelViewSet):
    queryset = ProductBatchingDetail.objects.filter(delete_flag=False)
    serializer_class = ProductBatchingDetailMaterialSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('product_batching',)
    pagination_class = None
