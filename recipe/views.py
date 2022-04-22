# Create your views here.
import datetime
import re

from django.db.models import Prefetch, Q, Max
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
from equipment.utils import gen_template_response
from mes import settings
from mes.derorators import api_recorder
from mes.sync import ProductBatchingSyncInterface
from plan.models import ProductClassesPlan
from production.models import PlanStatus
from recipe.filters import MaterialFilter, ProductInfoFilter, ProductBatchingFilter, \
    MaterialAttributeFilter, ERPMaterialFilter, ZCMaterialFilter
from recipe.serializers import MaterialSerializer, ProductInfoSerializer, \
    ProductBatchingListSerializer, ProductBatchingCreateSerializer, MaterialAttributeSerializer, \
    ProductBatchingRetrieveSerializer, ProductBatchingUpdateSerializer, \
    ProductBatchingPartialUpdateSerializer, MaterialSupplierSerializer, \
    ProductBatchingDetailMaterialSerializer, WeighCntTypeSerializer, ERPMaterialCreateSerializer, ERPMaterialSerializer, \
    ERPMaterialUpdateSerializer, ZCMaterialSerializer, ProductBatchingDetailRetrieveSerializer, \
    ReplaceRecipeMaterialSerializer
from recipe.models import Material, ProductInfo, ProductBatching, MaterialAttribute, \
    ProductBatchingDetail, MaterialSupplier, WeighCntType, WeighBatchingDetail, ZCMaterial, ERPMESMaterialRelation, \
    ProductBatchingEquip, ProductBatchingMixed, MultiReplaceMaterial


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
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            if self.request.query_params.get('exclude_stage'):
                stage_names = GlobalCode.objects.filter(
                    global_type__type_name='胶料段次').values_list('global_name', flat=True)
                queryset = queryset.exclude(material_type__global_name__in=stage_names)
            else:
                queryset = queryset.filter(use_flag=1)
                if mc_code:  # 通用卡片需排出没有erp绑定关系和物料类型为胶料段次的物料
                    stages = list(GlobalCode.objects.filter(use_flag=True, global_type__use_flag=True, global_type__type_name='胶料段次').values_list('global_name', flat=True))
                    erp_materials = set(ERPMESMaterialRelation.objects.filter(~Q(material__material_type__global_name__in=stages), use_flag=True).values_list('material__material_name', flat=True))
                    queryset = queryset.filter(~Q(Q(material_name__endswith='-C') | Q(material_name__endswith='-X')), material_name__in=erp_materials)
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
                    used_type__in=[6, 7]).filter(stage_product_batch_no=stage_product_batch_no, factory__isnull=True,
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
        product_batching = ProductBatching.objects.exclude(used_type__in=[6, 7]).filter(site_id=site,
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
                queryset = queryset.filter(Q(batching_details__material__material_name=wms_material_name) |
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
            raise ValidationError('请检查所选择物料在群控中的状态')
        max_times = MultiReplaceMaterial.objects.all().aggregate(max_times=Max('times'))['max_times']
        times = 1 if not max_times else max_times + 1
        for i in replace_ids:
            recipe = ProductBatching.objects.filter(id=i).last()
            created_data = {'origin_material': origin_material, 'replace_material': replace_material,
                            'created_user': self.request.user, 'created_date': datetime.datetime.now(),
                            'product_batching': recipe, 'times': times}
            # 查询群控配方
            sfj_recipe = ProductBatching.objects.using('SFJ').filter(
                stage_product_batch_no=recipe.stage_product_batch_no,
                dev_type__category_name=recipe.dev_type.category_name,
                batching_type=1)
            if not sfj_recipe:
                created_data.update({'failed_reason': '未找到群控配方'})
                MultiReplaceMaterial.objects.create(**created_data)
                continue
            # 查看配方是否都在密炼
            processing_recipe = ProductClassesPlan.objects.using('SFJ').filter(
                product_batching__in=list(sfj_recipe), status__in=['等待', '运行中'])
            if processing_recipe:
                created_data.update({'failed_reason': '存在机台正在密炼的群控配方'})
                MultiReplaceMaterial.objects.create(**created_data)
                continue
            with atomic():
                # 替换mes
                update_data = {}
                batching_detail = recipe.batching_details.filter(delete_flag=False, material=wms_instance)
                xl_info = recipe.weight_cnt_types.filter(delete_flag=False)
                xl_detail = xl_info.last().weight_details.filter(delete_flag=False, material=wms_instance) if xl_info else None
                if batching_detail:
                    update_data.update({'handle_material_name': replace_material, 'material': replace_instance,
                                        'batching_detail_equip_id': batching_detail.last().id})
                    batching_detail.update(**{'material': replace_instance})
                elif xl_detail:
                    update_data.update(
                        {'handle_material_name': replace_material.rstrip('-C|-X'), 'material': replace_instance,
                         'cnt_type_detail_equip_id': xl_detail.last().id})
                    xl_detail.update(**{'material': replace_instance})
                else:
                    created_data.update({'failed_reason': '配方中未找到该原材料'})
                    MultiReplaceMaterial.objects.create(**created_data)
                    continue
                ProductBatchingEquip.objects.filter(product_batching=recipe, material=wms_instance).update(
                    **update_data)

            with atomic(using='SFJ'):
                # 替换群控
                sfj_detail = ProductBatchingDetail.objects.using('SFJ').filter(delete_flag=False,
                                                                               product_batching__in=list(sfj_recipe),
                                                                               material=sfj_origin_instance)
                equip_no_list = set(sfj_detail.values_list('product_batching__equip__equip_no', flat=True))
                sfj_detail.update(**{'material': sfj_replace_instance})
            for equip_no in equip_no_list:
                created_data.update({'status': '成功', 'equip_no': equip_no})
                MultiReplaceMaterial.objects.create(**created_data)
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
            mixed_ratio = self.request.data.get('mixed_ratio')
            feeds, ratios = mixed_ratio['stage'], mixed_ratio['ratio']
            instance = ProductBatching.objects.filter(id=product_batching_id).last()
            f_s = instance.batching_details.filter(Q(material__material_name__icontains=feeds['f_feed']) | Q(
                material__material_name__icontains=feeds['s_feed'])).last()
            if not f_s:
                raise ValidationError('对搭设置的段次信息在配方中不存在')
            f_weight, s_weight = round(float(f_s.actual_weight) * (ratios['f_ratio'] / sum(ratios.values())), 3), \
                                 round(float(f_s.actual_weight) * (ratios['s_ratio'] / sum(ratios.values())), 3)
            # 查询对搭设置
            mixed = ProductBatchingMixed.objects.filter(product_batching_id=product_batching_id)
            use_data = {'f_feed': feeds['f_feed'], 's_feed': feeds['s_feed'], 's_weight': s_weight,
                        'f_feed_name': instance.stage_product_batch_no.replace(instance.stage.global_name, feeds['f_feed']),
                        's_feed_name': instance.stage_product_batch_no.replace(instance.stage.global_name, feeds['s_feed']),
                        'f_ratio': ratios['f_ratio'], 's_ratio': ratios['s_ratio'], 'f_weight': f_weight}
            if not mixed:  # 不存在新增
                use_data.update({'product_batching': instance})
                ProductBatchingMixed.objects.create(**use_data)
            else:  # 存在则更新
                ProductBatchingMixed.objects.update(**use_data)
        return Response('操作成功')


@method_decorator([api_recorder], name="dispatch")
class RecipeNoticeAPiView(APIView):
    """配方数据下发至上辅机（只有应用状态的配方才可下发）"""
    permission_classes = ()
    authentication_classes = ()

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
            sfj_same_recipe = ProductBatching.objects.using('SFJ').exclude(used_type__in=[6, 7]).filter(stage_product_batch_no=real_product_no)
            if sfj_same_recipe:
                return Response({'notice_flag': True})
        # 发送配方的返回信息
        receive_msg = ""
        enable_equip = list(ProductBatchingEquip.objects.filter(product_batching_id=product_batching_id, is_used=True, send_recipe_flag=False)
                            .values_list('equip_no', flat=True).distinct())
        if not enable_equip:
            raise ValidationError('配方已经发送到相应机台或未找到配方投料设置信息')
        # 过滤掉有等待或者运行中的群控配方
        n_date = datetime.datetime.now().date() - datetime.timedelta(days=1)
        send_equip = []
        for single_equip_no in enable_equip:
            pcp_obj = ProductClassesPlan.objects.using('SFJ').filter(delete_flag=False, created_date__date__gte=n_date,
                                                                     product_batching__stage_product_batch_no=real_product_no,
                                                                     equip__equip_no=single_equip_no).last()
            if pcp_obj:
                plan_status = PlanStatus.objects.using('SFJ').filter(plan_classes_uid=pcp_obj.plan_classes_uid).last()
                if plan_status.status in ['运行中', '等待']:
                    receive_msg += f"{single_equip_no}: 配方正在密炼, 无法下发 "
                else:
                    send_equip.append(single_equip_no)
            else:
                send_equip.append(single_equip_no)
        if not send_equip:
            raise ValidationError(f"该配方在所选{'、'.join(enable_equip)}机台密炼, 无法下发")
        interface = ProductBatchingSyncInterface(instance=product_batching, context={'enable_equip': send_equip})
        try:
            interface.request()
        except Exception as e:
            receive_msg += f"{'、'.join(send_equip)}: {e.args[0]} "
        else:
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
            used_type__in=[6, 7]).filter(stage_product_batch_no=data['stage_product_batch_no'],
                                         batching_type=2,
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
            used_type__in=[6, 7]).filter(
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