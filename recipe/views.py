
# Create your views here.
from django.db.models import Sum
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
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
from recipe.filters import MaterialFilter, ProductInfoFilter, ProductRecipeFilter, ProductBatchingFilter
from recipe.models import Material, ProductInfo, ProductRecipe, ProductBatching
from recipe.serializers import MaterialSerializer, ProductInfoSerializer, ProductInfoCreateSerializer, \
    ProductInfoUpdateSerializer, ProductInfoPartialUpdateSerializer, ProductInfoCopySerializer, \
    ProductRecipeListSerializer, ProductBatchingListSerializer, ProductBatchingCreateSerializer


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
    queryset = Material.objects.filter(delete_flag=False)
    serializer_class = MaterialSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialFilter


@method_decorator([api_recorder], name="dispatch")
class ProductInfoViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.ListModelMixin,
                         GenericViewSet):
    """
    list:
        胶料配方标准列表
    retrieve:
        胶料配方标准详情
    create:
        新建胶料配方标准
    update:
        胶料配方标准(只有编辑状态的胶料配方才可操作)
    partial_update:
        胶料应用和废弃操作
    """
    queryset = ProductInfo.objects.filter(delete_flag=False)
    permission_classes = (IsAuthenticatedOrReadOnly, )
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductInfoFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return ProductInfoCreateSerializer
        elif self.action == 'list':
            return ProductInfoSerializer
        elif self.action == 'partial_update':
            return ProductInfoPartialUpdateSerializer
        else:
            return ProductInfoUpdateSerializer


@method_decorator([api_recorder], name="dispatch")
class ProductInfoCopyView(CreateAPIView):
    """复制配方"""
    serializer_class = ProductInfoCopySerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)


@method_decorator([api_recorder], name="dispatch")
class ProductStageInfo(APIView):
    """根据产地获取所以胶料及其段次信息, 参数：xxx/?factory_id=111"""

    def get(self, request):
        factory_id = self.request.query_params.get('factory_id')
        if not factory_id:
            raise ValidationError('缺少必填参数')
        try:
            factory = GlobalCode.objects.get(id=factory_id)
        except Exception:
            raise ValidationError('产地不存在')
        ret = []
        products = ProductInfo.objects.filter(factory=factory).prefetch_related('productrecipe_set')
        for product in products:
            stage_names = product.productrecipe_set.values_list('stage__global_name', flat=True)
            ret.append({'product_info': product.product_no, 'stage_names': stage_names})
        return Response(data=ret)


class ProductRecipeListAPI(ListAPIView):
    """根据胶料工艺和段次获取胶料段次配方原材料信息"""
    queryset = ProductRecipe.objects.filter(delete_flag=False).order_by('num')
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductRecipeFilter
    serializer_class = ProductRecipeListSerializer
    pagination_class = None

    def list(self, request, *args, **kwargs):
        product_info_id = self.request.query_params.get('product_info_id')
        stage_id = self.request.query_params.get('stage_id')
        if not all([product_info_id, stage_id]):
            raise ValidationError('参数错误')
        recipe = ProductRecipe.objects.filter(product_info_id=product_info_id, stage_id=stage_id).first()
        if not recipe:
            raise ValidationError('当前段次配方不存在')

        pre_recipe = ProductRecipe.objects.filter(product_info_id=product_info_id,
                                                  num__lt=recipe.num).order_by('-num').first()
        pre_recipe_data = None
        if pre_recipe:
            pre_batch = ProductBatching.objects.filter(product_info_id=product_info_id,
                                                       stage_id=pre_recipe.stage_id).first()
            if not pre_batch:
                raise ValidationError('请先配置上段位的配料')
            else:
                ratio = ProductRecipe.objects.filter(product_info_id=product_info_id,
                                                     num__lte=recipe.num
                                                     ).aggregate(ratio=Sum('ratio'))['ratio']
                pre_recipe_data = OrderedDict()
                pre_recipe_data['material_type'] = pre_batch.stage.global_name
                pre_recipe_data['material'] = None
                pre_recipe_data['ratio'] = ratio
                pre_recipe_data['density'] = pre_batch.batching_proportion
                pre_recipe_data['material_name'] = pre_batch.stage_product_batch_no
        resp = super().list(request, *args, **kwargs)
        data = resp.data
        if pre_recipe_data:
            data.insert(0, pre_recipe_data)
        return Response(data)


class ProductBatchingViewSet(CommonDeleteMixin, ModelViewSet):
    """
    list:
        胶料配料标准列表
    retrieve:
        胶料配料标准详情
    create:
        新建胶料配料标准
    update:
        修改胶料配料标准
    partial_update:
        修改胶料配料标准
    """
    queryset = ProductBatching.objects.filter(delete_flag=False)
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductBatchingFilter

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductBatchingListSerializer
        elif self.action == 'create':
            return ProductBatchingCreateSerializer
        else:
            return ProductBatchingListSerializer
