from django.urls import path, include
from rest_framework.routers import DefaultRouter

from plan.views import ProductDayPlanViewSet, \
    MaterialDemandedAPIView, ProductDayPlanManyCreate, \
    ProductDayPlanAPiView, MaterialDemandedView, ProductClassesPlanManyCreate, ProductClassesPlanList, PlanReceive, \
    ProductBatchingReceive, ProductBatchingDetailReceive, ProductDayPlanReceive, ProductClassesPlanReceive, \
    MaterialReceive, BatchingClassesPlanView, IssueBatchingClassesPlanView

router = DefaultRouter()

# 胶料日计划
router.register(r'product-day-plans', ProductDayPlanViewSet)
# 计划管理新增页面展示
router.register(r'product-classes-plan-list', ProductClassesPlanList)

# 配料日班次计划
router.register(r'batching-classes-plan', BatchingClassesPlanView)


urlpatterns = [
    path('', include(router.urls)),
    path('plan-receive/', PlanReceive.as_view()),  # 上辅机群控中计划同步回mes
    path('material-demanded-apiview/', MaterialDemandedAPIView.as_view()),  # 原材料需求量展示
    path('product-day-plan-manycreate/', ProductDayPlanManyCreate.as_view()),  # 群增胶料日计划
    path('product-day-plan-notice/', ProductDayPlanAPiView.as_view()),  # 计划下发至上辅机
    path('materia-quantity-demande/', MaterialDemandedView.as_view()),  # 计划原材料需求列表
    path('product-classes-plan-manycreate/', ProductClassesPlanManyCreate.as_view()),  # 群增胶料日班次计划

    # 上辅机同步给mes的数据
    path('product-batching-receive/', ProductBatchingReceive.as_view()),  # 胶料配料标准同步
    path('product-batching-detail-receive/', ProductBatchingDetailReceive.as_view()),  # 胶料配料标准详情同步
    path('product-day-plan-receive/', ProductDayPlanReceive.as_view()),  # 胶料日计划同步
    path('product-classes-plan-receive/', ProductClassesPlanReceive.as_view()),  # 胶料日班次计划同步
    path('material-receive/', MaterialReceive.as_view()),  # 原材料同步
    path('issue-batching-classes-plan/<int:pk>/', IssueBatchingClassesPlanView.as_view())
]
