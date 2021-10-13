import uuid

from basics.models import Equip

from datetime import datetime

from django.db.transaction import atomic
from rest_framework import serializers

from rest_framework.validators import UniqueTogetherValidator, UniqueValidator

from basics.models import WorkSchedulePlan
from equipment.models import EquipDownType, EquipDownReason, EquipCurrentStatus, EquipMaintenanceOrder, EquipPart, \
    PropertyTypeNode, Property, PlatformConfig, EquipSupplier, EquipProperty, EquipAreaDefine, EquipPartNew, \
    EquipComponent, EquipComponentType, EquipArea, ERPSpareComponentRelation, EquipSpareErp, EquipFaultType, EquipFault,\
    PropertyTypeNode, Property, PlatformConfig, EquipFaultSignal, EquipMachineHaltType, EquipMachineHaltReason, \
    EquipOrderAssignRule, EquipMaintenanceAreaSetting
from mes.base_serializer import BaseModelSerializer
from mes.conf import COMMON_READ_ONLY_FIELDS


class EquipRealtimeSerializer(BaseModelSerializer):
    class Meta:
        model = Equip
        fields = "__all__"


class EquipDownTypeSerializer(BaseModelSerializer):
    class Meta:
        model = EquipDownType
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS
        validators = [UniqueTogetherValidator(queryset=EquipDownType.objects.filter(delete_flag=False).all(),
                                              fields=('no', 'name'), message='该数据已存在'),
                      UniqueTogetherValidator(queryset=EquipDownType.objects.filter(delete_flag=False).all(),
                                              fields=('no',), message='该类型代码已存在'),
                      UniqueTogetherValidator(queryset=EquipDownType.objects.filter(delete_flag=False).all(),
                                              fields=('name',), message='该类型名称已存在'),
                      ]


class EquipDownReasonSerializer(BaseModelSerializer):
    equip_down_type_name = serializers.CharField(source='equip_down_type.name', read_only=True, help_text='停机类型')

    class Meta:
        model = EquipDownReason
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipCurrentStatusSerializer(BaseModelSerializer):
    equip_no = serializers.CharField(source='equip.equip_no', read_only=True, help_text='设备编码')
    equip_name = serializers.CharField(source='equip.equip_name', read_only=True, help_text='设备名称')
    equip_type = serializers.CharField(source='equip.category.equip_type.global_name', read_only=True, help_text='设备类型')
    process = serializers.CharField(source='equip.category.process.global_name', read_only=True, help_text='工序')
    maintain_list = serializers.SerializerMethodField(read_only=True, help_text='部位维修列表')

    def get_maintain_list(self, obj):
        equip_part_set = obj.equip.equip_part_equip.all()
        part_list = []
        for equip_part_obj in equip_part_set:
            maintain_order_set = equip_part_obj.equip_maintenance_order_part.filter(status=3).all()
            if maintain_order_set:
                part_list.append(equip_part_obj.name)
        return set(part_list)

    class Meta:
        model = EquipCurrentStatus
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipPartSerializer(BaseModelSerializer):
    equip_no = serializers.CharField(source='equip.equip_no', read_only=True, help_text='设备编码')
    equip_name = serializers.CharField(source='equip.equip_name', read_only=True, help_text='设备名称')
    equip_type = serializers.CharField(source='equip.category.equip_type.global_name',
                                       read_only=True, help_text='设备类型')
    process = serializers.CharField(source='equip.category.process.global_name', read_only=True, help_text='工序')
    location_name = serializers.CharField(source='location.name', read_only=True, help_text='位置点')

    class Meta:
        model = EquipPart
        fields = "__all__"
        read_only_fields = COMMON_READ_ONLY_FIELDS
        validators = [UniqueTogetherValidator(queryset=EquipPart.objects.filter(delete_flag=False).all(),
                                              fields=('no', 'name', 'equip', 'location'), message='该数据已存在')]


class EquipMaintenanceOrderSerializer(BaseModelSerializer):
    equip_no = serializers.CharField(source='equip_part.equip.equip_no', read_only=True, help_text='设备编码')
    equip_name = serializers.CharField(source='equip_part.equip.equip_name', read_only=True, help_text='设备名称')
    part_name = serializers.CharField(source='equip_part.name', read_only=True, help_text='设备部位名称')
    affirm_username = serializers.CharField(source='affirm_user.username', read_only=True)
    assign_username = serializers.CharField(source='assign_user.username', read_only=True)
    maintenance_username = serializers.CharField(source='maintenance_user.username', read_only=True)
    take_time = serializers.SerializerMethodField(read_only=True, help_text='维修时间')

    def get_take_time(self, obj):
        try:
            return obj.end_time - obj.begin_time
        except:
            return None

    class Meta:
        model = EquipMaintenanceOrder
        fields = '__all__'


class PropertyTypeNodeSerializer(BaseModelSerializer):
    class Meta:
        model = PropertyTypeNode
        fields = '__all__'
        validators = [UniqueTogetherValidator(queryset=PropertyTypeNode.objects.filter(delete_flag=False).all(),
                                              fields=('name',), message='该数据已存在')]


class PropertySerializer(BaseModelSerializer):
    property_type = serializers.CharField(source='property_type_node.name', read_only=True, help_text='类型')
    status_name = serializers.CharField(source='get_status_display', help_text='状态', read_only=True)

    class Meta:
        model = Property
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipMaintenanceOrderUpdateSerializer(BaseModelSerializer):

    @atomic()
    def update(self, instance, validated_data):
        if 'status' in validated_data:
            if validated_data['status'] == 3:  # 开始维修
                validated_data['begin_time'] = datetime.now()
                instance.equip_part.equip.equip_current_status_equip.status = '维修开始'
                instance.equip_part.equip.equip_current_status_equip.save()
            if validated_data['status'] == 4:  # 结束维修
                validated_data['end_time'] = datetime.now()
            if validated_data['status'] == 5:  # 确认完成
                validated_data['affirm_time'] = datetime.now()
                validated_data['affirm_user'] = self.context["request"].user
            if validated_data['status'] == 7:  # 退回,重建一张维修单，将之前的维修单状态改为关闭
                validated_data['status'] = 6
                EquipMaintenanceOrder.objects.create(
                    order_uid=uuid.uuid1(),
                    factory_date=instance.factory_date,
                    equip_part=instance.equip_part,
                    first_down_reason=instance.first_down_reason,
                    first_down_type=instance.first_down_type,
                    down_flag=instance.down_flag,
                    image=instance.image,
                    down_time=instance.down_time,
                    order_src=instance.order_src,
                    note=instance.note,
                    relevance_order_uid=instance.relevance_order_uid,
                    created_user=self.context["request"].user
                )
        if validated_data.get('maintenance_user', None):
            validated_data['assign_user'] = self.context["request"].user
        else:
            validated_data['maintenance_user'] = self.context["request"].user
            validated_data['assign_user'] = self.context["request"].user
        instance = super().update(instance, validated_data)
        if 'status' in validated_data and validated_data[
            'status'] == 4:  # 维修单维修结束之后判断这个设备的所有维修单 没有开始维修的维修单 就把这个设备改为维修结束
            equip = instance.equip_part.equip
            part_set = equip.equip_part_equip.all()
            part_list = []
            for part_obj in part_set:
                main_set = part_obj.equip_maintenance_order_part.filter(status=3).all()
                if main_set:
                    part_list.append(main_set)
            if not part_list:
                equip.equip_current_status_equip.status = '维修结束'
                equip.equip_current_status_equip.save()
        return instance

    class Meta:
        fields = (
            'id', 'status', 'maintenance_user', 'down_reason', 'take_time', 'first_down_reason', 'first_down_type',
            'note', 'assign_user')
        extra_kwargs = {'first_down_reason': {'required': False},
                        'first_down_type': {'required': False},
                        'note': {'required': False}}
        # fields = ('id', 'status', 'maintenance_user', 'down_reason', 'take_time')
        model = EquipMaintenanceOrder


class EquipMaintenanceCreateOrderSerializer(BaseModelSerializer):

    def create(self, validated_data):
        now = datetime.now()
        work_schedule_plan = WorkSchedulePlan.objects.filter(
            start_time__lte=now,
            end_time__gte=now,
            plan_schedule__work_schedule__work_procedure__global_name='密炼').first()
        if work_schedule_plan:
            factory_date = work_schedule_plan.plan_schedule.day_time
            class_name = work_schedule_plan.classes.global_name
        else:
            factory_date = now.date()
            class_name = "早班"
        validated_data["class_name"] = class_name
        validated_data['order_uid'] = uuid.uuid1()
        validated_data['factory_date'] = factory_date
        down_flag = validated_data.get('down_flag', None)
        if down_flag:
            validated_data['equip_part'].equip.equip_current_status_equip.status = '停机'
            validated_data['equip_part'].equip.equip_current_status_equip.save()
        return super().create(validated_data)

    class Meta:
        model = EquipMaintenanceOrder
        fields = ('equip_part', 'first_down_reason', 'first_down_type', 'down_flag', 'image',
                  'down_time', 'order_src', 'note')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class PlatformConfigSerializer(BaseModelSerializer):
    class Meta:
        model = PlatformConfig
        fields = '__all__'
        validators = [UniqueTogetherValidator(queryset=PlatformConfig.objects.filter(delete_flag=False).all(),
                                              fields=('platform',), message='已存在该平台的通知配置')]


class EquipMaintenanceOrderLogSerializer(BaseModelSerializer):
    equip_no = serializers.CharField(source='equip_part.equip.equip_no', read_only=True, help_text='设备编码')
    equip_name = serializers.CharField(source='equip_part.equip.equip_name', read_only=True, help_text='设备名称')
    equip_type = serializers.CharField(source='equip_part.equip.category.equip_type.global_name',
                                       read_only=True, help_text='设备类型')
    waiting_repair = serializers.SerializerMethodField(read_only=True, help_text='等待维修时间')
    repair_time = serializers.SerializerMethodField(read_only=True, help_text='维修时间')
    stop_time = serializers.SerializerMethodField(read_only=True, help_text='停机时间')

    def get_repair_time(self, obj):
        try:
            return obj.end_time - obj.begin_time
        except:
            return None

    def get_waiting_repair(self, obj):
        try:
            return obj.begin_time - obj.created_date
        except:
            return None

    def get_stop_time(self, obj):
        if obj.down_flag:
            try:
                return obj.affirm_time - obj.down_time
            except:
                return None
        else:
            return None

    class Meta:
        model = EquipMaintenanceOrder
        fields = '__all__'


# **************************2021-10-09最新序列化器**************************


class EquipSupplierSerializer(BaseModelSerializer):
    supplier_code = serializers.CharField(help_text='供应商编号',
                                          validators=[UniqueValidator(queryset=EquipSupplier.objects.all(), message='该编码已存在')])
    supplier_name = serializers.CharField(help_text='供应商名称',
                                          validators=[UniqueValidator(queryset=EquipSupplier.objects.filter(use_flag=True), message='该供应商已存在')])
    use_flag_name = serializers.SerializerMethodField()

    def get_use_flag_name(self, obj):
        return 'Y' if obj.use_flag else 'N'

    class Meta:
        model = EquipSupplier
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipComponentListSerializer(BaseModelSerializer):
    equip_type_name = serializers.CharField(source='equip_part.equip_type.category_name', help_text='所属主设备种类')
    equip_part_name = serializers.CharField(source='equip_part.part_name', help_text='所属设备部位')
    equip_component_type_name = serializers.CharField(source='equip_component_type.component_type_name', help_text='所属部件分类')
    is_binding = serializers.BooleanField(help_text='是否绑定备件')

    class Meta:
        model = EquipComponent
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipFaultSignalSerializer(BaseModelSerializer):
    equip_no = serializers.CharField(source='equip.equip_no', read_only=True)
    equip_component_name = serializers.CharField(source='equip_component.component_name', read_only=True)
    equip_part_name = serializers.CharField(source='equip_component.equip_part.part_name', read_only=True)

    class Meta:
        model = EquipFaultSignal
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipPropertySerializer(BaseModelSerializer):
    status_name = serializers.SerializerMethodField()
    equip_type_no = serializers.ReadOnlyField(source='equip_type.category_no', help_text='设备类型')
    equip_type_name = serializers.ReadOnlyField(source="equip_type.equip_type.global_name", read_only=True, help_text='设备型号')
    made_in = serializers.ReadOnlyField(source='equip_supplier.supplier_name', help_text='设备制造商')

    def get_status_name(self, obj):
        dic = {
            1: '使用中',
            2: '废弃',
            3: '限制'}
        return dic.get(obj.status)

    class Meta:
        model = EquipProperty
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipMachineHaltTypeSerializer(BaseModelSerializer):

    class Meta:
        model = EquipMachineHaltType
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipAreaDefineSerializer(BaseModelSerializer):
    area_name = serializers.CharField(help_text='位置区域名称',
                                      validators=[UniqueValidator(queryset=EquipAreaDefine.objects.all(), message='该名称已存在')])
    area_code = serializers.CharField(help_text='位置区域编号',
                                      validators=[UniqueValidator(queryset=EquipAreaDefine.objects.all(), message='该编号已存在')])
    use_flag_name = serializers.SerializerMethodField()

    def get_use_flag_name(self, obj):
        return 'Y' if obj.use_flag else 'N'

    class Meta:
        model = EquipAreaDefine
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipPartNewSerializer(BaseModelSerializer):
    part_code = serializers.CharField(help_text='部位编码',
                                      validators=[UniqueValidator(queryset=EquipPartNew.objects.all(), message='该编码已存在')])
    part_name = serializers.CharField(help_text='设备名称',
                                      validators=[UniqueValidator(queryset=EquipPartNew.objects.all(), message='该名称已存在')])
    category_no = serializers.ReadOnlyField(source='equip_type.category_no', help_text='所属主设备种类')
    global_name = serializers.ReadOnlyField(source='global_part_type.global_name', help_text='部位分类')
    use_flag_name = serializers.SerializerMethodField()

    def get_use_flag_name(self, obj):
        return 'Y' if obj.use_flag else 'N'

    class Meta:
        model = EquipPartNew
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipMachineHaltReasonSerializer(BaseModelSerializer):
    equip_fault_types = serializers.SerializerMethodField(read_only=True)

    def update(self, instance, validated_data):
        instance.equip_fault_type.clear()
        return super().update(instance, validated_data)

    def get_equip_fault_types(self, obj):
        return obj.equip_fault_type.values()

    class Meta:
        model = EquipMachineHaltReason
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipComponentTypeSerializer(BaseModelSerializer):
    # 设备部件分类
    component_type_code = serializers.CharField(help_text='分类编号',
                                                validators=[UniqueValidator(queryset=EquipComponentType.objects.all(), message='该编号已存在')])
    component_type_name = serializers.CharField(help_text='分类名称',
                                                validators=[UniqueValidator(queryset=EquipComponentType.objects.all(), message='该名称已存在')])

    class Meta:
        model = EquipComponentType
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipOrderAssignRuleSerializer(BaseModelSerializer):
    equip_type_name = serializers.CharField(source='equip_type.global_name', read_only=True)

    class Meta:
        model = EquipOrderAssignRule
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipAreaSerializer(BaseModelSerializer):

    class Meta:
        model = EquipArea
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipComponentCreateSerializer(BaseModelSerializer):
    component_code = serializers.CharField(max_length=64,
                                           validators=[
                                                UniqueValidator(queryset=EquipComponent.objects.all(),
                                                                message='该部件代码已存在'),
                                           ])
    component_name = serializers.CharField(max_length=64,
                                           validators=[
                                                UniqueValidator(queryset=EquipComponent.objects.all(),
                                                                message='该部件名称已存在'),
                                           ])

    class Meta:
        model = EquipComponent
        fields = ('equip_type', 'equip_part', 'equip_component_type', 'component_code', 'component_name', 'use_flag',
                  'created_username')


class ERPSpareComponentRelationListSerializer(serializers.ModelSerializer):
    equip_component_type_name = serializers.CharField(source='equip_spare_erp.equip_component_type.component_type_name', help_text='备件分类')
    spare_code = serializers.CharField(source='equip_spare_erp.spare_code', help_text='备件编码')
    spare_name = serializers.CharField(source='equip_spare_erp.spare_name', help_text='备件名称')
    supplier_name = serializers.CharField(source='equip_spare_erp.supplier_name', help_text='供应商名称')

    class Meta:
        model = ERPSpareComponentRelation
        fields = '__all__'


class EquipSpareErpListSerializer(BaseModelSerializer):
    equip_component_type_name = serializers.CharField(source='equip_component_type.component_type_name', help_text='备件分类')

    class Meta:
        model = EquipSpareErp
        fields = '__all__'


class EquipSpareErpCreateSerializer(BaseModelSerializer):
    spare_code = serializers.CharField(max_length=64,
                                       validators=[
                                           UniqueValidator(queryset=EquipSpareErp.objects.all(),
                                                           message='该备件代码已存在'),
                                       ])
    spare_name = serializers.CharField(max_length=64,
                                       validators=[
                                           UniqueValidator(queryset=EquipSpareErp.objects.all(),
                                                           message='该备件名称已存在'),
                                       ])

    class Meta:
        model = EquipSpareErp
        fields = ('equip_component_type', 'spare_code', 'spare_name', 'specification', 'technical_params', 'unit',
                  'key_parts_flag', 'supplier_name', 'lower_stock', 'upper_stock', 'cost', 'texture_material',
                  'period_validity', 'use_flag', 'created_username')


class ERPSpareComponentRelationCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ERPSpareComponentRelation
        fields = '__all__'


# class EquipSpareErpSerializer(serializers.ModelSerializer):
#     equip_type_name = serializers.CharField(source='equip_component_type.category_name', help_text='备件分类')
#     equip_part_name = serializers.CharField(source='spare_code', help_text='备件编码')
#     equip_component_type_name = serializers.CharField(source='spare_name', help_text='备件名称')
#     supplier_name = serializers.CharField(source='supplier_name', help_text='供应商名称')
#
#     class Meta:
#         model = EquipSpareErp
#         fields = '__all__'


class EquipFaultTypeSerializer(BaseModelSerializer):
    """设备故障分类类型序列化器"""
    fault_type_code = serializers.CharField(max_length=64,
                                            validators=[
                                                UniqueValidator(queryset=EquipFaultType.objects.all(),
                                                                message='该代码类型编号已存在'),
                                            ])
    fault_type_name = serializers.CharField(max_length=64,
                                            validators=[
                                                UniqueValidator(queryset=EquipFaultType.objects.filter(delete_flag=False),
                                                                message='该代码类型名称已存在'),
                                            ])

    class Meta:
        model = EquipFaultType
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS
        validators = [
            UniqueTogetherValidator(
                queryset=model.objects.filter(delete_flag=False),
                fields=('fault_type_name', 'use_flag'),
                message="该类型名称已存在"
            )
        ]


class EquipFaultCodeSerializer(BaseModelSerializer):
    """设备故障分类序列化器"""
    fault_type_code = serializers.ReadOnlyField(source='equip_fault_type.fault_type_code')
    fault_type_name = serializers.ReadOnlyField(source='equip_fault_type.fault_type_name')
    fault_code = serializers.CharField(max_length=64, validators=[UniqueValidator(queryset=EquipFault.objects.all(),
                                                                                  message='该公共代码编号已存在')])


    @staticmethod
    def validate_equip_fault_type(equip_fault_type):
        if equip_fault_type.use_flag == 0:
            raise serializers.ValidationError('弃用状态的分类类型不可新建')
        return equip_fault_type

    def create(self, validated_data):
        validated_data.update(created_user=self.context["request"].user)
        instance = super().create(validated_data)
        return instance

    def update(self, instance, validated_data):
        validated_data.update(last_updated_user=self.context["request"].user)
        return super(EquipFaultCodeSerializer, self).update(instance, validated_data)

    class Meta:
        model = EquipFault
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipMaintenanceAreaSettingSerializer(BaseModelSerializer):
    equip_no = serializers.CharField(source='equip.equip_no', read_only=True)
    equip_name = serializers.CharField(source='equip.equip_name', read_only=True)
    equip_part_name = serializers.CharField(source='equip_part.part_name', read_only=True)
    equip_area_name = serializers.CharField(source='equip_area.area_name', read_only=True)

    class Meta:
        model = EquipMaintenanceAreaSetting
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS
