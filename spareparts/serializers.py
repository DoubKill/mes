import datetime
from datetime import timedelta

from rest_framework import serializers
from django.db.transaction import atomic

from rest_framework.validators import UniqueTogetherValidator, UniqueValidator
from basics.models import GlobalCodeType, GlobalCode, ClassesDetail, WorkSchedule, Equip, SysbaseEquipLevel, \
    WorkSchedulePlan, PlanSchedule, EquipCategoryAttribute, Location
from mes.base_serializer import BaseModelSerializer
from plan.uuidfield import UUidTools
from recipe.models import MaterialAttribute
from spareparts.models import SpareInventory, SpareLocationBinding, SpareInventoryLog, SpareLocation, SpareType, Spare
from django.db.models import Avg, Max, Min, Count, Sum  # 引入函数


class MaterialLocationBindingSerializer(BaseModelSerializer):
    """位置点和物料绑定"""
    spare_no = serializers.ReadOnlyField(source='spare.no', help_text='编码', default='')
    spare_name = serializers.ReadOnlyField(source='spare.name', help_text='名称', default='')
    location_name = serializers.ReadOnlyField(source='location.name', help_text='库存位', default='')

    def validate(self, attrs):
        instance_obj = self.instance
        location = attrs.get('location', None)
        if location.used_flag == 0:
            raise serializers.ValidationError('该库存位已被停用，不可选')

        if instance_obj:  # 修改
            si_obj = instance_obj.location.si_spare_location.all().filter(qty__gt=0).first()
            if si_obj:
                raise serializers.ValidationError('当前物料已存在当前库存位了,不允许修改')
            if location.type.global_name == '备品备件地面':  # 因此公用代码轻易不要动
                SpareInventory.objects.filter(spare=instance_obj.spare, location=instance_obj.location).update(
                    delete_flag=True)
                return attrs
            mlb = SpareLocationBinding.objects.exclude(
                id=instance_obj.id).filter(location=location, delete_flag=False).first()
            if mlb:
                raise serializers.ValidationError('此库存位已经绑定了物料了')
            SpareInventory.objects.filter(spare=instance_obj.spare, location=instance_obj.location).update(
                delete_flag=True)

        else:  # 新增
            if location.type.global_name == '备品备件地面':  # 因此公用代码轻易不要动
                return attrs
            mlb = SpareLocationBinding.objects.filter(location=location, delete_flag=False).first()
            if mlb:
                raise serializers.ValidationError('此库存位已经绑定了物料了')
        return attrs

    class Meta:
        model = SpareLocationBinding
        # fields = ('id', 'material_no', 'material_name', 'location_name')
        fields = "__all__"


class SpareInventorySerializer(BaseModelSerializer):
    # 备品备件库
    spare_no = serializers.ReadOnlyField(source='spare.no', help_text='编码', default='')
    cost = serializers.ReadOnlyField(source='spare.cost', help_text='单价', default='')
    spare_name = serializers.ReadOnlyField(source='spare.name', help_text='名称', default='')
    location_name = serializers.ReadOnlyField(source='location.name', help_text='库存位', default='')
    location_no = serializers.ReadOnlyField(source='location.no', help_text='库存位', default='')
    type_name = serializers.ReadOnlyField(source='spare.type.name', help_text='物料类型', default='')
    unit = serializers.ReadOnlyField(source='spare.unit', help_text='单位', default='')
    bound = serializers.SerializerMethodField(help_text='上下限', read_only=True)

    def get_bound(self, obj):
        si_obj = SpareInventory.objects.filter(spare=obj.spare, delete_flag=False).aggregate(sum_qty=Sum("qty"))
        if si_obj['sum_qty'] < obj.spare.lower:
            return '-'
        elif si_obj['sum_qty'] > obj.spare.upper:
            return '+'
        else:
            return None

    @atomic()
    def create(self, validated_data):
        if not validated_data['location']:
            location_obj = SpareLocation.objects.filter(type__global_name='备品备件地面').first()
            if not location_obj:
                raise serializers.ValidationError('请先创建一个类型为备品备件地面的库存位，因为不选库存位，我们默认是地面')
            validated_data['location'] = location_obj

        spare = validated_data['spare']
        location = validated_data['location']
        si_obj = SpareInventory.objects.filter(spare=spare, location=location, delete_flag=False).first()
        if si_obj:
            raise serializers.ValidationError('已存在该位置点和物料的数据')
        validated_data['total_count'] = validated_data['qty'] * validated_data['spare'].cost
        validated_data['unit'] = validated_data['spare'].unit
        instance = super().create(validated_data)
        SpareInventoryLog.objects.create(warehouse_no=instance.warehouse_info.no,
                                         warehouse_name=instance.warehouse_info.name,
                                         location=instance.location.no,
                                         qty=instance.qty, quality_status=instance.quality_status,
                                         spare_no=instance.spare.no,
                                         spare_name=instance.spare.name,
                                         spare_type= instance.spare.type.name if instance.spare.type else '',
                                         cost=instance.qty * instance.spare.cost,
                                         unit_count=instance.spare.cost,
                                         fin_time=datetime.date.today(),
                                         type='入库',
                                         src_qty=0, dst_qty=instance.qty, created_user=instance.created_user)
        return instance

    class Meta:
        model = SpareInventory
        fields = '__all__'


class SpareInventoryLogSerializer(BaseModelSerializer):
    # 履历
    location = serializers.SerializerMethodField(help_text='location_name', read_only=True)
    unit = serializers.SerializerMethodField(help_text='单位', read_only=True)

    def get_location(self, obj):
        sl_obj = SpareLocation.objects.get(no=obj.location)
        return sl_obj.name

    def get_unit(self, obj):
        s_obj = Spare.objects.get(no=obj.spare_no)
        return s_obj.unit

    class Meta:
        model = SpareInventoryLog
        fields = '__all__'


class SpareTypeSerializer(BaseModelSerializer):
    # 备品备件类型
    class Meta:
        model = SpareType
        fields = '__all__'


class SpareSerializer(BaseModelSerializer):
    # 备品备件信息
    type_name = serializers.ReadOnlyField(source='type.name', help_text='物料类型')

    def validate(self, attrs):
        upper = attrs.get('upper', None)  # 上
        lower = attrs.get('lower', None)  # 下
        if upper < lower:
            raise serializers.ValidationError('上限不能小于下限！')
        return attrs

    class Meta:
        model = Spare
        fields = '__all__'


class SpareLocationSerializer(BaseModelSerializer):
    # 位置点
    type_name = serializers.ReadOnlyField(source='type.global_name')

    def create(self, validated_data):
        validated_data['no'] = UUidTools.location_no(validated_data['name'])
        type = validated_data.get('type', None)
        if not type:
            validated_data['type'] = GlobalCode.objects.filter(global_name='备品备件地面').first()
        return super().create(validated_data)

    class Meta:
        model = SpareLocation
        fields = ('id', 'type_name', 'name', 'type', 'used_flag')
