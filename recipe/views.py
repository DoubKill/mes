# Create your views here.
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from basics.views import CommonDeleteMixin
from mes.derorators import api_recorder
from mes.permissions import ProductBatchingPermissions
from mes.sync import ProductBatchingSyncInterface
from recipe.filters import MaterialFilter, ProductInfoFilter, ProductBatchingFilter, \
    MaterialAttributeFilter
from recipe.serializers import MaterialSerializer, ProductInfoSerializer, \
    ProductBatchingListSerializer, ProductBatchingCreateSerializer, MaterialAttributeSerializer, \
    ProductBatchingRetrieveSerializer, ProductBatchingUpdateSerializer, \
    ProductBatchingPartialUpdateSerializer
from recipe.models import Material, ProductInfo, ProductBatching, MaterialAttribute, \
    ProductBatchingDetail


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
    queryset = Material.objects.filter(delete_flag=False).select_related('material_type').order_by('-created_date')
    serializer_class = MaterialSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialFilter

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
            # 本来是删除，现在改为是启用就改为禁用 是禁用就改为启用
            # instance = self.get_object()
            # if instance.use_flag:
            #     instance.use_flag = False
            # else:
            #     instance.use_flag = True
            # instance.last_updated_user = request.user
            # instance.save()
            # return Response(status=status.HTTP_204_NO_CONTENT)
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
class ValidateProductVersionsView(APIView):
    """验证版本号，创建胶料工艺信息前调用，
    参数：xxx/?factory=产地id&site=SITEid&product_info=胶料代码id&versions=版本号&stage=段次id"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        factory = self.request.query_params.get('factory')
        site = self.request.query_params.get('site')
        product_info = self.request.query_params.get('product_info')
        stage = self.request.query_params.get('stage')
        versions = self.request.query_params.get('versions')
        if not all([versions, factory, site, product_info, stage]):
            raise ValidationError('参数不足')
        try:
            stage = int(stage)
            site = int(site)
            product_info = int(product_info)
            factory = int(factory)
        except Exception:
            raise ValidationError('参数错误')
        product_batching = ProductBatching.objects.filter(factory_id=factory, site_id=site, stage_id=stage,
                                                          product_info_id=product_info
                                                          ).order_by('-versions').first()
        if product_batching:
            if product_batching.versions >= versions:  # TODO 目前版本检测根据字符串做比较，后期搞清楚具体怎样填写版本号
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
    # TODO 配方下载功能（只能下载应用状态的配方，并去除当前计划中的配方）
    queryset = ProductBatching.objects.filter(delete_flag=False).select_related("factory", "site",
                                                                                "dev_type", "stage", "product_info"
                                                                                ).order_by('-created_date')
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductBatchingFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'stage_product_batch_no', 'batching_weight', 'production_time_interval')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)

    def get_permissions(self):
        if self.request.query_params.get('all'):
            return ()
        if self.action == 'partial_update':
            return (ProductBatchingPermissions(),
                    IsAuthenticated())
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


class RecipeNoticeAPiView(APIView):
    """配方数据下发至上辅机（只有应用状态的配方才可下发）"""
    permission_classes = ()
    authentication_classes = ()

    def post(self, request):
        product_batching_id = self.request.query_params.get('product_batching_id')
        if not product_batching_id:
            raise ValidationError('缺失参数')
        try:
            product_batching = ProductBatching.objects.get(id=product_batching_id)
        except Exception:
            raise ValidationError('该配方不存在')
        if not product_batching.used_type == 4:
            raise ValidationError('只有应用状态的配方才可下发至上辅机')
        interface = ProductBatchingSyncInterface(instance=product_batching)
        try:
            interface.request()
        except Exception as e:
            raise ValidationError(e)
        return Response('发送成功', status=status.HTTP_200_OK)
