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
                                  related_name='user_prods', blank=True, null=True)
    used_time = models.DateTimeField(help_text='应用时间', verbose_name='应用时间', blank=True, null=True)
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
