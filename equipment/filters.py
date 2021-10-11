import django_filters

from equipment.models import EquipDownType, EquipDownReason, EquipPart, EquipMaintenanceOrder, Property, PlatformConfig, \
    EquipCurrentStatus, EquipSupplier, EquipProperty, EquipPartNew, EquipComponent, EquipAreaDefine, EquipComponentType


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
    maintenance_username = django_filters.CharFilter(field_name='maintenance_user_id',
                                                     help_text='维修人')

    class Meta:
        model = EquipMaintenanceOrder
        fields = (
            'equip_no', 'equip_name', 'date', 'status', 'order_uid', 'equip_type', 'month', 'year',
            'maintenance_username')


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
    factory_date = django_filters.DateFilter(field_name='factory_date', help_text='日期')

    class Meta:
        model = EquipMaintenanceOrder
        fields = ('equip_no', 'equip_type', 'month', 'year')


class EquipCurrentStatusFilter(django_filters.rest_framework.FilterSet):
    status = django_filters.CharFilter(field_name='status', help_text='状态')

    class Meta:
        model = EquipCurrentStatus
        fields = ('status',)


class EquipSupplierFilter(django_filters.rest_framework.FilterSet):
    supplier_name = django_filters.CharFilter(field_name='supplier_name', help_text='供应商名称', lookup_expr='icontains')
    use_flag = django_filters.CharFilter(field_name='use_flag', help_text='是否使用')
    supplier_type = django_filters.CharFilter(field_name='supplier_type', help_text='供应商类别')

    class Meta:
        model = EquipSupplier
        fields = ('supplier_name', 'use_flag', 'supplier_type')


class EquipPropertyFilter(django_filters.rest_framework.FilterSet):
    property_no = django_filters.CharFilter(field_name='property_no', help_text='固定资产', lookup_expr='icontains')
    equip_no = django_filters.CharFilter(field_name='equip_no', help_text='设备编码', lookup_expr='icontains')
    equip_type_no = django_filters.CharFilter(field_name='equip_type__category_no', help_text='设备类型', lookup_expr='icontains')

    class Meta:
        model = EquipProperty
        fields = ('property_no', 'equip_no', 'equip_type_no')


class EquipPartNewFilter(django_filters.rest_framework.FilterSet):
    category_no = django_filters.CharFilter(field_name='equip_type__category_no', help_text='所属主设备种类', lookup_expr='icontains')
    global_name = django_filters.CharFilter(field_name='global_part_type__global_name', help_text='部位分类', lookup_expr='icontains')
    part_code = django_filters.CharFilter(field_name='part_code', help_text='部位代码', lookup_expr='icontains')
    part_name = django_filters.CharFilter(field_name='part_name', help_text='部位名称', lookup_expr='icontains')

    class Meta:
        model = EquipPartNew
        fields = ('category_no', 'global_name', 'part_code', 'part_name')


class EquipComponentTypeFilter(django_filters.rest_framework.FilterSet):
    component_type_name = django_filters.CharFilter(field_name='component_type_name', help_text='类型名称', lookup_expr='icontains')
    component_type_code = django_filters.CharFilter(field_name='component_type_code', help_text='类型编码', lookup_expr='icontains')

    class Meta:
        model = EquipComponentType
        fields = ('component_type_name', 'component_type_code')


class EquipAreaDefineFilter(django_filters.rest_framework.FilterSet):

    area_name = django_filters.CharFilter(field_name='area_name', help_text='位置区域名称', lookup_expr='icontains')
    use_flag = django_filters.CharFilter(field_name='use_flag', help_text='是否启用')

    class Meta:
        model = EquipAreaDefine
        fields = ('area_name', 'use_flag')
