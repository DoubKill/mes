import django_filters

from spareparts.models import MaterialLocationBinding, SpareInventoryLog, SpareInventory


class SpareInventoryFilter(django_filters.rest_framework.FilterSet):
    material_no = django_filters.CharFilter(field_name='material__material_no', help_text='编码', lookup_expr='icontains')
    material_name = django_filters.CharFilter(field_name='material__material_name', help_text='名称',
                                              lookup_expr='icontains')
    location_name = django_filters.CharFilter(field_name='location__name', help_text='库存位',lookup_expr='icontains')

    class Meta:
        model = SpareInventory
        fields = ('material_no', 'material_name', 'location_id')


class MaterialLocationBindingFilter(django_filters.rest_framework.FilterSet):
    material_no = django_filters.CharFilter(field_name='material__material_no', help_text='编码', lookup_expr='icontains')
    material_name = django_filters.CharFilter(field_name='material__material_name', help_text='名称',
                                              lookup_expr='icontains')
    location_name = django_filters.CharFilter(field_name='location__name', help_text='库存位', lookup_expr='icontains')

    class Meta:
        model = MaterialLocationBinding
        fields = ('material_no', 'material_name', 'location_name')


class SpareInventoryLogFilter(django_filters.rest_framework.FilterSet):
    material_no = django_filters.CharFilter(field_name='material_no', help_text='编码', lookup_expr='icontains')
    material_name = django_filters.CharFilter(field_name='material_name', help_text='名称', lookup_expr='icontains')
    location_name = django_filters.CharFilter(field_name='location', help_text='库存位', lookup_expr='icontains')
    type = django_filters.CharFilter(field_name='type', help_text='类型', lookup_expr='icontains')
    begin_time = django_filters.DateTimeFilter(field_name='fin_time', lookup_expr="gte",
                                               help_text='开始时间')
    end_time = django_filters.DateTimeFilter(field_name='fin_time', lookup_expr="lte",
                                             help_text='结束时间')

    class Meta:
        model = SpareInventoryLog
        fields = ('material_no', 'material_name', 'location_name', 'begin_time', 'end_time', 'type')
