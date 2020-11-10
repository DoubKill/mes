import django_filters
<<<<<<< HEAD
from .models import InventoryLog
=======

from inventory.models import DeliveryPlan


class PutPlanManagementFilter(django_filters.rest_framework.FilterSet):
    """出库计划过滤器"""
    st = django_filters.DateTimeFilter(field_name="created_date", help_text='创建时间', lookup_expr="gte")
    et = django_filters.DateTimeFilter(field_name="created_date", help_text='创建时间', lookup_expr="lte")
    status = django_filters.CharFilter(field_name="status",help_text ='订单状态')
    material_no = django_filters.CharFilter(field_name="material_no",help_text ='物料编码')
    name = django_filters.CharFilter(field_name="warehouse_info__name",help_text='仓库名称')


    class Meta:
        model = DeliveryPlan
        fields = ('st', 'et', 'status','material_no','name')
from . import models
>>>>>>> 9f8df301f4dfab6f4be1d95eb93977bd74bbeee0


class InventoryLogFilter(django_filters.rest_framework.FilterSet):
    start_time = django_filters.CharFilter(field_name='start_time', lookup_expr='gte')
    end_time = django_filters.CharFilter(field_name='start_time', lookup_expr='lte')
    type = django_filters.CharFilter(field_name='order_type')
    location = django_filters.CharFilter(field_name='location')
    material_no = django_filters.CharFilter(field_name='material_no', lookup_expr='icontains')

    class Meta:
        model = InventoryLog
        fields = ['start_time', 'end_time', 'type', 'location', 'material_no']
