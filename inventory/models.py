from django.db import models

# Create your models here.
from basics.models import GlobalCode
from recipe.models import Material
from system.models import AbstractEntity, User


class OutOrderFeedBack(models.Model):
    """出库订单反馈"""
    task_id = models.CharField(max_length=64, verbose_name='任务编号', help_text='任务编号', blank=True)
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
    no = models.CharField(max_length=64, verbose_name='仓库编码', help_text='仓库编码')
    name = models.CharField(max_length=64, unique=True, verbose_name='仓库名称', help_text='仓库名称')
    ip = models.CharField(max_length=64, verbose_name='仓库ip', help_text='仓库ip', blank=True, default='')
    address = models.CharField(max_length=64, verbose_name='仓库地址', help_text='仓库地址', blank=True, default='')
    use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)

    class Meta:
        db_table = 'ware_house_info'
        verbose_name_plural = verbose_name = '仓库信息'


class WarehouseMaterialType(models.Model):
    """仓库物料类型"""
    warehouse_info = models.ForeignKey(WarehouseInfo, on_delete=models.CASCADE, related_name="warehouse_material_types")
    material_type = models.ForeignKey(GlobalCode, on_delete=models.CASCADE)
    use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)

    class Meta:
        db_table = 'ware_house_material_type'
        verbose_name_plural = verbose_name = '仓库物料类型'


class InventoryLog(models.Model):
    """出入库履历"""
    warehouse_no = models.CharField(max_length=64, verbose_name='仓库编号', help_text='仓库编号')
    warehouse_name = models.CharField(max_length=64, verbose_name='仓库名称', help_text='仓库名称')
    order_no = models.CharField(max_length=64, verbose_name='订单号', help_text='订单号')
    pallet_no = models.CharField(max_length=64, verbose_name='托盘号', help_text='托盘号')
    location = models.CharField(max_length=64, verbose_name='货位地址', help_text='货位地址')
    qty = models.PositiveIntegerField(verbose_name='数量', help_text='数量', blank=True, null=True)
    weight = models.DecimalField(verbose_name='重量', help_text='重量', blank=True, null=True, decimal_places=2,
                                 max_digits=8)
    material_no = models.CharField(max_length=64, verbose_name='物料编码', help_text='物料编码')
    quality_status = models.CharField(max_length=8, verbose_name='品质状态', help_text='品质状态')
    lot_no = models.CharField(max_length=64, verbose_name='lot_no', help_text='lot_no')
    order_type = models.CharField(max_length=64, verbose_name='订单类型', help_text='订单类型')
    inout_reason = models.CharField(max_length=64, verbose_name='出入库原因', help_text='出入库原因')
    inout_num_type = models.CharField(max_length=64, verbose_name='出入库数类型', help_text='出入库数类型')
    inventory_type = models.CharField(max_length=64, verbose_name='BZ出入库类型', help_text='BZ出入库数类型') # 生产出库/快检异常出库
    unit = models.CharField(max_length=64, verbose_name='单位', help_text='单位')
    initiator = models.CharField(max_length=64, blank=True, null=True, verbose_name='发起人',
                                 help_text='发起人')
    start_time = models.DateTimeField('发起时间', blank=True, null=True, help_text='发起时间')
    fin_time = models.DateTimeField(verbose_name='完成时间', help_text='完成时间', auto_now_add=True)

    class Meta:
        db_table = 'inventory_log'
        verbose_name_plural = verbose_name = '出入库履历'


class MaterialInventory(models.Model):
    """库存信息|线边库"""
    material = models.ForeignKey(Material, verbose_name='物料id', help_text='物料id', on_delete=models.CASCADE,
                                 related_name="material_inventory_m")
    container_no = models.CharField(max_length=64, verbose_name='托盘号/容器号', help_text='托盘号/容器号')
    site = models.ForeignKey(GlobalCode, verbose_name='产地', help_text='产地', on_delete=models.CASCADE,
                             related_name="material_inventory_s")
    qty = models.IntegerField(verbose_name='库存数', help_text='库存数')
    unit = models.CharField(max_length=64, verbose_name='单位', help_text='单位')
    unit_weight = models.DecimalField(verbose_name='单位重量', help_text='单位重量', decimal_places=2, max_digits=8, blank=True,
                                      null=True)
    # weight = models.DecimalField(verbose_name='重量', help_text='重量',decimal_places=2, max_digits=8, blank=True, null=True)
    total_weight = models.DecimalField(verbose_name='总重量', help_text='总重量', decimal_places=2, max_digits=8, blank=True,
                                       null=True)
    quality_status = models.CharField(max_length=8, verbose_name='品质状态', help_text='品质状态')
    lot_no = models.CharField(max_length=64, verbose_name='lot_no', help_text='lot_no')
    location = models.CharField(max_length=64, verbose_name='库位', help_text='库位')
    warehouse_info = models.ForeignKey(WarehouseInfo, verbose_name='仓库id', help_text='仓库id', on_delete=models.CASCADE,
                                       related_name="material_inventory_w")

    class Meta:
        db_table = 'material_inventory'
        verbose_name_plural = verbose_name = '库存信息'


class BzFinalMixingRubberInventory(models.Model):
    """bz终炼胶库"""
    id = models.PositiveIntegerField(db_column='库存索引', primary_key=True)
    store_id = models.CharField(max_length=20, db_column='库房编号')
    store_name = models.CharField(max_length=20, db_column='库房名称')
    bill_id = models.CharField(max_length=50, db_column='订单号')
    container_no = models.CharField(max_length=50, db_column='托盘号')
    location = models.CharField(max_length=20, db_column='货位地址')
    qty = models.DecimalField(max_digits=15, decimal_places=3, db_column='数量')
    total_weight = models.DecimalField(max_digits=15, decimal_places=3, db_column='重量')
    quality_status = models.CharField(max_length=20, db_column='品质状态')
    memo = models.CharField(max_length=250, db_column='车号')
    lot_no = models.CharField(max_length=200, db_column='追溯号')
    material_no = models.CharField(max_length=50, db_column='物料编码')
    in_storage_time = models.DateTimeField(db_column='入库时间')
    location_status = models.CharField(max_length=20, db_column='货位状态')

    def material_type(self):
        try:
            mt = self.material_no.split("-")[1]
        except:
            mt = self.material_no
        return mt

    def unit(self):
        return "kg"

    def unit_weight(self):
        return str(round(self.total_weight / self.qty, 3))

    class Meta:
        db_table = 'v_ASRS_STORE_MESVIEW'
        managed = False


class BzFinalMixingRubberInventoryLB(models.Model):
    """bz终炼胶库"""
    id = models.PositiveIntegerField(db_column='库存索引', primary_key=True)
    store_id = models.CharField(max_length=20, db_column='库房编号')
    store_name = models.CharField(max_length=20, db_column='库房名称')
    bill_id = models.CharField(max_length=50, db_column='订单号')
    container_no = models.CharField(max_length=50, db_column='托盘号')
    location = models.CharField(max_length=20, db_column='货位地址')
    qty = models.DecimalField(max_digits=15, decimal_places=3, db_column='数量')
    total_weight = models.DecimalField(max_digits=15, decimal_places=3, db_column='重量')
    quality_status = models.CharField(max_length=20, db_column='品质状态')
    memo = models.CharField(max_length=250, db_column='车号')
    lot_no = models.CharField(max_length=200, db_column='追溯号')
    material_no = models.CharField(max_length=50, db_column='物料编码')
    in_storage_time = models.DateTimeField(db_column='入库时间')
    location_status = models.CharField(max_length=20, db_column='货位状态')

    def material_type(self):
        try:
            mt = self.material_no.split("-")[1]
        except:
            mt = self.material_no
        return mt

    def unit(self):
        return "kg"

    def unit_weight(self):
        return str(round(self.total_weight / self.qty, 3))

    class Meta:
        db_table = 'v_ASRS_STORE_MESVIEW'
        managed = False


class WmsInventoryStock(models.Model):
    """wms"""
    sn = models.CharField(max_length=255, db_column='Sn', primary_key=True)
    qty = models.DecimalField(max_digits=18, decimal_places=2, db_column='Quantity')
    material_name = models.CharField(max_length=64, db_column='MaterialName')
    total_weight = models.DecimalField(max_digits=18, decimal_places=2, db_column='WeightOfActual')
    material_no = models.CharField(max_length=64, db_column='MaterialCode')
    location = models.CharField(max_length=255, db_column='ProductionAddress')
    unit = models.CharField(max_length=64, db_column='WeightUnit')
    quality_status = models.IntegerField(db_column='StockDetailState')
    material_type = models.CharField(max_length=64)
    lot_no = models.CharField(max_length=64, db_column='BatchNo')

    class Meta:
        db_table = 't_inventory_stock'
        managed = False

    @classmethod
    def get_sql(cls, material_type=None, material_no=None):
        material_type_filter = """AND material.MaterialGroupName LIKE '%%{0}%%'""" \
            .format(material_type) if material_type else ''
        material_no_filter = """AND stock.MaterialCode LIKE '%%{material_no}%%'""" \
            .format(material_no=material_no) if material_no else ''
        sql = """
                    SELECT *, material.MaterialGroupName AS material_type 
                    FROM zhada_wms_zhongc.dbo.t_inventory_stock stock,
                      zhada_wms_zhongc.dbo.t_inventory_material material
                        WHERE stock.MaterialCode = material.MaterialCode
                        {0} {1}
                    """.format(material_type_filter, material_no_filter)
        return sql

    def container_no(self):
        return "Unknown"

    def unit_weight(self):
        return "Unknown"


class WmsInventoryMaterial(models.Model):
    id = models.PositiveIntegerField(db_column='id', primary_key=True)
    material_no = models.CharField(max_length=64, db_column='MaterialCode')
    material_type = models.CharField(max_length=64, db_column='MaterialGroupName')

    class Meta:
        db_table = 't_inventory_material'
        managed = False


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
    pallet_no = models.CharField(max_length=64, verbose_name='托盘号', help_text='托盘号', blank=True, null=True)
    need_qty = models.PositiveIntegerField(verbose_name='需求数量', help_text='需求数量', blank=True, null=True)
    need_weight = models.DecimalField(max_digits=8, decimal_places=3, verbose_name='需求重量', help_text='需求重量', blank=True,
                                      null=True)
    material_no = models.CharField(max_length=64, verbose_name='物料编码', help_text='物料编码', blank=True, null=True)
    inventory_type = models.CharField(max_length=32, verbose_name='出入库类型', help_text='出入库类型', blank=True, null=True)
    order_type = models.CharField(max_length=32, verbose_name='订单类型', help_text='订单类型', blank=True, null=True)
    inventory_reason = models.CharField(max_length=128, verbose_name='出入库原因', help_text='出入库原因', blank=True, null=True)
    unit = models.CharField(max_length=64, verbose_name='单位', help_text='单位', blank=True, null=True)
    status = models.PositiveIntegerField(verbose_name='订单状态', help_text='订单状态', choices=ORDER_TYPE_CHOICE, default=4)
    created_date = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    last_updated_date = models.DateTimeField(verbose_name='修改时间', blank=True, null=True)
    created_user = models.CharField(max_length=64, verbose_name='发起人', help_text='发起人', blank=True, null=True)
    location = models.CharField(max_length=64, verbose_name='货位地址', help_text='货位地址',blank=True, null=True)


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
    status = models.PositiveIntegerField(verbose_name='订单号', help_text='订单号', choices=ORDER_TYPE_CHOICE, default=4)
    created_date = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    created_user = models.CharField(max_length=64, verbose_name='发起人', help_text='发起人', blank=True, null=True)

    class Meta:
        db_table = 'delivery_plan_status'
        verbose_name_plural = verbose_name = '出库计划状态变更表'


class Station(models.Model):
    """站点信息"""
    no = models.CharField('站点编码', max_length=64, help_text='站点编码')
    name = models.CharField('站点名称', max_length=64, help_text='站点名称')
    desc = models.CharField('备注', max_length=64, help_text='备注', blank=True, default='')
    warehouse_info = models.ForeignKey(WarehouseInfo, verbose_name='所属仓库', help_text='所属仓库', on_delete=models.SET_NULL,
                                       null=True, blank=True)
    type = models.ForeignKey(GlobalCode, verbose_name='站点类型', help_text='站点类型', on_delete=models.SET_NULL, null=True,
                             blank=True)
    use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)

    class Meta:
        db_table = 'station'
        verbose_name_plural = verbose_name = '站点信息'