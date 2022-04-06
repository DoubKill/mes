from django.urls import path, include
from rest_framework.routers import DefaultRouter

from plan.views import ProductDayPlanViewSet, \
    MaterialDemandedAPIView, ProductDayPlanManyCreate, \
    ProductDayPlanAPiView, MaterialDemandedView, ProductClassesPlanManyCreate, ProductClassesPlanList, PlanReceive, \
    ProductBatchingReceive, ProductBatchingDetailReceive, ProductDayPlanReceive, ProductClassesPlanReceive, \
    MaterialReceive, BatchingClassesPlanView, IssueBatchingClassesPlanView, BatchingClassesEquipPlanViewSet, \
    PlantImportView, LabelPlanInfo, SchedulingParamsSettingView, SchedulingRecipeMachineSettingView, \
    MaterialTankStatusView, SchedulingEquipCapacityViewSet, SchedulingWashRuleViewSet, \
    SchedulingWashPlaceKeywordViewSet, SchedulingWashPlaceOperaKeywordViewSet, RecipeMachineWeight, \
    SchedulingProductDemandedDeclareViewSet, ProductDeclareSummaryViewSet, SchedulingProductSafetyParamsViewSet, \
    SchedulingResultViewSet, SchedulingEquipShutDownPlanViewSet, SchedulingProceduresView, SchedulingStockSummary, \
    SchedulingMaterialDemanded, RecipeStages

router = DefaultRouter()

# 胶料日计划
router.register(r'product-day-plans', ProductDayPlanViewSet)
# 计划管理新增页面展示
router.register(r'product-classes-plan-list', ProductClassesPlanList)

# 配料日班次计划
router.register(r'batching-classes-plan', BatchingClassesPlanView)

router.register(r'batching-classes-equip-plan', BatchingClassesEquipPlanViewSet)

router.register(r'scheduling-params-setting', SchedulingParamsSettingView)  # 排程基础参数设置
router.register(r'scheduling-recipe-machine-setting', SchedulingRecipeMachineSettingView)  # 排程定机表
router.register(r'scheduling-equip-capacity', SchedulingEquipCapacityViewSet)  # 机台生产能力
router.register(r'scheduling-wash-rules', SchedulingWashRuleViewSet)  # 洗车放置规则
router.register(r'scheduling-place-keyword', SchedulingWashPlaceKeywordViewSet)  # 胶料/单位关键字定义
router.register(r'scheduling-place-opera-keyword', SchedulingWashPlaceOperaKeywordViewSet)  # 处理关键字定义
router.register(r'scheduling-product-demanded-declare', SchedulingProductDemandedDeclareViewSet)  # 胶料计划申报
router.register(r'scheduling-product-declare-summary', ProductDeclareSummaryViewSet)  # 胶料计划申报汇总
router.register(r'scheduling-product-safety-params', SchedulingProductSafetyParamsViewSet)  # 各分厂安全库存及安全系数列表
router.register(r'scheduling-result', SchedulingResultViewSet)  # 排程结果
router.register(r'scheduling-equip-shutdown-plan', SchedulingEquipShutDownPlanViewSet)  # 计划停机
router.register(r'scheduling-stock-summary', SchedulingStockSummary)  # 无硫库存统计


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
    path('issue-batching-classes-plan/<int:pk>/', IssueBatchingClassesPlanView.as_view()),
    path('plan-import/', PlantImportView.as_view()),  # 计划导入
    path('label-plan-info/', LabelPlanInfo.as_view()),

    path('recipe-machine-weight/', RecipeMachineWeight.as_view()),
    path('mat-tank-status/', MaterialTankStatusView.as_view()),
    path('scheduling-procedures/', SchedulingProceduresView.as_view()),
    path('scheduling-material-demanded/', SchedulingMaterialDemanded.as_view()),
    path('scheduling-recipe-stages/', RecipeStages.as_view()),
]
