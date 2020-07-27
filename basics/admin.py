from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Permission

from basics.models import GlobalCodeType, GlobalCode, WorkSchedule, ClassesDetail, WorkSchedulePlan,EquipCategoryAttribute,Equip, SysbaseEquipLevel
from system.models import Section, User, FunctionBlock,FunctionPermission,Function,Menu,GroupExtension

admin.site.register([GlobalCodeType, GlobalCode, WorkSchedule, ClassesDetail, WorkSchedulePlan,EquipCategoryAttribute,Equip, SysbaseEquipLevel])
admin.site.register(User,  UserAdmin)
admin.site.register([Section, FunctionBlock,FunctionPermission,Function,Menu,GroupExtension])
admin.site.register([Permission])
