# Create your views here.
import datetime
import json
import re
import logging

from django.db.models import Prefetch, Q, Max, F
from django.db.transaction import atomic
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet, ReadOnlyModelViewSet

from basics.models import GlobalCode, EquipCategoryAttribute
from basics.views import CommonDeleteMixin
from equipment.utils import gen_template_response
from mes import settings
from mes.derorators import api_recorder
from mes.sync import ProductBatchingSyncInterface
from plan.models import ProductClassesPlan
from production.models import PlanStatus, MaterialTankStatus
from recipe.filters import MaterialFilter, ProductInfoFilter, ProductBatchingFilter, \
    MaterialAttributeFilter, ERPMaterialFilter, ZCMaterialFilter, RecipeChangeHistoryFilter
from recipe.serializers import MaterialSerializer, ProductInfoSerializer, \
    ProductBatchingListSerializer, ProductBatchingCreateSerializer, MaterialAttributeSerializer, \
    ProductBatchingRetrieveSerializer, ProductBatchingUpdateSerializer, \
    ProductBatchingPartialUpdateSerializer, MaterialSupplierSerializer, \
    ProductBatchingDetailMaterialSerializer, WeighCntTypeSerializer, ERPMaterialCreateSerializer, ERPMaterialSerializer, \
    ERPMaterialUpdateSerializer, ZCMaterialSerializer, ProductBatchingDetailRetrieveSerializer, \
    ReplaceRecipeMaterialSerializer, WFProductBatchingCreateSerializer, WFProductBatchingUpdateSerializer, \
    WFProductBatchingListSerializer, WFProductBatchingRetrieveSerializer, RecipeChangeHistorySerializer, RecipeChangeHistoryRetrieveSerializer
from recipe.models import Material, ProductInfo, ProductBatching, MaterialAttribute, \
    ProductBatchingDetail, MaterialSupplier, WeighCntType, WeighBatchingDetail, ZCMaterial, ERPMESMaterialRelation, \
    ProductBatchingEquip, ProductBatchingMixed, MultiReplaceMaterial, RecipeChangeHistory, RecipeChangeDetail
from recipe.utils import get_mixed

error_logger = logging.getLogger('error_log')


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
        mc_code = self.request.query_params.get('mc_code')  # 人工配通用条码去除-C、-X尾缀
        wms_code = self.request.query_params.get('wms_code')  # 原材料补打通用条码去除-C、-X尾缀
        only_storage_flag = self.request.query_params.get('only_storage_flag')  # 仅显示未设定有效期的物料
        only_safety_flag = self.request.query_params.get('only_safety_flag')  # 仅显示未设定安全库存的物料
        queryset = self.filter_queryset(self.get_queryset())
        if only_storage_flag:
            queryset = queryset.filter(material_attr__period_of_validity__isnull=True)
        if only_safety_flag:
            queryset = queryset.filter(material_attr__safety_inventory__isnull=True)
        if self.request.query_params.get('all'):
            if self.request.query_params.get('exclude_stage'):
                stage_names = GlobalCode.objects.filter(
                    global_type__type_name='胶料段次').values_list('global_name', flat=True)
                queryset = queryset.exclude(material_type__global_name__in=stage_names)
            else:
                queryset = queryset.filter(use_flag=1)
                if mc_code:  # 通用卡片需排除没有erp绑定关系
                    stages = list(GlobalCode.objects.filter(use_flag=True, global_type__use_flag=True, global_type__type_name='化工类别').values_list('global_name', flat=True))
                    erp_materials = set(ERPMESMaterialRelation.objects.filter(material__material_type__global_name__in=stages, use_flag=True).values_list('material__material_name', flat=True))
                    queryset = queryset.filter(~Q(Q(material_name__endswith='-C') | Q(material_name__endswith='-X')), material_name__in=erp_materials)
                if wms_code:  # 原材料补打卡片需排除没有erp绑定关系
                    stages = list(GlobalCode.objects.filter(use_flag=True, global_type__use_flag=True, global_type__type_name='机台补打类别').values_list('global_name', flat=True))
                    erp_materials = set(ERPMESMaterialRelation.objects.filter(material__material_type__global_name__in=stages, use_flag=True).values_list('material__material_name', flat=True))
                    queryset = queryset.filter(~Q(Q(material_name__endswith='-C') | Q(material_name__endswith='-X')), material_name__in=erp_materials)
            data = queryset.values('id', 'material_no', 'material_name',
                                   'material_type__global_name', 'material_type', 'for_short',
                                   'package_unit', 'package_unit__global_name', 'use_flag')
            return Response({'results': data})
        else:
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

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

    @action(methods=['post'], detail=False, permission_classes=[IsAuthenticated], url_path='batch-set',
            url_name='batch-set')
    def batch_set(self, request):
        req_data = self.request.data
        if not isinstance(req_data, dict):
            raise ValidationError('参数错误！')
        materials = req_data.pop('materials', [])
        if not isinstance(materials, list):
            raise ValidationError('参数错误！')
        for m in materials:
            req_data.update({'material': m})
            s = MaterialAttributeSerializer(data=req_data, context={'request': request})
            s.is_valid(raise_exception=True)
            s.save()
        return Response('ok')


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
                    used_type__in=[6]).filter(stage_product_batch_no=stage_product_batch_no, factory__isnull=True,
                                              batching_type=2, dev_type_id=dev_type).exists():
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
        product_batching = ProductBatching.objects.exclude(used_type__in=[6]).filter(site_id=site,
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
        Prefetch('weight_cnt_types__weight_details', queryset=WeighBatchingDetail.objects.filter(
            delete_flag=False).order_by('id')),
    ).order_by('stage_product_batch_no', 'dev_type')
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductBatchingFilter
    EXPORT_FIELDS_DICT = {
        '序号': 'id',
        '配方名称': 'stage_product_batch_no'
    }

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        exclude_used_type = self.request.query_params.get('exclude_used_type')
        filter_type = self.request.query_params.get('filter_type')  # 1 表示部分发送(蓝色) 2 表示未设置可用机台
        recipe_type = self.request.query_params.get('recipe_type')  # 配方类别(车胎胶料、斜交胎胶料...)
        wms_material_name = self.request.query_params.get('wms_material_name')  # 原材料名称过滤
        print_type = self.request.query_params.get('print_type')  # 胶皮补打[加硫、无硫]过滤
        export = self.request.query_params.get('export')  # 导出涉及上述原材料的配方名称
        if exclude_used_type:
            queryset = queryset.exclude(used_type=exclude_used_type)
        if self.request.query_params.get('all'):
            if self.request.query_params.get('sfj_recipe'):
                _equip = self.request.query_params.get('equip_no')
                data = ProductBatching.objects.using('SFJ').filter(used_type=4, batching_type=1, equip__equip_no=_equip).values(
                    'id', 'stage_product_batch_no', 'batching_weight', 'production_time_interval', 'used_type', 'dev_type',
                    'dev_type__category_name'
                )
            else:
                data = queryset.values('id', 'stage_product_batch_no',
                                       'batching_weight',
                                       'production_time_interval',
                                       'used_type',
                                       'dev_type',
                                       'dev_type__category_name')
                if print_type:
                    data = list(set(data.filter(stage__global_name__in=['FM', 'RFM', 'RE'])
                                    .values_list('stage_product_batch_no', flat=True))) if print_type == '加硫' else \
                        list(set(data.exclude(stage__global_name__in=['FM', 'RFM', 'RE'])
                                 .values_list('stage_product_batch_no', flat=True)))
            return Response({'results': data})
        else:
            if filter_type:
                res_id = []
                recipe_ids = ProductBatchingEquip.objects.filter(is_used=True).values_list('product_batching_id', flat=True).distinct()
                if filter_type == '1':
                    if not recipe_ids:
                        return Response([])
                    for r_id in recipe_ids:
                        enable_equip = list(ProductBatchingEquip.objects.filter(product_batching_id=r_id).values_list('equip_no', flat=True).distinct())
                        send_success_equip = list(ProductBatchingEquip.objects.filter(product_batching_id=r_id, send_recipe_flag=True).values_list('equip_no', flat=True).distinct())
                        if enable_equip != send_success_equip:
                            res_id.append(r_id)
                    queryset = queryset.filter(id__in=res_id)
                elif filter_type == '2':
                    queryset = queryset.exclude(id__in=list(recipe_ids))
            if recipe_type:
                stage_prefix = re.split(r'[,|，]', recipe_type)
                filter_str = ''
                for i in stage_prefix:
                    filter_str += ('' if not filter_str else '|') + f"Q(product_info__product_name__startswith='{i.strip()}')"
                queryset = queryset.filter(eval(filter_str))
                if 'C' in stage_prefix or 'TC' in stage_prefix:  # 车胎类别(C)与半钢类别(CJ)需要区分
                    queryset = queryset.filter(~Q(product_info__product_name__startswith='CJ'), ~Q(product_info__product_name__startswith='TCJ'))
                if 'U' in stage_prefix or 'TU' in stage_prefix:  # 车胎类别(UC)与斜胶类别(U)需要区分
                    queryset = queryset.filter(~Q(product_info__product_name__startswith='UC'), ~Q(product_info__product_name__startswith='TUC'))
            if wms_material_name:
                queryset = queryset.filter(Q(batching_details__material__material_name=wms_material_name,
                                             batching_details__delete_flag=False) |
                                           Q(weight_cnt_types__delete_flag=False,
                                             weight_cnt_types__weight_details__material__material_name=wms_material_name)).distinct()
                if export:
                    now_date = datetime.datetime.now().strftime('%Y-%m-%d')
                    file_name = f"原材料({wms_material_name})使用配方列表{now_date}.xls"
                    data = self.get_serializer(queryset.order_by('id'), many=True).data
                    return gen_template_response(self.EXPORT_FIELDS_DICT, data, file_name)
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
class WFProductBatchingViewSet(ModelViewSet):
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
    queryset = ProductBatching.objects.filter(delete_flag=False, batching_type=3).select_related(
        "factory", "site", "dev_type", "stage", "product_info"
    ).prefetch_related(
        Prefetch('batching_details', queryset=ProductBatchingDetail.objects.filter(delete_flag=False).order_by('sn')),
        Prefetch('weight_cnt_types', queryset=WeighCntType.objects.filter(delete_flag=False)),
        Prefetch('weight_cnt_types__weight_details', queryset=WeighBatchingDetail.objects.filter(
            delete_flag=False).order_by('id')),
    ).order_by('stage_product_batch_no', 'dev_type')
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = ProductBatchingFilter
    EXPORT_FIELDS_DICT = {
        '序号': 'id',
        '配方名称': 'stage_product_batch_no'
    }

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        exclude_used_type = self.request.query_params.get('exclude_used_type')
        filter_type = self.request.query_params.get('filter_type')  # 1-表示已发送(蓝色) 2-表示未发送
        recipe_type = self.request.query_params.get('recipe_type')  # 配方类别(车胎胶料、斜交胎胶料...)
        wms_material_name = self.request.query_params.get('wms_material_name')  # 原材料名称过滤
        print_type = self.request.query_params.get('print_type')  # 胶皮补打[加硫、无硫]过滤
        export = self.request.query_params.get('export')  # 导出涉及上述原材料的配方名称
        if exclude_used_type:
            queryset = queryset.exclude(used_type=exclude_used_type)
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'stage_product_batch_no',
                                   'batching_weight',
                                   'production_time_interval',
                                   'used_type',
                                   'dev_type',
                                   'dev_type__category_name')
            if print_type:
                data = list(set(data.filter(stage__global_name__in=['FM', 'RFM', 'RE'])
                                .values_list('stage_product_batch_no', flat=True))) if print_type == '加硫' else \
                    list(set(data.exclude(stage__global_name__in=['FM', 'RFM', 'RE'])
                             .values_list('stage_product_batch_no', flat=True)))
            return Response({'results': data})
        else:
            if filter_type:
                res_id = []
                recipe_ids = ProductBatchingEquip.objects.filter(is_used=True).values_list('product_batching_id', flat=True).distinct()
                if filter_type == '1':
                    if not recipe_ids:
                        return Response([])
                    for r_id in recipe_ids:
                        enable_equip = list(ProductBatchingEquip.objects.filter(product_batching_id=r_id).values_list('equip_no', flat=True).distinct())
                        send_success_equip = list(ProductBatchingEquip.objects.filter(product_batching_id=r_id, send_recipe_flag=True).values_list('equip_no', flat=True).distinct())
                        if enable_equip != send_success_equip:
                            res_id.append(r_id)
                    queryset = queryset.filter(id__in=res_id)
                elif filter_type == '2':
                    queryset = queryset.exclude(id__in=list(recipe_ids))
            if recipe_type:
                stage_prefix = re.split(r'[,|，]', recipe_type)
                filter_str = ''
                for i in stage_prefix:
                    filter_str += ('' if not filter_str else '|') + f"Q(product_info__product_name__startswith='{i.strip()}')"
                queryset = queryset.filter(eval(filter_str))
                if 'C' in stage_prefix or 'TC' in stage_prefix:  # 车胎类别(C)与半钢类别(CJ)需要区分
                    queryset = queryset.filter(~Q(product_info__product_name__startswith='CJ'), ~Q(product_info__product_name__startswith='TCJ'))
                if 'U' in stage_prefix or 'TU' in stage_prefix:  # 车胎类别(UC)与斜胶类别(U)需要区分
                    queryset = queryset.filter(~Q(product_info__product_name__startswith='UC'), ~Q(product_info__product_name__startswith='TUC'))
            if wms_material_name:
                queryset = queryset.filter(Q(batching_details__material__material_name=wms_material_name,
                                             batching_details__delete_flag=False) |
                                           Q(weight_cnt_types__delete_flag=False,
                                             weight_cnt_types__weight_details__material__material_name=wms_material_name)).distinct()
                if export:
                    now_date = datetime.datetime.now().strftime('%Y-%m-%d')
                    file_name = f"原材料({wms_material_name})使用配方列表{now_date}.xls"
                    data = self.get_serializer(queryset.order_by('id'), many=True).data
                    return gen_template_response(self.EXPORT_FIELDS_DICT, data, file_name)
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
            return WFProductBatchingListSerializer
        elif self.action == 'create':
            return WFProductBatchingCreateSerializer
        elif self.action == 'retrieve':
            return WFProductBatchingRetrieveSerializer
        elif self.action == 'partial_update':
            return ProductBatchingPartialUpdateSerializer
        else:
            return WFProductBatchingUpdateSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete_flag = True
        instance.delete_user = request.user
        instance.save()
        instance.batching_details.filter().update(delete_flag=True, delete_user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name="dispatch")
class ReplaceRecipeMaterialViewSet(ModelViewSet):
    queryset = MultiReplaceMaterial.objects.all().order_by('-times', '-id')
    serializer_class = ReplaceRecipeMaterialSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        origin_material = self.request.query_params.get('origin_material')
        replace_material = self.request.query_params.get('replace_material')
        status = self.request.query_params.get('status')
        filter_kwargs = {}
        if origin_material:
            filter_kwargs['origin_material'] = origin_material
        if origin_material:
            filter_kwargs['replace_material'] = replace_material
        if status:
            filter_kwargs['status'] = status
        queryset = self.queryset.filter(**filter_kwargs)
        return queryset

    def list(self, request, *args, **kwargs):
        replace_ids_str = self.request.query_params.get('replace_ids')
        replace_ids = re.split(r'[,|，]', replace_ids_str)
        max_times = self.queryset.aggregate(max_times=Max('times'))['max_times']
        times = 1 if not max_times else max_times
        queryset = self.get_queryset().filter(product_batching_id__in=replace_ids, times=times)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        origin_material = self.request.data.get('origin_material')
        replace_material = self.request.data.get('replace_material')
        replace_ids_str = self.request.data.get('replace_ids')
        if not all([origin_material, replace_material, replace_ids_str]):
            raise ValidationError('检查参数是否完整')
        replace_ids = re.split(r'[,|，]', replace_ids_str)
        # 校验原材料信息
        wms_instance = Material.objects.filter(delete_flag=False, use_flag=True, material_name=origin_material).last()
        replace_instance = Material.objects.filter(delete_flag=False, use_flag=True, material_name=replace_material).last()
        if not all([wms_instance, replace_instance]):
            raise ValidationError('请检查所选择物料在mes的状态')
        # 获取群控原材料信息
        sfj_origin_instance = Material.objects.using('SFJ').filter(delete_flag=False, use_flag=True,
                                                                   material_name=origin_material).last()
        sfj_replace_instance = Material.objects.using('SFJ').filter(delete_flag=False, use_flag=True,
                                                                    material_name=replace_material).last()
        if not all([sfj_origin_instance, sfj_replace_instance]):
            raise ValidationError('请检查所选择物料在群控的状态')
        max_times = MultiReplaceMaterial.objects.all().aggregate(max_times=Max('times'))['max_times']
        times = 1 if not max_times else max_times + 1
        multi_created_list = []
        for i in replace_ids:
            if not i:
                continue
            mes_recipe = ProductBatching.objects.filter(id=i).last()
            created_data = {'origin_material': origin_material, 'replace_material': replace_material,
                            'created_user': self.request.user, 'created_date': datetime.datetime.now(),
                            'product_batching': mes_recipe, 'times': times}
            batching_detail = mes_recipe.batching_details.filter(delete_flag=False, material=wms_instance)
            if not batching_detail:
                created_data.update({'failed_reason': '配方中无此物料(胶料、炭黑、油料)'})
                multi_created_list.append(MultiReplaceMaterial(**created_data))
                continue
            mes_exist = mes_recipe.batching_details.filter(delete_flag=False, material=replace_instance)
            if mes_exist:
                created_data.update({'failed_reason': '配方中已经存在被替换物料'})
                multi_created_list.append(MultiReplaceMaterial(**created_data))
                continue
            # 查询群控配方 9-17:不操作群控废弃配方
            sfj_recipe = ProductBatching.objects.using('SFJ').filter(~Q(used_type=6), batching_type=1,
                                                                     stage_product_batch_no=mes_recipe.stage_product_batch_no,
                                                                     equip__category__category_no=mes_recipe.dev_type.category_name)
            if not sfj_recipe:
                created_data.update({'failed_reason': '未找到群控配方'})
                multi_created_list.append(MultiReplaceMaterial(**created_data))
                continue
            # 查看配方是否都在密炼(默认全部失败, 否则影响防错)
            limit_date = datetime.datetime.now().date() - datetime.timedelta(days=1)
            processing_plan = ProductClassesPlan.objects.using('SFJ').filter(delete_flag=False, created_date__date__gte=limit_date, product_batching__in=sfj_recipe, status__in=['等待', '运行中'])
            processing_recipe = set(processing_plan.values_list('equip__equip_no', flat=True))
            if processing_recipe:
                for j in processing_recipe:
                    s_recipe = sfj_recipe.filter(equip__equip_no=j).last()
                    sfj_product_batching = None if not s_recipe else s_recipe.id
                    created_data.update({'failed_reason': '存在机台正在密炼的群控配方', 'equip_no': j, 'sfj_product_batching': sfj_product_batching})
                    multi_created_list.append(MultiReplaceMaterial(**created_data))
                continue
            with atomic(using='SFJ'):
                # 群控存在无法替换
                sfj_exist = ProductBatchingDetail.objects.using('SFJ').filter(delete_flag=False,
                                                                              product_batching__in=sfj_recipe,
                                                                              material=sfj_replace_instance)
                if sfj_exist:
                    for s_exist in sfj_exist:
                        created_data.update({'failed_reason': '群控配方中已经存在被替换物料',
                                             'equip_no': s_exist.product_batching.equip.equip_no,
                                             'sfj_product_batching': s_exist.product_batching.id})
                        multi_created_list.append(MultiReplaceMaterial(**created_data))
                    continue
                # 如果替换的是炭黑或者油料物质, 需要判断是否存在日料罐中
                other_sfj_recipe = sfj_recipe.exclude(id__in=set(sfj_exist.values_list('product_batching_id', flat=True)))
                if not other_sfj_recipe:
                    continue
                # 替换群控
                sfj_detail = ProductBatchingDetail.objects.using('SFJ').filter(delete_flag=False,
                                                                               product_batching__in=other_sfj_recipe,
                                                                               material=sfj_origin_instance)
                if not sfj_detail:
                    continue
                # 两种物料在配方中均不存在
                both_not_found = other_sfj_recipe.exclude(id__in=set(sfj_detail.values_list('product_batching_id', flat=True)))
                if both_not_found:
                    for k in both_not_found:
                        not_found_equip_no = k.equip.equip_no
                        created_data.update({'failed_reason': f'{not_found_equip_no}配方两种物料均不存在',
                                             'equip_no': not_found_equip_no,
                                             'sfj_product_batching': k.id})
                        multi_created_list.append(MultiReplaceMaterial(**created_data))
                success_equips = []
                for s_detail in sfj_detail:
                    s_equip_no = s_detail.product_batching.equip.equip_no
                    if s_detail.type in [2, 3]:
                        check_type = s_detail.type - 1
                        tank = MaterialTankStatus.objects.filter(equip_no=s_equip_no, tank_type=check_type, material_no=replace_material).first()
                        if not tank:
                            created_data.update({'failed_reason': f'{s_equip_no}日料罐不存在替换物料',
                                                 'equip_no': s_equip_no, 'sfj_product_batching': s_detail.product_batching.id})
                            multi_created_list.append(MultiReplaceMaterial(**created_data))
                            continue
                    success_equips.append(s_equip_no)
                if not success_equips:
                    break
                wait_update = sfj_detail.filter(product_batching__equip__equip_no__in=success_equips)
                # 09-17: 不修改停用配方的状态
                sfj_recipe.filter(id__in=wait_update.exclude(product_batching__used_type=7).values_list('product_batching_id', flat=True)).update(used_type=1)
                wait_update.update(**{'material': sfj_replace_instance})
            for s_instance in sfj_recipe:
                equip_no = s_instance.equip.equip_no
                created_data['equip_no'] = equip_no
                if equip_no in success_equips:
                    created_data.update({'status': '成功', 'sfj_product_batching': s_instance.id})
                multi_created_list.append(MultiReplaceMaterial(**created_data))
            with atomic():
                # 替换mes
                update_data = {'handle_material_name': replace_material, 'material': replace_instance,
                               'batching_detail_equip_id': batching_detail.last().id}
                batching_detail.update(**{'material': replace_instance})
                ProductBatchingEquip.objects.filter(product_batching=mes_recipe, material=wms_instance).update(**update_data)
        # 保留本次替换记录
        MultiReplaceMaterial.objects.bulk_create(multi_created_list)
        return Response({'results': "替换操作执行完成"})


@method_decorator([api_recorder], name="dispatch")
class ProductBatchingNoNew(APIView):
    permission_class = (IsAuthenticated,)

    @atomic
    def post(self, request):
        opera_type = self.request.data.get('opera_type')
        product_batching_id = self.request.data.get('product_batching_id')
        if opera_type == 1:  # 删除可用机台
            equip_nos = set(self.request.data.get('equip_no_list'))
            if not equip_nos:
                raise ValidationError('未选择要删除的可用机台')
            # 查询可用机台
            recipe_info = ProductBatchingEquip.objects.filter(product_batching_id=product_batching_id)
            enable_equips = set(recipe_info.values_list('equip_no', flat=True))
            if not enable_equips:
                raise ValidationError('配方未设置可用机台')
            if equip_nos - enable_equips or equip_nos == enable_equips:
                raise ValidationError('检查配方可用机台和删除机台列表的设置')
            # 删除可用机台
            recipe_info.filter(equip_no__in=equip_nos).delete()
        elif opera_type == 2:  # 胶料单配设定变更
            single_manual = self.request.data.get('single_manual')
            recipe_info = ProductBatchingEquip.objects.filter(product_batching_id=product_batching_id)
            if not recipe_info:
                raise ValidationError('未设置配方可用机台, 不可修改胶料单配设置')
            for i in single_manual:
                nid, is_manual = i.get('id', 0), i.get('is_manual', False)
                recipe_info.filter(batching_detail_equip_id=nid).update(**{'is_manual': is_manual})
        else:  # 对搭比例设置
            flag = True
            mixed_ratio = self.request.data.get('mixed_ratio')
            instance = ProductBatching.objects.filter(id=product_batching_id).last()
            mixed = ProductBatchingMixed.objects.filter(product_batching_id=product_batching_id)
            if not mixed_ratio:
                if not mixed:
                    raise ValidationError('配方无对搭设置可修改')
                else:  # 清理掉对搭设置
                    mixed.delete()
                    flag = False
            if flag:
                feeds, ratios = mixed_ratio['stage'], mixed_ratio['ratio']
                f_s, f_stage = get_mixed(instance)
                if not f_s:
                    raise ValidationError('对搭设置的段次信息在配方中不存在')
                f_name, f_weight, s_weight = f_s.material.material_name, round(float(f_s.actual_weight) * (ratios['f_ratio'] / sum(ratios.values())), 3), round(float(f_s.actual_weight) * (ratios['s_ratio'] / sum(ratios.values())), 3)
                # 查询对搭设置
                use_data = {'f_feed': feeds['f_feed'], 's_feed': feeds['s_feed'], 's_weight': s_weight,
                            'f_feed_name': f_name.replace(f_stage, feeds['f_feed']), 'f_ratio': ratios['f_ratio'],
                            's_feed_name': f_name.replace(f_stage, feeds['s_feed']), 's_ratio': ratios['s_ratio'],
                            'f_weight': f_weight, 'origin_material_name': f_name}
                if not mixed:  # 不存在新增
                    use_data.update({'product_batching': instance})
                    ProductBatchingMixed.objects.create(**use_data)
                else:  # 存在则更新
                    ProductBatchingMixed.objects.update(**use_data)
        return Response('操作成功')


@method_decorator([api_recorder], name="dispatch")
class RecipeNoticeAPiView(APIView):
    """配方数据下发至上辅机（只有应用状态的配方才可下发）"""
    permission_classes = (IsAuthenticated,)

    @atomic()
    def post(self, request):
        product_batching_id = self.request.query_params.get('product_batching_id')
        product_no = self.request.query_params.get('product_no')
        real_product_no = product_no.split('_NEW')[0]
        notice_flag = self.request.query_params.get('notice_flag')
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
        if not notice_flag:
            # 查询群控是否存在同名配方
            sfj_same_recipe = ProductBatching.objects.using('SFJ').exclude(used_type__in=[6]).filter(stage_product_batch_no=real_product_no)
            if sfj_same_recipe:
                return Response({'notice_flag': True})
        # 发送配方的返回信息
        receive_msg = ""
        enable_equip_info = ProductBatchingEquip.objects.filter(product_batching_id=product_batching_id, is_used=True, send_recipe_flag=False)
        enable_equip = list(enable_equip_info.values_list('equip_no', flat=True).distinct())
        if not enable_equip:
            raise ValidationError('配方已经发送到相应机台或未找到配方投料设置信息')
        # 过滤掉有等待或者运行中的群控配方
        n_date = datetime.datetime.now().date() - datetime.timedelta(days=1)
        send_equip, check_msg = [], ''
        for single_equip_no in enable_equip:
            pcp_obj = ProductClassesPlan.objects.using('SFJ').filter(delete_flag=False, created_date__date__gte=n_date,
                                                                     product_batching__stage_product_batch_no=real_product_no,
                                                                     equip__equip_no=single_equip_no).last()
            if pcp_obj:
                plan_status = PlanStatus.objects.using('SFJ').filter(plan_classes_uid=pcp_obj.plan_classes_uid).last()
                if plan_status.status in ['运行中', '等待']:
                    check_msg += f"{single_equip_no}: 配方正在密炼, 无法下发 "
                    receive_msg += f"{single_equip_no}: 配方正在密炼, 无法下发 "
                else:
                    send_equip.append(single_equip_no)
            else:  # 炭黑罐或者油料罐物料不一致时无法发送
                c_o = enable_equip_info.filter(Q(feeding_mode__startswith='C', type=2) | Q(feeding_mode__startswith='O', type=3), equip_no=single_equip_no)
                if c_o:
                    for s_c_o in c_o:
                        tank = MaterialTankStatus.objects.using('SFJ').filter(equip_no=single_equip_no, use_flag=True, tank_type=s_c_o.type - 1, material_name=s_c_o.handle_material_name).first()
                        if not tank:
                            check_msg += f"{single_equip_no}: 物料设定异常:{s_c_o.handle_material_name} "
                            receive_msg += f"{single_equip_no}: 物料设定异常:{s_c_o.handle_material_name} "
                            break
                    else:
                        send_equip.append(single_equip_no)
                else:
                    send_equip.append(single_equip_no)
        if not send_equip:
            raise ValidationError(check_msg)
        interface = ProductBatchingSyncInterface(instance=product_batching, context={'enable_equip': send_equip})
        try:
            interface.request()
        except Exception as e:
            receive_msg += f"{'、'.join(send_equip)}: {e.args[0]} "
        else:
            _now_time, _username = datetime.datetime.now(), self.request.user.username
            try:
                # MES配方变更履历
                change_data = {
                    'recipe_no': real_product_no,
                    'dev_type': product_batching.dev_type.category_name,
                    'used_type': product_batching.used_type,
                    'created_time': product_batching.created_date,
                    'created_username': '' if not product_batching.created_user else product_batching.created_user.username,
                    'updated_time': datetime.datetime.now(),
                    'updated_username': self.request.user.username
                }
                change_history, _ = RecipeChangeHistory.objects.update_or_create(defaults=change_data,
                                                                                 **{'recipe_no': real_product_no,
                                                                                    'dev_type': product_batching.dev_type.category_name})
                record = change_history.change_details.order_by('id').last()
                if not record:
                    RecipeChangeDetail.objects.create(change_history=change_history, desc='MES配方新增',
                                                      changed_username=_username, submit_username=product_batching.submit_user.username,
                                                      submit_time=product_batching.submit_time, confirm_username=product_batching.check_user.username,
                                                      confirm_time=product_batching.check_time, sfj_down_username=_username,
                                                      sfj_down_time=_now_time, details='')
                else:
                    if 'NEW' in product_no:
                        old_mes_recipe = ProductBatching.objects.filter(stage_product_batch_no=real_product_no, batching_type=2,
                                                                        dev_type=product_batching.dev_type).last()
                        if not old_mes_recipe:
                            raise ValueError('未找到旧配方无法比较')
                        # 当前配方详情
                        current_recipe_dict = old_mes_recipe.batching_details_info
                        # 修改后配方详情
                        now_recipe_dict = product_batching.batching_details_info
                        added_material = set(now_recipe_dict.keys()) - set(current_recipe_dict.keys())
                        deleted_material = set(current_recipe_dict.keys()) - set(now_recipe_dict.keys())
                        common_material = set(current_recipe_dict.keys()) & set(now_recipe_dict.keys())
                        # 修改后配方详情
                        desc = []
                        change_detail_data = {1: [], 2: [], 3: []}
                        # 比对配料、比对投料方式、称量误差
                        if added_material:
                            desc.append('新增配料')
                            for i in added_material:
                                material_type = now_recipe_dict[i].get('type') if now_recipe_dict[i].get('type') else 4
                                change_detail_data[1].append({'type': material_type, 'key': i, 'flag': '新增', 'cv': float(now_recipe_dict[i]['actual_weight'])})
                            f_equip = product_batching.product_batching_equip.filter(material__material_name__in=added_material, is_used=True).values('material__material_name', 'equip_no', 'feeding_mode', 'type')
                            if f_equip:
                                _temp = {}
                                for j in f_equip:
                                    _material_name = j['material__material_name']
                                    if _material_name not in _temp:
                                        _temp[_material_name] = {'type': j['type'], 'key': _material_name, 'flag': '新增',
                                                                 'cv': f"{j['feeding_mode']}({j['equip_no']})"}
                                    else:
                                        _temp[_material_name]['cv'] = _temp[_material_name]['cv'] + f" {j['feeding_mode']}({j['equip_no']})"
                                desc.append('新增投料方式')
                                change_detail_data[2].extend(list(_temp.values()))
                        if deleted_material:
                            desc.append('删除配料')
                            for i in deleted_material:
                                material_type = current_recipe_dict[i].get('type') if current_recipe_dict[i].get('type') else 4
                                change_detail_data[1].append({'type': material_type, 'key': i, 'flag': '删除'})
                            f_equip = old_mes_recipe.product_batching_equip.filter(material__material_name__in=deleted_material, is_used=True).values(
                                'material__material_name', 'equip_no', 'feeding_mode', 'type')
                            if f_equip:
                                _temp = {}
                                for j in f_equip:
                                    _material_name = j['material__material_name']
                                    if _material_name not in _temp:
                                        _temp[_material_name] = {'type': j['type'], 'key': _material_name, 'flag': '删除',
                                                                 'cv': f"{j['feeding_mode']}({j['equip_no']})"}
                                    else:
                                        _temp[_material_name]['cv'] = _temp[_material_name]['cv'] + f" {j['feeding_mode']}({j['equip_no']})"
                                desc.append('删除投料方式')
                                change_detail_data[2].extend(list(_temp.values()))
                        if common_material:
                            for i in common_material:
                                material_type = now_recipe_dict[i].get('type') if now_recipe_dict[i].get('type') else 4
                                cv = now_recipe_dict[i]['actual_weight']
                                pv = current_recipe_dict[i]['actual_weight']

                                cv2 = now_recipe_dict[i]['standard_error']
                                pv2 = current_recipe_dict[i]['standard_error']
                                if pv != cv:
                                    desc.append('配料修改')
                                    change_detail_data[1].append({'type': material_type, 'key': i, 'flag': '修改', 'cv': float(cv), 'pv': float(pv)})
                                if pv2 != cv2:
                                    desc.append('称量误差')
                                    change_detail_data[3].append({'type': material_type, 'key': i, 'flag': '修改', 'cv': float(cv2), 'pv': float(pv2)})
                            c_equip = product_batching.product_batching_equip.filter(material__material_name__in=common_material, is_used=True).values(
                                'material__material_name', 'equip_no', 'feeding_mode', 'type')
                            c_equips = set(c_equip.values_list('equip_no', flat=True))
                            v_equip = old_mes_recipe.product_batching_equip.filter(material__material_name__in=common_material, is_used=True).values(
                                'material__material_name', 'equip_no', 'feeding_mode', 'type')
                            v_equips = set(v_equip.values_list('equip_no', flat=True))
                            added_equip = c_equips - v_equips
                            deleted_equip = v_equips - c_equips
                            common_equip = c_equips & v_equips
                            if added_equip:
                                add_info = c_equip.filter(equip_no__in=added_equip)
                                _temp = {}
                                for j in add_info:
                                    _material_name = j['material__material_name']
                                    if _material_name not in _temp:
                                        _temp[_material_name] = {'type': j['type'], 'key': _material_name, 'flag': '新增',
                                                                 'cv': f"{j['feeding_mode']}({j['equip_no']})"}
                                    else:
                                        _temp[_material_name]['cv'] = _temp[_material_name]['cv'] + f" {j['feeding_mode']}({j['equip_no']})"
                                desc.append('新增投料方式')
                                change_detail_data[2].extend(list(_temp.values()))
                            if deleted_equip:
                                deleted_info = v_equip.filter(equip_no__in=deleted_equip)
                                _temp = {}
                                for j in deleted_info:
                                    _material_name = j['material__material_name']
                                    if _material_name not in _temp:
                                        _temp[_material_name] = {'type': j['type'], 'key': _material_name, 'flag': '删除',
                                                                 'cv': f"{j['feeding_mode']}({j['equip_no']})"}
                                    else:
                                        _temp[_material_name]['cv'] = _temp[_material_name]['cv'] + f" {j['feeding_mode']}({j['equip_no']})"
                                desc.append('删除投料方式')
                                change_detail_data[2].extend(list(_temp.values()))
                            if common_equip:
                                for i in common_material:
                                    s, _cv = {}, ""
                                    for s_equip_no in common_equip:
                                        common_info1 = c_equip.filter(equip_no=s_equip_no, material__material_name=i).last()
                                        common_info2 = v_equip.filter(equip_no=s_equip_no, material__material_name=i).last()
                                        if common_info1['feeding_mode'] != common_info2['feeding_mode']:
                                            _cv += f"{common_info2['feeding_mode']}->{common_info1['feeding_mode']}({s_equip_no}) "
                                        else:
                                            continue
                                        if not s:
                                            s.update({'type': common_info1['type'], 'key': i, 'flag': '修改'})
                                    if _cv:
                                        s['cv'] = _cv
                                        desc.append('修改投料方式')
                                        change_detail_data[2].append(s)
                        if desc:
                            RecipeChangeDetail.objects.create(
                                change_history=change_history, desc='/'.join(set(desc)), details=json.dumps(change_detail_data, ensure_ascii=False),
                                changed_username=_username, submit_username=product_batching.submit_user.username,
                                submit_time=product_batching.submit_time, confirm_username=product_batching.check_user.username,
                                confirm_time=product_batching.check_time, sfj_down_username=_username, sfj_down_time=_now_time)
                    else:
                        record.sfj_down_time = _now_time
                        record.sfj_down_username = _username
                        record.save()
            except Exception as e:
                error_logger.error(f'更新配方履历变更失败{e.args[0]}')
            for p in ProductBatching.objects.filter(batching_type=1,
                                                    stage_product_batch_no=product_batching.stage_product_batch_no,
                                                    dev_type=product_batching.dev_type):
                p.batching_details.all().delete()
            # NEW配方下传成功：1、废弃旧配方；2、修改配方名称；
            if 'NEW' in product_no:
                # 废弃原配方
                old_mes_recipe = ProductBatching.objects.filter(stage_product_batch_no=real_product_no, batching_type=2,
                                                                dev_type=product_batching.dev_type)
                old_mes_recipe.update(used_type=6)
                # 清除机台配方
                ProductBatchingEquip.objects.filter(product_batching_id__in=old_mes_recipe).update(is_used=False)
                # 去除配方里的_NEW
                product_batching.stage_product_batch_no = real_product_no
                product_batching.save()
                # 更新对搭表
                mixed = ProductBatchingMixed.objects.filter(product_batching=product_batching)
                if mixed:
                    f_feed_name, s_feed_name = mixed.last().f_feed_name.split('_NEW')[0], mixed.last().s_feed_name.split('_NEW')[0]
                    mixed.update(**{'f_feed_name': f_feed_name, 's_feed_name': s_feed_name})
            ProductBatchingEquip.objects.filter(product_batching_id=product_batching_id, equip_no__in=send_equip).update(send_recipe_flag=True)
            receive_msg += f"{'、'.join(send_equip)}: 配方下发成功 "
        return Response(data={'auxiliary_url': settings.AUXILIARY_URL, 'send_recipe_msg': receive_msg}, status=status.HTTP_200_OK)


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
            used_type__in=[6]).filter(stage_product_batch_no=data['stage_product_batch_no'], batching_type=2,
                                      dev_type__category_no=data['dev_type__category_no']).first()
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
        if product_batching:
            product_batching.batching_details.all().delete()
        else:
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
        try:
            material_type = GlobalCode.objects.filter(global_type__type_name='原材料类别',
                                                      global_name=product_batching.stage.global_name).first()
            Material.objects.get_or_create(
                material_no=product_batching.stage_product_batch_no,
                material_name=product_batching.stage_product_batch_no,
                material_type=material_type
            )
        except Exception as e:
            pass
        for item in data['batching_details']:
            item['product_batching'] = product_batching
            ProductBatchingDetail.objects.create(**item)
        product_batching.save()
        return Response('ok')


class DevTypeProductBatching(APIView):

    def get(self, request):
        dev_type = self.request.query_params.get('dev_type')
        product_no = self.request.query_params.get('product_no')
        if not all([dev_type, product_no]):
            raise ValidationError('参数不足')
        instance = ProductBatching.objects.exclude(
            used_type__in=[6]).filter(
            dev_type__category_no=dev_type,
            stage_product_batch_no=product_no,
            batching_type=2
        ).first()
        if instance:
            s = ProductBatchingDetailRetrieveSerializer(
                instance=instance.batching_details.filter(delete_flag=False), many=True)
            return Response(s.data)
        else:
            return Response({})


class ProductRatioView(ListAPIView):
    queryset = ProductBatching.objects.all()

    def list(self, request, *args, **kwargs):
        used_type = self.request.query_params.get('used_type')
        recipe_type = self.request.query_params.get('recipe_type')
        dev_type = self.request.query_params.get('dev_type')
        stage_product_batch_no = self.request.query_params.get('stage_product_batch_no')
        material_names = self.request.query_params.get('material_names')
        if not material_names:
            raise ValidationError('请选择原材料查询！')
        material_names = material_names.split(',')
        names = []
        for name in material_names:
            strip_name1 = name+'-C'
            strip_name2 = name+'-X'
            names.append(strip_name1)
            names.append(strip_name2)
            names.append(name)
        material_ids = list(Material.objects.filter(material_name__in=names).values_list('id', flat=True))
        queryset = ProductBatching.objects.exclude(used_type=6).filter(batching_type=2)

        if used_type:
            queryset = queryset.filter(used_type=used_type)
        if recipe_type:
            stage_prefix = re.split(r'[,|，]', recipe_type)
            product_nos = list(ProductInfo.objects.values_list('product_no', flat=True))
            filter_product_nos = list(
                filter(lambda x: ''.join(re.findall(r'[A-Za-z]', x)) in stage_prefix, product_nos))
            queryset = queryset.filter(product_info__product_no__in=filter_product_nos)
        if dev_type:
            queryset = queryset.filter(dev_type_id=dev_type)
        if stage_product_batch_no:
            queryset = queryset.filter(stage_product_batch_no__icontains=stage_product_batch_no)
        if material_ids:
            pb_ids1 = list(queryset.filter(batching_details__material_id__in=material_ids).values_list('id', flat=True))
            pb_ids2 = list(WeighBatchingDetail.objects.filter(
                material_id__in=material_ids,
                delete_flag=0,
                weigh_cnt_type__delete_flag=0
            ).values_list('weigh_cnt_type__product_batching_id', flat=True))
            queryset = queryset.filter(id__in=set(pb_ids1+pb_ids2))
        page = self.paginate_queryset(queryset)
        ret = []
        pt_dict = {}
        pt = GlobalCode.objects.filter(global_type__type_name='配方类别').order_by('id').values('global_no', 'global_name')
        for item in pt:
            type_name = item['global_no']
            for i in item['global_name'].split(','):
                pt_dict[i] = type_name
        for item in page:
            dev_type_name = item.dev_type.category_name
            used_type = item.used_type
            stage_product_batch_no = item.stage_product_batch_no
            details1 = list(item.batching_details.filter(
                delete_flag=0,
                material_id__in=material_ids).values('material__material_name', 'actual_weight'))
            details2 = list(WeighBatchingDetail.objects.filter(
                        material_id__in=material_ids,
                        delete_flag=0,
                        weigh_cnt_type__delete_flag=0,
                        weigh_cnt_type__product_batching_id=item.id
            ).values(material__material_name=F('material__material_name'), actual_weight=F('standard_weight')))
            details = details1 + details2
            try:
                re_result = re.match(r'[A-Z]+', stage_product_batch_no.split('-')[2])
                if not re_result:
                    recipe_type = '未知'
                else:
                    recipe_type = pt_dict.get(re_result.group(), '未知')
            except Exception:
                recipe_type = '未知'
            ret.append({
                'recipe_type': recipe_type,
                'dev_type_name': dev_type_name,
                'used_type': used_type,
                'stage_product_batch_no': stage_product_batch_no,
                'detail': [{'material_name': i['material__material_name'].rstrip('-C').rstrip('-X'),
                            'weight': i['actual_weight']} for i in details]
            })
        return Response({'results': ret, 'count': queryset.count()})


@method_decorator([api_recorder], name="dispatch")
class RecipeChangeHistoryViewSet(ModelViewSet):
    queryset = RecipeChangeHistory.objects.order_by('recipe_no')
    filter_backends = (DjangoFilterBackend,)
    filter_class = RecipeChangeHistoryFilter
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return RecipeChangeHistoryRetrieveSerializer
        return RecipeChangeHistorySerializer

    def list(self, request, *args, **kwargs):
        used_types = self.request.query_params.get('used_types')
        queryset = self.filter_queryset(self.get_queryset())
        if used_types:
            queryset = queryset.filter(used_type__in=used_types.split(','))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
