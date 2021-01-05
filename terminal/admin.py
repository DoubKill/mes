from django.contrib import admin

# Register your models here.


from terminal.models import Terminal, TerminalLocation, Version, WeightTankStatus


@admin.register(Terminal)
class BankAdmin(admin.ModelAdmin):
    list_display = ['name', 'no', 'desc']


@admin.register(TerminalLocation)
class BankAdmin(admin.ModelAdmin):
    list_display = ['location', 'terminal', 'equip']


@admin.register(Version)
class BankAdmin(admin.ModelAdmin):
    list_display = ['type', 'number', 'desc', 'url']


@admin.register(WeightTankStatus)
class BankAdmin(admin.ModelAdmin):
    list_display = ['tank_name', 'tank_no', 'material_name',
                    'material_no', 'status', 'open_flag', 'equip_no']