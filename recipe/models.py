
from django.db import models
from basics.models import GlobalCode, Equip, EquipCategoryAttribute
from system.models import AbstractEntity, User


class Material(AbstractEntity):
    """原材料信息"""
    material_no = models.CharField(max_length=64, help_text='原材料编码', verbose_name='原材料编码', unique=True)
    material_name = models.CharField(max_length=64, help_text='原材料名称', verbose_name='原材料名称')
    for_short = models.CharField(max_length=64, help_text='原材料简称', verbose_name='原材料简称', blank=True, null=True)
    material_type = models.ForeignKey(GlobalCode, help_text='原材料类别', verbose_name='原材料类别',
                                      on_delete=models.DO_NOTHING, related_name='mt_materials')
    package_unit = models.ForeignKey(GlobalCode, help_text='包装单位', verbose_name='包装单位',
                                     on_delete=models.DO_NOTHING, related_name='pu_materials', blank=True, null=True)
    use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)

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
    supplier_no = models.IntegerField(help_text='供应商编码', verbose_name='供应商编码', unique=True)

    class Meta:
        db_table = 'material_supplier'
        verbose_name_plural = verbose_name = '原材料供应商'


class ProductInfo(AbstractEntity):
    """胶料工艺信息"""
    product_no = models.CharField(max_length=64, help_text='胶料编码', verbose_name='胶料编码', unique=True)
    product_name = models.CharField(max_length=64, help_text='胶料名称', verbose_name='胶料名称')

    def __str__(self):
        return self.product_name

    class Meta:
        db_table = 'product_info'
        verbose_name_plural = verbose_name = '胶料代码'


class ProductRecipe(AbstractEntity):
    """胶料段次配方标准"""
    product_recipe_no = models.CharField(max_length=64, help_text='胶料标准编号', verbose_name='胶料标准编号')
    sn = models.PositiveIntegerField(verbose_name='序号', help_text='序号')
    product_info = models.ForeignKey(ProductInfo, verbose_name='胶料工艺', help_text='胶料工艺',
                                     on_delete=models.DO_NOTHING)
    material = models.ForeignKey(Material, verbose_name='原材料', help_text='原材料',
                                 on_delete=models.DO_NOTHING, blank=True, null=True)
    stage = models.ForeignKey(GlobalCode, help_text='段次', verbose_name='段次',
                              on_delete=models.DO_NOTHING)
    ratio = models.DecimalField(verbose_name='配比', help_text='配比',
                                decimal_places=2, max_digits=8, blank=True, null=True)

    def __str__(self):
        return self.product_recipe_no

    class Meta:
        db_table = 'product_recipe'
        verbose_name_plural = verbose_name = '胶料段次配方标准'


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
    dev_type = models.ForeignKey(EquipCategoryAttribute, help_text='机型', on_delete=models.DO_NOTHING, blank=True,
                                 null=True)
    stage = models.ForeignKey(GlobalCode, help_text='段次', verbose_name='段次',
                              on_delete=models.DO_NOTHING, related_name='stage_batches')
    versions = models.CharField(max_length=64, help_text='版本', verbose_name='版本')
    used_type = models.PositiveSmallIntegerField(help_text='使用状态', choices=USE_TYPE_CHOICE, default=1)
    batching_weight = models.DecimalField(verbose_name='配料重量', help_text='配料重量',
                                          decimal_places=3, max_digits=8, default=0)
    manual_material_weight = models.DecimalField(verbose_name='手动小料重量', help_text='手动小料重量',
                                                 decimal_places=3, max_digits=8, default=0)
    auto_material_weight = models.DecimalField(verbose_name='自动小料重量', help_text='自动小料重量',
                                               decimal_places=3, max_digits=8, default=0)
    volume = models.DecimalField(verbose_name='配料体积', help_text='配料体积', decimal_places=2, max_digits=8,
                                 blank=True, null=True)
    used_user = models.ForeignKey(User, help_text='启用人', blank=True, null=True,
                                  on_delete=models.DO_NOTHING, related_name='used_batching')
    used_time = models.DateTimeField(help_text='启用时间', verbose_name='启用时间', blank=True, null=True)
    obsolete_user = models.ForeignKey(User, help_text='弃用人', blank=True, null=True,
                                      on_delete=models.DO_NOTHING, related_name='obsolete_batching')
    obsolete_time = models.DateTimeField(help_text='弃用时间', verbose_name='弃用时间', blank=True, null=True)
    production_time_interval = models.DecimalField(help_text='炼胶时间(分)', blank=True, null=True,
                                                   decimal_places=2, max_digits=8)
    equip = models.ForeignKey(Equip, help_text='设备', blank=True, null=True, on_delete=models.DO_NOTHING)

    def __str__(self):
        return self.stage_product_batch_no

    class Meta:
        db_table = 'product_batching'
        verbose_name_plural = verbose_name = '胶料配料标准'


class ProductBatchingDetail(AbstractEntity):
    AUTO_FLAG = (
        (0, None),
        (1, '自动'),
        (2, '手动'),
    )
    product_batching = models.ForeignKey(ProductBatching, help_text='配料标准', on_delete=models.DO_NOTHING,
                                         related_name='batching_details')
    sn = models.PositiveIntegerField(verbose_name='序号', help_text='序号')
    material = models.ForeignKey(Material, verbose_name='原材料', help_text='原材料', on_delete=models.DO_NOTHING)
    actual_weight = models.DecimalField(verbose_name='重量', help_text='重量', decimal_places=3, max_digits=8)
    standard_error = models.DecimalField(help_text='误差值范围', decimal_places=3, max_digits=8, default=0)
    auto_flag = models.PositiveSmallIntegerField(help_text='手动/自动', choices=AUTO_FLAG)

    class Meta:
        db_table = 'product_batching_detail'
        verbose_name_plural = verbose_name = '胶料配料标准详情'