from django.contrib import admin

from .models import EquipMaintenanceOrder, EquipPart, PlatformConfig

admin.site.register(
    [EquipMaintenanceOrder,EquipPart,PlatformConfig])
