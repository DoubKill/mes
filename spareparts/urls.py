# -*- coding: UTF-8 -*-
"""
auther:
datetime: 2020/8/28
name:
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from spareparts.views import SpareInventoryViewSet, SpareLocationBindingViewSet, SpareInventoryLogViewSet, \
    SpareLocationViewSet, SpareTypeViewSet, SpareViewSet, SpareImportAPIView

router = DefaultRouter()
# 备品备件库
router.register('spare-inventory', SpareInventoryViewSet)

# 位置点和物料绑定
router.register('spare-location-binding', SpareLocationBindingViewSet)
# 出入履历
router.register('spare-inventory-log', SpareInventoryLogViewSet)
# 库存点
router.register('spare-location', SpareLocationViewSet)

# 备品备件类型
router.register('spare-type', SpareTypeViewSet)
# 备品备件信息
router.register('spare', SpareViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('spare-import/', SpareImportAPIView.as_view()),  # 备品备件基本信息导入

]
