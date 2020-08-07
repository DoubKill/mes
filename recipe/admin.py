from django.contrib import admin

# Register your models here.


from recipe.models import ProductMaster,ProductBatching,ProductInfo,Material,ProductBatchingDetail

admin.site.register([ProductMaster,ProductBatching,ProductInfo,Material,ProductBatchingDetail])