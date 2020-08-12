import django_filters
from production.models import *


class TrainsFeedbacksFilter(django_filters.rest_framework.FilterSet):
    """车次产出反馈过滤器"""
    plan_classes_uid = django_filters.CharFilter(field_name='plan_classes_uid', help_text='班次计划唯一码')
    equip_no = django_filters.CharFilter(field_name='equip_no', help_text='机号')
    product_no = django_filters.CharFilter(field_name='product_no', help_text='产出胶料编号')

    class Meta:
        model = TrainsFeedbacks
        fields = ('plan_classes_uid', 'equip_no', 'product_no', 'actual_trains')


class PalletFeedbacksFilter(django_filters.rest_framework.FilterSet):
    """托盘产出反馈过滤器"""
    plan_classes_uid = django_filters.CharFilter(field_name='plan_classes_uid', help_text='班次计划唯一码')
    equip_no= django_filters.CharFilter(field_name='equip_no', help_text='机号')
    product_no = django_filters.CharFilter(field_name='product_no', help_text='产出胶料编号')

    class Meta:
        model = PalletFeedbacks
        fields = ('plan_classes_uid', 'equip_no', 'product_no')


class EquipStatusFilter(django_filters.rest_framework.FilterSet):
    """机台状态反馈过滤器"""
    plan_classes_uid = django_filters.CharFilter(field_name='plan_classes_uid', help_text='班次计划唯一码')
    equip_no = django_filters.CharFilter(field_name='equip_no', help_text='机号')
    # product_no = django_filters.CharFilter(field_name='product_no', help_text='产出胶料编号')

    class Meta:
        model = EquipStatus
        fields = ('plan_classes_uid', 'current_trains')


class PlanStatusFilter(django_filters.rest_framework.FilterSet):
    """计划状态过滤器"""
    plan_classes_uid = django_filters.CharFilter(field_name='plan_classes_uid', help_text='班次计划唯一码')

    class Meta:
        model = PlanStatus
        fields = ('plan_classes_uid',)


class ExpendMaterialFilter(django_filters.rest_framework.FilterSet):
    """原材料消耗过滤器"""
    plan_classes_uid = django_filters.CharFilter(field_name='plan_classes_uid', help_text='班次计划唯一码')

    class Meta:
        model = ExpendMaterial
        fields = ('plan_classes_uid',)


class QualityControlFilter(django_filters.rest_framework.FilterSet):
    """质量检测结果过滤器"""
    barcode = django_filters.CharFilter(field_name='barcode', help_text='班次计划唯一码')

    class Meta:
        model = QualityControl
        fields = ('barcode',)
