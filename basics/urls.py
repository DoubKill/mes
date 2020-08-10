from django.urls import include, path
from rest_framework.routers import DefaultRouter

from basics.views import GlobalCodeTypeViewSet, GlobalCodeViewSet, WorkScheduleViewSet, EquipCategoryViewSet, \
    EquipViewSet, ClassesDetailViewSet, PlanScheduleViewSet

# app_name = 'basics'
router = DefaultRouter()

# 公共代码类型
router.register(r'global-types', GlobalCodeTypeViewSet)

# 公共代码
router.register(r'global-codes', GlobalCodeViewSet)

# 工作日程
router.register(r'work_schedules', WorkScheduleViewSet)

# 设备种类
router.register(r'equips-category', EquipCategoryViewSet)

# 设备
router.register(r'equips', EquipViewSet)

# 班次条目
router.register(r'schedule-classes', ClassesDetailViewSet)

# 计划时间
router.register(r'plan-schedule', PlanScheduleViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
