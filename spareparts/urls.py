# -*- coding: UTF-8 -*-
"""
auther:
datetime: 2020/8/28
name:
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from spareparts.views import SpareInventoryViewSet, MaterialLocationBindingViewSet, SpareInventoryLogViewSet

router = DefaultRouter()
# 备品备件库
router.register('spare-inventory', SpareInventoryViewSet)

# 位置点和物料绑定
router.register('material-location-binding', MaterialLocationBindingViewSet)
# 出入履历
router.register('spare-inventory-log', SpareInventoryLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
