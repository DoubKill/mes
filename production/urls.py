from django.urls import include, path
from rest_framework.routers import DefaultRouter

from production.summary_views import ClassesBanBurySummaryView, EquipBanBurySummaryView, CollectTrainsFeedbacksList, \
    CutTimeCollect, SumCollectTrains
from production.views import *

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

# 密炼LOT生产履历
router.register(r'production-record', ProductionRecordViewSet)

# 密炼机台别计划对比
router.register(r'plan-reality', PlanRealityViewSet, basename="plan-reality")

# 密炼实绩
router.register(r'product-actual', ProductActualViewSet, basename="product-actual")

urlpatterns = [
    path('', include(router.urls)),
    path('trains-feedbacks-batch/', TrainsFeedbacksBatch.as_view()),
    path('pallet-feedbacks-batch/', PalletFeedbacksBatch.as_view()),
    path('equip-status-batch/', EquipStatusBatch.as_view()),
    path('plan-status-batch/', PlanStatusBatch.as_view()),
    path('classes-banbury-summary/', ClassesBanBurySummaryView.as_view()),
    path('expend-material-batch/', ExpendMaterialBatch.as_view()),
    path('collect-trains-feed/', CollectTrainsFeedbacksList.as_view()),  # 胶料单车次时间汇总
    path('sum-collect-trains/', SumCollectTrains.as_view()),  # 胶料单车次时间汇总最大最小平均时间
    path('cut-time-collect/', CutTimeCollect.as_view()),  # 规格切换时间汇总
    path('equip-banbury-summary/', EquipBanBurySummaryView.as_view()),
    path('expend-material-batch/', ExpendMaterialBatch.as_view()),
    path('pallet-trains-feedbacks/', PalletTrainFeedback.as_view()),  # 托盘开始到结束车次列表
    path('production-plan-reality-analysis/', ProductionPlanRealityAnalysisView.as_view()), # 产量计划实际分析
    path('update-cause/', UpdateUnReachedCapacityCauseView.as_view()),  # 创建未达产能原因
    path('interval-output-statistics/', IntervalOutputStatisticsView.as_view())  # 区间产量统计
]
