import django_filters
from plan.models import ProductDayPlan, MaterialDemanded, ProductBatchingDayPlan, MaterialRequisition


class ProductDayPlanFilter(django_filters.rest_framework.FilterSet):
    """胶料日计划过滤器"""
    plan_data = django_filters.DateTimeFilter(field_name='plan_schedule__day_time', help_text='日期')

    class Meta:
        model = ProductDayPlan
        fields = ('plan_data',)


class MaterialDemandedFilter(django_filters.rest_framework.FilterSet):
    """原材料需求量过滤器"""
    schedule_no = django_filters.NumberFilter(field_name='product_day_plan__plan_schedule__work_schedule__schedule_no')

    class Meta:
        model = MaterialDemanded
        fields = ('schedule_no',)


class ProductBatchingDayPlanFilter(django_filters.rest_framework.FilterSet):
    """配料小料日计划过滤器"""
    plan_data = django_filters.DateTimeFilter(field_name='plan_schedule__day_time', help_text='日期')

    class Meta:
        model = ProductBatchingDayPlan
        fields = ('plan_data',)


class MaterialRequisitionFilter(django_filters.rest_framework.FilterSet):
    """领料日计划过滤器"""
    material_id = django_filters.NumberFilter(field_name='id')

    class Meta:
        model = MaterialRequisition
        fields = ('material_id',)
