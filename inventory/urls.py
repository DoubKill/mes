# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/8/28
name: 
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .terminal_views import TerminalDispatchLogViewSet, TerminalDispatchViewSet
from .views import *

router = DefaultRouter()

# 原材料立库
router.register(r'material-inventory-view', views.MaterialInventoryView, basename="material-inventory")

# 胶料立库
router.register(r'product-inventory', views.ProductInventory, basename="product-inventory")

# 出库计划管理
router.register('put-plan-management', PutPlanManagement)

# 帘布库出库管理
router.register(r'lb-plan-management', views.PutPlanManagementLB)

# 终炼胶出库管理
router.register(r'final-plan-management', views.PutPlanManagementFianl)

# 原材料库出库管理
router.register(r'material-plan-management', views.MaterialPlanManagement)

# 炭黑库出库管理
router.register(r'carbon-plan-management', views.CarbonPlanManagement)

# 过期胶料管理
router.register('overdue-material-management', OverdueMaterialManagement)

# 物料库存信息|线边库|终炼胶库|原材料库
router.register(r'material-inventory-manage', views.MaterialInventoryManageViewSet,
                basename='material-inventory-manage'),

# 物料出入库履历
router.register(r'inventory-log', views.InventoryLogViewSet)

# 仓库信息
router.register(r'warehouse-info', views.WarehouseInfoViewSet)

# 站点信息
router.register(r'station-info', views.StationInfoViewSet)

# 仓库物料类型
router.register(r'warehouse-material-type', views.WarehouseMaterialTypeViewSet)

'''在后面加发货终端设计的url表示发货终端设计所需要的接口和mes页面所需要的接口耦合了，在此提示说明一下，防止重复开发'''
# 发货计划管理
router.register(r'dispatch-plan', views.DispatchPlanViewSet)  # 发货终端设计67

# 目的地
router.register(r'dispatch-location', views.DispatchLocationViewSet)

# 终端发货履历管理
router.register(r'terminal-dispatch-log', TerminalDispatchLogViewSet)

# 终端发货履历管理
router.register(r'terminal-dispatch-plan', TerminalDispatchViewSet)

# 出库看板
router.register(r'inventory-log-out', InventoryLogOutViewSet)

# 物料条码质量维护
router.register(r'barcode-quality', BarcodeQualityViewSet)

# 线边库库区
router.register(r'depot', DepotModelViewSet)

# 线边库库位
router.register(r'depot-site', DepotSiteModelViewSet)

# 线边库库存查询
router.register(r'depot-pallet', DepotPalltModelViewSet)
router.register(r'depot-pallet-info', DepotPalltInfoModelViewSet, basename='depot-pallet-info')

# 线边库出入库管理
router.register(r'pallet-data', PalletDataModelViewSet)

# 线边库出入库履历
router.register(r'depot-resume', DepotResumeModelViewSet, basename='depot-resume')

# 硫磺库库区
router.register(r'sulfur-depot', SulfurDepotModelViewSet)

# 硫磺库库位
router.register(r'sulfur-depot-site', SulfurDepotSiteModelViewSet)

# 硫磺出入库管理
router.register(r'sulfur-data', SulfurDataModelViewSet, basename='sulfur-data')

# 硫磺库库存查询
router.register(r'depot-sulfur', DepotSulfurModelViewSet, basename='depot-sulfur')
router.register(r'depot-sulfur-info', DepotSulfurInfoModelViewSet, basename='depot-sulfur-info')

# 硫磺库出入库履历
router.register(r'sulfur-resume', SulfurResumeModelViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('material-trace/', MaterialTraceView.as_view()),  # 原材料条码追溯
    path('product-trace/', ProductTraceView.as_view()),    # 胶料条码追溯
    path('material_count/', MaterialCount.as_view()),
    path('outwork_feedback/', OutWorkFeedBack.as_view()),  # 混炼终炼出库反馈接口
    path('material_out_back/', MaterialOutBack.as_view()),  # 原材料出库反馈
    path('dispatch-log/', DispatchLogView.as_view()),  # 发货历史记录
    path('material-inventory-list/', MaterialInventoryAPIView.as_view()),  # 库存信息
    path('materia_type_name_to_according/', MateriaTypeNameToAccording.as_view()),  # 根据物料类型和编码找到存在的仓库表
    path('sampling-rules/', SamplingRules.as_view()),

    # 原材料出库
    path('wms-stock/', WmsInventoryStockView.as_view()),  # 原材料货位列表
    path('wms-weight-stock/', WmsInventoryWeightStockView.as_view()),  # 原材料重量库存
    path('wms-entrance/', InventoryEntranceView.as_view()),  # 出库口列表
    path('wms-tunnels/', WMSTunnelView.as_view()),  # 巷道列表
    path('wms-material-groups/', WMSMaterialGroupNameView.as_view()),  # 物料组列表
    path('wms-inventory/', WMSInventoryView.as_view()),  # 库存统计列表

    # 炭黑出库
    path('th-stock/', THInventoryStockView.as_view()),  # 炭黑货位列表
    path('th-weight-stock/', THInventoryWeightStockView.as_view()),  # 炭黑重量库存
    path('th-entrance/', THInventoryEntranceView.as_view()),  # 炭黑出库口列表
    path('th-tunnels/', THTunnelView.as_view()),  # 巷道列表
    path('th-material-groups/', THMaterialGroupNameView.as_view()),  # 物料组列表
    path('th-inventory/', THInventoryView.as_view()),  # 库存统计列表

    # 出库大屏
    path('delivery-plan-now/', DeliveryPlanNow.as_view()),  # 混炼胶 当前在出库口的胶料信息
    path('delivery-plan-today/', DeliveryPlanToday.as_view()),  # 混炼胶 今日的总出库量
    path('mix-gum-out-list/', MixGumOutInventoryLogAPIView.as_view()),  # 混炼胶  倒叙显示最近几条出库信息

    path('delivery-plan-final-now/', DeliveryPlanFinalNow.as_view()),  # 终炼胶 当前在出库口的胶料信息
    path('delivery-plan-final-today/', DeliveryPlanFinalToday.as_view()),  # 终炼胶  今日的总出库量
    path('final-gum-out-list/', FinalGumOutInventoryLogAPIView.as_view()),  # 终炼胶  倒叙显示最近几条出库信息

    path('product-station-statics/', InventoryStaticsView.as_view()),  # 胶种库存分段统计
    path('product-details/', ProductDetailsView.as_view()),            # 胶料车间库存明细
]

