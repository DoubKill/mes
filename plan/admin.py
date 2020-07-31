from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Permission
from plan.models import ProductDayPlan, ProductClassesPlan

admin.site.register([ProductDayPlan, ProductClassesPlan])
