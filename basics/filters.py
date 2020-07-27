import django_filters
from django.contrib.auth.models import User, Group

from basics.models import Equip, GlobalCodeType, WorkSchedule
from system.models import GroupExtension


class EquipFilter(django_filters.rest_framework.FilterSet):
    equip_level = django_filters.CharFilter(field_name='equip_level__global_name', lookup_expr='icontains', help_text='工序')
    equip_name = django_filters.CharFilter(field_name='equip_name', lookup_expr='icontains', help_text='设备名')

    class Meta:
        model = Equip
        fields = ('equip_level', 'equip_name')


class GlobalCodeTypeFilter(django_filters.rest_framework.FilterSet):
    type_no = django_filters.CharFilter(field_name='type_no', lookup_expr='icontains', help_text='代码编号')
    type_name = django_filters.CharFilter(field_name='type_name', lookup_expr='icontains', help_text='代码名称')
    used_flag = django_filters.BooleanFilter(field_name='used_flag', lookup_expr='icontains', help_text='是否启用')

    class Meta:
        model = GlobalCodeType
        fields = ('type_no', 'type_name', 'used_flag')


class WorkScheduleFilter(django_filters.rest_framework.FilterSet):
    schedule_no = django_filters.CharFilter(field_name='schedule_no', lookup_expr='icontains', help_text='日程编号')
    schedule_name = django_filters.CharFilter(field_name='schedule_name', lookup_expr='icontains', help_text='日程名称')

    class Meta:
        model = WorkSchedule
        fields = ('schedule_no', 'schedule_name')