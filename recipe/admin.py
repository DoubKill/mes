from django.contrib import admin

# Register your models here.
from recipe.models import ProductMaster

admin.site.register([ProductMaster])