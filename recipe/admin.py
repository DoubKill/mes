from django.contrib import admin

# Register your models here.


from recipe.models import ProductBatching, ProductInfo, Material, ProductBatchingDetail, MaterialAttribute, MaterialSupplier

admin.site.register([ProductBatching, ProductInfo, Material, ProductBatchingDetail, MaterialAttribute, MaterialSupplier])