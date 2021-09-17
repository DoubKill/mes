import django_filters
from django_filters.rest_framework import DjangoFilterBackend

from production.models import PalletFeedbacks
from .models import InventoryLog, Station, DeliveryPlanLB, DispatchPlan, DispatchLog, DispatchLocation, \
    MixGumOutInventoryLog, MixGumInInventoryLog, DeliveryPlanFinal, MaterialOutPlan, BarcodeQuality, CarbonOutPlan, \
    MixinRubberyOutBoundOrder, FinalRubberyOutBoundOrder, DepotSite, SulfurDepotSite, DepotPallt, Sulfur, \
    OutBoundDeliveryOrder, OutBoundDeliveryOrderDetail

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
        fields = ('st', 'et', 'status', 'material_no', 'name', 'station', 'outbound_order')


class PutPlanManagementLBFilter(django_filters.rest_framework.FilterSet):
    """帘布库出库计划过滤器"""
    st = django_filters.DateTimeFilter(field_name="created_date", help_text='创建时间', lookup_expr="gte")
    et = django_filters.DateTimeFilter(field_name="created_date", help_text='创建时间', lookup_expr="lte")
    status = django_filters.CharFilter(field_name="status", help_text='订单状态')
    material_no = django_filters.CharFilter(field_name="material_no", help_text='物料编码', lookup_expr='icontains')
    name = django_filters.CharFilter(field_name="warehouse_info__name", help_text='仓库名称')
    station = django_filters.CharFilter(field_name="station", help_text='仓库名称', lookup_expr='icontains')

    class Meta:
        model = DeliveryPlanLB
        fields = ('st', 'et', 'status', 'material_no', 'name', 'station')


class PutPlanManagementFinalFilter(django_filters.rest_framework.FilterSet):
    """帘布库出库计划过滤器"""
    st = django_filters.DateTimeFilter(field_name="created_date", help_text='创建时间', lookup_expr="gte")
    et = django_filters.DateTimeFilter(field_name="created_date", help_text='创建时间', lookup_expr="lte")
    status = django_filters.CharFilter(field_name="status", help_text='订单状态')
    material_no = django_filters.CharFilter(field_name="material_no", help_text='物料编码', lookup_expr='icontains')
    name = django_filters.CharFilter(field_name="warehouse_info__name", help_text='仓库名称')
    station = django_filters.CharFilter(field_name="station", help_text='仓库名称', lookup_expr='icontains')

    class Meta:
        model = DeliveryPlanFinal
        fields = ('st', 'et', 'status', 'material_no', 'name', 'station', 'outbound_order')


class MaterialPlanManagementFilter(django_filters.rest_framework.FilterSet):
    """帘布库出库计划过滤器"""
    st = django_filters.DateTimeFilter(field_name="created_date", help_text='创建时间', lookup_expr="gte")
    et = django_filters.DateTimeFilter(field_name="created_date", help_text='创建时间', lookup_expr="lte")
    status = django_filters.CharFilter(field_name="status", help_text='订单状态')
    material_no = django_filters.CharFilter(field_name="material_no", help_text='物料编码', lookup_expr='icontains')
    name = django_filters.CharFilter(field_name="warehouse_info__name", help_text='仓库名称')
    station = django_filters.CharFilter(field_name="station", help_text='出库口')
    station_no = django_filters.CharFilter(field_name="station_no", help_text='出库口')

    class Meta:
        model = MaterialOutPlan
        fields = ('st', 'et', 'status', 'material_no', 'name')


class CarbonPlanManagementFilter(django_filters.rest_framework.FilterSet):
    """帘布库出库计划过滤器"""
    st = django_filters.DateTimeFilter(field_name="created_date", help_text='创建时间', lookup_expr="gte")
    et = django_filters.DateTimeFilter(field_name="created_date", help_text='创建时间', lookup_expr="lte")
    status = django_filters.CharFilter(field_name="status", help_text='订单状态')
    material_no = django_filters.CharFilter(field_name="material_no", help_text='物料编码', lookup_expr='icontains')
    name = django_filters.CharFilter(field_name="warehouse_info__name", help_text='仓库名称')
    station = django_filters.CharFilter(field_name="station", help_text='出库口')
    station_no = django_filters.CharFilter(field_name="station_no", help_text='出库口')

    class Meta:
        model = CarbonOutPlan
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


class BarcodeQualityFilter(django_filters.rest_framework.FilterSet):
    material_type = django_filters.CharFilter(field_name='material_type')
    material_no = django_filters.CharFilter(field_name='material_no', lookup_expr='icontains')
    material_name = django_filters.CharFilter(field_name='material_name', lookup_expr='icontains')
    barcode = django_filters.CharFilter(field_name='barcode', lookup_expr='icontains')

    class Meta:
        model = BarcodeQuality
        fields = ['material_type', 'material_no', 'material_name', 'barcode']


class PalletDataFilter(django_filters.rest_framework.FilterSet):
    """库存数据过滤器"""
    equip_no = django_filters.CharFilter(field_name='equip_no', help_text='机号', lookup_expr='icontains')
    product_no = django_filters.CharFilter(field_name='product_no', help_text='产出胶料编号', lookup_expr='icontains')
    classes = django_filters.CharFilter(field_name="classes", help_text='班次', lookup_expr='icontains')
    factory_date = django_filters.DateTimeFilter(field_name="factory_date", help_text="工厂日期", lookup_expr='icontains')

    class Meta:
        model = PalletFeedbacks
        fields = ('equip_no', 'product_no', "classes", "factory_date")


class DepotSiteDataFilter(django_filters.rest_framework.FilterSet):
    """线边库库位过滤器"""
    id = django_filters.CharFilter(field_name='depot__id')

    class Meta:
        model = DepotSite
        fields = ('id',)


class SulfurDepotSiteFilter(django_filters.rest_framework.FilterSet):
    """硫磺库库位过滤器"""
    id = django_filters.CharFilter(field_name='depot__id')

    class Meta:
        model = SulfurDepotSite
        fields = ('id',)


class DepotDataFilter(django_filters.rest_framework.FilterSet):
    """线边库出入库数据过滤器"""
    product_no = django_filters.CharFilter(field_name='pallet_data__product_no', help_text='胶料编码', lookup_expr='icontains')
    depot = django_filters.CharFilter(field_name='depot_site__depot__id', help_text='库区')
    depot_site = django_filters.CharFilter(field_name='depot_site__id', help_text='库位')

    class Meta:
        model = DepotPallt
        fields = ('product_no', 'depot', 'depot_site')


class DepotResumeFilter(django_filters.rest_framework.FilterSet):
    """线边库出入库履历过滤器"""
    product_no = django_filters.CharFilter(field_name='pallet_data__product_no', help_text='产出胶料编号', lookup_expr='icontains')
    equip_no = django_filters.CharFilter(field_name='pallet_data__equip_no', help_text='机号', lookup_expr='icontains')
    classes = django_filters.CharFilter(field_name="pallet_data__classes", help_text='班次', lookup_expr='icontains')
    factory_date = django_filters.DateTimeFilter(field_name="pallet_data__factory_date", help_text="工厂日期", lookup_expr='icontains')

    class Meta:
        model = DepotPallt
        fields = ('product_no', 'equip_no', "classes", "factory_date")


class SulfurDataFilter(django_filters.rest_framework.FilterSet):
    """硫磺库出入库过滤器"""
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    product_no = django_filters.CharFilter(field_name='product_no', lookup_expr='icontains')
    provider = django_filters.CharFilter(field_name='provider', lookup_expr='icontains')
    lot_no = django_filters.CharFilter(field_name='lot_no', lookup_expr='icontains')
    depot_name = django_filters.CharFilter(field_name='depot_site__depot__depot_name', help_text='库区')
    depot_site_name =django_filters.CharFilter(field_name='depot_site__depot_site_name', help_text='库位')
    s_time = django_filters.DateTimeFilter(field_name='enter_time', lookup_expr='gte')
    e_time = django_filters.DateTimeFilter(field_name='enter_time', lookup_expr='lte')

    class Meta:
        model = Sulfur
        fields = ['name', 'product_no', 'provider', 'lot_no', 'depot_name', 'depot_site_name', 's_time', 'e_time']


class DepotSulfurFilter(django_filters.rest_framework.FilterSet):
    """硫磺库库存查询过滤器"""
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    product_no = django_filters.CharFilter(field_name='product_no', lookup_expr='icontains')
    provider = django_filters.CharFilter(field_name='provider', lookup_expr='icontains')
    lot_no = django_filters.CharFilter(field_name='lot_no', lookup_expr='icontains')

    class Meta:
        model = Sulfur
        fields = ['name', 'product_no', 'provider', 'lot_no']


class SulfurResumeFilter(django_filters.rest_framework.FilterSet):
    """硫磺库出入库履历过滤器"""
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    product_no = django_filters.CharFilter(field_name='product_no', lookup_expr='icontains')
    provider = django_filters.CharFilter(field_name='provider', lookup_expr='icontains')
    lot_no = django_filters.CharFilter(field_name='lot_no', lookup_expr='icontains')

    depot_name = django_filters.CharFilter(field_name='depot_site__depot__depot_name', help_text='库区')
    depot_site_name =django_filters.CharFilter(field_name='depot_site__depot_site_name', help_text='库位')
    s_etime = django_filters.DateTimeFilter(field_name='enter_time', lookup_expr='gte')
    e_etime = django_filters.DateTimeFilter(field_name='enter_time', lookup_expr='lte')
    s_otime = django_filters.DateTimeFilter(field_name='outer_time', lookup_expr='gte')
    e_otime = django_filters.DateTimeFilter(field_name='outer_time', lookup_expr='lte')

    class Meta:
        model = Sulfur
        fields = ['name', 'product_no', 'provider', 'lot_no', 'sulfur_status', 'enter_time', 'outer_time',
                 'depot_name', 'depot_site_name']


class MixinRubberyOutBoundOrderFilter(django_filters.rest_framework.FilterSet):
    order_no = django_filters.CharFilter(field_name='order_no', lookup_expr='icontains')

    class Meta:
        model = MixinRubberyOutBoundOrder
        fields = ['order_no', 'status']


class FinalRubberyOutBoundOrderFilter(django_filters.rest_framework.FilterSet):
    order_no = django_filters.CharFilter(field_name='order_no', lookup_expr='icontains')

    class Meta:
        model = FinalRubberyOutBoundOrder
        fields = ['order_no', 'status']


class OutBoundDeliveryOrderFilter(django_filters.rest_framework.FilterSet):
    order_no = django_filters.CharFilter(field_name='order_no', lookup_expr='icontains', help_text='订单编号')
    product_no = django_filters.CharFilter(field_name='product_no', lookup_expr='icontains', help_text='胶料名称')
    warehouse = django_filters.CharFilter(field_name='warehouse', help_text='库区')
    station = django_filters.CharFilter(field_name='station', help_text='出库口')
    st = django_filters.DateFilter(field_name='created_date__date', lookup_expr='gte', help_text='开始时间')
    et = django_filters.DateFilter(field_name='created_date__date', lookup_expr='lte', help_text='结束时间')

    class Meta:
        model = OutBoundDeliveryOrder
        fields = ['order_no', 'product_no', 'warehouse', 'station', 'st', 'et', 'status']


class OutBoundDeliveryOrderDetailFilter(django_filters.rest_framework.FilterSet):
    order_no = django_filters.CharFilter(field_name='order_no', lookup_expr='icontains', help_text='出库任务号')
    sub_no = django_filters.CharFilter(field_name='sub_no', lookup_expr='icontains', help_text='订单子编号')
    pallet_no = django_filters.CharFilter(field_name='pallet_no', lookup_expr='icontains', help_text='托盘号')
    lot_no = django_filters.CharFilter(field_name='lot_no', lookup_expr='icontains', help_text='收皮条码')

    class Meta:
        model = OutBoundDeliveryOrderDetail
        fields = ['outbound_delivery_order_id', 'order_no', 'pallet_no', 'lot_no']
