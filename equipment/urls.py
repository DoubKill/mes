from django.urls import include, path
from rest_framework.routers import DefaultRouter

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
#
# # 备件库库区
# router.register('equip-warehouse-area', EquipWarehouseAreaViewSet)

# # 备件库库位
# router.register('equip-warehouse-location', EquipWarehouseLocationViewSet)

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

    # **************************2021-10-09最新URL**************************
    # 机台目标MTBF/MTTR设定
    path('equip-target-mtbmttr-settings/', EquipTargetMTBFMTTRSettingView.as_view()),
    # 备件PDA出入库
    path('equip-auto-plan/', EquipAutoPlanView.as_view())
]


