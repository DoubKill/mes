
# Create your views here.
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from basics.models import GlobalCode
from basics.views import CommonDeleteMixin
from mes.derorators import api_recorder
from recipe.filters import MaterialFilter, ProductInfoFilter
from recipe.models import Material, ProductInfo
from recipe.serializers import MaterialSerializer, ProductInfoSerializer, ProductInfoCreateSerializer, \
    ProductInfoUpdateSerializer, ProductInfoPartialUpdateSerializer, ProductInfoCopySerializer


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