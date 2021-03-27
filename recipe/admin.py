from django.contrib import admin

# Register your models here.


from recipe.models import ProductBatching, ProductInfo, Material, ProductBatchingDetail, MaterialAttribute, \
    MaterialSupplier, WeighCntType

admin.site.register([ProductBatching, ProductInfo, Material, ProductBatchingDetail,
                     MaterialAttribute, MaterialSupplier, WeighCntType])