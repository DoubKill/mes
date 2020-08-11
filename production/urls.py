from django.urls import include, path
from rest_framework.routers import DefaultRouter

from production.views import TrainsFeedbacksViewSet, PalletFeedbacksViewSet, EquipStatusViewSet, PlanStatusViewSet, \
    ExpendMaterialViewSet, OperationLogViewSet, QualityControlViewSet, PlanRealityViewSet

router = DefaultRouter()

# 车次/批次产出反馈
router.register(r'trains-feedbacks', TrainsFeedbacksViewSet)

# 托盘产出反馈
router.register(r'pallet-feedbacks', PalletFeedbacksViewSet)

# 机台状况反馈
router.register(r'equip-status', EquipStatusViewSet)

# 计划状态变更
router.register(r'plan-status', PlanStatusViewSet)

# 原材料消耗表
router.register(r'expend-materials', ExpendMaterialViewSet)

# 操作日志
router.register(r'operation-logs', OperationLogViewSet)

# 质检结果表
router.register(r'quality-control', QualityControlViewSet)

# 密炼机台别计划对比实际
# router.register(r'plan-reality', PlanRealityViewSet)

urlpatterns = [
    path('', include(router.urls)),

    path(r'plan-reality/', PlanRealityViewSet.as_view())
]
