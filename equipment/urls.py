from django.urls import include, path
from rest_framework.routers import DefaultRouter
from equipment.views import EquipRealtimeViewSet
from equipment.views import EquipDownTypeViewSet, EquipDownReasonViewSet

from equipment.views import EquipDownTypeViewSet, EquipDownReasonViewSet, EquipCurrentStatusList


router = DefaultRouter()

router.register(r"equip_realtime", EquipRealtimeViewSet)


# 设备停机类型
router.register('equip-down-type', EquipDownTypeViewSet)

# 设备停机原因
router.register('equip-down-reason', EquipDownReasonViewSet)



urlpatterns = [
    path('', include(router.urls)),
    path('equip-current-status-list/', EquipCurrentStatusList.as_view()),
]


