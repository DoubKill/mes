import django_filters

from equipment.models import EquipDownType, EquipDownReason, EquipPart, EquipMaintenanceOrder, Property, PlatformConfig


class EquipDownTypeFilter(django_filters.rest_framework.FilterSet):
    no = django_filters.CharFilter(field_name='no', help_text='类型代码', lookup_expr='icontains')
    name = django_filters.CharFilter(field_name='name', help_text='类型名称')

    class Meta:
        model = EquipDownType
        fields = ('no', 'name')


class EquipDownReasonFilter(django_filters.rest_framework.FilterSet):
    equip_down_type_name = django_filters.CharFilter(field_name='equip_down_type__name', help_text='停机类型名称')

    class Meta:
        model = EquipDownReason
        fields = ('equip_down_type_name',)


class EquipPartFilter(django_filters.rest_framework.FilterSet):
    equip_no = django_filters.CharFilter(field_name='equip__equip_no', help_text='设备编码', lookup_expr='icontains')
    equip_name = django_filters.CharFilter(field_name='equip__equip_name', help_text='设备名称', lookup_expr='icontains')
    equip_type = django_filters.CharFilter(field_name='equip__category__equip_type__global_name', help_text='设备类型')

    class Meta:
        model = EquipPart
        fields = ('equip_no', 'equip_name', 'equip_type')


class EquipMaintenanceOrderFilter(django_filters.rest_framework.FilterSet):
    equip_no = django_filters.CharFilter(field_name='equip_part__equip__equip_no', help_text='设备编码',
                                         lookup_expr='icontains')
    equip_name = django_filters.CharFilter(field_name='equip_part__equip__equip_name', help_text='设备名称',
                                           lookup_expr='icontains')
    date = django_filters.DateFilter(field_name='created_date__date', help_text='日期')
    month = django_filters.DateFilter(field_name='factory_date__month', help_text='生产日期-月')
    year = django_filters.DateFilter(field_name='factory_date__year', help_text='生产日期-年')
    order_uid = django_filters.CharFilter(field_name='order_uid', help_text='单号', lookup_expr='icontains')
    equip_type = django_filters.CharFilter(field_name='equip_part__equip__category__equip_type__global_name',
                                           help_text='设备类型', )

    class Meta:
        model = EquipMaintenanceOrder
        fields = (
            'equip_no', 'equip_name', 'date', 'status', 'order_uid', 'equip_type', 'month', 'year')


class PropertyFilter(django_filters.rest_framework.FilterSet):
    property_no = django_filters.CharFilter(field_name='property_no', help_text='固定资产编码', lookup_expr='icontains')
    equip_no = django_filters.CharFilter(field_name='equip_no', help_text='设备编码', lookup_expr='icontains')
    property_type = django_filters.CharFilter(field_name='property_type_node__name', help_text='固定资产类型')

    class Meta:
        model = Property
        fields = ('property_no', 'equip_no', 'property_type')


class PlatformConfigFilter(django_filters.rest_framework.FilterSet):
    platform = django_filters.CharFilter(field_name='platform', help_text='平台', lookup_expr='icontains')

    class Meta:
        model = PlatformConfig
        fields = ('platform',)


class EquipMaintenanceOrderLogFilter(django_filters.rest_framework.FilterSet):
    equip_no = django_filters.CharFilter(field_name='equip_part__equip__equip_no', help_text='设备编码',
                                         lookup_expr='icontains')
    month = django_filters.NumberFilter(field_name='factory_date__month', help_text='生产日期-月')
    year = django_filters.NumberFilter(field_name='factory_date__year', help_text='生产日期-年')
    equip_type = django_filters.CharFilter(field_name='equip_part__equip__category__equip_type__global_name',
                                           help_text='设备类型', )

    class Meta:
        model = EquipMaintenanceOrder
        fields = ('equip_no', 'equip_type', 'month', 'year')
