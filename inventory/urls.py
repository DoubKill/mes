# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/8/28
name: 
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .views import OutWork

router = DefaultRouter()

# 原材料立库
router.register(r'material-inventory-view', views.MaterialInventory, basename="material-inventory")
# 胶料立库
router.register(r'product-inventory', views.ProductInventory, basename="product-inventory")

# 物料库存信息|线边库|终炼胶库|原材料库
router.register(r'material-inventory-manage', views.MaterialInventoryManageViewSet, basename='material-inventory-manage')

# 物料出入库履历
router.register(r'inventory-log', views.InventoryLogViewSet)

urlpatterns = [
    path('out-store/', OutWork.as_view()),
    path('', include(router.urls)),
    ]