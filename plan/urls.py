from rest_framework.routers import DefaultRouter
from django.urls import path, include
from plan.views import ProductDayPlanViewSet, MaterialDemandedViewSet, ProductBatchingDayPlanViewSet, \
    ProductDayPlanCopyView, ProductBatchingDayPlanCopyView, MaterialRequisitionClassesViewSet, MaterialDemandedAPIView

router = DefaultRouter()

router.register(r'product-day-plans', ProductDayPlanViewSet)
router.register(r'product-batching-day-plans', ProductBatchingDayPlanViewSet)
router.register(r'material-requisition-classes', MaterialRequisitionClassesViewSet)
# router.register(r'material-requisitions', MaterialRequisitionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('material-demandeds/', MaterialDemandedViewSet.as_view()),
    path('product-day-plans-copy/', ProductDayPlanCopyView.as_view()),
    path('product-batching-day-plans-copy/', ProductBatchingDayPlanCopyView.as_view()),
    path('material-demanded-apiview/', MaterialDemandedAPIView.as_view()),

    # path('material-requisitions-copy/', MaterialRequisitionCopyView.as_view()),
]
