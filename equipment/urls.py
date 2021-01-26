# -*- coding: UTF-8 -*-
"""
auther:
datetime: 2020/8/28
name:
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from equipment.views import EquipDownTypeViewSet, EquipDownReasonViewSet, EquipCurrentStatusList

router = DefaultRouter()
# 设备停机类型
router.register('equip-down-type', EquipDownTypeViewSet)

# 设备停机原因
router.register('equip-down-reason', EquipDownReasonViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('equip-current-status-list/', EquipCurrentStatusList.as_view()),

]
