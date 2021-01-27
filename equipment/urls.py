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


urlpatterns = [
    path('', include(router.urls)),
    path('equip-current-status-list/', EquipCurrentStatusList.as_view()),
]


