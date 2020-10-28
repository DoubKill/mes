# -*- coding: UTF-8 -*-
"""
auther:
datetime: 2020/8/28
name:
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from quality.views import TestIndicatorListView, TestMethodViewSet, TestIndicatorDataPointListView, \
    MaterialTestOrderViewSet, TestTypeViewSet, DataPointViewSet, MaterialTestMethodViewSet, \
    MaterialDataPointIndicatorViewSet, ProductBatchingMaterialListView, MaterialDealResultViewSet, \
    DealSuggestionViewSet, MaterialDealStatusListView, DealTypeView

router = DefaultRouter()
router.register('material-test-orders', MaterialTestOrderViewSet)

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
# 不合格处理意见管理
router.register('material-deal-result', MaterialDealResultViewSet)

urlpatterns = [
    path('test-indicators/', TestIndicatorListView.as_view()),  # 试验指标列表
    path('batching-materials/', ProductBatchingMaterialListView.as_view()),  # 胶料原材料列表
    # path('material-test-indicators-tab/', MaterialTestIndicatorsTabView.as_view()),
    path('test-indicator-data-points/', TestIndicatorDataPointListView.as_view()),  # 获取试验指标下所有的数据点
    # path('mat-indicator-tab/', MatIndicatorsTabView.as_view()),
    path('result-status/', MaterialDealStatusListView.as_view()), # 不合格状态筛选
    path('deal-type/', DealTypeView.as_view()),
    path('', include(router.urls)),
    ]
