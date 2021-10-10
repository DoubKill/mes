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

# 供应商管理台账
router.register('equip-supplier', EquipSupplierViewSet)

# 设备固定资产台账
router.register('equip-property', EquipPropertyViewSet)

# 设备位置区域定义
router.register('equip-area-define', EquipAreaDefineViewSet)

# 设备部位定义
router.register('equip-part-new', EquipPartNewViewSet)

# 设备部件定义
router.register('equip-component', EquipComponentViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('equip-current-status-list/', EquipCurrentStatusList.as_view()),
    path('personal_repair_statistics/', PersonalStatisticsView.as_view()),
    path('equip-maintenance-order/other/<pk>/', EquipMaintenanceOrderOtherView.as_view()),
    path('day-error-statistics/', EquipErrorDayStatisticsView.as_view()),
    path('month-error-statistics/', EquipErrorMonthStatisticsView.as_view()),
    path('week-error-statistics/', EquipErrorWeekStatisticsView.as_view()),
    path('month-error-sort/', MonthErrorSortView.as_view()),
    path('overview/', EquipOverview.as_view())
]


