# -*- coding: UTF-8 -*-
"""
auther:
datetime: 2020/8/28
name:
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from quality.views import TestIndicatorViewSet, TestMethodViewSet, TestIndicatorDataPointListView, \
    MaterialTestOrderViewSet, TestTypeViewSet, DataPointViewSet, MaterialTestMethodViewSet, \
    MaterialDataPointIndicatorViewSet, ProductBatchingMaterialListView, MaterialDealResultViewSet, \
    DealSuggestionViewSet, MaterialDealStatusListView, DealTypeView, PalletFeedbacksTestListView, \
    MaterialTestIndicatorMethods, LevelResultViewSet, ProductDayStatistics, LabelPrintViewSet, DealSuggestionView, \
    MaterialTestResultHistoryView, ProductDayDetail, BatchMonthStatisticsView, PrintMaterialDealResult, \
    BatchDayStatisticsView, BatchProductNoDayStatisticsView, BatchProductNoMonthStatisticsView, \
    UnqualifiedDealOrderViewSet, UnqualifiedOrderTrains, ImportAndExportView, TestTypeRawViewSet, DataPointRawViewSet, \
    TestMethodRawViewSet, MaterialTestMethodRawViewSet, MaterialDataPointIndicatorRawViewSet, LevelResultRawViewSet, \
    TestIndicatorRawViewSet, MaterialTestIndicatorMethodsRaw, MaterialInventoryView, MaterialTestOrderRawViewSet, \
    TestIndicatorDataPointRawListView

router = DefaultRouter()


"""原料"""
# 试验指标
router.register('test-indicators-raw', TestIndicatorRawViewSet)
# 试验类型
router.register('test-types-raw', TestTypeRawViewSet)
# 试验类型数据点
router.register('data-points-raw', DataPointRawViewSet)
# 试验方法
router.register('test-methods-raw', TestMethodRawViewSet)
# 物料试验方法
router.register('mat-test-methods-raw', MaterialTestMethodRawViewSet)
# 物料数据指标
router.register('mat-data-point-indicators-raw', MaterialDataPointIndicatorRawViewSet)
# 等级和结果
router.register('level-result-raw', LevelResultRawViewSet)
# 原料检测单
router.register('material-test-orders-raw', MaterialTestOrderRawViewSet)


"""胶料"""
# 试验指标
router.register('test-indicators', TestIndicatorViewSet)
# 试验类型
router.register('test-types', TestTypeViewSet)
# 试验类型数据点
router.register('data-points', DataPointViewSet)
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
router.register('pallet-feed-test', PalletFeedbacksTestListView),

urlpatterns = [
    path('batching-materials/', ProductBatchingMaterialListView.as_view()),  # 胶料原材料列表
    path('test-indicator-data-points/', TestIndicatorDataPointListView.as_view()),  # 获取试验指标下所有的数据点
    path('result-status/', MaterialDealStatusListView.as_view()),  # 不合格状态筛选
    path('deal-type/', DealTypeView.as_view()),
    # path('material_valid_time/', MaterialDealResultUpdateValidTime.as_view()),  # 快检信息综合管理修改有效时间
    path('mat-test-indicator-methods/', MaterialTestIndicatorMethods.as_view()),
    path('product_day_statistics/', ProductDayStatistics.as_view()),  # 胶料日合格率统计
    path('product_day_detail/', ProductDayDetail.as_view()),  # 胶料日合格率详情信息统计
    path('deal-suggestion-view/', DealSuggestionView.as_view()),  # 处理意见展示
    path('test-result-history/', MaterialTestResultHistoryView.as_view()),
    path('print-material-deal-result/', PrintMaterialDealResult.as_view()),  # 不合格处理导出功能
    path('unqualified-trains/', UnqualifiedOrderTrains.as_view()),
    path('import-material-test-orders/', ImportAndExportView.as_view()),  # 快检数据导入

    path('mat-test-indicator-methods-raw/', MaterialTestIndicatorMethodsRaw.as_view()),
    path('material-inventory/', MaterialInventoryView.as_view()),  # 原料入库信息
    path('test-indicator-data-points-raw/', TestIndicatorDataPointRawListView.as_view()),

    path('', include(router.urls)),
]
