import json
import uuid
from datetime import datetime, date

from django.db.models import Max, Q, Sum
from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator, UniqueValidator

from basics.models import Equip, GlobalCode
from basics.models import WorkSchedulePlan
from equipment.models import EquipDownType, EquipDownReason, EquipCurrentStatus, EquipMaintenanceOrder, EquipPart, \
    EquipSupplier, EquipProperty, EquipAreaDefine, EquipPartNew, \
    EquipComponent, EquipComponentType, ERPSpareComponentRelation, EquipSpareErp, EquipFaultType, EquipFault, \
    PropertyTypeNode, Property, PlatformConfig, EquipFaultSignal, EquipMachineHaltType, EquipMachineHaltReason, \
    EquipOrderAssignRule, EquipMaintenanceAreaSetting, EquipBom, EquipJobItemStandardDetail, EquipJobItemStandard, \
    EquipMaintenanceStandard, EquipMaintenanceStandardMaterials, EquipRepairStandard, EquipRepairStandardMaterials, \
    EquipWarehouseLocation, EquipWarehouseArea, EquipWarehouseOrderDetail, EquipWarehouseOrder, EquipWarehouseInventory, \
    EquipWarehouseRecord, EquipApplyRepair, EquipPlan, EquipApplyOrder, EquipResultDetail, UploadImage, \
    EquipRepairMaterialReq, EquipInspectionOrder, EquipWarehouseAreaComponent, EquipRegulationRecord, \
    EquipMaintenanceStandardWork

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
                                          validators=[
                                              UniqueValidator(queryset=EquipSupplier.objects.all(), message='该编码已存在')])
    supplier_name = serializers.CharField(help_text='供应商名称', max_length=64,
                                          validators=[
                                              UniqueValidator(queryset=EquipSupplier.objects.filter(use_flag=True),
                                                              message='该供应商已存在')])
    use_flag_name = serializers.SerializerMethodField()

    def get_use_flag_name(self, obj):
        return 'Y' if obj.use_flag else 'N'

    class Meta:
        model = EquipSupplier
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipComponentListSerializer(BaseModelSerializer):
    equip_part_name = serializers.CharField(source='equip_part.part_name', help_text='所属设备部位', max_length=64)
    equip_component_type_name = serializers.CharField(source='equip_component_type.component_type_name',
                                                      help_text='所属部件分类', max_length=64)
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
    equip_type_name = serializers.ReadOnlyField(source="equip_type.equip_type.global_name", read_only=True,
                                                help_text='设备型号')
    made_in = serializers.ReadOnlyField(source='equip_supplier.supplier_name', help_text='设备制造商', default='')
    price = serializers.DecimalField(max_digits=20, decimal_places=2)

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


class EquipPropertyCreatSerializer(BaseModelSerializer):

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
                                      validators=[
                                          UniqueValidator(queryset=EquipAreaDefine.objects.all(), message='该名称已存在')])
    area_code = serializers.CharField(help_text='位置区域编号', max_length=64,
                                      validators=[
                                          UniqueValidator(queryset=EquipAreaDefine.objects.all(), message='该编号已存在')])
    use_flag_name = serializers.SerializerMethodField()

    def get_use_flag_name(self, obj):
        return 'Y' if obj.use_flag else 'N'

    class Meta:
        model = EquipAreaDefine
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipPartNewSerializer(BaseModelSerializer):
    part_code = serializers.CharField(help_text='部位编码', max_length=64,
                                      validators=[
                                          UniqueValidator(queryset=EquipPartNew.objects.all(), message='该编码已存在')])
    part_name = serializers.CharField(help_text='设备名称', max_length=64,
                                      validators=[
                                          UniqueValidator(queryset=EquipPartNew.objects.all(), message='该名称已存在')])
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
        extra_kwargs = {'equip_fault': {"required": False}}


class EquipComponentTypeSerializer(BaseModelSerializer):
    # 设备部件分类
    component_type_code = serializers.CharField(help_text='分类编号', max_length=64,
                                                validators=[UniqueValidator(queryset=EquipComponentType.objects.all(),
                                                                            message='该编号已存在')])
    component_type_name = serializers.CharField(help_text='分类名称', max_length=64,
                                                validators=[UniqueValidator(queryset=EquipComponentType.objects.all(),
                                                                            message='该名称已存在')])

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
    use_flag_name = serializers.SerializerMethodField()
    equip_type_name = serializers.ReadOnlyField(source='equip_type.global_name')

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
    equip_component_type_name = serializers.CharField(source='equip_spare_erp.equip_component_type.component_type_name',
                                                      help_text='备件分类', max_length=64)
    spare_code = serializers.CharField(source='equip_spare_erp.spare_code', help_text='备件编码', max_length=64)
    spare_name = serializers.CharField(source='equip_spare_erp.spare_name', help_text='备件名称', max_length=64)
    supplier_name = serializers.CharField(source='equip_spare_erp.supplier_name', help_text='供应商名称', max_length=64)

    class Meta:
        model = ERPSpareComponentRelation
        fields = '__all__'


class EquipSpareErpListSerializer(BaseModelSerializer):
    equip_component_type_name = serializers.CharField(source='equip_component_type.component_type_name',
                                                      help_text='备件分类', max_length=64)
    key_parts_flag_name = serializers.SerializerMethodField()
    use_flag_name = serializers.SerializerMethodField()
    cost = serializers.SerializerMethodField()

    def get_cost(self, obj):
        return round(obj.cost if obj.cost else 0, 2)

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


class EquipSpareErpImportCreateSerializer(BaseModelSerializer):
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
                  'period_validity', 'use_flag', 'info_source')


class ERPSpareComponentRelationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ERPSpareComponentRelation
        fields = '__all__'


class EquipFaultTypeSerializer(BaseModelSerializer):
    """设备故障分类类型序列化器"""
    fault_type_code = serializers.CharField(max_length=64,
                                            validators=[
                                                UniqueValidator(queryset=EquipFaultType.objects.all(),
                                                                message='该代码类型编号已存在'),
                                            ])
    fault_type_name = serializers.CharField(max_length=64,
                                            validators=[
                                                UniqueValidator(
                                                    queryset=EquipFaultType.objects.filter(delete_flag=False),
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
    component_type = serializers.ReadOnlyField(source='component.equip_component_type.component_type_name',
                                               help_text='设备部件规格', default='')
    baoyang_standard_name = serializers.ReadOnlyField(source='maintenance_baoyang.standard_name', help_text='保养标准',
                                                      default='')
    repair_standard_name = serializers.ReadOnlyField(source='equip_repair_standard.standard_name', help_text='维修标准',
                                                     default='')
    xunjian_standard_name = serializers.ReadOnlyField(source='maintenance_xunjian.standard_name', help_text='巡检标准',
                                                      default='')
    runhua_standard_name = serializers.ReadOnlyField(source='maintenance_runhua.standard_name', help_text='润滑标准',
                                                     default='')
    biaoding_standard_name = serializers.ReadOnlyField(source='maintenance_biaoding.standard_name', help_text='标定标准',
                                                       default='')
    part_name = serializers.ReadOnlyField(source='part.part_name', default='')
    component_name = serializers.ReadOnlyField(source='component.component_name', default='')
    equip_no = serializers.ReadOnlyField(source='equip_info.equip_no', default='')
    equip_name = serializers.ReadOnlyField(source='equip_info.equip_name', default='')
    equip_status = serializers.SerializerMethodField()
    property_type_node = serializers.ReadOnlyField(source='property_type.global_name', default='')
    part_type = serializers.ReadOnlyField(source='part.global_part_type.global_name', help_text='部位分类', default='')

    def get_equip_status(self, obj):
        if obj.equip_info:
            return '启用' if obj.equip_info.use_flag else '停用'
        return ''

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
    workshop = serializers.CharField(source='maintenance_user.workshop', read_only=True, default='')

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
        details = EquipJobItemStandardDetail.objects.filter(equip_standard=instance).order_by('id') \
            .values('sequence', 'content', 'check_standard_desc', 'check_standard_type', 'unit')
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
        details = EquipJobItemStandardDetail.objects.filter(equip_standard=obj).order_by('id') \
            .values('id', 'sequence', 'content', 'check_standard_desc', 'check_standard_type', 'unit')
        return details

    class Meta:
        model = EquipJobItemStandard
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipJobItemStandardDetailSerializer(BaseModelSerializer):
    class Meta:
        model = EquipJobItemStandardDetail
        fields = ('sequence', 'content', 'check_standard_desc', 'check_standard_type', 'unit')
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

    def validate(self, attrs):
        work_details = attrs['work_details']
        for detail in work_details:
            check_standard_desc = detail['check_standard_desc']
            check_standard_type = detail['check_standard_type']
            if check_standard_type == '数值范围':
                try:
                    m, n = check_standard_desc.split('-')
                    assert eval(m) <= eval(n)
                except:
                    raise serializers.ValidationError('数值范围不正确')
                else:
                    continue
            if check_standard_desc not in check_standard_type or check_standard_desc not in ['有', '无', '合格', '不合格',
                                                                                             '完成', '未完成', '正常', '异常']:
                raise serializers.ValidationError('判断标准不正确')
        return attrs

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
        fields = ('work_type', 'standard_name', 'work_details')
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipMaintenanceStandardSerializer(BaseModelSerializer):
    standard_code = serializers.CharField(help_text='标准编号', max_length=64, validators=[
        UniqueValidator(queryset=EquipMaintenanceStandard.objects.all(), message='标准编号已存在')])
    equip_part_name = serializers.ReadOnlyField(source='equip_part.part_name', help_text='部位名称', default='')
    equip_component_name = serializers.ReadOnlyField(source='equip_component.component_name', help_text='部件名称')
    equip_job_item_standard_name = serializers.ReadOnlyField(source='equip_job_item_standard.standard_name',
                                                             help_text='作业项目', default='')
    specification = serializers.ReadOnlyField(source='maintenance_materials.equip_spare_erp.specification',
                                              help_text='所需物料规格')
    quantity = serializers.ReadOnlyField(source='maintenance_materials.quantity', help_text='物料数量')
    unit = serializers.ReadOnlyField(source='maintenance_materials.equip_spare_erp.unit', help_text='物料数量单位')
    equip = serializers.ReadOnlyField(source='equip_no')
    equip_job_item_standard_detail = serializers.SerializerMethodField()
    spare_list = serializers.SerializerMethodField()
    work_list = serializers.SerializerMethodField()
    equip_no = serializers.SerializerMethodField()

    def to_representation(self, instance):
        res = super().to_representation(instance)

        detail_list = EquipJobItemStandardDetail.objects.filter(equip_standard=res.get('equip_job_item_standard')) \
            .values('id', 'equip_standard', 'sequence', 'content', 'check_standard_desc', 'check_standard_type')
        res['detail_list'] = detail_list

        return res

    def get_spare_list(self, obj):
        spare_list = EquipMaintenanceStandardMaterials.objects.filter(equip_maintenance_standard=obj).values(
            'equip_spare_erp__id', 'equip_spare_erp__spare_code', 'equip_spare_erp__spare_name',
            'equip_spare_erp__specification',
            'equip_spare_erp__technical_params', 'quantity', 'equip_spare_erp__unit')
        return spare_list

    def get_work_list(self, obj):
        work_list = EquipMaintenanceStandardWork.objects.filter(equip_maintenance_standard=obj).values(
            'equip_area_define__id',
            'equip_area_define__inspection_line_no',
            'equip_area_define__area_code',
            'equip_area_define__area_name',
            'equip_part__id',
            'equip_part__part_name',
            'equip_component__id',
            'equip_component__component_name',
            'equip_job_item_standard__id',
            'equip_job_item_standard__standard_name'
        ).order_by('id')
        for work in work_list:
            details = EquipJobItemStandardDetail.objects.filter(equip_standard_id=work['equip_job_item_standard__id']).order_by('id') \
                .values('sequence', 'content')
            work_details_column = ''
            for detail in details:
                work_details_column += f"{detail['sequence']}、{detail['content']}；"
            work['work_details_column'] = work_details_column
        return work_list

    # def get_spare_list_str(self, obj):
    #     spare_list = EquipMaintenanceStandardMaterials.objects.filter(equip_maintenance_standard=obj).values(
    #         'equip_spare_erp__spare_name')
    #     data = ','.join([i.get('equip_spare_erp__spare_name') for i in spare_list])
    #     return data

    def get_equip_job_item_standard_detail(self, obj):
        data = EquipJobItemStandardDetail.objects.filter(equip_standard=obj.equip_job_item_standard).values('sequence',
                                                                                                            'content')
        res = [f"{i['sequence']}、{i['content']}；" for i in data]
        return ''.join(res)

    def get_equip_no(self, obj):
        return obj.equip_no.split('，')

    class Meta:
        model = EquipMaintenanceStandard
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipMaintenanceStandardCreateSerializer(BaseModelSerializer):
    equip_no = serializers.ListField(write_only=True, default=[])

    def validate_equip_no(self, equip_no):
        return '，'.join(equip_no)

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
    equip_part_name = serializers.ReadOnlyField(source='equip_part.part_name', help_text='部位名称')
    equip_component_name = serializers.ReadOnlyField(source='equip_component.component_name', help_text='部件名称')
    equip_fault_name = serializers.ReadOnlyField(source='equip_fault.fault_name', help_text='故障分类')
    equip_job_item_standard_name = serializers.ReadOnlyField(source='equip_job_item_standard.standard_name',
                                                             help_text='作业项目')
    specification = serializers.ReadOnlyField(source='repair_materials.equip_spare_erp.specification',
                                              help_text='所需物料规格')
    quantity = serializers.ReadOnlyField(source='repair_materials.quantity', help_text='物料数量')
    unit = serializers.ReadOnlyField(source='repair_materials.equip_spare_erp.unit', help_text='物料数量单位')
    equip = serializers.ReadOnlyField(source='equip_no')
    equip_job_item_standard_detail = serializers.SerializerMethodField()
    spare_list = serializers.SerializerMethodField()
    spare_list_str = serializers.SerializerMethodField()
    equip_no = serializers.SerializerMethodField()

    def to_representation(self, instance):
        res = super().to_representation(instance)
        # detail_list = []
        detail_list = EquipJobItemStandardDetail.objects.filter(equip_standard=res.get('equip_job_item_standard')) \
            .values('id', 'equip_standard', 'sequence', 'content', 'check_standard_desc', 'check_standard_type')
        res['detail_list'] = detail_list
        return res

    def get_spare_list(self, obj):
        spare_list = EquipRepairStandardMaterials.objects.filter(equip_repair_standard=obj).values(
            'equip_spare_erp__id', 'equip_spare_erp__spare_code', 'equip_spare_erp__spare_name',
            'equip_spare_erp__specification',
            'equip_spare_erp__technical_params', 'quantity', 'equip_spare_erp__unit')
        return spare_list

    def get_spare_list_str(self, obj):
        spare_list = EquipRepairStandardMaterials.objects.filter(equip_repair_standard=obj).values(
            'equip_spare_erp__spare_name')
        data = ','.join([i.get('equip_spare_erp__spare_name') for i in spare_list])
        return data

    def get_equip_job_item_standard_detail(self, obj):
        data = EquipJobItemStandardDetail.objects.filter(equip_standard=obj.equip_job_item_standard).values('sequence',
                                                                                                            'content')
        res = [f"{i['sequence']}、{i['content']}；" for i in data]
        return ''.join(res)

    def get_equip_no(self, obj):
        return obj.equip_no.split('，')

    class Meta:
        model = EquipRepairStandard
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipRepairStandardCreateSerializer(BaseModelSerializer):

    equip_no = serializers.ListField(write_only=True, default=[])

    def validate_equip_no(self, equip_no):
        return '，'.join(equip_no)

    class Meta:
        model = EquipRepairStandard
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipRepairStandardImportSerializer(BaseModelSerializer):
    standard_code = serializers.CharField(help_text='标准编号', max_length=64, validators=[
        UniqueValidator(queryset=EquipMaintenanceStandard.objects.all(), message='标准编号已存在')])
    standard_name = serializers.CharField(help_text='标准名称', max_length=64, validators=[
        UniqueValidator(queryset=EquipMaintenanceStandard.objects.all(), message='标准名称已存在')])

    class Meta:
        model = EquipRepairStandard
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS


class EquipApplyRepairSerializer(BaseModelSerializer):
    part_name = serializers.ReadOnlyField(source='equip_part_new.part_name', help_text='部位名称')
    result_fault_cause_name = serializers.ReadOnlyField(source='result_fault_cause', help_text='故障原因名称')
    image_url_list = serializers.ListField(help_text='报修图片地址列表', write_only=True, default=[])
    inspection_order = serializers.IntegerField(default=None)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        apply_repair_graph_url = ret.get('apply_repair_graph_url') if ret.get('apply_repair_graph_url') else '[]'
        ret.update({'apply_repair_graph_url': json.loads(apply_repair_graph_url)})
        return ret

    @atomic
    def create(self, validated_data):
        # 生成报修编号
        now_time = ''.join(str(datetime.now().date()).split('-'))
        max_code = EquipPlan.objects.filter(plan_id__startswith=f'BX{now_time}').aggregate(max_code=Max('plan_id'))['max_code']
        sequence = '%04d' % (int(max_code[-4:]) + 1) if max_code else '0001'
        validated_data.update({
            'plan_id': f'BX{now_time}{sequence}', 'status': '已生成',
            'apply_repair_graph_url': json.dumps(validated_data.pop('image_url_list')),
            'plan_name': f"{validated_data['plan_department']}{f'BX{now_time}{sequence}'}"
        })
        # 生成维修计划
        equip_plan_data = {
            'work_type': '维修', 'plan_id': validated_data['plan_id'], 'plan_name': validated_data['plan_name'],
            'equip_no': validated_data['equip_no'], 'equip_condition': validated_data['equip_condition'],
            'importance_level': validated_data.get('importance_level', '高'), 'status': '已生成工单',
            'created_user': self.context['request'].user,
            'planned_maintenance_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        EquipPlan.objects.create(**equip_plan_data)
        # 生成维修工单
        max_order_code = EquipApplyOrder.objects.filter(work_order_no__startswith=validated_data['plan_id']).aggregate(
            max_order_code=Max('work_order_no'))['max_order_code']
        work_order_no = validated_data['plan_id'] + '-' + (
            '%04d' % (int(max_order_code.split('-')[-1]) + 1) if max_order_code else '0001')
        equip_order_data = {'plan_id': validated_data['plan_id'], 'plan_name': validated_data['plan_name'],
                            'work_order_no': work_order_no, 'equip_no': validated_data['equip_no'],
                            'status': '已生成', 'equip_condition': validated_data['equip_condition'],
                            'importance_level': validated_data.get('importance_level', '高'),
                            'created_user': self.context['request'].user,
                            'result_fault_cause': validated_data.get('result_fault_cause'),
                            'planned_repair_date': str(datetime.now().date())}
        if validated_data.get('equip_part_new'):
            equip_order_data['equip_part_new'] = validated_data.get('equip_part_new')
        if validated_data.get('result_fault_desc'):
            equip_order_data['result_fault_desc'] = validated_data.get('result_fault_desc')
        inspection_order = validated_data.pop('inspection_order', None)
        if inspection_order:
            equip_order_data['inspection_order_id'] = inspection_order
        EquipApplyOrder.objects.create(**equip_order_data)
        return super().create(validated_data)

    class Meta:
        model = EquipApplyRepair
        fields = '__all__'


class EquipRepairMaterialReqSerializer(BaseModelSerializer):
    spare_code = serializers.ReadOnlyField(source='equip_spare.spare_code', help_text='备件编码')
    spare_name = serializers.ReadOnlyField(source='equip_spare.spare_name', help_text='备件名称')
    equip_component_type_name = serializers.ReadOnlyField(source='equip_spare.equip_component_type.component_type_name',
                                                          help_text='备件分类')
    specification = serializers.ReadOnlyField(source='equip_spare.specification', help_text='规格型号')
    technical_params = serializers.ReadOnlyField(source='equip_spare.technical_params', help_text='技术参数')
    unit = serializers.ReadOnlyField(source='equip_spare.unit', help_text='标准单位')

    def to_representation(self, instance):
        instance = super().to_representation(instance)
        out_record = EquipWarehouseOrder.objects.filter(order_id=instance['warehouse_out_no']).first()
        instance.update({'out_record_status': out_record.status_name, 'warehouse_out_no': instance['warehouse_out_no']})
        return instance

    class Meta:
        model = EquipRepairMaterialReq
        fields = '__all__'


class EquipApplyOrderSerializer(BaseModelSerializer):
    part_name = serializers.ReadOnlyField(source='equip_part_new.part_name', help_text='部位名称', default='')
    equip_repair_standard_name = serializers.ReadOnlyField(source='equip_repair_standard.standard_code',
                                                           help_text='维修标准名', default='')
    equip_maintenance_standard_name = serializers.ReadOnlyField(source='equip_maintenance_standard.standard_code',
                                                                help_text='维护标准名', default='')
    result_fault_cause_name = serializers.ReadOnlyField(source='result_fault_cause', help_text='故障原因名称',
                                                        default='')
    result_repair_standard_name = serializers.ReadOnlyField(source='result_repair_standard.standard_code',
                                                            help_text='实际维修标准名称', default='')
    result_maintenance_standard_name = serializers.ReadOnlyField(source='result_maintenance_standard.standard_code',
                                                                 help_text='实际维护标准名称', default='')
    work_persons = serializers.ReadOnlyField(source='equip_repair_standard.cycle_person_num', help_text='作业标准人数',
                                             default='')
    equip_barcode = serializers.SerializerMethodField(help_text='设备条码')
    equip_type = serializers.SerializerMethodField(help_text='设备机型')
    work_content = serializers.ListField(help_text='实际维修标准列表', write_only=True, default=[])
    image_url_list = serializers.ListField(help_text='图片列表', write_only=True, default=[])
    apply_material_list = EquipRepairMaterialReqSerializer(help_text='申请物料列表', write_only=True, many=True, default=[])
    repair_users = serializers.SerializerMethodField(help_text='维修人')

    def get_equip_type(self, obj):
        instance = Equip.objects.filter(equip_no=obj.equip_no).first()
        return instance.category_id if instance else ''

    def get_equip_barcode(self, obj):
        instance = EquipApplyRepair.objects.filter(plan_id=obj.plan_id).first()
        return instance.equip_barcode if instance else ''

    def get_repair_users(self, obj):
        user = obj.repair_user
        return user.split('，') if user else None

    def to_representation(self, instance):
        res = super().to_representation(instance)
        work_content = []
        result_repair_graph_url = res.get('result_repair_graph_url') if res.get('result_repair_graph_url') else '[]'
        result_accept_graph_url = res.get('result_accept_graph_url') if res.get('result_accept_graph_url') else '[]'
        res.update({'result_repair_graph_url': json.loads(result_repair_graph_url),
                    'result_accept_graph_url': json.loads(result_accept_graph_url)})
        # 是否申请物料
        is_applyed = EquipRepairMaterialReq.objects.filter(work_order_no=res['work_order_no']).first()
        res['is_applyed'] = True if is_applyed else False
        if res['work_type'] == '维修':
            instance = EquipRepairStandard.objects.filter(id=res.get('result_repair_standard')).first()
        else:
            instance = EquipMaintenanceStandard.objects.filter(id=res.get('result_maintenance_standard')).first()
        if instance:
            data = EquipResultDetail.objects.filter(work_order_no=res['work_order_no'],
                                                    equip_jobitem_standard=instance.equip_job_item_standard)
            if data:
                for i in data:
                    work_content.append(
                        {'job_item_sequence': i.job_item_sequence, 'job_item_content': i.job_item_content,
                         'job_item_check_standard': i.job_item_check_standard,
                         'equip_jobitem_standard_id': i.equip_jobitem_standard_id,
                         'operation_result': i.operation_result, 'job_item_check_type': i.job_item_check_type})
                work_content.sort(key=lambda x: x['job_item_sequence'])
        res['work_content'] = work_content
        out_order = EquipRepairMaterialReq.objects.filter(work_order_no=res['work_order_no']).first()
        res['warehouse_out_no'] = out_order.warehouse_out_no if out_order else ''
        # 报修图片
        instance_apply = EquipApplyRepair.objects.filter(plan_id=res.get('plan_id')).first()
        res['apply_repair_graph_url'] = json.loads(instance_apply.apply_repair_graph_url) if instance_apply else []
        # 区域位置
        bom_obj = EquipBom.objects.filter(equip_info__equip_no=res.get('equip_no')).first()
        res['are_name'] = bom_obj.equip_area_define.area_name if bom_obj and bom_obj.equip_area_define else ''
        # 部门
        prod = GlobalCode.objects.filter(delete_flag=False, global_type__use_flag=1,
                                         global_type__type_name='设备部门组织名称').first()
        res['product_name'] = prod.global_name if prod else ''
        return res

    @atomic
    def update(self, instance, validated_data):
        work_type = instance.work_type
        work_content = validated_data.pop('work_content')
        image_url_list = validated_data.pop('image_url_list')
        apply_material_list = validated_data.pop('apply_material_list')
        # 更新作业内容
        if work_type == "维修":
            result_standard = validated_data.get('result_repair_standard')
            result_standard_id = result_standard.id if result_standard else 0
            instance_standard = EquipRepairStandard.objects.filter(id=result_standard_id).first()
        else:
            result_standard = validated_data.get('result_maintenance_standard')
            result_standard_id = result_standard.id if result_standard else 0
            instance_standard = EquipMaintenanceStandard.objects.filter(id=result_standard_id).first()
        if instance_standard:
            EquipResultDetail.objects.filter(work_order_no=instance.work_order_no).delete()
            for item in work_content:
                item.update({'work_type': instance.work_type, 'work_order_no': instance.work_order_no})
                EquipResultDetail.objects.create(**item)
        validated_data['result_repair_graph_url'] = json.dumps(image_url_list)
        for apply_material in apply_material_list:
            EquipRepairMaterialReq.objects.create(**apply_material)
        # 更新报修申请工单状态
        if validated_data.get('result_repair_final_result') == '等待':
            validated_data['last_updated_date'] = datetime.now()
        else:
            if instance.created_user.username == '系统自动':
                validated_data.update({'repair_end_datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                       'last_updated_date': datetime.now(), 'status': '已验收', 'accept_user': '系统自动',
                                       'accept_datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                       'result_accept_desc': '验收通过', 'result_accept_result': '合格'})
            else:
                validated_data.update({'repair_end_datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                       'last_updated_date': datetime.now(), 'status': '已完成',
                                       'accept_user': instance.created_user.username})
        EquipApplyRepair.objects.filter(plan_id=instance.plan_id).update(status=validated_data.get('status'))
        # 记录到增减人员履历中
        queryset = EquipRegulationRecord.objects.filter(plan_id=instance.plan_id, status='增')
        for obj in queryset:
            obj.end_time = datetime.now()
            obj.use_time += float('%.2f' % ((datetime.now() - obj.begin_time).total_seconds() / 60))
            obj.save()
        response = super().update(instance, validated_data)
        return response

    class Meta:
        model = EquipApplyOrder
        fields = '__all__'
        read_only_fields = ['result_repair_graph_url', 'result_accept_graph_url']


class EquipApplyOrderExportSerializer(BaseModelSerializer):

    def to_representation(self, instance):
        res = super().to_representation(instance)
        # 故障原因
        fault_reason = instance.result_fault_cause if instance.result_fault_cause else (
            instance.equip_repair_standard.standard_name if instance.equip_repair_standard else instance.equip_maintenance_standard.standard_name)
        result_fault_reason = instance.result_repair_standard.standard_name if instance.result_repair_standard else (
            instance.result_maintenance_standard.standard_name if instance.result_maintenance_standard else '')
        res['fault_reason'] = fault_reason
        res['result_fault_reason'] = result_fault_reason
        res['part_name'] = instance.equip_part_new.part_name if instance.equip_part_new else ''
        res['result_material_requisition'] = 'Y' if res['result_material_requisition'] else 'N'
        res['result_need_outsourcing'] = 'Y' if res['result_need_outsourcing'] else 'N'
        res['wait_material'] = 'Y' if res['wait_material'] else 'N'
        res['wait_outsourcing'] = 'Y' if res['wait_outsourcing'] else 'N'
        return res

    class Meta:
        model = EquipApplyOrder
        fields = '__all__'


class EquipInspectionOrderSerializer(BaseModelSerializer):
    equip_repair_standard_name = serializers.ReadOnlyField(source='equip_repair_standard.standard_code',
                                                           help_text='维护标准名', default='')
    work_persons = serializers.ReadOnlyField(source='equip_maintenance_standard.cycle_person_num', help_text='作业标准人数',
                                             default='')
    type = serializers.ReadOnlyField(source='equip_repair_standard.type', help_text='类别(机械/电气)', default='')
    area_name = serializers.ReadOnlyField(source='equip_maintenance_standard_work.equip_area_define.area_name', help_text='巡检区域名称')
    equip_type = serializers.SerializerMethodField(help_text='设备机型')
    work_content = serializers.ListField(help_text='实际巡检标准列表', write_only=True, default=[])
    image_url_list = serializers.ListField(help_text='图片列表', write_only=True, default=[])
    plan_name = serializers.CharField(max_length=64, help_text='巡检计划名称', validators=[
        UniqueValidator(queryset=EquipInspectionOrder.objects.all(), message='巡检计划名称已存在')
    ])
    repair_users = serializers.SerializerMethodField(help_text='巡检人')
    lot_no = serializers.ReadOnlyField(source='equip_maintenance_standard_work.lot_no', help_text='巡检区域条码')
    part_name = serializers.ReadOnlyField(source='equip_maintenance_standard_work.equip_part.part_name', help_text='巡检区域部位')
    part_name_id = serializers.ReadOnlyField(source='equip_maintenance_standard_work.equip_part.id', help_text='巡检区域部位id')
    component_name = serializers.ReadOnlyField(source='equip_maintenance_standard_work.equip_component.component_name', help_text='巡检区域部件')

    def get_equip_type(self, obj):
        instance = Equip.objects.filter(equip_no=obj.equip_no).first()
        return instance.category_id if instance else ''

    def get_repair_users(self, obj):
        user = obj.repair_user
        return user.split('，') if user else None

    def to_representation(self, instance):
        res = super().to_representation(instance)
        work_content = []
        result_repair_graph_url = res.get('result_repair_graph_url') if res.get('result_repair_graph_url') else '[]'
        res.update({'result_repair_graph_url': json.loads(result_repair_graph_url)})
        instance = EquipMaintenanceStandardWork.objects.filter(id=res.get('equip_maintenance_standard_work')).first()

        if instance:
            data = EquipResultDetail.objects.filter(work_order_no=res['work_order_no'],
                                                    equip_jobitem_standard=instance.equip_job_item_standard)
            if data:
                for i in data:
                    abnormal_operation_url = []
                    if i.abnormal_operation_url:
                        abnormal_operation_url = json.dumps(i.abnormal_operation_url) if isinstance(i.abnormal_operation_url, list) else json.loads(i.abnormal_operation_url)
                    work_content.append(
                        {'job_item_sequence': i.job_item_sequence, 'job_item_content': i.job_item_content,
                         'job_item_check_standard': i.job_item_check_standard,
                         'equip_jobitem_standard_id': i.equip_jobitem_standard_id,
                         'unit': i.equip_jobitem_standard.standard_detail.unit,
                         'operation_result': i.operation_result, 'job_item_check_type': i.job_item_check_type,
                         'abnormal_operation_desc': i.abnormal_operation_desc,
                         'abnormal_operation_result': i.abnormal_operation_result,
                         'abnormal_operation_url': abnormal_operation_url,
                         'uid': i.id
                         })
            else:
                data = EquipJobItemStandardDetail.objects.filter(equip_standard=instance.equip_job_item_standard) \
                    .values('id', 'equip_standard', 'sequence', 'content', 'check_standard_desc', 'check_standard_type', 'unit')
                for i in data:
                    work_content.append(
                        {'job_item_sequence': i.get('sequence'), 'job_item_content': i.get('content'),
                         'job_item_check_standard': i.get('check_standard_desc'),
                         'equip_jobitem_standard_id': i.get('equip_standard'),
                         'job_item_check_type': i.get('check_standard_type'),
                         'unit': i.get('unit'),
                         'uid': i.get('id')})
            work_content.sort(key=lambda x: x['job_item_sequence'])
        res['work_content'] = work_content
        # 区域位置
        bom_obj = EquipBom.objects.filter(equip_info__equip_no=res.get('equip_no')).first()
        res['are_name'] = bom_obj.equip_area_define.area_name if bom_obj and bom_obj.equip_area_define else ''
        # 部门
        prod = GlobalCode.objects.filter(delete_flag=False, global_type__use_flag=1,
                                         global_type__type_name='设备部门组织名称').first()
        res['product_name'] = prod.global_name if prod else ''
        return res

    @atomic
    def create(self, validated_data):
        work_content = validated_data.pop('work_content')
        image_url_list = validated_data.pop('image_url_list')
        # 生成巡检计划号
        now_time = ''.join(str(datetime.now().date()).split('-'))
        max_code = EquipInspectionOrder.objects.aggregate(max_code=Max('plan_id'))['max_code']
        sequence = '%04d' % (int(max_code[-4:]) + 1) if max_code else '0001'
        plan_id = f'XJ{now_time}{sequence}'
        # 生成巡检工单编号
        max_order_code = EquipInspectionOrder.objects.filter(work_order_no__startswith=plan_id).aggregate(
            max_order_code=Max('work_order_no'))['max_order_code']
        work_order_no = plan_id + '-' + ('%04d' % (int(max_order_code.split('-')[-1]) + 1) if max_order_code else '0001')
        # 获取条码
        instance = EquipBom.objects.filter(equip_info__equip_no=validated_data['equip_no']).first()
        equip_barcode = instance.node_id if instance else ''
        validated_data.update({
            'plan_id': plan_id, 'status': '已生成', 'work_order_no': work_order_no, 'equip_barcode': equip_barcode,
            'planned_repair_date': datetime.now().date()
        })
        return super().create(validated_data)

    class Meta:
        model = EquipInspectionOrder
        fields = '__all__'
        read_only_fields = ['inspection_graph_url']


class UploadImageSerializer(BaseModelSerializer):

    def to_representation(self, instance):
        res = super().to_representation(instance)
        res['image_file_name'] = instance.image_file_name.url
        return res

    class Meta:
        model = UploadImage
        fields = '__all__'


class EquipWarehouseAreaSerializer(BaseModelSerializer):
    area_name = serializers.CharField(help_text='库区名称', validators=[
        UniqueValidator(EquipWarehouseArea.objects.filter(delete_flag=False), message='该库区已存在')
    ])
    equip_component_type = serializers.ListField(write_only=True, default=[])
    equip_component_type_name = serializers.SerializerMethodField()
    equip_component_type_id = serializers.SerializerMethodField()

    class Meta:
        model = EquipWarehouseArea
        fields = ('id', 'area_name', 'desc', 'equip_component_type', 'equip_component_type_name', 'area_barcode', 'equip_component_type_id')
        read_only_fields = COMMON_READ_ONLY_FIELDS

    def get_equip_component_type_name(self, instance):
        equip_component_type_name = '，'.join([i.get('equip_component_type__component_type_name')  for i in EquipWarehouseAreaComponent.objects.filter(equip_warehouse_area=instance).values(
                'equip_component_type__component_type_name')])
        return equip_component_type_name

    def get_equip_component_type_id(self, instance):
        equip_component_type_id = [i.get('equip_component_type__id')  for i in EquipWarehouseAreaComponent.objects.filter(equip_warehouse_area=instance).values(
                'equip_component_type__id')]
        return equip_component_type_id

    @atomic
    def create(self, validated_data):
        component_type_list = validated_data.pop('equip_component_type')
        barcode = EquipWarehouseArea.objects.aggregate(area_barcode=Max('area_barcode'))
        area_barcode = str('%03d' % (int(barcode['area_barcode'][2:]) + 1)) if barcode.get('area_barcode') else '001'
        validated_data.update(area_barcode='KQ' + area_barcode)
        instance = super().create(validated_data)
        for component_type in component_type_list:
            EquipWarehouseAreaComponent.objects.create(equip_warehouse_area=instance, equip_component_type_id=component_type)
        return instance

    @atomic
    def update(self, instance, validated_data):
        component_type_list = validated_data.pop('equip_component_type')
        EquipWarehouseAreaComponent.objects.filter(equip_warehouse_area=instance).delete()
        for component_type in component_type_list:
            EquipWarehouseAreaComponent.objects.create(equip_warehouse_area=instance, equip_component_type_id=component_type)
        return super().update(instance, validated_data)


class EquipWarehouseLocationSerializer(BaseModelSerializer):
    location_name = serializers.CharField(help_text='库位名称', validators=[
        UniqueValidator(EquipWarehouseLocation.objects.filter(delete_flag=False), message='该库位已存在')
    ])
    area_name = serializers.ReadOnlyField(source='equip_warehouse_area.area_name')

    class Meta:
        model = EquipWarehouseLocation
        fields = ('id', 'equip_warehouse_area', 'location_name', 'desc', 'area_name', 'location_barcode')
        read_only_fields = COMMON_READ_ONLY_FIELDS

    def create(self, validated_data):
        barcode = EquipWarehouseLocation.objects.filter(
            equip_warehouse_area=validated_data['equip_warehouse_area']).aggregate(
            location_barcode=Max('location_barcode'))
        location_barcode = str('%05d' % (int(barcode['location_barcode'][5:]) + 1)) if barcode.get(
            'location_barcode') else '00001'
        area_barcode = validated_data['equip_warehouse_area'].area_barcode[2:]
        validated_data.update(location_barcode='KW' + area_barcode + location_barcode)
        instance = super().create(validated_data)
        return instance


class EquipWarehouseOrderDetailSerializer(BaseModelSerializer):

    spare_code = serializers.ReadOnlyField(source='equip_spare.spare_code', help_text='备件编码')
    spare_name = serializers.ReadOnlyField(source='equip_spare.spare_name', help_text='备件名称')
    component_type_name = serializers.ReadOnlyField(source='equip_spare.equip_component_type.component_type_name',
                                                    help_text='备件分类名称')
    specification = serializers.ReadOnlyField(source='equip_spare.specification', help_text='规格型号')
    technical_params = serializers.ReadOnlyField(source='equip_spare.technical_params', help_text='用途')
    key_parts_flag = serializers.ReadOnlyField(source='equip_spare.key_parts_flag', help_text='是否关键部位')
    unit = serializers.ReadOnlyField(source='equip_spare.unit', help_text='单位')
    all_qty = serializers.SerializerMethodField()

    class Meta:
        model = EquipWarehouseOrderDetail
        fields = ("id", "created_username", "spare_code", "spare_name", "component_type_name", "specification",
            "technical_params", "unit", "created_date", "in_quantity", "out_quantity", "plan_in_quantity",
            "plan_out_quantity", "status", "status_name", "equip_warehouse_order", "equip_spare", "all_qty", "key_parts_flag")

    def get_all_qty(self, instance):
        res = EquipWarehouseInventory.objects.filter(equip_spare=instance.equip_spare, delete_flag=False).aggregate(all_qty=Sum('quantity'))
        return res.get('all_qty') if res.get('all_qty') else 0


class EquipWarehouseOrderSerializer(BaseModelSerializer):
    equip_spare = serializers.ListField(default=[], write_only=True)
    order_id = serializers.CharField(help_text='单据条码', validators=[
        UniqueValidator(EquipWarehouseOrder.objects.all(), message='该条码已存在')])
    order_detail = EquipWarehouseOrderDetailSerializer(many=True, read_only=True)

    class Meta:
        model = EquipWarehouseOrder
        fields = ("id", "created_username", "order_id", "order_detail", "submission_department",
        "status", "desc", "work_order_no", 'status_name', 'equip_spare', 'created_date', 'barcode')
        read_only_fields = COMMON_READ_ONLY_FIELDS

    @atomic
    def create(self, validated_data):
        equip_spare_list = validated_data.pop('equip_spare')
        desc = validated_data.get('desc') if validated_data.get('desc') else None
        validated_data.update({'desc': desc})
        order = super().create(validated_data)
        status = validated_data['status']
        for equip_sapre in equip_spare_list:
            if not isinstance(equip_sapre['quantity'], int):
                raise serializers.ValidationError('入库数量必须为整数')
            if status == 1:  # 入库单据
                kwargs = {
                    'equip_spare_id': equip_sapre['id'],
                    'plan_in_quantity': equip_sapre['quantity'],
                    'status': status,
                    'created_user': self.context["request"].user,
                    'equip_warehouse_order': order
                }
            else:  # status == 4:  出库单据
                kwargs = {
                    'equip_spare_id': equip_sapre['id'],
                    'plan_out_quantity': equip_sapre['quantity'],
                    'status': status,
                    'created_user': self.context["request"].user,
                    'equip_warehouse_order': order
                }
            EquipWarehouseOrderDetail.objects.create(**kwargs)
        return validated_data

    @atomic
    def update(self, instance, validated_data):
        equip_spare_list = validated_data.pop('equip_spare')
        desc = validated_data.get('desc') if validated_data.get('desc') else None
        validated_data.update({'desc': desc})
        # 备件列表
        queryset = EquipWarehouseOrderDetail.objects.filter(equip_warehouse_order=instance)
        dic = {}  # 提交过来的备件数组
        state_lst = []  # 判断单据的状态
        for equip_spare in equip_spare_list:
            dic.update({equip_spare['id']: equip_spare['quantity']})
            # 单据中新添加的备件
            if not queryset.filter(equip_spare_id=equip_spare['id']).exists():
                if instance.status in [1, 2, 3]:
                    state_lst.append(2)
                    EquipWarehouseOrderDetail.objects.create(equip_warehouse_order=instance,
                                                             equip_spare_id=equip_spare['id'],
                                                             plan_in_quantity=equip_spare['quantity'],
                                                             created_user=self.context["request"].user,
                                                             status=1)
                else:
                    state_lst.append(5)
                    EquipWarehouseOrderDetail.objects.create(equip_warehouse_order=instance,
                                                             equip_spare_id=equip_spare['id'],
                                                             plan_out_quantity=equip_spare['quantity'],
                                                             created_user=self.context["request"].user,
                                                             status=4)

        for obj in queryset:
            if obj.equip_spare_id not in dic.keys():
                obj.delete()
            else:
                if obj.status in [1, 2, 3]:  # 入库完成的也可以再次修改计划入库数量
                    obj.plan_in_quantity = dic[obj.equip_spare_id]
                    if dic[obj.equip_spare_id] == obj.in_quantity:
                        obj.status = 3  # 已入库
                        state_lst.append(3)
                    elif dic[obj.equip_spare_id] > obj.in_quantity and obj.in_quantity:  # 计划入库数量 > 已入库的数量
                        obj.status = 2  # 入库中
                        state_lst.append(2)
                    obj.save()
                elif obj.status in [4, 5, 6]:
                    obj.plan_out_quantity = dic[obj.equip_spare_id]
                    if dic[obj.equip_spare_id] == obj.out_quantity:
                        obj.status = 6  # 已出库
                        state_lst.append(6)
                    elif dic[obj.equip_spare_id] > obj.out_quantity and obj.out_quantity:  # 计划出库数量 > 已出库的数量
                        obj.status = 5  # 出库中
                        state_lst.append(5)
                    obj.save()
        if 2 in state_lst:
            validated_data['status'] = 2
        elif 3 in state_lst and 2 not in state_lst:
            validated_data['status'] = 3
        elif 5 in state_lst:
            validated_data['status'] = 5
        elif 6 in state_lst and 5 not in state_lst:
            validated_data['status'] = 6
        super().update(instance, validated_data)
        return validated_data


class EquipWarehouseInventorySerializer(BaseModelSerializer):
    order_id = serializers.ReadOnlyField(source='equip_warehouse_order_detail.equip_warehouse_order.order_id', help_text='出入库单号')

    work_order_no = serializers.ReadOnlyField(source='equip_warehouse_order_detail.equip_warehouse_order.work_order_no',
                                              help_text='工单编号')

    class Meta:
        model = EquipWarehouseInventory
        fields = '__all__'


class EquipWarehouseRecordSerializer(BaseModelSerializer):
    order_id = serializers.ReadOnlyField(source='equip_warehouse_order_detail.equip_warehouse_order.order_id', help_text='出入库单号')
    submission_department = serializers.ReadOnlyField(
        source='equip_warehouse_order_detail.equip_warehouse_order.submission_department', help_text='提交部门')
    spare_code = serializers.ReadOnlyField(source='equip_spare.spare_code', help_text='备件编码')
    spare_name = serializers.ReadOnlyField(source='equip_spare.spare_name', help_text='备件名称')
    component_type_name = serializers.ReadOnlyField(source='equip_spare.equip_component_type.component_type_name',
                                                    help_text='备件分类名称')
    specification = serializers.ReadOnlyField(source='equip_spare.specification', help_text='规格型号')
    technical_params = serializers.ReadOnlyField(source='equip_spare.technical_params', help_text='用途')
    cost = serializers.ReadOnlyField(source='equip_spare.cost', help_text='单价')
    unit = serializers.ReadOnlyField(source='equip_spare.unit', help_text='单位')
    money = serializers.SerializerMethodField()
    area_name = serializers.ReadOnlyField(source='equip_warehouse_area.area_name', help_text='库区')
    location_name = serializers.ReadOnlyField(source='equip_warehouse_location.location_name', help_text='库位')
    work_order_no = serializers.ReadOnlyField(source='equip_warehouse_order_detail.equip_warehouse_order.work_order_no',
                                              help_text='工单编号')

    class Meta:
        model = EquipWarehouseRecord
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS

    def get_money(self, instance):
        if instance.equip_spare.cost and instance.status in ['出库', '入库']:
            return round(instance.equip_spare.cost * int(instance.quantity), 2)
        return 0


class EquipPlanSerializer(BaseModelSerializer):
    plan_name = serializers.CharField(help_text='计划名称', validators=[UniqueValidator(
        queryset=EquipPlan.objects.all(), message='计划名称已存在')])
    plan_id = serializers.ReadOnlyField()
    equip_no = serializers.ListField(help_text='机台', write_only=True)
    standard_name = serializers.ReadOnlyField(help_text='维护标准名称', source='equip_manintenance_standard.standard_code')
    repair_standard_name = serializers.ReadOnlyField(help_text='维修标准名称', source='equip_repair_standard.standard_code')
    type = serializers.ReadOnlyField(help_text='巡检标准类别', source='equip_manintenance_standard.type', default='')
    equip_name = serializers.ReadOnlyField(source='equip_no')
    planned_maintenance_date = serializers.CharField()
    next_maintenance_date = serializers.CharField(default=None)
    standard = serializers.SerializerMethodField()
    timeout_color = serializers.SerializerMethodField()

    class Meta:
        model = EquipPlan
        fields = '__all__'

    def get_standard(self, instance):
        standard = None
        if instance.equip_repair_standard:
            standard = instance.equip_repair_standard.standard_name
        elif instance.equip_manintenance_standard:
            standard = instance.equip_manintenance_standard.standard_name
        return standard

    def get_timeout_color(self, instance):
        if instance.work_type == '巡检':
           if '红色' in EquipInspectionOrder.objects.filter(plan_id=instance.plan_id).values_list('timeout_color', flat=True):
                return '红色'
        else:
           if '红色' in EquipApplyOrder.objects.filter(plan_id=instance.plan_id).values_list('timeout_color', flat=True):
            return '红色'

    def create(self, validated_data):
        dic = EquipPlan.objects.filter(work_type=validated_data['work_type'], created_date__date=date.today()).aggregate(
            Max('plan_id'))
        res = dic.get('plan_id__max')
        work_type = {
            '巡检': 'XJ',
            '保养': 'BY',
            '润滑': 'RH',
            '标定': 'BD',
            '维修': 'BX'
        }
        if res:
            plan_id = res[:10] + str('%04d' % (int(res[-4:]) + 1))
        else:
            plan_id = f'{work_type.get(validated_data["work_type"])}{date.today().strftime("%Y%m%d")}0001'

        equip_no = '，'.join([equip for equip in validated_data['equip_no']])
        validated_data['plan_id'] = plan_id
        validated_data['equip_no'] = equip_no
        validated_data['plan_source'] = '人工创建'
        validated_data['status'] = '未生成工单'
        validated_data['planned_maintenance_date'] = datetime.strptime(validated_data["planned_maintenance_date"], '%Y-%m-%d')
        if validated_data.get('next_maintenance_date'):
            validated_data['next_maintenance_date'] = datetime.strptime(validated_data["next_maintenance_date"], '%Y-%m-%d')

        instance = super().create(validated_data)
        return instance
