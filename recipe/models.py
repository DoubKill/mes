
from django.db import models

# Create your models here.
from basics.models import GlobalCode
from system.models import AbstractEntity, User


class Material(AbstractEntity):
    """原材料信息"""
    material_no = models.CharField(max_length=64, help_text='原材料编码', verbose_name='原材料编码')
    material_name = models.CharField(max_length=64, help_text='原材料名称', verbose_name='原材料名称')
    for_short = models.CharField(max_length=64, help_text='原材料简称', verbose_name='原材料简称', blank=True, null=True)
    material_type = models.ForeignKey(GlobalCode, help_text='原材料类别', verbose_name='原材料类别',
                                      on_delete=models.DO_NOTHING, related_name='mt_materials')
    density = models.DecimalField(verbose_name='比重', help_text='比重', decimal_places=2, max_digits=8)
    package_unit = models.ForeignKey(GlobalCode, help_text='包装单位', verbose_name='包装单位',
                                     on_delete=models.DO_NOTHING, related_name='pu_materials')
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
    versions = models.CharField(max_length=64, help_text='版本', verbose_name='版本')
    precept = models.CharField(max_length=64, help_text='方案', verbose_name='方案')
    factory = models.ForeignKey(GlobalCode, help_text='产地', verbose_name='产地',
                                on_delete=models.DO_NOTHING, related_name='f_prods')
    used_type = models.ForeignKey(GlobalCode, help_text='使用状态', verbose_name='使用状态',
                                  on_delete=models.DO_NOTHING, related_name='ut_prods')
    recipe_weight = models.DecimalField(verbose_name='重量', help_text='重量', decimal_places=2, max_digits=8)
    used_user = models.ForeignKey(User, help_text='应用人', verbose_name='应用人', on_delete=models.DO_NOTHING,
                                  related_name='used_prods', blank=True, null=True)
    used_time = models.DateTimeField(help_text='应用时间', verbose_name='应用时间', blank=True, null=True)
    obsolete_user = models.ForeignKey(User, help_text='应用人', verbose_name='应用人', on_delete=models.DO_NOTHING,
                                      related_name='obsolete_prods', blank=True, null=True)
    obsolete_time = models.DateTimeField(help_text='废弃时间', verbose_name='废弃时间', blank=True, null=True)

    def __str__(self):
        return self.product_name

    class Meta:
        db_table = 'product_info'
        verbose_name_plural = verbose_name = '胶料工艺'


class ProductRecipe(AbstractEntity):
    """胶料段次配方标准"""
    product_recipe_no = models.CharField(max_length=64, help_text='胶料标准编号', verbose_name='胶料标准编号')
    num = models.PositiveIntegerField(verbose_name='序号', help_text='序号')
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
    product_info = models.ForeignKey(ProductInfo, help_text='胶料工艺信息', on_delete=models.DO_NOTHING)
    stage_product_batch_no = models.CharField(max_length=63, help_text='段次胶料标准编码')
    stage = models.ForeignKey(GlobalCode, help_text='段次', verbose_name='段次',
                              on_delete=models.DO_NOTHING, related_name='stage_masters')
    dev_type = models.ForeignKey(GlobalCode, help_text='机型', on_delete=models.DO_NOTHING)
    batching_weight = models.DecimalField(verbose_name='配料重量', help_text='配料重量', decimal_places=2, max_digits=8)
    manual_material_weight = models.DecimalField(verbose_name='手动小料重量', help_text='手动小料重量',
                                                 decimal_places=2, max_digits=8, blank=True, null=True)
    volume = models.DecimalField(verbose_name='配料体积', help_text='配料体积', decimal_places=2, max_digits=8)
    batching_time_interval = models.TimeField(help_text='配料时间(秒)', blank=True, null=True)
    rm_flag = models.BooleanField(help_text='返炼与否', default=False)
    rm_time_interval = models.TimeField(help_text='返炼时间', blank=True, null=True)
    batching_proportion = models.DecimalField(verbose_name='配料比重', help_text='手动小料重量', decimal_places=2, max_digits=8)
    production_time_interval = models.TimeField(help_text='炼胶时间(秒)', blank=True, null=True)

    def __str__(self):
        return self.stage_product_batch_no

    class Meta:
        db_table = 'product_batching'
        verbose_name_plural = verbose_name = '胶料配料标准'


class ProductBatchingDetail(AbstractEntity):
    product_batching = models.ForeignKey(ProductBatching, help_text='配料标准', on_delete=models.DO_NOTHING,
                                         related_name='batching_details')
    num = models.PositiveIntegerField(verbose_name='序号', help_text='序号')
    material = models.ForeignKey(Material, verbose_name='原材料', help_text='原材料',
                                 on_delete=models.DO_NOTHING, blank=True, null=True)
    previous_product_batching = models.ForeignKey(ProductBatching, verbose_name='上段位配料标准', help_text='上段位配料标准',
                                                  on_delete=models.DO_NOTHING, blank=True, null=True)
    ratio = models.DecimalField(verbose_name='配比', help_text='配比',
                                decimal_places=2, max_digits=8, blank=True, null=True)
    density = models.DecimalField(verbose_name='比重', help_text='比重',
                                  decimal_places=2, max_digits=8, blank=True, null=True)
    ratio_weight = models.DecimalField(verbose_name='配比体积', help_text='比重',
                                       decimal_places=2, max_digits=8, blank=True, null=True)
    standard_volume = models.DecimalField(verbose_name='计算体积', help_text='计算体积',
                                          decimal_places=2, max_digits=8, blank=True, null=True)
    actual_volume = models.DecimalField(verbose_name='实际体积', help_text='实际体积',
                                        decimal_places=2, max_digits=8, blank=True, null=True)
    standard_weight = models.DecimalField(verbose_name='标准重量', help_text='标准重量',
                                          decimal_places=2, max_digits=8, blank=True, null=True)
    actual_weight = models.DecimalField(verbose_name='实际重量', help_text='实际重量',
                                        decimal_places=2, max_digits=8, blank=True, null=True)
    time_interval = models.TimeField(help_text='时间间隔', blank=True, null=True)
    temperature = models.DecimalField(verbose_name='温度', help_text='温度',
                                      decimal_places=2, max_digits=8, blank=True, null=True)
    rpm = models.DecimalField(verbose_name='转速', help_text='转速',
                              decimal_places=2, max_digits=8, blank=True, null=True)

    class Meta:
        db_table = 'product_batching_detail'
        verbose_name_plural = verbose_name = '胶料配料标准'


class ProductMaster(AbstractEntity):
    product_no = models.CharField(max_length=64, help_text='胶料标准编号', verbose_name='胶料标准编号')
    stage = models.ForeignKey(GlobalCode, help_text='段次', verbose_name='段次',
                              on_delete=models.DO_NOTHING, related_name='s_masters')
    dev_type = models.ForeignKey(GlobalCode, help_text='机型', on_delete=models.DO_NOTHING,
                                 related_name='dev_masters')
    factory = models.ForeignKey(GlobalCode, help_text='产地', verbose_name='产地',
                                on_delete=models.DO_NOTHING, related_name='f_masters')
    versions = models.CharField(max_length=64, help_text='版本', verbose_name='版本')
    product_name = models.CharField(max_length=64, help_text='胶料名称', verbose_name='胶料名称')
    batching_weight = models.DecimalField(verbose_name='配料重量', help_text='配料重量', decimal_places=2, max_digits=8)
    batching_time_interval = models.TimeField(help_text='配料时间', blank=True, null=True)
    used_type = models.ForeignKey(GlobalCode, help_text='使用状态', verbose_name='使用状态',
                                  on_delete=models.DO_NOTHING, related_name='ut_masters')
    used_user = models.ForeignKey(User, help_text='应用人', verbose_name='应用人', on_delete=models.DO_NOTHING,
                                  related_name='u_masters', blank=True, null=True)
    used_time = models.DateTimeField(help_text='应用时间', verbose_name='应用时间', blank=True, null=True)
    obsolete_time = models.DateTimeField(help_text='废弃时间', verbose_name='废弃时间', blank=True, null=True)
    product_batching = models.ForeignKey(ProductBatching, help_text='配料标准', on_delete=models.DO_NOTHING)

    class Meta:
        db_table = 'product_master'
        verbose_name_plural = verbose_name = '胶料主信息'


class ProductProcess(AbstractEntity):
    product_batching = models.ForeignKey(ProductBatching, help_text='配料标准', on_delete=models.DO_NOTHING)
    detail = models.TextField(help_text='步序细节')

    class Meta:
        db_table = 'product_process'
        verbose_name_plural = verbose_name = '胶料配料标准'