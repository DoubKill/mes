from django.contrib import admin

# Register your models here.
from production.models import TrainsFeedbacks, PalletFeedbacks, LocationPoint

admin.site.register([TrainsFeedbacks])
admin.site.register(PalletFeedbacks)
admin.site.register(LocationPoint)