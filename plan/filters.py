import django_filters
from plan.models import ProductDayPlan, MaterialDemanded, ProductBatchingDayPlan


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


class ProductBatchingDayPlanFilter(django_filters.rest_framework.FilterSet):
    """配料小料日计划过滤器"""
    plan_date = django_filters.DateTimeFilter(field_name='plan_schedule__day_time', help_text='日期')
    equip_no = django_filters.CharFilter(field_name='equip__equip_no', help_text='机台')
    product_no = django_filters.CharFilter(field_name='product_batching__stage_product_batch_no', help_text='胶料编码')

    class Meta:
        model = ProductBatchingDayPlan
        fields = ('plan_date', 'equip_no', 'product_no')


'''
class MaterialRequisitionFilter(django_filters.rest_framework.FilterSet):
    """领料日计划过滤器"""
    material_id = django_filters.NumberFilter(field_name='id')

    class Meta:
        model = MaterialRequisition
        fields = ('material_id',)
'''
