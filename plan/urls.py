from rest_framework.routers import DefaultRouter
from django.urls import path, include
from plan.views import ProductDayPlanViewSet, MaterialDemandedViewSet, ProductBatchingDayPlanViewSet, \
    MaterialRequisitionViewSet, ProductDayPlanCopyView,ProductBatchingDayPlanCopyView,MaterialRequisitionCopyView

router = DefaultRouter()

router.register(r'product-day-plan', ProductDayPlanViewSet)
router.register(r'material-demanded', MaterialDemandedViewSet)
router.register(r'product-batching-day-plan', ProductBatchingDayPlanViewSet)
router.register(r'material-requisition', MaterialRequisitionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('product-day-plans-copy/', ProductDayPlanCopyView.as_view()),
    path('product-batching-day-plans-copy/', ProductBatchingDayPlanCopyView.as_view()),
    path('material-requisition-copy/', MaterialRequisitionCopyView.as_view()),
]
