import django_filters

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

