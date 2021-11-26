from django.urls import path, include
from rest_framework.routers import DefaultRouter

from recipe.views import MaterialViewSet, ProductInfoViewSet, \
    ProductBatchingViewSet, MaterialAttributeViewSet, \
    ValidateProductVersionsView, RecipeNoticeAPiView, MaterialSupplierViewSet, \
    WeighCntTypeViewSet, ProductBatchingDetailListView, ERPMaterialViewSet, ZCMaterialListView, GetERPZcMaterialAPiView, \
    ProductDevBatchingReceive, DevTypeProductBatching

router = DefaultRouter()

# 原材料
router.register(r'materials', MaterialViewSet)

# 原材料属性
router.register(r'materials-attribute', MaterialAttributeViewSet)

# 胶料工艺信息
router.register(r'product-infos', ProductInfoViewSet)

# 胶料配料
router.register(r'product-batching', ProductBatchingViewSet)

router.register(r'materials-supplier', MaterialSupplierViewSet)

# 中策ERP原材料对应关系绑定
router.register(r'erp-materials', ERPMaterialViewSet, basename='erp-mats')

# 小料配方
# router.register(r'weigh-batching', WeighBatchingViewSet)
router.register(r'weigh-cnt-type', WeighCntTypeViewSet)
router.register(r'product-batching-detail', ProductBatchingDetailListView)

urlpatterns = [
    path('', include(router.urls)),
    path('zc-materials/', ZCMaterialListView.as_view()),
    path('recipe-notice/', RecipeNoticeAPiView.as_view()),  # 配方下发至上辅机
    path('validate-versions/', ValidateProductVersionsView.as_view()),  # 验证版本号，创建胶料工艺信息前调用
    path('zc-materials-though-mes/', GetERPZcMaterialAPiView.as_view()),  # 通过mes物料名获取绑定关系的中策物料信息
    path('product-dev-batching-receive/', ProductDevBatchingReceive.as_view()),
    path('dev-type-batching/', DevTypeProductBatching.as_view())
    ]
