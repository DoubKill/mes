from django.db import models

from basics.models import AbstractEntity

class TrainsFeedbacks(AbstractEntity):
    """车次产出反馈"""
    # id = models.BigIntegerField(primary_key=True, auto_created=True, unique=True)
    plan_classes_uid = models.CharField(help_text='班次计划唯一码', verbose_name='班次计划唯一码',max_length=64, blank=True)
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
    product_time = models.DateTimeField(help_text='工作站生产报表时间/存盘时间', verbose_name='工作站生产报表时间/存盘时间',null=True)

    @property
    def time(self):
        temp = self.end_time - self.begin_time
        return temp.total_seconds()

    def __str__(self):
        return f"{self.plan_classes_uid}|{self.bath_no}|{self.equip_no}"

    class Meta:
        db_table = 'trains_feedbacks'
        verbose_name_plural = verbose_name = '胶料车次产出反馈'


class PalletFeedbacks(AbstractEntity):
    """托盘产出反馈"""
    # id = models.BigIntegerField(primary_key=True, auto_created=True, unique=True)
    plan_classes_uid = models.CharField(help_text='班次计划唯一码', verbose_name='班次计划唯一码',max_length=64, blank=True)
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
    product_time = models.DateTimeField(help_text='工作站生产报表时间/存盘时间', verbose_name='工作站生产报表时间/存盘时间',null=True)

    def __str__(self):
        return f"{self.plan_classes_uid}|{self.lot_no}|{self.equip_no}"

    class Meta:
        db_table = 'pallet_feedbacks'
        verbose_name_plural = verbose_name = '胶料托盘产出反馈'


class EquipStatus(AbstractEntity):
    """机台状况反馈"""
    plan_classes_uid = models.CharField(help_text='班次计划唯一码', verbose_name='班次计划唯一码',max_length=64, blank=True)
    equip_no = models.CharField(max_length=64, help_text="机台号", verbose_name='机台号', blank=True)
    temperature = models.DecimalField(decimal_places=2, max_digits=8, help_text='温度', verbose_name='温度')
    rpm = models.DecimalField(decimal_places=2, max_digits=8, help_text='转速', verbose_name='转速')
    energy = models.DecimalField(decimal_places=2, max_digits=8, help_text='能量', verbose_name='能量')
    power = models.DecimalField(decimal_places=2, max_digits=8, help_text='功率', verbose_name='功率')
    pressure = models.DecimalField(decimal_places=2, max_digits=8, help_text='压力', verbose_name='压力')
    status = models.CharField(max_length=64, help_text='状态', verbose_name='状态')
    current_trains = models.IntegerField(help_text='当前车次', verbose_name='当前车次')
    product_time = models.DateTimeField(help_text='工作站生产报表时间/存盘时间', verbose_name='工作站生产报表时间/存盘时间',null=True)

    def __str__(self):
        return f"{self.plan_classes_uid}|{self.equip_no}"

    class Meta:
        db_table = 'equip_status'
        verbose_name_plural = verbose_name = '机台状况反馈'


class PlanStatus(AbstractEntity):
    """计划状态变更"""
    plan_classes_uid = models.CharField(help_text='班次计划唯一码', verbose_name='班次计划唯一码',max_length=64, blank=True)
    equip_no = models.CharField(max_length=64, help_text="机台号", verbose_name='机台号', blank=True)
    product_no = models.CharField(max_length=64, help_text='产出胶料', verbose_name='产出胶料', blank=True)
    status = models.CharField(max_length=64, help_text='状态', verbose_name='状态', blank=True)
    operation_user = models.CharField(max_length=64, help_text='操作员', verbose_name='操作员', blank=True)
    product_time = models.DateTimeField(help_text='工作站生产报表时间/存盘时间', verbose_name='工作站生产报表时间/存盘时间',null=True)

    def __str__(self):
        return f"{self.plan_classes_uid}|{self.equip_no}|{self.product_no}"

    class Meta:
        db_table = 'plan_status'
        verbose_name_plural = verbose_name = '计划状态变更'


class ExpendMaterial(AbstractEntity):
    """原材料消耗表"""
    plan_classes_uid = models.CharField(help_text='班次计划唯一码', verbose_name='班次计划唯一码',max_length=64, blank=True)
    equip_no = models.CharField(max_length=64, help_text="机台号", verbose_name='机台号', blank=True)
    product_no = models.CharField(max_length=64, help_text='产出胶料', verbose_name='产出胶料', blank=True)
    trains = models.IntegerField(help_text='车次', verbose_name='车次')
    plan_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='计划重量', verbose_name='计划重量')
    actual_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='实际消耗重量', verbose_name='实际消耗重量')
    masterial_no = models.CharField(max_length=64, help_text='原材料id', verbose_name='原材料id', blank=True)
    masterial_type = models.CharField(max_length=64, help_text='原材料类型', verbose_name='原材料类型', blank=True)
    masterial_name = models.CharField(max_length=64, help_text='原材料名称', verbose_name='原材料名称', blank=True)
    product_time = models.DateTimeField(help_text='工作站生产报表时间/存盘时间', verbose_name='工作站生产报表时间/存盘时间',null=True)

    def __str__(self):
        return f"{self.plan_classes_uid}|{self.equip_no}|{self.product_no}|{self.masterial_no}"

    class Meta:
        db_table = 'expend_material'
        verbose_name_plural = verbose_name = '原材料消耗'


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
    masterial_no = models.CharField(max_length=64, help_text='原材料id', verbose_name='原材料id')
    masterial_type = models.CharField(max_length=64, help_text='原材料类型', verbose_name='原材料类型')
    masterial_name = models.CharField(max_length=64, help_text='原材料名称', verbose_name='原材料名称')
    use_flag = models.BooleanField(help_text="是否启用", verbose_name='是否启用', default=0)
    low_value = models.DecimalField(decimal_places=2, max_digits=8, help_text='慢称值', verbose_name='慢称值')
    advance_value = models.DecimalField(decimal_places=2, max_digits=8, help_text='提前量', verbose_name='提前量')
    adjust_value = models.DecimalField(decimal_places=2, max_digits=8, help_text='调整值', verbose_name='调整值')
    dot_time = models.DecimalField(decimal_places=2, max_digits=8, help_text='点动时间', verbose_name='电动时间')
    fast_speed = models.DecimalField(decimal_places=2, max_digits=8, help_text='快称速度', verbose_name='快称速度')
    low_speed = models.DecimalField(decimal_places=2, max_digits=8, help_text='慢称速度', verbose_name='慢称速度')
    product_time = models.DateTimeField(help_text='工作站生产报表时间/存盘时间', verbose_name='工作站生产报表时间/存盘时间',null=True)

    def __str__(self):
        return f"{self.tank_name}|{self.tank_type}|{self.equip_no}"

    class Meta:
        db_table = 'material_tank_status'
        verbose_name_plural = verbose_name = '储料罐状态'