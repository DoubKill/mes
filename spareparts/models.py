from django.db import models

from basics.models import GlobalCode, Location
from inventory.models import WarehouseInfo
from recipe.models import Material
from system.models import AbstractEntity


# Create your models here.

class SpareType(AbstractEntity):
    """备品备件类型"""
    no = models.CharField(help_text='类型编码', max_length=64, unique=True)
    name = models.CharField(help_text='类型名称', max_length=64, unique=True)

    class Meta:
        db_table = 'spare_type'
        verbose_name_plural = verbose_name = '备品备件类型'


class Spare(AbstractEntity):
    """备品备件基本信息"""
    no = models.CharField(help_text='备品备件编码', max_length=64, unique=True)
    name = models.CharField(help_text='备品备件名称', max_length=64, unique=True)
    type = models.ForeignKey(SpareType, help_text='备品备件类别id', on_delete=models.CASCADE, related_name='s_spare_type',
                             blank=True, null=True)
    unit = models.CharField(help_text='单位', max_length=64)
    upper = models.IntegerField(help_text='库存上限')
    lower = models.IntegerField(help_text='库存下限')
    cost = models.DecimalField(max_digits=15, decimal_places=3, db_column='单位价')

    class Meta:
        db_table = 'spare'
        verbose_name_plural = verbose_name = '备品备件基本信息'


class SpareLocation(AbstractEntity):
    """备品备件位置点"""
    no = models.CharField(help_text='编码', max_length=64, unique=True)
    name = models.CharField(help_text='名称', max_length=64, unique=True)
    desc = models.CharField(help_text='备注', max_length=64, null=True)
    used_flag = models.IntegerField(help_text='是否启动', default=1)
    type = models.ForeignKey(GlobalCode, help_text='类型id',
                             on_delete=models.CASCADE, related_name='spare_location_gc', blank=True, null=True)
    image_url = models.CharField(help_text='位置相关照片', max_length=128, null=True)

    # image_url=models.ImageField(help_text='位置相关照片') 这个字段是图片 个人觉得用这个字段比较合理 但是设计是上面一个 而且页面功能暂时也不做这个，所以就先按照上面的来
    class Meta:
        db_table = 'spare_location'
        verbose_name_plural = verbose_name = '备品备件位置点'


class SpareLocationBinding(AbstractEntity):
    """位置点和物料绑定"""
    location = models.ForeignKey(SpareLocation, help_text='位置点id', on_delete=models.CASCADE,
                                 related_name='slb_location',
                                 blank=True, null=True)
    spare = models.ForeignKey(Spare, help_text='备品备件id', on_delete=models.CASCADE, related_name='slb_spare',
                              blank=True, null=True)

    class Meta:
        db_table = 'spare_location_binding'
        verbose_name_plural = verbose_name = '位置点和物料绑定'


class SpareInventory(AbstractEntity):
    """备品备件库"""
    spare = models.ForeignKey(Spare, help_text='备品备件id', on_delete=models.CASCADE, related_name='si_spare',
                              blank=True, null=True)
    pallet_no = models.IntegerField(help_text='容器id(托盘号)', null=True)
    site = models.ForeignKey(GlobalCode, help_text='产地', on_delete=models.CASCADE, related_name='si_gc', blank=True,
                             null=True)
    qty = models.IntegerField(help_text='库存数')
    unit = models.CharField(help_text='单位', max_length=64, default='件')
    quality_status = models.CharField(help_text='品质状态', max_length=64, default='合格')
    location = models.ForeignKey(SpareLocation, help_text='库位id',
                                 on_delete=models.CASCADE, related_name='si_spare_location', blank=True, null=True)
    warehouse_info = models.ForeignKey(WarehouseInfo, on_delete=models.CASCADE, related_name="si_warehouse_info",
                                       blank=True, null=True, help_text='仓库')
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
    CHOICE1 = (
        ('出库', "出库"),
        ('入库', "入库"),
        ('数量变更', "数量变更"),
    )
    warehouse_no = models.CharField(help_text='仓库编号', max_length=64)
    warehouse_name = models.CharField(help_text='仓库名称', max_length=64)
    pallet_no = models.CharField(help_text='托盘号', max_length=64, null=True)
    location = models.CharField(help_text='货位地址', max_length=64)
    qty = models.IntegerField(help_text='变更数量')
    weight = models.DecimalField(max_digits=15, decimal_places=3, db_column='重量', default=0)
    quality_status = models.CharField(help_text='品质状态', max_length=64)
    spare_no = models.CharField(help_text='备品备件编码', max_length=64)
    spare_name = models.CharField(help_text='备品备件名称', max_length=64)
    spare_type = models.CharField(help_text='备品备件类型', max_length=64)
    fin_time = models.DateField(help_text='完成时间')
    type = models.CharField(help_text='类型', max_length=32, choices=CHOICE1)
    cost = models.DecimalField(max_digits=15, decimal_places=3, db_column='费用', null=True)
    reason = models.CharField(help_text='出库原因/备注', max_length=64, null=True)
    receive_user = models.CharField(help_text='领用人', max_length=64, null=True)
    purpose = models.CharField(help_text='用途', max_length=64, null=True)
    status = models.IntegerField(help_text='状态', choices=CHOICE, default=1)
    src_qty = models.IntegerField(help_text='变更前数量')
    dst_qty = models.IntegerField(help_text='变更后数量')
    unit_count= models.DecimalField(max_digits=15, decimal_places=3, db_column='单价', null=True)

    class Meta:
        db_table = 'spare_inventory_log'
        verbose_name_plural = verbose_name = '出入库履历'
