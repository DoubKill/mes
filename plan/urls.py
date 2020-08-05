from rest_framework.routers import DefaultRouter
from django.urls import path, include
from plan.views import ProductDayPlanViewSet, MaterialDemandedViewSet, ProductBatchingDayPlanViewSet, \
    MaterialRequisitionViewSet, ProductDayPlanCopyView, ProductBatchingDayPlanCopyView, MaterialRequisitionCopyView

router = DefaultRouter()

router.register(r'product-day-plans', ProductDayPlanViewSet)
router.register(r'material-demandeds', MaterialDemandedViewSet)
router.register(r'product-batching-day-plans', ProductBatchingDayPlanViewSet)
router.register(r'material-requisitions', MaterialRequisitionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('product-day-plans-copy/', ProductDayPlanCopyView.as_view()),
    path('product-batching-day-plans-copy/', ProductBatchingDayPlanCopyView.as_view()),
    path('material-requisitions-copy/', MaterialRequisitionCopyView.as_view()),
]
