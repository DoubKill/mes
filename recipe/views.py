# Create your views here.
from django.db.models import Prefetch
from django.db.transaction import atomic
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet, ReadOnlyModelViewSet

from basics.models import GlobalCode, EquipCategoryAttribute
from basics.views import CommonDeleteMixin
from mes import settings
from mes.derorators import api_recorder
from mes.sync import ProductBatchingSyncInterface
from recipe.filters import MaterialFilter, ProductInfoFilter, ProductBatchingFilter, \
    MaterialAttributeFilter, ERPMaterialFilter, ZCMaterialFilter
from recipe.serializers import MaterialSerializer, ProductInfoSerializer, \
    ProductBatchingListSerializer, ProductBatchingCreateSerializer, MaterialAttributeSerializer, \
    ProductBatchingRetrieveSerializer, ProductBatchingUpdateSerializer, \
    ProductBatchingPartialUpdateSerializer, MaterialSupplierSerializer, \
    ProductBatchingDetailMaterialSerializer, WeighCntTypeSerializer, ERPMaterialCreateSerializer, ERPMaterialSerializer, \
    ERPMaterialUpdateSerializer, ZCMaterialSerializer
from recipe.models import Material, ProductInfo, ProductBatching, MaterialAttribute, \
    ProductBatchingDetail, MaterialSupplier, WeighCntType, WeighBatchingDetail, ZCMaterial, ERPMESMaterialRelation


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
            if self.request.query_params.get('exclude_stage'):
                stage_names = GlobalCode.objects.filter(
                    global_type__type_name='胶料段次').values_list('global_name', flat=True)
                queryset = queryset.exclude(material_type__global_name__in=stage_names)
            else:
                queryset = queryset.filter(use_flag=1)
            data = queryset.values('id', 'material_no', 'material_name',
                                   'material_type__global_name', 'material_type', 'for_short',
                                   'package_unit', 'package_unit__global_name', 'use_flag')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.use_flag is True and ProductBatchingDetail.objects.filter(material=instance,
                                                                              delete_flag=False).exists():
            raise ValidationError('该原材料已关联配方，无法停用!')
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
        site = self.request.query_params.get('site')
        product_info = self.request.query_params.get('product_info')
        stage = self.request.query_params.get('stage')
        versions = self.request.query_params.get('versions')
        dev_type = self.request.query_params.get('dev_type')
        stage_product_batch_no = self.request.query_params.get('stage_product_batch_no')
        if stage_product_batch_no:
            if ProductBatching.objects.exclude(
                    used_type=6).filter(stage_product_batch_no=stage_product_batch_no,
                                        factory__isnull=True,
                                        batching_type=2,
                                        dev_type_id=dev_type).exists():
                raise ValidationError('该配方已存在')
            return Response('OK')
        if not all([versions, site, product_info, stage]):
            raise ValidationError('参数不足')
        try:
            stage = int(stage)
            site = int(site)
            product_info = int(product_info)
            dev_type = int(dev_type)
        except Exception:
            raise ValidationError('参数错误')
        product_batching = ProductBatching.objects.exclude(used_type=6).filter(site_id=site,
                                                                               stage_id=stage,
                                                                               product_info_id=product_info,
                                                                               versions=versions,
                                                                               batching_type=2,
                                                                               dev_type_id=dev_type,
                                                                               ).first()
        if product_batching:
            raise ValidationError('该配方已存在')
            # if product_batching.versions >= versions:
            #     raise ValidationError({'versions': '该配方版本号不得小于现有版本号'})
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
        Prefetch('batching_details', queryset=ProductBatchingDetail.objects.filter(delete_flag=False).order_by('sn')),
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
        for p in ProductBatching.objects.filter(batching_type=1,
                                                stage_product_batch_no=product_batching.stage_product_batch_no,
                                                dev_type=product_batching.dev_type):
            p.batching_details.all().delete()
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


@method_decorator([api_recorder], name="dispatch")
class ZCMaterialListView(ListAPIView):
    """中策ERP系统物料列表"""
    queryset = ZCMaterial.objects.all()
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    serializer_class = ZCMaterialSerializer
    filter_class = ZCMaterialFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        is_binding = self.request.query_params.get('is_binding')
        if is_binding:
            if is_binding == 'Y':
                queryset = queryset.filter(material__isnull=False).distinct()
            else:
                queryset = queryset.filter(material__isnull=True).distinct()
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'material_no', 'material_name')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class ERPMaterialViewSet(CommonDeleteMixin, ModelViewSet):
    """ERP物料绑定关系数据"""
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ERPMaterialFilter

    def get_queryset(self):
        stage_names = GlobalCode.objects.filter(
            global_type__type_name='胶料段次').values_list('global_name', flat=True)
        erp_material_no = self.request.query_params.get('erp_material_no')
        erp_material_name = self.request.query_params.get('erp_material_name')
        is_binding = self.request.query_params.get('is_binding')
        filter_kwargs = {}
        query_set = Material.objects.exclude(
            material_type__global_name__in=stage_names).prefetch_related('zc_materials').order_by('-created_date')
        if erp_material_no:
            filter_kwargs['zc_materials__material_no__icontains'] = erp_material_no
        if erp_material_name:
            filter_kwargs['zc_materials__material_name__icontains'] = erp_material_name
        if is_binding:
            if is_binding == 'Y':
                filter_kwargs['zc_materials__isnull'] = False
            else:
                filter_kwargs['zc_materials__isnull'] = True
        if filter_kwargs:
            query_set = query_set.filter(**filter_kwargs).distinct()
        return query_set

    def get_serializer_class(self):
        if self.action == 'create':
            return ERPMaterialCreateSerializer
        elif self.action == 'list':
            return ERPMaterialSerializer
        else:
            return ERPMaterialUpdateSerializer


@method_decorator([api_recorder], name="dispatch")
class GetERPZcMaterialAPiView(APIView):
    """通过mes物料名获取有绑定关系的中策物料"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        material_no = self.request.query_params.get('material_name')
        zc_materials = ERPMESMaterialRelation.objects.filter(material__material_no=material_no)\
            .values('zc_material__material_name', 'zc_material__wlxxid')
        return Response({'results': list(zc_materials)})


@method_decorator([api_recorder], name="dispatch")
class ProductDevBatchingReceive(APIView):

    @atomic()
    def post(self, request):
        # data = {
        #     'factory__global_no': '安吉',
        #     'site__global_no': 'C',
        #     'product_info__product_no': 'C590',
        #     'stage_product_batch_no': "C-FM-C590-01",
        #     'dev_type__category_no': "F370",
        #     'stage__global_no': "FM",
        #     'versions': "01",
        #     'used_type': 4,
        #     'batching_details': [{'sn': 1,
        #                           'material__material_no': 'aaa',
        #                           'actual_weight': 121,
        #                           'standard_error': 12,
        #                           'auto_flag': 1,
        #                           'type': 1}]
        # }
        data = self.request.data
        product_batching = ProductBatching.objects.exclude(
            used_type=6).filter(stage_product_batch_no=data['stage_product_batch_no'],
                                batching_type=2,
                                dev_type__category_no=data['dev_type__category_no']).first()
        if product_batching:
            return Response('ok')
        else:
            try:
                dev_type = EquipCategoryAttribute.objects.get(category_no=data['dev_type__category_no'])
                if data['factory__global_no']:
                    factory = GlobalCode.objects.get(global_no=data['factory__global_no'])
                else:
                    factory = None
                if data['product_info__product_no']:
                    product_info = ProductInfo.objects.get(product_no=data['product_info__product_no'])
                else:
                    product_info = None
                if data['site__global_no']:
                    site = GlobalCode.objects.get(global_no=data['site__global_no'])
                else:
                    site = None
                if data['stage__global_no']:
                    stage = GlobalCode.objects.get(global_no=data['stage__global_no'])
                else:
                    stage = None
                for m in data['batching_details']:
                    material_no = m.pop('material__material_no')
                    material = Material.objects.filter(material_no=material_no).first()
                    if not material:
                        raise ValidationError('MES原材料:{}不存在！'.format(material_no))
                    m['material'] = material
            except EquipCategoryAttribute.DoesNotExist:
                raise ValidationError('MES机型{}不存在'.format(data.get('dev_type__category_no')))
            except GlobalCode.DoesNotExist as e:
                raise ValidationError('MES公共代码{}不存在'.format(e))
            except ProductInfo.DoesNotExist:
                raise ValidationError('MES胶料代码{}不存在'.format(data['product_info__product_no']))
            except Material.DoesNotExist:
                raise ValidationError('MES原材料不存在！')
            except Exception as e:
                raise e
            product_batching = ProductBatching.objects.create(
                dev_type=dev_type,
                factory=factory,
                site=site,
                product_info=product_info,
                stage=stage,
                batching_type=2,
                versions=data['versions'],
                used_type=data['used_type'],
                stage_product_batch_no=data['stage_product_batch_no']
            )
            for item in data['batching_details']:
                item['product_batching'] = product_batching
                ProductBatchingDetail.objects.create(**item)
            product_batching.save()
            return Response('ok')