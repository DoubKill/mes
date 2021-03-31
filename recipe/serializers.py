from datetime import datetime
import logging

from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from basics.models import GlobalCode
import uuid
from mes.base_serializer import BaseModelSerializer
from mes.sync import ProductObsoleteInterface
from plan.models import ProductClassesPlan
from recipe.models import Material, ProductInfo, ProductBatching, ProductBatchingDetail, \
    MaterialAttribute, MaterialSupplier, WeighBatchingDetail, WeighCntType
from mes.conf import COMMON_READ_ONLY_FIELDS

logger = logging.getLogger('api_log')
sync_logger = logging.getLogger('sync_log')


class MaterialSerializer(BaseModelSerializer):
    material_no = serializers.CharField(max_length=64, help_text='编码',
                                        validators=[UniqueValidator(queryset=Material.objects.filter(delete_flag=0),
                                                                    message='该原材料已存在')])
    material_type_name = serializers.CharField(source='material_type.global_name', read_only=True)
    package_unit_name = serializers.CharField(source='package_unit.global_name', read_only=True)
    created_user_name = serializers.CharField(source='created_user.username', read_only=True)
    update_user_name = serializers.CharField(source='last_updated_user.username', default=None, read_only=True)
    safety_inventory = serializers.IntegerField(source='material_attr.safety_inventory', read_only=True, default=None)
    period_of_validity = serializers.IntegerField(source='material_attr.period_of_validity', read_only=True,
                                                  default=None)
    validity_unit = serializers.CharField(source='material_attr.validity_unit', read_only=True, default=None)

    def update(self, instance, validated_data):
        validated_data['last_updated_user'] = self.context['request'].user
        return super().update(instance, validated_data)

    class Meta:
        model = Material
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialAttributeSerializer(BaseModelSerializer):

    def create(self, validated_data):
        material = validated_data['material']
        if not hasattr(material, 'material_attr'):
            MaterialAttribute.objects.create(**validated_data)
        else:
            instance = material.material_attr
            return super().update(instance, validated_data)
        return validated_data

    class Meta:
        model = MaterialAttribute
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS
        extra_kwargs = {'material': {'validators': []}}


class MaterialSupplierSerializer(BaseModelSerializer):
    material = serializers.PrimaryKeyRelatedField(queryset=Material.objects.filter(delete_flag=False))
    material_type = serializers.CharField(source='material.material_type.global_name', read_only=True)
    material_no = serializers.CharField(source='material.material_no', read_only=True)
    material_name = serializers.CharField(source='material.material_name', read_only=True)

    def create(self, validated_data):
        validated_data['supplier_no'] = uuid.uuid1()
        return super(MaterialSupplierSerializer, self).create(validated_data)

    class Meta:
        model = MaterialSupplier
        exclude = ('supplier_no',)
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ProductInfoSerializer(BaseModelSerializer):
    update_username = serializers.CharField(source='last_updated_user.username', read_only=True)

    class Meta:
        model = ProductInfo
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ProductInfoCopySerializer(BaseModelSerializer):

    def validate(self, attrs):
        versions = attrs['versions']
        factory = attrs['factory']
        product_no = attrs['product_info_id'].product_no
        product_info = ProductInfo.objects.filter(factory=factory, product_no=product_no).order_by('-versions').first()
        if product_info:
            if product_info.versions >= versions:
                raise serializers.ValidationError('版本不得小于目前已有的版本')
        attrs['used_type'] = 1
        return attrs

    @atomic()
    def create(self, validated_data):
        base_product_info = validated_data.pop('product_info_id')
        validated_data['created_user'] = self.context['request'].user
        validated_data['recipe_weight'] = base_product_info.recipe_weight
        validated_data['product_no'] = base_product_info.product_no
        validated_data['product_name'] = base_product_info.product_name
        validated_data['precept'] = base_product_info.precept
        instance = super().create(validated_data)
        return instance

    class Meta:
        model = ProductInfo
        fields = '__all__'


class ProductBatchingDetailSerializer(BaseModelSerializer):
    material = serializers.PrimaryKeyRelatedField(queryset=Material.objects.filter(delete_flag=False, use_flag=1))
    material_type = serializers.CharField(source='material.material_type.global_name', read_only=True)
    material_name = serializers.CharField(source='material.material_name', read_only=True)
    material_no = serializers.CharField(source='material.material_no', read_only=True)

    class Meta:
        model = ProductBatchingDetail
        exclude = ('product_batching',)
        extra_kwargs = {'material': {'validators': []}}


class ProductBatchingDetailRetrieveSerializer(ProductBatchingDetailSerializer):

    class Meta:
        model = ProductBatchingDetail
        exclude = ('product_batching',)
        extra_kwargs = {'material': {'validators': []},
                        'id': {
                            'read_only': False,
                            'allow_null': True,
                            'required': False}
                        }


class ProductBatchingListSerializer(BaseModelSerializer):
    product_no = serializers.CharField(source='product_info.product_no', read_only=True)
    product_name = serializers.CharField(source='product_info.product_name', read_only=True)
    created_user_name = serializers.CharField(source='created_user.username', read_only=True)
    update_user_name = serializers.CharField(source='last_updated_user.username', read_only=True)
    stage_name = serializers.CharField(source="stage.global_name", read_only=True)
    site_name = serializers.CharField(source="site.global_name", read_only=True)
    dev_type_name = serializers.CharField(source='dev_type.category_name', default=None, read_only=True)
    submit_username = serializers.CharField(source="submit_user.username", read_only=True)
    check_username = serializers.CharField(source="check_user.username", read_only=True)
    reject_username = serializers.CharField(source="reject_user.username", read_only=True)
    used_username = serializers.CharField(source="used_user.username", read_only=True)
    obsolete_username = serializers.CharField(source="obsolete_user.username", read_only=True)

    class Meta:
        model = ProductBatching
        fields = '__all__'


class WeighCntTypeDetailCreateSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.material_name', read_only=True)
    material_no = serializers.CharField(source='material.material_no', read_only=True)

    class Meta:
        model = WeighBatchingDetail
        exclude = ('weigh_cnt_type', )


class WeighCntTypeCreateSerializer(serializers.ModelSerializer):
    weight_details = WeighCntTypeDetailCreateSerializer(many=True, required=False)

    class Meta:
        model = WeighCntType
        exclude = ('product_batching', )


class ProductBatchingCreateSerializer(BaseModelSerializer):
    batching_details = ProductBatchingDetailSerializer(many=True, required=False,
                                                       help_text="""
                                                           [{"sn": 序号, "material":原材料id, 
                                                           "actual_weight":重量, "standard_error":误差值}]""")
    weight_cnt_types = WeighCntTypeCreateSerializer(many=True, required=False, help_text="""
    [
        {
            "name": "名称",
            "package_cnt": "分包数量",
            "package_type": "打包类型 1自动 2手动",
            "weight_details": [
                {
                    "material": "原材料id",
                    "standard_weight": "重量",
                    "standard_error": "误差",
                }
            ]
        },
    ]
    """)

    @atomic()
    def create(self, validated_data):
        batching_details = validated_data.pop('batching_details', None)
        weight_cnt_types = validated_data.pop('weight_cnt_types', None)
        stage_product_batch_no = validated_data.get('stage_product_batch_no')
        if stage_product_batch_no:
            # 传胶料编码则代表是特殊配方
            validated_data.pop('site', None)
            validated_data.pop('stage', None)
            validated_data.pop('versions', None)
            validated_data.pop('product_info', None)
        else:
            site = validated_data.get('site')
            stage = validated_data.get('stage')
            product_info = validated_data.get('product_info')
            versions = validated_data.get('versions')
            if not all([site, stage, product_info, versions]):
                raise serializers.ValidationError('参数不足')
            validated_data['stage_product_batch_no'] = '{}-{}-{}-{}'.format(site.global_name, stage.global_name,
                                                                            product_info.product_no, versions)
        instance = super().create(validated_data)
        if batching_details:
            batching_detail_list = [None] * len(batching_details)
            for i, detail in enumerate(batching_details):
                material = detail.get('material')
                detail.pop('id', None)
                if material.material_type.global_name == '炭黑':
                    detail['type'] = 2
                elif material.material_type.global_name == '油料':
                    detail['type'] = 3
                detail['product_batching'] = instance
                batching_detail_list[i] = ProductBatchingDetail(**detail)
            ProductBatchingDetail.objects.bulk_create(batching_detail_list)
        if weight_cnt_types:
            # 新建小料包
            for weight_cnt_type in weight_cnt_types:
                weight_details = weight_cnt_type.pop('weight_details', None)
                weight_cnt_type['product_batching'] = instance
                cnt_type_instance = WeighCntType.objects.create(**weight_cnt_type)
                if weight_details:
                    # 新建小料包详情
                    weight_cnt_types_detail_list = [None] * len(weight_details)
                    for j, weight_detail in enumerate(weight_details):
                        weight_detail["weigh_cnt_type"] = cnt_type_instance
                        weight_cnt_types_detail_list[j] = WeighBatchingDetail(**weight_detail)
                    WeighBatchingDetail.objects.bulk_create(weight_cnt_types_detail_list)
        try:
            material_type = GlobalCode.objects.filter(global_type__type_name='原材料类别',
                                                      global_name=instance.stage.global_name).first()
            Material.objects.get_or_create(
                material_no=instance.stage_product_batch_no,
                material_name=instance.stage_product_batch_no,
                material_type=material_type,
                created_user=self.context['request'].user
            )
        except Exception as e:
            logger.error(e)
        instance.save()
        return instance

    class Meta:
        model = ProductBatching
        fields = ('factory', 'site', 'product_info', 'precept', 'stage_product_batch_no', 'weight_cnt_types',
                  'stage', 'versions', 'batching_details', 'equip', 'id', 'dev_type', 'production_time_interval')
        extra_kwargs = {
            'stage_product_batch_no': {
                'allow_blank': True,
                'allow_null': True,
                'required': False}
        }


class WeighCntTypeDetailRetrieveSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.material_name', read_only=True)
    material_no = serializers.CharField(source='material.material_no', read_only=True)

    class Meta:
        model = WeighBatchingDetail
        exclude = ('weigh_cnt_type', )
        extra_kwargs = {'id': {'read_only': False, 'allow_null': True, 'required': False}}


class WeighCntTypeRetrieveSerializer(serializers.ModelSerializer):
    weight_details = WeighCntTypeDetailRetrieveSerializer(many=True)

    class Meta:
        model = WeighCntType
        exclude = ('product_batching', )
        extra_kwargs = {'id': {'read_only': False, 'allow_null': True, 'required': False}}


class ProductBatchingRetrieveSerializer(ProductBatchingListSerializer):
    batching_details = ProductBatchingDetailRetrieveSerializer(many=True, required=False,
                                                               help_text=""" 带id则表示更新某条数据删除
                                                               将delete_flag改为true即可，否则代表新加一条数据
                                                               [
                                                               {"id": 1,
                                                               "sn": 序号, 
                                                               "material":原材料id, 
                                                               "actual_weight":重量, 
                                                               "error_range":误差值,
                                                               "delete_flag": false
                                                               },
                                                               {
                                                               "sn": 序号, 
                                                               "material":原材料id, 
                                                               "actual_weight":重量, 
                                                               "error_range":误差值,
                                                               },
                                                               ]""")
    weight_cnt_types = WeighCntTypeRetrieveSerializer(many=True, required=False, help_text="""
    [
        {   
            "id": id
            "name": "名称",
            "package_cnt": "分包数量",
            "package_type": "打包类型 1自动 2手动",
            "delete_flag": false,
            "weight_details": [
                {
                    "id": id,
                    "delete_flag": true
                    "material": "原材料id",
                    "standard_weight": "重量",
                    "standard_error": "误差",
                }
            ]
        },
    ]
    """)

    class Meta:
        model = ProductBatching
        fields = '__all__'


class ProductBatchingUpdateSerializer(ProductBatchingRetrieveSerializer):
    batching_detail_ids = serializers.ListField(required=False, allow_empty=True, allow_null=True)
    cnt_type_ids = serializers.ListField(required=False, allow_empty=True, allow_null=True)
    weight_detail_ids = serializers.ListField(required=False, allow_empty=True, allow_null=True)

    @atomic()
    def update(self, instance, validated_data):
        if instance.used_type not in (1, 4):  # 新建、启用状态的配方才可修改
            raise serializers.ValidationError('操作无效！')
        batching_details = validated_data.pop('batching_details', None)
        weight_cnt_types = validated_data.pop('weight_cnt_types', None)
        batching_detail_ids = validated_data.pop('batching_detail_ids', [])
        cnt_type_ids = validated_data.pop('cnt_type_ids', [])
        weight_detail_ids = validated_data.pop('weight_detail_ids', [])
        ProductBatchingDetail.objects.filter(id__in=batching_detail_ids).update(delete_flag=True)
        WeighCntType.objects.filter(id__in=cnt_type_ids).update(delete_flag=True)
        WeighBatchingDetail.objects.filter(id__in=weight_detail_ids).update(delete_flag=True)
        instance = super().update(instance, validated_data)
        if batching_details is not None:
            for detail in batching_details:
                batching_detail_id = detail.pop('id', None)
                material = detail.get('material')
                if material.material_type.global_name == '炭黑':
                    detail['type'] = 2
                elif material.material_type.global_name == '油料':
                    detail['type'] = 3
                if batching_detail_id:
                    # 更新
                    batching_detail_instance = ProductBatchingDetail.objects.filter(id=batching_detail_id).first()
                    if not batching_detail_instance:
                        raise serializers.ValidationError('object does not exit!')
                    ProductBatchingDetail.objects.filter(id=batching_detail_id).update(**detail)
                else:
                    # 更新
                    detail['product_batching'] = instance
                    ProductBatchingDetail.objects.create(**detail)
        if weight_cnt_types is not None:
            for weight_cnt_type in weight_cnt_types:
                weight_details = weight_cnt_type.pop('weight_details', None)
                weight_cnt_type_id = weight_cnt_type.pop('id', None)
                if weight_cnt_type_id:
                    # 有id则更新
                    cnt_type_instance = WeighCntType.objects.filter(id=weight_cnt_type_id).first()
                    if not cnt_type_instance:
                        raise serializers.ValidationError('object does not exit!')
                    WeighCntType.objects.filter(id=weight_cnt_type_id).update(**weight_cnt_type)
                else:
                    # 否则新建
                    weight_cnt_type['product_batching'] = instance
                    cnt_type_instance = WeighCntType.objects.create(**weight_cnt_type)
                if weight_details:
                    # 更新小料包详情
                    for weight_detail in weight_details:
                        weight_detail_id = weight_detail.pop('id', None)
                        if weight_detail_id:
                            # 有id则更新
                            detail = WeighBatchingDetail.objects.filter(id=weight_detail_id).first()
                            if not detail:
                                raise serializers.ValidationError('object does not exit!')
                            WeighBatchingDetail.objects.filter(id=weight_detail_id).update(**weight_detail)
                        else:
                            # 否则新建
                            weight_detail["weigh_cnt_type"] = cnt_type_instance
                            WeighBatchingDetail.objects.create(**weight_detail)
        instance.used_type = 1
        instance.save()
        return instance

    class Meta:
        model = ProductBatching
        fields = ('id', 'batching_details', 'dev_type', 'production_time_interval', 'weight_cnt_types',
                  'batching_detail_ids', 'cnt_type_ids', 'weight_detail_ids')


class ProductBatchingPartialUpdateSerializer(BaseModelSerializer):
    pass_flag = serializers.BooleanField(help_text='通过标志，1：通过, 0:驳回', write_only=True)

    def update(self, instance, validated_data):
        pass_flag = validated_data['pass_flag']
        if pass_flag:
            if instance.used_type == 1:  # 提交
                instance.submit_user = self.context['request'].user
                instance.submit_time = datetime.now()
                instance.used_type = 2
            elif instance.used_type == 2:  # 审核通过
                instance.used_type = 3
                instance.check_user = self.context['request'].user
                instance.check_time = datetime.now()
            elif instance.used_type == 3:  # 启用
                # 废弃旧版本
                ProductBatching.objects.filter(used_type=4,
                                               site=instance.site,
                                               product_info=instance.product_info,
                                               factory=instance.factory,
                                               stage=instance.stage
                                               ).update(used_type=6, used_time=datetime.now())
                instance.used_type = 4
                instance.used_user = self.context['request'].user
                instance.used_time = datetime.now()
            elif instance.used_type == 5:
                instance.used_type = 1
        else:
            if instance.used_type in (4, 5):  # 弃用
                if instance.used_type == 4:
                    if instance.dev_type:
                        # 如果该配方关联的计划不是全部完成（只要有计划是等待、已下达、运行中）都不能废弃的
                        if ProductClassesPlan.objects.exclude(status='完成').filter(product_batching=instance,
                                                                                  delete_flag=False).exists():
                            raise serializers.ValidationError('该配方有关联尚未完成的计划，无法废弃！')
                        try:
                            ProductObsoleteInterface(instance=instance).request()
                        except Exception as e:
                            sync_logger.error(e)
                instance.obsolete_user = self.context['request'].user
                instance.used_type = 6
                instance.obsolete_time = datetime.now()
            else:  # 驳回
                instance.used_type = 5
                instance.reject_user = self.context['request'].user
                instance.reject_time = datetime.now()
        instance.last_updated_user = self.context['request'].user
        instance.save()
        return instance

    class Meta:
        model = ProductBatching
        fields = ('id', 'pass_flag')


class WeighBatchingDetailSerializer(serializers.ModelSerializer):
    material_name = serializers.ReadOnlyField(source='material.material_name')
    material_no = serializers.ReadOnlyField(source='material.material_no')

    class Meta:
        model = WeighBatchingDetail
        fields = ('id', 'material', 'material_name', 'material_no', 'standard_weight')


# class WeighBatchingSerializer(BaseModelSerializer):
#     stage_product_batch_no = serializers.ReadOnlyField(source='product_batching.stage_product_batch_no', default='')
#     category_name = serializers.ReadOnlyField(source='product_batching.dev_type.category_name', default='')
#     production_time_interval = serializers.ReadOnlyField(source='product_batching.production_time_interval')
#     created_username = serializers.ReadOnlyField(source='created_user.username', default='')
#
#     class Meta:
#         model = WeighBatching
#         fields = ('id', 'weight_batch_no', 'stage_product_batch_no', 'category_name', 'production_time_interval',
#                   'used_type', 'created_username', 'created_date')


# class WeighBatchingChangeUsedTypeSerializer(serializers.ModelSerializer):
#     used_type = serializers.IntegerField(required=False, allow_null=True)
#
#     class Meta:
#         model = WeighBatching
#         fields = ('used_type',)
#
#     def update(self, instance, validated_data):
#         target_used_type = validated_data.get('used_type')
#         if instance.used_type == 1:  # 编辑 => 提交
#             instance.submit_user = self.context['request'].user
#             instance.submit_time = timezone.now()
#             instance.used_type = 2
#         elif instance.used_type == 2:  # 提交 => 校对 or 提交 => 驳回
#             if target_used_type == 3 or target_used_type == 5:
#                 instance.used_type = target_used_type
#         elif instance.used_type == 3:  # 校对 => 启用 or 校对 => 驳回
#             if target_used_type == 4 or target_used_type == 5:
#                 instance.used_type = target_used_type
#         elif instance.used_type == 4:  # 启用 => 废弃
#             if BatchingClassesPlan.objects.filter(
#                     ~Q(status=1), weigh_cnt_type__weigh_batching=instance).exists():
#                 raise serializers.ValidationError('该配方已关联下发计划，不可废弃')
#             instance.used_type = 6
#             instance.obsolete_user = self.context['request'].user
#             instance.obsolete_time = timezone.now()
#         elif instance.used_type == 5:  # 驳回 => 编辑 or 驳回 => 废弃
#             instance.used_type = target_used_type
#         elif instance.used_type == 6:  # 废弃 => 编辑 临时补全逻辑
#             instance.used_type = target_used_type
#
#         if target_used_type == 5:  # 驳回
#             instance.reject_user = self.context['request'].user
#             instance.reject_time = timezone.now()
#         elif target_used_type == 4:  # 启用
#             instance.used_user = self.context['request'].user
#             instance.used_time = timezone.now()
#         elif target_used_type == 6:
#             instance.obsolete_user = self.context['request'].user
#             instance.obsolete_time = timezone.now()
#         instance.save()
#         return instance


class WeighBatchingDetailCreateSerializer(BaseModelSerializer):

    class Meta:
        model = WeighBatchingDetail
        fields = ('material', 'standard_weight')


# class WeighBatchingCreateSerializer(BaseModelSerializer):
#     weight_types = WeighCntTypeCreateSerializer(many=True, help_text="""[{"weigh_type": 料包类型(1硫磺包；2细料包),
#                                                 "package_cnt":打包数量, "package_type": 打包类型(1自动；2手动),
#                                                 "weight_details": [{"material": 原材料id, "standard_weight": 重量}]}]""")
#
#     @atomic()
#     def create(self, validated_data):
#         weight_types = validated_data.pop('weight_types', [])
#         product_batching = validated_data['product_batching']
#         validated_data['weight_batch_no'] = product_batching.stage_product_batch_no\
#                                             + '-' + product_batching.dev_type.category_name
#         instance = super(WeighBatchingCreateSerializer, self).create(validated_data)
#         for weight_type in weight_types:
#             max_tag = WeighCntType.objects.filter(
#                 weigh_type=weight_type['weigh_type'],
#                 weigh_batching=instance).aggregate(max_tag=Max('tag'))['max_tag']
#             if max_tag:
#                 weight_type['tag'] = max_tag + 1
#             weight_details = weight_type.pop('weight_details', [])
#             weight_type['weigh_batching'] = instance
#             weight_cne_type = WeighCntType.objects.create(**weight_type)
#             for weight_detail in weight_details:
#                 weight_detail['weigh_cnt_type'] = weight_cne_type
#                 WeighBatchingDetail.objects.create(**weight_detail)
#         return instance
#
#     class Meta:
#         model = WeighBatching
#         fields = ('product_batching', 'weight_types')


class WeighBatchingDetailListSerializer(BaseModelSerializer):
    material_no = serializers.ReadOnlyField(source='material.material_no')
    material_name = serializers.ReadOnlyField(source='material.material_name')

    class Meta:
        model = WeighBatchingDetail
        fields = ('material_no', 'material_name', 'standard_weight', 'material')


class WeighCntTypeListSerializer(BaseModelSerializer):
    weight_details = WeighBatchingDetailListSerializer(many=True)

    class Meta:
        model = WeighCntType
        fields = ('weigh_type', 'package_cnt', 'package_type', 'weight_details', 'tag')


# class WeighBatchingRetrieveSerializer(BaseModelSerializer):
#     stage_product_batch_no = serializers.ReadOnlyField(source='product_batching.stage_product_batch_no', default='')
#     category_name = serializers.ReadOnlyField(source='product_batching.dev_type.category_name', default='')
#     production_time_interval = serializers.ReadOnlyField(source='product_batching.production_time_interval')
#     weight_types = WeighCntTypeListSerializer(many=True)
#     batching_weight = serializers.ReadOnlyField(source='product_batching.batching_weight', default='')
#     product_name = serializers.ReadOnlyField(source='product_batching.product_info.product_name', default='')
#
#     class Meta:
#         model = WeighBatching
#         fields = ('id', 'weight_batch_no', 'stage_product_batch_no', 'category_name', 'batching_weight',
#                   'production_time_interval', 'used_type', 'weight_types', 'product_batching', 'product_name')


# class WeighBatchingUpdateSerializer(BaseModelSerializer):
#     weight_types = WeighCntTypeCreateSerializer(many=True, required=True,
#                                                 help_text="""[{"weigh_type": 料包类型(1硫磺包；2细料包), "package_cnt":打包数量,
#                                                     "package_type": 打包类型(1自动；2手动), "weight_details":
#                                                     [{"material": 原材料id, "standard_weight": 重量}]}]""")
#
#     @atomic()
#     def update(self, instance, validated_data):
#         instance.weight_types.all().delete()
#         weight_types = validated_data.pop('weight_types', [])
#         for weight_type in weight_types:
#             weight_details = weight_type.pop('weight_details', [])
#             max_tag = WeighCntType.objects.filter(
#                 weigh_type=weight_type['weigh_type'],
#                 weigh_batching=instance).aggregate(max_tag=Max('tag'))['max_tag']
#             if max_tag:
#                 weight_type['tag'] = max_tag + 1
#             weight_type['weigh_batching'] = instance
#             weight_cne_type = WeighCntType.objects.create(**weight_type)
#             for weight_detail in weight_details:
#                 weight_detail['weigh_cnt_type'] = weight_cne_type
#                 WeighBatchingDetail.objects.create(**weight_detail)
#         return instance
#
#     class Meta:
#         model = WeighBatching
#         fields = ('id', 'weight_types')


class ProductBatchingDetailMaterialSerializer(serializers.ModelSerializer):
    material_name = serializers.ReadOnlyField(source='material.material_name')
    material_no = serializers.ReadOnlyField(source='material.material_no')

    class Meta:
        model = ProductBatchingDetail
        fields = ('id', 'material', 'material_name', 'material_no', 'actual_weight')


class WeighCntTypeSerializer(serializers.ModelSerializer):
    weight_details = WeighBatchingDetailSerializer(many=True)

    class Meta:
        model = WeighCntType
        fields = ('id', 'weigh_type', 'package_cnt', 'weight_details', 'package_type')
        read_only_fields = ('weigh_type',)