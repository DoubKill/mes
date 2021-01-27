import datetime
from datetime import timedelta

from rest_framework import serializers
from django.db.transaction import atomic

from rest_framework.validators import UniqueTogetherValidator, UniqueValidator

from basics.models import WorkSchedulePlan
from equipment.models import EquipDownType, EquipDownReason, EquipCurrentStatus, EquipMaintenanceOrder, EquipPart
from mes.base_serializer import BaseModelSerializer
from plan.uuidfield import UUidTools


class EquipDownTypeSerializer(BaseModelSerializer):
    class Meta:
        model = EquipDownType
        fields = "__all__"
        validators = [UniqueTogetherValidator(queryset=EquipDownType.objects.filter(delete_flag=False).all(),
                                              fields=('no', 'name'), message='该数据已存在'),
                      UniqueTogetherValidator(queryset=EquipDownType.objects.filter(delete_flag=False).all(),
                                              fields=('no',), message='该类型代码已存在'),
                      UniqueTogetherValidator(queryset=EquipDownType.objects.filter(delete_flag=False).all(),
                                              fields=('name',), message='该类型名称已存在'),
                      ]


class EquipDownReasonSerializer(BaseModelSerializer):
    equip_down_type_name = serializers.CharField(source='equip_down_type.name', read_only=True, help_text='停机类型')

    class Meta:
        model = EquipDownReason
        fields = "__all__"


class EquipCurrentStatusSerializer(BaseModelSerializer):
    equip_no = serializers.CharField(source='equip.equip_no', read_only=True, help_text='设备编码')
    equip_name = serializers.CharField(source='equip.equip_name', read_only=True, help_text='设备名称')
    equip_type = serializers.CharField(source='equip.category.equip_type.global_name', read_only=True, help_text='设备类型')
    process = serializers.CharField(source='equip.category.process.global_name', read_only=True, help_text='工序')

    class Meta:
        model = EquipCurrentStatus
        fields = "__all__"


class EquipPartSerializer(BaseModelSerializer):
    equip_no = serializers.CharField(source='equip.equip_no', read_only=True, help_text='设备编码')
    equip_name = serializers.CharField(source='equip.equip_name', read_only=True, help_text='设备名称')
    equip_type = serializers.CharField(source='equip.category.equip_type.global_name', read_only=True, help_text='设备类型')
    process = serializers.CharField(source='equip.category.process.global_name', read_only=True, help_text='工序')
    location_name = serializers.CharField(source='location.name', read_only=True, help_text='位置点')

    class Meta:
        model = EquipPart
        fields = "__all__"
        validators = [UniqueTogetherValidator(queryset=EquipPart.objects.filter(delete_flag=False).all(),
                                              fields=('no', 'name', 'equip', 'location'), message='该数据已存在')]


class EquipMaintenanceOrderSerializer(BaseModelSerializer):
    equip_no = serializers.CharField(source='equip.equip_no', read_only=True, help_text='设备编码')
    equip_name = serializers.CharField(source='equip.equip_name', read_only=True, help_text='设备名称')
    part_name = serializers.CharField(source='part.name', read_only=True, help_text='设备部位名称')

    class Meta:
        model = EquipMaintenanceOrder
        fields = '__all__'
