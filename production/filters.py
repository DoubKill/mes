import django_filters
from production.models import *


class TrainsFeedbacksFilter(django_filters.rest_framework.FilterSet):
    """胶料日计划过滤器"""
    plan_classes_uid = django_filters.DateTimeFilter(field_name='plan_classes_uid', help_text='日期')

    class Meta:
        model = TrainsFeedbacks
        fields = ('plan_classes_uid')
