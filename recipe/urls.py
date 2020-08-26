from django.urls import path, include
from rest_framework.routers import DefaultRouter

from recipe.views import MaterialViewSet, ProductInfoViewSet, \
    ProductBatchingViewSet, MaterialAttributeViewSet, \
    ValidateProductVersionsView, RecipeNoticeAPiView

router = DefaultRouter()

# 原材料
router.register(r'materials', MaterialViewSet)

# 原材料属性
router.register(r'materials-attribute', MaterialAttributeViewSet)

# 胶料工艺信息
router.register(r'product-infos', ProductInfoViewSet)

# 胶料配料
router.register(r'product-batching', ProductBatchingViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('recipe-notice/', RecipeNoticeAPiView.as_view()),  # 配方下发至上辅机
    path('validate-versions/', ValidateProductVersionsView.as_view()),  # 验证版本号，创建胶料工艺信息前调用
    ]
