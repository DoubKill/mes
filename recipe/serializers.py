import json
import logging
import uuid
from datetime import datetime

from django.db.models import Q
from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from basics.models import GlobalCode
from mes.base_serializer import BaseModelSerializer
from mes.conf import COMMON_READ_ONLY_FIELDS
from recipe.models import Material, ProductInfo, ProductBatching, ProductBatchingDetail, \
    MaterialAttribute, MaterialSupplier, WeighBatchingDetail, WeighCntType, ZCMaterial, ERPMESMaterialRelation, \
    ProductBatchingEquip, ProductBatchingMixed, MultiReplaceMaterial, RecipeChangeHistory, RecipeChangeDetail
from recipe.utils import get_mixed

sync_logger = logging.getLogger('sync_log')
error_logger = logging.getLogger('error_log')


class MaterialSerializer(BaseModelSerializer):
    material_no = serializers.CharField(max_length=64, help_text='编码',
                                        validators=[UniqueValidator(queryset=Material.objects.filter(delete_flag=0),
                                                                    message='该原材料已存在')])
    material_name = serializers.CharField(max_length=64, help_text='名称',
                                        validators=[UniqueValidator(queryset=Material.objects.filter(delete_flag=0),
                                                                    message='该原材料名称已存在')])
    material_type_name = serializers.CharField(source='material_type.global_name', read_only=True)
    package_unit_name = serializers.CharField(source='package_unit.global_name', read_only=True)
    created_user_name = serializers.CharField(source='created_user.username', read_only=True)
    update_user_name = serializers.CharField(source='last_updated_user.username', default=None, read_only=True)
    safety_inventory = serializers.IntegerField(source='material_attr.safety_inventory', read_only=True, default=None)
    period_of_validity = serializers.IntegerField(source='material_attr.period_of_validity', read_only=True,
                                                  default=None)
    validity_unit = serializers.CharField(source='material_attr.validity_unit', read_only=True, default=None)
    storage_time = serializers.CharField(source='material_attr.storage_time', read_only=True, default=None)
    is_binding = serializers.SerializerMethodField()
    suppliers = serializers.SerializerMethodField()

    def get_is_binding(self, obj):
        return 'Y' if obj.zc_materials.count() >= 1 else 'N'

    def get_suppliers(self, obj):
        return ','.join(obj.suppliers.values_list('provenance', flat=True))

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
        validated_data['created_user'] = self.context['request'].user
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
    master = serializers.DictField(default={})
    is_manual = serializers.BooleanField(default=False)

    def to_representation(self, instance):
        res = super().to_representation(instance)
        batching_info = ProductBatchingEquip.objects.filter(product_batching=instance.product_batching,
                                                            batching_detail_equip=instance, type=instance.type)
        update_data = {i.equip_no: i.feeding_mode for i in batching_info}
        res.update({'master': update_data, 'is_manual': batching_info.first().is_manual if batching_info.first() else False})
        return res

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

    def to_representation(self, instance):
        res = super().to_representation(instance)
        # 查看是否存在_NEW配方
        product_no = instance.stage_product_batch_no
        if '_NEW' in product_no:
            new_recipe_id = instance.id
        else:
            new_recipe = ProductBatching.objects.exclude(used_type__in=[6]).filter(
                stage_product_batch_no=f'{instance.stage_product_batch_no}_NEW', dev_type=instance.dev_type).first()
            new_recipe_id = new_recipe.id if new_recipe else 0
        res['new_recipe_id'] = new_recipe_id
        # 返回配方可用机台
        equip_info = ProductBatchingEquip.objects.filter(product_batching=instance)
        enable_equip = list(equip_info.values_list('equip_no', flat=True).distinct())
        send_success_equip = list(equip_info.filter(send_recipe_flag=True).values_list('equip_no', flat=True).distinct())
        mixed = ProductBatchingMixed.objects.filter(product_batching=instance).first()
        mixed_ratio = {} if not mixed else {'stage': {'f_feed': mixed.f_feed, 's_feed': mixed.s_feed},
                                            'ratio': {'f_ratio': mixed.f_ratio, 's_ratio': mixed.s_ratio}}
        send_xl_equip = equip_info.last().send_xl_equip if equip_info else ''
        res.update({'enable_equip': enable_equip, 'send_success_equip': send_success_equip, 'mixed_ratio': mixed_ratio,
                    'send_xl_equip': send_xl_equip})
        return res

    class Meta:
        model = ProductBatching
        fields = '__all__'


class WFProductBatchingListSerializer(BaseModelSerializer):
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

    def to_representation(self, instance):
        res = super().to_representation(instance)
        equip_info = ProductBatchingEquip.objects.filter(product_batching=instance)
        send_success_equip = list(equip_info.filter(send_recipe_flag=True).values_list('equip_no', flat=True).distinct())
        send_xl_equip = equip_info.last().send_xl_equip if equip_info else ''
        res.update({'send_success_equip': send_success_equip, 'send_xl_equip': send_xl_equip})
        return res

    class Meta:
        model = ProductBatching
        fields = '__all__'


class WeighCntTypeDetailCreateSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.material_name', read_only=True)
    material_no = serializers.CharField(source='material.material_no', read_only=True)
    master = serializers.DictField(default={})

    class Meta:
        model = WeighBatchingDetail
        exclude = ('weigh_cnt_type',)


class WeighCntTypeCreateSerializer(serializers.ModelSerializer):
    weight_details = WeighCntTypeDetailCreateSerializer(many=True, required=False)

    class Meta:
        model = WeighCntType
        exclude = ('product_batching', 'name', 'weigh_type', 'package_cnt', 'package_type')


class ProductBatchingCreateSerializer(BaseModelSerializer):
    batching_details = ProductBatchingDetailSerializer(many=True, required=False,
                                                       help_text="""[{"sn": 序号, "material":原材料id, 
                                                       "type":"1:密炼机投料口,2:炭黑粉料罐,3:油料罐","actual_weight":重量, 
                                                       "standard_error":误差值}]""")
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
    create_new = serializers.BooleanField(default=False)
    new_recipe_id = serializers.IntegerField(default=0)
    mixed_ratio = serializers.DictField(default={})

    @atomic()
    def create(self, validated_data):
        batching_details = validated_data.pop('batching_details', None)
        weight_cnt_types = validated_data.pop('weight_cnt_types', None)
        stage_product_batch_no = validated_data.get('stage_product_batch_no')
        create_new = validated_data.pop('create_new')
        new_recipe_id = validated_data.pop('new_recipe_id')
        mixed_ratio = validated_data.pop('mixed_ratio')
        if stage_product_batch_no:
            # 传胶料编码则代表是特殊配方
            validated_data.pop('site', None)
            validated_data.pop('stage', None)
            validated_data.pop('versions', None)
            validated_data.pop('product_info', None)
            mes_recipe_name = stage_product_batch_no
        else:
            site = validated_data.get('site')
            stage = validated_data.get('stage')
            product_info = validated_data.get('product_info')
            versions = validated_data.get('versions')
            if not all([site, stage, product_info, versions]):
                raise serializers.ValidationError('参数不足')
            mes_recipe_name = '{}-{}-{}-{}'.format(site.global_name, stage.global_name, product_info.product_no, versions)
        if create_new:
            mes_recipe_name += '_NEW'
            if new_recipe_id != 0:  # 删除存在的NEW配方
                new_recipe = ProductBatching.objects.filter(id=new_recipe_id).first()
                batching_details_info, weight_cnt_types_info = new_recipe.batching_details.all(), new_recipe.weight_cnt_types.all()
                if batching_details_info:
                    batching_details_info.delete()
                if weight_cnt_types_info:
                    WeighBatchingDetail.objects.filter(weigh_cnt_type__in=weight_cnt_types_info).delete()
                    weight_cnt_types_info.delete()
                ProductBatchingEquip.objects.filter(product_batching=new_recipe).delete()
                ProductBatchingMixed.objects.filter(product_batching=new_recipe).delete()
                new_recipe.delete()
        validated_data['stage_product_batch_no'] = mes_recipe_name
        stage_product_batch_no = mes_recipe_name
        instance = super().create(validated_data)
        if batching_details:
            for i, detail in enumerate(batching_details):
                material = detail.get('material')
                detail.pop('id', None)
                master = detail.pop('master', None)
                is_manual = detail.pop('is_manual', False)
                if material.material_type.global_name == '炭黑':
                    detail['type'] = 2
                elif material.material_type.global_name == '油料':
                    detail['type'] = 3
                detail['product_batching'] = instance
                detail_instance = ProductBatchingDetail.objects.create(**detail)
                # 保存投料方式设定
                if master:
                    for k, v in master.items():
                        data = {'product_batching': instance, 'equip_no': k, 'material': material, 'feeding_mode': v,
                                'handle_material_name': material.material_name, 'type': detail['type'],
                                'batching_detail_equip': detail_instance, 'is_manual': is_manual}
                        ProductBatchingEquip.objects.create(**data)
        if weight_cnt_types:
            # 新建小料包
            for weight_cnt_type in weight_cnt_types:
                weight_details = weight_cnt_type.pop('weight_details', None)
                weight_cnt_type['product_batching'] = instance
                if '-FM' in stage_product_batch_no:
                    weight_cnt_type.update({'name': '硫磺', 'weigh_type': 1})
                else:
                    weight_cnt_type.update({'name': '细料', 'weigh_type': 2})
                cnt_type_instance = WeighCntType.objects.create(**weight_cnt_type)
                if weight_details:
                    # 新建小料包详情
                    for j, weight_detail in enumerate(weight_details):
                        master = weight_detail.pop('master', None)
                        cnt_detail = weight_detail.get('material')
                        weight_detail["weigh_cnt_type"] = cnt_type_instance
                        cnt_detail_instance = WeighBatchingDetail.objects.create(**weight_detail)
                        # 保存投料方式设定
                        if master:
                            for k, v in master.items():
                                handle_material_name = cnt_detail.material_name[:-2] if cnt_detail.material_name.endswith('-C') or cnt_detail.material_name.endswith('-X') else cnt_detail.material_name
                                data = {'product_batching': instance, 'equip_no': k, 'type': 4, 'feeding_mode': v,
                                        'material': cnt_detail, 'handle_material_name': handle_material_name,
                                        'cnt_type_detail_equip': cnt_detail_instance}
                                ProductBatchingEquip.objects.create(**data)
        if mixed_ratio:
            feeds, ratios = mixed_ratio['stage'], mixed_ratio['ratio']
            f_s, f_stage = get_mixed(instance)
            if not f_s:
                raise serializers.ValidationError('对搭设置的段次信息在配方中不存在')
            f_name, f_weight, s_weight = f_s.material.material_name, round(float(f_s.actual_weight) * (ratios['f_ratio'] / sum(ratios.values())), 3), round(float(f_s.actual_weight) * (ratios['s_ratio'] / sum(ratios.values())), 3)
            created_data = {'product_batching': instance, 'f_feed': feeds['f_feed'], 's_feed': feeds['s_feed'],
                            'f_feed_name': f_name.replace(f_stage, feeds['f_feed']), 'f_ratio': ratios['f_ratio'],
                            's_feed_name': f_name.replace(f_stage, feeds['s_feed']), 's_ratio': ratios['s_ratio'],
                            'f_weight': f_weight, 's_weight': s_weight, 'origin_material_name': f_name}
            ProductBatchingMixed.objects.create(**created_data)
        if not mes_recipe_name.endswith('_NEW'):
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
                pass
        instance.save()
        # 记录履历 1、新建空配方(直接生成); 2、新建配方并生成配料
        try:
            if not create_new:
                change_data = {
                    'recipe_no': instance.stage_product_batch_no,
                    'dev_type': instance.dev_type.category_name,
                    'used_type': instance.used_type,
                    'created_time': instance.created_date,
                    'created_username': '' if not instance.created_user else instance.created_user.username,
                    'updated_time': datetime.now(),
                    'updated_username': self.context['request'].user.username
                }
                change_history, flag = RecipeChangeHistory.objects.get_or_create(defaults=change_data,
                                                                                 **{'recipe_no': instance.stage_product_batch_no,
                                                                                    'dev_type': instance.dev_type.category_name})
                desc = []
                change_detail_data = {1: [], 2: [], 3: []}  # {1: [{'type': 1, 'material_no': "aaa", 'flag': 'add', 'pv': '12', 'cv': '13'}], 2: "", 3: ""}
                # 比对配料、称量误差、比对投料方式
                if batching_details:
                    desc.append('新增配料')
                    for i in batching_details:
                        material_name = i['material'].material_name
                        change_detail_data[1].append({'type': i['type'], 'key': material_name, 'flag': '新增', 'cv': float(i['actual_weight'])})
                        if i.get('master'):
                            desc.append('新增投料方式')
                            _cv = ''
                            for _equip_no, _feed in i.get('master').items():
                                _cv = f"{_feed}({_equip_no}) "
                            change_detail_data[3].append({'type': i['type'], 'key': material_name, 'flag': '新增', 'cv': _cv})
                if weight_cnt_types:
                    desc.append('新增配料')
                    _weighting_details = weight_cnt_types[0].get('weight_details', [])
                    for i in _weighting_details:
                        material_name = i['material'].material_name
                        change_detail_data[1].append({'type': 4, 'key': material_name, 'flag': '新增', 'cv': float(i['standard_weight'])})
                        if i.get('master'):
                            desc.append('新增投料方式')
                            _cv = ''
                            for _equip_no, _feed in i.get('master').items():
                                _cv = f"{_feed}({_equip_no}) "
                            change_detail_data[3].append({'type': 4, 'key': material_name, 'flag': '新增', 'cv': _cv})
                if not flag:
                    desc = ['新增配方']
                RecipeChangeDetail.objects.create(
                    change_history=change_history,
                    desc='/'.join(set(desc)),
                    details=json.dumps(change_detail_data, ensure_ascii=False),
                    changed_username=self.context['request'].user.username
                )
                if not flag:  # 查到记录
                    change_history.used_type = 1
                    change_history.save()
        except Exception as e:
            error_logger.error(f'记录配方履历失败: {e.args[0]}')
        return instance

    class Meta:
        model = ProductBatching
        fields = ('factory', 'site', 'product_info', 'precept', 'stage_product_batch_no', 'weight_cnt_types', 'equip',
                  'create_new', 'stage', 'versions', 'batching_details', 'id', 'dev_type', 'production_time_interval',
                  'new_recipe_id', 'mixed_ratio')
        extra_kwargs = {
            'stage_product_batch_no': {
                'allow_blank': True,
                'allow_null': True,
                'required': False}
        }


class WFProductBatchingCreateSerializer(BaseModelSerializer):
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
    weigh_type = serializers.IntegerField(write_only=True, help_text='1-硫磺包 2-细料包')

    @atomic
    def create(self, validated_data):
        weight_cnt_types = validated_data.pop('weight_cnt_types', None)
        weigh_type = validated_data.pop('weigh_type')
        validated_data['batching_type'] = 3
        instance = super().create(validated_data)
        if weight_cnt_types:
            # 新建小料包
            for weight_cnt_type in weight_cnt_types:
                weight_details = weight_cnt_type.pop('weight_details', None)
                weight_cnt_type['product_batching'] = instance
                if weigh_type == 1:
                    weight_cnt_type.update({'name': '硫磺', 'weigh_type': 1})
                else:
                    weight_cnt_type.update({'name': '细料', 'weigh_type': 2})
                cnt_type_instance = WeighCntType.objects.create(**weight_cnt_type)
                if weight_details:
                    # 新建小料包详情
                    for j, weight_detail in enumerate(weight_details):
                        master = weight_detail.pop('master', None)
                        cnt_detail = weight_detail.get('material')
                        weight_detail["weigh_cnt_type"] = cnt_type_instance
                        cnt_detail_instance = WeighBatchingDetail.objects.create(**weight_detail)
                        # 保存投料方式设定
                        if master:
                            for k, v in master.items():
                                handle_material_name = cnt_detail.material_name[:-2] if cnt_detail.material_name.endswith('-C') or cnt_detail.material_name.endswith('-X') else cnt_detail.material_name
                                data = {'product_batching': instance, 'equip_no': k, 'type': 4, 'feeding_mode': v,
                                        'material': cnt_detail, 'handle_material_name': handle_material_name,
                                        'cnt_type_detail_equip': cnt_detail_instance}
                                ProductBatchingEquip.objects.create(**data)
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
            pass
        instance.save()
        return instance

    class Meta:
        model = ProductBatching
        fields = ('stage_product_batch_no', 'weight_cnt_types', 'weigh_type')
        extra_kwargs = {'stage_product_batch_no': {'validators': [UniqueValidator(queryset=ProductBatching.objects.filter(delete_flag=0),
                                                                                  message='配方已经存在')]}}


class WeighCntTypeDetailRetrieveSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.material_name', read_only=True)
    material_no = serializers.CharField(source='material.material_no', read_only=True)
    material_type = serializers.CharField(source='material.material_type.global_name', read_only=True)
    master = serializers.DictField(default={})

    def to_representation(self, instance):
        res = super().to_representation(instance)
        batching_info = ProductBatchingEquip.objects.filter(product_batching=instance.weigh_cnt_type.product_batching,
                                                            cnt_type_detail_equip=instance, type=4)
        update_data = {i.equip_no: i.feeding_mode for i in batching_info}
        res.update({'master': update_data})
        return res

    class Meta:
        model = WeighBatchingDetail
        exclude = ('weigh_cnt_type', )
        extra_kwargs = {'id': {'read_only': False, 'allow_null': True, 'required': False}}


class WeighCntTypeRetrieveSerializer(serializers.ModelSerializer):
    weight_details = WeighCntTypeDetailRetrieveSerializer(many=True)

    class Meta:
        model = WeighCntType
        exclude = ('product_batching', 'name', 'weigh_type', 'package_cnt', 'package_type')
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


class WFProductBatchingRetrieveSerializer(WFProductBatchingListSerializer):
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

    def to_representation(self, instance):
        res = super().to_representation(instance)
        s_weigh_type = instance.weight_cnt_types.filter(delete_flag=False).last()
        weigh_type = s_weigh_type.weigh_type if s_weigh_type else None
        res['weigh_type'] = weigh_type
        return res

    class Meta:
        model = ProductBatching
        fields = '__all__'


class ProductBatchingUpdateSerializer(ProductBatchingRetrieveSerializer):
    batching_detail_ids = serializers.ListField(required=False, allow_empty=True, allow_null=True)
    cnt_type_ids = serializers.ListField(required=False, allow_empty=True, allow_null=True)
    weight_detail_ids = serializers.ListField(required=False, allow_empty=True, allow_null=True)
    del_batching_equip = serializers.ListField(required=False, allow_empty=True, allow_null=True)
    mixed_ratio = serializers.DictField(default={})

    @atomic()
    def update(self, instance, validated_data):
        if instance.used_type not in (1, 4):  # 新建、启用状态的配方才可修改
            raise serializers.ValidationError('操作无效！')
        batching_details = validated_data.pop('batching_details', None)
        weight_cnt_types = validated_data.pop('weight_cnt_types', None)
        mixed_ratio = validated_data.pop('mixed_ratio')
        batching_detail_ids = validated_data.pop('batching_detail_ids', [])
        cnt_type_ids = validated_data.pop('cnt_type_ids', [])
        del_batching_equip = validated_data.pop('del_batching_equip', [])
        weight_detail_ids = validated_data.pop('weight_detail_ids', [])
        # MES配方变更履历
        if not instance.stage_product_batch_no.endswith('_NEW'):
            try:
                change_data = {
                    'recipe_no': instance.stage_product_batch_no,
                    'dev_type': instance.dev_type.category_name,
                    'used_type': instance.used_type,
                    'created_time': instance.created_date,
                    'created_username': '' if not instance.created_user else instance.created_user.username,
                    'updated_time': datetime.now(),
                    'updated_username': self.context['request'].user.username
                }
                change_history, _ = RecipeChangeHistory.objects.update_or_create(defaults=change_data,
                                                                                 **{'recipe_no': instance.stage_product_batch_no,
                                                                                    'dev_type': instance.dev_type.category_name})
                # 修改后配方详情
                desc = []
                change_detail_data = {1: [], 2: [], 3: []}
                # 比对配料、称量误差、比对投料方式
                if batching_details:
                    desc.append('新增配料')
                    for i in batching_details:
                        material_name = i['material'].material_name
                        change_detail_data[1].append({'type': i['type'], 'key': material_name, 'flag': '新增', 'cv': float(i['actual_weight'])})
                        if i.get('master'):
                            desc.append('新增投料方式')
                            _cv = ''
                            for _equip_no, _feed in i.get('master').items():
                                _cv = f"{_feed}({_equip_no}) "
                            change_detail_data[3].append({'type': i['type'], 'key': material_name, 'flag': '新增', 'cv': _cv})
                if weight_cnt_types:
                    desc.append('新增配料')
                    _weighting_details = weight_cnt_types[0].get('weight_details')
                    for i in _weighting_details:
                        material_name = i['material'].material_name
                        change_detail_data[1].append({'type': 4, 'key': material_name, 'flag': '新增', 'cv': float(i['standard_weight'])})
                        if i.get('master'):
                            desc.append('新增投料方式')
                            _cv = ''
                            for _equip_no, _feed in i.get('master').items():
                                _cv = f"{_feed}({_equip_no}) "
                            change_detail_data[3].append({'type': 4, 'key': material_name, 'flag': '新增',  'cv': _cv})
                RecipeChangeDetail.objects.create(
                    change_history=change_history,
                    desc='/'.join(set(desc)),
                    details=json.dumps(change_detail_data, ensure_ascii=False),
                    changed_username=self.context['request'].user.username
                )
            except Exception as e:
                error_logger.error(f'更新配方履历变更失败{e.args[0]}')
        ProductBatchingDetail.objects.filter(id__in=batching_detail_ids).update(delete_flag=True)
        WeighCntType.objects.filter(id__in=cnt_type_ids).update(delete_flag=True)
        WeighBatchingDetail.objects.filter(id__in=weight_detail_ids).update(delete_flag=True)
        # 禁用删除机台
        if del_batching_equip:
            ProductBatchingEquip.objects.filter(product_batching=instance, equip_no__in=del_batching_equip).delete()
        # 删除物料
        del_b_detail = list(ProductBatchingDetail.objects.filter(id__in=batching_detail_ids))
        del_c_detail = list(WeighBatchingDetail.objects.filter(id__in=weight_detail_ids).values_list('id', flat=True))
        ProductBatchingEquip.objects.filter(Q(batching_detail_equip__in=del_b_detail) | Q(cnt_type_detail_equip__in=del_c_detail), product_batching=instance).delete()
        instance = super().update(instance, validated_data)
        if batching_details is not None:
            for detail in batching_details:
                batching_detail_id = detail.pop('id', None)
                master = detail.pop('master', None)
                is_manual = detail.pop('is_manual', False)
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
                    if master:
                        for k, v in master.items():
                            exist_equip = ProductBatchingEquip.objects.filter(product_batching=instance, is_used=True, equip_no=k, material=batching_detail_instance.material)
                            if exist_equip:
                                update_data = {'type': detail['type'], 'feeding_mode': v, 'material': material,
                                               'handle_material_name': material.material_name, 'is_manual': is_manual}
                                exist_equip.filter(batching_detail_equip_id=batching_detail_id).update(**update_data)
                            else:  # 新增机台
                                create_data = {'product_batching': instance, 'equip_no': k, 'material': material,
                                               'batching_detail_equip': batching_detail_instance, 'type': detail['type'],
                                               'feeding_mode': v, 'handle_material_name': material.material_name,
                                               'is_manual': is_manual}
                                ProductBatchingEquip.objects.create(**create_data)
                else:
                    # 更新
                    detail['product_batching'] = instance
                    batching_detail_instance = ProductBatchingDetail.objects.create(**detail)
                    # 保存投料方式设定
                    if master:
                        for k, v in master.items():
                            create_data = {'product_batching': instance, 'equip_no': k, 'material': material,
                                           'batching_detail_equip': batching_detail_instance, 'type': detail['type'],
                                           'feeding_mode': v, 'handle_material_name': material.material_name,
                                           'is_manual': is_manual}
                            ProductBatchingEquip.objects.create(**create_data)
                if master:
                    # 去除配方下发状态颜色
                    ProductBatchingEquip.objects.filter(product_batching=instance, equip_no__in=master.keys()).update(send_recipe_flag=False)
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
                    if '-FM' in instance.stage_product_batch_no:
                        weight_cnt_type.update({'name': '硫磺', 'weigh_type': 1})
                    else:
                        weight_cnt_type.update({'name': '细料', 'weigh_type': 2})
                    cnt_type_instance = WeighCntType.objects.create(**weight_cnt_type)
                if weight_details:
                    # 更新小料包详情
                    for weight_detail in weight_details:
                        weight_detail_id = weight_detail.pop('id', None)
                        material = weight_detail.get('material')
                        master = weight_detail.pop('master', None)
                        if weight_detail_id:
                            # 有id则更新
                            cnt_detail = WeighBatchingDetail.objects.filter(id=weight_detail_id).first()
                            if not cnt_detail:
                                raise serializers.ValidationError('object does not exit!')
                            WeighBatchingDetail.objects.filter(id=weight_detail_id).update(**weight_detail)
                            if master:
                                for k, v in master.items():
                                    exist_equip = ProductBatchingEquip.objects.filter(product_batching=instance, is_used=True, equip_no=k, material=cnt_detail.material)
                                    handle_material_name = cnt_detail.material.material_name[:-2] if cnt_detail.material.material_name.endswith('-C') or cnt_detail.material.material_name.endswith('-X') else cnt_detail.material.material_name
                                    if exist_equip:
                                        update_data = {'type': 4, 'feeding_mode': v, 'material': material, 'handle_material_name': handle_material_name}
                                        exist_equip.filter(cnt_type_detail_equip_id=weight_detail_id).update(**update_data)
                                    else:  # 新增机台
                                        create_data = {'product_batching': instance, 'equip_no': k, 'material': material,
                                                       'cnt_type_detail_equip': cnt_detail, 'type': 4, 'feeding_mode': v,
                                                       'handle_material_name': handle_material_name}
                                        ProductBatchingEquip.objects.create(**create_data)
                        else:
                            # 否则新建
                            weight_detail["weigh_cnt_type"] = cnt_type_instance
                            cnt_detail_instance = WeighBatchingDetail.objects.create(**weight_detail)
                            # 保存投料方式设定
                            if master:
                                for k, v in master.items():
                                    handle_material_name = material.material_name[:-2] if material.material_name.endswith('-C') or material.material_name.endswith('-X') else material.material_name
                                    data = {'product_batching': instance, 'equip_no': k, 'material': material,
                                            'handle_material_name': handle_material_name,
                                            'cnt_type_detail_equip': cnt_detail_instance, 'type': 4, 'feeding_mode': v}
                                    ProductBatchingEquip.objects.create(**data)
                        if master:
                            # 去除配方下发状态颜色
                            ProductBatchingEquip.objects.filter(product_batching=instance, equip_no__in=master.keys()).update(send_recipe_flag=False)
        if mixed_ratio:
            feeds, ratios = mixed_ratio['stage'], mixed_ratio['ratio']
            f_s, f_stage = get_mixed(instance)
            if not f_s:
                raise serializers.ValidationError('对搭设置的段次信息在配方中不存在')
            f_name, f_weight, s_weight = f_s.material.material_name, round(float(f_s.actual_weight) * (ratios['f_ratio'] / sum(ratios.values())), 3), round(float(f_s.actual_weight) * (ratios['s_ratio'] / sum(ratios.values())), 3)
            mixed_recipe = ProductBatchingMixed.objects.filter(product_batching=instance)
            ready_data = {'f_feed': feeds['f_feed'], 's_feed': feeds['s_feed'], 's_weight': s_weight,
                          'f_feed_name': f_name.replace(f_stage, feeds['f_feed']), 'f_ratio': ratios['f_ratio'],
                          's_feed_name': f_name.replace(f_stage, feeds['s_feed']), 's_ratio': ratios['s_ratio'],
                          'f_weight': f_weight, 'origin_material_name': f_name}
            if mixed_recipe:
                mixed_recipe.update(**ready_data)
            else:
                ready_data.update({'product_batching': instance})
                ProductBatchingMixed.objects.create(**ready_data)
        else:  # 清除对搭设置
            ProductBatchingMixed.objects.filter(product_batching=instance).delete()
        for cnt_type_instance in instance.weight_cnt_types.filter(delete_flag=False):
            if not cnt_type_instance.weight_details.filter(delete_flag=False).exists():
                cnt_type_instance.delete_flag = True
                cnt_type_instance.save()
        instance.used_type = 1
        instance.save()
        return instance

    class Meta:
        model = ProductBatching
        fields = ('id', 'batching_details', 'dev_type', 'production_time_interval', 'weight_cnt_types',
                  'batching_detail_ids', 'cnt_type_ids', 'weight_detail_ids', 'del_batching_equip', 'mixed_ratio')


class WFProductBatchingUpdateSerializer(WFProductBatchingRetrieveSerializer):
    cnt_type_ids = serializers.ListField(required=False, allow_empty=True, allow_null=True)
    weight_detail_ids = serializers.ListField(required=False, allow_empty=True, allow_null=True)
    weigh_type = serializers.IntegerField(write_only=True, help_text='1-硫磺包 2-细料包')

    @atomic()
    def update(self, instance, validated_data):
        if instance.used_type not in (1, 4):  # 新建、启用状态的配方才可修改
            raise serializers.ValidationError('操作无效！')
        WeighBatchingDetail.objects.filter(weigh_cnt_type__in=list(instance.weight_cnt_types.all())).update(delete_flag=True)
        instance.weight_cnt_types.all().update(delete_flag=True)
        ProductBatchingEquip.objects.filter(product_batching=instance).delete()
        weight_cnt_types = validated_data.pop('weight_cnt_types', None)
        weigh_type = validated_data.pop('weigh_type')
        instance = super().update(instance, validated_data)
        if weight_cnt_types is not None:
            for weight_cnt_type in weight_cnt_types:
                weight_details = weight_cnt_type.pop('weight_details', None)
                weight_cnt_type['product_batching'] = instance
                if weigh_type == 1:
                    weight_cnt_type.update({'name': '硫磺', 'weigh_type': 1})
                else:
                    weight_cnt_type.update({'name': '细料', 'weigh_type': 2})
                cnt_type_instance = WeighCntType.objects.create(**weight_cnt_type)
                if weight_details:
                    # 更新小料包详情
                    for weight_detail in weight_details:
                        w_id = weight_detail.pop('id', None)
                        material = weight_detail.get('material')
                        master = weight_detail.pop('master', None)
                        weight_detail["weigh_cnt_type"] = cnt_type_instance
                        cnt_detail_instance = WeighBatchingDetail.objects.create(**weight_detail)
                        # 保存投料方式设定
                        if master:
                            for k, v in master.items():
                                handle_material_name = material.material_name[:-2] if material.material_name.endswith('-C') or material.material_name.endswith('-X') else material.material_name
                                data = {'product_batching': instance, 'equip_no': k, 'material': material,
                                        'handle_material_name': handle_material_name,
                                        'cnt_type_detail_equip': cnt_detail_instance, 'type': 4, 'feeding_mode': v}
                                ProductBatchingEquip.objects.create(**data)
                        if master:
                            # 去除配方下发状态颜色
                            ProductBatchingEquip.objects.filter(product_batching=instance, equip_no__in=master.keys()).update(send_recipe_flag=False)
        instance.used_type = 1
        instance.save()
        return instance

    class Meta:
        model = ProductBatching
        fields = ('weight_cnt_types', 'cnt_type_ids', 'weight_detail_ids', 'weigh_type')


class ProductBatchingPartialUpdateSerializer(BaseModelSerializer):
    pass_flag = serializers.BooleanField(help_text='通过标志，1：通过, 0:驳回', write_only=True)
    used_or_abandon = serializers.BooleanField(help_text='启用配方操作, 1: 停用, 0: 废弃', write_only=True, default=0)

    def update(self, instance, validated_data):
        pass_flag = validated_data['pass_flag']
        now_time, opera_type = datetime.now().hour, ''
        if pass_flag:
            if instance.used_type != 7:
                # 去除配方下发状态颜色
                ProductBatchingEquip.objects.filter(product_batching=instance).update(send_recipe_flag=False)
            if instance.used_type == 1:  # 提交
                instance.submit_user = self.context['request'].user
                instance.submit_time = datetime.now()
                instance.used_type = 2
                opera_type = '提交'
            elif instance.used_type == 2:  # 审核通过
                # 早上8点到17点之间提交人和校对人不能一致
                if 8 <= now_time <= 16 and instance.submit_user == self.context['request'].user:
                    raise serializers.ValidationError('配方提交人和校对人不能相同[08:00-17:00]')
                instance.used_type = 3
                instance.check_user = self.context['request'].user
                instance.check_time = datetime.now()
                opera_type = '确认'
            elif instance.used_type in (3, 7):  # 启用
                # 废弃旧版本
                # ProductBatching.objects.filter(used_type=4,
                #                                site=instance.site,
                #                                product_info=instance.product_info,
                #                                factory=instance.factory,
                #                                stage=instance.stage
                #                                ).update(used_type=6, used_time=datetime.now())
                if instance.used_type == 3 and 8 <= now_time <= 16 and instance.submit_user == self.context['request'].user:
                    raise serializers.ValidationError('配方提交人不可启用配方[08:00-17:00]')
                instance.used_type = 4
                instance.used_user = self.context['request'].user
                instance.used_time = datetime.now()
                ProductBatchingEquip.objects.filter(product_batching=instance).update(is_used=True)
            elif instance.used_type == 5:
                instance.used_type = 1
        else:
            ProductBatchingEquip.objects.filter(product_batching=instance).update(is_used=False)
            used_or_abandon = validated_data.get('used_or_abandon')
            if instance.used_type == 4 and used_or_abandon:  # 停用
                instance.used_type = 7
            elif instance.used_type in (4, 5, 7):  # 弃用
                # if instance.used_type == 4:
                #     if instance.dev_type:
                #         # 如果该配方关联的计划不是全部完成（只要有计划是等待、已下达、运行中）都不能废弃的
                #         if ProductClassesPlan.objects.exclude(status='完成').filter(product_batching=instance,
                #                                                                   delete_flag=False).exists():
                #             raise serializers.ValidationError('该配方有关联尚未完成的计划，无法废弃！')
                        # try:
                        #     ProductObsoleteInterface(instance=instance).request()
                        # except Exception as e:
                        #     sync_logger.error(e)
                instance.obsolete_user = self.context['request'].user
                instance.used_type = 6
                instance.obsolete_time = datetime.now()
            else:  # 驳回
                instance.used_type = 5
                instance.reject_user = self.context['request'].user
                instance.reject_time = datetime.now()
        try:
            record = RecipeChangeHistory.objects.filter(recipe_no=instance.stage_product_batch_no,
                                                        dev_type=instance.dev_type.category_name,
                                                        )
            record.update(used_type=instance.used_type)
            if all([record, opera_type]):
                s_record = RecipeChangeDetail.objects.filter(change_history=record.last()).order_by('id').last()
                if s_record:
                    if opera_type == '提交':
                        s_record.submit_time = instance.submit_time
                        s_record.submit_username = instance.submit_user.username
                    else:
                        s_record.confirm_time = instance.check_time
                        s_record.confirm_username = instance.check_user.username
                    s_record.save()
        except Exception as e:
            error_logger.error(f'记录修改配方状态失败:{e.args[0]}')
        instance.last_updated_user = self.context['request'].user
        instance.save()
        return instance

    class Meta:
        model = ProductBatching
        fields = ('id', 'pass_flag', 'used_or_abandon')


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


class ERPMaterialBindingSerializer(serializers.ModelSerializer):

    class Meta:
        model = ERPMESMaterialRelation
        fields = ('zc_material', 'use_flag')


class ERPMaterialCreateSerializer(BaseModelSerializer):
    erp_material_data = ERPMaterialBindingSerializer(help_text="""
    [{"zc_material": erp物料id, "use_flag": 使用与否}]""", write_only=True, many=True)
    material_no = serializers.CharField(max_length=64, help_text='编码',
                                        validators=[UniqueValidator(queryset=Material.objects.filter(delete_flag=0),
                                                                    message='该原材料编码已存在！')])
    material_name = serializers.CharField(max_length=64, help_text='名称',
                                          validators=[UniqueValidator(queryset=Material.objects.filter(delete_flag=0),
                                                                      message='该原材料名称已存在！')])

    def create(self, validated_data):
        erp_material_data = validated_data.pop('erp_material_data', [])
        validated_data.update(created_user=self.context["request"].user)
        material = Material.objects.create(**validated_data)
        for item in erp_material_data:
            item['material'] = material
            ERPMESMaterialRelation.objects.create(**item)
        # material.save()
        return validated_data

    class Meta:
        model = Material
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS
        extra_kwargs = {'material_no': {'validators': []}}


class ERPMaterialSerializer(BaseModelSerializer):
    material_type_name = serializers.ReadOnlyField(source='material_type.global_name')
    package_unit_name = serializers.ReadOnlyField(source='package_unit.global_name', default=None)
    created_user_name = serializers.ReadOnlyField(source='created_user.username', default=None)
    update_user_name = serializers.ReadOnlyField(source='last_updated_user.username', default=None, read_only=True)
    is_binding = serializers.SerializerMethodField()

    def get_is_binding(self, obj):
        return 'Y' if obj.zc_materials.count() >= 1 else 'N'

    class Meta:
        model = Material
        fields = '__all__'


class ZCMaterialSerializer(serializers.ModelSerializer):

    class Meta:
        model = ZCMaterial
        fields = '__all__'


class ERPMaterialUpdateSerializer(BaseModelSerializer):
    zc_materials = serializers.SerializerMethodField(read_only=True)
    material_type_name = serializers.ReadOnlyField(source='material_type.global_name', read_only=True)
    package_unit_name = serializers.ReadOnlyField(source='package_unit.global_name', read_only=True)
    created_user_name = serializers.ReadOnlyField(source='created_user.username', read_only=True)
    update_user_name = serializers.ReadOnlyField(source='last_updated_user.username', default=None, read_only=True)
    erp_material_data = ERPMaterialBindingSerializer(help_text="""
        [{"zc_material": erp物料id, "use_flag": 使用与否}]""", write_only=True, many=True)
    material_name = serializers.CharField(max_length=64, help_text='名称',
                                          validators=[UniqueValidator(queryset=Material.objects.filter(delete_flag=0),
                                                                      message='该原材料名称已存在')])

    def get_zc_materials(self, obj):
        data = ERPMESMaterialRelation.objects.filter(material=obj).values('zc_material__material_no',
                                                                          'zc_material__material_name',
                                                                          'use_flag',
                                                                          'zc_material__id')
        ret = []
        for item in data:
            ret.append({'id': item['zc_material__id'],
                        'material_no': item['zc_material__material_no'],
                        'material_name': item['zc_material__material_name'],
                        'use_flag': item['use_flag']})
        return ret

    def update(self, instance, validated_data):
        erp_material_data = validated_data.pop('erp_material_data', [])
        validated_data.update(last_updated_user=self.context["request"].user)
        instance = super().update(instance, validated_data)
        ERPMESMaterialRelation.objects.filter(material=instance).delete()
        for item in erp_material_data:
            item['material'] = instance
            ERPMESMaterialRelation.objects.create(**item)
        return instance

    class Meta:
        model = Material
        fields = '__all__'
        extra_kwargs = {'material_no': {'read_only': True}}
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ReplaceRecipeMaterialSerializer(serializers.ModelSerializer):
    product_no = serializers.ReadOnlyField(source='product_batching.stage_product_batch_no')
    dev_type = serializers.ReadOnlyField(source='product_batching.dev_type.category_name')

    class Meta:
        model = MultiReplaceMaterial
        fields = '__all__'


class RecipeChangeHistorySerializer(serializers.ModelSerializer):
    change_desc = serializers.SerializerMethodField()

    def get_change_desc(self, obj):
        return list(obj.change_details.order_by('id').values('desc', 'changed_time__date', 'changed_username'))

    # def to_representation(self, instance):
    #     ret = super().to_representation(instance)
    #     change_desc = ret['change_desc']
    #     change_desc.insert(0, {'desc': '群控新增' if ret['origin'] == 1 else 'MES下传新增',
    #                            'changed_time__date': ret['created_time'][:10],
    #                            'changed_username': ret['created_username']})
    #     return ret

    class Meta:
        model = RecipeChangeHistory
        fields = '__all__'


class RecipeChangeDetailRetrieveSerializer(serializers.ModelSerializer):

    class Meta:
        model = RecipeChangeDetail
        fields = ('details', 'changed_time', 'changed_username', 'submit_username', 'submit_time', 'confirm_username', 'confirm_time',
                  'sfj_down_username', 'sfj_down_time', 'weight_down_username', 'weight_down_time', 'id')


class RecipeChangeHistoryRetrieveSerializer(RecipeChangeHistorySerializer):
    change_details = RecipeChangeDetailRetrieveSerializer(many=True)

    # def to_representation(self, instance):
    #     ret = super(RecipeChangeHistoryRetrieveSerializer, self).to_representation(instance)
    #     change_details = ret['change_details']
    #     change_details.insert(0, {'details': '',
    #                               'changed_time': ret['created_time'],
    #                               'changed_username': ret['created_username']})
    #     return ret


