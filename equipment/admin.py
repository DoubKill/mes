from django.contrib import admin

from .models import EquipMaintenanceOrder, EquipPart, PlatformConfig, EquipWarehouseArea, EquipWarehouseLocation, EquipWarehouseOrder, EquipWarehouseOrderDetail

admin.site.register(
    [EquipMaintenanceOrder,EquipPart,PlatformConfig, EquipWarehouseArea, EquipWarehouseLocation, EquipWarehouseOrder, EquipWarehouseOrderDetail])
