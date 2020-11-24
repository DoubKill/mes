# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/8/28
name: 
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .views import MaterialCount, PutPlanManagement, OverdueMaterialManagement, OutWorkFeedBack, DispatchPlanList, \
    DispatchPlanUpdate

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

# 发货计划管理
router.register(r'dispatch-plan', views.DispatchPlanViewSet)  # 发货终端设计67

# 目的地
router.register(r'dispatch-location', views.DispatchLocationViewSet)

# 发货履历管理(发货终端设计)
router.register(r'dispatch-log', views.DispatchLogViewSet)  # 发货终端设计123

urlpatterns = [
    path('material_count/', MaterialCount.as_view()),
    path('outwork_feedback/', OutWorkFeedBack.as_view()),
    path('dispatch-plan-list/', DispatchPlanList.as_view()),  # 发货终端设计4
    path('dispatch-plan-update/', DispatchPlanUpdate.as_view()),  # 发货终端设计5

    path('', include(router.urls)),
]
