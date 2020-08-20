
from django.db import models
from basics.models import GlobalCode, Equip
from system.models import AbstractEntity, User


class Material(AbstractEntity):
    """原材料信息"""
    material_no = models.CharField(max_length=64, help_text='原材料编码', verbose_name='原材料编码')
    material_name = models.CharField(max_length=64, help_text='原材料名称', verbose_name='原材料名称')
    for_short = models.CharField(max_length=64, help_text='原材料简称', verbose_name='原材料简称', blank=True, null=True)
    material_type = models.ForeignKey(GlobalCode, help_text='原材料类别', verbose_name='原材料类别',
                                      on_delete=models.DO_NOTHING, related_name='mt_materials')
    package_unit = models.ForeignKey(GlobalCode, help_text='包装单位', verbose_name='包装单位',
                                     on_delete=models.DO_NOTHING, related_name='pu_materials', blank=True, null=True)
    used_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用')

    def __str__(self):
        return self.material_name

    class Meta:
        db_table = 'material'
        verbose_name_plural = verbose_name = '原材料'


class MaterialAttribute(AbstractEntity):
    """原材料属性"""
    material = models.ForeignKey(Material, help_text='原材料', verbose_name='原材料', on_delete=models.DO_NOTHING)
    safety_inventory = models.IntegerField(help_text='安全库存标准', verbose_name='安全库存标准')

    class Meta:
        db_table = 'material_attribute'
        verbose_name_plural = verbose_name = '原材料属性'


class MaterialSupplier(AbstractEntity):
    """原材料供应商"""
    material = models.ForeignKey(Material, help_text='原材料', verbose_name='原材料', on_delete=models.DO_NOTHING)
    supplier_no = models.IntegerField(help_text='供应商编码', verbose_name='供应商编码')

    class Meta:
        db_table = 'material_supplier'
        verbose_name_plural = verbose_name = '原材料供应商'


class ProductInfo(AbstractEntity):
    """胶料工艺信息"""
    product_no = models.CharField(max_length=64, help_text='胶料编码', verbose_name='胶料编码')
    product_name = models.CharField(max_length=64, help_text='胶料名称', verbose_name='胶料名称')

    def __str__(self):
        return self.product_name

    class Meta:
        db_table = 'product_info'
        verbose_name_plural = verbose_name = '胶料代码'


class ProductBatching(AbstractEntity):
    """胶料配料标准"""
    USE_TYPE_CHOICE = (
        (1, '编辑'),
        (2, '提交'),
        (3, '校对'),
        (4, '启用'),
        (5, '驳回'),
        (6, '废弃')
    )
    factory = models.ForeignKey(GlobalCode, help_text='工厂', verbose_name='工厂',
                                on_delete=models.DO_NOTHING, related_name='f_batching')
    site = models.ForeignKey(GlobalCode, help_text='SITE', verbose_name='SITE',
                             on_delete=models.DO_NOTHING, related_name='s_batching')
    product_info = models.ForeignKey(ProductInfo, help_text='胶料工艺信息', on_delete=models.DO_NOTHING)
    precept = models.CharField(max_length=64, help_text='方案', verbose_name='方案', blank=True, null=True)
    stage_product_batch_no = models.CharField(max_length=63, help_text='胶料配方编码')
    dev_type = models.ForeignKey(GlobalCode, help_text='机型', on_delete=models.DO_NOTHING, blank=True, null=True)
    stage = models.ForeignKey(GlobalCode, help_text='段次', verbose_name='段次',
                              on_delete=models.DO_NOTHING, related_name='stage_batches')
    versions = models.CharField(max_length=64, help_text='版本', verbose_name='版本')
    used_type = models.PositiveSmallIntegerField(help_text='使用状态', choices=USE_TYPE_CHOICE, default=1)
    batching_weight = models.DecimalField(verbose_name='配料重量', help_text='配料重量',
                                          decimal_places=3, max_digits=8, default=0)
    manual_material_weight = models.DecimalField(verbose_name='手动小料重量', help_text='手动小料重量',
                                                 decimal_places=3, max_digits=8, blank=True, null=True)
    volume = models.DecimalField(verbose_name='配料体积', help_text='配料体积', decimal_places=2, max_digits=8,
                                 blank=True, null=True)
    used_time = models.DateTimeField(help_text='发行时间', verbose_name='发行时间', blank=True, null=True)
    production_time_interval = models.DecimalField(help_text='炼胶时间(分)', blank=True, null=True,
                                                   decimal_places=2, max_digits=8)
    equip_no = models.CharField(max_length=64, help_text='机台编号', blank=True, null=True)

    def __str__(self):
        return self.stage_product_batch_no

    class Meta:
        db_table = 'product_batching'
        verbose_name_plural = verbose_name = '胶料配料标准'


class ProductBatchingDetail(AbstractEntity):
    product_batching = models.ForeignKey(ProductBatching, help_text='配料标准', on_delete=models.DO_NOTHING,
                                         related_name='batching_details')
    sn = models.PositiveIntegerField(verbose_name='序号', help_text='序号')
    material = models.ForeignKey(Material, verbose_name='原材料', help_text='原材料', on_delete=models.DO_NOTHING)
    actual_weight = models.DecimalField(verbose_name='重量', help_text='重量', decimal_places=3, max_digits=8)
    error_range = models.DecimalField(help_text='误差值范围', decimal_places=3, max_digits=8, default=0)

    class Meta:
        db_table = 'product_batching_detail'
        verbose_name_plural = verbose_name = '胶料配料标准详情'


class ProductProcess(AbstractEntity):
    """胶料配方步序"""
    equip = models.ForeignKey(Equip, help_text='机台id', on_delete=models.DO_NOTHING)
    product_batching = models.ForeignKey(ProductBatching, help_text='配料标准', on_delete=models.DO_NOTHING)
    equip_code = models.PositiveIntegerField(help_text='锁定/解除', blank=True, null=True)
    reuse_time = models.PositiveIntegerField(help_text='回收时间', blank=True, null=True)
    mini_time = models.PositiveIntegerField(help_text='超温最短时间', blank=True, null=True)
    max_time = models.PositiveIntegerField(help_text='超温最长时间', blank=True, null=True)
    mini_temp = models.DecimalField(help_text='进胶最低温度', decimal_places=2, max_digits=8, blank=True, null=True)
    max_temp = models.DecimalField(help_text='进胶最高温度', decimal_places=2, max_digits=8, blank=True, null=True)
    over_temp = models.DecimalField(help_text='超温温度', decimal_places=2, max_digits=8, blank=True, null=True)
    reuse_flag = models.BooleanField(help_text='是否回收', default=False)
    zz_temp = models.DecimalField(help_text='转子水温', decimal_places=2, max_digits=8, blank=True, null=True)
    xlm_temp = models.DecimalField(help_text='卸料门水温', decimal_places=2, max_digits=8, blank=True, null=True)
    cb_temp = models.DecimalField(help_text='侧壁水温', decimal_places=2, max_digits=8, blank=True, null=True)
    temp_use_flag = models.BooleanField(help_text='三区水温弃用/启用', default=True)
    used_flag = models.BooleanField(help_text='配方弃用/启用', default=True)

    class Meta:
        db_table = 'product_process'
        verbose_name_plural = verbose_name = '胶料配料标准步序'


class BaseCondition(AbstractEntity):
    code = models.CharField(max_length=16, help_text='代码')
    condition = models.CharField(max_length=16, help_text='条件名称')

    class Meta:
        db_table = 'base_condition'
        verbose_name_plural = verbose_name = '基本条件'


class BaseAction(AbstractEntity):
    code = models.CharField(max_length=16, help_text='代码')
    action = models.CharField(max_length=16, help_text='条件名称')

    class Meta:
        db_table = 'base_action'
        verbose_name_plural = verbose_name = '基本动作'


class ProductProcessDetail(AbstractEntity):
    product_process = models.ForeignKey(ProductProcess, help_text='步序id', on_delete=models.DO_NOTHING,
                                        related_name='process_details')
    sn = models.CharField(max_length=64, help_text='序号')
    temperature = models.DecimalField(help_text='温度', blank=True, null=True, decimal_places=2, max_digits=8)
    rpm = models.DecimalField(help_text='转速', blank=True, null=True, decimal_places=2, max_digits=8)
    energy = models.DecimalField(help_text='能量', blank=True, null=True, decimal_places=2, max_digits=8)
    power = models.DecimalField(help_text='功率', blank=True, null=True, decimal_places=2, max_digits=8)
    pressure = models.DecimalField(help_text='压力', blank=True, null=True, decimal_places=2, max_digits=8)
    condition = models.ForeignKey(BaseCondition, help_text='条件id', blank=True, null=True, on_delete=models.DO_NOTHING)
    time = models.DecimalField(help_text='时间(分钟)', decimal_places=2, max_digits=8,
                               blank=True, null=True)
    action = models.ForeignKey(BaseAction, help_text='基本动作id', blank=True, null=True, on_delete=models.DO_NOTHING)
    time_unit = models.CharField(max_length=4, help_text='时间单位', blank=True, null=True)

    class Meta:
        db_table = 'product_process_detail'
        verbose_name_plural = verbose_name = '胶料配料标准步序详情'
