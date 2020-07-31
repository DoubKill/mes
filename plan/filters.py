import django_filters
from plan.models import ProductDayPlan, MaterialDemanded, ProductBatchingDayPlan, MaterialRequisition


class ProductDayPlanFilter(django_filters.rest_framework.FilterSet):
    """胶料日计划过滤器"""
    plan_data = django_filters.DateTimeFilter(field_name='plan_schedule__day_time', help_text='日期')
    sort = django_filters.CharFilter(field_name='equip__category')

    class Meta:
        model = ProductDayPlan
        fields = ('plan_data', 'sort')


class MaterialDemandedFilter(django_filters.rest_framework.FilterSet):
    """原材料需求量过滤器"""
    schedule_no = django_filters.BaseInFilter(field_name='material__material_no')
    sort = django_filters.CharFilter(field_name='material__material_name')

    class Meta:
        model = MaterialDemanded
        fields = ('schedule_no', 'sort')


class ProductBatchingDayPlanFilter(django_filters.rest_framework.FilterSet):
    """配料小料日计划过滤器"""
    plan_data = django_filters.DateTimeFilter(field_name='plan_schedule__day_time', help_text='日期')
    sort = django_filters.CharFilter(field_name='equip__category')

    class Meta:
        model = ProductBatchingDayPlan
        fields = ('plan_data', 'sort')


class MaterialRequisitionFilter(django_filters.rest_framework.FilterSet):
    """领料日计划过滤器"""
    material_id = django_filters.DateTimeFilter(field_name='id', help_text='日期')

    class Meta:
        model = MaterialRequisition
        fields = ('material_id',)
