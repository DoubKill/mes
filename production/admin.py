from django.contrib import admin

# Register your models here.
from production.models import TrainsFeedbacks, PalletFeedbacks

admin.site.register([TrainsFeedbacks])
admin.site.register(PalletFeedbacks)

