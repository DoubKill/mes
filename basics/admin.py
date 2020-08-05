from django.contrib import admin

# Register your models here.
from django.contrib import admin

from basics.models import GlobalCodeType, GlobalCode, WorkSchedule, ClassesDetail, WorkSchedulePlan, \
    EquipCategoryAttribute, Equip, SysbaseEquipLevel, PlanSchedule

admin.site.register(
    [GlobalCodeType, GlobalCode, WorkSchedule, ClassesDetail, WorkSchedulePlan, EquipCategoryAttribute, Equip,
     SysbaseEquipLevel, PlanSchedule])
