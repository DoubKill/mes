# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/8/28
name: 
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .views import OutWork, MaterialCount

router = DefaultRouter()

# 原材料立库
router.register(r'material-inventory-view', views.MaterialInventory, basename="material-inventory")
# 胶料立库
router.register(r'product-inventory', views.ProductInventory, basename="product-inventory")

# 物料库存信息|线边库|终炼胶库|原材料库
router.register(r'material-inventory-manage', views.MaterialInventoryManageViewSet, basename='material-inventory-manage')

# 混炼胶库

urlpatterns = [
    path('material_no/', MaterialCount.as_view()),
    path('out-store/', OutWork.as_view()),
    path('', include(router.urls)),
    ]