# Create your views here.
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
from mes.permissions import ProductInfoPermissions
from recipe.filters import MaterialFilter, ProductInfoFilter, ProductRecipeFilter, ProductBatchingFilter, \
    MaterialAttributeFilter
from recipe.serializers import MaterialSerializer, ProductInfoSerializer, ProductInfoCreateSerializer, \
    ProductInfoUpdateSerializer, ProductInfoPartialUpdateSerializer, ProductInfoCopySerializer, \
    ProductRecipeListSerializer, ProductBatchingListSerializer, ProductBatchingCreateSerializer, \
    MaterialAttributeSerializer, ProductBatchingRetrieveSerializer, ProductBatchingUpdateSerializer
from recipe.models import Material, ProductInfo, ProductRecipe, ProductBatching, MaterialAttribute


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
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialFilter

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if ProductRecipe.objects.filter(material=instance).exists():
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
    queryset = MaterialAttribute.objects.filter(delete_flag=False)
    serializer_class = MaterialAttributeSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialAttributeFilter


@method_decorator([api_recorder], name="dispatch")
class ValidateProductVersionsView(APIView):
    """验证版本号，创建胶料工艺信息前调用，参数：xxx/?versions=版本&factory=产地id&product_no=胶料编码"""

    def get(self, request):
        versions = self.request.query_params.get('versions')
        factory = self.request.query_params.get('factory')
        product_no = self.request.query_params.get('product_no')
        if not all([versions, factory, product_no]):
            raise ValidationError('参数不足')
        try:
            factory = int(factory)
        except Exception:
            raise ValidationError('参数错误')
        product_info = ProductInfo.objects.filter(factory_id=factory,
                                                  product_no=product_no).order_by('-versions').first()
        if product_info:
            if product_info.versions >= versions:  # TODO 目前版本检测根据字符串做比较，后期搞清楚具体怎样填写版本号
                return Response({'code': -1, 'message': '版本号不得小于现有版本号'})
        return Response({'code': 0, 'message': ''})


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
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductInfoFilter

    def get_permissions(self):
        if self.action == 'partial_update':
            return (ProductInfoPermissions(),
                    IsAuthenticatedOrReadOnly())
        else:
            return (IsAuthenticatedOrReadOnly(),)

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
class ProductStageInfoView(APIView):
    """根据产地获取所以胶料及其段次信息, 参数：xxx/?factory_id=111"""

    def get(self, request):
        factory_id = self.request.query_params.get('factory_id')
        if not factory_id:
            raise ValidationError('缺少必填参数')
        try:
            factory = GlobalCode.objects.get(id=factory_id, used_flag=0, delete_flag=False)
        except Exception:
            raise ValidationError('产地不存在')
        ret = []
        products = ProductInfo.objects.filter(factory=factory).prefetch_related('productrecipe_set')
        for product in products:
            # TODO 要做distinct stage，sqlite数据库暂时不支持
            stages = product.productrecipe_set.values('stage', 'stage__global_name')
            ret.append({'product_info': product.id, 'product_no': product.product_no, 'stages': stages})
        return Response(data=ret)


class ProductRecipeListView(ListAPIView):
    """根据胶料工艺和段次获取胶料段次配方原材料信息"""
    queryset = ProductRecipe.objects.filter(delete_flag=False).order_by('num')
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductRecipeFilter
    serializer_class = ProductRecipeListSerializer
    pagination_class = None


class ProductBatchingViewSet(ModelViewSet):
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
        elif self.action == 'retrieve':
            return ProductBatchingRetrieveSerializer
        else:
            return ProductBatchingUpdateSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete_flag = True
        instance.delete_user = request.user
        instance.save()
        instance.batching_details.filter().update(delete_flag=True, delete_user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PreProductBatchView(APIView):
    """根据胶料工艺id和段次获取上段位配料信息(新建配料时调用)，参数:xxx/?product_info_id=1&stage_id=1"""

    def get(self, request):
        product_info_id = self.request.query_params.get('product_info_id')
        stage_id = self.request.query_params.get('stage_id')
        try:
            product_info_id = int(product_info_id)
            stage_id = int(stage_id)
        except Exception:
            raise ValidationError('参数错误')
        recipe = ProductRecipe.objects.filter(product_info_id=product_info_id,
                                              stage_id=stage_id).order_by('-num').first()
        if not recipe:
            raise ValidationError('当前段次配方不存在')

        pre_recipe = ProductRecipe.objects.filter(product_info_id=product_info_id,
                                                  num__lt=recipe.num).order_by('-num').first()
        pre_recipe_data = {}
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
                pre_recipe_data['ratio'] = ratio
                pre_recipe_data['density'] = pre_batch.batching_proportion
                pre_recipe_data['material_name'] = pre_batch.stage_product_batch_no
                pre_recipe_data['previous_product_batching'] = pre_batch.id
        return Response(pre_recipe_data)
