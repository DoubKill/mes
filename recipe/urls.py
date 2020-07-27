from django.urls import path, include
from rest_framework.routers import DefaultRouter

from recipe.views import MaterialViewSet

router = DefaultRouter()

# 原材料
router.register(r'materials', MaterialViewSet)

urlpatterns = [
    path('', include(router.urls)),
]