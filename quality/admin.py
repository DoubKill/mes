from django.contrib import admin

# Register your models here.
from quality.models import MaterialDealResult, DealSuggestion, MaterialTestResult, MaterialTestOrder, \
    MaterialDataPointIndicator, MaterialTestMethod, TestMethod, DataPoint, TestType, TestIndicator, LabelPrint, \
    ZCKJConfig, SubMachine

admin.site.register(
    [MaterialDealResult, DealSuggestion, MaterialTestResult, MaterialTestOrder, MaterialDataPointIndicator,
     MaterialTestMethod, TestMethod, DataPoint, TestType, TestIndicator, LabelPrint])


@admin.register(ZCKJConfig)
class ZCKJConfigAdmin(admin.ModelAdmin):
    list_display = ['id', 'server', 'user', 'password', 'name', 'use_flag']


@admin.register(SubMachine)
class SubMachineAdmin(admin.ModelAdmin):
    list_display = ['nj_machine', 'max_rid', 'nj_machine_no', 'machine_no']