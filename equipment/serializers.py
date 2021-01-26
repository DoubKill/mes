import datetime
from datetime import timedelta

from rest_framework import serializers
from django.db.transaction import atomic

from rest_framework.validators import UniqueTogetherValidator, UniqueValidator
from equipment.models import EquipDownType, EquipDownReason, EquipCurrentStatus
from mes.base_serializer import BaseModelSerializer


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