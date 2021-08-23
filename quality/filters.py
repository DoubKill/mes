import django_filters

from quality.models import MaterialTestOrder, MaterialDataPointIndicator, \
    MaterialTestMethod, TestMethod, DataPoint, DealSuggestion, MaterialDealResult, UnqualifiedProductDealOrder, \
    ExamineMaterial, MaterialExamineType, MaterialExamineResult, MaterialEquip, MaterialReportEquip, \
    MaterialReportValue, ProductReportEquip, ProductReportValue, ProductTestPlanDetail


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
    lot_no = django_filters.CharFilter(field_name='lot_no', help_text='唯一追踪条码', lookup_expr="icontains")

    class Meta:
        model = MaterialDealResult
        fields = ('suggestion_desc', 'lot_no')


class UnqualifiedDealOrderFilter(django_filters.rest_framework.FilterSet):
    st = django_filters.DateFilter(field_name='created_date__date', lookup_expr='gte', help_text='开始时间')
    et = django_filters.DateFilter(field_name='created_date__date', lookup_expr='lte', help_text='结束时间')
    department = django_filters.CharFilter(field_name='department', lookup_expr='icontains', help_text='发生部门')
    status = django_filters.CharFilter(field_name='status', lookup_expr='icontains', help_text='不合格状态')
    unqualified_deal_order_uid = django_filters.CharFilter(field_name='unqualified_deal_order_uid',
                                                           lookup_expr='icontains', help_text='处置单号')

    class Meta:
        model = UnqualifiedProductDealOrder
        fields = ('st', 'et', 'department', 'status', 'unqualified_deal_order_uid')


"""新原材料快检"""


class MaterialEquipFilter(django_filters.rest_framework.FilterSet):
    equip_name = django_filters.CharFilter(field_name='equip_name', lookup_expr='icontains')
    equip_type_name = django_filters.CharFilter(field_name='equip_type__type_name', lookup_expr='icontains')

    class Meta:
        model = MaterialEquip
        fields = ('equip_name', 'equip_type_name')


class MaterialExamineTypeFilter(django_filters.rest_framework.FilterSet):
    compare = django_filters.ChoiceFilter(field_name='interval_type', choices=MaterialExamineType.INTERVAL_TYPES)
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = MaterialExamineType
        fields = ('compare', 'name')


class MaterialExamineResultFilter(django_filters.rest_framework.FilterSet):
    material_name = django_filters.CharFilter(field_name='material__name',
                                              help_text='原材料名称', lookup_expr='icontains')
    sample_name = django_filters.CharFilter(field_name='material__sample_name',
                                            help_text='样品名称', lookup_expr='icontains')
    batch = django_filters.CharFilter(field_name='material__batch',
                                      help_text='批次号', lookup_expr='icontains')
    supplier_name = django_filters.CharFilter(field_name='material__supplier',
                                              help_text='产地', lookup_expr='icontains')
    recorder_username = django_filters.CharFilter(field_name='recorder__username',
                                                  help_text='记录人', lookup_expr='icontains')
    sampling_username = django_filters.CharFilter(field_name='sampling_user__username',
                                                  help_text='抽样人', lookup_expr='icontains')

    class Meta:
        model = MaterialExamineResult
        fields = ('examine_date', 'transport_date', 're_examine', 'qualified',
                  'material_name', 'sample_name', 'batch', 'supplier_name',
                  'recorder_username', 'sampling_username')


class ExamineMaterialFilter(django_filters.rest_framework.FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains', help_text='原材料名称')
    sample_name = django_filters.CharFilter(field_name='sample_name', lookup_expr='icontains', help_text='样品名称')
    batch = django_filters.CharFilter(field_name='batch', lookup_expr='icontains', help_text='批次号')
    supplier = django_filters.CharFilter(field_name='supplier', lookup_expr='icontains', help_text='供应商')
    material_create_time_b = django_filters.DateTimeFilter(field_name='create_time', lookup_expr='gte')
    material_create_time_e = django_filters.DateTimeFilter(field_name='create_time', lookup_expr='lte')

    # examine_date = django_filters.DateFilter(field_name='examine_results__examine_date', help_text='检测日期')
    # transport_date = django_filters.DateFilter(field_name='examine_results__transport_date', help_text='收货日期')

    class Meta:
        model = ExamineMaterial
        fields = ('name',
                  'sample_name',
                  'batch',
                  'supplier',
                  'qualified',
                  'material_create_time_b',
                  'material_create_time_e')


class MaterialReportEquipFilter(django_filters.rest_framework.FilterSet):
    no = django_filters.CharFilter(field_name='no', lookup_expr='icontains')
    type = django_filters.CharFilter(field_name='type__id', lookup_expr='icontains')

    class Meta:
        model = MaterialReportEquip
        fields = ('no', 'type')


class MaterialReportValueFilter(django_filters.rest_framework.FilterSet):
    created_date = django_filters.DateTimeFilter(field_name='created_date__date', help_text='数据上报日期')

    class Meta:
        model = MaterialReportValue
        fields = ('created_date',)


class ProductReportEquipFilter(django_filters.rest_framework.FilterSet):
    no = django_filters.CharFilter(field_name='no', lookup_expr='icontains', help_text='设备编号')

    class Meta:
        model = ProductReportEquip
        fields = ('no',)


class ProductReportValueFilter(django_filters.rest_framework.FilterSet):
    created_date = django_filters.CharFilter(field_name='created_date__date', help_text='上报日期')

    class Meta:
        model = ProductReportValue
        fields = ('created_date',)


class ProductTestResumeFilter(django_filters.rest_framework.FilterSet):
    test_indicator_name = django_filters.CharFilter(field_name='test_plan__test_indicator_name', help_text='实验分区')
    test_time = django_filters.CharFilter(field_name='test_plan__test_time', lookup_expr='icontains', help_text='检测时间')
    test_classes = django_filters.CharFilter(field_name='test_plan__test_classes', help_text='检测班次')
    test_equip = django_filters.CharFilter(field_name='test_plan__test_equip__no', help_text='检测机台')
    plan_uid = django_filters.CharFilter(field_name='test_plan__plan_uid', lookup_expr='icontains', help_text='检测计划编码')
    status = django_filters.CharFilter(field_name='test_plan__status', help_text='检测状态')

    class Meta:
        model = ProductTestPlanDetail
        fields = '__all__'