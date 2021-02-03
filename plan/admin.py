from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Permission
from plan.models import ProductDayPlan, ProductClassesPlan, BatchingClassesPlan

admin.site.register([ProductDayPlan,BatchingClassesPlan])


@admin.register(ProductClassesPlan)
class ProductClassesPlanAdmin(admin.ModelAdmin):
    list_display = ['plan_trains', 'equip', 'classes', 'group', 'start_time', 'end_time']

    def classes(self, obj):
        return obj.work_schedule_plan.classes

    def group(self, obj):
        return obj.work_schedule_plan.group

    def start_time(self, obj):
        return obj.work_schedule_plan.start_time

    def end_time(self, obj):
        return obj.work_schedule_plan.end_time