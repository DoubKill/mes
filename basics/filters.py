import django_filters

from basics.models import Equip, GlobalCodeType, WorkSchedule, GlobalCode, EquipCategoryAttribute


class EquipFilter(django_filters.rest_framework.FilterSet):
    equip_level = django_filters.CharFilter(field_name='equip_level__global_name', lookup_expr='icontains', help_text='设备层级')
    equip_name = django_filters.CharFilter(field_name='equip_name', lookup_expr='icontains', help_text='设备名')
    equip_process = django_filters.CharFilter(field_name="category__process__global_name", lookup_expr='icontains', help_text='工序')

    class Meta:
        model = Equip
        fields = ('equip_level', 'equip_name', 'equip_process')


class GlobalCodeTypeFilter(django_filters.rest_framework.FilterSet):
    type_no = django_filters.CharFilter(field_name='type_no', lookup_expr='icontains', help_text='代码编号')
    type_name = django_filters.CharFilter(field_name='type_name', lookup_expr='icontains', help_text='代码名称')
    used_flag = django_filters.BooleanFilter(field_name='used_flag', help_text='是否启用')
    class_name = django_filters.CharFilter(field_name='type_name',  help_text='筛选班次')

    class Meta:
        model = GlobalCodeType
        fields = ('type_no', 'type_name', 'used_flag', 'class_name')


class WorkScheduleFilter(django_filters.rest_framework.FilterSet):
    schedule_no = django_filters.CharFilter(field_name='schedule_no', lookup_expr='icontains', help_text='日程编号')
    schedule_name = django_filters.CharFilter(field_name='schedule_name', lookup_expr='icontains', help_text='日程名称')

    class Meta:
        model = WorkSchedule
        fields = ('schedule_no', 'schedule_name')


class GlobalCodeFilter(django_filters.rest_framework.FilterSet):
    class_name = django_filters.CharFilter(field_name='global_type__type_name', help_text='筛选班次')
    id = django_filters.CharFilter(field_name='global_type__id', help_text="全局代码类型id")
    type_no = django_filters.CharFilter(field_name='global_type__type_no', help_text="全局代码类型编码")
    used_flag = django_filters.BooleanFilter(field_name='used_flag', help_text='是否启用')

    class Meta:
        model = GlobalCode
        fields = ('class_name', 'id', 'type_no', 'used_flag')


class EquipCategoryFilter(django_filters.rest_framework.FilterSet):
    category_name = django_filters.CharFilter(field_name="category_name", lookup_expr='icontains', help_text="设备机型名称")
    equip_type_name = django_filters.CharFilter(field_name="equip_type__global_name", lookup_expr='icontains', help_text="设备类型名称")

    class Meta:
        model = EquipCategoryAttribute
        fields = ('category_name', 'equip_type_name')