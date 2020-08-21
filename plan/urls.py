from rest_framework.routers import DefaultRouter
from django.urls import path, include
from plan.views import ProductDayPlanViewSet, ProductBatchingDayPlanViewSet, \
    ProductDayPlanCopyView, ProductBatchingDayPlanCopyView, MaterialRequisitionClassesViewSet, MaterialDemandedAPIView, \
    ProductBatchingDayPlanManyCreate, ProductDayPlanManyCreate

router = DefaultRouter()
# 胶料日计划
router.register(r'product-day-plans', ProductDayPlanViewSet)

# 小料日计划
router.register(r'product-batching-day-plans', ProductBatchingDayPlanViewSet)

# 领料班次计划
router.register(r'material-requisition-classes', MaterialRequisitionClassesViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('product-day-plans-copy/', ProductDayPlanCopyView.as_view()),  # 胶料日计划复制
    path('product-batching-day-plans-copy/', ProductBatchingDayPlanCopyView.as_view()),  # 小料日计划复制
    path('material-demanded-apiview/', MaterialDemandedAPIView.as_view()),  # 原材料需求量展示
    path('product-batching-day-plan-manycreate/', ProductBatchingDayPlanManyCreate.as_view()),  # 群增小料日计划
    path('product-day-plan-manycreate/', ProductDayPlanManyCreate.as_view()),  # 群增胶料日计划
]
