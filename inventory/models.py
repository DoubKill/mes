from django.db import models

# Create your models here.
from basics.models import GlobalCode


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


class WarehouseMaterial_type(models.Model):
    """仓库物料类型"""
    warehouse_info = models.ForeignKey(WarehouseInfo, on_delete=models.CASCADE, related_name="warehouse_material_types")
    material_type = models.OneToOneField(GlobalCode, on_delete=models.CASCADE)