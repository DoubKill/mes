# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/8/28
name: 
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .views import OutWork, MaterialCount \
    , PutPlanManagement, OverdueMaterialManagement

router = DefaultRouter()

# 原材料立库
router.register(r'material-inventory-view', views.MaterialInventoryView, basename="material-inventory")
# 胶料立库
router.register(r'product-inventory', views.ProductInventory, basename="product-inventory")
# 出库计划管理
router.register('put-plan-management', PutPlanManagement)

# 过期胶料管理
router.register('overdue-material-management', OverdueMaterialManagement)

router.register('out_work', OutWork)

# 物料库存信息|线边库|终炼胶库|原材料库
router.register(r'material-inventory-manage', views.MaterialInventoryManageViewSet, basename='material-inventory-manage')

<<<<<<< HEAD
# 物料出入库履历
router.register(r'inventory-log', views.InventoryLogViewSet)
=======
# 混炼胶库
>>>>>>> 9f8df301f4dfab6f4be1d95eb93977bd74bbeee0

urlpatterns = [
    path('material_count/', MaterialCount.as_view()),
    path('', include(router.urls)),

    ]