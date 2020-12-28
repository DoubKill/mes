import django_filters

from plan.models import BatchingClassesPlan
from terminal.models import FeedingLog, WeightPackageLog


class BatchingClassesPlanFilter(django_filters.rest_framework.FilterSet):
    product_factory_date = django_filters.CharFilter(field_name="work_schedule_plan__plan_schedule__day_time",
                                                     help_text="日期")
    classes = django_filters.CharFilter(field_name="work_schedule_plan__classes__global_name", help_text="班次")
    weigh_type = django_filters.CharFilter(field_name='weigh_cnt_type__weigh_type', help_text='类型， 1：a, 2:b, 3:硫磺')

    class Meta:
        model = BatchingClassesPlan
        fields = ("product_factory_date", "classes", 'weigh_type')


class FeedingLogFilter(django_filters.rest_framework.FilterSet):
    date = django_filters.DateFilter(field_name="created_date__date", help_text="日期")
    feeding_port = django_filters.CharFilter(field_name="feeding_port", help_text="投料口")

    class Meta:
        model = FeedingLog
        fields = ("date", "feeding_port")


class WeightPackageLogFilter(django_filters.rest_framework.FilterSet):
    plan_batching_uid = django_filters.CharFilter(field_name="plan_batching_uid", help_text="配料计划uid")
    product_no = django_filters.CharFilter(field_name="product_no", help_text="胶料编码", lookup_expr='icontains')
    dev_type = django_filters.CharFilter(field_name="dev_type", help_text="机型")

    class Meta:
        model = WeightPackageLog
        fields = ("plan_batching_uid", "product_no", 'dev_type')

