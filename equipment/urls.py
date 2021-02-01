# -*- coding: UTF-8 -*-
"""
auther:
datetime: 2020/8/28
name:
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from equipment.views import *

router = DefaultRouter()
# 设备停机类型
router.register('equip-down-type', EquipDownTypeViewSet)

# 设备停机原因
router.register('equip-down-reason', EquipDownReasonViewSet)

# 设备现况
router.register('equip-current-status', EquipCurrentStatusViewSet)

# 设备部位
router.register('equip-part', EquipPartViewSet)

# 维修表单
router.register('equip-maintenance-order', EquipMaintenanceOrderViewSet)

# 资产类型节点
router.register('property-type-node', PropertyTypeNodeViewSet)

# 资产
router.register('property', PropertyViewSet)

# 通知配置
router.register('platform-config', PlatformConfigViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('equip-current-status-list/', EquipCurrentStatusList.as_view()),  # 设备现况汇总

]
