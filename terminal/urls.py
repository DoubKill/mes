# -*- coding: UTF-8 -*-
"""
auther:
datetime: 2020/8/28
name:
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from terminal.views import BatchBasicInfoView, BatchProductionInfoView, BatchProductBatchingVIew, \
    LoadMaterialLogViewSet, EquipOperationLogView, BatchingClassesEquipPlanView, FeedingLogViewSet, \
    WeightBatchingLogViewSet, WeightPackageLogViewSet, WeightPackageTrainsView, CheckVersion, BarCodeTank, \
    WeightTankStatusViewSet, BatchChargeLogListViewSet, WeightBatchingLogListViewSet, \
    ProductExchange, XLMaterialVIewSet, XLBinVIewSet, RecipePreVIew, RecipeMaterialVIew, ReportBasicView, \
    ReportWeightView, XLPlanVIewSet, PackageExpireView, XLPlanCViewSet, XLPromptViewSet, WeightingTankStatus, \
    WeightPackageCViewSet, CarbonTankSetViewSet, FeedCheckOperationViewSet, FeedCapacityPlanView, \
    CarbonFeedingPromptViewSet, PowderTankSettingViewSet, OilTankSettingViewSet, PowderTankBatchingView, \
    FeedingErrorLampForCarbonView, FeedingOperateResultForCarbonView, CarbonOutCheckView, CarbonOutTaskView, \
    MaterialInfoIssue, ReplaceMaterialViewSet, ReturnRubberViewSet, ToleranceKeyword, ToleranceRuleViewSet, \
    WeightPackageManualViewSet, GetManualInfo, WeightPackageSingleViewSet, GetMaterialTolerance, UpdateFlagCountView, \
    MaterialDetailsAux, GetXlRecipesInfoView, XlRecipeNoticeView, ApplyHaltEquipView, FormulaPreparationView

router = DefaultRouter()
router.register('batch-log', LoadMaterialLogViewSet)  # 终端投料履历管理
router.register('replace-material', ReplaceMaterialViewSet)  # 密炼投料替换物料
router.register('return-rubber', ReturnRubberViewSet)  # 退回胶卡片打印
router.register('feeding-log', FeedingLogViewSet)  # PDA投料履历
router.register('weighting-log', WeightBatchingLogViewSet)  # 称量履历管理
router.register('weighting-package-log', WeightPackageLogViewSet)  # 称量打包履历
router.register('weighting-package-manual', WeightPackageManualViewSet)  # 人工单配(配方)
router.register('weighting-package-single', WeightPackageSingleViewSet)  # 人工单配(单一物料:配方和通用)
router.register('weighting-tack-status', WeightTankStatusViewSet)  # 料管信息
router.register('weighting-package-c', WeightPackageCViewSet)  # 打印数据获取以及状态更新(C#端)
router.register('carbon-tank-set', CarbonTankSetViewSet)  # 炭黑罐投料重量设定
router.register('feed-check-operation', FeedCheckOperationViewSet)  # 投料防错操作履历(炭黑, 粉料, 油料)
router.register('carbon-feeding-prompt', CarbonFeedingPromptViewSet)  # 炭黑罐投料提示
router.register('powder-tank-setting', PowderTankSettingViewSet, basename='powder-tank-setting')  # 粉料罐物料设定
router.register('oli-tank-setting', OilTankSettingViewSet, basename='oli-tank-setting')  # 油料罐物料设定

"""小料称量"""
router.register('xl-material', XLMaterialVIewSet)  # 小料原材料
router.register('xl-bin', XLBinVIewSet)  # 料仓
router.register('xl-plan', XLPlanVIewSet)  # 小料计划
router.register('xl-plan-c', XLPlanCViewSet)  # 小料计划(C#端)
router.register('xl-prompt', XLPromptViewSet)  # 扫码投料与提示(C#端)
router.register('tolerance-rule', ToleranceRuleViewSet)  # 技术标准-公差录入规则

urlpatterns = [
    path('', include(router.urls)),
    path('check-version/', CheckVersion.as_view()),  # 开机检查版本
    path('batch-bacisinfo/', BatchBasicInfoView.as_view()),  # 获取设备基础信息
    path('batch-productinfo/', BatchProductionInfoView.as_view()),  # 投料-获取当前班次计划信息以及当前投料信息
    path('batch-batching-info/', BatchProductBatchingVIew.as_view()),  # 投料-获取配方信息
    path('batch-equip-operation-log/', EquipOperationLogView.as_view()),  # 投料-机台停机/开机操作
    path('batching-classes-plan/', BatchingClassesEquipPlanView.as_view()),  # 配料班次计划列表
    path('weighting-package-trains/', WeightPackageTrainsView.as_view()),  # 称量打包车次列表
    path('bar-code-tank/', BarCodeTank.as_view()),
    path('batch-charge-log-list/', BatchChargeLogListViewSet.as_view()),  # 密炼投入履历
    path('weight-batching-log-list/', WeightBatchingLogListViewSet.as_view()),  # 药品投入统计
    path('product-exchange/', ProductExchange.as_view()),
    path('weighting-package-expire/', PackageExpireView.as_view()),  # 料包有效期
    path('weighting-tank-status/', WeightingTankStatus.as_view()),  # 料罐信息(C#端)
    path('tolerance-keyword/', ToleranceKeyword.as_view()),  # 公差标准[处理关键字定义、项目关键字定义、区分关键字定义]
    path('get-manual-info/', GetManualInfo.as_view()),  # 获取配方小料中需要人工配的物料种类详细信息
    path('get-material-tolerance/', GetMaterialTolerance.as_view()),  # 获取单个物料重量对应公差
    path('feed-capacity-plan/', FeedCapacityPlanView.as_view()),  # 炭黑投料提示-计划显示
    path('carbon-out-check/', CarbonOutCheckView.as_view()),  # 炭黑投料提示-出库确认
    path('power-tank-batching/', PowderTankBatchingView.as_view()),  # 粉料投料(PDA)
    path('carbon-out-task/', CarbonOutTaskView.as_view()),  # 下达炭黑出库任务
    path('xl-recipe-notice/', XlRecipeNoticeView.as_view()),  # 下传称量配方
    path('apply-halt-equip/', ApplyHaltEquipView.as_view()),  # 密炼终端停机申请
    path('formula-preparation/', FormulaPreparationView.as_view()),  # 密炼终端查看配方详细信息(备料)

    # 炭黑投料：wcs与mes交互
    path('FeedingErrorLampForCarbon/', FeedingErrorLampForCarbonView.as_view()),  # 炭黑解包方请求mes防错结果
    path('FeedingOperateResultForCarbon/', FeedingOperateResultForCarbonView.as_view()),  # 炭黑解包方回传投料结果

    # 小料称量
    path('xl-recipe/', RecipePreVIew.as_view()),  # 小料配方列表
    path('xl-recipes-info/', GetXlRecipesInfoView.as_view()),  # 小料所有机台配方列表
    path('update-flag-count/', UpdateFlagCountView.as_view()),  # 更改配方和计划中的合包设置与分包数
    path('xl-recipe-material/', RecipeMaterialVIew.as_view()),  # 小料配方原材料列表
    path('xl-report-basic/', ReportBasicView.as_view()),  # 称量车次报表列表
    path('xl-report-weight/', ReportWeightView.as_view()),  # 物料消耗报表

    path('material-info-issue/', MaterialInfoIssue.as_view()),
    path('material-details-aux/', MaterialDetailsAux.as_view())  # mes提供一个接口返回配方详情给群控
]
