import django_filters

from basics.models import Equip, GlobalCodeType, WorkSchedule, GlobalCode, EquipCategoryAttribute, ClassesDetail, \
    PlanSchedule, Location


class EquipFilter(django_filters.rest_framework.FilterSet):
    equip_level = django_filters.CharFilter(field_name='equip_level__global_name', lookup_expr='icontains',
                                            help_text='设备层级')
    equip_name = django_filters.CharFilter(field_name='equip_name', lookup_expr='icontains', help_text='设备名')
    equip_no = django_filters.CharFilter(field_name='equip_no', lookup_expr='icontains', help_text='设备名')
    equip_process = django_filters.CharFilter(field_name="category__process__global_name", lookup_expr='icontains',
                                              help_text='工序')
    category_name = django_filters.CharFilter(field_name='category__equip_type__global_name', help_text='设备类型名称')

    class Meta:
        model = Equip
        fields = ('equip_level', 'equip_name', 'equip_process', 'category_name', 'category', 'equip_no')


class GlobalCodeTypeFilter(django_filters.rest_framework.FilterSet):
    type_no = django_filters.CharFilter(field_name='type_no', lookup_expr='icontains', help_text='代码编号')
    type_name = django_filters.CharFilter(field_name='type_name', lookup_expr='icontains', help_text='代码名称')
    use_flag = django_filters.BooleanFilter(field_name='use_flag', help_text='是否启用')
    class_name = django_filters.CharFilter(field_name='type_name', help_text='筛选班次')

    class Meta:
        model = GlobalCodeType
        fields = ('type_no', 'type_name', 'use_flag', 'class_name')


class WorkScheduleFilter(django_filters.rest_framework.FilterSet):
    schedule_no = django_filters.CharFilter(field_name='schedule_no', lookup_expr='icontains', help_text='日程编号')
    schedule_name = django_filters.CharFilter(field_name='schedule_name', lookup_expr='icontains', help_text='日程名称')
    work_procedure = django_filters.CharFilter(field_name="work_procedure__global_name", help_text="工序")

    class Meta:
        model = WorkSchedule
        fields = ('schedule_no', 'schedule_name', 'work_procedure')


class GlobalCodeFilter(django_filters.rest_framework.FilterSet):
    class_name = django_filters.CharFilter(field_name='global_type__type_name', help_text='筛选班次')
    id = django_filters.CharFilter(field_name='global_type__id', help_text="全局代码类型id")
    type_no = django_filters.CharFilter(field_name='global_type__type_no', help_text="全局代码类型编码")
    use_flag = django_filters.NumberFilter(field_name='use_flag', help_text='0代表启用状态')

    class Meta:
        model = GlobalCode
        fields = ('class_name', 'id', 'type_no', 'use_flag')


class EquipCategoryFilter(django_filters.rest_framework.FilterSet):
    category_name = django_filters.CharFilter(field_name="category_name", lookup_expr='icontains', help_text="设备机型名称")
    equip_type_name = django_filters.CharFilter(field_name="equip_type__global_name", lookup_expr='icontains',
                                                help_text="设备类型名称")

    class Meta:
        model = EquipCategoryAttribute
        fields = ('category_name', 'equip_type_name')


class ClassDetailFilter(django_filters.rest_framework.FilterSet):
    schedule_name = django_filters.CharFilter(field_name='work_schedule__schedule_name', help_text='日程名称')

    class Meta:
        model = ClassesDetail
        fields = ('schedule_name',)


class PlanScheduleFilter(django_filters.rest_framework.FilterSet):
    year = django_filters.NumberFilter(field_name='day_time__year', help_text='年份')
    month = django_filters.NumberFilter(field_name='day_time__month', help_text='月份')
    work_schedule__schedule_name = django_filters.CharFilter(field_name="work_schedule__schedule_name",
                                                             lookup_expr='icontains', help_text="倒班名称")
    work_procedure = django_filters.CharFilter(field_name='work_schedule__work_procedure', help_text="工序")
    st = django_filters.DateFilter(field_name='day_time', lookup_expr='gte')
    et = django_filters.DateFilter(field_name='day_time', lookup_expr='lte')

    class Meta:
        model = PlanSchedule
        fields = ('day_time', 'month', 'year', 'work_schedule__schedule_name', 'work_procedure', 'st', 'et')


class LocationFilter(django_filters.rest_framework.FilterSet):
    name = django_filters.CharFilter(field_name='name', help_text='名称',lookup_expr='icontains')
    type_name = django_filters.CharFilter(field_name='type__global_name', help_text='类型')

    class Meta:
        model = Location
        fields = ('name', 'type_name')
