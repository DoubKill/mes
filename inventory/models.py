from django.db import models

# Create your models here.
from basics.models import GlobalCode
from recipe.models import Material
from system.models import AbstractEntity, User


class OutOrderFeedBack(models.Model):
    """出库订单反馈"""
    task_id = models.CharField(max_length=64, verbose_name='任务编号', help_text='任务编号',blank=True)
    material_no = models.CharField(max_length=64, verbose_name='物料信息ID', help_text='物料信息ID', blank=True)
    pdm_no = models.CharField(max_length=64, verbose_name='PDM号', help_text='PDM号', blank=True)
    batch_no = models.CharField(max_length=64, verbose_name='批号', help_text='批号', blank=True, null=True)
    lot_no = models.CharField(max_length=64, verbose_name='条码', help_text='条码', blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='重量', help_text='重量', blank=True)
    unit = models.CharField(max_length=64, verbose_name='重量单位', help_text='重量单位', blank=True)
    product_time = models.DateTimeField(verbose_name='生产日期', help_text='生产日期', blank=True)
    expire_time = models.DateTimeField(verbose_name='生产期限', help_text='生产期限', blank=True)
    rfid = models.CharField(max_length=64, verbose_name='托盘RFID', help_text='托盘RFID', blank=True)
    station = models.CharField(max_length=64, verbose_name='工位', help_text='工位', blank=True)
    out_user = models.CharField(max_length=64, verbose_name='出库人', help_text='出库人', blank=True)
    out_type = models.CharField(max_length=64, verbose_name='出库类型', help_text='出库类型', blank=True)

    class Meta:
        db_table = 'out_order_feedback'
        verbose_name_plural = verbose_name = '出库订单反馈'


class WarehouseInfo(models.Model):
    """仓库信息"""
    no = models.CharField(max_length=64, verbose_name='仓库信息', help_text='仓库信息')
    name = models.CharField(max_length=64, verbose_name='仓库名称', help_text='仓库名称')
    ip = models.CharField(max_length=64, verbose_name='仓库ip', help_text='仓库ip')
    address = models.CharField(max_length=64, verbose_name='仓库地址', help_text='仓库地址')

    class Meta:
        db_table = 'ware_house_info'
        verbose_name_plural = verbose_name = '仓库信息'


class WarehouseMaterialType(models.Model):
    """仓库物料类型"""
    warehouse_info = models.ForeignKey(WarehouseInfo, on_delete=models.CASCADE, related_name="warehouse_material_types")
    material_type = models.OneToOneField(GlobalCode, on_delete=models.CASCADE)

    class Meta:
        db_table = 'ware_house_material_type'
        verbose_name_plural = verbose_name = '仓库物料类型'


class InventoryLog(models.Model):
    """出入库履历"""
    warehouse_no = models.CharField(max_length=64, verbose_name='仓库编号', help_text='仓库编号')
    warehouse_name = models.CharField(max_length=64, verbose_name='仓库名称', help_text='仓库名称')
    order_no = models.CharField(max_length=64, verbose_name='订单号', help_text='订单号')
    pallet_no = models.CharField(max_length=64, verbose_name='托盘号', help_text='托盘号')
    location = models.CharField(max_length=64, verbose_name='货位地址',help_text='货位地址')
    qty = models.PositiveIntegerField(verbose_name='数量',help_text='数量', blank=True, null=True)
    wegit = models.DecimalField(verbose_name='重量', help_text='重量', blank=True, null=True, decimal_places=2,max_digits=8)
    material_no = models.CharField(max_length=64, verbose_name='物料编码',help_text='物料编码')
    quality_status = models.CharField(max_length=8, verbose_name='品质状态',help_text='品质状态')
    lot_no = models.CharField(max_length=64, verbose_name='lot_no', help_text='lot_no')
    fin_time = models.DateTimeField(verbose_name='完成时间', help_text='完成时间', auto_now_add=True)
    order_type= models.CharField(max_length=64, verbose_name='订单类型', help_text='订单类型')


    class Meta:
        db_table = 'inventory_log'
        verbose_name_plural = verbose_name = '出入库履历'


class MaterialInventory(models.Model):
    """库存信息|线边库"""
    material = models.ForeignKey(Material,verbose_name='物料id', help_text='物料id', on_delete=models.CASCADE, related_name="material_inventory_m")
    container_no = models.CharField(max_length=64 ,verbose_name='托盘号/容器号', help_text='托盘号/容器号')
    site = models.ForeignKey(GlobalCode ,verbose_name='产地', help_text='产地', on_delete=models.CASCADE, related_name="material_inventory_s")
    qty = models.IntegerField(verbose_name='库存数', help_text='库存数')
    unit = models.CharField(max_length=64, verbose_name='单位', help_text='单位')
    unit_weight = models.DecimalField(verbose_name='单位重量', help_text='单位重量',decimal_places=2, max_digits=8, blank=True, null=True)
    # weight = models.DecimalField(verbose_name='重量', help_text='重量',decimal_places=2, max_digits=8, blank=True, null=True)
    total_weight = models.DecimalField(verbose_name='总重量', help_text='总重量', decimal_places=2 ,max_digits=8, blank=True,null=True)
    quality_status = models.CharField(max_length=8, verbose_name='品质状态',help_text='品质状态')
    lot_no = models.CharField(max_length=64, verbose_name='lot_no',help_text='lot_no')
    location = models.CharField(max_length=64, verbose_name='库位', help_text='库位')
    warehouse_info = models.ForeignKey(WarehouseInfo, verbose_name='仓库id', help_text='仓库id', on_delete=models.CASCADE, related_name="material_inventory_w")

    class Meta:
        db_table = 'material_inventory'
        verbose_name_plural = verbose_name = '库存信息'


class DeliveryPlan(models.Model):
    """出库计划"""
    ORDER_TYPE_CHOICE = (
        (1, '完成'),
        (2, '执行中'),
        (3, '失败'),
        (4, '新建'),
        (5, '关闭')
    )
    warehouse_info = models.ForeignKey(WarehouseInfo, on_delete=models.CASCADE, related_name="delivery_plans")
    order_no = models.CharField(max_length=64, verbose_name='订单号', help_text='订单号')
    pallet_no = models.CharField(max_length=64, verbose_name='托盘号', help_text='托盘号',blank=True,null=True)
    need_qty = models.PositiveIntegerField(verbose_name='需求数量', help_text='需求数量')
    need_weight = models.DecimalField(max_digits=8,decimal_places=2, verbose_name='需求重量', help_text='需求重量')
    material_no = models.CharField(max_length=64, verbose_name='物料编码', help_text='物料编码')
    inventory_type = models.CharField(max_length=32, verbose_name='出入库类型', help_text='出入库类型')
    order_type = models.CharField(max_length=32, verbose_name='订单类型', help_text='订单类型')
    inventory_reason = models.CharField(max_length=128,verbose_name='出入库原因', help_text='出入库原因')
    unit = models.CharField(max_length=64, verbose_name='单位', help_text='单位')
    status = models.PositiveIntegerField(verbose_name='订单状态', help_text='订单状态',choices=ORDER_TYPE_CHOICE, default=1)
    out_time = models.DateTimeField(verbose_name='出库时间', help_text='出库时间', auto_now_add=True)
    created_date = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    last_updated_date = models.DateTimeField(verbose_name='修改时间', auto_now=True)
    location = models.CharField(max_length=64, verbose_name='货位地址', help_text='货位地址')
    created_user = models.ForeignKey(User, blank=True, null=True, related_name='c_%(app_label)s_%(class)s_related',
                                     help_text='创建人', verbose_name='创建人', on_delete=models.CASCADE,
                                     related_query_name='c_%(app_label)s_%(class)ss')


    class Meta:
        db_table = 'delivery_plan'
        verbose_name_plural = verbose_name = '出库计划'


class DeliveryPlanStatus(models.Model):
    """出库计划状态变更记录"""
    ORDER_TYPE_CHOICE = (
        (1, '完成'),
        (2, '执行中'),
        (3, '失败'),
        (4, '新建'),
        (5, '关闭')
    )
    warehouse_info = models.ForeignKey(WarehouseInfo, on_delete=models.CASCADE, related_name="delivery_plan_status")
    order_no = models.CharField(max_length=64, verbose_name='订单号', help_text='订单号')
    order_type = models.CharField(max_length=32, verbose_name='订单类型', help_text='订单类型')
    status = models.PositiveIntegerField(verbose_name='订单号', help_text='订单号', choices=ORDER_TYPE_CHOICE)

    class Meta:
        db_table = 'delivery_plan_status'
        verbose_name_plural = verbose_name = '出库计划状态变更表'
