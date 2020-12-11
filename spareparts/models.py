from django.db import models

from basics.models import GlobalCode, Location
from inventory.models import WarehouseInfo
from recipe.models import Material
from system.models import AbstractEntity


# Create your models here.


class MaterialLocationBinding(AbstractEntity):
    """位置点和物料绑定"""
    location = models.ForeignKey(Location, help_text='位置点id', on_delete=models.CASCADE, related_name='mlb_location',
                                 blank=True, null=True)
    material = models.ForeignKey(Material, help_text='物料id', on_delete=models.CASCADE, related_name='mlb_material',
                                 blank=True, null=True)

    class Meta:
        db_table = 'material_location_binding'
        verbose_name_plural = verbose_name = '位置点和物料绑定'


class SpareInventory(AbstractEntity):
    """备品备件库"""
    material = models.ForeignKey(Material, help_text='物料id', on_delete=models.CASCADE, related_name='si_material',
                                 blank=True, null=True)
    pallet_no = models.IntegerField(help_text='容器id(托盘号)', null=True)
    site = models.ForeignKey(GlobalCode, help_text='产地', on_delete=models.CASCADE, related_name='si_gc', blank=True,
                             null=True)
    qty = models.IntegerField(help_text='库存数')
    unit = models.CharField(help_text='单位', max_length=64, default='件')
    quality_status = models.CharField(help_text='品质状态', max_length=64, default='合格')
    location = models.ForeignKey(Location, help_text='库位id',
                                 on_delete=models.CASCADE, related_name='si_location', blank=True, null=True)
    warehouse_info = models.ForeignKey(WarehouseInfo, on_delete=models.CASCADE, related_name="si_warehouse_info",
                                       blank=True, null=True, help_text='仓库')
    unit_count = models.DecimalField(max_digits=15, decimal_places=3, db_column='单位价', null=True)
    total_count = models.DecimalField(max_digits=15, decimal_places=3, db_column='总价', null=True)

    class Meta:
        db_table = 'spare_inventory'
        verbose_name_plural = verbose_name = '备品备件库'


class SpareInventoryLog(AbstractEntity):
    """出入库履历"""
    CHOICE = (
        (1, "完成"),
        (2, "撤销"),
    )
    warehouse_no = models.CharField(help_text='仓库编号', max_length=64)
    warehouse_name = models.CharField(help_text='仓库名称', max_length=64)
    pallet_no = models.CharField(help_text='托盘号', max_length=64, null=True)
    location = models.CharField(help_text='货位地址', max_length=64)
    qty = models.IntegerField(help_text='变更数量')
    weight = models.DecimalField(max_digits=15, decimal_places=3, db_column='重量',default=0)
    quality_status = models.CharField(help_text='品质状态', max_length=64)
    material_no = models.CharField(help_text='物料编码', max_length=64)
    material_name = models.CharField(help_text='物料名称', max_length=64)
    fin_time = models.DateField(help_text='完成时间')
    type = models.CharField(help_text='类型', max_length=8)
    cost = models.DecimalField(max_digits=15, decimal_places=3, db_column='费用', null=True)
    reason = models.CharField(help_text='出库原因', max_length=64, null=True)
    receive_user = models.CharField(help_text='领用人', max_length=64, null=True)
    purpose = models.CharField(help_text='用途', max_length=64, null=True)
    status = models.IntegerField(help_text='状态', choices=CHOICE, default=1)
    src_qty = models.IntegerField(help_text='变更前数量')
    dst_qty = models.IntegerField(help_text='变更后数量')

    class Meta:
        db_table = 'spare_inventory_log'
        verbose_name_plural = verbose_name = '出入库履历'
