from django.db import models

from basics.models import Equip, GlobalCode, Location
from recipe.models import Material
from system.models import AbstractEntity


class Terminal(AbstractEntity):
    name = models.CharField(max_length=64, help_text='终端名称')
    no = models.CharField(max_length=64, help_text='终端编码(MAC地址)', unique=True)
    desc = models.CharField(max_length=64, help_text='描述', blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'terminal'
        verbose_name_plural = verbose_name = '终端'


class TerminalLocation(AbstractEntity):
    location = models.ForeignKey(Location, help_text='位置点', on_delete=models.CASCADE)
    terminal = models.ForeignKey(Terminal, help_text='终端', on_delete=models.CASCADE)
    equip = models.ForeignKey(Equip, help_text='设备', on_delete=models.CASCADE)

    def __str__(self):
        return '{}-{}-{}'.format(self.terminal, self.location, self.equip)

    class Meta:
        db_table = 'terminal_location_binding'
        verbose_name_plural = verbose_name = '终端位置点绑定'


class FeedingMaterialLog(models.Model):
    """群控中的模型"""
    STATUS_CHOICE = (
        (1, '正常'),
        (2, '异常')
    )
    feed_uid = models.CharField(max_length=64, help_text='进料uid')
    equip_no = models.CharField(max_length=64, help_text='设备编号')
    plan_classes_uid = models.CharField(verbose_name='班次计划唯一码', help_text='班次计划唯一码', max_length=64)
    trains = models.IntegerField(help_text='车次')
    product_no = models.CharField(max_length=64, help_text='胶料名称')
    production_factory_date = models.DateField(max_length=64, help_text='工厂时间')
    production_classes = models.CharField(max_length=64, help_text='生产班次')
    production_group = models.CharField(max_length=64, help_text='生产班组')
    batch_time = models.DateTimeField(help_text='投入时间', null=True)
    batch_classes = models.CharField(max_length=64, help_text='投入班次', null=True)
    batch_group = models.CharField(max_length=64, help_text='投入班组', null=True)
    feedback_time = models.DateTimeField(help_text='重量反馈时间', null=True)
    feed_begin_time = models.DateTimeField(help_text='进料开始时间', null=True)
    feed_end_time = models.DateTimeField(help_text='进料结束时间', null=True)
    failed_flag = models.PositiveIntegerField(help_text='状态', choices=STATUS_CHOICE, default=1)
    judge_reason = models.CharField(max_length=64, help_text='防错结果', blank=True, null=True)
    feed_status = models.CharField(max_length=8, help_text='进料类型: 正常;处理;强制;', blank=True, null=True)
    add_feed_result = models.IntegerField(help_text='扫码补充物料后是否能进上辅机: 0 可进; 1 不可进', blank=True, null=True)
    created_username = models.CharField(max_length=64, help_text='投入操作人', null=True, blank=True)

    class Meta:
        db_table = 'feed_material_log'
        verbose_name_plural = verbose_name = '进料履历'
        managed = False


class LoadMaterialLog(models.Model):
    """群控中的模型"""
    STATUS_CHOICE = (
        (1, '正常'),
        (2, '异常')
    )
    feed_log = models.ForeignKey(FeedingMaterialLog, on_delete=models.CASCADE)
    material_no = models.CharField(max_length=64, help_text='物料编码')
    material_name = models.CharField(max_length=64, help_text='物料名称')
    plan_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='计划重量', default=0)
    actual_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='实际重量', default=0)
    bra_code = models.CharField(max_length=64, help_text='条形码')
    weight_time = models.DateTimeField(help_text='上料时间', null=True)
    status = models.PositiveIntegerField(help_text='状态', choices=STATUS_CHOICE, blank=True, null=True)

    class Meta:
        db_table = 'load_material_log'
        verbose_name_plural = verbose_name = '上料履历'
        managed = False


class WeightPackageLog(AbstractEntity):
    PRINT_CHOICE = (
        (0, ''),
        (1, '点击打印'),
        (2, '调用打印'),
        (3, '打印成功')
    )
    equip_no = models.CharField(max_length=64, help_text='称量设备编号')
    plan_weight_uid = models.CharField(max_length=64, help_text='小料称量计划号')
    product_no = models.CharField(max_length=64, help_text='胶料名称-配方号')
    material_name = models.CharField(max_length=64, help_text='物料打包名称', null=True)
    material_no = models.CharField(max_length=64, help_text='物料打包编号', null=True)
    plan_weight = models.DecimalField(decimal_places=3, max_digits=8, help_text='单重', default=0)
    actual_weight = models.DecimalField(decimal_places=3, max_digits=8, help_text='实际重量', default=0)
    bra_code = models.CharField(max_length=64, help_text='条形码')
    status = models.CharField(help_text='打印状态', max_length=8, default='N')
    batch_time = models.DateTimeField(max_length=10, help_text='配料日期')
    batch_classes = models.CharField(max_length=8, help_text='配料班次')
    batch_group = models.CharField(max_length=8, help_text='配料班组')
    location_no = models.CharField(max_length=64, help_text='产线', null=True)
    dev_type = models.CharField(max_length=64, help_text='机型名称')
    begin_trains = models.IntegerField(help_text='开始包')
    end_trains = models.IntegerField(help_text='结束包')
    package_count = models.IntegerField(help_text='配置数量')
    print_begin_trains = models.IntegerField(help_text='打印起始车次')
    noprint_count = models.IntegerField(help_text='未打印数量')
    package_fufil = models.IntegerField(help_text='配料完成数量')
    package_plan_count = models.IntegerField(help_text='配料计划数量')
    print_flag = models.IntegerField(help_text='打印交互', choices=PRINT_CHOICE)
    print_count = models.IntegerField(help_text='打印数量', default=1)
    expire_days = models.IntegerField(help_text='有效期')
    record = models.IntegerField(help_text='plan表数据id', null=True)

    class Meta:
        db_table = 'weight_package_log'
        verbose_name_plural = verbose_name = '称量打包履历'


class PackageExpire(models.Model):
    product_no = models.CharField(max_length=64, help_text='配方号')
    product_name = models.CharField(max_length=64, help_text='配方名称')
    package_fine_usefullife = models.IntegerField(help_text='细料包有效期(天)', default=0)
    package_sulfur_usefullife = models.IntegerField(help_text='硫磺包有效期(天)', default=0)
    update_user = models.CharField(max_length=64, help_text='更新人员')
    update_date = models.DateField(help_text='更新时间')

    class Meta:
        db_table = 'package_expire'
        verbose_name_plural = verbose_name = '料包有效期'


class WeightBatchingLog(AbstractEntity):
    STATUS_CHOICE = (
        (1, '正常'),
        (2, '异常')
    )
    equip_no = models.CharField(max_length=64, help_text='称量设备编号')
    # plan_batching_uid = models.CharField(max_length=64, help_text='小料称量计划号')
    # product_no = models.CharField(max_length=64, help_text='胶料名称')
    scan_material = models.CharField(max_length=64, help_text='条码出库原材料名')
    material_name = models.CharField(max_length=64, help_text='原材料名称')
    material_no = models.CharField(max_length=64, help_text='原材料编码')
    # plan_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='计划重量', default=0)
    # actual_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='实际重量', default=0)
    bra_code = models.CharField(max_length=64, help_text='条形码')
    status = models.PositiveIntegerField(help_text='状态', choices=STATUS_CHOICE, default=1)
    batch_time = models.DateTimeField(max_length=64, help_text='投入时间')
    batch_classes = models.CharField(max_length=64, help_text='投入班次')
    batch_group = models.CharField(max_length=64, help_text='投入班组')
    tank_no = models.CharField(max_length=64, help_text='投入罐号')
    location_no = models.CharField(max_length=64, help_text='产线')
    dev_type = models.CharField(max_length=64, help_text='机型名称')
    failed_reason = models.CharField(max_length=64, help_text='投料失败原因')
    # quantity = models.IntegerField(default=1, help_text='包数')

    class Meta:
        db_table = 'weight_batch_log'
        verbose_name_plural = verbose_name = '称量投料履历'


class WeightTankStatus(AbstractEntity):
    STATUS_CHOICE = (
        (1, '低位'),
        (2, '高位'),
        (3, '正常位')
    )
    # tank_type = models.PositiveIntegerField(help_text='物料罐类型，1：炭黑罐  2：油料罐', choices=TANK_TYPE_CHOICE)
    tank_name = models.CharField(max_length=64, help_text='物料罐名称')
    tank_no = models.CharField(max_length=64, help_text='物料罐编号')
    material_name = models.CharField(max_length=64, help_text='原材料名称')
    material_no = models.CharField(max_length=64, help_text='原材料编码')
    use_flag = models.BooleanField(help_text='使用与否', default=True)
    status = models.PositiveIntegerField(help_text='状态，1：低位  2：高位, 3:正常位', choices=STATUS_CHOICE)
    open_flag = models.BooleanField(help_text='开启与否', default=False)
    equip_no = models.CharField(max_length=64, help_text='机台编号')

    class Meta:
        db_table = 'weight_tank_status'
        verbose_name_plural = verbose_name = '称量罐状态'


class EquipOperationLog(AbstractEntity):
    TYPE_CHOICE = (
        (1, '停机'),
        (2, '解除停机')
    )
    equip_no = models.CharField(max_length=64, help_text='机台编号')
    operation_type = models.PositiveIntegerField(help_text='操作类型', choices=TYPE_CHOICE)
    reason = models.CharField(max_length=64, help_text='原因', blank=True, null=True)

    class Meta:
        db_table = 'equip_operation_log'
        verbose_name_plural = verbose_name = '机台操作日志'


class FeedingLog(AbstractEntity):
    feeding_port = models.CharField(max_length=64, help_text='投料口')
    material_name = models.CharField(max_length=64, help_text='物料名称')

    class Meta:
        db_table = 'feeding_log'
        verbose_name_plural = verbose_name = '投料履历'


class LoadTankMaterialLog(AbstractEntity):
    plan_classes_uid = models.CharField(max_length=64, help_text='小料称量计划号')
    scan_material = models.CharField(max_length=64, help_text='扫码物料名', default='')
    material_no = models.CharField(max_length=64, help_text='原材料编码')
    material_name = models.CharField(max_length=64, help_text='原材料名称')
    bra_code = models.CharField(max_length=64, help_text='条形码')
    unit = models.CharField(db_column='WeightUnit', max_length=64)
    scan_time = models.DateTimeField(max_length=64, help_text='扫码时间')
    useup_time = models.DateTimeField(max_length=64, help_text='用完时间')
    init_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='初始重量', default=0)
    # real_weight  修正剩余量后计算使用
    real_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='真实计算重量', default=0)
    actual_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='当前消耗重量', default=0)
    adjust_left_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='调整剩余重量', default=0)
    single_need = models.DecimalField(decimal_places=2, max_digits=8, help_text='单车需要物料数量', null=True, blank=True)
    variety = models.DecimalField(decimal_places=2, max_digits=8, help_text='物料修改变化量', null=True, blank=True, default=0)

    class Meta:
        db_table = 'load_tank_material_log'
        verbose_name_plural = verbose_name = '料框物料信息'


class MaterialChangeLog(models.Model):
    bra_code = models.CharField(max_length=64, help_text='条形码')
    material_name = models.CharField(max_length=64, help_text='原材料名称')
    created_time = models.DateTimeField(help_text='修改时间')
    qty_change = models.DecimalField(decimal_places=2, max_digits=8, help_text='本次变化量', default=0)

    class Meta:
        db_table = 'material_change_log'
        verbose_name_plural = verbose_name = '料框物料修改履历'


class Version(models.Model):
    VERSION_CHOICE = (
        (1, "PDA"),
        (2, "密炼投料"),
        (3, "小料包产出"),
        (4, "小料称量"),
        (5, "人工称量")
    )
    type = models.PositiveIntegerField(choices=VERSION_CHOICE, verbose_name="类别")
    number = models.CharField(max_length=20, verbose_name="版本号")
    desc = models.CharField(max_length=200, verbose_name="版本说明", blank=True, null=True)
    url = models.URLField(verbose_name="更新地址", max_length=128)

    class Meta:
        db_table = 'versions'
        verbose_name_plural = verbose_name = '版本管理'
        ordering = ('id', 'type', 'number')
        unique_together = ['type', 'number']

    def __str__(self):
        return "{}----{}".format(self.get_type_display(), self.number)


"""
小料称量系统模型
"""


class Bin(models.Model):
    """料仓物料信息表"""
    id = models.BigAutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    bin = models.CharField(db_column='Bin', help_text='料仓位置', max_length=3, blank=True, null=True)  # Field name made lowercase.
    name = models.CharField(max_length=50, help_text='物料名称', blank=True, null=True)
    code = models.CharField(max_length=50, help_text='物料代码', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bin'


class MaterialInfo(models.Model):
    """原材料信息表"""
    id = models.BigAutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    name = models.CharField(max_length=50, help_text='物料名称', blank=True, null=True)
    code = models.CharField(max_length=50,  help_text='物料代码', blank=True, null=True)
    time = models.CharField(max_length=19, help_text='更新时间', blank=True, null=True)
    remark = models.CharField(max_length=10, help_text='备注', blank=True, null=True)
    use_not = models.IntegerField(blank=True, help_text='是否使用，0是1否', null=True)

    class Meta:
        managed = False
        db_table = 'material'


class Plan(models.Model):
    """称量计划"""
    id = models.BigAutoField(db_column='ID', help_text='自增字段',primary_key=True)  # Field name made lowercase.
    planid = models.CharField(max_length=14, help_text='mes传唯一码', blank=True, null=True)
    recipe = models.CharField(max_length=50, help_text='配方名称', blank=True, null=True)
    recipe_id = models.CharField(max_length=10, help_text='配方id', blank=True, null=True)
    recipe_ver = models.CharField(max_length=10, blank=True, help_text='配方版本',null=True)
    starttime = models.CharField(max_length=19, help_text='起始时间，写入后会被上位机更新',blank=True, null=True)
    stoptime = models.CharField(max_length=19, help_text='结束时间，不用写上位机更新',blank=True, null=True)
    grouptime = models.CharField(max_length=4, help_text='班时：早班、中班、晚班', blank=True, null=True)
    oper = models.CharField(max_length=8, help_text='操作员', blank=True, null=True)
    state = models.CharField(max_length=4, help_text='完成、终止、等待、运行中', blank=True, null=True)
    setno = models.IntegerField(blank=True, help_text='设定车次', null=True)
    actno = models.IntegerField(blank=True, help_text='完成车次，写0', null=True)
    order_by = models.IntegerField(blank=True, help_text='写1', null=True)
    date_time = models.CharField(max_length=10, help_text='日期', blank=True, null=True)
    addtime = models.CharField(max_length=19, help_text='创建时间', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'plan'


class RecipeMaterial(models.Model):
    """配方物料数据"""
    id = models.BigAutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    recipe_name = models.CharField(max_length=50, help_text='recipe_pre中配方名称', blank=True, null=True)
    name = models.CharField(max_length=50, help_text='物料名称', blank=True, null=True)
    weight = models.DecimalField(max_digits=5, decimal_places=3, blank=True, null=True)
    error = models.DecimalField(max_digits=4, decimal_places=3, blank=True, null=True)
    time = models.CharField(max_length=19, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'recipe_material'


class RecipePre(models.Model):
    """配方基础数据(表头数据)"""
    id = models.BigAutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    name = models.CharField(max_length=50, help_text='配方名称，唯一', blank=True, null=True)
    ver = models.CharField(max_length=10, blank=True, help_text='配方版本', null=True)
    remark1 = models.CharField(max_length=50, blank=True, null=True)
    remark2 = models.CharField(max_length=50, blank=True, null=True)
    weight = models.DecimalField(max_digits=6, help_text='原材料总重量，计算得出', decimal_places=3, blank=True, null=True)
    error = models.DecimalField(max_digits=5, help_text='总误差，界面写入', decimal_places=3, blank=True, null=True)
    time = models.CharField(max_length=19, help_text='修改时间', blank=True, null=True)
    use_not = models.IntegerField(blank=True, help_text='是否使用，0是1否', null=True)

    class Meta:
        managed = False
        db_table = 'recipe_pre'


class ReportBasic(models.Model):
    """称量车次报表数据"""
    id = models.BigAutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    planid = models.CharField(max_length=14, help_text='mes写入计划唯一码', blank=True, null=True)
    starttime = models.CharField(max_length=19, blank=True, null=True)
    savetime = models.CharField(max_length=19, blank=True, null=True)
    grouptime = models.CharField(max_length=4, blank=True, null=True)
    recipe = models.CharField(max_length=50, blank=True, null=True)
    recipe_ver = models.CharField(max_length=10, blank=True, null=True)
    setno = models.IntegerField(blank=True, null=True)
    actno = models.IntegerField(blank=True, null=True)
    set_weight = models.DecimalField(max_digits=5, decimal_places=3, blank=True, null=True)
    act_weight = models.DecimalField(max_digits=5, decimal_places=3, blank=True, null=True)
    warning = models.IntegerField(blank=True, help_text='检量是否报警，1：不合格，0：合格', null=True)
    set_error = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)
    act_error = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'report_basic'


class ReportWeight(models.Model):
    """物料消耗报表数据"""
    id = models.BigAutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    planid = models.CharField(max_length=14, blank=True, null=True)
    recipe = models.CharField(max_length=50, blank=True, null=True)
    setno = models.IntegerField(blank=True, null=True)
    车次 = models.IntegerField(blank=True, help_text='实际车次', null=True)
    recipe_ver = models.CharField(max_length=10, blank=True, null=True)
    时间 = models.CharField(max_length=19, help_text='称量耗时', blank=True, null=True)
    grouptime = models.CharField(max_length=4, blank=True, null=True)
    material = models.CharField(max_length=50, blank=True, null=True)
    set_weight = models.DecimalField(max_digits=5, decimal_places=3, blank=True, null=True)
    set_error = models.DecimalField(max_digits=4, decimal_places=3, blank=True, null=True)
    act_weight = models.DecimalField(max_digits=5, decimal_places=3, blank=True, null=True)
    warning = models.IntegerField(blank=True, null=True)
    back1 = models.CharField(max_length=10, help_text='没用', blank=True, null=True)
    act_error = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)
    time = models.IntegerField(blank=True, help_text='没用', null=True)

    class Meta:
        managed = False
        db_table = 'report_weight'

# class TempPlan(models.Model):
#     id = models.BigIntegerField(db_column='ID')  # Field name made lowercase.
#     planid = models.CharField(max_length=14, blank=True, null=True)
#     recipe = models.CharField(max_length=50, blank=True, null=True)
#     recipe_id = models.CharField(max_length=10, blank=True, null=True)
#     recipe_ver = models.IntegerField(blank=True, null=True)
#     starttime = models.CharField(max_length=19, blank=True, null=True)
#     stoptime = models.CharField(max_length=19, blank=True, null=True)
#     grouptime = models.CharField(max_length=4, blank=True, null=True)
#     oper = models.CharField(max_length=8, blank=True, null=True)
#     state = models.CharField(max_length=4, blank=True, null=True)
#     setno = models.IntegerField(blank=True, null=True)
#     actno = models.IntegerField(blank=True, null=True)
#     order_by = models.IntegerField(blank=True, null=True)
#     date_time = models.CharField(max_length=10, blank=True, null=True)
#     addtime = models.CharField(max_length=19, blank=True, null=True)
#
#     class Meta:
#         managed = False
#         db_table = 'temp_plan'
#
#
# class 当天计划 (models.Model):
#     id = models.BigAutoField(db_column='ID')  # Field name made lowercase.
#     时间 = models.CharField(max_length=20, blank=True, null=True)
#     配方名 = models.CharField(max_length=30, blank=True, null=True)
#     车次 = models.IntegerField(blank=True, null=True)
#
#     class Meta:
#         managed = False
#         db_table = '当天计划'


#
#
# class Hegelv(models.Model):
#     id = models.BigAutoField(db_column='ID')  # Field name made lowercase.
#     timer = models.DateTimeField(blank=True, null=True)
#     planid = models.CharField(max_length=20, blank=True, null=True)
#     recipe = models.CharField(max_length=20, blank=True, null=True)
#     qualified = models.CharField(max_length=20, blank=True, null=True)
#
#     class Meta:
#         managed = False
#         db_table = 'hegelv'
#
#
#
#
# class OrderPlan(models.Model):
#     id = models.BigIntegerField(db_column='ID')  # Field name made lowercase.
#     planid = models.CharField(max_length=14, blank=True, null=True)
#     recipe = models.CharField(max_length=50, blank=True, null=True)
#
#     class Meta:
#         managed = False
#         db_table = 'order_plan'

# class Record(models.Model):
#     id = models.BigAutoField(db_column='ID')  # Field name made lowercase.
#     time = models.DateTimeField(blank=True, null=True)
#     oper = models.CharField(max_length=10, blank=True, null=True)
#     record = models.CharField(max_length=50, blank=True, null=True)
#     type = models.CharField(max_length=4, blank=True, null=True)
#
#     class Meta:
#         managed = False
#         db_table = 'record'
#
#
# class RecordBeiliao(models.Model):
#     序号 = models.BigAutoField()
#     物料名 = models.CharField(max_length=20, blank=True, null=True)
#     重量 = models.FloatField(blank=True, null=True)
#
#     class Meta:
#         managed = False
#         db_table = 'record_beiliao'
#
#
# class RecordMaterial(models.Model):
#     id = models.BigIntegerField(db_column='ID', blank=True, null=True)  # Field name made lowercase.
#     time = models.DateTimeField(blank=True, null=True)
#     name = models.CharField(max_length=20, blank=True, null=True)
#     code = models.CharField(max_length=20, blank=True, null=True)
#     oper = models.CharField(max_length=10, blank=True, null=True)
#
#     class Meta:
#         managed = False
#         db_table = 'record_material'
#
#
# class RecordTable(models.Model):
#     id = models.BigAutoField(db_column='ID')  # Field name made lowercase.
#     name = models.CharField(max_length=50, blank=True, null=True)
#     code = models.CharField(max_length=50, blank=True, null=True)
#     time = models.CharField(max_length=19, blank=True, null=True)
#     user = models.CharField(max_length=10, blank=True, null=True)
#     remark = models.CharField(max_length=10, blank=True, null=True)
#
#     class Meta:
#         managed = False
#         db_table = 'record_table'
