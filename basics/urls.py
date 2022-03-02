from django.urls import include, path
from rest_framework.routers import DefaultRouter

from basics.views import GlobalCodeTypeViewSet, GlobalCodeViewSet, WorkScheduleViewSet, EquipCategoryViewSet, \
    EquipViewSet, PlanScheduleViewSet, ClassesDetailViewSet, PlanScheduleManyCreate, LocationViewSet, CurrentClassView, \
    CurrentFactoryDate

# app_name = 'basics'
router = DefaultRouter()

# 公共代码类型
router.register(r'global-types', GlobalCodeTypeViewSet)

# 公共代码
router.register(r'global-codes', GlobalCodeViewSet)

# 倒班管理
router.register(r'work_schedules', WorkScheduleViewSet)

# 设备种类
router.register(r'equips-category', EquipCategoryViewSet)

# 设备
router.register(r'equips', EquipViewSet)

# 班次下来列表接口
router.register(r'classes', ClassesDetailViewSet)

# 排班管理
router.register(r'plan-schedule', PlanScheduleViewSet)

# 位置点
router.register('location', LocationViewSet)
urlpatterns = [
    path(r'plan-schedules/', PlanScheduleManyCreate.as_view()),
    path('current_class/', CurrentClassView.as_view()),
    path('current-factory-date/', CurrentFactoryDate.as_view()),  # 根据当前时间获取工厂日期和班次
    path('', include(router.urls)),
]
