import django_filters
from django_filters.rest_framework import DjangoFilterBackend

from .models import InventoryLog, Station, DeliveryPlanLB, DispatchPlan, DispatchLog, DispatchLocation, \
    MixGumOutInventoryLog, MixGumInInventoryLog, DeliveryPlanFinal, MaterialOutPlan

from inventory.models import DeliveryPlan


class PutPlanManagementFilter(django_filters.rest_framework.FilterSet):
    """出库计划过滤器"""
    st = django_filters.DateTimeFilter(field_name="created_date", help_text='创建时间', lookup_expr="gte")
    et = django_filters.DateTimeFilter(field_name="created_date", help_text='创建时间', lookup_expr="lte")
    status = django_filters.CharFilter(field_name="status", help_text='订单状态')
    material_no = django_filters.CharFilter(field_name="material_no", help_text='物料编码', lookup_expr='icontains')
    name = django_filters.CharFilter(field_name="warehouse_info__name", help_text='仓库名称')
    station = django_filters.CharFilter(field_name="station", help_text='仓库名称', lookup_expr='icontains')

    class Meta:
        model = DeliveryPlan
        fields = ('st', 'et', 'status', 'material_no', 'name', 'station')


class PutPlanManagementLBFilter(django_filters.rest_framework.FilterSet):
    """帘布库出库计划过滤器"""
    st = django_filters.DateTimeFilter(field_name="created_date", help_text='创建时间', lookup_expr="gte")
    et = django_filters.DateTimeFilter(field_name="created_date", help_text='创建时间', lookup_expr="lte")
    status = django_filters.CharFilter(field_name="status", help_text='订单状态')
    material_no = django_filters.CharFilter(field_name="material_no", help_text='物料编码', lookup_expr='icontains')
    name = django_filters.CharFilter(field_name="warehouse_info__name", help_text='仓库名称')

    class Meta:
        model = DeliveryPlanLB
        fields = ('st', 'et', 'status', 'material_no', 'name')


class PutPlanManagementFinalFilter(django_filters.rest_framework.FilterSet):
    """帘布库出库计划过滤器"""
    st = django_filters.DateTimeFilter(field_name="created_date", help_text='创建时间', lookup_expr="gte")
    et = django_filters.DateTimeFilter(field_name="created_date", help_text='创建时间', lookup_expr="lte")
    status = django_filters.CharFilter(field_name="status", help_text='订单状态')
    material_no = django_filters.CharFilter(field_name="material_no", help_text='物料编码', lookup_expr='icontains')
    name = django_filters.CharFilter(field_name="warehouse_info__name", help_text='仓库名称')

    class Meta:
        model = DeliveryPlanFinal
        fields = ('st', 'et', 'status', 'material_no', 'name')


class MaterialPlanManagementFilter(django_filters.rest_framework.FilterSet):
    """帘布库出库计划过滤器"""
    st = django_filters.DateTimeFilter(field_name="created_date", help_text='创建时间', lookup_expr="gte")
    et = django_filters.DateTimeFilter(field_name="created_date", help_text='创建时间', lookup_expr="lte")
    status = django_filters.CharFilter(field_name="status", help_text='订单状态')
    material_no = django_filters.CharFilter(field_name="material_no", help_text='物料编码', lookup_expr='icontains')
    name = django_filters.CharFilter(field_name="warehouse_info__name", help_text='仓库名称')

    class Meta:
        model = MaterialOutPlan
        fields = ('st', 'et', 'status', 'material_no', 'name')



class InventoryLogFilter(django_filters.rest_framework.FilterSet):
    start_time = django_filters.CharFilter(field_name='start_time', lookup_expr='gte')
    end_time = django_filters.CharFilter(field_name='start_time', lookup_expr='lte')
    type = django_filters.CharFilter(field_name='order_type')
    location = django_filters.CharFilter(field_name='location')
    material_no = django_filters.CharFilter(field_name='material_no', lookup_expr='icontains')

    class Meta:
        model = InventoryLog
        fields = ['start_time', 'end_time', 'type', 'location', 'material_no']


class StationFilter(django_filters.rest_framework.FilterSet):
    warehouse_info = django_filters.CharFilter(field_name='warehouse_info')
    warehouse_name = django_filters.CharFilter(field_name='warehouse_info__name')

    class Meta:
        model = Station
        fields = ['warehouse_info', 'warehouse_name']


class DispatchPlanFilter(django_filters.rest_framework.FilterSet):
    """发货计划管理筛选"""
    start_time = django_filters.DateFilter(field_name='start_time__date', help_text='时间')
    status = django_filters.CharFilter(field_name='status', help_text='订单状态')
    material = django_filters.CharFilter(field_name='material__id', help_text='物料编码id')
    dispatch_type = django_filters.CharFilter(field_name='dispatch_type__id', help_text='发货类型')
    dispatch_location = django_filters.CharFilter(field_name='dispatch_location__id', help_text='目的地')
    material_no = django_filters.CharFilter(field_name='material__material_no', help_text='物料编码')

    class Meta:
        model = DispatchPlan
        fields = ['start_time', 'status', 'material', 'dispatch_type', 'dispatch_location', 'material_no']


class DispatchLogFilter(django_filters.rest_framework.FilterSet):
    """发货履历"""
    lot_no = django_filters.CharFilter(field_name='lot_no')
    order_no = django_filters.CharFilter(field_name='order_no', help_text='订单号')

    class Meta:
        model = DispatchLog
        fields = ['lot_no', 'order_no']


class DispatchLocationFilter(django_filters.rest_framework.FilterSet):
    '''目的地'''
    use_flag = django_filters.BooleanFilter(field_name='use_flag', help_text='是否启用')

    class Meta:
        model = DispatchLocation
        fields = ['use_flag']


class MixGumFilter(django_filters.rest_framework.FilterSet):
    start_time = django_filters.CharFilter(field_name='fin_time', lookup_expr='gte')
    end_time = django_filters.CharFilter(field_name='fin_time', lookup_expr='lte')
    location = django_filters.CharFilter(field_name='location', lookup_expr='icontains')
    material_no = django_filters.CharFilter(field_name='material_no', lookup_expr='icontains')

    class Meta:
        fields = ['start_time', 'end_time', 'location', 'material_no']


class MixGumInFilter(MixGumFilter):

    class Meta:
        model = MixGumInInventoryLog
        fields = ['start_time', 'end_time', 'location', 'material_no']


class MixGumOutFilter(MixGumFilter):

    class Meta:
        model = MixGumOutInventoryLog
        fields = ['start_time', 'end_time', 'location', 'material_no']


class InventoryFilterBackend(DjangoFilterBackend):

    def get_filterset(self, request, queryset, view):
        params = request.query_params
        store_name = params.get("store_name", "混炼胶库")
        order_type = params.get("order_type", "出库")
        # TODO 待其他库存对接上了之后需补充
        if store_name == "混炼胶库":
            if order_type == "出库":
                temp_filter = MixGumOutFilter
            else:
                temp_filter = MixGumInFilter
        else:
            temp_filter = InventoryLogFilter
        setattr(view, 'filter_class', temp_filter)
        filterset_class = self.get_filterset_class(view, queryset)
        if filterset_class is None:
            return None

        kwargs = self.get_filterset_kwargs(request, queryset, view)
        return filterset_class(**kwargs)
