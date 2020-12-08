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
from .views import MaterialCount, PutPlanManagement, OverdueMaterialManagement, OutWorkFeedBack, \
    DispatchLogView

router = DefaultRouter()

# 原材料立库
router.register(r'material-inventory-view', views.MaterialInventoryView, basename="material-inventory")
# 胶料立库
router.register(r'product-inventory', views.ProductInventory, basename="product-inventory")
# 出库计划管理
router.register('put-plan-management', PutPlanManagement)

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

# 帘布库出库管理
router.register(r'lb-plan-management', views.PutPlanManagementLB)

'''在后面加发货终端设计的url表示发货终端设计所需要的接口和mes页面所需要的接口耦合了，在此提示说明一下，防止重复开发'''
# 发货计划管理
router.register(r'dispatch-plan', views.DispatchPlanViewSet)  # 发货终端设计67

# 目的地
router.register(r'dispatch-location', views.DispatchLocationViewSet)

# 终端发货履历管理
router.register(r'terminal-dispatch-log', TerminalDispatchLogViewSet)

# 终端发货履历管理
router.register(r'terminal-dispatch-plan', TerminalDispatchViewSet)

urlpatterns = [
    path('material_count/', MaterialCount.as_view()),
    path('outwork_feedback/', OutWorkFeedBack.as_view()),
    path('dispatch-log/', DispatchLogView.as_view()),  # 发货历史记录
    path('', include(router.urls)),
]
