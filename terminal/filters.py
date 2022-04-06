import django_filters

from plan.models import BatchingClassesEquipPlan
from terminal.models import FeedingLog, WeightPackageLog, WeightTankStatus, LoadMaterialLog, WeightBatchingLog, \
    CarbonTankFeedWeightSet, FeedingOperationLog, ReplaceMaterial, ReturnRubber, WeightPackageManual, \
    WeightPackageSingle


class BatchingClassesEquipPlanFilter(django_filters.rest_framework.FilterSet):
    product_factory_date = django_filters.CharFilter(
        field_name="batching_class_plan__work_schedule_plan__plan_schedule__day_time",
        help_text="日期")
    classes = django_filters.CharFilter(field_name="batching_class_plan__work_schedule_plan__classes__global_name",
                                        help_text="班次")
    equip_no = django_filters.CharFilter(field_name="equip__equip_no", help_text="机台编号")

    class Meta:
        model = BatchingClassesEquipPlan
        fields = ("product_factory_date", "classes", 'equip_no')


class FeedingLogFilter(django_filters.rest_framework.FilterSet):
    date = django_filters.DateFilter(field_name="created_date__date", help_text="日期")
    feeding_port = django_filters.CharFilter(field_name="feeding_port", help_text="投料口")

    class Meta:
        model = FeedingLog
        fields = ("date", "feeding_port")


class WeightTankStatusFilter(django_filters.rest_framework.FilterSet):
    tank_no = django_filters.CharFilter(field_name='tank_no', lookup_expr='icontains', help_text='料管编码')
    equip_no = django_filters.CharFilter(field_name='equip_no', lookup_expr='icontains', help_text='设备编码')
    material_no = django_filters.CharFilter(field_name='material_no', lookup_expr='icontains', help_text='物料编码')
    status = django_filters.NumberFilter(field_name='status', help_text='料管状态，1：低位  2：高位')

    class Meta:
        model = WeightTankStatus
        fields = ("tank_no", 'equip_no', 'material_no', 'status')


class LoadMaterialLogFilter(django_filters.rest_framework.FilterSet):
    production_factory_date = django_filters.DateFilter(field_name='feed_log__production_factory_date',
                                                        help_text='工厂时间')
    equip_no = django_filters.CharFilter(field_name='feed_log__equip_no', lookup_expr='icontains', help_text='设备编码')
    production_classes = django_filters.CharFilter(field_name='feed_log__production_classes', lookup_expr='icontains',
                                                   help_text='生产班次')
    material_no = django_filters.CharFilter(field_name='material_no', help_text='原材料编码/投入编码',
                                            lookup_expr='icontains')
    plan_classes_uid = django_filters.CharFilter(field_name='feed_log__plan_classes_uid', help_text='计划编号')

    class Meta:
        model = LoadMaterialLog
        fields = ("production_factory_date", 'equip_no', 'production_classes', 'material_no')


class WeightBatchingLogListFilter(django_filters.rest_framework.FilterSet):
    batch_time = django_filters.DateFilter(field_name='batch_time__date', help_text='工厂时间')
    tank_no = django_filters.CharFilter(field_name='tank_no', help_text='罐号')
    equip_no = django_filters.CharFilter(field_name='equip_no', help_text='投入设备')
    batch_classes = django_filters.CharFilter(field_name='batch_classes', help_text='投入班次', lookup_expr='icontains')
    bra_code = django_filters.CharFilter(field_name='bra_code', help_text='条码', lookup_expr='icontains')
    material_name = django_filters.CharFilter(field_name='material_name', help_text='物料名', lookup_expr='icontains')
    created_username = django_filters.CharFilter(field_name='created_user__username', help_text='操作人', lookup_expr='icontains')

    class Meta:
        model = WeightBatchingLog
        fields = ('equip_no', 'batch_classes', 'tank_no', 'batch_time', 'material_name', 'bra_code', 'created_username')


class CarbonTankSetFilter(django_filters.rest_framework.FilterSet):
    equip_id = django_filters.CharFilter(field_name='equip_id', help_text='密炼机台号', lookup_expr='icontains')
    tank_no = django_filters.NumberFilter(field_name='tank_no', help_text='罐号')

    class Meta:
        model = CarbonTankFeedWeightSet
        fields = ('equip_id', 'tank_no')


class FeedingOperationLogFilter(django_filters.rest_framework.FilterSet):
    feeding_type = django_filters.ChoiceFilter(choices=FeedingOperationLog.TYPE_CHOICE, help_text='投料区分')
    feeding_port_no = django_filters.CharFilter(field_name='feeding_port_no', lookup_expr='icontains', help_text='投料口')
    feeding_time = django_filters.DateFromToRangeFilter(field_name='feeding_time__date', lookup_expr='range', help_text='投料时间')
    feeding_classes = django_filters.CharFilter(field_name='feeding_classes', lookup_expr='icontains', help_text='投料班次')
    feed_result = django_filters.CharFilter(field_name='feed_result', lookup_expr='icontains', help_text='防错结果')
    feeding_username = django_filters.CharFilter(field_name='feeding_username', lookup_expr='icontains', help_text='投料人员')

    class Meta:
        model = FeedingOperationLog
        fields = ('feeding_type', 'feeding_port_no', 'feeding_time', 'feeding_classes', 'feed_result', 'feeding_username')


class ReplaceMaterialFilter(django_filters.rest_framework.FilterSet):
    plan_classes_uid = django_filters.CharFilter(field_name='plan_classes_uid', lookup_expr='icontains', help_text='计划号')
    product_no = django_filters.CharFilter(field_name='product_no', lookup_expr='icontains', help_text='胶料配方')
    real_material = django_filters.CharFilter(field_name='real_material', lookup_expr='icontains', help_text='实际投入物料')
    bra_code = django_filters.CharFilter(field_name='bra_code', lookup_expr='icontains', help_text='实际投入物料条码')

    class Meta:
        model = ReplaceMaterial
        fields = ('id', 'plan_classes_uid', 'product_no', 'real_material', 'bra_code', 'status', 'equip_no', 'reason_type')


class ReturnRubberFilter(django_filters.rest_framework.FilterSet):
    bra_code = django_filters.CharFilter(field_name='bra_code', lookup_expr='icontains', help_text='卡片条码')
    product_no = django_filters.CharFilter(field_name='product_no', lookup_expr='icontains', help_text='胶料配方')

    class Meta:
        model = ReturnRubber
        fields = ('product_no', 'bra_code', 'print_type', 'status')
