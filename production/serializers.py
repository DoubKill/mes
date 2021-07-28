import datetime

import math
from rest_framework import serializers
from rest_framework.fields import Field

from mes.base_serializer import BaseModelSerializer
from mes.conf import COMMON_READ_ONLY_FIELDS
from plan.models import ProductClassesPlan
from production.models import TrainsFeedbacks, PalletFeedbacks, EquipStatus, PlanStatus, ExpendMaterial, QualityControl, \
    OperationLog, UnReachedCapacityCause, ProcessFeedback, AlarmLog


class EquipStatusSerializer(BaseModelSerializer):
    """机台状况反馈"""
    plan_classes_uid = serializers.CharField(allow_null=True, allow_blank=True)
    equip_no = serializers.CharField(allow_null=True, allow_blank=True)
    status = serializers.CharField(allow_null=True, allow_blank=True)

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


class ProcessFeedbackSerializer(BaseModelSerializer):
    """步序反馈报表"""

    class Meta:
        model = ProcessFeedback
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS


class AlarmLogSerializer(BaseModelSerializer):
    """步序反馈报表"""

    class Meta:
        model = AlarmLog
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

    def get_interval_time(self, obj):
        if obj.actual_trains > 1:
            actual_trains = obj.actual_trains - 1
            tfb_obj = TrainsFeedbacks.objects.filter(plan_classes_uid=obj.plan_classes_uid,
                                                     actual_trains=actual_trains).last()
            if tfb_obj:
                return obj.begin_time - tfb_obj.end_time
            else:
                return 0
        elif obj.actual_trains == 1:
            tfb_obj = TrainsFeedbacks.objects.filter(equip_no=obj.equip_no, id__lt=obj.id).last()
            if tfb_obj:
                return obj.begin_time - tfb_obj.end_time
            else:
                return 0

    class Meta:
        model = TrainsFeedbacks
        fields = ('id', 'equip_no', 'product_no', 'actual_trains', 'time_consuming', 'classes', 'interval_time')


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


# 将群控的车次报表直接移植过来
class TrainsFeedbacksSerializer2(BaseModelSerializer):
    """车次产出反馈"""
    status = serializers.SerializerMethodField(read_only=True)
    actual_weight = serializers.SerializerMethodField(read_only=True)
    mixer_time = serializers.SerializerMethodField(read_only=True)

    def get_mixer_time(self, obj):
        try:
            return obj.end_time - obj.begin_time
        except:
            return None

    def get_actual_weight(self, obj):
        if not obj.actual_weight:
            return None
        else:
            return str(obj.actual_weight / 100)

    def get_status(self, object):
        ps_obj = PlanStatus.objects.filter(equip_no=object.equip_no,
                                           plan_classes_uid=object.plan_classes_uid,
                                           product_no=object.product_no,
                                           actual_trains=object.actual_trains).order_by('product_time').last()
        if ps_obj:
            status = ps_obj.status
        else:
            status = None
        return status

    class Meta:
        model = TrainsFeedbacks
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS


class CurveInformationSerializer(serializers.ModelSerializer):
    """工艺曲线信息"""

    class Meta:
        model = EquipStatus
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class MixerInformationSerializer2(serializers.ModelSerializer):
    """密炼信息"""

    class Meta:
        model = ProcessFeedback
        fields = "__all__"


class WeighInformationSerializer2(serializers.ModelSerializer):
    """称量信息"""

    class Meta:
        model = ExpendMaterial
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class TrainsFixSerializer(serializers.Serializer):
    factory_date = serializers.DateField(required=False)
    classes = serializers.CharField(required=False)
    equip_no = serializers.CharField(required=False)
    product_no = serializers.CharField(required=False)
    begin_trains = serializers.IntegerField(min_value=1)
    end_trains = serializers.IntegerField(min_value=1)
    fix_num = serializers.IntegerField(required=False)
    lot_no = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        begin_trains = attrs['begin_trains']
        end_trains = attrs['end_trains']
        if begin_trains > end_trains:
            raise serializers.ValidationError('开始车次不得大于结束车次')
        return attrs