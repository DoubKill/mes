from django.contrib import admin

from .models import MaterialInventory, WarehouseInfo

admin.site.register([MaterialInventory, WarehouseInfo])
