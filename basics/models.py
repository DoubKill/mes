from django.db import models
from system.models import AbstractEntity
from django.utils.translation import ugettext_lazy as _


class GlobalCodeType(AbstractEntity):
    """公共代码类型表"""
    type_no = models.CharField(max_length=64, help_text=_('类型编号'), verbose_name=_('类型编号'), unique=True)
    type_name = models.CharField(max_length=64, help_text='类型名称', verbose_name='类型名称')
    description = models.CharField(max_length=256, blank=True, null=True, help_text='说明', verbose_name='说明')
    used_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用')

    def __str__(self):
        return self.type_name

    class Meta:
        db_table = 'global_code_type'
        verbose_name_plural = verbose_name = '公共代码类型'


class GlobalCode(AbstractEntity):
    """公共代码表"""
    global_type = models.ForeignKey('GlobalCodeType', models.DO_NOTHING, related_name="global_codes",
                                    help_text='全局类型ID', verbose_name='全局类型ID')
    global_no = models.CharField(max_length=64, help_text='公共代码编号', verbose_name='公共代码编号')
    global_name = models.CharField(max_length=64, help_text='公用代码名称', verbose_name='公用代码名称')
    description = models.CharField(max_length=256, blank=True, null=True,
                                   help_text='说明', verbose_name='说明')
    used_flag = models.IntegerField(help_text='是否启用', verbose_name='是否删除', default=0)

    def __str__(self):
        return self.global_name

    class Meta:
        db_table = 'global_code'
        verbose_name_plural = verbose_name = '公共代码'


class WorkSchedule(AbstractEntity):
    """倒班管理"""
    schedule_no = models.CharField(max_length=64, help_text='倒班编号', verbose_name='倒班编号', unique=True)
    schedule_name = models.CharField(max_length=64, help_text='倒班名称', verbose_name='倒班名称')
    description = models.CharField(max_length=256, blank=True, null=True,
                                   help_text='说明', verbose_name='说明')

    def __str__(self):
        return self.schedule_name

    class Meta:
        db_table = 'work_schedule'
        verbose_name_plural = verbose_name = '倒班管理'


class ClassesDetail(AbstractEntity):
    """倒班条目"""
    TYPE_CHOICE = (
        ('normal', '正常'),
        ('rest', '休假'),
    )
    work_schedule = models.ForeignKey('WorkSchedule', models.DO_NOTHING,
                                      help_text='工作日程id', verbose_name='工作日程id', related_name="classesdetail_set")
    classes = models.ForeignKey('GlobalCode', models.DO_NOTHING,
                                help_text='班次', verbose_name='班次', related_name="classes_detail")
    description = models.CharField(max_length=256, blank=True, null=True,
                                   help_text='说明', verbose_name='说明')
    start_time = models.TimeField(help_text='开始时间', verbose_name='开始时间')
    end_time = models.TimeField(help_text='结束时间', verbose_name='结束时间')

    def __str__(self):
        return self.classes.global_name

    class Meta:
        db_table = 'classes_detail'
        verbose_name_plural = verbose_name = '倒班条目'


class EquipCategoryAttribute(AbstractEntity):
    """设备种类属性"""
    equip_type = models.ForeignKey('GlobalCode', models.DO_NOTHING, related_name='equip_category_attribute_t',
                                   help_text='设备类型', verbose_name='设备类型')
    category_no = models.CharField(max_length=64, help_text='机型编号', verbose_name='机型编号')
    category_name = models.CharField(max_length=64, help_text='机型名称', verbose_name='机型名称')
    volume = models.IntegerField(help_text='容积', verbose_name='容积')
    description = models.CharField(max_length=256, blank=True, null=True,
                                   help_text='设备说明', verbose_name='设备说明')
    process = models.ForeignKey('GlobalCode', models.DO_NOTHING, related_name='equip_category_attribute_p',
                                help_text='工序', verbose_name='工序')

    def __str__(self):
        return self.category_name

    class Meta:
        db_table = 'equip_category_attribute'
        verbose_name_plural = verbose_name = '设备种类属性'


class Equip(AbstractEntity):
    """设备表"""
    category = models.ForeignKey('EquipCategoryAttribute', models.DO_NOTHING, related_name='equip_c',
                                 help_text='设备种类属性', verbose_name='设备种类属性')
    parent = models.ForeignKey('self', blank=True, null=True,
                               help_text='上层设备', verbose_name='上层设备', on_delete=models.DO_NOTHING,
                               related_name="equip_p")
    equip_no = models.CharField(max_length=64, help_text='设备编号', verbose_name='设备编号')
    equip_name = models.CharField(max_length=64, help_text='设备名称', verbose_name='设备名称')
    used_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用')
    description = models.CharField(max_length=256, blank=True, null=True,
                                   help_text='设备说明', verbose_name='设备说明')
    count_flag = models.BooleanField(help_text='是否产量计数', verbose_name='是否产量计数')

    equip_level = models.ForeignKey('GlobalCode', models.DO_NOTHING, related_name='equip_l',
                                    help_text='层级', verbose_name='层级')

    def __str__(self):
        return self.equip_name

    class Meta:
        db_table = 'equip'
        verbose_name_plural = verbose_name = '设备'


class SysbaseEquipLevel(AbstractEntity):
    """设备层次"""
    parent = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True,
                               help_text='上层设备层次', verbose_name='上层设备层次', related_name='sysbase_equip_level')
    equip_level_no = models.CharField(max_length=64, help_text='编号', verbose_name='编号')
    equip_level_name = models.CharField(max_length=64, help_text='名称', verbose_name='名称')
    description = models.CharField(max_length=256, blank=True, null=True,
                                   help_text='说明', verbose_name='说明')
    equip_level = models.ForeignKey(GlobalCode, models.DO_NOTHING,
                                    help_text='层级', verbose_name='层级', related_name='sysbase_equip_level')

    class Meta:
        db_table = 'sysbase_equip_level'
        verbose_name_plural = verbose_name = '设备层次'


class PlanSchedule(AbstractEntity):
    """排班管理"""
    day_time = models.DateField(help_text='日期', verbose_name='日期')
    work_schedule = models.ForeignKey(WorkSchedule, models.DO_NOTHING,
                                      help_text='工作日程id', verbose_name='工作日程id', related_name="plan_schedule")

    class Meta:
        db_table = 'plan_schedule'
        verbose_name_plural = verbose_name = '排班管理'


class WorkSchedulePlan(AbstractEntity):
    """排班详情"""
    classes_detail = models.ForeignKey(ClassesDetail, models.DO_NOTHING,
                                       help_text='班次id', verbose_name='班次id', related_name="work_schedule_plan")
    group = models.ForeignKey(GlobalCode, models.DO_NOTHING,
                              help_text='班组id', verbose_name='班组id', related_name="work_schedule_plan")
    group_name = models.CharField(max_length=64, help_text='班组名称', verbose_name='班组名称')
    rest_flag = models.BooleanField(help_text='是否休息', verbose_name='是否休息')
    plan_schedule = models.ForeignKey(PlanSchedule, models.DO_NOTHING,
                                      help_text='计划时间id', verbose_name='计划时间id', related_name="work_schedule_plan")

    class Meta:
        db_table = 'work_schedule_plan'
        verbose_name_plural = verbose_name = '排班详情'
