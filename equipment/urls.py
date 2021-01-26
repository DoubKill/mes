from django.urls import include, path
from rest_framework.routers import DefaultRouter
from equipment.views import EquipRealtimeViewSet
from equipment.views import EquipDownTypeViewSet, EquipDownReasonViewSet


router = DefaultRouter()

router.register(r"equip_realtime", EquipRealtimeViewSet)


# 设备停机类型
router.register('equip_down_type', EquipDownTypeViewSet)

# 设备停机原因
router.register('equip_down_reason', EquipDownReasonViewSet)


urlpatterns = [
    path('', include(router.urls)),
]

