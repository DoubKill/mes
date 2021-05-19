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

"""# 原材料新"""
# 原材料检测设备
router.register('material-equipment', MaterialExamineEquipmentViewSet)
# 原材料检测设备类型
router.register('material-equipment-type', MaterialExamineEquipmentTypeViewSet)
# 原材料检测类型
router.register('material-examine-type', MaterialExamineTypeViewSet)
# 原材料评级标准
router.register('material-rate-standard', MaterialExamineRatingStandardViewSet)
# 原材料指标单位管理
router.register('material-unit', ExamineValueUnitViewSet)
# 原材料检测结果管理
router.register('material-examine-result', MaterialExamineResultViewSet)
# 原材料检测单指标结果管理
router.register('material-examine-single-result', MaterialSingleTypeExamineResultViewSet)

router.register('examine-material', ExamineMaterialViewSet)

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
    path('unqualified-trains/', UnqualifiedOrderTrains.as_view()),
    path('import-material-test-orders/', ImportAndExportView.as_view()),  # 快检数据导入
    path('barcode-preview/', BarCodePreview.as_view()),  # 条码追溯中的条码预览接口
    path('deal-mathod-history/', DealMethodHistoryView.as_view()),
    path('datapoint-curve/', TestDataPointCurveView.as_view()),
    path('data-point-label-history/', DataPointLabelHistoryView.as_view())
]
