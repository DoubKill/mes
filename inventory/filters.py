import django_filters
from .models import InventoryLog


class InventoryLogFilter(django_filters.rest_framework.FilterSet):
    start_time = django_filters.CharFilter(field_name='start_time', lookup_expr='gte')
    end_time = django_filters.CharFilter(field_name='start_time', lookup_expr='lte')
    type = django_filters.CharFilter(field_name='order_type')
    location = django_filters.CharFilter(field_name='location')
    material_no = django_filters.CharFilter(field_name='material_no', lookup_expr='icontains')

    class Meta:
        model = InventoryLog
        fields = ['start_time', 'end_time', 'type', 'location', 'material_no']
