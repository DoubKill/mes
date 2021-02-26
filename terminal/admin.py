from django.contrib import admin

# Register your models here.


from terminal.models import Terminal, TerminalLocation, Version, WeightTankStatus, MaterialSupplierCollect, WeightBatchingLog


@admin.register(Terminal)
class TerminalAdmin(admin.ModelAdmin):
    list_display = ['name', 'no', 'desc']


@admin.register(TerminalLocation)
class TerminalLocationAdmin(admin.ModelAdmin):
    list_display = ['location', 'terminal', 'equip']


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    list_display = ['type', 'number', 'desc', 'url']


@admin.register(WeightTankStatus)
class WeightTankStatusAdmin(admin.ModelAdmin):
    list_display = ['tank_name', 'tank_no', 'material_name',
                    'material_no', 'status', 'open_flag', 'equip_no']


@admin.register(MaterialSupplierCollect)
class MaterialSupplierCollectAdmin(admin.ModelAdmin):
    list_display = ['bra_code', 'material_name', 'material_no', 'batch_no']


admin.site.register(WeightBatchingLog)

