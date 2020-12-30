from django.contrib import admin

# Register your models here.
from production.models import TrainsFeedbacks, PalletFeedbacks, LocationPoint

admin.site.register([TrainsFeedbacks])
admin.site.register(PalletFeedbacks)


@admin.register(LocationPoint)
class BankAdmin(admin.ModelAdmin):
    list_display = ['name', 'no', 'location_type', 'img_url', 'desc']