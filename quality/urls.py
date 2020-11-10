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
    MaterialDealResultUpdateValidTime, MaterialTestIndicatorMethods, LevelResultViewSet, ProductDayStatistics, \
    LabelPrintViewSet, DealSuggestionView

router = DefaultRouter()
router.register('material-test-orders', MaterialTestOrderViewSet)
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
# 不合格处理意见
router.register('deal-suggestion', DealSuggestionViewSet)
# 不合格处理
router.register('material-deal-result', MaterialDealResultViewSet)
# 等级和结果
router.register('level-result', LevelResultViewSet)
# 快检标签打印
router.register('label-print', LabelPrintViewSet)

urlpatterns = [
    path('batching-materials/', ProductBatchingMaterialListView.as_view()),  # 胶料原材料列表
    path('test-indicator-data-points/', TestIndicatorDataPointListView.as_view()),  # 获取试验指标下所有的数据点
    path('result-status/', MaterialDealStatusListView.as_view()),  # 不合格状态筛选
    path('deal-type/', DealTypeView.as_view()),
    path('pallet-feed-test/', PalletFeedbacksTestListView.as_view()),  # 快检信息综合管里
    path('material_valid_time/', MaterialDealResultUpdateValidTime.as_view()),  # 快检信息综合管理修改有效时间
    path('mat-test-indicator-methods/', MaterialTestIndicatorMethods.as_view()),
    path('product_day_statistics/', ProductDayStatistics.as_view()),  # 胶料日合格率统计
    path('deal-suggestion-view/', DealSuggestionView.as_view()),  # 处理意见展示
    path('', include(router.urls)),
]
