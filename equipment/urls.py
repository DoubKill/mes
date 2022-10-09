from django.urls import include, path
from rest_framework.routers import DefaultRouter

from equipment.models import XLCommonCode
from equipment.views import *


router = DefaultRouter()

router.register(r"equip_realtime", EquipRealtimeViewSet)


# 设备停机类型
router.register('equip-down-type', EquipDownTypeViewSet)

# 设备停机原因
router.register('equip-down-reason', EquipDownReasonViewSet)

# 设备现况
router.register('equip-current-status', EquipCurrentStatusViewSet)

# 设备部位
router.register('equip-part', EquipPartViewSet)

# 维修表单
router.register('equip-maintenance-order', EquipMaintenanceOrderViewSet)

# 资产类型节点
router.register('property-type-node', PropertyTypeNodeViewSet)

# 资产
router.register('property', PropertyViewSet)

# 通知配置
router.register('platform-config', PlatformConfigViewSet)

# 设备维修履历
router.register('equip-maintenance-order-log', EquipMaintenanceOrderLogViewSet)


# **************************2021-10-09最新URL**************************

# 供应商管理台账
router.register('equip-supplier', EquipSupplierViewSet)

# 设备固定资产台账
router.register('equip-property', EquipPropertyViewSet)

# 设备位置区域定义
router.register('equip-area-define', EquipAreaDefineViewSet)

# 设备部位定义
router.register('equip-part-new', EquipPartNewViewSet)

# 设备部件分类
router.register('equip-component-type', EquipComponentTypeViewSet)

# 设备部件定义
router.register('equip-component', EquipComponentViewSet)

# 部件与erp备件关系
router.register('erp-spare-component-relation', ERPSpareComponentRelationViewSet)

# erp备件物料信息
router.register('equip-spare-erp', EquipSpareErpViewSet)

# 设备BOM管理
router.register('equip-bom', EquipBomViewSet)

# 设备故障分类类型
router.register(r'equip-fault-types', EquipFaultTypeViewSet)

# 设备故障分类
router.register(r'equip-fault-codes', EquipFaultCodeViewSet)

# 设备故障信号
router.register('equip-fault-signal', EquipFaultSignalViewSet)
# 设备停机类型
router.register('equip-machine-halt-type', EquipMachineHaltTypeViewSet)
# 设备停机原因
router.register('equip-machine-halt-reason', EquipMachineHaltReasonViewSet)
# 工单指派规则
router.register('equip-order-assign-rule', EquipOrderAssignRuleViewSet)
# 维护包干设置
router.register('equip-maintenance-area-settings', EquipMaintenanceAreaSettingViewSet)

# 设备作业项目标准定义
router.register('equip-job-item-standard', EquipJobItemStandardViewSet)

# 设备维护作业标准定义
router.register('equip_maintenance_standard', EquipMaintenanceStandardViewSet)

# 设备维修作业标准定义
router.register('equip-repair-standard', EquipRepairStandardViewSet)

# 备件库库区
router.register('equip-warehouse-area', EquipWarehouseAreaViewSet)

# 备件库库位
router.register('equip-warehouse-location', EquipWarehouseLocationViewSet)

# 备件入出库单据
router.register('equip-warehouse-order', EquipWarehouseOrderViewSet)

# 备件库出入库管理
router.register('equip-warehouse-order-detail', EquipWarehouseOrderDetailViewSet, basename='equip-warehouse-order-detail')

# 备件库库存查询
router.register('equip-warehouse-inventory', EquipWarehouseInventoryViewSet)

# 备件库出入库履历查询
router.register('equip-warehouse-record', EquipWarehouseRecordViewSet, basename='equip-warehouse-record')

# 入出库统计分析
router.register('equip-warehouse-statistical', EquipWarehouseStatisticalViewSet)

# 设备报修申请
router.register('equip-apply-repair', EquipApplyRepairViewSet)

# 设备维修工单查询
router.register('equip-apply-order', EquipApplyOrderViewSet)

# 设备巡检工单查询
router.register('equip-inspection-order', EquipInspectionOrderViewSet)

# 维修物料申请
router.register('equip-repair-material-req', EquipRepairMaterialReqViewSet)

# 图片上传
router.register('upload-images', UploadImageViewSet)

# 设备维护维修计划
router.register('equip-plan', EquipPlanViewSet)

# 日清扫标准
router.register('daily-clean-standard', DailyCleanStandardViewSet)

# 日清扫表
router.register('daily-clean-table', DailyCleanTableViewSet)

# 岗位安全装置点检标准
router.register('check-point-standard', CheckPointStandardViewSet)

# 岗位安全装置点检表
router.register('check-point-table', CheckPointTableViewSet)

# 除尘袋滤器温度标准
router.register('check-temperature-standard', CheckTemperatureStandardViewSet)

# 除尘袋滤器温度检查表
router.register('check-temperature-table', CheckTemperatureTableViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('equip-current-status-list/', EquipCurrentStatusList.as_view()),
    path('personal_repair_statistics/', PersonalStatisticsView.as_view()),
    path('equip-maintenance-order/other/<pk>/', EquipMaintenanceOrderOtherView.as_view()),
    path('day-error-statistics/', EquipErrorDayStatisticsView.as_view()),
    path('month-error-statistics/', EquipErrorMonthStatisticsView.as_view()),
    path('week-error-statistics/', EquipErrorWeekStatisticsView.as_view()),
    path('month-error-sort/', MonthErrorSortView.as_view()),
    path('overview/', EquipOverview.as_view()),
    path('get-default-code/', GetDefaultCodeView.as_view()),
    path('get-staff/', GetStaffsView.as_view()),

    # **************************2021-10-09最新URL**************************
    # 机台目标MTBF/MTTR设定
    path('equip-target-mtbmttr-settings/', EquipTargetMTBFMTTRSettingView.as_view()),
    # 备件PDA出入库
    path('equip-auto-plan/', EquipAutoPlanView.as_view()),
    # 条码打印
    path('equip-code-print/', EquipCodePrintView.as_view()),
    # 钉钉工单查询
    path('equip-order-list/', EquipOrderListView.as_view()),
    # MTBF/MTTR分析报表
    path('equip-mtbfmttp-statement/', EquipMTBFMTTPStatementView.as_view()),
    # 工单别 处理时间分析报表
    path('equip-workorder-statement/', EquipWorkOrderStatementView.as_view()),
    # 机台别 处理时间分析报表
    path('equip-statement/', EquipStatementView.as_view()),
    # 人员别 处理时间分析报表
    path('equip-user-statement/', EquipUserStatementView.as_view()),
    # 期间别 处理时间分析报表
    path('equip-period-statement/', EquipPeriodStatementView.as_view()),
    # 工单按时完成率报表
    path('equip-finishing-rate/', EquipFinishingRateView.as_view()),
    # 交旧率报表
    path('equip-old-rate/', EquipOldRateView.as_view()),
    # 同步erp接口
    path('get-spare/', GetSpare.as_view()),
    # 获取备件入库单据接口
    path('get-spare-order/', GetSpareOrder.as_view()),
    # 委托工单与查询
    path('equip-order-entrust/', EquipOrderEntrustView.as_view()),
    # 通用料包条码
    path('xl-common-code/', XLCommonCodeView.as_view()),

    path('index/', EquipIndexView.as_view())

]


