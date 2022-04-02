import django_filters

from inventory.models import ProductStockDailySummary
from plan.models import ProductDayPlan, MaterialDemanded, ProductClassesPlan, \
    BatchingClassesPlan, SchedulingRecipeMachineSetting, SchedulingProductDemandedDeclareSummary, \
    SchedulingProductSafetyParams, SchedulingResult, SchedulingProductDemandedDeclare


class ProductDayPlanFilter(django_filters.rest_framework.FilterSet):
    """胶料日计划过滤器"""
    plan_date = django_filters.DateTimeFilter(field_name='plan_schedule__day_time', help_text='日期')
    equip_no = django_filters.CharFilter(field_name='equip__equip_no', help_text='机台')
    product_no = django_filters.CharFilter(field_name='product_batching__stage_product_batch_no', help_text='胶料编码')

    class Meta:
        model = ProductDayPlan
        fields = ('plan_date', 'equip_no', 'product_no')


class MaterialDemandedFilter(django_filters.rest_framework.FilterSet):
    """原材料需求量过滤器"""
    plan_date = django_filters.DateTimeFilter(field_name='work_schedule_plan__plan_schedule__day_time', help_text='日期')
    material_type = django_filters.CharFilter(field_name='material__material_type__global_name', help_text='原材料类别')
    material_name = django_filters.CharFilter(field_name='material__material_name', help_text='原材料名称',
                                              lookup_expr='icontains')
    classes = django_filters.CharFilter(field_name='work_schedule_plan__classes__global_name', help_text='班次')

    product_no = django_filters.CharFilter(
        field_name='product_classes_plan__product_day_plan__product_batching__stage_product_batch_no',
        lookup_expr='icontains', help_text='胶料编码')

    class Meta:
        model = MaterialDemanded
        fields = ('plan_date', 'material_type', 'material_name', 'classes')


class ProductClassesPlanFilter(django_filters.rest_framework.FilterSet):
    """计划管理"""
    classes = django_filters.CharFilter(field_name='work_schedule_plan__classes__global_name', help_text='班次')
    product_no = django_filters.CharFilter(field_name='product_batching__stage_product_batch_no',
                                           help_text='胶料编码')
    begin_time = django_filters.DateTimeFilter(field_name='work_schedule_plan__start_time', lookup_expr="gte",
                                               help_text='开始时间')
    end_time = django_filters.DateTimeFilter(field_name='work_schedule_plan__start_time', lookup_expr="lte",
                                             help_text='结束时间')
    # equip_no = django_filters.CharFilter(field_name='product_day_plan__equip__equip_no', help_text='机台编号')
    equip_no = django_filters.CharFilter(field_name='equip__equip_no', help_text='机台编号')
    schedule_name = django_filters.CharFilter(
        field_name='work_schedule_plan__plan_schedule__id', help_text='排班规则')
    day_time = django_filters.DateFilter(field_name='work_schedule_plan__plan_schedule__day_time', help_text='当前日期')

    class Meta:
        model = ProductClassesPlan
        fields = ('classes', 'product_no', 'begin_time', 'end_time', 'equip_no', 'schedule_name', 'day_time')


class BatchingClassesPlanFilter(django_filters.rest_framework.FilterSet):
    day_time = django_filters.DateFilter(field_name='work_schedule_plan__plan_schedule__day_time')
    dev_type = django_filters.CharFilter(field_name='weigh_cnt_type__product_batching__dev_type')
    weight_batch_no = django_filters.CharFilter(field_name='weigh_cnt_type__name',
                                                lookup_expr='icontains')
    classes_name = django_filters.CharFilter(field_name='work_schedule_plan__classes__global_name')
    status = django_filters.CharFilter(field_name='status')

    class Meta:
        model = BatchingClassesPlan
        fields = ('day_time', 'dev_type', 'weight_batch_no', 'classes_name')


class SchedulingRecipeMachineSettingFilter(django_filters.rest_framework.FilterSet):
    """胶料日计划过滤器"""
    product_no = django_filters.CharFilter(field_name='product_no', help_text='胶料代码', lookup_expr='icontains')

    class Meta:
        model = SchedulingRecipeMachineSetting
        fields = ('product_no', 'rubber_type')


class SchedulingProductDemandedDeclareSummaryFilter(django_filters.rest_framework.FilterSet):
    """胶料日计划过滤器"""
    product_no = django_filters.CharFilter(field_name='product_no', help_text='胶料代码', lookup_expr='icontains')

    class Meta:
        model = SchedulingProductDemandedDeclareSummary
        fields = ('factory_date', 'product_no')


class SchedulingProductSafetyParamsFilter(django_filters.rest_framework.FilterSet):
    """胶料日计划过滤器"""
    product_no = django_filters.CharFilter(field_name='product_no', help_text='胶料代码', lookup_expr='icontains')

    class Meta:
        model = SchedulingProductSafetyParams
        fields = ('factory', 'product_no')


class SchedulingProductDemandedDeclareFilter(django_filters.rest_framework.FilterSet):
    st = django_filters.DateFilter(field_name='factory_date', lookup_expr='gte')
    et = django_filters.DateFilter(field_name='factory_date', lookup_expr='lte')
    order_no = django_filters.CharFilter(field_name='order_no', lookup_expr='icontains')

    class Meta:
        model = SchedulingProductDemandedDeclare
        fields = ('factory', 'st', 'et', 'product_no', 'status', 'order_no')


class ProductStockDailySummaryFilter(django_filters.rest_framework.FilterSet):

    class Meta:
        model = ProductStockDailySummary
        fields = ('factory_date', 'product_no')