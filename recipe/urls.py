from django.urls import path, include
from rest_framework.routers import DefaultRouter

from recipe.views import MaterialViewSet, ProductInfoViewSet, ProductInfoCopyView, ProductStageInfoView, \
    ProductRecipeListView, ProductBatchingViewSet, PreProductBatchView, MaterialAttributeViewSet, \
    ValidateProductVersionsView, ProcessStepsViewSet

router = DefaultRouter()

# 原材料
router.register(r'materials', MaterialViewSet)

# 原材料属性
router.register(r'materials-attribute', MaterialAttributeViewSet)

# 胶料工艺信息
router.register(r'product-infos', ProductInfoViewSet)

# 胶料配料
router.register(r'product-batching', ProductBatchingViewSet)

# 胶料步序
router.register(r'process-steps', ProcessStepsViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('validate-versions/', ValidateProductVersionsView.as_view()),  # 验证版本号，创建胶料工艺信息前调用
    path('copy-product-infos/', ProductInfoCopyView.as_view()),  # 胶料复制
    path('product-stages/', ProductStageInfoView.as_view()),  # 根据产地获取胶料及其段次信息
    path('product-recipe/', ProductRecipeListView.as_view()),  # 根据胶料工艺和段次获取胶料段次配方原材料信息
    path('pre-batch-info/', PreProductBatchView.as_view()),  # 根据胶料工艺id和段次获取上段位配料信息
    ]
