# -*- coding: UTF-8 -*-
"""
auther:
datetime: 2020/8/28
name:
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from terminal.views import BatchBasicInfoView, BatchProductionInfoView, BatchProductBatchingVIew, \
    BatchChargeLogViewSet, EquipOperationLogView, BatchingClassesPlanView, FeedingLogViewSet, WeightTankStatusView, \
    WeightBatchingLogViewSet, WeightPackageLogViewSet, WeightPackageTrainsView, CheckVersion, BarCodeTank, DevTypeView

router = DefaultRouter()
router.register('batch-log', BatchChargeLogViewSet)  # 投料履历管理
router.register('feeding-log', FeedingLogViewSet)  # PDA投料履历
router.register('weighting-log', WeightBatchingLogViewSet)  # 称量履历管理
router.register('weighting-package-log', WeightPackageLogViewSet)  # 称量打包履历


urlpatterns = [
    path('', include(router.urls)),
    path('check-version/', CheckVersion.as_view()),  # 开机检查版本
    path('batch-bacisinfo/', BatchBasicInfoView.as_view()),  # 获取设备基础信息
    path('batch-productinfo/', BatchProductionInfoView.as_view()),  # 投料-获取生产信息
    path('batch-batching-info/', BatchProductBatchingVIew.as_view()),  # 投料-获取配方信息
    path('batch-equip-operation-log/', EquipOperationLogView.as_view()),  # 投料-机台停机/开机操作
    path('batching-classes-plan/', BatchingClassesPlanView.as_view()),  # 配料班次计划列表
    path('weighting-tack-status/', WeightTankStatusView.as_view()),  # 小料称量-料管信息
    path('weighting-package-trains/', WeightPackageTrainsView.as_view()),  # 称量打包车次列表
    path('bar-code-tank/', BarCodeTank.as_view()),
    path('dev-types', DevTypeView.as_view())
]
