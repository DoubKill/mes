from datetime import datetime
import logging

from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from basics.models import GlobalCode
from mes.base_serializer import BaseModelSerializer
from mes.sync import ProductObsoleteInterface
from recipe.models import Material, ProductInfo, ProductBatching, ProductBatchingDetail, \
    MaterialAttribute
from mes.conf import COMMON_READ_ONLY_FIELDS

logger = logging.getLogger('api_log')
sync_logger = logging.getLogger('sync_log')


class MaterialSerializer(BaseModelSerializer):
    material_no = serializers.CharField(max_length=64, help_text='编码',
                                        validators=[UniqueValidator(queryset=Material.objects.filter(delete_flag=0),
                                                                    message='该原材料已存在')])
    material_type = serializers.PrimaryKeyRelatedField(queryset=GlobalCode.objects.filter(used_flag=0,
                                                                                          delete_flag=False),
                                                       help_text='原材料类型id',
                                                       error_messages={'does_not_exist': '该原材料类型已被弃用或删除，操作无效'})
    package_unit = serializers.PrimaryKeyRelatedField(queryset=GlobalCode.objects.filter(used_flag=0,
                                                                                         delete_flag=False),
                                                      help_text='包装单位id', required=False,
                                                      allow_null=True, allow_empty=True,
                                                      error_messages={'does_not_exist': '该包装单位类型已被弃用或删除，操作无效'})
    material_type_name = serializers.CharField(source='material_type.global_name', read_only=True)
    package_unit_name = serializers.CharField(source='package_unit.global_name', read_only=True)
    created_user_name = serializers.CharField(source='created_user.username', read_only=True)
    update_user_name = serializers.CharField(source='last_updated_user.username', default=None, read_only=True)

    def update(self, instance, validated_data):
        validated_data['last_updated_user'] = self.context['request'].user
        return super().update(instance, validated_data)

    class Meta:
        model = Material
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialAttributeSerializer(BaseModelSerializer):
    material_no = serializers.CharField(source='Material.material_no', read_only=True)
    material_name = serializers.CharField(source='Material.material_name', read_only=True)

    class Meta:
        model = MaterialAttribute
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ProductInfoSerializer(BaseModelSerializer):
    update_username = serializers.CharField(source='last_updated_user.username', read_only=True)

    class Meta:
        model = ProductInfo
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ProductInfoCopySerializer(BaseModelSerializer):
    factory = serializers.PrimaryKeyRelatedField(queryset=GlobalCode.objects.filter(used_flag=0, delete_flag=False),
                                                 help_text='产地id')

    def validate(self, attrs):
        versions = attrs['versions']
        factory = attrs['factory']
        product_no = attrs['product_info_id'].product_no
        product_info = ProductInfo.objects.filter(factory=factory, product_no=product_no).order_by('-versions').first()
        if product_info:
            if product_info.versions >= versions:  # TODO 目前版本检测根据字符串做比较，后期搞清楚具体怎样填写版本号
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
    material = serializers.PrimaryKeyRelatedField(queryset=Material.objects.filter(delete_flag=False, used_flag=1))
    material_type = serializers.CharField(source='material.material_type.global_name', read_only=True)
    material_name = serializers.CharField(source='material.material_name', read_only=True)

    class Meta:
        model = ProductBatchingDetail
        exclude = ('product_batching', )


class ProductBatchingListSerializer(BaseModelSerializer):
    product_no = serializers.CharField(source='product_info.product_no')
    product_name = serializers.CharField(source='product_info.product_name')
    created_user_name = serializers.CharField(source='created_user.username', read_only=True)
    update_user_name = serializers.CharField(source='last_updated_user.username', read_only=True)
    stage_name = serializers.CharField(source="stage.global_name")
    site_name = serializers.CharField(source="site.global_name")
    dev_type_name = serializers.CharField(source='dev_type.category_name', default=None, read_only=True)

    class Meta:
        model = ProductBatching
        fields = '__all__'


class ProductBatchingCreateSerializer(BaseModelSerializer):
    stage = serializers.PrimaryKeyRelatedField(queryset=GlobalCode.objects.filter(used_flag=0, delete_flag=False),
                                               help_text='段次id')
    batching_details = ProductBatchingDetailSerializer(many=True, required=False,
                                                       help_text="""
                                                           [{"sn": 序号, "material":原材料id, "auto_flag": true,
                                                           "actual_weight":重量, "standard_error":误差值}]""")

    def validate(self, attrs):
        product_batching = ProductBatching.objects.filter(factory=attrs['factory'],
                                                          site=attrs['site'],
                                                          stage=attrs['stage'],
                                                          product_info=attrs['product_info']
                                                          ).order_by('-versions').first()
        if product_batching:
            if product_batching.versions >= attrs['versions']:  # TODO 目前版本检测根据字符串做比较，后期搞清楚具体怎样填写版本号
                raise serializers.ValidationError('该配方版本号不得小于现有版本号')
        return attrs

    @atomic()
    def create(self, validated_data):
        batching_details = validated_data.pop('batching_details', None)
        instance = super().create(validated_data)
        batching_weight = manual_material_weight = auto_material_weight = 0
        if batching_details:
            batching_detail_list = [None] * len(batching_details)
            for i, detail in enumerate(batching_details):
                auto_flag = detail.get('detail')
                actual_weight = detail.get('actual_weight', 0)
                if auto_flag == 1:
                    auto_material_weight += actual_weight
                elif auto_flag == 2:
                    manual_material_weight += actual_weight
                batching_weight += actual_weight
                detail['product_batching'] = instance
                batching_detail_list[i] = ProductBatchingDetail(**detail)
            ProductBatchingDetail.objects.bulk_create(batching_detail_list)
        instance.batching_weight = batching_weight
        instance.manual_material_weight = manual_material_weight
        instance.auto_material_weight = auto_material_weight
        instance.save()
        try:
            material_type = GlobalCode.objects.filter(global_type__type_name='原材料类别',
                                                      global_name=instance.stage.global_name).first()
            Material.objects.get_or_create(
                material_no=instance.stage_product_batch_no,
                material_name=instance.stage_product_batch_no,
                material_type=material_type
            )
        except Exception as e:
            logger.error(e)
        return instance

    class Meta:
        model = ProductBatching
        fields = ('factory', 'site', 'product_info', 'precept', 'stage_product_batch_no',
                  'stage', 'versions', 'batching_details', 'equip', 'id', 'dev_type')


class ProductBatchingRetrieveSerializer(ProductBatchingListSerializer):
    batching_details = ProductBatchingDetailSerializer(many=True, required=False,
                                                       help_text="""
                                                       [{"sn": 序号, "material":原材料id, 
                                                       "actual_weight":重量, "error_range":误差值}]""")

    class Meta:
        model = ProductBatching
        fields = '__all__'


class ProductBatchingUpdateSerializer(ProductBatchingRetrieveSerializer):

    @atomic()
    def update(self, instance, validated_data):
        if instance.used_type != 1:
            raise serializers.ValidationError('只有编辑状态的配方才可修改')
        batching_details = validated_data.pop('batching_details', None)
        instance = super().update(instance, validated_data)
        batching_weight = manual_material_weight = auto_material_weight = 0
        if batching_details is not None:
            instance.batching_details.all().delete()
            batching_detail_list = [None] * len(batching_details)
            for i, detail in enumerate(batching_details):
                actual_weight = detail.get('actual_weight', 0)
                auto_flag = detail.get('detail')
                if auto_flag == 1:
                    auto_material_weight += actual_weight
                elif auto_flag == 2:
                    manual_material_weight += actual_weight
                batching_weight += actual_weight
                detail['product_batching'] = instance
                batching_detail_list[i] = ProductBatchingDetail(**detail)
            ProductBatchingDetail.objects.bulk_create(batching_detail_list)
            instance.batching_weight = batching_weight
            instance.manual_material_weight = manual_material_weight
            instance.auto_material_weight = auto_material_weight
            instance.save()
        return instance

    class Meta:
        model = ProductBatching
        fields = ('id', 'batching_details', 'dev_type', 'production_time_interval')


class ProductBatchingPartialUpdateSerializer(BaseModelSerializer):
    pass_flag = serializers.BooleanField(help_text='通过标志，1：通过, 0:驳回', write_only=True)

    def update(self, instance, validated_data):
        pass_flag = validated_data['pass_flag']
        if pass_flag:
            if instance.used_type == 1:  # 审核通过
                instance.used_type = 2
            elif instance.used_type == 2:  # 审核通过
                instance.used_type = 3
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
        else:
            if instance.used_type == 4:  # 弃用
                instance.obsolete_user = self.context['request'].user
                instance.used_type = 6
                instance.obsolete_time = datetime.now()
                try:
                    ProductObsoleteInterface(instance=instance).request()
                except Exception as e:
                    sync_logger.error(e)
            else:  # 驳回
                instance.used_type = 5
        instance.last_updated_user = self.context['request'].user
        instance.save()
        return instance

    class Meta:
        model = ProductBatching
        fields = ('id', 'pass_flag')