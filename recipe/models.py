from django.db import models

# Create your models here.
from basics.models import GlobalCode
from system.models import AbstractEntity


class Material(AbstractEntity):
    """原材料信息"""
    material_no = models.CharField(max_length=64, help_text='原材料编码', verbose_name='原材料编码')
    material_name = models.CharField(max_length=64, help_text='原材料名称', verbose_name='原材料名称')
    for_short = models.CharField(max_length=64, help_text='原材料简称', verbose_name='原材料简称', blank=True, null=True)
    material_type = models.ForeignKey(GlobalCode, help_text='原材料类别', verbose_name='原材料类别',
                                      on_delete=models.DO_NOTHING, related_name='mt_materials')
    density = models.DecimalField(verbose_name='比重', help_text='比重', decimal_places=2, max_digits=8)
    packet_unit = models.ForeignKey(GlobalCode, help_text='包装单位', verbose_name='包装单位',
                                    on_delete=models.DO_NOTHING, related_name='pu_materials')
    used_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用')

    def __str__(self):
        return self.material_name

    class Meta:
        db_table = 'material'
        verbose_name_plural = verbose_name = '原材料'