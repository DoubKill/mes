import datetime

import math
from rest_framework import serializers
from rest_framework.fields import Field

from mes.base_serializer import BaseModelSerializer
from mes.conf import COMMON_READ_ONLY_FIELDS
from plan.models import ProductClassesPlan
from production.models import TrainsFeedbacks, PalletFeedbacks, EquipStatus, PlanStatus, ExpendMaterial, QualityControl, \
    OperationLog, UnReachedCapacityCause


class EquipStatusSerializer(BaseModelSerializer):
    """机台状况反馈"""

    class Meta:
        model = EquipStatus
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS


class TrainsFeedbacksBatchSerializer(BaseModelSerializer):
    """批量上传车次报表序列化器"""

    class Meta:
        model = TrainsFeedbacks
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS


class TrainsFeedbacksSerializer(BaseModelSerializer):
    """车次产出反馈"""
    equip_status = serializers.SerializerMethodField(read_only=True)
    actual_weight = serializers.SerializerMethodField(read_only=True)

    def get_equip_status(self, object):
        equip_status = {}
        plan_classes_uid = object.plan_classes_uid
        equip_no = object.equip_no
        current_trains = object.actual_trains
        equip = EquipStatus.objects.filter(plan_classes_uid=plan_classes_uid,
                                           equip_no=equip_no,
                                           current_trains=current_trains).last()
        if not equip:
            raise serializers.ValidationError("该车次数据无对应设备，请检查相关设备")
        equip_status.update(temperature=equip.temperature,
                            energy=equip.energy,
                            rpm=equip.rpm)
        return equip_status

    def get_actual_weight(self, object):
        actual = object.actual_weight
        if actual:
            if len(str(actual)) >= 5:
                return actual / 100
        return actual

    class Meta:
        model = TrainsFeedbacks
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS


class PalletFeedbacksSerializer(BaseModelSerializer):
    """托盘产出反馈"""
    stage = serializers.SerializerMethodField(read_only=True)

    def get_stage(self, object):
        plan_classes_uid = object.plan_classes_uid if object.plan_classes_uid else 0
        productclassesplan = ProductClassesPlan.objects.filter(plan_classes_uid=plan_classes_uid).first()
        if productclassesplan:
            try:
                stage = productclassesplan.product_day_plan.product_batching.stage.global_name
            except:
                stage = None
        else:
            stage = None
        return stage if stage else ""

    class Meta:
        model = PalletFeedbacks
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS


class PlanStatusSerializer(BaseModelSerializer):
    """计划状态变更"""

    class Meta:
        model = PlanStatus
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ExpendMaterialSerializer(BaseModelSerializer):
    """原材料消耗表"""

    class Meta:
        model = ExpendMaterial
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS


class OperationLogSerializer(BaseModelSerializer):
    """操作日志"""

    class Meta:
        model = OperationLog
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS


class QualityControlSerializer(BaseModelSerializer):
    """质检结果表"""

    class Meta:
        model = QualityControl
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ProductionRecordSerializer(BaseModelSerializer):
    """密炼生产履历"""
    validtime = serializers.SerializerMethodField(read_only=True)
    class_group = serializers.SerializerMethodField(read_only=True)
    margin = serializers.CharField(default=None, read_only=True)

    def get_validtime(self, object):
        end_time = object.end_time if object.end_time else 0
        validtime = end_time + datetime.timedelta(days=1)
        return validtime if validtime else ""

    def get_class_group(self, object):
        product = ProductClassesPlan.objects.filter(plan_classes_uid=object.plan_classes_uid).first()
        if product:
            group = product.work_schedule_plan.group
            return group.global_name if group else None
        else:
            return None

    class Meta:
        model = PalletFeedbacks
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS


class CollectTrainsFeedbacksSerializer(BaseModelSerializer):
    """胶料单车次时间汇总"""
    time_consuming = serializers.SerializerMethodField(read_only=True, help_text='耗时')
    interval_time = serializers.SerializerMethodField(read_only=True, help_text='间隔时间')

    def get_time_consuming(self, obj):
        if not obj.end_time or not obj.begin_time:
            return None
        return obj.end_time - obj.begin_time

    class Meta:
        model = TrainsFeedbacks
        fields = ('id', 'equip_no', 'product_no', 'actual_trains', 'time_consuming', 'classes')


class UnReachedCapacityCauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnReachedCapacityCause
        fields = ['factory_date', 'classes', 'equip_no', 'cause']


class ProductionPlanRealityAnalysisSerializer(serializers.ModelSerializer):
    plan_train_sum = serializers.SerializerMethodField()
    time_span_train_count = serializers.SerializerMethodField()
    cause = serializers.SerializerMethodField()

    class Meta:
        model = TrainsFeedbacks
        fields = ['factory_date', 'classes', 'equip_no', 'plan_train_sum', 'time_span_train_count', 'cause']

    def get_cause(self, obj):
        cause, _ = UnReachedCapacityCause.objects.get_or_create(
            factory_date=obj['factory_date'],
            classes=obj['classes'],
            equip_no=obj['equip_no'])
        return cause.cause

    def get_plan_train_sum(self, obj):
        return obj.get('plan_train_sum')

    def get_time_span_train_count(self, obj):
        hour_step = self.context.get('hour_step', 2)
        time_span_train_count = {}
        for time_span in range(hour_step, 13, hour_step):
            time_span_train_count.update({
                time_span: [math.ceil(obj.get('plan_train_sum', 0) / 12 * time_span),
                            math.ceil(obj.get('finished_train_count', 0) / 12 * time_span)]
            })
        return time_span_train_count

