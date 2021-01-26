from django.urls import include, path
from rest_framework.routers import DefaultRouter


# app_name = 'system'
from equipment.views import EquipRealtimeViewSet

router = DefaultRouter()

router.register(r"equip_realtime", EquipRealtimeViewSet)



urlpatterns = [
    path('', include(router.urls)),
\
]
