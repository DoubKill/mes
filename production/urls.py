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

# 将群控的车次报表直接移植过来
# 称量信息展示
router.register(r'weigh-information-list', WeighInformationList, basename="weigh-information-list")
# 密炼信息展示
router.register(r'mixer-information-list', MixerInformationList, basename="mixer-information-list")
# 工艺曲线信息展示
router.register(r'curve-information-list', CurveInformationList, basename="curve-information-list")
# 报警信息展示
router.register(r'alarm_log-list', AlarmLogList, basename="alarm_log-list")
# 车次报表展示
router.register(r'trains-feedbacks-apiview', TrainsFeedbacksAPIView, basename="trains-feedbacks-apiview")
# 绩效 岗位阶梯表
router.register(r'performance-job-ladder', PerformanceJobLadderViewSet)
# 丁基胶 规格设定
router.register('product-info-dj', ProductInfoDingJiViewSet)
# 细料/硫磺单价
router.register('set-the-price', SetThePriceViewSet)
# 员工其他奖惩/补贴
router.register('performance-subsidy', PerformanceSubsidyViewSet, basename='performance-subsidy')


urlpatterns = [
    path('', include(router.urls)),
    path('trains-feedbacks-batch/', TrainsFeedbacksBatch.as_view()),
    path('pallet-feedbacks-batch/', PalletFeedbacksBatch.as_view()),
    path('equip-status-batch/', EquipStatusBatch.as_view()),
    path('plan-status-batch/', PlanStatusBatch.as_view()),
    path('process-feedback-batch/', ProcessFeedbackBatch.as_view()),
    path('alarm-log-batch/', AlarmLogBatch.as_view()),
    path('classes-banbury-summary/', ClassesBanBurySummaryView.as_view()),
    path('expend-material-batch/', ExpendMaterialBatch.as_view()),
    path('collect-trains-feed/', CollectTrainsFeedbacksList.as_view()),  # 胶料单车次时间汇总
    path('sum-collect-trains/', SumCollectTrains.as_view()),  # 胶料单车次时间汇总最大最小平均时间
    path('cut-time-collect/', CutTimeCollect.as_view()),  # 规格切换时间汇总
    path('equip-banbury-summary/', EquipBanBurySummaryView.as_view()),
    path('expend-material-batch/', ExpendMaterialBatch.as_view()),
    path('pallet-trains-feedbacks/', PalletTrainFeedback.as_view()),  # 托盘开始到结束车次列表
    path('production-plan-reality-analysis/', ProductionPlanRealityAnalysisView.as_view()),  # 产量计划实际分析
    path('update-cause/', UpdateUnReachedCapacityCauseView.as_view()),  # 创建未达产能原因
    path('interval-output-statistics/', IntervalOutputStatisticsView.as_view()),  # 区间产量统计
    path('material-output-real/', MaterialOutputView.as_view()),  # 规格产量统计
    path('equip-product-real/', EquipProductRealView.as_view()),  # 实时机台生产信息
    path('material-pass-real/', MaterialPassRealView.as_view()),
    path('equip-tank/', MaterialTankStatusList.as_view()),  # 机台编号和罐编号
    # 中策调可视化的接口
    path('equip-output-statistics/', WeekdayProductStatisticsView.as_view()), # 上周所有机台每日总产能
    path('output-statistics/', ProductionStatisticsView.as_view()), # 上月每日炼胶总产能
    path('equip-output-real/', DayCapacityView.as_view()),  # 单日产能
    path('plan-info-real/', PlanInfoReal.as_view()),  # 密炼状态信息
    path('equip-info-real/', EquipInfoReal.as_view()),  # 设备状态信息

    path('runtime-record/', RuntimeRecordView.as_view()),  # 生产运行记录

    path('trains-fix/', TrainsFixView.as_view()),  # 车次修改（+-）
    path('pallet-train-batch-fix/', PalletTrainsBatchFixView.as_view()),  # 收皮车次批量修改

    # 生产运行记录
    path('runtime-record-detail/', RuntimeRecordDetailView.as_view()),

    # 生产管理-生产记录（计划对比实际）
    path('product-classes-plan-real/', ProductPlanRealView.as_view()),

    path('open-api/batch-info/', ProductBatchInfo.as_view()),

    # 不合格品原因统计
    path('durate-putin-reson/', RubberCannotPutinReasonView.as_view()),
    # 机台目标值设定
    path('machine-target-value/', MachineTargetValue.as_view()),
    # 月产量统计汇总报表
    path('monthly-output-statistics-report/', MonthlyOutputStatisticsReport.as_view()),

    # 密炼机台产量汇总表
    path('summary-of-mill-output/', SummaryOfMillOutput.as_view()),
    # 称量设备产量汇总表
    path('summary-of-weighing-output/', SummaryOfWeighingOutput.as_view()),

    # 员工出勤记录表
    path('employee-attendance-records/', EmployeeAttendanceRecordsView.as_view()),
    path('employee-attendance-records-export/', EmployeeAttendanceRecordsExport.as_view({'get': 'export'})),

    # 绩效 单价表
    path('performance-unit-price/', PerformanceUnitPriceView.as_view()),
    # 员工绩效汇总
    path('performance-summary/', PerformanceSummaryView.as_view()),

    # 是否独立上岗模版
    path('independent-post-template/', IndependentPostTemplateView.as_view()),


    # 月产量完成报表
    path('daily-production-completion-report/', DailyProductionCompletionReport.as_view()),
]
