# -*- coding: UTF-8 -*-
"""
auther:
datetime: 2020/8/28
name:
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from terminal.views import BatchBasicInfoView, BatchProductionInfoView, BatchProductBatchingVIew, \
    BatchChargeLogViewSet, EquipOperationLogView, BatchingClassesPlanView, FeedingLogViewSet, \
    WeightBatchingLogViewSet, WeightPackageLogViewSet, WeightPackageTrainsView, CheckVersion, BarCodeTank, \
    WeightTankStatusViewSet, BatchChargeLogListViewSet, WeightBatchingLogListViewSet

router = DefaultRouter()
router.register('batch-log', BatchChargeLogViewSet)  # 投料履历管理
router.register('feeding-log', FeedingLogViewSet)  # PDA投料履历
router.register('weighting-log', WeightBatchingLogViewSet)  # 称量履历管理
router.register('weighting-package-log', WeightPackageLogViewSet)  # 称量打包履历
router.register('weighting-tack-status', WeightTankStatusViewSet)  # 料管信息

urlpatterns = [
    path('', include(router.urls)),
    path('check-version/', CheckVersion.as_view()),  # 开机检查版本
    path('batch-bacisinfo/', BatchBasicInfoView.as_view()),  # 获取设备基础信息
    path('batch-productinfo/', BatchProductionInfoView.as_view()),  # 投料-获取当前班次计划信息以及当前投料信息
    path('batch-batching-info/', BatchProductBatchingVIew.as_view()),  # 投料-获取配方信息
    path('batch-equip-operation-log/', EquipOperationLogView.as_view()),  # 投料-机台停机/开机操作
    path('batching-classes-plan/', BatchingClassesPlanView.as_view()),  # 配料班次计划列表
    path('weighting-package-trains/', WeightPackageTrainsView.as_view()),  # 称量打包车次列表
    path('bar-code-tank/', BarCodeTank.as_view()),
    path('batch-charge-log-list/', BatchChargeLogListViewSet.as_view()),  # 密炼投入履历
    path('weight-batching-log-list/', WeightBatchingLogListViewSet.as_view()),  # 药品投入统计
]
