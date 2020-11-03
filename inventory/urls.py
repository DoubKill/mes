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

urlpatterns = [
    path('out-store/', OutWork.as_view()),
    path('', include(router.urls)),
    ]