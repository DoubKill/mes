# Create your models here.
from django.db import models

from basics.models import Equip, Location, GlobalCode, EquipCategoryAttribute
from system.models import AbstractEntity, User


class EquipPart(AbstractEntity):
    no = models.CharField(max_length=64, help_text='部位编号', verbose_name='编号')
    name = models.CharField(max_length=64, help_text='部位名称', verbose_name='名称')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="equip_part_location",
                                 help_text='所处位置',
                                 verbose_name='所处位置', null=True)
    equip = models.ForeignKey(Equip, on_delete=models.CASCADE, related_name="equip_part_equip",
                              help_text='设备', verbose_name='设备')

    class Meta:
        db_table = 'equip_part'
        verbose_name_plural = verbose_name = '设备部位表'


class EquipCurrentStatus(AbstractEntity):
    """设备现况汇总"""
    STATUSES = (
        ('停机', '停机'),
        ('故障', '故障'),
        ('维修开始', '维修开始'),
        ('维修结束', '维修结束'),
        ('空转', '空转'),
        ('运行中', '运行中'),
    )
    equip = models.OneToOneField(Equip, on_delete=models.CASCADE, related_name="equip_current_status_equip")
    status = models.CharField(choices=STATUSES, max_length=64, verbose_name='状态', help_text='状态')
    user = models.CharField(max_length=64, verbose_name='操作员', help_text='操作员')

    class Meta:
        db_table = 'equip_current_status'
        verbose_name_plural = verbose_name = '设备现况汇总'


class EquipDownType(AbstractEntity):
    """设备停机类型"""
    no = models.CharField(max_length=64, verbose_name='类型代码', help_text='类型代码')
    name = models.CharField(max_length=64, verbose_name='类型名称', help_text='类型名称')

    class Meta:
        db_table = 'equip_down_type'
        verbose_name_plural = verbose_name = '设备停机类型'


class EquipDownReason(AbstractEntity):
    """设备停机原因"""
    no = models.CharField(max_length=64, verbose_name='原因代码', help_text='类型代码')
    equip_down_type = models.ForeignKey(EquipDownType, on_delete=models.CASCADE, related_name="equip_down_reason_type")
    desc = models.CharField(max_length=256, verbose_name='描述', help_text='描述', blank=True, null=True)

    class Meta:
        db_table = 'equip_down_reason'
        verbose_name_plural = verbose_name = '设备停机原因'


class EquipMaintenanceOrder(AbstractEntity):
    """维修表单"""
    STATUSES = (
        (1, '新建'),
        (2, '就绪'),
        (3, '开始维修'),
        (4, '维修结束'),
        (5, '确认完成'),
        (6, '关闭'),
        (7, '退回'),
    )
    ORDER_SRC_CHOICE = (
        (1, 'MES'),
        (2, '终端')
    )
    order_uid = models.CharField(max_length=64, verbose_name='唯一码', help_text='唯一码')
    # equip = models.ForeignKey(Equip, on_delete=models.CASCADE, related_name="equip_maintenance_order_equip",
    #                           help_text='设备', verbose_name='设备')
    equip_part = models.ForeignKey(EquipPart, on_delete=models.CASCADE, related_name="equip_maintenance_order_part",
                                   help_text='设备部位', verbose_name='部位')
    first_down_reason = models.CharField(max_length=64, verbose_name='初诊原因', help_text='初诊原因')
    first_down_type = models.CharField(max_length=64, verbose_name='初诊类型', help_text='初诊类型')
    down_flag = models.BooleanField(help_text='是否已经停机', verbose_name='是否已经停机', default=False)
    image = models.ImageField(upload_to='equipment/%Y/%m/', help_text='相关照片', verbose_name='相关照片',
                              blank=True, null=True)
    factory_date = models.DateField(help_text='设备故障工厂日期', verbose_name='设备故障工厂日期')
    down_time = models.DateTimeField(help_text='设备故障时间', verbose_name='设备故障时间')
    order_src = models.CharField(max_length=64, help_text='订单来源', verbose_name='订单来源',
                                 choices=ORDER_SRC_CHOICE, default=1)
    maintenance_user = models.ForeignKey(User, help_text='维修人', verbose_name='维修人',
                                         null=True, on_delete=models.CASCADE, related_name='m_order')
    assign_user = models.ForeignKey(User, help_text='指派人', verbose_name='指派人', null=True,
                                    on_delete=models.CASCADE, related_name='ass_order')
    begin_time = models.DateTimeField(help_text='开始维修时间', verbose_name='开始维修时间', null=True)
    end_time = models.DateTimeField(help_text='结束维修时间', verbose_name='结束维修时间', null=True)
    affirm_time = models.DateTimeField(help_text='确认启动时间', verbose_name='确认启动时间', null=True)
    affirm_user = models.ForeignKey(User, help_text='确认启动人', verbose_name='确认启动人', null=True,
                                    on_delete=models.CASCADE, related_name='aff_order')
    down_reason = models.CharField(max_length=256, help_text='维修原因', verbose_name='维修原因', null=True)
    down_type = models.CharField(max_length=64, help_text='维修类型', verbose_name='维修类型', null=True)
    take_time = models.DateTimeField(help_text='接单时间', verbose_name='接单时间', null=True)
    first_note = models.CharField(max_length=256, help_text='初诊备注', verbose_name='初诊备注', null=True)
    note = models.CharField(max_length=256, help_text='维修备注', verbose_name='维修备注', blank=True, null=True)
    status = models.PositiveIntegerField(choices=STATUSES, default=1, help_text='状态', verbose_name='状态')
    note_time = models.DateTimeField(help_text='写原因时间', verbose_name='写原因时间', null=True)
    return_flag = models.BooleanField(help_text='是否退单', verbose_name='是否退单', default=False)
    relevance_order_uid = models.CharField(max_length=64, help_text='关联单号', verbose_name='关联单号', null=True)
    class_name = models.CharField(max_length=64, help_text='班次', verbose_name='班次', default='早班')

    class Meta:
        db_table = 'equip_maintenance_order'
        verbose_name_plural = verbose_name = '维修表单'


class PropertyTypeNode(AbstractEntity):
    """资产类型节点"""
    name = models.CharField(max_length=64, help_text='名称', verbose_name='名称')
    parent = models.ForeignKey('self', help_text='父节点', related_name='children_property_type_node',
                               blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        db_table = 'property_type_node'
        verbose_name_plural = verbose_name = '资产类型节点'


class Property(AbstractEntity):
    STATUSES = (
        (1, '使用中'),
        (2, '废弃'),
        (3, '限制'),
    )
    no = models.CharField(max_length=64, help_text='编号', verbose_name='编号', null=True)
    name = models.CharField(max_length=64, help_text='名称', verbose_name='名称', null=True)
    property_no = models.CharField(max_length=64, help_text='固定资产编码', verbose_name='固定资产编码', unique=True)
    src_no = models.CharField(max_length=64, help_text='原编码', verbose_name='原编码')
    financial_no = models.CharField(max_length=64, help_text='财务编码', verbose_name='财务编码')
    equip_type = models.CharField(max_length=64, help_text='设备型号', verbose_name='设备型号')
    equip_no = models.CharField(max_length=64, help_text='设备编码', verbose_name='设备编码')
    equip_name = models.CharField(max_length=64, help_text='设备名称', verbose_name='设备名称')
    made_in = models.CharField(max_length=64, help_text='设备制造商', verbose_name='设备制造商')
    capacity = models.CharField(max_length=64, help_text='产能', verbose_name='产能')
    price = models.CharField(max_length=64, help_text='价格', verbose_name='价格')
    status = models.PositiveIntegerField(choices=STATUSES, default=1, help_text='状态', verbose_name='状态')
    property_type_node = models.ForeignKey(PropertyTypeNode, on_delete=models.CASCADE,
                                           related_name="property_type_node_name")
    leave_factory_no = models.CharField(max_length=64, help_text='出厂编码', verbose_name='出厂编码')
    leave_factory_date = models.DateField(help_text='出厂日期', verbose_name='出厂日期')
    use_date = models.DateField(help_text='使用日期', verbose_name='使用日期')

    class Meta:
        db_table = 'property'
        verbose_name_plural = verbose_name = '资产'


class PlatformConfig(AbstractEntity):
    """通知配置"""
    platform = models.CharField(max_length=64, help_text='平台', verbose_name='平台')
    url = models.CharField(max_length=256, help_text='url', verbose_name='url')
    tag = models.CharField(max_length=256, help_text='标签', verbose_name='标签', null=True)
    private_key = models.CharField(max_length=256, help_text='秘钥', verbose_name='秘钥')
    token = models.CharField(max_length=64, help_text='token', verbose_name='token', null=True)

    class Meta:
        db_table = 'platform_config'
        verbose_name_plural = verbose_name = '通知配置'


class InformContent(AbstractEntity):
    """通知内容"""
    platform = models.ForeignKey(PlatformConfig, on_delete=models.CASCADE,
                                 related_name="platform_config_platform")
    content = models.TextField(help_text='内容', verbose_name='内容')
    config_value = models.TextField(help_text='接受者', verbose_name='接受者',null=True)
    sent_flag = models.BooleanField(help_text='是否发送完成', verbose_name='是否发送完成', default=False)

    class Meta:
        db_table = 'inform_content'
        verbose_name_plural = verbose_name = '通知内容'


# **************************2021-10-09**************************
# **************************最新模型类**************************


class EquipSupplier(AbstractEntity):
    """
        设备供应商
    """
    supplier_code = models.CharField(max_length=64, help_text='供应商编码')
    supplier_name = models.CharField(max_length=64, help_text='供应商名称')
    region = models.CharField(max_length=64, help_text='地域', blank=True, null=True)
    contact_name = models.CharField(max_length=64, help_text='联系人', blank=True, null=True)
    contact_phone = models.CharField(max_length=64, help_text='联系人电话', blank=True, null=True)
    supplier_type = models.CharField(max_length=64, help_text='供应商类别', blank=True, null=True)
    use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)

    class Meta:
        db_table = 'equip_supplier'
        verbose_name_plural = verbose_name = '设备供应商'


class EquipProperty(AbstractEntity):
    """
        设备固定资产
    """
    STATUSES = (
        (1, '使用中'),
        (2, '废弃'),
        (3, '限制'),
    )
    no = models.CharField(max_length=64, help_text='编号', verbose_name='编号', null=True)
    name = models.CharField(max_length=64, help_text='名称', verbose_name='名称', null=True)
    property_no = models.CharField(max_length=64, help_text='固定资产编码', verbose_name='固定资产编码', unique=True, null=True, blank=True)
    src_no = models.CharField(max_length=64, help_text='原编码', verbose_name='原编码', blank=True, null=True)
    financial_no = models.CharField(max_length=64, help_text='财务编码', verbose_name='财务编码', blank=True, null=True)
    equip_type = models.ForeignKey(EquipCategoryAttribute, on_delete=models.CASCADE, help_text='所属主设备种类')
    equip_no = models.CharField(max_length=64, help_text='设备编码', verbose_name='设备编码', blank=True, null=True)
    equip_name = models.CharField(max_length=64, help_text='设备名称', verbose_name='设备名称', blank=True, null=True)
    made_in = models.CharField(max_length=64, help_text='设备制造商', verbose_name='设备制造商', blank=True, null=True)
    capacity = models.CharField(max_length=64, help_text='产能', verbose_name='产能', blank=True, null=True)
    price = models.FloatField(help_text='价格', verbose_name='价格', blank=True, null=True)
    status = models.PositiveIntegerField(choices=STATUSES, default=1, help_text='状态', verbose_name='状态')
    leave_factory_no = models.CharField(max_length=64, help_text='出厂编码', verbose_name='出厂编码', blank=True, null=True)
    leave_factory_date = models.DateField(help_text='出厂日期', verbose_name='出厂日期', blank=True, null=True)
    use_date = models.DateField(help_text='使用日期', verbose_name='使用日期', blank=True, null=True)
    equip_supplier = models.ForeignKey(EquipSupplier, help_text='设备供应商', on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        db_table = 'equip_property'
        verbose_name_plural = verbose_name = '设备固定资产'


class EquipAreaDefine(AbstractEntity):
    """
        设备区域定义
    """
    area_code = models.CharField(max_length=64, help_text='区域编号')
    area_name = models.CharField(max_length=64, help_text='区域名称')
    inspection_line_no = models.IntegerField(help_text='巡检顺序编号', blank=True, null=True)
    desc = models.CharField(max_length=256, help_text='备注说明', blank=True, null=True)
    use_flag = models.BooleanField(help_text='是否启用', default=True)

    class Meta:
        db_table = 'equip_area_define'
        verbose_name_plural = verbose_name = '设备区域定义'


class EquipPartNew(AbstractEntity):
    """
        设备部位
    """
    equip_type = models.ForeignKey(EquipCategoryAttribute, on_delete=models.CASCADE,
                                   help_text='所属主设备种类')
    part_code = models.CharField(max_length=64, help_text='部位编号')
    part_name = models.CharField(max_length=64, help_text='部位名称')
    global_part_type = models.ForeignKey(GlobalCode, help_text='部位分类', on_delete=models.CASCADE)
    use_flag = models.BooleanField(help_text='是否启用', default=True)

    class Meta:
        db_table = 'equip_part_new'
        verbose_name_plural = verbose_name = '设备部位'


class EquipComponentType(AbstractEntity):
    """
        设备部件分类
    """
    component_type_code = models.CharField(max_length=64, help_text='部件分类编号')
    component_type_name = models.CharField(max_length=64, help_text='部件分类名称')
    use_flag = models.BooleanField(help_text='是否启用', default=True)

    class Meta:
        db_table = 'equip_component_type'
        verbose_name_plural = verbose_name = '设备部件分类'


class EquipComponent(AbstractEntity):
    """
        设备部件
    """
    # equip_type = models.ForeignKey(EquipCategoryAttribute, on_delete=models.CASCADE,
    #                                help_text='所属主设备种类')
    equip_part = models.ForeignKey(EquipPartNew, on_delete=models.CASCADE,
                                   help_text='所属主设备部位')
    equip_component_type = models.ForeignKey(EquipComponentType, on_delete=models.CASCADE,
                                             help_text='部件分类')
    component_code = models.CharField(max_length=64, help_text='部件编号')
    component_name = models.CharField(max_length=64, help_text='部件名称')
    use_flag = models.BooleanField(help_text='是否启用', default=True)

    @property
    def is_binding(self):
        return self.equip_components.count() > 0

    class Meta:
        db_table = 'equip_component'
        verbose_name_plural = verbose_name = '设备部件'


class EquipSpareErp(AbstractEntity):
    """
        erp备件物料
    """
    spare_code = models.CharField(max_length=64, help_text='erp备件编码')
    spare_name = models.CharField(max_length=64, help_text='erp备件名称')
    equip_component_type = models.ForeignKey(EquipComponentType, on_delete=models.CASCADE,
                                             help_text='部件分类')
    supplier_name = models.CharField(max_length=64, help_text='供应商名称', blank=True, null=True)
    specification = models.CharField(max_length=64, help_text='技术型号', blank=True, null=True)
    technical_params = models.CharField(max_length=64, help_text='技术参数', blank=True, null=True)
    unit = models.CharField(max_length=64, help_text='单位', blank=True, null=True)
    key_parts_flag = models.BooleanField(help_text='是否关键部位', blank=True, null=True)
    upper_stock = models.FloatField(help_text='库存上限', blank=True, null=True)
    lower_stock = models.FloatField(help_text='库存下限', blank=True, null=True)
    cost = models.FloatField(help_text='计划价格', blank=True, null=True)
    texture_material = models.CharField(max_length=64, help_text='材质', blank=True, null=True)
    period_validity = models.IntegerField(help_text='有效期', blank=True, null=True)
    use_flag = models.BooleanField(help_text='是否启用', default=True)
    info_source = models.CharField(max_length=64, help_text='来源', blank=True, null=True, default='MES')
    equip_component = models.ManyToManyField(EquipComponent, help_text='设备部件', related_name='equip_components',
                                             through='ERPSpareComponentRelation')

    class Meta:
        db_table = 'equip_spare_erp'
        verbose_name_plural = verbose_name = 'erp备件物料'


class ERPSpareComponentRelation(models.Model):
    equip_component = models.ForeignKey(EquipComponent, help_text='设备部件', on_delete=models.CASCADE)
    equip_spare_erp = models.ForeignKey(EquipSpareErp, help_text='erp备件物料', on_delete=models.CASCADE)
    reuse_flag = models.BooleanField(help_text='是否以旧换新', default=True)

    class Meta:
        db_table = 'erp_spare_component_relation'
        verbose_name_plural = verbose_name = 'erp备件部件对应'


# class EquipSpare(AbstractEntity):
#     """
#         备件代码定义
#     """
#     spare_code = models.CharField(max_length=64, help_text='备件编码')
#     spare_name = models.CharField(max_length=64, help_text='备件名称')
#     equip_component_type = models.ForeignKey(EquipComponentType, on_delete=models.CASCADE,
#                                              help_text='部件分类')
#     specification = models.CharField(max_length=64, help_text='技术型号', blank=True, null=True)
#     technical_params = models.CharField(max_length=64, help_text='技术参数', blank=True, null=True)
#     unit = models.CharField(max_length=64, help_text='单位', blank=True, null=True)
#     key_parts_flag = models.BooleanField(help_text='是否关键部位', blank=True, null=True)
#     upper_stock = models.FloatField(help_text='库存上限', blank=True, null=True)
#     lower_stock = models.FloatField(help_text='库存下限', blank=True, null=True)
#     cost = models.FloatField(help_text='计划价格', blank=True, null=True)
#     texture_material = models.CharField(max_length=64, help_text='材质', blank=True, null=True)
#     period_validity = models.IntegerField(help_text='有效期', blank=True, null=True)
#     use_flag = models.BooleanField(help_text='是否启用', default=True)
#
#     class Meta:
#         db_table = 'erp_spare'
#         verbose_name_plural = verbose_name = '备件代码定义'


class EquipFaultType(AbstractEntity):
    """
        设备故障类型
    """
    fault_type_code = models.CharField(max_length=64, help_text='故障分类编码')
    fault_type_name = models.CharField(max_length=64, help_text='故障分类名称')
    use_flag = models.BooleanField(help_text='是否启用', default=True)

    class Meta:
        db_table = 'equip_fault_type'
        verbose_name_plural = verbose_name = '设备故障类型'


class EquipFault(AbstractEntity):
    """
        设备故障分类
    """
    equip_fault_type = models.ForeignKey(EquipFaultType, help_text='备件故障分类', on_delete=models.CASCADE)
    fault_code = models.CharField(max_length=64, help_text='故障分类编码')
    fault_name = models.CharField(max_length=64, help_text='故障分类名称')
    use_flag = models.BooleanField(help_text='是否启用', default=True)
    desc = models.CharField(max_length=256, help_text='备注说明', blank=True, null=True)

    class Meta:
        db_table = 'equip_fault'
        verbose_name_plural = verbose_name = '设备故障分类'


class EquipFaultSignal(AbstractEntity):
    """
        设备故障信号
    """
    signal_code = models.CharField(max_length=64, help_text='故障信号编码')
    signal_name = models.CharField(max_length=64, help_text='故障信号名称')
    equip = models.ForeignKey(Equip, help_text='机台', on_delete=models.CASCADE)
    equip_part = models.ForeignKey(EquipPartNew, help_text='设备部位', verbose_name='设备部位',
                                   on_delete=models.SET_NULL, blank=True, null=True)
    equip_component = models.ForeignKey(EquipComponent, help_text='设备部件', on_delete=models.SET_NULL, blank=True, null=True)
    signal_variable_name = models.CharField(max_length=64, help_text='故障变量名称', blank=True, null=True)
    signal_variable_type = models.CharField(max_length=64, help_text='故障变量类型', blank=True, null=True)
    alarm_signal_minvalue = models.FloatField(help_text='报警下限值', blank=True, null=True)
    alarm_signal_maxvalue = models.FloatField(help_text='报警上限值', blank=True, null=True)
    alarm_signal_duration = models.FloatField(help_text='报警持续时间', blank=True, null=True)
    alarm_signal_down_flag = models.BooleanField(help_text='报警是否停机')
    alarm_signal_desc = models.CharField(max_length=256, help_text='报警停机描述', blank=True, null=True)
    fault_signal_minvalue = models.FloatField(help_text='故障下限值', blank=True, null=True)
    fault_signal_maxvalue = models.FloatField(help_text='故障上限值', blank=True, null=True)
    fault_signal_duration = models.FloatField(help_text='故障持续时间', blank=True, null=True)
    fault_signal_down_flag = models.BooleanField(help_text='故障是否停机')
    fault_signal_desc = models.CharField(max_length=256, help_text='故障停机描述', blank=True, null=True)
    use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)

    class Meta:
        db_table = 'equip_fault_signal'
        verbose_name_plural = verbose_name = '设备故障信号'


class EquipMachineHaltType(AbstractEntity):
    """
        设备停机类型
    """
    machine_halt_type_code = models.CharField(max_length=64, help_text='停机分类编码')
    machine_halt_type_name = models.CharField(max_length=64, help_text='停机分类名称')
    use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)

    class Meta:
        db_table = 'equip_machine_halt_type'
        verbose_name_plural = verbose_name = '设备停机类型'


class EquipMachineHaltReason(AbstractEntity):
    """
        设备停机原因
    """
    equip_machine_halt_type = models.ForeignKey(EquipMachineHaltType, help_text='设备停机类型', on_delete=models.CASCADE)
    machine_halt_reason_code = models.CharField(max_length=64, help_text='停机原因编码')
    machine_halt_reason_name = models.CharField(max_length=64, help_text='停机原因名称')
    use_flag = models.BooleanField(help_text='是否启用', default=True)
    desc = models.CharField(max_length=256, help_text='备注说明', blank=True, null=True)
    equip_fault = models.ManyToManyField(EquipFault, help_text='故障分类', related_name='halt_reasons')

    class Meta:
        db_table = 'equip_machine_halt_reason'
        verbose_name_plural = verbose_name = '设备停机原因'


class EquipOrderAssignRule(AbstractEntity):
    """
        工单指派规则
    """
    rule_code = models.CharField(max_length=64, help_text='标准编号')
    rule_name = models.CharField(max_length=64, help_text='标准名称')
    work_type = models.CharField(max_length=64, help_text='作业类型', blank=True, null=True)
    equip_type = models.ForeignKey(GlobalCode, models.CASCADE, help_text='设备类型', blank=True, null=True)
    equip_condition = models.CharField(max_length=64, help_text='设备条件', blank=True, null=True)
    important_level = models.CharField(max_length=64, help_text='重要程度', blank=True, null=True)
    receive_interval = models.IntegerField(help_text='接单间隔时间（分钟）', blank=True, null=True)
    receive_warning_times = models.IntegerField(help_text='接单重复提醒次数', blank=True, null=True)
    start_interval = models.IntegerField(help_text='维修开始间隔时间（分钟）', blank=True, null=True)
    start_warning_times = models.IntegerField(help_text='开始重复提醒次数', blank=True, null=True)
    accept_interval = models.IntegerField(help_text='验收间隔时间（分钟）', blank=True, null=True)
    accept_warning_times = models.IntegerField(help_text='验收重复提醒次数', blank=True, null=True)
    use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)

    class Meta:
        db_table = 'equip_order_assign_rule'
        verbose_name_plural = verbose_name = '工单指派规则'


class EquipTargetMTBFMTTRSetting(AbstractEntity):
    """
        机台目标MTBF/MTTR设定
    """
    equip = models.ForeignKey(Equip, on_delete=models.CASCADE, related_name="equip_target_settings", help_text='设备')
    target_mtb = models.FloatField()
    target_mttr = models.FloatField()

    class Meta:
        db_table = 'equip_target_mttbmttr_setting'
        verbose_name_plural = verbose_name = '机台目标MTBF/MTTR设定'


class EquipMaintenanceAreaSetting(AbstractEntity):
    maintenance_user = models.ForeignKey(User, help_text='包干人员', on_delete=models.CASCADE)
    equip = models.ForeignKey(Equip, on_delete=models.CASCADE, help_text='机台')
    equip_part = models.ForeignKey(EquipPartNew, on_delete=models.SET_NULL,
                                   help_text='设备部位', blank=True, null=True)
    equip_area = models.ForeignKey(EquipAreaDefine, on_delete=models.SET_NULL,
                                   help_text='设备区域', blank=True, null=True)

    class Meta:
        db_table = 'equip_maintenance_area_setting'
        verbose_name_plural = verbose_name = '维护包干设置'


class EquipJobItemStandard(AbstractEntity):
    WORK_TYPE_CHOICE = (
        ('巡检', '巡检'),
        ('保养', '保养'),
        ('标定', '标定'),
        ('润滑', '润滑'),
        ('维修', '维修')
    )
    work_type = models.CharField(max_length=64, help_text='作业类型', choices=WORK_TYPE_CHOICE)
    standard_code = models.CharField(max_length=64, help_text='标准编号')
    standard_name = models.CharField(max_length=64, help_text='标准名称')
    use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)

    class Meta:
        db_table = 'equip_job_item_standard'
        verbose_name_plural = verbose_name = '设备作业项目标准'


class EquipJobItemStandardDetail(AbstractEntity):
    TYPE_CHOICE = (
        ('有无', '有无'),
        ('数值范围', '数值范围'),
        ('正常异常', '正常异常'),
        ('完成未完成', '完成未完成'),
        ('合格不合格', '合格不合格'),
    )
    equip_standard = models.ForeignKey(EquipJobItemStandard, help_text='设备作业项目标准', on_delete=models.CASCADE)
    sequence = models.IntegerField(help_text='次序')
    content = models.CharField(max_length=64, help_text='内容')
    check_standard_desc = models.CharField(max_length=64, help_text='判断标准/步骤说明')
    check_standard_type = models.CharField(max_length=64, help_text='类型', choices=TYPE_CHOICE)

    class Meta:
        db_table = 'equip_job_item_standard_details'
        verbose_name_plural = verbose_name = '设备作业项目标准明细'


class EquipMaintenanceStandard(AbstractEntity):
    standard_code = models.CharField(max_length=64, help_text='标准编号')
    standard_name = models.CharField(max_length=64, help_text='标准名称')
    work_type = models.CharField(max_length=64, help_text='作业类型')
    equip_type = models.ForeignKey(EquipCategoryAttribute, on_delete=models.CASCADE, help_text='所属主设备种类')
    equip_part = models.ForeignKey(EquipPartNew, on_delete=models.CASCADE,
                                   help_text='设备部位', verbose_name='设备部位')
    equip_component = models.ForeignKey(EquipComponent, help_text='设备部件', on_delete=models.CASCADE,
                                        blank=True, null=True)
    equip_condition = models.CharField(max_length=64, help_text='设备条件')
    important_level = models.CharField(max_length=64, help_text='重要程度')
    equip_job_item_standard = models.ForeignKey(EquipJobItemStandard, help_text='设备作业项目标准', on_delete=models.CASCADE)
    start_time = models.DateField(help_text='起始日期', blank=True, null=True)
    maintenance_cycle = models.IntegerField(help_text='起始周期', blank=True, null=True)
    cycle_unit = models.CharField(max_length=64, help_text='起始周期单位', blank=True, null=True)
    cycle_num = models.IntegerField(help_text='周期数', blank=True, null=True)
    cycle_person_num = models.IntegerField(help_text='所需人数', blank=True, null=True)
    operation_time = models.IntegerField(help_text='作业时间', blank=True, null=True)
    operation_time_unit = models.CharField(max_length=64, help_text='作业时间单位', blank=True, null=True)
    remind_flag1 = models.BooleanField(help_text='是否钉钉提醒发送包干人员')
    remind_flag2 = models.BooleanField(help_text='是否钉钉提醒发送上级人员')
    remind_flag3 = models.BooleanField(help_text='是否钉钉提醒发送上上级人员')
    use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)

    class Meta:
        db_table = 'equip_maintenance_standard'
        verbose_name_plural = verbose_name = '设备维护作业标准定义'


class EquipMaintenanceStandardMaterials(AbstractEntity):
    equip_maintenance_standard = models.ForeignKey(EquipMaintenanceStandard, help_text='设备维护作业标准定义',
                                                   related_name='maintenance_materials', on_delete=models.CASCADE)
    equip_spare_erp = models.ForeignKey(EquipSpareErp, help_text='erp备件物料', on_delete=models.CASCADE)
    quantity = models.IntegerField(help_text='数量')

    class Meta:
        db_table = 'equip_maintenance_standard_materials'
        verbose_name_plural = verbose_name = '设备维护所需物料'


class EquipRepairStandard(AbstractEntity):
    standard_code = models.CharField(max_length=64, help_text='标准编号')
    standard_name = models.CharField(max_length=64, help_text='标准名称')
    # work_type = models.CharField(max_length=64, help_text='作业类型')
    equip_type = models.ForeignKey(EquipCategoryAttribute, on_delete=models.CASCADE, help_text='所属主设备种类')
    equip_part = models.ForeignKey(EquipPartNew, on_delete=models.CASCADE,
                                   help_text='设备部位', verbose_name='设备部位')
    equip_component = models.ForeignKey(EquipComponent, help_text='设备部件', on_delete=models.CASCADE
                                        , blank=True, null=True)
    equip_condition = models.CharField(max_length=64, help_text='设备条件')
    important_level = models.CharField(max_length=64, help_text='重要程度')
    equip_fault = models.ForeignKey(EquipFault, help_text='故障分类', on_delete=models.CASCADE)
    equip_job_item_standard = models.ForeignKey(EquipJobItemStandard, help_text='设备作业项目标准', on_delete=models.CASCADE)
    cycle_person_num = models.IntegerField(help_text='所需人数', blank=True, null=True)
    operation_time = models.IntegerField(help_text='作业时间', blank=True, null=True)
    operation_time_unit = models.CharField(max_length=64, help_text='作业时间单位', blank=True, null=True)
    remind_flag1 = models.BooleanField(help_text='是否钉钉提醒发送包干人员')
    remind_flag2 = models.BooleanField(help_text='是否钉钉提醒发送上级人员')
    remind_flag3 = models.BooleanField(help_text='是否钉钉提醒发送上上级人员')
    use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)

    class Meta:
        db_table = 'equip_repair_standard'
        verbose_name_plural = verbose_name = '设备维修作业标准定义'


class EquipRepairStandardMaterials(AbstractEntity):
    equip_repair_standard = models.ForeignKey(EquipRepairStandard, help_text='设备维修作业标准定义',
                                                   related_name='repair_materials', on_delete=models.CASCADE)
    equip_spare_erp = models.ForeignKey(EquipSpareErp, help_text='erp备件物料', on_delete=models.CASCADE)
    quantity = models.IntegerField(help_text='数量')

    class Meta:
        db_table = 'equip_repair_standard_materials'
        verbose_name_plural = verbose_name = '设备维护所需物料'


class EquipBom(AbstractEntity):
    """
        设备BOM管理
    """
    node_id = models.CharField(max_length=64, help_text='节点编号', null=True, blank=True)
    factory_id = models.CharField(max_length=64, help_text='分厂名称', null=True, blank=True)
    equip_info = models.ForeignKey(Equip, on_delete=models.CASCADE, help_text='设备信息', null=True, blank=True)
    property_type = models.ForeignKey(GlobalCode, on_delete=models.CASCADE, help_text='设备类型ID', null=True, blank=True)
    part = models.ForeignKey(EquipPartNew, on_delete=models.CASCADE, help_text='部位编号', null=True, blank=True)
    component = models.ForeignKey(EquipComponent, help_text='部件编号', on_delete=models.CASCADE, null=True, blank=True)
    part_type = models.CharField(max_length=256, help_text='部件规格', null=True, blank=True)
    part_status = models.CharField(max_length=64, help_text='部件状态', null=True, blank=True)
    equip_area_define = models.ForeignKey(EquipAreaDefine, help_text='区域编号', on_delete=models.CASCADE, null=True, blank=True)
    maintenance_xunjian_flag = models.BooleanField(help_text='是否巡检', blank=True, null=True)
    maintenance_xunjian = models.ForeignKey(EquipMaintenanceStandard, help_text='巡检标准', on_delete=models.CASCADE, null=True, blank=True)
    equip_repair_standard_flag = models.BooleanField(max_length=64, help_text='是否维修', null=True, blank=True)
    equip_repair_standard = models.ForeignKey(EquipRepairStandard, help_text='维修标准', on_delete=models.CASCADE, related_name='repair', null=True, blank=True)
    maintenance_baoyang_flag = models.BooleanField(max_length=64, help_text='是否保养', null=True, blank=True)
    maintenance_baoyang = models.ForeignKey(EquipMaintenanceStandard, help_text='保养标准', on_delete=models.CASCADE, related_name='baoyang', null=True, blank=True)
    maintenance_runhua_flag = models.BooleanField(max_length=64, help_text='是否润滑', null=True, blank=True)
    maintenance_runhua = models.ForeignKey(EquipMaintenanceStandard, help_text='润滑标准', on_delete=models.CASCADE, related_name='runhua', null=True, blank=True)
    maintenance_biaoding_flag = models.BooleanField(max_length=64, help_text='是否标定', null=True, blank=True)
    maintenance_biaoding = models.ForeignKey(EquipMaintenanceStandard, help_text='标定标准', on_delete=models.CASCADE, related_name='biaoding', null=True, blank=True)
    parent_flag = models.ForeignKey('self', help_text='父节点id', on_delete=models.CASCADE, null=True, blank=True)
    level = models.IntegerField(help_text='树的层级', null=True, blank=True)

    class Meta:
        db_table = 'equip_bom'
        verbose_name_plural = verbose_name = '设备BOM'


# class EquipWarehouseArea(AbstractEntity):
#     """
#         备件库库区
#     """
#     area_name = models.CharField(max_length=64, help_text='库区名称')
#     description = models.CharField(max_length=64, help_text='描述', default='')
#     equip_component_type = models.ForeignKey(EquipComponentType, help_text='备件分类', on_delete=models.CASCADE, null=True, blank=True)
#     use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)
#
#     class Meta:
#         db_table = 'equip_warehouse_area'
#         verbose_name = verbose_name_plural = '备件库库区'
#
#
# class EquipWarehouseLocation(AbstractEntity):
#     """
#         备件库库位
#     """
#     equip_warehouse_area = models.ForeignKey(EquipWarehouseArea, help_text='库区名称', on_delete=models.CASCADE)
#     location_name = models.CharField(max_length=64, help_text='库位名称')
#     description = models.CharField(max_length=64, help_text='描述', default='')
#     use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)
#
#     class Meta:
#         db_table = 'equip_warehouse_location'
#         verbose_name = verbose_name_plural = '备件库库位'
#
#
# class EquipWarehouseOrder(AbstractEntity):
#     """
#     备件库出入库单据
#     """
#     order_type = models.CharField(max_length=64, help_text='单据类别')
#     order_id = models.CharField(max_length=64, help_text='单据条码')
#     submission_department = models.CharField(max_length=64, help_text='提交部门')
#     order_status = models.CharField(max_length=64, help_text='单据状态')
#
#     class Meta:
#         db_table = 'equip_warehouse_order'
#         verbose_name = verbose_name_plural = '备件库出入库单据'
#
#
# class EquipWarehouseOrderDetail(AbstractEntity):
#     """
#     备件库出入库单据明细
#     """
#     order_type = models.CharField(max_length=64, help_text='单据类别')
#     equip_warehouse_inorder_id = models.CharField(max_length=64, help_text='单据条码')
#     spare_barcode = models.CharField(max_length=64, help_text='备件条码')
#     equip_spare = models.ForeignKey(EquipSpareErp, on_delete=models.CASCADE, help_text='备件代码')
#     order_quantity = models.IntegerField(help_text='单据数量')
#     completed_quantity = models.IntegerField(help_text='已完成单据数量')
#     equip_warehouse_area = models.ForeignKey(EquipWarehouseArea, help_text='库区名称', on_delete=models.CASCADE)
#     equip_warehouse_location = models.ForeignKey(EquipWarehouseLocation, help_text='库位名称', on_delete=models.CASCADE)
#     factory_code = models.CharField(max_length=64, help_text='出厂编码')
#     factory_datetime = models.DateField(help_text='出厂日期')
#     equip_supplier = models.ForeignKey(EquipSupplier, on_delete=models.CASCADE, help_text='供应商')
#     manufacturer = models.ForeignKey(EquipSupplier, on_delete=models.CASCADE, help_text='制造商')
#     status = models.CharField(max_length=64, help_text='状态')
#
#     class Meta:
#         db_table = 'equip_warehouse_order_detail'
#         verbose_name = verbose_name_plural = '备件库出入库单据明细'

