from django.contrib import admin

from .models import EquipMaintenanceOrder,EquipPart
admin.site.register(
    [EquipMaintenanceOrder,EquipPart])
