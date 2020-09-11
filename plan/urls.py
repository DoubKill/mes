from rest_framework.routers import DefaultRouter
from django.urls import path, include
from plan.views import ProductDayPlanViewSet, \
    MaterialDemandedAPIView, ProductDayPlanManyCreate, \
    ProductDayPlanAPiView, MaterialDemandedView

router = DefaultRouter()

# 胶料日计划
router.register(r'product-day-plans', ProductDayPlanViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('material-demanded-apiview/', MaterialDemandedAPIView.as_view()),  # 原材料需求量展示
    path('product-day-plan-manycreate/', ProductDayPlanManyCreate.as_view()),  # 群增胶料日计划
    path('product-day-plan-notice/', ProductDayPlanAPiView.as_view()),  # 计划下发至上辅机
    path('materia-quantity-demande/', MaterialDemandedView.as_view()),  # 计划原材料需求列表
]
