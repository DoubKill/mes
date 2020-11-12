from django.contrib import admin

from .models import MaterialInventory, WarehouseInfo, InventoryLog, Station

admin.site.register([MaterialInventory, WarehouseInfo, InventoryLog, Station])
