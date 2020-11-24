from django.contrib import admin

from .models import MaterialInventory, WarehouseInfo, InventoryLog, Station, DispatchPlan, DispatchLocation, DispatchLog

admin.site.register(
    [MaterialInventory, WarehouseInfo, InventoryLog, Station, DispatchPlan, DispatchLocation, DispatchLog])
