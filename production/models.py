from django.db import models

from basics.models import AbstractEntity, GlobalCode, Location
from system.models import User


class TrainsFeedbacks(AbstractEntity):
    """车次产出反馈"""
    # id = models.BigIntegerField(primary_key=True, auto_created=True, unique=True)
    plan_classes_uid = models.CharField(help_text='班次计划唯一码', verbose_name='班次计划唯一码', max_length=64, blank=True, null=True)
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
            models.Index(fields=['end_time']),
            models.Index(fields=['factory_date'])]


class PalletFeedbacks(AbstractEntity):
    """托盘产出反馈"""
    # id = models.BigIntegerField(primary_key=True, auto_created=True, unique=True)
    plan_classes_uid = models.CharField(help_text='班次计划唯一码', verbose_name='班次计划唯一码', max_length=64, blank=True, null=True)
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
            models.Index(fields=["lot_no"]),
            models.Index(fields=['factory_date'])]


class EquipStatus(AbstractEntity):
    """机台状况反馈"""
    plan_classes_uid = models.CharField(help_text='班次计划唯一码', verbose_name='班次计划唯一码', max_length=64, blank=True, null=True)
    equip_no = models.CharField(max_length=64, help_text="机台号", verbose_name='机台号', blank=True, null=True)
    temperature = models.DecimalField(decimal_places=2, max_digits=8, help_text='温度', verbose_name='温度')
    rpm = models.DecimalField(decimal_places=2, max_digits=8, help_text='转速', verbose_name='转速')
    energy = models.DecimalField(decimal_places=2, max_digits=8, help_text='能量', verbose_name='能量')
    power = models.DecimalField(decimal_places=2, max_digits=8, help_text='功率', verbose_name='功率')
    pressure = models.DecimalField(decimal_places=2, max_digits=8, help_text='压力', verbose_name='压力')
    status = models.CharField(max_length=64, help_text='状态', verbose_name='状态', blank=True, null=True)
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
    plan_classes_uid = models.CharField(help_text='班次计划唯一码', verbose_name='班次计划唯一码', max_length=64, blank=True, null=True)
    equip_no = models.CharField(max_length=64, help_text="机台号", verbose_name='机台号', blank=True, null=True)
    product_no = models.CharField(max_length=64, help_text='产出胶料', verbose_name='产出胶料', blank=True, null=True)
    status = models.CharField(max_length=64, help_text='状态', verbose_name='状态', blank=True, null=True)
    operation_user = models.CharField(max_length=64, help_text='操作员', verbose_name='操作员', blank=True, null=True)
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
    plan_classes_uid = models.CharField(help_text='班次计划唯一码', verbose_name='班次计划唯一码', max_length=64, blank=True, null=True)
    equip_no = models.CharField(max_length=64, help_text="机台号", verbose_name='机台号', blank=True, null=True)
    product_no = models.CharField(max_length=64, help_text='产出胶料', verbose_name='产出胶料', blank=True, null=True)
    trains = models.IntegerField(help_text='车次', verbose_name='车次')
    plan_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='计划重量', verbose_name='计划重量')
    actual_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='实际消耗重量', verbose_name='实际消耗重量')
    material_no = models.CharField(max_length=64, help_text='原材料id', verbose_name='原材料id', blank=True, null=True)
    material_type = models.CharField(max_length=64, help_text='原材料类型', verbose_name='原材料类型', blank=True, null=True)
    material_name = models.CharField(max_length=64, help_text='原材料名称', verbose_name='原材料名称', blank=True, null=True)
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
            models.Index(fields=['plan_classes_uid'])]


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
        indexes = [
            models.Index(fields=['plan_classes_uid']),
            models.Index(fields=['equip_no']),
            models.Index(fields=['product_no'])
        ]


class AlarmLog(AbstractEntity):
    """报警日志"""
    equip_no = models.CharField(max_length=64, help_text="机台号", verbose_name='机台号')
    content = models.TextField(max_length=1024, help_text="内容", verbose_name='内容')
    product_time = models.DateTimeField(help_text="报警时间", verbose_name='报警时间')

    class Meta:
        db_table = 'alarm_log'
        verbose_name_plural = verbose_name = '报警日志'
        indexes = [models.Index(fields=['equip_no']), models.Index(fields=['product_time'])]


class ProductionLine(models.Model):
    no = models.CharField(max_length=64, help_text="编码", verbose_name='编码')
    name = models.CharField(max_length=64, help_text="产线名称", verbose_name='产线名称')
    desc = models.CharField(max_length=64, help_text='说明')
    use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)
    work_procedure = models.ForeignKey(GlobalCode, models.CASCADE, help_text='工序')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'production_line'
        verbose_name_plural = verbose_name = '产线'


class ProductionLineLocation(models.Model):
    location = models.ForeignKey(Location, help_text='位置点', on_delete=models.CASCADE)
    production_line = models.ForeignKey(ProductionLine, help_text='产线', on_delete=models.CASCADE)

    def __str__(self):
        return '{}-{}'.format(self.location, self.production_line)

    class Meta:
        db_table = 'production_line_location'
        verbose_name_plural = verbose_name = '产线位置点'


class ProductionDailyRecords(models.Model):
    factory_date = models.DateField(help_text='工厂日期')
    equip_error_record = models.TextField(help_text='设备异常记录', null=True)
    process_shutdown_record = models.TextField(help_text='工艺停机记录', null=True)
    production_shutdown_record = models.TextField(help_text='生产停机记录', null=True)
    auxiliary_positions_record = models.TextField(help_text='辅助岗位名单记录', null=True)
    classes = models.CharField(help_text='班次', max_length=64, null=True)
    shift_leader = models.CharField(help_text='值班长', max_length=64, null=True)

    class Meta:
        db_table = 'production_daily_records'


class ProductionPersonnelRecords(models.Model):
    equip_no = models.CharField(max_length=64, help_text="机台号", verbose_name='机台号')
    production_daily = models.ForeignKey(ProductionDailyRecords, related_name='production_personnel', on_delete=models.CASCADE)
    feeding_post = models.CharField('投料岗位', max_length=64, null=True)
    extrusion_post = models.CharField('挤出岗位', max_length=64, null=True)
    collection_post = models.CharField('收皮岗位', max_length=64, null=True)

    class Meta:
        db_table = 'production_personnel_records'


class RubberCannotPutinReason(models.Model):
    reason_name = models.CharField(help_text='原因名称', max_length=64)
    factory_date = models.DateTimeField(help_text='工厂时间')
    machine_no = models.CharField(max_length=64, help_text='机台')
    production_no = models.CharField(max_length=64, help_text='配方名')
    lot_no = models.CharField(max_length=64, help_text='托盘号')
    pallet_no = models.CharField(max_length=64, help_text='收皮条码')
    actual_weight = models.FloatField(help_text='实际重量')
    input_datetime = models.DateTimeField(help_text='录入时间')

    class Meta:
        db_table = 'rubber_cannot_putin_reason'


class MachineTargetYieldSettings(models.Model):
    Z01 = models.IntegerField(help_text='机台目标值')
    Z02 = models.IntegerField(help_text='机台目标值')
    Z03 = models.IntegerField(help_text='机台目标值')
    Z04 = models.IntegerField(help_text='机台目标值')
    Z05 = models.IntegerField(help_text='机台目标值')
    Z06 = models.IntegerField(help_text='机台目标值')
    Z07 = models.IntegerField(help_text='机台目标值')
    Z08 = models.IntegerField(help_text='机台目标值')
    Z09 = models.IntegerField(help_text='机台目标值')
    Z10 = models.IntegerField(help_text='机台目标值')
    Z11 = models.IntegerField(help_text='机台目标值')
    Z12 = models.IntegerField(help_text='机台目标值')
    Z13 = models.IntegerField(help_text='机台目标值')
    Z14 = models.IntegerField(help_text='机台目标值')
    Z15 = models.IntegerField(help_text='机台目标值')
    E190 = models.IntegerField(help_text='机台目标值/190E')
    input_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    input_datetime = models.DateTimeField(help_text='录入时间', auto_now_add=True)

    class Meta:
        db_table = 'machine_target_yield_settings'


class EmployeeAttendanceRecords(models.Model):
    user = models.ForeignKey(User, help_text='员工', on_delete=models.SET_NULL, null=True)
    section = models.CharField(help_text='岗位', max_length=64)
    factory_date = models.DateField(help_text='工厂时间')
    begin_date = models.DateTimeField(help_text='上岗时间', null=True, blank=True)
    end_date = models.DateTimeField(help_text='下岗时间', null=True, blank=True)
    work_time = models.FloatField(help_text='计算工作时间', null=True, blank=True, default=12)
    actual_time = models.FloatField(help_text='承认工作时间', null=True, blank=True, default=12)
    classes = models.CharField(help_text='班次', max_length=12, null=True, blank=True)
    group = models.CharField(help_text='班组', max_length=12, null=True, blank=True)
    equip = models.CharField(help_text='机台', max_length=12, null=True, blank=True)
    status = models.CharField(max_length=12, help_text='上岗/换岗/加班', null=True, blank=True)
    is_use = models.CharField(max_length=12, help_text='确认/添加/废弃', null=True, blank=True)

    class Meta:
        db_table = 'employee_attendance_records'
        verbose_name_plural = verbose_name = '员工出勤记录表'


class FillCardApply(models.Model):
    factory_date = models.DateField(help_text='工厂时间')
    user = models.ForeignKey(User, help_text='员工', on_delete=models.SET_NULL, null=True)
    equip = models.CharField(max_length=64, help_text='机台')
    classes = models.CharField(help_text='班次', max_length=12, null=True, blank=True)
    group = models.CharField(help_text='班组', max_length=12, null=True, blank=True)
    section = models.CharField(help_text='岗位', max_length=64)
    # employee_attendance_records_ids = models.CharField(max_length=32, help_text='考勤记录', null=True, blank=True)
    bk_date = models.DateTimeField(help_text='补卡时间', null=True, blank=True)
    desc = models.TextField(help_text='补卡理由', null=True, blank=True)
    handling_suggestion = models.TextField(help_text='处理意见', null=True, blank=True)
    handling_result = models.NullBooleanField(help_text='处理结果', default=None)
    apply_date = models.DateTimeField(auto_now_add=True, help_text='申请时间')
    status = models.CharField(max_length=12, help_text='上岗/换岗/下岗', null=True, blank=True)

    class Meta:
        db_table = 'fill_card_apply'
        verbose_name_plural = verbose_name = '补卡申请'


class ApplyForExtraWork(models.Model):
    factory_date = models.DateField(help_text='工厂时间')
    user = models.ForeignKey(User, help_text='员工', on_delete=models.SET_NULL, null=True)
    equip = models.CharField(max_length=64, help_text='机台')
    classes = models.CharField(help_text='班次', max_length=12, null=True, blank=True)
    group = models.CharField(help_text='班组', max_length=12, null=True, blank=True)
    section = models.CharField(help_text='岗位', max_length=64)
    employee_attendance_records_ids = models.CharField(max_length=32, help_text='考勤记录', null=True, blank=True)
    begin_date = models.DateTimeField(help_text='加班开始时间', null=True, blank=True)
    end_date = models.DateTimeField(help_text='加班结束', null=True, blank=True)
    desc = models.TextField(help_text='加班理由', null=True, blank=True)
    handling_suggestion = models.TextField(help_text='处理意见', null=True, blank=True)
    apply_date = models.DateTimeField(auto_now_add=True, help_text='申请时间')
    handling_result = models.NullBooleanField(help_text='处理结果', default=None)

    class Meta:
        db_table = 'apply_for_extra_work'
        verbose_name_plural = verbose_name = '加班申请'


class PerformanceJobLadder(models.Model):
    Status = (
        (1, '最大值'),
        (2, '平均值')
    )
    code = models.CharField(help_text='岗位编号', max_length=64, unique=True)
    name = models.CharField(help_text='岗位名称', max_length=64)
    type = models.CharField(help_text='岗位类别', max_length=64, null=True, blank=True)
    coefficient = models.IntegerField(help_text='绩效系数')
    post_standard = models.PositiveIntegerField(choices=Status, default=1, help_text='多岗位合并基准', null=True, blank=True)
    post_coefficient = models.IntegerField(help_text='多岗位合并系数', null=True, blank=True)
    delete_flag = models.BooleanField(help_text='是否删除', verbose_name='是否删除', default=False)

    class Meta:
        db_table = 'performance_job_ladder'
        verbose_name_plural = verbose_name = '岗位阶梯表'


class PerformanceUnitPrice(models.Model):
    state = models.CharField(help_text='段次', max_length=64)
    equip_type = models.CharField(help_text='机型', max_length=64)
    pt = models.FloatField(help_text='普通胶', null=True, blank=True)
    dj = models.FloatField(help_text='丁基胶', null=True, blank=True)

    class Meta:
        db_table = 'performance_unit_price'
        verbose_name_plural = verbose_name = '绩效单价表'


class ProductInfoDingJi(AbstractEntity):
    product_no = models.CharField(help_text='胶料编码', max_length=64)
    product_name = models.CharField(help_text='胶料名称', max_length=64)
    is_use = models.BooleanField(help_text='是否作为丁基胶判断标准', default=0)

    class Meta:
        db_table = 'product_info_dingji'
        verbose_name_plural = verbose_name = '丁基胶规格设定'


class SetThePrice(models.Model):
    xl = models.FloatField(help_text='细料单价')
    lh = models.FloatField(help_text='硫磺单价')

    class Meta:
        db_table = 'set_the_price'
        verbose_name_plural = verbose_name = '设定细料硫磺单价'


class SubsidyInfo(models.Model):
    Type = (
        (1, '其他奖惩'),
        (2, '生产补贴')
    )
    date = models.DateField(help_text='日期', null=True, blank=True)
    type = models.PositiveIntegerField(help_text='补贴类别', choices=Type, default=1)
    name = models.CharField(max_length=64, help_text='姓名')
    group = models.CharField(max_length=12, help_text='班组')
    price = models.FloatField(help_text='补贴/奖励金额', default=0)
    desc = models.TextField(help_text='补贴说明', null=True, blank=True)

    class Meta:
        db_table = 'subsidy_info'
        verbose_name_plural = verbose_name = '员工绩效汇总'


class IndependentPostTemplate(models.Model):
    name = models.CharField(max_length=64, help_text='姓名')
    status = models.BooleanField(help_text='是否独立上岗', default=1)
    work_type = models.CharField(max_length=64, help_text='员工类别', default='正常')
    date_time = models.CharField(max_length=12, help_text='日期：2022-3')

    class Meta:
        db_table = 'independent_post_template'
        verbose_name_plural = verbose_name = '是否独立上岗'


class AttendanceGroupSetup(models.Model):
    attendance_group = models.CharField(max_length=64, help_text='考勤组名称')
    attendance_users = models.CharField(max_length=64, help_text='参加考勤人员')
    attendance_st = models.TimeField(help_text='考勤开始时间')
    attendance_et = models.TimeField(help_text='考勤结束时间')
    principal = models.CharField(max_length=64, help_text='考勤负责人')
    range_time = models.IntegerField(help_text='上班多久后可打下班卡', null=True, blank=True)
    lead_time = models.IntegerField(help_text='提前几分钟可打工卡', null=True, blank=True)
    type = models.CharField(help_text='类别', max_length=64, null=True, blank=True)

    class Meta:
        db_table = 'attendance_group_setup'
        verbose_name_plural = verbose_name = '绩效管理考勤组'


class EquipMaxValueCache(models.Model):
    equip_no = models.CharField(max_length=12, help_text='机台')
    date_time = models.DateField(help_text='缓存截止时间')
    value = models.IntegerField(default=0, help_text='机台最高产量')

    class Meta:
        db_table ='equip_max_value_cache'
        verbose_name_plural = verbose_name = '机台最高产量缓存'


class OuterMaterial(models.Model):
    factory_date = models.DateField(help_text='工厂时间')
    weight = models.DecimalField(max_digits=8, decimal_places=2, help_text='吨')

    class Meta:
        db_table = 'outer_material'
        verbose_name_plural = verbose_name = '外发无硫料'


class Equip190E(models.Model):
    specification = models.CharField(max_length=12, help_text='规格')
    state = models.CharField(max_length=12, help_text='段次')
    weight = models.DecimalField(max_digits=8, decimal_places=2, help_text='kg')

    class Meta:
        db_table = 'equip_190e'
        verbose_name_plural = verbose_name = '190E机台规格信息设定'


class Equip190EWeight(models.Model):
    setup = models.ForeignKey(Equip190E, on_delete=models.CASCADE)
    factory_date = models.DateField(help_text='工厂时间', null=True, blank=True)
    classes = models.CharField(help_text='班次', max_length=12, null=True, blank=True)
    qty = models.IntegerField(help_text='车数', null=True, blank=True)

    class Meta:
        db_table = 'equip_190e_weight'
        verbose_name_plural = verbose_name = '190E机台产量信息'


class AttendanceClockDetail(models.Model):
    name = models.CharField(max_length=64, help_text='姓名')
    date = models.DateField(auto_now_add=True, help_text='打卡日期')
    date_time = models.DateTimeField(auto_now_add=True, help_text='打卡时间')
    equip = models.CharField(max_length=64, help_text='机台')
    group = models.CharField(max_length=64, help_text='班组')
    classes = models.CharField(max_length=64, help_text='班次')
    section = models.CharField(max_length=64, help_text='岗位')
    work_type = models.CharField(max_length=64, help_text='打卡类别')

    class Meta:
        db_table = 'attendance_clock_detail'
        verbose_name_plural = verbose_name = '用户考勤打卡明细'


class MlTrainsInfo(AbstractEntity):
    factory_date = models.DateField(help_text='工厂时间')
    classes = models.CharField(help_text='班次', max_length=12)
    equip_no = models.CharField(max_length=12, help_text='机台')
    product_no = models.CharField(max_length=64, help_text='胶料编码')
    trains = models.IntegerField(help_text='车数', default=0)

    class Meta:
        db_table = 'ml_trains_info'
        verbose_name_plural = verbose_name = '录入人工密炼车次信息'
