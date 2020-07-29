from datetime import datetime

from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from basics.models import GlobalCode
from mes.base_serializer import BaseModelSerializer
from recipe.models import Material, ProductInfo, ProductRecipe, ProductBatching, ProductBatchingDetail, ProductMaster
from mes.conf import COMMON_READ_ONLY_FIELDS
from recipe.models import Material


class MaterialSerializer(serializers.ModelSerializer):
    material_type_name = serializers.CharField(source='material_type.global_name', read_only=True)
    packet_unit_name = serializers.CharField(source='packet_unit.global_name', read_only=True)
    created_user_name = serializers.CharField(source='created_user.username', read_only=True)
    update_user_name = serializers.SerializerMethodField(read_only=True)

    def get_update_user_name(self, obj):
        return obj.last_updated_user.username if obj.last_updated_user else None

    def create(self, validated_data):
        validated_data['created_user'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data['last_updated_user'] = self.context['request'].user
        return super().update(instance, validated_data)

    class Meta:
        model = Material
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ProductRecipeSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.material_name', read_only=True)
    stage_name = serializers.CharField(source='stage.global_name', read_only=True)
    material_material_type = serializers.CharField(source='material.material_type.global_name', read_only=True)

    class Meta:
        model = ProductRecipe
        exclude = ('product_info', 'product_recipe_no')


class ProductInfoCreateSerializer(serializers.ModelSerializer):
    productrecipe_set = ProductRecipeSerializer(many=True, help_text="""[{"num": 编号, "material": 原材料id, 
    "stage": 段次id, "ratio": 配比}...]""")

    def validate(self, attrs):
        recipes = attrs.get('productrecipe_set')
        recipe_weight = sum(i.get('ratio', 0) for i in recipes)
        used_type = GlobalCode.objects.filter(global_type__type_name='胶料状态',
                                              global_name='编辑',
                                              used_flag=0).first()
        if not used_type:
            raise serializers.ValidationError('请先配置公共代码中的胶料状态【编辑】数据')
        attrs['used_type'] = used_type
        attrs['recipe_weight'] = recipe_weight
        return attrs

    @atomic()
    def create(self, validated_data):
        recipes = validated_data.pop('productrecipe_set', None)
        validated_data['created_user'] = self.context['request'].user
        instance = super().create(validated_data)
        recipes_list = []
        product_recipe_no = instance.product_no  # TODO 搞清楚product_info表存的是编号还是编码
        for recipe in recipes:
            recipe['product_info'] = instance
            recipe['product_recipe_no'] = product_recipe_no
            recipes_list.append(ProductRecipe(**recipe))
        ProductRecipe.objects.bulk_create(recipes_list)
        return instance

    class Meta:
        model = ProductInfo
        fields = ('product_no', 'product_name', 'versions', 'precept',
                  'factory', 'productrecipe_set')


class ProductInfoSerializer(serializers.ModelSerializer):
    factory = serializers.CharField(source='factory.global_name')
    update_user = serializers.SerializerMethodField(read_only=True)
    used_user = serializers.SerializerMethodField(read_only=True)
    used_type_name = serializers.CharField(source='used_type.global_name')

    def get_update_user(self, obj):
        return obj.last_updated_user.username if obj.last_updated_user else None

    def get_used_user(self, obj):
        return obj.used_user.username if obj.used_user else None

    class Meta:
        model = ProductInfo
        fields = ('id', 'product_no', 'product_name', 'factory', 'used_type', "used_user",
                  'recipe_weight', 'used_time', 'obsolete_time', 'update_user', 'used_type_name')


class ProductInfoPartialUpdateSerializer(serializers.ModelSerializer):

    def validate(self, attrs):
        if self.instance.used_type.global_name == '编辑':  # 应用
            used_type = GlobalCode.objects.filter(global_type=self.instance.used_type.global_type,
                                                  global_name='应用',
                                                  used_flag=0).first()
            if not used_type:
                raise serializers.ValidationError('请先配置公共代码中的胶料状态【应用】数据')
        elif self.instance.used_type.global_name == '应用':  # 废弃
            used_type = GlobalCode.objects.filter(global_type=self.instance.used_type.global_type,
                                                  global_name='废弃',
                                                  used_flag=0).first()
            if not used_type:
                raise serializers.ValidationError('请先配置公共代码中的胶料状态【废弃】数据')
        else:
            raise serializers.ValidationError('无法操作')
        attrs['used_type'] = used_type
        return attrs

    def update(self, instance, validated_data):
        used_type = validated_data['used_type']
        if instance.used_type.global_name == '编辑':  # 应用
            instance.used_type = used_type
            instance.used_user = self.context['request'].user
            instance.used_time = datetime.now()
            # 废弃旧版本
            ProductInfo.objects.exclude(id=instance.id
                                        ).filter(used_type=2).update(used_type=3, obsolete_time=datetime.now())
        else:  # 废弃
            instance.used_type = used_type
            instance.obsolete_time = datetime.now()
        instance.last_updated_user = self.context['request'].user
        instance.save()
        return instance

    class Meta:
        model = ProductInfo
        fields = ('id', )


class ProductInfoUpdateSerializer(serializers.ModelSerializer):
    productrecipe_set = ProductRecipeSerializer(many=True)

    @atomic()
    def update(self, instance, validated_data):
        if not instance.used_type.global_name == '编辑':
            raise PermissionDenied('当前胶料状态不是编辑，无法操作')
        recipes = validated_data.pop('productrecipe_set', None)
        recipe_weight = sum(i.get('ratio', 0) for i in recipes)
        if recipes:
            ProductRecipe.objects.filter(product_info=instance, delete_flag=False).update(delete_flag=True)
            recipes_list = []
            product_recipe_no = instance.product_no  # TODO 搞清楚product_info表存的是编号还是编码
            for recipe in recipes:
                recipe['product_recipe_no'] = product_recipe_no
                recipe['product_info'] = instance
                recipes_list.append(ProductRecipe(**recipe))
            ProductRecipe.objects.bulk_create(recipes_list)
        instance.recipe_weight = recipe_weight
        instance.save()
        return instance

    class Meta:
        model = ProductInfo
        fields = ('id', 'product_no', 'product_name', 'used_type', 'recipe_weight', 'productrecipe_set')


class ProductInfoCopySerializer(serializers.ModelSerializer):
    product_info_id = serializers.PrimaryKeyRelatedField(queryset=ProductInfo.objects.exclude(
        used_type__global_type__type_name='胶料状态', used_type__global_name='编辑', used_type__used_flag=0), write_only=True, help_text='复制配方工艺id')

    def validate(self, attrs):
        used_type = GlobalCode.objects.filter(global_type__type_name='胶料状态',
                                              global_name='编辑',
                                              used_flag=0).first()
        if not used_type:
            raise serializers.ValidationError('请先配置公共代码中的胶料状态【编辑】数据')
        attrs['used_type'] = used_type
        return attrs

    @atomic()
    def create(self, validated_data):
        base_product_info = validated_data.pop('product_info_id')
        validated_data['created_user'] = self.context['request'].user
        validated_data['recipe_weight'] = base_product_info.recipe_weight
        validated_data['product_no'] = base_product_info.product_no
        validated_data['product_name'] = base_product_info.product_name
        validated_data['precept'] = base_product_info.precept
        validated_data['created_user'] = base_product_info.precept
        instance = super().create(validated_data)
        recipes = base_product_info.productrecipe_set.filter(delete_flag=False).values(
            'product_recipe_no', 'num', 'material_id', 'stage_id', 'ratio')
        recipes_list = []
        for recipe in recipes:
            recipe['product_info'] = instance
            recipes_list.append(ProductRecipe(**recipe))
        ProductRecipe.objects.bulk_create(recipes_list)
        return instance

    class Meta:
        model = ProductInfo
        fields = ('product_info_id', 'factory', 'versions')


class ProductRecipeListSerializer(serializers.ModelSerializer):
    material_type = serializers.CharField(source='material.material_type.global_name')
    material_name = serializers.CharField(source='material.material_name')
    density = serializers.CharField(source='material.density')

    class Meta:
        model = ProductRecipe
        fields = ('material_type', 'material', 'ratio', 'density', 'material_name')


class ProductBatchingDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductBatchingDetail
        exclude = ('product_batching', 'density', 'ratio')


class ProductBatchingListSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product_info.product_name')
    dev_type_name = serializers.CharField(source='dev_type.global_name')
    used_type_name = serializers.CharField(source='product_info.used_type.global_name')
    created_user_name = serializers.CharField(source='created_user.username', read_only=True)
    update_user_name = serializers.SerializerMethodField(read_only=True)

    def get_update_user_name(self, obj):
        return obj.last_updated_user.username if obj.last_updated_user else None

    class Meta:
        model = ProductBatching
        fields = ('stage_product_batch_no', 'product_name', 'dev_type_name', 'used_type_name',
                  'batching_weight', 'production_time_interval', 'rm_flag', 'rm_time_interval',
                  'created_user_name', 'created_date', 'update_user_name', 'last_updated_date')


class ProductBatchingCreateSerializer(serializers.ModelSerializer):
    batching_details = ProductBatchingDetailSerializer(many=True, help_text=
                                                       """
                                                       配料详情：{
                                                                'num': '序号',
                                                                'material': '原材料',
                                                                'ratio_weight': '配比体积',
                                                                'standard_volume': '序号',
                                                                'actual_volume': '计算体积',
                                                                'standard_weight': '实际体积',
                                                                'actual_weight': '标准重量',
                                                                'time_interval': '实际重量',
                                                                'temperature': '温度',
                                                                'rpm': '转速',
                                                            }""")

    def validate(self, attrs):
        batching_details = attrs.get('batching_details', None)
        batching_weight = manual_material_weight = volume = 0
        for detail in batching_details:
            batching_weight += detail.get('actual_weight', 0)
            volume += detail.get('actual_volume', 0)
            if detail.get('material'):
                if detail.get('material').material_type.global_type.type_name == '手动小料':
                    manual_material_weight += detail.get('actual_weight', 0)
        attrs['manual_material_weight'] = manual_material_weight
        attrs['batching_weight'] = batching_weight
        attrs['volume'] = volume
        attrs['batching_proportion'] = float(batching_weight / volume) if volume else 0
        attrs['created_user'] = self.context['request'].user
        return attrs

    @atomic()
    def create(self, validated_data):
        batching_details = validated_data.pop('batching_details', None)
        instance = super().create(validated_data)
        batching_detail_list = []
        for detail in batching_details:
            detail['product_batching'] = instance
            detail['ratio'] = ProductRecipe
            if detail.get('material'):
                recipe = ProductRecipe.objects.filter(product_info=validated_data['product_info'],
                                                      stage=validated_data['stage'],
                                                      material=detail['material']
                                                      ).first()
                if recipe:
                    detail['ratio'] = recipe.ratio
                detail['density'] = detail.get('material').density
            else:
                detail['density'] = 0
            batching_detail_list.append(ProductBatchingDetail(**detail))
        ProductBatchingDetail.objects.bulk_create(batching_detail_list)
        return instance

    class Meta:
        model = ProductBatching
        fields = ('product_info', 'stage_product_batch_no', 'stage', 'dev_type',
                  'batching_time_interval', 'rm_time_interval', 'production_time_interval', 'batching_details'
                  )


class ProductMasterSerializer(BaseModelSerializer):

    factory = serializers.SerializerMethodField(read_only=True)
    versions = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProductBatching
        fields = "__all__"

    def get_factory(self, object):
        return object.product_info.factory.global_name

    def get_versions(self, object):
        return object.product_info.versions