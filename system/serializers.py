"""
auther :liwei
create_date:
updater:
update_time:
"""

from django.contrib.auth.hashers import make_password

from django.contrib.auth.models import Permission
from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from basics.models import Equip, WorkSchedulePlan, GlobalCode
from mes.base_serializer import BaseModelSerializer
from mes.conf import COMMON_READ_ONLY_FIELDS
from plan.models import ProductClassesPlan, MaterialDemanded, ProductDayPlan
from production.models import PlanStatus
from recipe.models import ProductBatching, Material, ProductBatchingDetail
from system.models import GroupExtension, User, Section


class PermissionSerializer(BaseModelSerializer):
    class Meta:
        model = Permission
        fields = ("id", "codename", "name",)


class UserUpdateSerializer(BaseModelSerializer):
    is_active = serializers.BooleanField(read_only=True)
    username = serializers.CharField(required=False)
    password = serializers.CharField(required=False)
    num = serializers.CharField(required=False, validators=[
        UniqueValidator(queryset=User.objects.all(),
                        message='该员工工号已存在'),
    ])

    def to_representation(self, instance):
        instance = super().to_representation(instance)
        instance.pop('password')
        return instance

    def update(self, instance, validated_data):
        validated_data['password'] = make_password(validated_data['password']) if validated_data.get(
            'password') else instance.password
        return super(UserUpdateSerializer, self).update(instance, validated_data)

    class Meta:
        model = User
        fields = '__all__'


class UserSerializer(BaseModelSerializer):
    is_active = serializers.BooleanField(read_only=True)
    num = serializers.CharField(validators=[UniqueValidator(queryset=User.objects.all(), message='该员工工号已存在')])
    section_name = serializers.CharField(source="section.name", default="", read_only=True)

    def to_representation(self, instance):
        instance = super().to_representation(instance)
        instance.pop('password')
        return instance

    def create(self, validated_data):
        password = validated_data.get('password')
        user = super().create(validated_data)
        user.set_password(password)
        user.save()
        return user

    class Meta:
        model = User
        exclude = ('user_permissions', 'groups')
        extra_kwargs = {
            'group_extensions': {
                'required': False
            }
        }


class GroupUserSerializer(BaseModelSerializer):
    id = serializers.IntegerField()
    username = serializers.CharField(required=False)
    password = serializers.CharField(required=False)
    num = serializers.CharField(required=False)

    def to_representation(self, instance):
        instance = super().to_representation(instance)
        instance.pop('password')
        return instance

    class Meta:
        model = User
        fields = '__all__'


class GroupExtensionSerializer(BaseModelSerializer):
    """角色组扩展序列化器"""
    # group_users = UserUpdateSerializer(read_only=True, many=True)

    class Meta:
        model = GroupExtension
        read_only_fields = COMMON_READ_ONLY_FIELDS
        exclude = ('permissions', )

    def to_representation(self, instance):
        return super().to_representation(instance)


class GroupExtensionUpdateSerializer(BaseModelSerializer):
    """更新角色组用户序列化器"""

    class Meta:
        model = GroupExtension
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class GroupUserUpdateSerializer(BaseModelSerializer):
    """更新角色组用户序列化器"""
    group_users = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), write_only=True,
                                                     help_text="""{"group_users":[<user_id>, ……]}""")

    def update(self, instance, validated_data):
        user_ids = validated_data['group_users']
        instance.group_users.remove(*instance.group_users.all())
        instance.group_users.add(*user_ids)
        instance.save()
        return super().update(instance, validated_data)

    class Meta:
        model = GroupExtension
        fields = ('id', 'group_users')


class SectionSerializer(BaseModelSerializer):
    section_id = serializers.CharField(max_length=40,
                                           validators=[
                                               UniqueValidator(queryset=Section.objects.all(),
                                                               message='该部门编号已存在'),
                                           ])
    users = serializers.SerializerMethodField()
    in_charge_username = serializers.CharField(source='in_charge_user.username', read_only=True)

    def get_users(self, obj):
        temp_set = obj.section_users.filter(is_leave=False).values_list("username", flat=True)
        return list(temp_set)

    class Meta:
        model = Section
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ProductBatchingDetailSyncInterface(serializers.ModelSerializer):
    material = serializers.CharField(source='material.material_no')

    class Meta:
        model = ProductBatchingDetail
        fields = ('product_batching', 'sn', 'material', 'actual_weight', 'standard_error', 'auto_flag', 'type')


class ProductBatchingSyncInterface(serializers.ModelSerializer):
    batching_details = ProductBatchingDetailSyncInterface(many=True)

    class Meta:
        model = ProductBatching
        fields = (
            'factory', 'site', 'product_info', 'precept', 'stage_product_batch_no', 'dev_type', 'stage', 'versions',
            'used_type', 'batching_weight', 'manual_material_weight', 'auto_material_weight', 'volume', 'submit_user',
            'submit_time', 'reject_user', 'reject_time', 'used_user', 'used_time', 'obsolete_user', 'obsolete_time',
            'production_time_interval',
            'equip', 'batching_type', 'batching_details')


class ProductDayPlanSyncInterface(serializers.ModelSerializer):
    product_batching = serializers.CharField(source='product_batching.stage_product_batch_no')

    class Meta:
        model = ProductDayPlan
        fields = ('equip', 'product_batching', 'plan_schedule')


class PlanReceiveSerializer(serializers.ModelSerializer):
    equip = serializers.CharField()
    work_schedule_plan = serializers.CharField()
    product_batching = ProductBatchingSyncInterface()
    product_day_plan = ProductDayPlanSyncInterface()

    @atomic()
    def validate(self, attrs):
        work_schedule_plan = attrs.get('work_schedule_plan')
        product_batching = attrs.get('product_batching')
        equip = attrs.get('equip')
        batching_details = attrs['product_batching']['batching_details']
        try:
            equip = Equip.objects.get(equip_no=equip, delete_flag=False)
            work_schedule_plan = WorkSchedulePlan.objects.get(work_schedule_plan_no=work_schedule_plan,
                                                              delete_flag=False)
        except Equip.DoesNotExist:
            raise serializers.ValidationError('MES机台{}不存在'.format(attrs.get('equip')))
        except WorkSchedulePlan.DoesNotExist:
            raise serializers.ValidationError('排班详情{}不存在'.format(attrs.get('work_schedule_plan')))
        except Exception as e:
            raise serializers.ValidationError('相关表没有数据')
        # 判断胶料配方是否存在 不存在则创建
        product_batching_obj = ProductBatching.objects.filter(
            stage_product_batch_no=product_batching['stage_product_batch_no'], delete_flag=False).first()
        if not product_batching_obj:
            attrs['product_batching'] = ProductBatching.objects.create(**product_batching)
        else:
            attrs['product_batching'] = product_batching_obj
        # 判断胶料日计划是否存在 不存在则创建
        pdp_dict = attrs.get('product_day_plan')
        pb_obj = ProductBatching.objects.filter(
            stage_product_batch_no=pdp_dict['product_batching']['stage_product_batch_no']).first()
        if not pb_obj:
            raise serializers.ValidationError('配方未同步')
        pdp_obj = ProductDayPlan.objects.filter(equip=pdp_dict['equip'], product_batching=pb_obj,
                                                plan_schedule=pdp_dict['plan_schedule']).first()
        if pdp_obj:
            attrs['product_day_plan'] = pdp_obj
        else:
            attrs['product_day_plan'] = ProductDayPlan.objects.create(equip=pdp_dict['equip'], product_batching=pb_obj,
                                                                      plan_schedule=pdp_dict['plan_schedule'])
        attrs['work_schedule_plan'] = work_schedule_plan
        attrs['equip'] = equip
        for batching_details_dict in batching_details:
            m_obj = Material.objects.filter(material_no=batching_details_dict['material']['material_no']).first()
            ProductBatchingDetail.objects.create(product_batching=batching_details_dict['product_batching'],
                                                 sn=batching_details_dict['sn'], material=m_obj,
                                                 actual_weight=batching_details_dict['sn'],
                                                 standard_error=batching_details_dict['standard_error'],
                                                 auto_flag=batching_details_dict['auto_flag'],
                                                 type=batching_details_dict['type'])
        return attrs

    @atomic()
    def create(self, validated_data):
        instance = super().create(validated_data)
        # 创建计划状态
        PlanStatus.objects.create(plan_classes_uid=instance.plan_classes_uid, equip_no=instance.equip.equip_no,
                                  product_no=instance.product_batching.stage_product_batch_no,
                                  status='等待', operation_user=self.context['request'].user.username)
        # 创建原材料需求量
        for pbd_obj in instance.product_batching.batching_details.filter(delete_flag=False):
            MaterialDemanded.objects.create(product_classes_plan=instance,
                                            work_schedule_plan=instance.work_schedule_plan,
                                            material=pbd_obj.material,
                                            material_demanded=pbd_obj.actual_weight * instance.plan_trains,
                                            plan_classes_uid=instance.plan_classes_uid)
        return instance

    class Meta:
        model = ProductClassesPlan
        fields = ('product_day_plan',
                  'sn', 'plan_trains', 'time', 'weight', 'unit', 'work_schedule_plan',
                  'plan_classes_uid', 'note', 'equip',
                  'product_batching')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MaterialReceiveSerializer(serializers.ModelSerializer):
    material_type = serializers.CharField()
    package_unit = serializers.CharField()

    @atomic()
    def validate(self, attrs):
        material_type = attrs.get('material_type')
        package_unit = attrs.get('package_unit')
        try:
            material_type = GlobalCode.objects.get(global_no=material_type)
        except GlobalCode.DoesNotExist:
            raise serializers.ValidationError(
                'MES公共代码{0}不存在'.format(attrs.get('material_type')))
        except Exception as e:
            raise serializers.ValidationError('相关表没有数据')
        if package_unit == '0':
            package_unit = None
        else:
            try:
                package_unit = GlobalCode.objects.get(global_no=package_unit)
            except GlobalCode.DoesNotExist:
                raise serializers.ValidationError(
                    'MES公共代码{0}不存在'.format(attrs.get('package_unit')))
            except Exception as e:
                raise serializers.ValidationError('相关表没有数据')
        attrs['material_type'] = material_type
        attrs['package_unit'] = package_unit
        return attrs

    @atomic()
    def create(self, validated_data):
        instance = super().create(validated_data)
        return instance

    class Meta:
        model = Material
        fields = ('material_no', 'material_name', 'for_short', 'material_type', 'package_unit', 'use_flag')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class UserImportSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=150)
    num = serializers.CharField(max_length=20)
    section = serializers.CharField(max_length=512, allow_null=True, allow_blank=True)
    group_extensions = serializers.CharField(max_length=512, allow_null=True, allow_blank=True)

    def validate(self, attrs):
        username = attrs['username']
        num = attrs['num']
        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError('已存在一位使用该名字的用户：{}'.format(username))
        if User.objects.filter(num=num).exists():
            raise serializers.ValidationError('已存在一位使用该工号的用户：{}'.format(num))
        section_name = attrs.pop('section', None)
        permissions = attrs.pop('group_extensions', None)
        if section_name:
            section = Section.objects.filter(name=section_name).first()
            if not section:
                raise serializers.ValidationError('未找到该部门：{}'.format(section_name))
            attrs['section'] = section
        if permissions:
            permissions = permissions.split('/')
            ps = []
            for permission in permissions:
                p = GroupExtension.objects.filter(name=permission).first()
                if not p:
                    raise serializers.ValidationError('未找到该角色：{}'.format(permission))
                ps.append(p.id)
                attrs['group_extensions'] = ps
        return attrs

    def create(self, validated_data):
        password = validated_data.get('password')
        user = super().create(validated_data)
        user.set_password(password)
        user.save()
        return user

    class Meta:
        model = User
        fields = ('username', 'password', 'num', 'phone_number', 'id_card_num', 'section', 'group_extensions')