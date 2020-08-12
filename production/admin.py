from django.contrib import admin

# Register your models here.
from production.models import TrainsFeedbacks

admin.site.register([TrainsFeedbacks])