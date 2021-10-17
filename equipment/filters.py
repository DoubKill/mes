import django_filters

from equipment.models import EquipDownType, EquipDownReason, EquipPart, EquipMaintenanceOrder, Property, PlatformConfig, \
    EquipCurrentStatus, EquipSupplier, EquipProperty, EquipPartNew, EquipComponent, EquipAreaDefine, EquipComponentType, \
    ERPSpareComponentRelation, EquipSpareErp, EquipFault, EquipFaultType, \
    EquipCurrentStatus, EquipFaultSignal, EquipMachineHaltType, EquipMachineHaltReason, EquipOrderAssignRule, EquipBom, \
    EquipJobItemStandard


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


# **************************2021-10-09最新序过滤器**************************


class EquipSupplierFilter(django_filters.rest_framework.FilterSet):
    supplier_name = django_filters.CharFilter(field_name='supplier_name', help_text='供应商名称', lookup_expr='icontains')
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
    equip_type = django_filters.NumberFilter(field_name='equip_type_id', help_text='所属主设备种类')
    category_no = django_filters.NumberFilter(field_name='equip_type__id', help_text='所属主设备种类')
    global_name = django_filters.CharFilter(field_name='global_part_type__global_name', help_text='部位分类', lookup_expr='icontains')
    part_code = django_filters.CharFilter(field_name='part_code', help_text='部位代码', lookup_expr='icontains')
    part_name = django_filters.CharFilter(field_name='part_name', help_text='部位名称', lookup_expr='icontains')

    class Meta:
        model = EquipPartNew
        fields = ('equip_type', 'category_no', 'global_name', 'part_code', 'part_name')


class EquipComponentTypeFilter(django_filters.rest_framework.FilterSet):
    component_type_name = django_filters.CharFilter(field_name='component_type_name', help_text='类型名称', lookup_expr='icontains')
    component_type_code = django_filters.CharFilter(field_name='component_type_code', help_text='类型编码', lookup_expr='icontains')

    class Meta:
        model = EquipComponentType
        fields = ('component_type_name', 'component_type_code')


class EquipAreaDefineFilter(django_filters.rest_framework.FilterSet):

    area_name = django_filters.CharFilter(field_name='area_name', help_text='位置区域名称', lookup_expr='icontains')

    class Meta:
        model = EquipAreaDefine
        fields = ('area_name', 'use_flag')

# class EquipSpareErpFilter(django_filters.rest_framework.FilterSet):
#     equip_component_type = django_filters.CharFilter(field_name='equip_component_type__component_type_name',
#                                                      help_text='备件分类', lookup_expr='icontains')
#     spare_code = django_filters.CharFilter(field_name='spare_code', help_text='备件编码', lookup_expr='icontains')
#     spare_name = django_filters.CharFilter(field_name='spare_name', help_text='备件名称',  lookup_expr='icontains')
#     supplier_name = django_filters.CharFilter(field_name='supplier_name', help_text='备件经销商', lookup_expr='icontains')
#
#     class Meta:
#         model = EquipSpareErp
#         fields = ('equip_component_type', 'spare_code', 'spare_name', 'supplier_name')


class ERPSpareComponentRelationFilter(django_filters.rest_framework.FilterSet):
    equip_component_id = django_filters.CharFilter(field_name='equip_component_id', help_text="部件id")

    class Meta:
        model = ERPSpareComponentRelation
        fields = ('equip_component_id',)


class EquipSpareErpFilter(django_filters.rest_framework.FilterSet):
    equip_component_type = django_filters.CharFilter(field_name='equip_component_type__component_type_name',
                                                     help_text='备件分类', lookup_expr='icontains')
    spare_code = django_filters.CharFilter(field_name='spare_code', help_text='备件编码', lookup_expr='icontains')
    spare_name = django_filters.CharFilter(field_name='spare_name', help_text='备件名称',  lookup_expr='icontains')
    supplier_name = django_filters.CharFilter(field_name='supplier_name', help_text='供应商名称', lookup_expr='icontains')
    specification = django_filters.CharFilter(field_name='specification', help_text='规格型号', lookup_expr='icontains')

    class Meta:
        model = EquipSpareErp
        fields = ('equip_component_type', 'spare_code', 'spare_name', 'supplier_name', 'specification', 'use_flag')


class EquipBomFilter(django_filters.rest_framework.FilterSet):
    factory_id = django_filters.CharFilter(field_name='factory_id', lookup_expr='icontains', help_text='分厂')
    property_type_node = django_filters.CharFilter(field_name='property_type_node', lookup_expr='icontains', help_text='设备类型')
    equip_no = django_filters.CharFilter(field_name='equip_no', lookup_expr='icontains', help_text='机台')
    part_name = django_filters.CharFilter(field_name='part_name', lookup_expr='icontains', help_text='部位名称')
    component_name = django_filters.CharFilter(field_name='component_name', lookup_expr='icontains', help_text='部件名称')

    class Meta:
        model = EquipBom
        fields = ('factory_id', 'property_type_node', 'equip_no', 'part_name', 'component_name', 'level')


class EquipFaultTypeFilter(django_filters.rest_framework.FilterSet):
    fault_type_name = django_filters.CharFilter(field_name='fault_type_name', lookup_expr='icontains', help_text='故障分类名称')

    class Meta:
        model = EquipFaultType
        fields = ('fault_type_name', 'use_flag')


class EquipFaultCodeFilter(django_filters.rest_framework.FilterSet):
    id = django_filters.CharFilter(field_name='equip_fault_type__id', help_text="故障分类类型id")
    fault_type_name = django_filters.CharFilter(field_name='equip_fault_type__fault_type_name', help_text="大分类名称", lookup_expr='icontains')
    fault_name = django_filters.CharFilter(field_name='fault_name', help_text="中故障分类名称", lookup_expr='icontains')
    fault_code = django_filters.CharFilter(field_name='fault_code', help_text="中故障分类名称", lookup_expr='icontains')

    class Meta:
        model = EquipFault
        fields = ('id', 'fault_name', 'use_flag', 'fault_type_name', 'fault_code')


class EquipFaultSignalFilter(django_filters.rest_framework.FilterSet):
    equip_no = django_filters.CharFilter(field_name='equip__equip_no', help_text='机台编号')
    equip_name = django_filters.CharFilter(field_name='equip__equip_name', help_text='机台名称', lookup_expr='icontains')
    signal_name = django_filters.CharFilter(field_name='signal_name', help_text='信号名称', lookup_expr='icontains')
    signal_variable_type = django_filters.CharFilter(field_name='signal_variable_type', help_text='故障变量类型', lookup_expr='icontains')

    class Meta:
        model = EquipFaultSignal
        fields = ('alarm_signal_down_flag', 'fault_signal_down_flag', 'use_flag', 'equip_no',
                  'equip_name', 'signal_name', 'signal_variable_type')


class EquipMachineHaltTypeFilter(django_filters.rest_framework.FilterSet):
    machine_halt_type_name = django_filters.CharFilter(field_name='machine_halt_type_name', help_text='停机分类名称', lookup_expr='icontains')

    class Meta:
        model = EquipMachineHaltType
        fields = ('machine_halt_type_name', 'use_flag')


class EquipMachineHaltReasonFilter(django_filters.rest_framework.FilterSet):
    machine_halt_reason_name = django_filters.CharFilter(field_name='machine_halt_reason_name', help_text='停机原因名称', lookup_expr='icontains')

    class Meta:
        model = EquipMachineHaltReason
        fields = ('machine_halt_reason_name', 'use_flag', 'equip_machine_halt_type_id')


class EquipOrderAssignRuleFilter(django_filters.rest_framework.FilterSet):
    rule_name = django_filters.CharFilter(field_name='rule_name', help_text='标准名称', lookup_expr='icontains')
    work_type = django_filters.CharFilter(field_name='work_type', help_text='作业类型')
    equip_type_id = django_filters.CharFilter(field_name='equip_type_id', help_text='设备类型id')
    equip_condition = django_filters.CharFilter(field_name='equip_condition', help_text='设备条件')
    important_level = django_filters.CharFilter(field_name='important_level', help_text='重要程度')

    class Meta:
        model = EquipOrderAssignRule
        fields = ('rule_name', 'work_type', 'equip_type_id', 'equip_condition', 'important_level', 'use_flag')


class EquipJobItemStandardFilter(django_filters.rest_framework.FilterSet):
    work_type = django_filters.ChoiceFilter(choices=EquipJobItemStandard.WORK_TYPE_CHOICE, help_text='作业类型')
    standard_name = django_filters.CharFilter(field_name='standard_name', help_text='作业项目', lookup_expr='icontains')

    class Meta:
        model = EquipJobItemStandard
        fields = ('work_type', 'standard_name')
