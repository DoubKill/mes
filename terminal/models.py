from django.db import models

from basics.models import Equip, GlobalCode
from production.models import LocationPoint
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
    location = models.ForeignKey(LocationPoint, help_text='位置点', on_delete=models.CASCADE)
    terminal = models.ForeignKey(Terminal, help_text='终端', on_delete=models.CASCADE)
    equip = models.ForeignKey(Equip, help_text='设备', on_delete=models.CASCADE)

    def __str__(self):
        return '{}-{}-{}'.format(self.terminal, self.location, self.equip)

    class Meta:
        db_table = 'terminal_location_binding'
        verbose_name_plural = verbose_name = '终端位置点绑定'


class BatchChargeLog(AbstractEntity):
    STATUS_CHOICE = (
        (1, '正常'),
        (2, '异常')
    )
    equip_no = models.CharField(max_length=64, help_text='机台编号')
    plan_classes_uid = models.CharField(max_length=64, help_text='班次计划唯一码')
    trains = models.CharField(max_length=64, help_text='车次')
    product_no = models.CharField(max_length=64, help_text='胶料名称')
    material_name = models.CharField(max_length=64, help_text='原材料名称')
    material_no = models.CharField(max_length=64, help_text='原材料编码')
    plan_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='计划重量')
    actual_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='时实际重量')
    bra_code = models.CharField(max_length=64, help_text='条形码')
    production_factory_date = models.DateField(max_length=64, help_text='工厂时间')
    production_classes = models.CharField(max_length=64, help_text='生产班次')
    production_group = models.CharField(max_length=64, help_text='生产班组')
    status = models.PositiveIntegerField(help_text='状态', choices=STATUS_CHOICE, default=1)
    # batch_time = models.DateTimeField(max_length=64, help_text='投入时间')
    batch_classes = models.CharField(max_length=64, help_text='投入班次')
    batch_group = models.CharField(max_length=64, help_text='投入班组')

    class Meta:
        db_table = 'batch_charge_log'
        verbose_name_plural = verbose_name = '投料履历'


class WeightPackageLog(AbstractEntity):
    # STATUS_CHOICE = (
    #     (1, '投料'),
    #     (2, '撤销')
    # )
    equip_no = models.CharField(max_length=64, help_text='称量设备编号')
    plan_batching_uid = models.CharField(max_length=64, help_text='小料称量计划号')
    product_no = models.CharField(max_length=64, help_text='胶料名称')
    material_name = models.CharField(max_length=64, help_text='物料打包名称')
    material_no = models.CharField(max_length=64, help_text='物料打包编号')
    plan_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='计划重量', default=0)
    actual_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='实际重量', default=0)
    bra_code = models.CharField(max_length=64, help_text='条形码')
    production_factory_date = models.DateField(max_length=64, help_text='工厂时间')
    production_classes = models.CharField(max_length=64, help_text='生产班次')
    production_group = models.CharField(max_length=64, help_text='生产班组')
    # status = models.PositiveIntegerField(help_text='状态', choices=STATUS_CHOICE)
    # batch_time = models.DateTimeField(max_length=64, help_text='打包时间')
    batch_classes = models.CharField(max_length=64, help_text='投入班次')
    batch_group = models.CharField(max_length=64, help_text='投入班组')
    location_no = models.CharField(max_length=64, help_text='产线')
    dev_type = models.CharField(max_length=64, help_text='机型名称')
    begin_trains = models.IntegerField(help_text='开始包')
    end_trains = models.IntegerField(help_text='结束包')
    times = models.IntegerField(help_text='打印次数', default=1)
    quantity = models.IntegerField(default=1, help_text='包数')

    class Meta:
        db_table = 'weight_package_log'
        verbose_name_plural = verbose_name = '称量打包履历'


class WeightBatchingLog(AbstractEntity):
    # STATUS_CHOICE = (
    #     (1, '投料'),
    #     (2, '撤销')
    # )
    equip_no = models.CharField(max_length=64, help_text='称量设备编号')
    plan_batching_uid = models.CharField(max_length=64, help_text='小料称量计划号')
    trains = models.IntegerField(help_text='车次')
    product_no = models.CharField(max_length=64, help_text='胶料名称')
    material_name = models.CharField(max_length=64, help_text='原材料名称')
    material_no = models.CharField(max_length=64, help_text='原材料编码')
    plan_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='计划重量')
    actual_weight = models.DecimalField(decimal_places=2, max_digits=8, help_text='实际重量')
    bra_code = models.CharField(max_length=64, help_text='条形码')
    production_factory_date = models.DateField(max_length=64, help_text='工厂时间')
    production_classes = models.CharField(max_length=64, help_text='生产班次')
    production_group = models.CharField(max_length=64, help_text='生产班组')
    # status = models.PositiveIntegerField(help_text='状态', choices=STATUS_CHOICE)
    # batch_time = models.DateTimeField(max_length=64, help_text='投入时间')
    batch_classes = models.CharField(max_length=64, help_text='投入班次')
    batch_group = models.CharField(max_length=64, help_text='投入班组')
    tank_no = models.CharField(max_length=64, help_text='投入罐号')
    location_no = models.CharField(max_length=64, help_text='产线')
    dev_type = models.CharField(max_length=64, help_text='机型名称')
    quantity = models.IntegerField(default=1, help_text='包数')

    class Meta:
        db_table = 'weight_batch_log'
        verbose_name_plural = verbose_name = '称量投料履历'


class WeightTankStatus(AbstractEntity):
    STATUS_CHOICE = (
        (1, '低位'),
        (2, '高位')
    )
    # tank_type = models.PositiveIntegerField(help_text='物料罐类型，1：炭黑罐  2：油料罐', choices=TANK_TYPE_CHOICE)
    tank_name = models.CharField(max_length=64, help_text='物料罐名称')
    tank_no = models.CharField(max_length=64, help_text='物料罐编号')
    material_name = models.CharField(max_length=64, help_text='原材料名称')
    material_no = models.CharField(max_length=64, help_text='原材料编码')
    use_flag = models.BooleanField(help_text='使用与否', default=True)
    status = models.PositiveIntegerField(help_text='状态，1：低位  2：高位', choices=STATUS_CHOICE)
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

#
# class MaterialSupplierCollect(AbstractEntity):
#     bar_code = models.CharField(max_length=64, help_text='条形码')
#     material_name = models.CharField(max_length=64, help_text='原材料名称')
#     material_no = models.CharField(max_length=64, help_text='原材料编码')
#     batch_no = models.CharField(max_length=64, help_text='批次号', blank=True, null=True)
#
#     class Meta:
#         db_table = 'material_supplier_collect'
#         verbose_name_plural = verbose_name = '物料条形码管理'