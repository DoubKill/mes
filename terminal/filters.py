import django_filters

from plan.models import BatchingClassesPlan
from terminal.models import FeedingLog, WeightPackageLog, WeightTankStatus


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


class WeightTankStatusFilter(django_filters.rest_framework.FilterSet):
    tank_no = django_filters.CharFilter(field_name='tank_no', lookup_expr='icontains', help_text='料管编码')
    equip_no = django_filters.CharFilter(field_name='equip_no', lookup_expr='icontains', help_text='设备编码')
    material_no = django_filters.CharFilter(field_name='material_no', lookup_expr='icontains', help_text='物料编码')
    status = django_filters.NumberFilter(field_name='status', help_text='料管状态，1：地位  2：高位')

    class Meta:
        model = WeightTankStatus
        fields = ("tank_no", 'equip_no', 'material_no', 'status')