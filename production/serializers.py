import datetime

import math

from django.db.models import Q
from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.validators import UniqueValidator, UniqueTogetherValidator

from mes.base_serializer import BaseModelSerializer
from mes.common_code import days_cur_month_dates
from mes.conf import COMMON_READ_ONLY_FIELDS
from plan.models import ProductClassesPlan
from production.models import TrainsFeedbacks, PalletFeedbacks, EquipStatus, PlanStatus, ExpendMaterial, QualityControl, \
    OperationLog, UnReachedCapacityCause, ProcessFeedback, AlarmLog, RubberCannotPutinReason, PerformanceJobLadder, \
    ProductInfoDingJi, SetThePrice, SubsidyInfo, AttendanceGroupSetup, EmployeeAttendanceRecords, FillCardApply, \
    ApplyForExtraWork, Equip190EWeight, OuterMaterial, Equip190E, AttendanceClockDetail, EmployeeAttendanceRecordsLog, \
    WeightClassPlan, WeightClassPlanDetail, EquipDownDetails
from recipe.models import MaterialAttribute
from system.models import User
from terminal.utils import get_current_factory_date


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

    def create(self, validated_data):
        if 'classes' in validated_data and 'plan_classes_uid' in validated_data:
            if not validated_data['classes']:
                ps = ProductClassesPlan.objects.filter(plan_classes_uid=validated_data['plan_classes_uid']).first()
                if ps:
                    validated_data['classes'] = ps.work_schedule_plan.classes.global_name
        if validated_data['equip_no'] != 'Z04':
            if TrainsFeedbacks.objects.filter(plan_classes_uid=validated_data['plan_classes_uid'],
                                              actual_trains=validated_data['actual_trains']).exists():
                return validated_data
        else:
            if TrainsFeedbacks.objects.filter(plan_classes_uid=validated_data['plan_classes_uid'],
                                              actual_trains=validated_data['actual_trains'],
                                              operation_user=validated_data.get('operation_user')).exists():
                return validated_data
        return super().create(validated_data)

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
        # 2023-05-19 排胶温度从车次报表中获取
        try:
            if equip_no == 'Z01':
                energy = round(object.evacuation_energy / 10, 1)
            elif equip_no == 'Z02':
                energy = round(object.evacuation_energy / 0.6, 1)
            elif equip_no == 'Z04':
                energy = round(object.evacuation_energy * 0.28 * object.plan_weight / 1000, 1)
            elif equip_no == 'Z12':
                energy = round(object.evacuation_energy / 5.3, 1)
            elif equip_no == 'Z13':
                energy = round(object.evacuation_energy / 31.7, 1)
            else:
                energy = round(object.evacuation_energy, 1)
        except:
            energy = 0
        equip_status.update(temperature=object.temperature, energy=energy, rpm=equip.rpm)
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

    def create(self, validated_data):
        instance = PalletFeedbacks.objects.filter(lot_no=validated_data['lot_no']).first()
        if instance:
            return instance
        begin_trains = validated_data['begin_trains']
        end_trains = validated_data['end_trains']
        actual_weight = validated_data['actual_weight']
        pallet_no = validated_data.get('pallet_no')
        if begin_trains <= 0 or end_trains <= 0 or actual_weight <= 0:
            return validated_data
        if pallet_no == '0':
            return validated_data
        return super().create(validated_data)

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
        return (obj.end_time - obj.begin_time).total_seconds()

    def get_interval_time(self, obj):
        if obj.actual_trains > 1:
            actual_trains = obj.actual_trains - 1
            tfb_obj = TrainsFeedbacks.objects.filter(plan_classes_uid=obj.plan_classes_uid,
                                                     actual_trains=actual_trains).last()
            if tfb_obj:
                return (obj.begin_time - tfb_obj.end_time).total_seconds()
            else:
                return 0
        elif obj.actual_trains == 1:
            tfb_obj = TrainsFeedbacks.objects.filter(equip_no=obj.equip_no, id__lt=obj.id).order_by('-id').first()
            if tfb_obj:
                return (obj.begin_time - tfb_obj.end_time).total_seconds()
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
    actual_weight = serializers.SerializerMethodField(read_only=True)
    mixer_time = serializers.SerializerMethodField(read_only=True)
    ai_value = serializers.SerializerMethodField(read_only=True)

    def get_ai_value(self, obj):
        irm_queryset = ProcessFeedback.objects.filter(
            Q(plan_classes_uid=obj.plan_classes_uid,
              equip_no=obj.equip_no,
              product_no=obj.product_no,
              current_trains=obj.actual_trains)
            &
            ~Q(Q(condition='') | Q(condition__isnull=True))
        ).exclude(condition__in=('配方结束', '同时执行')).order_by('-sn').first()
        if irm_queryset:
            return irm_queryset.power
        return None

    def to_representation(self, instance):
        data = super(TrainsFeedbacksSerializer2, self).to_representation(instance)
        evacuation_energy = data['evacuation_energy']
        equip_no = data['equip_no']
        actual_weight = data['actual_weight']
        try:
            if equip_no == 'Z01':
                data['evacuation_energy'] = round(evacuation_energy / 10, 1)
            if equip_no == 'Z02':
                data['evacuation_energy'] = round(evacuation_energy / 0.6)
            if equip_no == 'Z04':
                data['evacuation_energy'] = round(evacuation_energy * 0.28 * float(actual_weight) / 1000, 1)
            if equip_no == 'Z12':
                data['evacuation_energy'] = round(evacuation_energy / 5.3, 1)
            if equip_no == 'Z13':
                data['evacuation_energy'] = round(evacuation_energy / 31.7, 1)
        except Exception:
            pass
        return data

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


class PalletFeedbacksBatchModifySerializer(BaseModelSerializer):

    class Meta:
        model = PalletFeedbacks
        fields = ('id', 'begin_trains', 'end_trains', 'lot_no', 'product_no', 'actual_weight')
        extra_kwargs = {'id': {'read_only': False}}


class ProductPlanRealViewSerializer(serializers.ModelSerializer):
    actual_trains = serializers.SerializerMethodField(read_only=True, help_text='实际车次')
    classes = serializers.CharField(source='work_schedule_plan.classes.global_name', read_only=True, help_text='班次')
    product_no = serializers.CharField(source='product_batching.stage_product_batch_no', read_only=True)
    begin_time = serializers.SerializerMethodField(read_only=True, help_text='开始时间')

    def get_begin_time(self, obj):
        tfb_obj = TrainsFeedbacks.objects.filter(plan_classes_uid=obj.plan_classes_uid).order_by('actual_trains').first()
        if tfb_obj:
            return tfb_obj.begin_time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return None

    def get_actual_trains(self, obj):
        tfb_obj = TrainsFeedbacks.objects.filter(plan_classes_uid=obj.plan_classes_uid).order_by('actual_trains').last()
        if tfb_obj:
            return tfb_obj.actual_trains
        else:
            return 0

    class Meta:
        model = ProductClassesPlan
        fields = ('classes', 'plan_trains', 'actual_trains', 'product_no', 'begin_time')


class RubberCannotPutinReasonSerializer(serializers.ModelSerializer):
    input_datetime = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    factory_date = serializers.DateTimeField(format='%Y-%m-%d', read_only=True)
    trains = serializers.SerializerMethodField()

    def get_trains(self, obj):
        if all([obj.begin_trains, obj.end_trains]):
            if obj.begin_trains == obj.end_trains:
                return obj.begin_trains
            return '{}-{}'.format(obj.begin_trains, obj.end_trains)
        elif obj.begin_trains:
            return obj.begin_trains
        elif obj.end_trains:
            return obj.end_trains
        else:
            return ''

    class Meta:
        model = RubberCannotPutinReason
        fields = '__all__'


class PerformanceJobLadderSerializer(serializers.ModelSerializer):
    code = serializers.CharField(default='GW0001')
    post_standard_name = serializers.SerializerMethodField()

    class Meta:
        model = PerformanceJobLadder
        fields = '__all__'

    def create(self, validated_data):
        if PerformanceJobLadder.objects.exists():
            code = int(PerformanceJobLadder.objects.last().code[2:]) + 1
            code = 'GW%.4d' % code
            validated_data['code'] = code
        instance = super().create(validated_data)
        return instance

    def get_post_standard_name(self, obj):
        return obj.get_post_standard_display()


class ProductInfoDingJiSerializer(BaseModelSerializer):
    username = serializers.ReadOnlyField(source='created_user__username')

    class Meta:
        model = ProductInfoDingJi
        fields = '__all__'


class SetThePriceSerializer(serializers.ModelSerializer):

    class Meta:
        model = SetThePrice
        fields = '__all__'

    def create(self, validated_data):
        instance = SetThePrice.objects.first()
        if instance:
            super().update(instance, validated_data)
        else:
            instance = super().create(validated_data)
        return instance


class SubsidyInfoSerializer(serializers.ModelSerializer):

    class Meta:
        model = SubsidyInfo
        fields = '__all__'


class AttendanceGroupSetupSerializer(serializers.ModelSerializer):
    attendance_users = serializers.SerializerMethodField()
    work_schedule_name = serializers.ReadOnlyField(source='work_schedule.schedule_name', help_text='倒班名称')

    class Meta:
        model = AttendanceGroupSetup
        validators = [UniqueTogetherValidator(queryset=AttendanceGroupSetup.objects.all(), fields=('type', 'group'), message='类别+班组重复')]
        fields = '__all__'

    def update(self, instance, validated_data):
        users = validated_data.pop('users', None)  # [1, 2]
        instance.users.clear()
        instance.users.add(*users)
        super().update(instance, validated_data)
        return instance

    def create(self, validated_data):
        users = validated_data.pop('users', None)
        instance = super().create(validated_data)
        instance.users.add(*users)
        return instance

    def get_attendance_users(self, obj):
        user_list = list(obj.users.all().values_list('username', flat=True))
        res = ','.join(user_list)
        return res


class EmployeeAttendanceRecordsSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', default=None)

    class Meta:
        model = EmployeeAttendanceRecords
        fields = '__all__'

    def validate(self, attrs):
        user = attrs.pop('user')
        attrs['user'] = User.objects.filter(username=user.get('username')).first()
        return attrs

    def create(self, validated_data):
        # 已经确认过或者整体提交不能添加考勤数据 黑色[#141414]
        r_exist = EmployeeAttendanceRecords.objects.filter(factory_date=validated_data['factory_date'],
                                                           group=validated_data['group'],
                                                           equip=validated_data['equip'],
                                                           section=validated_data['section'],
                                                           user=validated_data['user'],
                                                           record_status__in=['#141414'])
        if r_exist:
            raise serializers.ValidationError('添加失败: 该考勤数据已锁定!')
        return super().create(validated_data)


class FillCardApplySerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    id_card_num = serializers.SerializerMethodField()

    class Meta:
        model = FillCardApply
        fields = '__all__'

    def get_username(self, obj):
        return obj.user.username

    def get_id_card_num(self, obj):
        return obj.user.id_card_num


class ApplyForExtraWorkSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    id_card_num = serializers.SerializerMethodField()

    class Meta:
        model = ApplyForExtraWork
        fields = '__all__'

    def get_username(self, obj):
        return obj.user.username

    def get_id_card_num(self, obj):
        return obj.user.id_card_num


class Equip190EWeightSerializer(serializers.ModelSerializer):
    specification = serializers.CharField(source='setup.specification', read_only=True)
    state = serializers.CharField(source='setup.state', read_only=True)
    weight = serializers.CharField(source='setup.weight', read_only=True)

    class Meta:
        model = Equip190EWeight
        fields = '__all__'


class OuterMaterialSerializer(serializers.ModelSerializer):

    class Meta:
        model = OuterMaterial
        fields = '__all__'


class Equip190ESerializer(serializers.ModelSerializer):
    class Meta:
        model = Equip190E
        fields = '__all__'

    def create(self, validated_data):
        specification = validated_data['specification']
        state = validated_data['state']
        if Equip190E.objects.filter(specification=specification, state=state).exists():
            raise serializers.ValidationError(f"{specification}  {state}已存在")
        return super().create(validated_data)


class EquipStatusBatchSerializer(BaseModelSerializer):
    """机台状况反馈"""

    class Meta:
        model = EquipStatus
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class AttendanceClockDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = AttendanceClockDetail
        fields = '__all__'


class EmployeeAttendanceRecordsLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmployeeAttendanceRecordsLog
        fields = '__all__'


class WeightClassPlanSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    weight_class_details = serializers.DictField(default={}, write_only=True)

    def to_representation(self, instance):
        res = super().to_representation(instance)
        details = instance.weight_class_details.all()
        weight_class_details = {}
        for i in details:
            m, d = i.factory_date.split('-')[-2:]
            if m.startswith('0'):
                m = m[-1]
            if d.startswith('0'):
                d = d[-1]
            weight_class_details[f'{m}/{d}'] = i.class_code
        res['weight_class_details'] = weight_class_details
        return res

    @atomic
    def create(self, validated_data):
        target_month = validated_data['target_month']
        now_factory_date = get_current_factory_date()['factory_date']
        weight_class_details = validated_data.pop('weight_class_details')
        instance = super().create(validated_data)
        details = []
        if weight_class_details:
            for k, v in weight_class_details.items():
                class_date = target_month + '-' + '%02d' % int(k.split('/')[-1])
                if class_date < now_factory_date.strftime('%Y-%m-%d'):  # 只能修改当天及以后的排班
                    continue
                v = v if v else None
                detail = {'factory_date': class_date, 'class_code': v, 'weight_class_plan': instance}
                details.append(WeightClassPlanDetail(**detail))
        else:
            # 获取当月所有天数
            date_list = days_cur_month_dates(date_time=target_month)
            for i in date_list:
                details.append(WeightClassPlanDetail(**{'weight_class_plan': instance, 'factory_date': i}))
        WeightClassPlanDetail.objects.bulk_create(details)
        return instance

    class Meta:
        model = WeightClassPlan
        fields = ('id', 'target_month', 'classes', 'station', 'user', 'weight_class_details', 'username')
        unique_together = validators = [UniqueTogetherValidator(queryset=WeightClassPlan.objects.filter(delete_flag=False),
                                                                fields=('user', 'target_month'), message='该人员本月已有排班')]
        read_only_fields = COMMON_READ_ONLY_FIELDS


class WeightClassPlanUpdateSerializer(serializers.ModelSerializer):
    weight_class_details = serializers.DictField(default={}, write_only=True)

    @atomic
    def update(self, instance, validated_data):
        weight_class_details, target_month = validated_data.pop('weight_class_details'), validated_data['target_month']
        now_factory_date = get_current_factory_date()['factory_date']
        flag = True if instance.weight_class_details.all() else False
        for k, v in weight_class_details.items():
            class_date = target_month + '-' + '%02d' % int(k.split('/')[-1])
            if not flag:  # 新建
                detail = {'factory_date': class_date, 'class_code': v, 'weight_class_plan': instance}
                WeightClassPlanDetail.objects.create(**detail)
            else:  # 更新
                if class_date < (now_factory_date - datetime.timedelta(days=3)).strftime('%Y-%m-%d'):  # 只能修改当天以后的排班
                    continue
                v = v if v else None
                WeightClassPlanDetail.objects.filter(weight_class_plan=instance, factory_date=class_date).update(class_code=v)
        return super().update(instance, validated_data)

    class Meta:
        model = WeightClassPlan
        fields = ('target_month', 'station', 'weight_class_details')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipDownDetailsImportSerializer(serializers.ModelSerializer):

    def validate(self, validated_data):
        equip_no = validated_data['equip_no']
        group_name = validated_data['group']
        classes = validated_data['classes']
        if len(equip_no) == 2:
            new_eq_name = '{}0{}'.format(equip_no[0], equip_no[1])
            validated_data['equip_no'] = new_eq_name
        if len(classes) == 1:
            new_cs_name = classes + '班'
            validated_data['classes'] = new_cs_name
        if len(group_name) == 1:
            new_gp_name = group_name + '班'
            validated_data['group'] = new_gp_name
        return validated_data

    class Meta:
        model = EquipDownDetails
        fields = '__all__'