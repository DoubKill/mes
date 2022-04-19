# -*- coding: UTF-8 -*-
"""
auther:
datetime: 2020/8/28
name:
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from quality.views import *

router = DefaultRouter()

"""胶料"""
# 试验指标
router.register('test-indicators', TestIndicatorViewSet)
# 试验类型
router.register('test-types', TestTypeViewSet)
# 试验类型数据点
router.register('data-points', DataPointViewSet)
# 数据点误差管理（pass章管理）
router.register('data-point-standard-errors', DataPointStandardErrorViewSet)
# 试验方法
router.register('test-methods', TestMethodViewSet)
# 物料试验方法
router.register('mat-test-methods', MaterialTestMethodViewSet)
# 物料数据库指标
router.register('mat-data-point-indicators', MaterialDataPointIndicatorViewSet)
# 检测单
router.register('material-test-orders', MaterialTestOrderViewSet)
# 不合格处理意见
router.register('deal-suggestion', DealSuggestionViewSet)
# 不合格处理
router.register('material-deal-result', MaterialDealResultViewSet)
# 等级和结果
router.register('level-result', LevelResultViewSet)
# 快检标签打印
router.register('label-print', LabelPrintViewSet)

# 月批次快检合格率统计
router.register('batch-month-statistics', BatchMonthStatisticsView)

# 日批次快检合格率统计
router.register('batch-day-statistics', BatchDayStatisticsView)

# 胶料日合格率统计
router.register('batch-product-no-day-statistics', BatchProductNoDayStatisticsView, basename='dayStatistics')

# 胶料月合格率统计
router.register('batch-product-no-month-statistics', BatchProductNoMonthStatisticsView)

# 不合格处置单
router.register('unqualified-deal-orders', UnqualifiedDealOrderViewSet)

# 快检信息综合管里详情
router.register('pallet-feed-test', PalletFeedbacksTestListView)

# 不做pass章的判定胶种
router.register('ignored-product-info', IgnoredProductInfoViewSet)

# 胶料上报设备管理
router.register('product-report-equip', ProductReportEquipViewSet)

# 胶料上报值管理
router.register('product-report-value', ProductReportValueViewSet)


"""# 原材料新"""
# 检测设备类型
router.register('material-equip-types', MaterialEquipTypeViewSet)

# 检测设备
router.register('material-equips', MaterialEquipViewSet)

# 原材料指标单位管理
router.register('material-unit', ExamineValueUnitViewSet)

# 原材料检测类型
router.register('material-examine-type', MaterialExamineTypeViewSet)

# 原材料检测结果管理
router.register('material-examine-result', MaterialExamineResultViewSet)

# 原材料管理
router.register('examine-material', ExamineMaterialViewSet)

# 原材料总部送检条码登记
router.register('material-inspection-registration', MaterialInspectionRegistrationViewSet)

# 原材料不合格管理
# router.register('material-unqualified-process', UnqualifiedMaterialProcessModeViewSet)

# 原材料上报设备
router.register('material-report-equip', MaterialReportEquipViewSet)

# 原材料数据上报
router.register('material-report-value', MaterialReportValueViewSet)
# 门尼检测计划
router.register('product-test-plan', ProductTestPlanViewSet)
# 门尼检测计划详情
router.register('product-test-plan-detail', ProductTestPlanDetailViewSet)
# 门尼检测履历
router.register('product-test-resume', ProductTestResumeViewSet)

# 物性/钢拔检测数据查看/修改
router.register('rubber-max-stretch-test-result', RubberMaxStretchTestResultViewSet)
# 原材料检测计划
router.register('material-test-plan', MaterialTestPlanViewSet, basename='material-test-plan')
# 原材料检测计划详情
router.register('material-test-plan-detail', MaterialTestPlanDetailViewSet, basename='material-test-plan-detail')

urlpatterns = [
    path('', include(router.urls)),
    path('batching-materials/', ProductBatchingMaterialListView.as_view()),  # 胶料原材料列表
    path('test-indicator-data-points/', TestIndicatorDataPointListView.as_view()),  # 获取试验指标下所有的数据点
    path('result-status/', MaterialDealStatusListView.as_view()),  # 不合格状态筛选
    path('deal-type/', DealTypeView.as_view()),  # 创建处理类型
    # path('material_valid_time/', MaterialDealResultUpdateValidTime.as_view()),  # 快检信息综合管理修改有效时间
    path('mat-test-indicator-methods/', MaterialTestIndicatorMethods.as_view()),
    path('product_day_statistics/', ProductDayStatistics.as_view()),  # 胶料日合格率统计
    path('product_day_detail/', ProductDayDetail.as_view()),  # 胶料日合格率详情信息统计
    path('deal-suggestion-view/', DealSuggestionView.as_view()),  # 处理意见展示
    path('test-result-history/', MaterialTestResultHistoryView.as_view()),
    path('print-material-deal-result/', PrintMaterialDealResult.as_view()),  # 不合格处理导出功能
    # path('unqualified-trains/', UnqualifiedOrderTrains.as_view()),
    path('import-material-test-orders/', ImportAndExportView.as_view()),  # 快检数据导入
    path('barcode-preview/', BarCodePreview.as_view()),  # 条码追溯中的条码预览接口
    path('deal-mathod-history/', DealMethodHistoryView.as_view()),
    path('datapoint-curve/', TestDataPointCurveView.as_view()),
    path('data-point-label-history/', DataPointLabelHistoryView.as_view()),
    path('material-unqualified-types/', MaterialSingleTypeExamineResultView.as_view()),
    path('material-examine-result-curve/', ExamineResultCurveView.as_view()),
    path('show-qualified-range/', ShowQualifiedRange.as_view()),  # 全局配置快检卡片打印显示合格区间
    path('wms-material-search/', WMSMaterialSearchView.as_view()),
    path('report-value/', ReportValueView.as_view()),  # 数据检测值上报（胶料、原材料）
    path('equip-test-data/', TestDataView.as_view()),  # 设备监控数据
    path('check-equip/', CheckEquip.as_view()),  # 检测机台的转态

    # 不合格收皮数据列表
    path('unqialified-pallet-list/', UnqualifiedPalletFeedBackListView.as_view()),
    path('data-point-list/', DataPointListView.as_view()),

    # 不合格率统计
    path('product-test-statics/', ProductTestStaticsView.as_view()),  # 胶料别不合格率统计
    path('class-test-statics/', ClassTestStaticsView.as_view()),  # 班次别不合格率统计
    path('unqialified-equip/', UnqialifiedEquipView.as_view()),  # 机台别 不合格率统计

    path('label-print-logs/', LabelPrintLogView.as_view()),
    path('mat-data-point-indicators-history/', MaterialDataPointIndicatorHistoryView.as_view())
]
