import uuid

from basics.models import Equip

from datetime import datetime

from django.db.transaction import atomic
from rest_framework import serializers

from rest_framework.validators import UniqueTogetherValidator, UniqueValidator

from basics.models import WorkSchedulePlan
from equipment.models import EquipDownType, EquipDownReason, EquipCurrentStatus, EquipMaintenanceOrder, EquipPart, \
    PropertyTypeNode, Property, PlatformConfig, EquipSupplier, EquipProperty, EquipAreaDefine, EquipPartNew, \
    EquipComponent, EquipComponentType, ERPSpareComponentRelation, EquipSpareErp, EquipFaultType, EquipFault, \
    PropertyTypeNode, Property, PlatformConfig, EquipFaultSignal, EquipMachineHaltType, EquipMachineHaltReason, \
    EquipOrderAssignRule, EquipMaintenanceAreaSetting, EquipBom, EquipJobItemStandardDetail, EquipJobItemStandard, \
    EquipMaintenanceStandard, EquipMaintenanceStandardMaterials, EquipRepairStandard, EquipRepairStandardMaterials
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
    supplier_code = serializers.CharField(help_text='供应商编号', max_length=64,
                                          validators=[UniqueValidator(queryset=EquipSupplier.objects.all(), message='该编码已存在')])
    supplier_name = serializers.CharField(help_text='供应商名称', max_length=64,
                                          validators=[UniqueValidator(queryset=EquipSupplier.objects.filter(use_flag=True), message='该供应商已存在')])
    use_flag_name = serializers.SerializerMethodField()

    def get_use_flag_name(self, obj):
        return 'Y' if obj.use_flag else 'N'

    class Meta:
        model = EquipSupplier
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipComponentListSerializer(BaseModelSerializer):
    equip_type_name = serializers.CharField(source='equip_part.equip_type.category_name', help_text='所属主设备种类', max_length=64)
    equip_type = serializers.IntegerField(source='equip_part.equip_type_id')
    equip_part_name = serializers.CharField(source='equip_part.part_name', help_text='所属设备部位', max_length=64)
    equip_component_type_name = serializers.CharField(source='equip_component_type.component_type_name', help_text='所属部件分类', max_length=64)
    is_binding = serializers.BooleanField(help_text='是否绑定备件')
    use_flag_name = serializers.SerializerMethodField()

    def get_use_flag_name(self, obj):
        return 'Y' if obj.use_flag else 'N'

    class Meta:
        model = EquipComponent
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipFaultSignalSerializer(BaseModelSerializer):
    signal_code = serializers.CharField(validators=[
                                              UniqueValidator(queryset=EquipFaultSignal.objects.all(),
                                                              message='该故障信号编码已存在')])
    signal_name = serializers.CharField(validators=[
                                              UniqueValidator(queryset=EquipFaultSignal.objects.all(),
                                                              message='该故障信号名称已存在')])
    equip_no = serializers.CharField(source='equip.equip_no', read_only=True)
    equip_name = serializers.CharField(source='equip.equip_name', read_only=True)
    equip_component_name = serializers.CharField(source='equip_component.component_name', read_only=True, default='')
    equip_part_name = serializers.CharField(source='equip_part.part_name', read_only=True, default='')
    equip_category_id = serializers.IntegerField(source='equip.category_id', read_only=True, default='')
    use_flag_name = serializers.SerializerMethodField()
    alarm_signal_down_flag_name = serializers.SerializerMethodField()
    fault_signal_down_flag_name = serializers.SerializerMethodField()

    def get_use_flag_name(self, obj):
        return 'Y' if obj.use_flag else 'N'

    def get_alarm_signal_down_flag_name(self, obj):
        return 'Y' if obj.alarm_signal_down_flag else 'N'

    def get_fault_signal_down_flag_name(self, obj):
        return 'Y' if obj.fault_signal_down_flag else 'N'

    class Meta:
        model = EquipFaultSignal
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipPropertySerializer(BaseModelSerializer):
    no = serializers.ReadOnlyField()
    name = serializers.ReadOnlyField()
    status_name = serializers.SerializerMethodField()
    equip_type_no = serializers.ReadOnlyField(source='equip_type.category_no', help_text='设备类型')
    equip_type_name = serializers.ReadOnlyField(source="equip_type.equip_type.global_name", read_only=True, help_text='设备型号')
    made_in = serializers.ReadOnlyField(source='equip_supplier.supplier_name', help_text='设备制造商', default='')
    property_no = serializers.CharField(help_text='固定资产编码', max_length=64,
                                        validators=[UniqueValidator(queryset=EquipProperty.objects.all(), message='固定资产名称已存在')])

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
    machine_halt_type_code = serializers.CharField(validators=[
        UniqueValidator(queryset=EquipMachineHaltType.objects.all(),
                        message='该停机类型编码已存在')])
    machine_halt_type_name = serializers.CharField(validators=[
        UniqueValidator(queryset=EquipMachineHaltType.objects.all(),
                        message='该停机类型名称已存在')])

    class Meta:
        model = EquipMachineHaltType
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipAreaDefineSerializer(BaseModelSerializer):
    area_name = serializers.CharField(help_text='位置区域名称', max_length=64,
                                      validators=[UniqueValidator(queryset=EquipAreaDefine.objects.all(), message='该名称已存在')])
    area_code = serializers.CharField(help_text='位置区域编号', max_length=64,
                                      validators=[UniqueValidator(queryset=EquipAreaDefine.objects.all(), message='该编号已存在')])
    use_flag_name = serializers.SerializerMethodField()

    def get_use_flag_name(self, obj):
        return 'Y' if obj.use_flag else 'N'

    class Meta:
        model = EquipAreaDefine
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipPartNewSerializer(BaseModelSerializer):
    part_code = serializers.CharField(help_text='部位编码', max_length=64,
                                      validators=[UniqueValidator(queryset=EquipPartNew.objects.all(), message='该编码已存在')])
    part_name = serializers.CharField(help_text='设备名称', max_length=64,
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
    machine_halt_reason_code = serializers.CharField(validators=[
        UniqueValidator(queryset=EquipMachineHaltReason.objects.all(),
                        message='该停机原因编码已存在')])
    machine_halt_reason_name = serializers.CharField(validators=[
        UniqueValidator(queryset=EquipMachineHaltReason.objects.all(),
                        message='该停机原因名称已存在')])
    equip_faults = serializers.SerializerMethodField(read_only=True)

    @staticmethod
    def validate_equip_machine_halt_type(equip_machine_halt_type):
        if equip_machine_halt_type.use_flag == 0:
            raise serializers.ValidationError('弃用状态的停机类型不可新建')
        return equip_machine_halt_type

    def update(self, instance, validated_data):
        instance.equip_fault.clear()
        return super().update(instance, validated_data)

    def get_equip_faults(self, obj):
        return obj.equip_fault.values()

    class Meta:
        model = EquipMachineHaltReason
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipComponentTypeSerializer(BaseModelSerializer):
    # 设备部件分类
    component_type_code = serializers.CharField(help_text='分类编号', max_length=64,
                                                validators=[UniqueValidator(queryset=EquipComponentType.objects.all(), message='该编号已存在')])
    component_type_name = serializers.CharField(help_text='分类名称', max_length=64,
                                                validators=[UniqueValidator(queryset=EquipComponentType.objects.all(), message='该名称已存在')])

    class Meta:
        model = EquipComponentType
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipOrderAssignRuleSerializer(BaseModelSerializer):
    rule_code = serializers.CharField(validators=[
        UniqueValidator(queryset=EquipOrderAssignRule.objects.all(),
                        message='该工单指派规则编码已存在')])
    rule_name = serializers.CharField(validators=[
        UniqueValidator(queryset=EquipOrderAssignRule.objects.all(),
                        message='该工单指派规则名称已存在')])
    equip_type_name = serializers.CharField(source='equip_type.global_name', read_only=True, default='')
    use_flag_name = serializers.SerializerMethodField()

    def get_use_flag_name(self, obj):
        return 'Y' if obj.use_flag else 'N'

    class Meta:
        model = EquipOrderAssignRule
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
        fields = ('equip_part', 'equip_component_type', 'component_code', 'component_name', 'use_flag')


class ERPSpareComponentRelationListSerializer(serializers.ModelSerializer):
    equip_component_type_name = serializers.CharField(source='equip_spare_erp.equip_component_type.component_type_name', help_text='备件分类', max_length=64)
    spare_code = serializers.CharField(source='equip_spare_erp.spare_code', help_text='备件编码', max_length=64)
    spare_name = serializers.CharField(source='equip_spare_erp.spare_name', help_text='备件名称', max_length=64)
    supplier_name = serializers.CharField(source='equip_spare_erp.supplier_name', help_text='供应商名称', max_length=64)

    class Meta:
        model = ERPSpareComponentRelation
        fields = '__all__'


class EquipSpareErpListSerializer(BaseModelSerializer):
    equip_component_type_name = serializers.CharField(source='equip_component_type.component_type_name', help_text='备件分类', max_length=64)
    key_parts_flag_name = serializers.SerializerMethodField()
    use_flag_name = serializers.SerializerMethodField()

    def get_key_parts_flag_name(self, obj):
        return '是' if obj.key_parts_flag else '否'

    def get_use_flag_name(self, obj):
        return 'Y' if obj.use_flag else 'N'

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
                  'period_validity', 'use_flag')


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


class EquipFaultCodeSerializer(BaseModelSerializer):
    """设备故障分类序列化器"""
    fault_type_code = serializers.ReadOnlyField(source='equip_fault_type.fault_type_code')
    fault_type_name = serializers.ReadOnlyField(source='equip_fault_type.fault_type_name')
    fault_code = serializers.CharField(max_length=64, validators=[UniqueValidator(queryset=EquipFault.objects.all(),
                                                                                  message='该公共代码编号已存在')])
    fault_name = serializers.CharField(max_length=64, validators=[UniqueValidator(queryset=EquipFault.objects.all(),
                                                                                  message='该公共代码名称已存在')])

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


class EquipBomSerializer(BaseModelSerializer):
    equip_area_code = serializers.ReadOnlyField(source='equip_area_define.area_code', help_text='区域编号', default='')
    equip_area_name = serializers.ReadOnlyField(source='equip_area_define.area_name', help_text='区域名称', default='')
    equip_type = serializers.ReadOnlyField(source='equip_info.category.category_name', help_text='设备机型', default='')
    equip_type_nid = serializers.ReadOnlyField(source='equip_info.category_id', help_text='设备机型id', default='')
    part_code = serializers.ReadOnlyField(source='part.part_code', help_text='设备部位编号', default='')
    component_code = serializers.ReadOnlyField(source='component.component_code', help_text='设备部件编号', default='')
    component_type = serializers.ReadOnlyField(source='component.equip_component_type.component_type_name', help_text='设备部件规格', default='')
    baoyang_standard_name = serializers.ReadOnlyField(source='maintenance_baoyang.standard_name', help_text='保养标准', default='')
    repair_standard_name = serializers.ReadOnlyField(source='equip_repair_standard.standard_name', help_text='维修标准', default='')
    xunjian_standard_name = serializers.ReadOnlyField(source='maintenance_xunjian.standard_name', help_text='巡检标准', default='')
    runhua_standard_name = serializers.ReadOnlyField(source='maintenance_runhua.standard_name', help_text='润滑标准', default='')
    biaoding_standard_name = serializers.ReadOnlyField(source='maintenance_biaoding.standard_name', help_text='标定标准', default='')

    class Meta:
        model = EquipBom
        fields = '__all__'


class EquipBomUpdateSerializer(BaseModelSerializer):

    class Meta:
        model = EquipBom
        fields = ('equip_area_define', 'maintenance_xunjian', 'maintenance_xunjian_flag', 'equip_repair_standard',
                  'equip_repair_standard_flag', 'maintenance_baoyang', 'maintenance_baoyang_flag', 'maintenance_runhua',
                  'maintenance_runhua_flag', 'maintenance_biaoding', 'maintenance_biaoding_flag')


class EquipMaintenanceAreaSettingSerializer(BaseModelSerializer):
    equip_no = serializers.CharField(source='equip.equip_no', read_only=True)
    equip_name = serializers.CharField(source='equip.equip_name', read_only=True)
    equip_part_name = serializers.CharField(source='equip_part.part_name', read_only=True, default='')
    equip_area_name = serializers.CharField(source='equip_area.area_name', read_only=True, default='')

    class Meta:
        model = EquipMaintenanceAreaSetting
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS
        validators = [UniqueTogetherValidator(queryset=EquipMaintenanceAreaSetting.objects.all(),
                                              fields=('maintenance_user', 'equip', 'equip_part'),
                                              message='请勿重复添加！'),
                      ]


class EquipJobItemStandardListSerializer(BaseModelSerializer):
    work_details = serializers.SerializerMethodField(help_text='作业详情')

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        details = EquipJobItemStandardDetail.objects.filter(equip_standard=instance).order_by('id')\
            .values('sequence', 'content', 'check_standard_desc', 'check_standard_type')
        work_details_column = check_standard_desc_column = check_standard_type_column = ''
        for detail in details:
            work_details_column += f"{detail['sequence']}、{detail['content']}；"
            check_standard_desc_column += f"{detail['sequence']}、{detail['check_standard_desc']}；"
            check_standard_type_column += f"{detail['sequence']}、{detail['check_standard_type']}；"
            ret.update({'work_details_column': work_details_column,
                        'check_standard_desc_column': check_standard_desc_column,
                        'check_standard_type_column': check_standard_type_column})
        return ret

    def get_work_details(self, obj):
        # 获取作业详情
        details = EquipJobItemStandardDetail.objects.filter(equip_standard=obj).values('id', 'sequence', 'content',
                                                                                       'check_standard_desc',
                                                                                       'check_standard_type')
        return details

    class Meta:
        model = EquipJobItemStandard
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipJobItemStandardDetailSerializer(BaseModelSerializer):

    class Meta:
        model = EquipJobItemStandardDetail
        fields = ('sequence', 'content', 'check_standard_desc', 'check_standard_type')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipJobItemStandardCreateSerializer(BaseModelSerializer):
    standard_code = serializers.CharField(max_length=64, help_text='作业标准编号',
                                          validators=[UniqueValidator(queryset=EquipJobItemStandard.objects.all(),
                                                                      message='作业标准编号已存在')])
    standard_name = serializers.CharField(max_length=64, help_text='作业标准名称',
                                          validators=[UniqueValidator(queryset=EquipJobItemStandard.objects.all(),
                                                                      message='作业标准名称已存在')])
    work_details = EquipJobItemStandardDetailSerializer(help_text="""
        [{"sequence": 1, "content": "外观检查", "check_standard_desc": "正常", "check_standard_type": "有无"}]""",
                                                        write_only=True, many=True)

    def create(self, validated_data):
        work_details = validated_data.pop('work_details', [])
        validated_data['created_user'] = self.context['request'].user
        instance = EquipJobItemStandard.objects.create(**validated_data)
        for detail in work_details:
            detail['equip_standard'] = instance
            EquipJobItemStandardDetail.objects.create(**detail)
        return validated_data

    class Meta:
        model = EquipJobItemStandard
        fields = ('work_type', 'standard_code', 'standard_name', 'work_details')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipJobItemStandardUpdateSerializer(BaseModelSerializer):
    standard_name = serializers.CharField(max_length=64, help_text='作业标准名称',
                                          validators=[UniqueValidator(queryset=EquipJobItemStandard.objects.all(),
                                                                      message='作业标准名称已存在')])
    work_details = EquipJobItemStandardDetailSerializer(help_text="""
        [{"sequence": 1, "content": "外观检查", "check_standard_desc": "正常", "check_standard_type": "有无"}]""",
                                                        write_only=True, many=True)

    def update(self, instance, validated_data):
        work_details = validated_data.pop('work_details', [])
        # 删除之前的作业内容
        EquipJobItemStandardDetail.objects.filter(equip_standard=instance.id).delete()
        validated_data['last_updated_user'] = self.context['request'].user
        for detail in work_details:
            detail['equip_standard'] = instance
            EquipJobItemStandardDetail.objects.create(**detail)
        return super().update(instance, validated_data)

    class Meta:
        model = EquipJobItemStandard
        fields = ('standard_name', 'work_details')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipMaintenanceStandardSerializer(BaseModelSerializer):
    standard_code = serializers.CharField(help_text='标准编号', max_length=64, validators=[
        UniqueValidator(queryset=EquipMaintenanceStandard.objects.all(), message='标准编号已存在')])
    standard_name = serializers.CharField(help_text='标准名称', max_length=64, validators=[
        UniqueValidator(queryset=EquipMaintenanceStandard.objects.all(), message='标准名称已存在')])
    equip_type_name = serializers.ReadOnlyField(source='equip_type.category_name', help_text='设备种类')
    equip_part_name = serializers.ReadOnlyField(source='equip_part.part_name', help_text='部位名称')
    equip_component_name = serializers.ReadOnlyField(source='equip_component.component_name', help_text='部件名称')
    equip_job_item_standard_name = serializers.ReadOnlyField(source='equip_job_item_standard.standard_name', help_text='作业项目')
    equip_job_item_standard_detail = serializers.SerializerMethodField()
    spare_list = serializers.SerializerMethodField()
    spare_list_str = serializers.SerializerMethodField()

    def get_spare_list(self, obj):
        spare_list = EquipMaintenanceStandardMaterials.objects.filter(equip_maintenance_standard=obj).values(
            'equip_spare_erp__id', 'equip_spare_erp__spare_code', 'equip_spare_erp__spare_name', 'equip_spare_erp__specification',
            'equip_spare_erp__technical_params', 'quantity', 'equip_spare_erp__unit')

        return spare_list

    def get_spare_list_str(self, obj):
        spare_list = EquipMaintenanceStandardMaterials.objects.filter(equip_maintenance_standard=obj).values('equip_spare_erp__spare_name')
        data = ','.join([i.get('equip_spare_erp__spare_name') for i in spare_list])
        return data

    def get_equip_job_item_standard_detail(self, obj):
        data = EquipJobItemStandardDetail.objects.filter(equip_standard=obj.equip_job_item_standard).values('sequence', 'content')
        res = [f"{i['sequence']}、{i['content']}；" for i in data]
        return ''.join(res)

    class Meta:
        model = EquipMaintenanceStandard
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipMaintenanceStandardImportSerializer(BaseModelSerializer):
    standard_code = serializers.CharField(help_text='标准编号', max_length=64, validators=[
        UniqueValidator(queryset=EquipMaintenanceStandard.objects.all(), message='标准编号已存在')])
    standard_name = serializers.CharField(help_text='标准名称', max_length=64, validators=[
        UniqueValidator(queryset=EquipMaintenanceStandard.objects.all(), message='标准名称已存在')])
    spares = serializers.CharField(write_only=True, default='')

    class Meta:
        model = EquipMaintenanceStandard
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipRepairStandardSerializer(BaseModelSerializer):
    standard_code = serializers.CharField(help_text='标准编号', max_length=64, validators=[
        UniqueValidator(queryset=EquipRepairStandard.objects.all(), message='标准编号已存在')])
    standard_name = serializers.CharField(help_text='标准名称', max_length=64, validators=[
        UniqueValidator(queryset=EquipRepairStandard.objects.all(), message='标准名称已存在')])
    equip_type_name = serializers.ReadOnlyField(source='equip_type.category_name', help_text='设备种类')
    equip_part_name = serializers.ReadOnlyField(source='equip_part.part_name', help_text='部位名称')
    equip_component_name = serializers.ReadOnlyField(source='equip_component.component_name', help_text='部件名称')
    equip_fault_name = serializers.ReadOnlyField(source='equip_fault.fault_name', help_text='故障分类')
    equip_job_item_standard_name = serializers.ReadOnlyField(source='equip_job_item_standard.standard_name', help_text='作业项目')
    equip_job_item_standard_detail = serializers.SerializerMethodField()
    spare_list = serializers.SerializerMethodField()
    spare_list_str = serializers.SerializerMethodField()

    def get_spare_list(self, obj):
        spare_list = EquipRepairStandardMaterials.objects.filter(equip_repair_standard=obj).values(
            'equip_spare_erp__id', 'equip_spare_erp__spare_code', 'equip_spare_erp__spare_name', 'equip_spare_erp__specification',
            'equip_spare_erp__technical_params', 'quantity', 'equip_spare_erp__unit')
        return spare_list

    def get_spare_list_str(self, obj):
        spare_list = EquipRepairStandardMaterials.objects.filter(equip_repair_standard=obj).values('equip_spare_erp__spare_name')
        data = ','.join([i.get('equip_spare_erp__spare_name') for i in spare_list])
        return data

    def get_equip_job_item_standard_detail(self, obj):
        data = EquipJobItemStandardDetail.objects.filter(equip_standard=obj.equip_job_item_standard).values('sequence', 'content')
        res = [f"{i['sequence']}、{i['content']}；" for i in data]
        return ''.join(res)

    class Meta:
        model = EquipRepairStandard
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipRepairStandardImportSerializer(BaseModelSerializer):
    standard_code = serializers.CharField(help_text='标准编号', max_length=64, validators=[
        UniqueValidator(queryset=EquipMaintenanceStandard.objects.all(), message='标准编号已存在')])
    standard_name = serializers.CharField(help_text='标准名称', max_length=64, validators=[
        UniqueValidator(queryset=EquipMaintenanceStandard.objects.all(), message='标准名称已存在')])
    spares = serializers.CharField(write_only=True, default='')

    class Meta:
        model = EquipRepairStandard
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS

# class EquipWarehouseAreaSerializer(BaseModelSerializer):
#     area_name = serializers.CharField(max_length=64, help_text='库区名称',
#                                       validators=[UniqueValidator(queryset=EquipWarehouseArea.objects.filter(use_flag=1),
#                                                                   message='库区名称已存在')])
#     equip_component_type_name = serializers.ReadOnlyField(source='equip_component_type__component_type_name', help_text='备件分类名称')
#
#     class Meta:
#         model = EquipWarehouseArea
#         fields = '__all__'

