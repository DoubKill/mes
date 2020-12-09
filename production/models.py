from django.db import models

from basics.models import AbstractEntity


class TrainsFeedbacks(AbstractEntity):
    """车次产出反馈"""
    # id = models.BigIntegerField(primary_key=True, auto_created=True, unique=True)
    plan_classes_uid = models.CharField(help_text='班次计划唯一码', verbose_name='班次计划唯一码', max_length=64, blank=True)
    plan_trains = models.IntegerField(help_text='计划车次', verbose_name='计划车次')
    actual_trains = models.IntegerField(help_text='实际车次', verbose_name='实际车次')
    bath_no = models.IntegerField(help_text='批次', verbose_name='批次', blank=True)
    equip_no = models.CharField(max_length=64, help_text="机台号", verbose_name='机台号', blank=True)
    product_no = models.CharField(max_length=64, help_text='产出胶料', verbose_name='产出胶料', blank=True)
    plan_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='计划重量', verbose_name='计划重量')
    actual_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='实际重量', verbose_name='实际重量')
    begin_time = models.DateTimeField(help_text='开始时间', verbose_name='开始时间')
    end_time = models.DateTimeField(help_text='结束时间', verbose_name='结束时间')
    operation_user = models.CharField(max_length=64, help_text='操作员', verbose_name='操作员', blank=True)
    classes = models.CharField(max_length=64, help_text='班次', verbose_name='班次', blank=True)
    product_time = models.DateTimeField(help_text='工作站生产报表时间/存盘时间',
                                        verbose_name='工作站生产报表时间/存盘时间', null=True)
    factory_date = models.DateField(help_text='工厂日期', verbose_name='工厂日期', blank=True, null=True)

    '''中间表字段补充'''
    control_mode = models.CharField(max_length=8, blank=True, null=True, help_text='控制方式', verbose_name='控制方式')
    operating_type = models.CharField(max_length=8, blank=True, null=True, help_text='作业方式', verbose_name='作业方式')
    evacuation_time = models.IntegerField(blank=True, null=True, help_text='排胶时间', verbose_name='排胶时间')
    evacuation_temperature = models.IntegerField(blank=True, null=True, help_text='排胶温度', verbose_name='排胶温度')
    evacuation_energy = models.IntegerField(blank=True, null=True, help_text='排胶能量', verbose_name='排胶能量')
    interval_time = models.IntegerField(blank=True, null=True, help_text='间隔时间', verbose_name='间隔时间')
    mixer_time = models.IntegerField(blank=True, null=True, help_text='密炼时间', verbose_name='密炼时间')

    evacuation_power = models.CharField(max_length=64, blank=True, null=True, help_text='排胶功率', verbose_name='排胶功率')
    consum_time = models.IntegerField(blank=True, null=True, help_text='消耗总时间', verbose_name='消耗总时间')
    gum_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='胶料重量', verbose_name='胶料重量', null=True,
                                     blank=True)
    cb_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='炭黑重量', verbose_name='炭黑重量', null=True,
                                    blank=True)
    oil1_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='油1重量', verbose_name='油1重量', null=True,
                                      blank=True)
    oil2_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='油2重量', verbose_name='油2重量', null=True,
                                      blank=True)
    add_gum_time = models.IntegerField(blank=True, null=True, help_text='加胶时间', verbose_name='加胶时间')
    add_cb_time = models.IntegerField(blank=True, null=True, help_text='加炭黑时间', verbose_name='加炭黑时间')
    add_oil1_time = models.IntegerField(blank=True, null=True, help_text='加油1时间', verbose_name='加油1时间')
    add_oil2_time = models.IntegerField(blank=True, null=True, help_text='加油1时间', verbose_name='加油1时间')

    @property
    def time(self):
        temp = self.end_time - self.begin_time
        return temp.total_seconds()

    def __str__(self):
        return f"{self.plan_classes_uid}|{self.bath_no}|{self.equip_no}"

    class Meta:
        db_table = 'trains_feedbacks'
        verbose_name_plural = verbose_name = '胶料车次产出反馈'
        indexes = [
            models.Index(fields=['plan_classes_uid']),
            models.Index(fields=['equip_no']),
            models.Index(fields=['product_no']),
            models.Index(fields=['operation_user']),
            models.Index(fields=['begin_time']),
            models.Index(fields=['end_time']), ]


class PalletFeedbacks(AbstractEntity):
    """托盘产出反馈"""
    # id = models.BigIntegerField(primary_key=True, auto_created=True, unique=True)
    plan_classes_uid = models.CharField(help_text='班次计划唯一码', verbose_name='班次计划唯一码', max_length=64, blank=True)
    bath_no = models.IntegerField(help_text='批次', verbose_name='批次', blank=True)
    equip_no = models.CharField(max_length=64, help_text="机台号", verbose_name='机台号', blank=True)
    product_no = models.CharField(max_length=64, help_text='产出胶料', verbose_name='产出胶料', blank=True)
    plan_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='计划重量', verbose_name='计划重量')
    actual_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='实际重量', verbose_name='实际重量')
    begin_time = models.DateTimeField(help_text='开始时间', verbose_name='开始时间')
    end_time = models.DateTimeField(help_text='结束时间', verbose_name='结束时间')
    operation_user = models.CharField(max_length=74, help_text='操作员', verbose_name='操作员', blank=True)
    begin_trains = models.IntegerField(help_text='开始车次', verbose_name='开始车次')
    end_trains = models.IntegerField(help_text='结束车次', verbose_name='结束车次')
    pallet_no = models.CharField(max_length=64, help_text='托盘', verbose_name='托盘', blank=True)
    # barcode = models.CharField(max_length=64, help_text='收皮条码', verbose_name='收皮条码')
    classes = models.CharField(max_length=64, help_text='班次', verbose_name='班次', blank=True)
    lot_no = models.CharField(max_length=64, help_text='追踪号', verbose_name='追踪号', blank=True)
    product_time = models.DateTimeField(help_text='工作站生产报表时间/存盘时间',
                                        verbose_name='工作站生产报表时间/存盘时间', null=True)
    factory_date = models.DateField(help_text='工厂日期', verbose_name='工厂日期', blank=True, null=True)

    def __str__(self):
        return f"{self.plan_classes_uid}|{self.lot_no}|{self.equip_no}"

    class Meta:
        db_table = 'pallet_feedbacks'
        verbose_name_plural = verbose_name = '胶料托盘产出反馈'
        indexes = [
            models.Index(fields=['plan_classes_uid']),
            models.Index(fields=['equip_no']),
            models.Index(fields=['product_no']),
            models.Index(fields=["classes"]),
            models.Index(fields=["pallet_no"]),
            models.Index(fields=["end_time"]),
            models.Index(fields=["lot_no"]), ]


class EquipStatus(AbstractEntity):
    """机台状况反馈"""
    plan_classes_uid = models.CharField(help_text='班次计划唯一码', verbose_name='班次计划唯一码', max_length=64, blank=True)
    equip_no = models.CharField(max_length=64, help_text="机台号", verbose_name='机台号', blank=True)
    temperature = models.DecimalField(decimal_places=2, max_digits=8, help_text='温度', verbose_name='温度')
    rpm = models.DecimalField(decimal_places=2, max_digits=8, help_text='转速', verbose_name='转速')
    energy = models.DecimalField(decimal_places=2, max_digits=8, help_text='能量', verbose_name='能量')
    power = models.DecimalField(decimal_places=2, max_digits=8, help_text='功率', verbose_name='功率')
    pressure = models.DecimalField(decimal_places=2, max_digits=8, help_text='压力', verbose_name='压力')
    status = models.CharField(max_length=64, help_text='状态', verbose_name='状态', blank=True)
    current_trains = models.IntegerField(help_text='当前车次', verbose_name='当前车次')
    product_time = models.DateTimeField(help_text='工作站生产报表时间/存盘时间',
                                        verbose_name='工作站生产报表时间/存盘时间', null=True)

    def __str__(self):
        return f"{self.plan_classes_uid}|{self.equip_no}"

    class Meta:
        db_table = 'equip_status'
        verbose_name_plural = verbose_name = '机台状况反馈'
        indexes = [
            models.Index(fields=['equip_no']),
            models.Index(fields=['plan_classes_uid']),
            models.Index(fields=['product_time']),
            models.Index(fields=['current_trains']), ]


class PlanStatus(AbstractEntity):
    """计划状态变更"""
    plan_classes_uid = models.CharField(help_text='班次计划唯一码', verbose_name='班次计划唯一码', max_length=64, blank=True)
    equip_no = models.CharField(max_length=64, help_text="机台号", verbose_name='机台号', blank=True)
    product_no = models.CharField(max_length=64, help_text='产出胶料', verbose_name='产出胶料', blank=True)
    status = models.CharField(max_length=64, help_text='状态', verbose_name='状态', blank=True)
    operation_user = models.CharField(max_length=64, help_text='操作员', verbose_name='操作员', blank=True)
    product_time = models.DateTimeField(help_text='工作站生产报表时间/存盘时间',
                                        verbose_name='工作站生产报表时间/存盘时间', null=True)
    # 群控里有但是mes没有
    actual_trains = models.IntegerField(blank=True, null=True, help_text='实际车次', verbose_name='实际车次')

    def __str__(self):
        return f"{self.plan_classes_uid}|{self.equip_no}|{self.product_no}"

    class Meta:
        db_table = 'plan_status'
        verbose_name_plural = verbose_name = '计划状态变更'
        indexes = [
            models.Index(fields=['equip_no']),
            models.Index(fields=['plan_classes_uid']),
            models.Index(fields=['product_no']), ]


class ExpendMaterial(AbstractEntity):
    """原材料消耗表"""
    plan_classes_uid = models.CharField(help_text='班次计划唯一码', verbose_name='班次计划唯一码', max_length=64, blank=True)
    equip_no = models.CharField(max_length=64, help_text="机台号", verbose_name='机台号', blank=True)
    product_no = models.CharField(max_length=64, help_text='产出胶料', verbose_name='产出胶料', blank=True)
    trains = models.IntegerField(help_text='车次', verbose_name='车次')
    plan_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='计划重量', verbose_name='计划重量')
    actual_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='实际消耗重量', verbose_name='实际消耗重量')
    material_no = models.CharField(max_length=64, help_text='原材料id', verbose_name='原材料id', blank=True)
    material_type = models.CharField(max_length=64, help_text='原材料类型', verbose_name='原材料类型', blank=True)
    material_name = models.CharField(max_length=64, help_text='原材料名称', verbose_name='原材料名称', blank=True)
    product_time = models.DateTimeField(help_text='工作站生产报表时间/存盘时间',
                                        verbose_name='工作站生产报表时间/存盘时间', null=True)

    def __str__(self):
        return f"{self.plan_classes_uid}|{self.equip_no}|{self.product_no}|{self.material_no}"

    class Meta:
        db_table = 'expend_material'
        verbose_name_plural = verbose_name = '原材料消耗'
        indexes = [
            models.Index(fields=['equip_no']),
            models.Index(fields=['product_no']),
            models.Index(fields=['material_type']),
            models.Index(fields=['product_time']), ]


class OperationLog(AbstractEntity):
    """操作日志"""
    equip_no = models.CharField(max_length=64, help_text="机台号", verbose_name='机台号')
    content = models.CharField(max_length=1024, help_text='操作日志内容', verbose_name='操作日志内容')

    def __str__(self):
        return self.equip_no

    class Meta:
        db_table = 'operation_log'
        verbose_name_plural = verbose_name = '操作日志'


class QualityControl(AbstractEntity):
    """质检结果表"""
    barcode = models.CharField(max_length=64, help_text='收皮条码', verbose_name='收皮条码')
    qu_content = models.CharField(max_length=1024, help_text='质检内容', verbose_name='质检内容')

    def __str__(self):
        return self.barcode

    class Meta:
        db_table = 'quality-control'
        verbose_name_plural = verbose_name = '质检结果'


class MaterialTankStatus(AbstractEntity):
    """储料罐状态"""

    equip_no = models.CharField(max_length=64, help_text="机台号", verbose_name='机台号')
    tank_type = models.CharField(max_length=64, help_text="储料罐类型", verbose_name='储料罐类型')
    tank_name = models.CharField(max_length=64, help_text="储料罐名称", verbose_name='储料罐名称')
    tank_no = models.CharField(max_length=64, help_text="储料罐编号", verbose_name='储料罐编号')
    material_no = models.CharField(max_length=64, help_text='原材料id', verbose_name='原材料id')
    material_type = models.CharField(max_length=64, help_text='原材料类型', verbose_name='原材料类型')
    material_name = models.CharField(max_length=64, help_text='原材料名称', verbose_name='原材料名称')
    use_flag = models.BooleanField(help_text="是否启用", verbose_name='是否启用', default=0)
    low_value = models.DecimalField(decimal_places=2, max_digits=8, help_text='慢称值', verbose_name='慢称值')
    advance_value = models.DecimalField(decimal_places=2, max_digits=8, help_text='提前量', verbose_name='提前量')
    adjust_value = models.DecimalField(decimal_places=2, max_digits=8, help_text='调整值', verbose_name='调整值')
    dot_time = models.DecimalField(decimal_places=2, max_digits=8, help_text='点动时间', verbose_name='电动时间')
    fast_speed = models.DecimalField(decimal_places=2, max_digits=8, help_text='快称速度', verbose_name='快称速度')
    low_speed = models.DecimalField(decimal_places=2, max_digits=8, help_text='慢称速度', verbose_name='慢称速度')
    product_time = models.DateTimeField(help_text='工作站生产报表时间/存盘时间',
                                        verbose_name='工作站生产报表时间/存盘时间', null=True)

    def __str__(self):
        return f"{self.tank_name}|{self.tank_type}|{self.equip_no}"

    class Meta:
        db_table = 'material_tank_status'
        verbose_name_plural = verbose_name = '储料罐状态'
        indexes = [models.Index(fields=['equip_no']), ]


class UnReachedCapacityCause(AbstractEntity):
    factory_date = models.DateField('工厂日期')
    classes = models.CharField('班次', max_length=64)
    equip_no = models.CharField("机台号", max_length=64)
    cause = models.TextField('未达产能原因', blank=True, default='')

    class Meta:
        unique_together = ('factory_date', 'classes', 'equip_no')


# 将群控的车次报表移植过来
class ProcessFeedback(AbstractEntity):
    """步序反馈表"""
    sn = models.PositiveIntegerField(help_text='序号/步骤号')
    condition = models.CharField(max_length=20, help_text='条件', blank=True, null=True)
    time = models.PositiveIntegerField(help_text='时间(分钟)', default=0)
    temperature = models.PositiveIntegerField(help_text='温度', default=0)
    power = models.DecimalField(help_text='功率', default=0, decimal_places=1, max_digits=5)
    energy = models.DecimalField(help_text='能量', default=0, decimal_places=1, max_digits=5)
    action = models.CharField(max_length=20, help_text='基本动作', blank=True, null=True)
    rpm = models.PositiveIntegerField(help_text='转速', default=0)
    pressure = models.DecimalField(help_text='压力', default=0, decimal_places=1, max_digits=5)
    plan_classes_uid = models.CharField(help_text='班次计划唯一码', verbose_name='班次计划唯一码', max_length=64)
    product_no = models.CharField(max_length=64, help_text='产出胶料', verbose_name='产出胶料')
    product_time = models.DateTimeField(help_text='工作站生产报表时间/存盘时间', verbose_name='工作站生产报表时间/存盘时间', null=True)
    equip_no = models.CharField(max_length=64, help_text="机台号", verbose_name='机台号')
    current_trains = models.PositiveIntegerField(help_text='当前车次')

    def __str__(self):
        return f"{self.plan_classes_uid}|{self.equip_no}|{self.product_no}"

    class Meta:
        db_table = 'process_feedback'
        verbose_name_plural = verbose_name = '步序反馈报表'

class AlarmLog(AbstractEntity):
    """报警日志"""
    equip_no = models.CharField(max_length=64, help_text="机台号", verbose_name='机台号')
    content = models.TextField(max_length=1024, help_text="内容", verbose_name='内容')
    product_time = models.DateTimeField(help_text="报警时间", verbose_name='报警时间')

    class Meta:
        db_table = 'alarm_log'
        verbose_name_plural = verbose_name = '报警日志'
        indexes = [models.Index(fields=['equip_no']), models.Index(fields=['product_time'])]