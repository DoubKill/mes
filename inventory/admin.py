from django.contrib import admin

from .models import MaterialInventory, WarehouseInfo, InventoryLog, Station, DispatchPlan, DispatchLocation, \
    DispatchLog, MixGumOutInventoryLog, BzFinalMixingRubberInventory, BzFinalMixingRubberInventoryLB, WmsInventoryStock, \
    WarehouseMaterialType, DeliveryPlan

admin.site.register(
    [MaterialInventory, WarehouseInfo, InventoryLog, Station, DispatchPlan, DispatchLocation, DispatchLog,
     MixGumOutInventoryLog,BzFinalMixingRubberInventory,BzFinalMixingRubberInventoryLB,WmsInventoryStock,WarehouseMaterialType,DeliveryPlan])
