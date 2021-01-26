from django.db import models

# Create your models here.
from django.db import models

from basics.models import Equip
from system.models import AbstractEntity


class EquipCurrentStatus(AbstractEntity):
    """设备现况汇总"""
    EQUIP_STATUS = (
        (1, "运行中"),
        (2, "故障停机"),
        (3, "维修中"),
    )
    equip = models.ForeignKey(Equip, on_delete=models.CASCADE, related_name="equip_current_status_equip")
    status = models.PositiveIntegerField(verbose_name='设备状态', help_text="设备状态" ,choices=EQUIP_STATUS, default=1)
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
    desc = models.CharField(max_length=256, verbose_name='描述', help_text='描述')

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
    order_uid = models.CharField(max_length=64, verbose_name='唯一码', help_text='唯一码')
    equip_id = models.PositiveIntegerField(help_text='设备', verbose_name='设备')
    part_id = models.PositiveIntegerField(help_text='部位', verbose_name='部位')
    first_down_reason = models.CharField(max_length=64, verbose_name='初诊原因', help_text='初诊原因')
    first_down_type = models.CharField(max_length=64, verbose_name='初诊类型', help_text='初诊类型')
    down_flag = models.BooleanField(help_text='是否已经停机', verbose_name='是否已经停机')
    first_imgurl = models.CharField(max_length=64, help_text='相关照片', verbose_name='相关照片', null=True)
    factory_date = models.DateField(help_text='工厂时间', verbose_name='工厂时间')
    order_src = models.CharField(max_length=64, help_text='订单来源', verbose_name='订单来源')
    maintenance_user = models.CharField(max_length=64, help_text='维修人', verbose_name='维修人', null=True)
    assign_user = models.CharField(max_length=64, help_text='指派人', verbose_name='指派人', null=True)
    begin_time = models.DateTimeField(help_text='开始维修时间', verbose_name='开始维修时间', null=True)
    end_time = models.DateTimeField(help_text='结束维修时间', verbose_name='结束维修时间', null=True)
    affirm_time = models.DateTimeField(help_text='确认启动时间', verbose_name='确认启动时间', null=True)
    affirm_user = models.CharField(max_length=64, help_text='确认启动人', verbose_name='确认启动人', null=True)
    down_reason = models.CharField(max_length=256, help_text='维修原因', verbose_name='维修原因', null=True)
    down_type = models.CharField(max_length=64, help_text='维修类型', verbose_name='维修类型', null=True)
    take_time = models.DateTimeField(help_text='接单时间', verbose_name='接单时间', null=True)
    first_note = models.CharField(max_length=256, help_text='初诊备注', verbose_name='初诊备注', null=True)
    note = models.CharField(max_length=256, help_text='维修备注', verbose_name='维修备注', null=True)
    status = models.PositiveIntegerField(choices=STATUSES, default=1, help_text='状态', verbose_name='状态')
    note_time = models.DateTimeField(help_text='写原因时间', verbose_name='写原因时间', null=True)
    return_flag = models.BooleanField(help_text='是否退单', verbose_name='是否退单')
    relevance_order_uid = models.CharField(max_length=64, help_text='关联单号', verbose_name='关联单号', null=True)

    class Meta:
        db_table = 'equip_maintenance_order'
        verbose_name_plural = verbose_name = '维修表单'
