import django_filters
from quality.models import MaterialTestOrder, MaterialDataPointIndicator, \
    MaterialTestMethod, \
    TestMethod, DataPoint


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
    day_time = django_filters.DateTimeFilter(field_name="production_factory_date__date", help_text='生产时间', lookup_expr="lte")
    equip_no = django_filters.CharFilter(field_name='production_equip_no', help_text='机号')
    product_no = django_filters.CharFilter(field_name='product_no', lookup_expr='icontains', help_text='产出胶料编号')
    classes = django_filters.CharFilter(field_name="production_class", help_text='班次')

    class Meta:
        model = MaterialTestOrder
        fields = ('day_time', 'equip_no', 'product_no', "classes")


class MaterialDataPointIndicatorFilter(django_filters.rest_framework.FilterSet):
    material_test_method_id = django_filters.CharFilter(field_name='material_test_method_id',
                                                        help_text='物料试验方法id')

    class Meta:
        model = MaterialDataPointIndicator
        fields = ('material_test_method_id', )


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