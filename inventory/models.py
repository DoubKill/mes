from django.db import models

# Create your models here.
from django.db.models import Sum

from basics.models import GlobalCode, Equip
from production.models import PalletFeedbacks
from recipe.models import Material, ProductBatching
from system.models import AbstractEntity, User


class WarehouseInfo(AbstractEntity):
    """仓库信息"""
    no = models.CharField(max_length=64, verbose_name='仓库编码', help_text='仓库编码')
    name = models.CharField(max_length=64, unique=True, verbose_name='仓库名称', help_text='仓库名称')
    ip = models.CharField(max_length=64, verbose_name='仓库ip', help_text='仓库ip', blank=True, default='')
    address = models.CharField(max_length=64, verbose_name='仓库地址', help_text='仓库地址', blank=True, default='')
    use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)

    class Meta:
        db_table = 'ware_house_info'
        verbose_name_plural = verbose_name = '仓库信息'


class WarehouseMaterialType(AbstractEntity):
    """仓库物料类型"""
    warehouse_info = models.ForeignKey(WarehouseInfo, on_delete=models.CASCADE, related_name="warehouse_material_types")
    material_type = models.ForeignKey(GlobalCode, on_delete=models.CASCADE)
    use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)

    class Meta:
        db_table = 'ware_house_material_type'
        verbose_name_plural = verbose_name = '仓库物料类型'


class MaterialInventory(AbstractEntity):
    """库存信息|线边库"""
    material = models.ForeignKey(Material, verbose_name='物料id', help_text='物料id', on_delete=models.CASCADE,
                                 related_name="material_inventory_m", null=True)
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
    """bz混炼胶库 | 目前混炼胶终炼胶都存"""
    id = models.PositiveIntegerField(db_column='库存索引', primary_key=True)
    store_id = models.CharField(max_length=20, db_column='库房编号')
    store_name = models.CharField(max_length=20, db_column='库房名称')
    bill_id = models.CharField(max_length=50, db_column='订单号')
    container_no = models.CharField(max_length=50, db_column='托盘号')
    location = models.CharField(max_length=20, db_column='货位地址')
    qty = models.DecimalField(max_digits=15, decimal_places=3, db_column='数量')
    total_weight = models.DecimalField(max_digits=15, decimal_places=3, db_column='重量')
    quality_status = models.CharField(max_length=20, db_column='品质状态')
    quality_level = models.CharField(max_length=6, db_column='品质等级')
    memo = models.CharField(max_length=250, db_column='车号')
    lot_no = models.CharField(max_length=200, db_column='追溯号')
    material_no = models.CharField(max_length=50, db_column='物料编码')
    in_storage_time = models.DateTimeField(db_column='入库时间')
    location_status = models.CharField(max_length=20, db_column='货位状态')

    @property
    def material_name(self):
        return self.material_no

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
    """bz帘布/终炼"""
    id = models.PositiveIntegerField(db_column='库存索引', primary_key=True)
    store_id = models.CharField(max_length=20, db_column='库房编号')
    store_name = models.CharField(max_length=20, db_column='库房名称')
    bill_id = models.CharField(max_length=50, db_column='订单号')
    container_no = models.CharField(max_length=50, db_column='托盘号')
    location = models.CharField(max_length=20, db_column='货位地址')
    qty = models.DecimalField(max_digits=15, decimal_places=3, db_column='数量')
    total_weight = models.DecimalField(max_digits=15, decimal_places=3, db_column='重量')
    quality_status = models.CharField(max_length=20, db_column='品质状态')
    quality_level = models.CharField(max_length=6, db_column='品质等级')
    memo = models.CharField(max_length=250, db_column='车号')
    lot_no = models.CharField(max_length=200, db_column='追溯号')
    material_no = models.CharField(max_length=50, db_column='物料编码')
    material_name = models.CharField(max_length=50, db_column='MATNAME')
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
    """wms原材料库"""
    sn = models.CharField(max_length=255, db_column='Sn', primary_key=True)
    qty = models.DecimalField(max_digits=18, decimal_places=2, db_column='Quantity')
    material_name = models.CharField(max_length=64, db_column='MaterialName')
    total_weight = models.DecimalField(max_digits=18, decimal_places=2, db_column='WeightOfActual')
    material_no = models.CharField(max_length=64, db_column='MaterialCode')
    location = models.CharField(max_length=255, db_column='SpaceId')
    unit = models.CharField(max_length=64, db_column='StandardUnit')
    quality_status = models.IntegerField(db_column='StockDetailState')
    # material_type = models.CharField(max_length=64)
    batch_no = models.CharField(max_length=64, db_column='BatchNo')
    container_no = models.CharField(max_length=32, db_column="LadenToolNumber")
    in_storage_time = models.DateTimeField(db_column='CreaterTime')
    lot_no = models.CharField(max_length=64, db_column='TrackingNumber')
    supplier_name = models.CharField(max_length=64, db_column='SupplierName')
    tunnel = models.CharField(max_length=32, db_column="tunnelId")  # 巷道
    # shelf = models.CharField(max_length=32, db_column="shelfId", help_text="列号")  # 列号
    # layer = models.CharField(max_length=32, db_column="layerId", help_text="层号")  # 层号
    sl = models.DecimalField(max_digits=18, decimal_places=4, db_column='SL')
    zl = models.DecimalField(max_digits=18, decimal_places=4, db_column='ZL')

    def unit_weight(self):
        return self.total_weight / self.qty

    def location_status(self):
        return "暂未开放"

    class Meta:
        db_table = 't_inventory_stock'
        managed = False

    @classmethod
    def get_sql(cls, material_type=None, material_no=None, container_no=None, order_no=None, location=None, tunnel=None, quality_status=None, lot_no=None):
        material_type_filter = """AND material.MaterialGroupName LIKE '%%{material_type}%%'""" \
            .format(material_type=material_type) if material_type else ''
        material_no_filter = """AND stock.MaterialCode LIKE '%%{material_no}%%'""" \
            .format(material_no=material_no) if material_no else ''
        container_no_filter = """AND stock.LadenToolNumber LIKE '%%{container_no}%%'""" \
            .format(container_no=container_no) if container_no else ''
        order_no_filter = """AND stock.BatchNo LIKE '%%{order_no}%%'""" \
            .format(order_no=order_no) if order_no else ''
        location_filter = """AND stock.SpaceId LIKE '%%{location}%%'""" \
            .format(location=location) if location else ''
        tunnel_filter = """AND stock.tunnelId = '{tunnel}'""" \
            .format(tunnel=tunnel) if tunnel else ''
        quality_filter = """AND stock.StockDetailState = '{quality_status}'""" \
            .format(quality_status=quality_status) if quality_status else ''
        lot_no_filter = """AND stock.TrackingNumber LIKE '%%{lot_no}%%'""" \
            .format(lot_no=lot_no) if lot_no else ''
        sql = """
                    SELECT *, material.MaterialGroupName AS material_type 
                    FROM zhada_wms_zhongc.dbo.t_inventory_stock stock,
                      zhada_wms_zhongc.dbo.t_inventory_material material
                        WHERE stock.MaterialCode = material.MaterialCode
                        {0} {1} {2} {3} {4} {5} {6}
                    """.format(material_type_filter, material_no_filter, container_no_filter,
                               order_no_filter, location_filter, tunnel_filter, quality_filter, lot_no_filter)
        return sql

    @classmethod
    def quality_sql(cls, material_type=None, material_no=None, lot_no=None):
        material_type_filter = """AND material.MaterialGroupName LIKE '%%{0}%%'""" \
            .format(material_type) if material_type else ''
        material_no_filter = """AND stock.MaterialCode LIKE '%%{material_no}%%'""" \
            .format(material_no=material_no) if material_no else ''
        lot_no_filter = """AND stock.TrackingNumber LIKE '%%{lot_no}%%'""" \
            .format(lot_no=lot_no) if lot_no else ''
        sql = """
                            SELECT *, material.MaterialGroupName AS material_type 
                            FROM zhada_wms_zhongc.dbo.t_inventory_stock stock,
                              zhada_wms_zhongc.dbo.t_inventory_material material
                                WHERE stock.MaterialCode = material.MaterialCode
                                {0} {1} {2}
                            """.format(material_type_filter, material_no_filter, lot_no_filter)
        return sql


class WmsInventoryMaterial(models.Model):
    # 原材料库分类表
    id = models.PositiveIntegerField(db_column='id', primary_key=True)
    material_no = models.CharField(max_length=64, db_column='MaterialCode')
    material_name = models.CharField(max_length=128, db_column='Name')
    material_type = models.CharField(max_length=64, db_column='MaterialGroupName')
    pdm_no = models.CharField(max_length=64, db_column='Pdm')
    erp_material_no = models.CharField(max_length=64, db_column='ZCMaterialCode')
    unit = models.CharField(max_length=64, db_column='StandardUnit')
    is_validity = models.BooleanField(db_column='IsValidity')
    period_of_validity = models.IntegerField(db_column='Validity')

    class Meta:
        db_table = 't_inventory_material'
        managed = False


class OutBoundDeliveryOrder(AbstractEntity):
    """
        胶料出库单据
    """
    WAREHOUSE_CHOICE = (
        ('混炼胶库', '混炼胶库'),
        ('终炼胶库', '终炼胶库')
    )
    STATUS_CHOICE = (
        (1, '已创建'),
        (2, '等待出库'),
        (3, '已出库'),
        (4, '关闭'),
        (5, '失败')
    )
    ORDER_TYPE_CHOICE = (
        (1, '普通'),
        (2, '指定胶料信息'),
        (3, '指定托盘号'),
    )
    warehouse = models.CharField(max_length=64, verbose_name='库区', help_text='库区(混炼胶库/终炼胶库)', choices=WAREHOUSE_CHOICE)
    order_no = models.CharField(max_length=64, verbose_name='出库单号', help_text='出库单号', unique=True)
    status = models.PositiveIntegerField(verbose_name='状态', help_text='状态', choices=STATUS_CHOICE, default=1)
    product_no = models.CharField(max_length=64, help_text='胶料名称', blank=True, null=True)
    station = models.CharField(max_length=64, help_text='出库口名称')
    order_qty = models.IntegerField(help_text='订单数量', default=0)
    # need_qty = models.IntegerField(help_text='需求数量', default=0)
    # work_qty = models.IntegerField(help_text='工作数量', default=0)
    # finished_qty = models.IntegerField(help_text='完成数量', default=0)
    need_weight = models.FloatField(help_text='需求重量', default=0)
    finished_weight = models.FloatField(help_text='完成重量', default=0)
    inventory_type = models.CharField(max_length=32, verbose_name='出库类型', help_text='出库类型', blank=True, null=True)
    inventory_reason = models.CharField(max_length=32, verbose_name='出库原因', help_text='出库原因', blank=True, null=True)
    quality_status = models.CharField(max_length=64, help_text='品质状态', blank=True, null=True)
    order_type = models.PositiveIntegerField(choices=ORDER_TYPE_CHOICE, default=1, help_text='类型')
    pallet_no = models.CharField(max_length=32, verbose_name='托盘号', help_text='托盘号', blank=True, null=True)
    factory_date = models.DateField(verbose_name='工厂日期', help_text='工厂日期', blank=True, null=True)
    equip_no = models.CharField(max_length=32, verbose_name='机台号', help_text='机台号', blank=True, null=True)
    classes = models.CharField(max_length=32, verbose_name='班次', help_text='班次', blank=True, null=True)
    begin_trains = models.IntegerField(verbose_name='开始车次', help_text='开始车次', blank=True, null=True)
    end_trains = models.IntegerField(verbose_name='结束车次', help_text='结束车次', blank=True, null=True)

    class Meta:
        db_table = 'outbound_delivery_order'
        verbose_name_plural = verbose_name = '胶料出库单据'


class OutBoundDeliveryOrderDetail(AbstractEntity):
    """
        胶料出库单据详情
    """
    STATUS_CHOICE = (
        (1, '新建'),
        (2, '执行中'),
        (3, '已出库'),
        (4, '取消'),
        (5, '失败')
    )
    outbound_delivery_order = models.ForeignKey(OutBoundDeliveryOrder, help_text='出库单据', on_delete=models.CASCADE,
                                                related_name='outbound_delivery_details')
    order_no = models.CharField(max_length=64, verbose_name='出库任务编号', help_text='出库任务编号', unique=True)
    # station = models.CharField(max_length=64, verbose_name='出库口', help_text='出库口', blank=True, null=True)
    status = models.PositiveIntegerField(verbose_name='出库任务状态', help_text='出库任务状态', choices=STATUS_CHOICE, default=1)
    pallet_no = models.CharField(max_length=64, verbose_name='托盘号', help_text='托盘号', blank=True, null=True)
    location = models.CharField(max_length=64, verbose_name='货位地址', help_text='货位地址', blank=True, null=True)
    lot_no = models.CharField(max_length=64, help_text='收皮条码', blank=True, null=True)
    memo = models.CharField(max_length=64, help_text='车号', blank=True, null=True)
    qty = models.IntegerField(help_text='车数', default=0)
    weight = models.FloatField(help_text='重量', default=0)
    quality_status = models.CharField(max_length=64, help_text='品质状态')
    inventory_time = models.DateTimeField(verbose_name='入库时间', blank=True, null=True)
    finish_time = models.DateTimeField(verbose_name='出库完成时间', blank=True, null=True)
    equip = models.ManyToManyField(Equip, verbose_name="设备", help_text="设备", blank=True,
                                   related_name='equip_delivery_details')
    dispatch = models.ManyToManyField('DispatchPlan', verbose_name="发货单", help_text="发货单", blank=True,
                                      related_name='dispatch_delivery_details')
    sub_no = models.CharField(max_length=64, help_text='订单自编号', blank=True, null=True)

    class Meta:
        db_table = 'outbound_delivery_order_details'
        verbose_name_plural = verbose_name = '胶料出库单据详情'


class MixinRubberyOutBoundOrder(AbstractEntity):
    """混炼胶出库单据"""
    STATUS_CHOICE = (
        (1, '已创建'),
        (2, '等待出库'),
        (3, '已出库'),
        (4, '关闭'),
        (5, '失败')
    )
    warehouse_name = models.CharField(max_length=64, help_text='仓库名称')
    order_type = models.CharField(max_length=32, verbose_name='订单类型', help_text='订单类型', blank=True, null=True)
    order_no = models.CharField(max_length=64, verbose_name='出库单号', help_text='出库单号', unique=True)
    status = models.PositiveIntegerField(verbose_name='状态', help_text='状态', choices=STATUS_CHOICE, default=1)

    class Meta:
        db_table = 'mixin_rubber_outbound_order'
        verbose_name_plural = verbose_name = '混炼胶出库单据'


class DeliveryPlan(AbstractEntity):
    """出库计划 | 混炼胶"""
    ORDER_TYPE_CHOICE = (
        (1, '完成'),
        (2, '执行中'),
        (3, '失败'),
        (4, '新建'),
        (5, '关闭')
    )
    outbound_order = models.ForeignKey(MixinRubberyOutBoundOrder, help_text='出库单据',
                                       on_delete=models.SET_NULL, null=True, related_name='mixin_plans')
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
    unit = models.CharField(max_length=64, verbose_name='单位', help_text='单位', default="kg")
    status = models.PositiveIntegerField(verbose_name='订单状态', help_text='订单状态', choices=ORDER_TYPE_CHOICE, default=4)
    location = models.CharField(max_length=64, verbose_name='货位地址', help_text='货位地址', blank=True, null=True)
    station = models.CharField(max_length=64, verbose_name='出库口', help_text='出库口', blank=True, null=True)
    finish_time = models.DateTimeField(verbose_name='完成时间', blank=True, null=True)
    equip = models.ManyToManyField(Equip, verbose_name="设备", help_text="设备", blank=True,
                                   related_name='dispatch_mix_deliverys')
    dispatch = models.ManyToManyField('DispatchPlan', verbose_name="发货单", help_text="发货单", blank=True,
                                      related_name='equip_mix_deliverys')
    lot_no = models.CharField(max_length=64, help_text='托盘号', blank=True, null=True)
    memo = models.CharField(max_length=64, help_text='车号', blank=True, null=True)

    class Meta:
        db_table = 'delivery_plan'
        verbose_name_plural = verbose_name = '出库计划'


class DeliveryPlanLB(AbstractEntity):
    """出库计划 | 帘布"""
    ORDER_TYPE_CHOICE = (
        (1, '完成'),
        (2, '执行中'),
        (3, '失败'),
        (4, '新建'),
        (5, '关闭')
    )
    warehouse_info = models.ForeignKey(WarehouseInfo, on_delete=models.CASCADE, related_name="delivery_plans_lb")
    order_no = models.CharField(max_length=64, verbose_name='订单号', help_text='订单号')
    pallet_no = models.CharField(max_length=64, verbose_name='托盘号', help_text='托盘号', blank=True, null=True)
    need_qty = models.PositiveIntegerField(verbose_name='需求数量', help_text='需求数量', blank=True, null=True)
    need_weight = models.DecimalField(max_digits=8, decimal_places=3, verbose_name='需求重量', help_text='需求重量', blank=True,
                                      null=True)
    material_no = models.CharField(max_length=64, verbose_name='物料编码', help_text='物料编码', blank=True, null=True)
    material_name = models.CharField(max_length=64, verbose_name='物料名称', help_text='物料名称', blank=True, null=True)
    inventory_type = models.CharField(max_length=32, verbose_name='出入库类型', help_text='出入库类型', blank=True, null=True)
    order_type = models.CharField(max_length=32, verbose_name='订单类型', help_text='订单类型', blank=True, null=True)
    inventory_reason = models.CharField(max_length=128, verbose_name='出入库原因', help_text='出入库原因', blank=True, null=True)
    unit = models.CharField(max_length=64, verbose_name='单位', help_text='单位', default="kg")
    status = models.PositiveIntegerField(verbose_name='订单状态', help_text='订单状态', choices=ORDER_TYPE_CHOICE, default=4)
    location = models.CharField(max_length=64, verbose_name='货位地址', help_text='货位地址', blank=True, null=True)
    station = models.CharField(max_length=64, verbose_name='出库口', help_text='出库口', blank=True, null=True)
    finish_time = models.DateTimeField(verbose_name='完成时间', blank=True, null=True)
    equip = models.ManyToManyField(Equip, verbose_name="设备", help_text="设备", blank=True,
                                   related_name='dispatch_lb_deliverys')
    dispatch = models.ManyToManyField("DispatchPlan", verbose_name="发货单", help_text="发货单", blank=True,
                                      related_name='equip_lb_deliverys')

    class Meta:
        db_table = 'delivery_plan_lb'
        verbose_name_plural = verbose_name = '帘布库出库计划'


class FinalRubberyOutBoundOrder(AbstractEntity):
    """终炼胶出库单据"""
    STATUS_CHOICE = (
        (1, '已创建'),
        (2, '等待出库'),
        (3, '已出库'),
        (4, '关闭'),
        (5, '失败')
    )
    warehouse_name = models.CharField(max_length=64, help_text='仓库名称')
    order_type = models.CharField(max_length=32, verbose_name='订单类型', help_text='订单类型', blank=True, null=True)
    order_no = models.CharField(max_length=64, verbose_name='出库单号', help_text='出库单号', unique=True)
    status = models.PositiveIntegerField(verbose_name='状态', help_text='状态', choices=STATUS_CHOICE, default=1)

    class Meta:
        db_table = 'final_rubber_outbound_order'
        verbose_name_plural = verbose_name = '终炼胶出库单据'


class DeliveryPlanFinal(AbstractEntity):
    """出库计划 | 终炼"""
    ORDER_TYPE_CHOICE = (
        (1, '完成'),
        (2, '执行中'),
        (3, '失败'),
        (4, '新建'),
        (5, '关闭')
    )
    outbound_order = models.ForeignKey(FinalRubberyOutBoundOrder, help_text='出库单据',
                                       on_delete=models.SET_NULL, null=True, related_name='final_plans')
    warehouse_info = models.ForeignKey(WarehouseInfo, on_delete=models.CASCADE, related_name="delivery_plans_final")
    order_no = models.CharField(max_length=64, verbose_name='订单号', help_text='订单号')
    pallet_no = models.CharField(max_length=64, verbose_name='托盘号', help_text='托盘号', blank=True, null=True)
    need_qty = models.PositiveIntegerField(verbose_name='需求数量', help_text='需求数量', blank=True, null=True)
    need_weight = models.DecimalField(max_digits=8, decimal_places=3, verbose_name='需求重量', help_text='需求重量', blank=True,
                                      null=True)
    material_no = models.CharField(max_length=64, verbose_name='物料编码', help_text='物料编码', blank=True, null=True)
    inventory_type = models.CharField(max_length=32, verbose_name='出入库类型', help_text='出入库类型', blank=True, null=True)
    order_type = models.CharField(max_length=32, verbose_name='订单类型', help_text='订单类型', blank=True, null=True)
    inventory_reason = models.CharField(max_length=128, verbose_name='出入库原因', help_text='出入库原因', blank=True, null=True)
    unit = models.CharField(max_length=64, verbose_name='单位', help_text='单位', default="kg")
    status = models.PositiveIntegerField(verbose_name='订单状态', help_text='订单状态', choices=ORDER_TYPE_CHOICE, default=4)
    location = models.CharField(max_length=64, verbose_name='货位地址', help_text='货位地址', blank=True, null=True)
    station = models.CharField(max_length=64, verbose_name='出库口', help_text='出库口', blank=True, null=True)
    finish_time = models.DateTimeField(verbose_name='完成时间', blank=True, null=True)
    equip = models.ManyToManyField(Equip, verbose_name="设备", help_text="设备", blank=True,
                                   related_name='dispatch_final_deliverys')
    dispatch = models.ManyToManyField('DispatchPlan', verbose_name="发货单", help_text="发货单", blank=True,
                                      related_name='equip_final_deliverys')
    lot_no = models.CharField(max_length=64, help_text='托盘号', blank=True, null=True)
    memo = models.CharField(max_length=64, help_text='车号', blank=True, null=True)

    class Meta:
        db_table = 'delivery_plan_final'
        verbose_name_plural = verbose_name = '终炼胶库出库计划'


class MaterialOutPlan(AbstractEntity):
    """出库计划 | 原材料"""
    ORDER_TYPE_CHOICE = (
        (1, '完成'),
        (2, '执行中'),
        (3, '失败'),
        (4, '新建'),
        (5, '关闭')
    )
    warehouse_info = models.ForeignKey(WarehouseInfo, on_delete=models.CASCADE, related_name="material_out_plan")
    order_no = models.CharField(max_length=64, verbose_name='订单号', help_text='订单号')
    pallet_no = models.CharField(max_length=64, verbose_name='托盘号', help_text='托盘号', blank=True, null=True)
    need_qty = models.DecimalField(max_digits=8, decimal_places=3, verbose_name='需求数量', help_text='需求数量', blank=True, null=True)
    need_weight = models.DecimalField(max_digits=8, decimal_places=3, verbose_name='需求重量', help_text='需求重量', blank=True,
                                      null=True)
    material_no = models.CharField(max_length=64, verbose_name='物料编码', help_text='物料编码', blank=True, null=True)
    material_name = models.CharField(max_length=64, verbose_name='物料名称', help_text='物料名称', blank=True, null=True)
    batch_no = models.CharField(max_length=64, verbose_name='批次号', help_text='批次号', blank=True, null=True)
    inventory_type = models.CharField(max_length=32, verbose_name='出入库类型', help_text='出入库类型', blank=True, null=True)
    order_type = models.CharField(max_length=32, verbose_name='订单类型', help_text='订单类型', blank=True, null=True)
    inventory_reason = models.CharField(max_length=128, verbose_name='出入库原因', help_text='出入库原因', blank=True, null=True)
    unit = models.CharField(max_length=64, verbose_name='单位', help_text='单位', default="kg")
    status = models.PositiveIntegerField(verbose_name='订单状态', help_text='订单状态', choices=ORDER_TYPE_CHOICE, default=4)
    location = models.CharField(max_length=64, verbose_name='货位地址', help_text='货位地址', blank=True, null=True)
    station = models.CharField(max_length=64, verbose_name='出库口', help_text='出库口')
    station_no = models.CharField(max_length=64, verbose_name='出库口编码', help_text='出库口编码')
    finish_time = models.DateTimeField(verbose_name='完成时间', blank=True, null=True)
    equip = models.ManyToManyField(Equip, verbose_name="设备", help_text="设备", blank=True,
                                   related_name='material_out_equip')
    dispatch = models.ManyToManyField('DispatchPlan', verbose_name="发货单", help_text="发货单", blank=True,
                                      related_name='material_out_dispatch')

    class Meta:
        db_table = 'material_out_plan'
        verbose_name_plural = verbose_name = '原材料出库计划'


class CarbonOutPlan(AbstractEntity):
    """出库计划 | 原材料"""
    ORDER_TYPE_CHOICE = (
        (1, '完成'),
        (2, '执行中'),
        (3, '失败'),
        (4, '新建'),
        (5, '关闭')
    )
    warehouse_info = models.ForeignKey(WarehouseInfo, on_delete=models.CASCADE, related_name="carbon_out_plan")
    order_no = models.CharField(max_length=64, verbose_name='订单号', help_text='订单号')
    pallet_no = models.CharField(max_length=64, verbose_name='托盘号', help_text='托盘号', blank=True, null=True)
    need_qty = models.DecimalField(max_digits=8, decimal_places=3, verbose_name='需求数量', help_text='需求数量', blank=True, null=True)
    need_weight = models.DecimalField(max_digits=8, decimal_places=3, verbose_name='需求重量', help_text='需求重量', blank=True,
                                      null=True)
    material_no = models.CharField(max_length=64, verbose_name='物料编码', help_text='物料编码', blank=True, null=True)
    material_name = models.CharField(max_length=64, verbose_name='物料名称', help_text='物料名称', blank=True, null=True)
    batch_no = models.CharField(max_length=64, verbose_name='批次号', help_text='批次号', blank=True, null=True)
    inventory_type = models.CharField(max_length=32, verbose_name='出入库类型', help_text='出入库类型', blank=True, null=True)
    order_type = models.CharField(max_length=32, verbose_name='订单类型', help_text='订单类型', blank=True, null=True)
    inventory_reason = models.CharField(max_length=128, verbose_name='出入库原因', help_text='出入库原因', blank=True, null=True)
    unit = models.CharField(max_length=64, verbose_name='单位', help_text='单位', default="kg")
    status = models.PositiveIntegerField(verbose_name='订单状态', help_text='订单状态', choices=ORDER_TYPE_CHOICE, default=4)
    location = models.CharField(max_length=64, verbose_name='货位地址', help_text='货位地址', blank=True, null=True)
    station = models.CharField(max_length=64, verbose_name='出库口', help_text='出库口')
    station_no = models.CharField(max_length=64, verbose_name='出库口编码', help_text='出库口编码')
    finish_time = models.DateTimeField(verbose_name='完成时间', blank=True, null=True)
    equip = models.ManyToManyField(Equip, verbose_name="设备", help_text="设备", blank=True,
                                   related_name='carbon_out_equip')
    dispatch = models.ManyToManyField('DispatchPlan', verbose_name="发货单", help_text="发货单", blank=True,
                                      related_name='carbon_out_dispatch')

    class Meta:
        db_table = 'carbon_out_plan'
        verbose_name_plural = verbose_name = '原材料出库计划'


class DeliveryPlanStatus(AbstractEntity):
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

    class Meta:
        db_table = 'delivery_plan_status'
        verbose_name_plural = verbose_name = '出库计划状态变更表'


class Station(AbstractEntity):
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


class DispatchLocation(AbstractEntity):
    """发货地"""

    no = models.CharField('发货地编码', max_length=64, help_text='发货地编码')
    name = models.CharField('发货地名称', max_length=64, help_text='发货地名称', unique=True)
    desc = models.CharField('备注', max_length=64, help_text='备注', blank=True, default='')
    use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)

    class Meta:
        db_table = 'dispatch_location'
        verbose_name_plural = verbose_name = '发货地'


class DispatchLog(AbstractEntity):
    """发货履历"""
    STATUS_CHOICES = (
        (1, '完成'),
        (2, '撤销')
    )
    order_no = models.CharField(max_length=64, verbose_name='订单号', help_text='订单号')
    pallet_no = models.CharField(max_length=64, verbose_name='托盘号', help_text='托盘号')
    need_qty = models.PositiveIntegerField(verbose_name='需求数量', help_text='需求数量')
    need_weight = models.DecimalField(verbose_name='需求重量', help_text='需求重量', blank=True, null=True,
                                      decimal_places=2, max_digits=8)
    dispatch_type = models.CharField(max_length=64, verbose_name='发货类型', help_text='发货类型')
    material_no = models.CharField(max_length=64, verbose_name='物料编码', help_text='物料编码')
    quality_status = models.CharField(max_length=8, verbose_name='品质状态', help_text='品质状态')
    lot_no = models.CharField(max_length=64, verbose_name='lot_no', help_text='lot_no')
    order_type = models.CharField(max_length=64, verbose_name='订单类型', help_text='订单类型', null=True)
    status = models.PositiveIntegerField(verbose_name="发货状态", help_text="发货状态", choices=STATUS_CHOICES)
    qty = models.PositiveIntegerField(verbose_name='单托数量', help_text='单托数量', default=2)
    weight = models.DecimalField(verbose_name='单托重量', help_text='单托重量', decimal_places=2, max_digits=8)
    dispatch_location = models.CharField(max_length=64, verbose_name='目的地', help_text='目的地')
    dispatch_user = models.CharField(max_length=16, verbose_name='发货人', help_text='发货人')
    order_created_time = models.DateTimeField(verbose_name="订单创建时间", help_text="订单创建时间", auto_now_add=True)
    fin_time = models.DateTimeField(verbose_name='完成时间', help_text='完成时间', null=True, blank=True)

    class Meta:
        db_table = 'dispatch_log'
        verbose_name_plural = verbose_name = '发货履历'


class DispatchPlan(AbstractEntity):
    """发货计划"""
    STATUS_CHOICES = (
        (1, '完成'),
        (2, '执行中'),
        (3, '失败'),
        (4, '新建'),
        (5, '关闭')
    )

    order_no = models.CharField(max_length=64, verbose_name='订单号', help_text='订单号')
    need_qty = models.PositiveIntegerField(verbose_name='需求数量', help_text='需求数量')
    need_weight = models.DecimalField(verbose_name='需求重量', help_text='需求重量', blank=True, null=True, decimal_places=2,
                                      max_digits=8)
    material = models.ForeignKey(Material, verbose_name='物料编码', help_text='物料编码', on_delete=models.SET_NULL,
                                 blank=True, null=True)
    dispatch_type = models.ForeignKey(GlobalCode, verbose_name='发货类型', help_text='发货类型', on_delete=models.SET_NULL,
                                      blank=True, null=True)
    order_type = models.CharField(max_length=8, verbose_name='订单类型', help_text='订单类型', null=True)
    actual_qty = models.PositiveIntegerField(verbose_name='已发数量', help_text='已发数量', default=0)
    actual_weight = models.DecimalField(verbose_name='已发重量', help_text='已发重量', decimal_places=2,
                                        max_digits=8, default=0)
    status = models.PositiveIntegerField(verbose_name="状态", help_text="状态", choices=STATUS_CHOICES, default=4)
    qty = models.PositiveIntegerField(verbose_name='单托数量', help_text='单托数量', blank=True, null=True)
    dispatch_location = models.ForeignKey(DispatchLocation, verbose_name='目的地', help_text='目的地',
                                          on_delete=models.SET_NULL, blank=True, null=True)
    dispatch_user = models.CharField(max_length=16, verbose_name='发货人', help_text='发货人', null=True, blank=True)
    start_time = models.DateTimeField(verbose_name="发起时间", help_text="发起时间", auto_now_add=True)
    fin_time = models.DateTimeField(verbose_name='完成时间', help_text='完成时间', null=True, blank=True)

    class Meta:
        db_table = 'dispatch_plan'
        verbose_name_plural = verbose_name = '发货计划'


class MixGumOutInventoryLog(models.Model):
    """混炼胶库出库履历视图"""
    order_no = models.CharField(max_length=100, db_column='BILLID', primary_key=True, help_text='出库单号')
    pallet_no = models.CharField(max_length=50, db_column='PALLETID', help_text='托盘号')
    location = models.CharField(max_length=50, db_column='CID', help_text="货位地址")
    qty = models.DecimalField(max_digits=15, decimal_places=3, db_column='CarNum', help_text='数量')
    weight = models.DecimalField(max_digits=15, decimal_places=3, db_column='Weight', help_text='已发重量')
    quality_status = models.CharField(db_column='MStatus', max_length=6, help_text='品质状态')
    lot_no = models.CharField(max_length=100, db_column='Lot_no', null=True, blank=True)
    inout_num_type = models.CharField(max_length=50, db_column='OutType', help_text='出入库数类型')
    initiator = models.CharField(max_length=50, db_column='OutUser', help_text='发起人')
    material_no = models.CharField(max_length=100, db_column='MID', help_text='物料编码')
    start_time = models.DateTimeField(db_column='DEALTIME', help_text='发起时间')

    def warehouse_no(self):
        return "混炼胶库"

    # def inout_num_type(self):
    #     if self.out_num_type == "快检出库":
    #         return "指定出库"
    #     else:
    #         return "正常出库"

    def warehouse_name(self):
        return "混炼胶库"

    def material_name(self):
        return self.material_no

    def unit(self):
        return "kg"

    def order_type(self):
        return "出库"

    # TODO 这里可以搞几个map用来做映射
    def inout_reason(self):
        return self.inout_num_type

    def inventory_type(self):
        return self.inout_num_type


    class Meta:
        db_table = 'v_ASRS_TO_MES_RE_MESVIEW'
        managed = False


class MixGumInInventoryLog(models.Model):
    """混炼胶库入库履历视图"""
    order_no = models.CharField(max_length=50, db_column='BILLID', primary_key=True)
    pallet_no = models.CharField(max_length=50, db_column='PALLETID')
    location = models.CharField(max_length=50, db_column='CID', help_text="货位地址")
    qty = models.DecimalField(max_digits=15, decimal_places=3, db_column='NUM')
    weight = models.DecimalField(max_digits=15, decimal_places=3, db_column='SWEIGHT')
    quality_status = models.CharField(db_column='MSTATUS', max_length=50)
    lot_no = models.CharField(max_length=200, db_column='LotNo', null=True, blank=True)
    inout_num_type = models.CharField(max_length=20, db_column='IOCLASSNAME')
    material_no = models.CharField(max_length=50, db_column='MID')
    material_name = models.CharField(max_length=50, db_column='MATNAME')
    start_time = models.DateTimeField(db_column='LTIME')
    project_no = models.CharField(db_column='PROJECTNO', max_length=50, null=True, blank=True)
    class_id = models.BigIntegerField(db_column="IOCLASS_ID", null=True, blank=True)

    def warehouse_no(self):
        return "混炼胶库"

    def warehouse_name(self):
        return "混炼胶库"

    def unit(self):
        return "kg"

    def order_type(self):
        return "入库"

    def inventory_type(self):
        return self.inout_num_type

    def inout_reason(self):
        return self.inout_num_type

    def fin_time(self):
        return None

    class Meta:
        db_table = 'v_ASRS_LOG_IN_OPREATE_MESVIEW'
        managed = False


class InventoryLog(AbstractEntity):
    """混炼胶出入库履历"""
    warehouse_no = models.CharField(max_length=64, verbose_name='仓库编号', help_text='仓库编号')
    warehouse_name = models.CharField(max_length=64, verbose_name='仓库名称', help_text='仓库名称')
    order_no = models.CharField(max_length=64, verbose_name='订单号', help_text='订单号')
    pallet_no = models.CharField(max_length=64, verbose_name='托盘号', help_text='托盘号')
    location = models.CharField(max_length=64, verbose_name='货位地址', help_text='货位地址')
    station = models.CharField(max_length=64, verbose_name='出库口', help_text='出库口', null=True, blank=True)
    qty = models.PositiveIntegerField(verbose_name='数量', help_text='数量', blank=True, null=True)
    weight = models.DecimalField(verbose_name='重量', help_text='重量', blank=True, null=True, decimal_places=2,
                                 max_digits=8)
    material_no = models.CharField(max_length=64, verbose_name='物料编码', help_text='物料编码')
    quality_status = models.CharField(max_length=8, verbose_name='品质状态', help_text='品质状态')
    lot_no = models.CharField(max_length=64, verbose_name='lot_no', help_text='lot_no')
    order_type = models.CharField(max_length=64, verbose_name='订单类型', help_text='订单类型')
    inout_reason = models.CharField(max_length=64, verbose_name='出入库原因', help_text='出入库原因')
    inout_num_type = models.CharField(max_length=64, verbose_name='出入库数类型', help_text='出入库数类型')
    inventory_type = models.CharField(max_length=64, verbose_name='BZ出入库类型', help_text='BZ出入库数类型')  # 生产出库/快检异常出库
    unit = models.CharField(max_length=64, verbose_name='单位', help_text='单位')
    initiator = models.CharField(max_length=64, blank=True, null=True, verbose_name='发起人',
                                 help_text='发起人')
    start_time = models.DateTimeField('发起时间', blank=True, null=True, help_text='发起时间')
    fin_time = models.DateTimeField(verbose_name='完成时间', help_text='完成时间', auto_now_add=True)

    class Meta:
        db_table = 'inventory_log'
        verbose_name_plural = verbose_name = '出入库履历'


# class RubberInventoryLog(AbstractEntity):
#     """出入库履历"""
#     warehouse_no = models.CharField(max_length=64, verbose_name='仓库编号', help_text='仓库编号')
#     warehouse_name = models.CharField(max_length=64, verbose_name='仓库名称', help_text='仓库名称')
#     order_no = models.CharField(max_length=64, verbose_name='订单号', help_text='订单号')
#     pallet_no = models.CharField(max_length=64, verbose_name='托盘号', help_text='托盘号')
#     location = models.CharField(max_length=64, verbose_name='货位地址', help_text='货位地址')
#     qty = models.PositiveIntegerField(verbose_name='数量', help_text='数量', blank=True, null=True)
#     weight = models.DecimalField(verbose_name='重量', help_text='重量', blank=True, null=True, decimal_places=2,
#                                  max_digits=8)
#     material_no = models.CharField(max_length=64, verbose_name='物料编码', help_text='物料编码')
#     quality_status = models.CharField(max_length=8, verbose_name='品质状态', help_text='品质状态')
#     lot_no = models.CharField(max_length=64, verbose_name='lot_no', help_text='lot_no')
#     order_type = models.CharField(max_length=8, verbose_name='订单类型', help_text='订单类型')
#     classes = models.CharField(max_length=64, verbose_name='班次', help_text='班次')
#     equip_no = models.CharField(max_length=64, verbose_name='机台号', help_text='机台号')
#     io_location = models.CharField(max_length=64, verbose_name='出入库口', help_text='出入库口')
#     dst_location = models.CharField(max_length=64, verbose_name='目的地', help_text='目的地')
#     inout_reason = models.CharField(max_length=64, verbose_name='出入库原因', help_text='出入库原因')
#     inout_num_type = models.CharField(max_length=64, verbose_name='出入库数类型', help_text='出入库数类型')
#     inventory_type = models.CharField(max_length=64, verbose_name='BZ出入库类型', help_text='BZ出入库数类型')  # 生产出库/快检异常出库
#     unit = models.CharField(max_length=64, verbose_name='单位', help_text='单位')
#     initiator = models.CharField(max_length=64, blank=True, null=True, verbose_name='发起人',
#                                  help_text='发起人')
#     factory_date = models.DateTimeField('工厂日期', blank=True, null=True, help_text='工厂日期')
#     start_time = models.DateTimeField('发起时间', blank=True, null=True, help_text='发起时间')
#     fin_time = models.DateTimeField(verbose_name='完成时间', help_text='完成时间', auto_now_add=True)
#
#     class Meta:
#         db_table = 'rubber_inventory_log'
#         verbose_name_plural = verbose_name = '出入库履历'


#TODO
############原材料|炭黑共用抽象表########################################################################################################

class MaterialInventoryLog(AbstractEntity):
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
    material_name = models.CharField(max_length=64, verbose_name='物料名称', help_text='物料名称')
    quality_status = models.CharField(max_length=8, verbose_name='品质状态', help_text='品质状态')
    lot_no = models.CharField(max_length=64, verbose_name='lot_no', help_text='lot_no')
    order_type = models.CharField(max_length=8, verbose_name='订单类型', help_text='订单类型')
    # classes = models.CharField(max_length=64, verbose_name='班次', help_text='班次')
    # equip_no = models.CharField(max_length=64, verbose_name='机台号', help_text='机台号')
    station = models.CharField(max_length=64, verbose_name='出入库口', help_text='出入库口')
    dst_location = models.CharField(max_length=64, verbose_name='目的地', help_text='目的地', null=True, blank=True)
    inout_reason = models.CharField(max_length=64, verbose_name='出入库原因', help_text='出入库原因')
    inventory_type = models.CharField(max_length=64, verbose_name='出入库数类型', help_text='出入库数类型')
    unit = models.CharField(max_length=64, verbose_name='单位', help_text='单位')
    initiator = models.CharField(max_length=64, blank=True, null=True, verbose_name='发起人',
                                 help_text='发起人')
    start_time = models.DateTimeField(verbose_name='发起时间', blank=True, null=True, help_text='发起时间')
    fin_time = models.DateTimeField(verbose_name='完成时间', help_text='完成时间', auto_now_add=True)
    detail = models.CharField(max_length=255, verbose_name='任务详情', help_text='任务详情', blank=True)

    class Meta:
        db_table = 'material_inventory_log'
        verbose_name_plural = verbose_name = '出入库履历'


class MaterialInHistoryOther(models.Model):
    id = models.BigIntegerField(primary_key=True, db_column='Id')
    order_no = models.CharField(max_length=64, db_column='TaskNumber')
    initiator = models.CharField(max_length=64, db_column='LastUserId')
    start_time = models.DateTimeField(verbose_name='发起时间', help_text='发起时间', blank=True, null=True,
                                      db_column='CreaterTime')
    fin_time = models.DateTimeField(verbose_name='完成时间', help_text='完成时间', blank=True, null=True, db_column='LastTime')

    class Meta:
        db_table = 't_stock_in_task'
        managed = False


class MaterialInHistory(models.Model):
    """原材料入库记录"""
    id = models.BigIntegerField(primary_key=True, db_column='Id')
    batch_no = models.CharField(max_length=64, db_column="BatchNo")
    supplier = models.CharField(max_length=255, db_column="ContactCompanyName")
    order_no = models.CharField(max_length=64, db_column='TaskId')
    pallet_no = models.CharField(max_length=64, db_column='LadenToolNumber')
    location = models.CharField(max_length=64, db_column='SpaceId', help_text="货位地址")
    qty = models.DecimalField(max_digits=18, decimal_places=2, db_column='Quantity')
    weight = models.DecimalField(max_digits=18, decimal_places=2, db_column='WeightOfActual')
    unit = models.CharField(db_column='WeightUnit', max_length=50)
    lot_no = models.CharField(max_length=64, db_column='TrackingNumber', null=True, blank=True)
    inout_type = models.IntegerField(db_column='TaskType')
    material_no = models.CharField(max_length=64, db_column='MaterialCode')
    material_name = models.CharField(max_length=64, db_column='MaterialName')
    task = models.ForeignKey("MaterialInHistoryOther", on_delete=models.CASCADE, related_name="mih",
                             db_column="StockInTaskEntityId")
    sl = models.DecimalField(max_digits=18, decimal_places=4, db_column='SL')
    zl = models.DecimalField(max_digits=18, decimal_places=4, db_column='ZL')

    class Meta:
        db_table = 't_stock_in_task_upper'
        managed = False


class MaterialOutHistoryOther(models.Model):
    """原材料出库记录"""
    TASK_STATUS_CHOICE = (
        (1, '已创建'),
        (2, '等待出库'),
        (3, '出库中'),
        (4, '已出库'),
        (5, '异常出库'),
        (6, '取消'),
    )
    TASK_TYPE_CHOICE = (
        (1, '生产正常出库'),
        (2, 'mes指定库位出库'),
        (3, 'mes指定重量出库'),
        (4, '自主创建'),
    )
    id = models.BigIntegerField(primary_key=True, db_column='Id')
    order_no = models.CharField(max_length=64, db_column='TaskNumber')
    initiator = models.CharField(max_length=64, db_column='LastUserId',help_text='创建人')
    start_time = models.DateTimeField(verbose_name='创建时间', help_text='创建时间', blank=True, null=True,
                                      db_column='CreaterTime')
    fin_time = models.DateTimeField(verbose_name='完成时间', help_text='完成时间', blank=True, null=True, db_column='LastTime')
    task_type = models.IntegerField(db_column='StockOutTaskType', help_text='出库类型', choices=TASK_TYPE_CHOICE)
    task_status = models.IntegerField(db_column='StockOutTaskState', help_text='出库状态', choices=TASK_STATUS_CHOICE)

    class Meta:
        db_table = 't_stock_out_task'
        managed = False


class MaterialOutHistory(models.Model):
    """原材料出库记录"""
    id = models.BigIntegerField(primary_key=True, db_column='Id')
    batch_no = models.CharField(max_length=64, db_column="BatchNo", help_text='批次号')
    supplier = models.CharField(max_length=255, db_column="ContactCompanyName", help_text='供应商')
    order_no = models.CharField(max_length=64, db_column='TaskId', help_text='下架任务号')
    pallet_no = models.CharField(max_length=64, db_column='LadenToolNumber', help_text='托盘号')
    location = models.CharField(max_length=64, db_column='SpaceId', help_text="货位地址")
    qty = models.DecimalField(max_digits=18, decimal_places=2, db_column='Quantity', help_text='数量')
    weight = models.DecimalField(max_digits=18, decimal_places=2, db_column='WeightOfActual', help_text='重量')
    unit = models.CharField(db_column='WeightUnit', max_length=64, help_text='单位重量')
    lot_no = models.CharField(max_length=64, db_column='TrackingNumber', null=True, blank=True, help_text='追踪码')
    inout_type = models.IntegerField(db_column='TaskType', help_text='出库类型')
    material_no = models.CharField(max_length=64, db_column='MaterialCode', help_text='物料编码')
    material_name = models.CharField(max_length=64, db_column='MaterialName', help_text='物料名称')
    task = models.ForeignKey("MaterialOutHistoryOther", on_delete=models.CASCADE, related_name="moh",
                             db_column="StockOutTaskEntityId", help_text='出库单据ID')
    entrance = models.CharField(max_length=64, db_column='EntranceCode', help_text='出库口')
    task_status = models.IntegerField(db_column='TaskState', help_text='出库状态')
    standard_unit = models.CharField(max_length=64, db_column='StandardUnit', help_text='标准单位')
    piece_count = models.DecimalField(max_digits=18, decimal_places=2, db_column='PieceCount')
    zc_num = models.CharField(max_length=64, db_column='ZcdNumber')
    sl = models.DecimalField(max_digits=18, decimal_places=4, db_column='SL')
    zl = models.DecimalField(max_digits=18, decimal_places=4, db_column='ZL')

    class Meta:
        db_table = 't_stock_out_task_down'
        managed = False


class BarcodeQuality(models.Model):
    # material = models.OneToOneField(Material, related_name="barcode_quality", on_delete=models.CASCADE, null=True)
    # material_no = models.CharField(max_length=64, help_text="wms物料编码")
    # material_name = models.CharField(max_length=64, help_text="wms物料名称")
    # material_type = models.CharField(max_length=64, help_text="wms物料类型")
    lot_no = models.CharField(max_length=64, help_text="wms条码", primary_key=True)
    # container_no = models.CharField(max_length=64, help_text="托盘号")
    # qty = models.IntegerField()
    # total_weight = models.DecimalField(max_digits=5, decimal_places=3)
    quality_status = models.CharField(max_length=64, help_text="品质")

    # location = models.CharField(max_length=64, help_text="货位地址")

    class Meta:
        db_table = "barcode_quality"
        verbose_name_plural = verbose_name = '物料条码质量维护'


class MaterialEntrance(models.Model):
    code = models.CharField(max_length=64, db_column='EntranceCode')
    name = models.CharField(max_length=64, db_column='Name')

    class Meta:
        db_table = "t_inventory_entrance"
        managed = False


# by afeng
class FinalGumOutInventoryLog(models.Model):
    """终炼胶库出库履历视图"""
    order_no = models.CharField(max_length=100, db_column='BILLID', primary_key=True, help_text='出库单号')
    pallet_no = models.CharField(max_length=50, db_column='PALLETID', help_text='托盘号')
    location = models.CharField(max_length=50, db_column='CID', help_text="货位地址")
    qty = models.DecimalField(max_digits=15, decimal_places=3, db_column='CarNum', help_text='数量')
    weight = models.DecimalField(max_digits=15, decimal_places=3, db_column='Weight', help_text='已发重量')
    quality_status = models.CharField(db_column='MStatus', max_length=6, help_text='品质状态')
    lot_no = models.CharField(max_length=100, db_column='Lot_no', null=True, blank=True)
    inout_num_type = models.CharField(max_length=50, db_column='OutType', help_text='出入库数类型')
    initiator = models.CharField(max_length=50, db_column='OutUser', help_text='发起人')
    material_no = models.CharField(max_length=100, db_column='MID', help_text='物料编码')
    start_time = models.DateTimeField(db_column='DEALTIME', help_text='发起时间')

    def warehouse_no(self):
        return "终炼胶库"

    # def inout_num_type(self):
    #     if self.out_num_type == "快检出库":
    #         return "指定出库"
    #     else:
    #         return "正常出库"

    def warehouse_name(self):
        return "终炼胶库"

    def material_name(self):
        return self.material_no

    def unit(self):
        return "kg"

    def order_type(self):
        return "出库"

    # TODO 这里可以搞几个map用来做映射
    def inout_reason(self):
        return self.inout_num_type

    def inventory_type(self):
        return self.inout_num_type

    def fin_time(self):
        return None

    class Meta:
        db_table = 'v_ASRS_TO_MES_RE_MESVIEW'
        managed = False


class FinalGumInInventoryLog(models.Model):
    """终炼胶库入库履历视图"""
    order_no = models.CharField(max_length=50, db_column='BILLID', primary_key=True)
    pallet_no = models.CharField(max_length=50, db_column='PALLETID')
    location = models.CharField(max_length=50, db_column='CID', help_text="货位地址")
    qty = models.DecimalField(max_digits=15, decimal_places=3, db_column='Num')
    weight = models.DecimalField(max_digits=15, decimal_places=3, db_column='SWeight')
    quality_status = models.CharField(db_column='MStatus', max_length=50)
    lot_no = models.CharField(max_length=200, db_column='LotNo', null=True, blank=True)
    inout_num_type = models.CharField(max_length=20, db_column='IOCLASSNAME')
    material_no = models.CharField(max_length=50, db_column='MID')
    material_name = models.CharField(max_length=50, db_column='MATNAME')
    start_time = models.DateTimeField(db_column='LTIME')
    project_no = models.CharField(db_column='PROJECTNO', max_length=50, null=True, blank=True)
    class_id = models.BigIntegerField(db_column="IOCLASS_ID", null=True, blank=True)

    def warehouse_no(self):
        return "终炼胶库"

    def warehouse_name(self):
        return "终炼胶库"

    def unit(self):
        return "kg"

    def order_type(self):
        return "入库"

    def inventory_type(self):
        return self.inout_num_type

    def inout_reason(self):
        return self.inout_num_type

    def fin_time(self):
        return None

    class Meta:
        db_table = 'v_ASRS_LOG_IN_OPREATE_MESVIEW'
        managed = False


class Depot(models.Model):
    """线边库 库区表"""
    depot_name = models.CharField(max_length=64, help_text='库区名称', verbose_name='库区名称')
    description = models.CharField(max_length=64, help_text='库区描述', verbose_name='库区描述')
    is_use = models.BooleanField(help_text='是否删除', verbose_name='是否删除', default=True)

    def __str__(self):
        return self.depot_name

    class Meta:
        db_table = 'depot'
        verbose_name_plural = verbose_name = '库区'


class DepotSite(models.Model):
    """线边库 库位表"""
    depot_site_name = models.CharField(max_length=64, help_text='库位名称', verbose_name='库位名称')
    description = models.CharField(max_length=64, help_text='库位描述', verbose_name='库位描述')
    depot = models.ForeignKey(Depot, on_delete=models.CASCADE, related_name='depot')
    is_use = models.BooleanField(help_text='是否删除', verbose_name='是否删除', default=True)

    def __str__(self):
        return self.depot_site_name

    class Meta:
        db_table = 'depot_site'
        verbose_name_plural = verbose_name = '库位'

    @property
    def depot_name(self):
        return self.depot.depot_name


class DepotPallt(models.Model):
    """线边库 出入库数据"""
    status = (
        (1, '入库'),
        (2, '出库')
    )
    enter_time = models.DateTimeField(help_text='入库时间', verbose_name='入库时间', blank=True,null=True)
    outer_time = models.DateTimeField(help_text='出库时间', verbose_name='出库时间', blank=True,null=True)
    pallet_status = models.SmallIntegerField(choices=status, help_text='状态', verbose_name='状态', null=True, blank=True)
    depot_site = models.ForeignKey(DepotSite, on_delete=models.CASCADE, related_name='depotsite', help_text='库位', verbose_name='库位')
    pallet_data = models.OneToOneField(PalletFeedbacks, on_delete=models.CASCADE, related_name='palletfeedbacks',
                                       help_text='托盘', verbose_name='托盘')

    class Meta:
        db_table = 'depot_pallet'
        verbose_name_plural = verbose_name = '线边库数据'

    @property
    def depot_name(self):
        return self.depot_site.depot.depot_name

    @property
    def depot_site_name(self):
        return self.depot_site.depot_site_name

class SulfurDepot(models.Model):
    """硫磺 库区表"""
    depot_name = models.CharField(max_length=64, help_text='库区名称', verbose_name='库区名称')
    description = models.CharField(max_length=64, help_text='库区描述', verbose_name='库区描述')
    is_use = models.BooleanField(help_text='是否删除', verbose_name='是否删除', default=True)

    class Meta:
        db_table = 'sulfur_depot'
        verbose_name_plural = verbose_name = '库区'

    def __str__(self):
        return self.depot_name


class SulfurDepotSite(models.Model):
    """硫磺库 库位表"""
    depot_site_name = models.CharField(max_length=64, help_text='库位名称', verbose_name='库位名称')
    description = models.CharField(max_length=64, help_text='库位描述', verbose_name='库位描述')
    depot = models.ForeignKey(SulfurDepot, on_delete=models.CASCADE, related_name='sulfur_depot_site')
    is_use = models.BooleanField(help_text='是否删除', verbose_name='是否删除', default=True)

    class Meta:
        db_table = 'sulfur_depot_site'
        verbose_name_plural = verbose_name = '库位'

    def __str__(self):
        return self.depot_site_name


class Sulfur(models.Model):
    """硫磺数据"""
    name = models.CharField(max_length=64, help_text='硫磺名称', verbose_name='硫磺名称')
    product_no = models.CharField(max_length=64, help_text='物料编码', verbose_name='物料编码')
    provider = models.CharField(max_length=64, help_text='供应商', verbose_name='供应商')
    lot_no = models.CharField(max_length=64, help_text='批号', verbose_name='批号')
    num = models.IntegerField(help_text='数量(包)', verbose_name='数量(包)', default=1)
    weight = models.DecimalField(max_digits=15, decimal_places=3, help_text='重量', verbose_name='重量')
    status = (
        (1, '入库'),
        (2, '出库')
    )
    sulfur_status = models.SmallIntegerField(choices=status, help_text='状态', verbose_name='状态', null=True, blank=True)
    enter_time = models.DateTimeField(help_text='入库时间', verbose_name='入库时间', blank=True,null=True)
    outer_time = models.DateTimeField(help_text='出库时间', verbose_name='出库时间', blank=True,null=True)
    depot_site = models.ForeignKey(SulfurDepotSite, on_delete=models.CASCADE, related_name='sulfur', help_text='库位', verbose_name='库位')

    class Meta:
        db_table = 'sulfur'
        verbose_name_plural = verbose_name = '硫磺数据'

    def __str__(self):
        return self.name

    @property
    def depot_name(self):
        return self.depot_site.depot.depot_name

    @property
    def depot_site_name(self):
        return self.depot_site.depot_site_name


class WMSReleaseLog(AbstractEntity):
    tracking_num = models.CharField(max_length=128, help_text='追踪码')
    operation_type = models.CharField(max_length=10, help_text='放行/合格')

    class Meta:
        db_table = 'wms_release_log'
        verbose_name_plural = verbose_name = '原材料立库放行记录'


class WMSExceptHandle(AbstractEntity):
    material_code = models.CharField(max_length=128, help_text='物料编码')
    lot_no = models.CharField(max_length=64, help_text='质检条码', null=True, blank=True)
    batch_no = models.CharField(max_length=64, help_text='批次号', null=True, blank=True)
    num = models.IntegerField(help_text='处理次数', default=1)
    result = models.CharField(max_length=10, help_text='放行/不放行', null=True, blank=True)
    except_reason = models.TextField(help_text='异常处理说明', null=True, blank=True)
    quality_status = models.CharField(max_length=10, help_text='不合格/待检品/合格')
    status = models.CharField(max_length=12, help_text='异常处理/设定合格', default='异常处理')

    class Meta:
        db_table = 'wms_except_handle'
        verbose_name_plural = verbose_name = '原材料异常处理记录'


class WmsNucleinManagement(AbstractEntity):
    material_no = models.CharField(max_length=128, help_text="wms物料编码")
    material_name = models.CharField(max_length=128, help_text="wms物料名称")
    zc_material_code = models.CharField(max_length=128, help_text='中策物料编码', blank=True, null=True)
    batch_no = models.CharField(max_length=128, help_text='批次号', db_index=True)
    locked_status = models.CharField(max_length=8, help_text='状态（已锁定/已解锁）', default='已锁定')

    class Meta:
        db_table = 'wms_nuclein_management'
        verbose_name_plural = verbose_name = '原材料核酸管控'


class WMSMaterialSafetySettings(AbstractEntity):
    TYPE_CHOICE = (
        (1, '日均用量计算值（吨）'),
        (2, '日均用量设定值（吨）')
    )
    type = models.IntegerField(help_text='设定类别', choices=TYPE_CHOICE, default=1)
    avg_consuming_weight = models.FloatField(help_text='日均用量计算值（kg）', default=0)
    avg_setting_weight = models.FloatField(help_text='日均用量设定值（kg）', default=0)
    wms_material_code = models.CharField(max_length=128, help_text='WMS物料编码')
    warning_days = models.FloatField(help_text='预警天数', default=0)
    warning_weight = models.FloatField(help_text='预警重量（kg）', default=0)

    def save(self, *args, **kwargs):
        if self.type == 1:
            self.warning_weight = self.avg_consuming_weight * self.warning_days
        else:
            self.warning_weight = self.avg_setting_weight * self.warning_days
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'wms_material_safety'
        verbose_name_plural = verbose_name = '原材料立库安全预警设置'


class ProductStockDailySummary(models.Model):
    factory_date = models.DateField(help_text='日期')
    product_no = models.CharField(max_length=64, help_text='胶料名称')
    stock_weight = models.FloatField(help_text='库内库存重量', default=0)
    area_weight = models.FloatField(help_text='现场库存重量', default=0)
    stage = models.CharField(max_length=64, help_text='段次', blank=True, null=True)
    # recipe_no = models.CharField(max_length=64, help_text='配方名称', blank=True, null=True)

    class Meta:
        db_table = 'product_stock_daily_summary'
        verbose_name_plural = verbose_name = '胶片库存每日统计'


class MaterialOutboundOrder(models.Model):
    order_type = models.IntegerField(help_text='出库类型 1：原材料 2：炭黑库', db_index=True)
    order_no = models.CharField(max_length=128, help_text='订单编号', db_index=True)
    created_date = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    created_username = models.CharField(max_length=128, help_text='创建人')

    class Meta:
        db_table = 'material_outbound_order'
        verbose_name_plural = verbose_name = '胶片库存每日统计'


class HfBakeMaterialSet(models.Model):
    material_name = models.CharField(max_length=128, help_text='原材料名称', unique=True)
    temperature_set = models.IntegerField(help_text='烘烤温度[0-100]')
    bake_time = models.DecimalField(max_digits=4, decimal_places=1, help_text='烘烤时长[0.0-200.0]')
    delete_flag = models.BooleanField(default=False, help_text='物料是否删除')
    created_date = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    opera_username = models.CharField(max_length=16, help_text='操作人')
    last_updated_date = models.DateTimeField(verbose_name='创建时间', auto_now=True)

    class Meta:
        db_table = 'hf_bake_material_set'
        verbose_name_plural = verbose_name = '原材料烘烤温度以及时长设置'


class HfBakeLog(models.Model):
    oast_no = models.CharField(max_length=8, help_text='烘箱编号')
    material_name = models.CharField(max_length=512, help_text='烘烤物料')
    temperature_set = models.IntegerField(help_text='设定烘烤温度', null=True, blank=True)
    bake_time = models.DecimalField(max_digits=4, decimal_places=1, help_text='设定烘烤时长', null=True, blank=True)
    actual_temperature = models.IntegerField(help_text='实际烘烤温度', null=True, blank=True)
    actual_bake_time = models.CharField(max_length=16, help_text='实际烘烤时长', null=True, blank=True)
    created_date = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    opera_username = models.CharField(max_length=16, help_text='操作人')
    last_updated_date = models.DateTimeField(verbose_name='创建时间', auto_now=True)

    class Meta:
        db_table = 'hf_bake_log'
        verbose_name_plural = verbose_name = '烘房烘烤履历'


class WMSOutboundHistory(models.Model):
    QUALITY_STATUS_CHOICE = (
        ('合格品', '合格品'),
        ('抽检中', '抽检中'),
        ('不合格品', '不合格品'),
        ('过期', '过期'),
        ('待检', '待检'),
    )
    task_no = models.CharField(max_length=128, help_text='出库单号', unique=True)
    quality_status = models.CharField(max_length=8, help_text='立库品质状态', choices=QUALITY_STATUS_CHOICE)
    mes_test_result = models.CharField(max_length=8, help_text='MES检测结果(合格/不合格/未检测)')
    zc_test_result = models.CharField(max_length=8, help_text='总厂检测结果(合格/不合格/待检/未知)')
    hs_status = models.CharField(max_length=8, help_text='核酸管控结果(已锁定/已解锁/未锁定)')
    mooney_value = models.IntegerField(help_text='门尼检测值', blank=True, null=True)
    mooney_level = models.CharField(max_length=8, help_text='门尼等级(高门尼/标准门尼/低门尼)', blank=True, null=True)

    class Meta:
        db_table = 'wms_outbond_history'
        verbose_name_plural = verbose_name = 'wms出库记录'
