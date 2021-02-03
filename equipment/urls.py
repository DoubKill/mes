from django.urls import include, path
from rest_framework.routers import DefaultRouter
from equipment.views import EquipRealtimeViewSet
from equipment.views import EquipDownTypeViewSet, EquipDownReasonViewSet

from equipment.views import *


router = DefaultRouter()

router.register(r"equip_realtime", EquipRealtimeViewSet)


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

# 设备维修履历
router.register('equip-maintenance-order-log', EquipMaintenanceOrderLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('equip-current-status-list/', EquipCurrentStatusList.as_view()),
]


