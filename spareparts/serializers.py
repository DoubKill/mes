import datetime
from datetime import timedelta

from rest_framework import serializers
from django.db.transaction import atomic

from rest_framework.validators import UniqueTogetherValidator, UniqueValidator
from basics.models import GlobalCodeType, GlobalCode, ClassesDetail, WorkSchedule, Equip, SysbaseEquipLevel, \
    WorkSchedulePlan, PlanSchedule, EquipCategoryAttribute
from mes.base_serializer import BaseModelSerializer
from plan.uuidfield import UUidTools
from spareparts.models import SpareInventory, MaterialLocationBinding, SpareInventoryLog


class MaterialLocationBindingSerializer(BaseModelSerializer):
    """位置点和物料绑定"""
    material_no = serializers.ReadOnlyField(source='material.material_no', help_text='编码', default='')
    material_name = serializers.ReadOnlyField(source='material.material_name', help_text='名称', default='')
    location_name = serializers.ReadOnlyField(source='location.name', help_text='库存位', default='')

    def validate(self, attrs):
        location = attrs.get('location', None)
        material = attrs.get('material', None)
        mlb = MaterialLocationBinding.objects.filter(location=location, delete_flag=False).first()
        if mlb:
            raise serializers.ValidationError('此库存位已经绑定了物料了')
        return attrs

    class Meta:
        model = MaterialLocationBinding
        # fields = ('id', 'material_no', 'material_name', 'location_name')
        fields = "__all__"


class SpareInventorySerializer(BaseModelSerializer):
    # 备品备件库
    material_no = serializers.ReadOnlyField(source='material.material_no', help_text='编码', default='')
    material_name = serializers.ReadOnlyField(source='material.material_name', help_text='名称', default='')
    location_name = serializers.ReadOnlyField(source='location.name', help_text='库存位', default='')

    @atomic()
    def create(self, validated_data):
        instance = super().create(validated_data)
        SpareInventoryLog.objects.create(warehouse_no=instance.warehouse_info.no,
                                         warehouse_name=instance.warehouse_info.name,
                                         location=instance.location.name,
                                         qty=instance.qty, quality_status=instance.quality_status,
                                         material_no=instance.material.material_no,
                                         material_name=instance.material.material_name, fin_time=datetime.date.today(),
                                         type='入库',
                                         src_qty=0, dst_qty=instance.qty, created_user=instance.created_user)
        return instance

    class Meta:
        model = SpareInventory
        fields = '__all__'


class SpareInventoryLogSerializer(BaseModelSerializer):
    class Meta:
        model = SpareInventoryLog
        fields = '__all__'
