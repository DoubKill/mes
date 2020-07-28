from django.urls import path, include
from rest_framework.routers import DefaultRouter

from recipe.views import MaterialViewSet, ProductInfoViewSet, ProductInfoCopyView, ProductStageInfo

router = DefaultRouter()

# 原材料
router.register(r'materials', MaterialViewSet)

# 胶料工艺信息
router.register(r'product-infos', ProductInfoViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('copy-product-infos/', ProductInfoCopyView.as_view()),  # 胶料复制
    path(r'product-stages/', ProductStageInfo.as_view()),  # 根据产地获取胶料及其段次信息
]