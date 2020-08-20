from django.db.models import F
from rest_framework import serializers
from django.db.transaction import atomic

from rest_framework.validators import UniqueTogetherValidator, UniqueValidator
from basics.models import GlobalCodeType, GlobalCode, ClassesDetail, WorkSchedule, Equip, SysbaseEquipLevel, \
    WorkSchedulePlan, PlanSchedule, EquipCategoryAttribute
from mes.base_serializer import BaseModelSerializer
from mes.conf import COMMON_READ_ONLY_FIELDS


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
        validators = [
            UniqueTogetherValidator(
                queryset=model.objects.filter(delete_flag=False),
                fields=('global_no', 'global_name', 'global_type', 'used_flag'),
                message="该公共代码已存在"
            )
        ]


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

    class Meta:
        model = ClassesDetail
        fields = ('id', 'classes_name')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class ClassesDetailUpdateSerializer(BaseModelSerializer):
    """工作日程班次条目修改序列化器"""

    class Meta:
        model = ClassesDetail
        exclude = ('work_schedule',)
        extra_kwargs = {'id': {'read_only': False}}


class WorkScheduleSerializer(BaseModelSerializer):
    """日程创建、列表、详情序列化器"""
    classesdetail_set = ClassesDetailSerializer(many=True,
                                                help_text="""[{"classes":班次id,"classes_name":班次名称,"start_time":"2020-12-12 12:12:12","end_time":"2020-12-12 12:12:12","classes_type_name":"正常"}]""", )

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
    classesdetail_set = ClassesDetailUpdateSerializer(many=True,
                                                      help_text="""[{"id":1, "classes":班次id,"classes_name":班次名称,"start_time":"2020-12-12 12:12:12","end_time":"2020-12-12 12:12:12","classes_type_name":"正常"}]""")

    @atomic()
    def update(self, instance, validated_data):
        classesdetail_set = validated_data.pop('classesdetail_set', None)
        if len(classesdetail_set) != 3:
            raise serializers.ValidationError("请输入正确的班次条目集合")
        for plan in classesdetail_set:
            plan_id = plan.pop('id')
            ClassesDetail.objects.filter(id=plan_id).update(**plan)
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

    class Meta:
        model = WorkSchedulePlan
        exclude = ('plan_schedule',)
        read_only_fields = COMMON_READ_ONLY_FIELDS


class PlanScheduleSerializer(BaseModelSerializer):
    """计划时间排班序列化器"""
    work_schedule_plan = WorkSchedulePlanSerializer(many=True,
                                                    help_text="""{"work_schedule_plan":[{"classes_detail":1,"group":1,"group_name":"a班","rest_flag":0},{"classes_detail":2,"group":2,"group_name":"b班","rest_flag":0},{"classes_detail":3,"group":3,"group_name":"c班","rest_flag":0}],"day_time":"2020-07-25 15:55:50","week_time":"monday","work_schedule":1}""")

    class Meta:
        model = PlanSchedule
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS

    @atomic()
    def create(self, validated_data):
        work_schedule_plan = validated_data.pop('work_schedule_plan', None)
        instance = super().create(validated_data)
        work_schedule_plan_list = []
        for plan in work_schedule_plan:
            plan['plan_schedule'] = instance
            work_schedule_plan_list.append(WorkSchedulePlan(**plan))
        WorkSchedulePlan.objects.bulk_create(work_schedule_plan_list)
        return instance
