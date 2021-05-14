import django_filters

from quality.models import MaterialTestOrder, MaterialDataPointIndicator, \
    MaterialTestMethod, TestMethod, DataPoint, DealSuggestion, MaterialDealResult, UnqualifiedDealOrder, DataPointRaw, \
    TestMethodRaw, MaterialTestMethodRaw, MaterialDataPointIndicatorRaw, MaterialTestOrderRaw, \
    UnqualifiedMaterialDealResult, ExamineMaterial, MaterialExamineEquipment, MaterialExamineType


class TestMethodFilter(django_filters.rest_framework.FilterSet):
    test_indicator_id = django_filters.NumberFilter(field_name='test_type__test_indicator_id', help_text='试验指标id')

    class Meta:
        model = TestMethod
        fields = ('test_indicator_id', 'test_type_id')


class DataPointFilter(django_filters.rest_framework.FilterSet):
    test_indicator_id = django_filters.NumberFilter(field_name='test_type__test_indicator_id', help_text='试验指标id')
    test_type_id = django_filters.NumberFilter(field_name='test_type_id', help_text='试验类型id')

    class Meta:
        model = DataPoint
        fields = ('test_indicator_id', 'test_indicator_id')


class MaterialTestOrderFilter(django_filters.rest_framework.FilterSet):
    st = django_filters.DateFilter(field_name="production_factory_date", help_text='开始工厂日期', lookup_expr='gte')
    et = django_filters.DateFilter(field_name="production_factory_date", help_text='结束工厂日期', lookup_expr='lte')
    equip_no = django_filters.CharFilter(field_name='production_equip_no', help_text='机号')
    product_no = django_filters.CharFilter(field_name='product_no', lookup_expr='icontains', help_text='产出胶料编号')
    classes = django_filters.CharFilter(field_name="production_class", help_text='班次')
    stage = django_filters.CharFilter(field_name='product_no', lookup_expr='icontains', help_text='段次')

    class Meta:
        model = MaterialTestOrder
        fields = ('st', 'et', 'equip_no', 'product_no', "classes", 'stage', 'is_qualified')


class MaterialDataPointIndicatorFilter(django_filters.rest_framework.FilterSet):
    material_test_method_id = django_filters.CharFilter(field_name='material_test_method_id',
                                                        help_text='物料试验方法id')

    class Meta:
        model = MaterialDataPointIndicator
        fields = ('material_test_method_id',)


class MaterialTestMethodFilter(django_filters.rest_framework.FilterSet):
    material_no = django_filters.CharFilter(field_name="material__material_no", lookup_expr='icontains',
                                            help_text='胶料编码')
    test_type_id = django_filters.NumberFilter(field_name='test_method__test_type_id',
                                               help_text='试验类型id')
    test_indicator_id = django_filters.NumberFilter(field_name='test_method__test_type__test_indicator_id',
                                                    help_text='试验指标id')

    class Meta:
        model = MaterialTestMethod
        fields = ('material_no', 'test_indicator_id', 'test_type_id')


class DealSuggestionFilter(django_filters.rest_framework.FilterSet):
    deal_type = django_filters.NumberFilter(field_name='deal_type_id', help_text='处理类型id')
    type_name = django_filters.CharFilter(field_name='deal_type__global_name', help_text="类型名称")

    class Meta:
        model = DealSuggestion
        fields = ("deal_type",)


class MaterialDealResulFilter(django_filters.rest_framework.FilterSet):
    day = django_filters.CharFilter(field_name='production_factory_date', lookup_expr='icontains', help_text='生产日期筛选')
    status = django_filters.CharFilter(field_name='status', help_text='状态筛选')

    class Meta:
        model = MaterialDealResult
        fields = ("status", "day")


class PalletFeedbacksTestFilter(django_filters.rest_framework.FilterSet):
    suggestion_desc = django_filters.CharFilter(field_name='deal_suggestion', help_text='处理意见筛选')

    class Meta:
        model = MaterialDealResult
        fields = ('suggestion_desc',)


class UnqualifiedDealOrderFilter(django_filters.rest_framework.FilterSet):
    st = django_filters.DateFilter(field_name='created_date__date', lookup_expr='gte', help_text='开始时间')
    et = django_filters.DateFilter(field_name='created_date__date', lookup_expr='lte', help_text='结束时间')

    class Meta:
        model = UnqualifiedDealOrder
        fields = ('st', 'et')


class DataPointRawFilter(django_filters.rest_framework.FilterSet):
    test_indicator_id = django_filters.NumberFilter(field_name='test_type__test_indicator_id', help_text='试验指标id')
    test_type_id = django_filters.NumberFilter(field_name='test_type_id', help_text='试验类型id')

    class Meta:
        model = DataPointRaw
        fields = ('test_indicator_id', 'test_indicator_id')


class TestMethodRawFilter(django_filters.rest_framework.FilterSet):
    test_indicator_id = django_filters.NumberFilter(field_name='test_type__test_indicator_id', help_text='试验指标id')

    class Meta:
        model = TestMethodRaw
        fields = ('test_indicator_id', 'test_type_id')


class MaterialTestMethodRawFilter(django_filters.rest_framework.FilterSet):
    material_no = django_filters.CharFilter(field_name="material__material_no", lookup_expr='icontains',
                                            help_text='胶料编码')
    test_type_id = django_filters.NumberFilter(field_name='test_method__test_type_id',
                                               help_text='试验类型id')
    test_indicator_id = django_filters.NumberFilter(field_name='test_method__test_type__test_indicator_id',
                                                    help_text='试验指标id')

    class Meta:
        model = MaterialTestMethodRaw
        fields = ('material_no', 'test_indicator_id', 'test_type_id')


class MaterialDataPointIndicatorRawFilter(django_filters.rest_framework.FilterSet):
    material_test_method_id = django_filters.CharFilter(field_name='material_test_method_id',
                                                        help_text='物料试验方法id')

    class Meta:
        model = MaterialDataPointIndicatorRaw
        fields = ('material_test_method_id',)


class MaterialTestOrderRawFilter(django_filters.rest_framework.FilterSet):
    lot_no = django_filters.CharFilter(field_name='lot_no', lookup_expr='icontains', help_text='批次号')
    material_no = django_filters.CharFilter(field_name='material__material_no',
                                            lookup_expr='icontains', help_text='物料编号')
    material_name = django_filters.CharFilter(field_name='material__material_name',
                                              lookup_expr='icontains', help_text='物料名称')

    class Meta:
        model = MaterialTestOrderRaw
        fields = ('storage_date', 'is_qualified', 'lot_no', 'storage_date')


class UnqualifiedMaterialDealResultFilter(django_filters.rest_framework.FilterSet):
    storage_date = django_filters.DateFilter(field_name='material_test_order_raw__storage_date')
    lot_no = django_filters.CharFilter(field_name='material_test_order_raw__lot_no', lookup_expr='icontains',
                                       help_text='批次号')
    material_no = django_filters.CharFilter(field_name='material_test_order_raw__material__material_no',
                                            lookup_expr='icontains', help_text='物料编号')
    material_name = django_filters.CharFilter(field_name='material_test_order_raw__material__material_name',
                                              lookup_expr='icontains', help_text='物料名称')

    class Meta:
        model = UnqualifiedMaterialDealResult
        fields = ('storage_date', 'lot_no', 'material_no', 'material_name')

"""新原材料快检"""
class MaterialExamineEquipmentFilter(django_filters.rest_framework.FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    type_name = django_filters.CharFilter(field_name='type__name')

    class Meta:
        model = MaterialExamineEquipment
        fields = ('name', 'type_name')


class MaterialExamineTypeFilter(django_filters.rest_framework.FilterSet):
    compare = django_filters.ChoiceFilter(field_name='interval_type', choices=MaterialExamineType.INTERVAL_TYPES)
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = MaterialExamineType
        fields = ('compare', 'name')


class ExamineMaterialFilter(django_filters.rest_framework.FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    sample_name = django_filters.CharFilter(field_name='sample_name', lookup_expr='icontains')
    batch = django_filters.CharFilter(field_name='batch', lookup_expr='icontains')
    supplier = django_filters.CharFilter(field_name='supplier__name', lookup_expr='icontains')
    material_create_time_b = django_filters.DateTimeFilter(field_name='create_time', lookup_expr='gte')
    material_create_time_e = django_filters.DateTimeFilter(field_name='create_time', lookup_expr='lte')
    examine_date = django_filters.DateFilter(field_name='examine_results__examine_date')
    transport_date = django_filters.DateFilter(field_name='examine_results__transport_date')

    class Meta:
        model = ExamineMaterial
        fields = ('name', 'sample_name', 'batch',
                  'supplier',
                  'qualified',
                  'material_create_time_b',
                  'material_create_time_e',
                  'examine_date')