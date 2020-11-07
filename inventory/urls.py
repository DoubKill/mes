# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/8/28
name: 
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .views import OutWork \
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

urlpatterns = [
    # path('out-store/', OutWork.as_view()),
    path('', include(router.urls)),

    ]