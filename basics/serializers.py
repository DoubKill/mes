from datetime import timedelta

from django.db.models import F
from rest_framework import serializers
from django.db.transaction import atomic

from rest_framework.validators import UniqueTogetherValidator, UniqueValidator
from basics.models import GlobalCodeType, GlobalCode, ClassesDetail, WorkSchedule, Equip, SysbaseEquipLevel, \
    WorkSchedulePlan, PlanSchedule, EquipCategoryAttribute
from mes.base_serializer import BaseModelSerializer
from mes.conf import COMMON_READ_ONLY_FIELDS
from plan.uuidfield import UUidTools


class GlobalCodeTypeSerializer(BaseModelSerializer):
    """公共代码类型序列化器"""
    type_name = serializers.CharField(max_length=64,
                                      validators=[
                                          UniqueValidator(queryset=GlobalCodeType.objects.filter(delete_flag=False),
                                                          message='该代码类型名称已存在'),
                                      ])
    type_no = serializers.CharField(max_length=64,
                                    validators=[
                                        UniqueValidator(queryset=GlobalCodeType.objects.all(),
                                                        message='该代码类型编号已存在'),
                                    ])

    def update(self, instance, validated_data):
        if 'used_flag' in validated_data:
            if instance.used_flag != validated_data['used_flag']:
                if validated_data['used_flag'] == 0:  # 弃用
                    instance.global_codes.filter().update(used_flag=F('id'))
                else:  # 启用
                    instance.global_codes.filter().update(used_flag=0)
        instance = super().update(instance, validated_data)
        return instance

    class Meta:
        model = GlobalCodeType
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS
        validators = [
            UniqueTogetherValidator(
                queryset=model.objects.filter(delete_flag=False),
                fields=('type_name', 'used_flag'),
                message="该代码类型名称已存在"
            )
        ]


class GlobalCodeSerializer(BaseModelSerializer):
    """公共代码序列化器"""
    global_no = serializers.CharField(max_length=64, validators=[UniqueValidator(
        queryset=GlobalCode.objects.all(), message='该公共代码编号已存在')])

    @staticmethod
    def validate_global_type(global_type):
        if global_type.used_flag == 0:
            raise serializers.ValidationError('弃用状态的代码类型不可新建公共代码')
        return global_type

    def create(self, validated_data):
        validated_data.update(created_user=self.context["request"].user)
        instance = super().create(validated_data)
        if 'used_flag' in validated_data:
            if validated_data['used_flag'] != 0:  # 不是启用状态，修改其used_flag为id
                instance.used_flag = instance.id
                instance.save()
        return instance

    def update(self, instance, validated_data):
        if 'used_flag' in validated_data:
            if instance.used_flag != validated_data['used_flag']:
                if validated_data['used_flag'] != 0:  # 弃用
                    validated_data['used_flag'] = instance.id
        validated_data.update(last_updated_user=self.context["request"].user)
        return super(GlobalCodeSerializer, self).update(instance, validated_data)

    class Meta:
        model = GlobalCode
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ClassesDetailSerializer(BaseModelSerializer):
    """工作日程班次条目创建、列表、详情序列化器"""
    classes_name = serializers.CharField(source="classes.global_name")

    class Meta:
        model = ClassesDetail
        exclude = ('work_schedule',)
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ClassesSimpleSerializer(BaseModelSerializer):
    """工作日程班次下拉列表"""
    classes_name = serializers.CharField(source="classes.global_name")
    work_schedule_name = serializers.CharField(source="work_schedule.schedule_name", read_only=True)

    class Meta:
        model = ClassesDetail
        fields = ('id', 'classes_name', 'work_schedule_name')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class WorkScheduleSerializer(BaseModelSerializer):
    """日程创建、列表、详情序列化器"""
    classesdetail_set = ClassesDetailSerializer(many=True,
                                                help_text="""[{"classes":班次id,"classes_name":班次名称,
                                                "start_time":"12:12:12","end_time":"12:12:12",
                                                "classes_type_name":"正常"}]""", )

    @atomic()
    def create(self, validated_data):
        classesdetail_set = validated_data.pop('classesdetail_set', None)
        instance = super().create(validated_data)
        classes_details_list = []
        for plan in classesdetail_set:
            plan['work_schedule'] = instance
            classes_details_list.append(ClassesDetail(**plan))
        ClassesDetail.objects.bulk_create(classes_details_list)
        return instance

    class Meta:
        model = WorkSchedule
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class WorkScheduleUpdateSerializer(BaseModelSerializer):
    """日程修改序列化器"""
    classesdetail_set = ClassesDetailSerializer(many=True,
                                                help_text="""[{"id":1, "classes":班次id,"classes_name":班次名称,
                                                      "start_time":"12:12:12", "end_time":"12:12:12",
                                                      "classes_type_name":"正常"}]""")

    @atomic()
    def update(self, instance, validated_data):
        if instance.plan_schedule.exists():
            raise serializers.ValidationError('该倒班已关联排班计划，不可修改')
        classesdetail_set = validated_data.pop('classesdetail_set', None)
        if classesdetail_set is not None:
            instance.classesdetail_set.all().delete()
            classes_details_list = []
            for plan in classesdetail_set:
                plan['work_schedule'] = instance
                classes_details_list.append(ClassesDetail(**plan))
            ClassesDetail.objects.bulk_create(classes_details_list)
        instance = super().update(instance, validated_data)
        return instance

    class Meta:
        model = WorkSchedule
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipCategoryAttributeSerializer(BaseModelSerializer):
    """设备分类属性表序列化器"""
    equip_process_name = serializers.CharField(source="process.global_name", read_only=True)
    equip_process_no = serializers.CharField(source="process.global_no", read_only=True)
    equip_type_name = serializers.CharField(source="equip_type.global_name", read_only=True)
    category_no = serializers.CharField(max_length=64, validators=[UniqueValidator(
        queryset=EquipCategoryAttribute.objects.all(), message='该设备属性编号已存在')])

    class Meta:
        model = EquipCategoryAttribute
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipSerializer(BaseModelSerializer):
    """设备序列化器"""
    category_no = serializers.CharField(source="category.category_no", read_only=True)
    category_name = serializers.CharField(source="category.category_name", read_only=True)
    equip_process_name = serializers.CharField(source="category.process.global_name", read_only=True)
    equip_process_no = serializers.CharField(source="category.process.global_no", read_only=True)
    equip_type = serializers.CharField(source="category.equip_type.global_name", read_only=True)
    equip_level_name = serializers.CharField(source="equip_level.global_name", read_only=True)
    equip_no = serializers.CharField(max_length=64,
                                     validators=[UniqueValidator(
                                         queryset=Equip.objects.all(), message='该设备编号已存在')])

    class Meta:
        model = Equip
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipCreateAndUpdateSerializer(BaseModelSerializer):
    """设备序列化器增改用"""

    class Meta:
        model = Equip
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class SysbaseEquipLevelSerializer(BaseModelSerializer):
    """设备层次序列化器"""

    class Meta:
        model = SysbaseEquipLevel
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class WorkSchedulePlanSerializer(BaseModelSerializer):
    """工作日程计划序列化器"""
    classes_name = serializers.CharField(source='classes.global_name', read_only=True)
    group_name = serializers.CharField(source='group.global_name', read_only=True)

    class Meta:
        model = WorkSchedulePlan
        exclude = ('plan_schedule','work_schedule_plan_no')
        read_only_fields = ('created_date', 'last_updated_date', 'delete_date',
                            'delete_flag', 'created_user', 'last_updated_user',
                            'delete_user', 'start_time', 'end_time')


class PlanScheduleSerializer(BaseModelSerializer):
    """计划时间排班序列化器"""
    work_schedule_plan = WorkSchedulePlanSerializer(many=True,
                                                    help_text="""{"classes":班次id, "rest_flag":0, "group":班组id""")
    work_schedule_name = serializers.CharField(source='work_schedule.schedule_name', read_only=True)

    class Meta:
        model = PlanSchedule
        # fields = '__all__'
        exclude = ('plan_schedule_no',)
        read_only_fields = COMMON_READ_ONLY_FIELDS

    def validate(self, attrs):
        day_time = attrs['day_time']
        work_schedule = attrs['work_schedule']
        if PlanSchedule.objects.filter(day_time=day_time, work_schedule=work_schedule).exists():
            raise serializers.ValidationError('当前日期已存在此倒班')
        return attrs

    @atomic()
    def create(self, validated_data):
        day_time = validated_data['day_time']
        work_schedule_plan = validated_data.pop('work_schedule_plan', None)
        validated_data['plan_schedule_no'] = UUidTools.uuid1_hex()
        instance = super().create(validated_data)
        work_schedule_plan_list = []
        morning_class = ClassesDetail.objects.filter(work_schedule=instance.work_schedule,
                                                     classes__global_name='早班').first()
        evening_class = ClassesDetail.objects.filter(work_schedule=instance.work_schedule,
                                                     classes__global_name='晚班').first()
        for plan in work_schedule_plan:
            classes = plan['classes']
            class_detail = ClassesDetail.objects.filter(work_schedule=instance.work_schedule,
                                                        classes=plan['classes']).first()
            if not class_detail:
                raise serializers.ValidationError('暂无此班次倒班数据')
            if classes.global_name == '晚班':  # 晚班的结束时间小于等于早班的开始时间，日期则加一天
                if all([morning_class, evening_class]):
                    if evening_class.end_time <= morning_class.start_time:
                        day_time = (day_time + timedelta(days=1)).strftime("%Y-%m-%d")
            plan['start_time'] = str(day_time) + ' ' + str(class_detail.start_time)
            plan['end_time'] = str(day_time) + ' ' + str(class_detail.end_time)
            plan['plan_schedule'] = instance
            plan['work_schedule_plan_no'] = UUidTools.uuid1_hex()
            work_schedule_plan_list.append(WorkSchedulePlan(**plan))
        WorkSchedulePlan.objects.bulk_create(work_schedule_plan_list)
        return instance
