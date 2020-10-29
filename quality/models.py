from django.db import models

# Create your models here.
from basics.models import GlobalCode
from recipe.models import Material
from system.models import AbstractEntity


class TestIndicator(AbstractEntity):
    """检测指标"""
    no = models.CharField(max_length=64, help_text='指标编号', unique=True)
    name = models.CharField(max_length=64, help_text='指标名称', unique=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'test_indicator'
        verbose_name_plural = verbose_name = '检测指标'


class TestType(AbstractEntity):
    """试验类型"""
    no = models.CharField(max_length=64, help_text='类型编号', unique=True)
    name = models.CharField(max_length=64, help_text='类型名称', unique=True)
    test_indicator = models.ForeignKey(TestIndicator, help_text='检测指标',
                                       on_delete=models.CASCADE, related_name='indicator_types')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'test_type'
        verbose_name_plural = verbose_name = '试验类型'


class DataPoint(AbstractEntity):
    no = models.CharField(max_length=64, help_text='数据点编号', unique=True)
    name = models.CharField(max_length=64, help_text='数据点名称')
    unit = models.CharField(max_length=64, help_text='单位')
    test_type = models.ForeignKey(TestType, help_text='试验类型', on_delete=models.CASCADE, related_name='type_points')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'data_point'
        verbose_name_plural = verbose_name = '数据点'
        unique_together = ('name', 'test_type')


class TestMethod(AbstractEntity):
    """试验方法"""
    no = models.CharField(max_length=64, help_text='试验方法编号', unique=True)
    name = models.CharField(max_length=64, help_text='试验方法名称', unique=True)
    test_type = models.ForeignKey(TestType, help_text='试验类型', on_delete=models.CASCADE, related_name='type_methods')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'test_method'
        verbose_name_plural = verbose_name = '试验方法'


class MaterialTestMethod(AbstractEntity):
    """物料试验方法"""
    material = models.ForeignKey(Material, help_text='原材料', on_delete=models.CASCADE, related_name='mat_methods')
    test_method = models.ForeignKey(TestMethod, help_text='试验方法', on_delete=models.CASCADE)
    data_point = models.ManyToManyField(DataPoint, help_text='数据点', related_name='point_methods')

    def __str__(self):
        return self.test_method.name

    class Meta:
        db_table = 'material_test_methods'
        verbose_name_plural = verbose_name = '物料试验方法'
        unique_together = ('material', 'test_method')


class MaterialDataPointIndicator(AbstractEntity):
    """数据点评判指标"""
    material_test_method = models.ForeignKey(MaterialTestMethod, help_text='物料试验方法',
                                             on_delete=models.CASCADE, related_name='mat_indicators')
    data_point = models.ForeignKey(DataPoint, help_text='数据点', on_delete=models.CASCADE,
                                   related_name='point_indicators')
    level = models.PositiveIntegerField(help_text='等级')
    result = models.CharField(max_length=64, help_text='结果')
    upper_limit = models.DecimalField(help_text='上限', decimal_places=2, max_digits=8)
    lower_limit = models.DecimalField(help_text='下限', decimal_places=2, max_digits=8)

    def __str__(self):
        return '{}-{}'.format(self.material_test_method, self.level)

    class Meta:
        db_table = 'material_data_indicator'
        verbose_name_plural = verbose_name = '数据点评判指标'


class MaterialTestOrder(AbstractEntity):
    """物料检测单"""
    lot_no = models.CharField(max_length=64, help_text='收皮条码')
    material_test_order_uid = models.CharField(max_length=64, help_text='唯一码', unique=True)
    actual_trains = models.PositiveIntegerField(help_text='车次')
    product_no = models.CharField(max_length=64, help_text='胶料编码')
    plan_classes_uid = models.CharField(max_length=64, help_text='班次计划唯一码')
    production_class = models.CharField(max_length=64, help_text='生产班次名')
    production_group = models.CharField(max_length=64, help_text='生产班组名')
    production_equip_no = models.CharField(max_length=64, help_text='机台')
    production_factory_date = models.DateTimeField(help_text='生产时间')
    note = models.TextField(max_length=100, help_text='备注', blank=True, null=True)

    class Meta:
        db_table = 'material_test_order'
        verbose_name_plural = verbose_name = '物料检测单'


class MaterialTestResult(AbstractEntity):
    """检测结果"""
    data_point_indicator = models.ForeignKey(MaterialDataPointIndicator, help_text='数据评判指标id', on_delete=models.CASCADE,
                                             blank=True, null=True)
    material_test_order = models.ForeignKey(MaterialTestOrder, help_text='物料检测单', on_delete=models.CASCADE,
                                            related_name='order_results')
    test_factory_date = models.DateTimeField(help_text='检测时间')
    value = models.DecimalField(help_text='检测值', decimal_places=2, max_digits=8)
    test_class = models.CharField(max_length=64, help_text='检测班次', blank=True, null=True)
    test_group = models.CharField(max_length=64, help_text='检测班组', blank=True, null=True)
    test_times = models.PositiveIntegerField(help_text='检验次数')
    data_point_name = models.CharField(max_length=64, help_text='数据点名称')
    test_method_name = models.CharField(max_length=64, help_text='试验方法名称')
    test_indicator_name = models.CharField(max_length=64, help_text='检测指标名称')
    mes_result = models.CharField(max_length=64, help_text='mes评判结果', blank=True, null=True)
    result = models.CharField(max_length=64, help_text='快检系统评判结果', blank=True, null=True)

    class Meta:
        db_table = 'material_test_result'
        verbose_name_plural = verbose_name = '检测结果'


class DealSuggestion(AbstractEntity):
    """处理意见"""
    suggestion_desc = models.CharField(max_length=256, help_text="处理描述")
    deal_type = models.ForeignKey(GlobalCode, help_text="处理类型id",
                                  on_delete=models.CASCADE, related_name='deal_opinions')

    class Meta:
        db_table = 'deal_suggestion'
        verbose_name_plural = verbose_name = '处理意见'


class MaterialDealResult(AbstractEntity):
    """胶料处理结果"""
    CHOICE = (
        ("待处理", "待处理"),
        ("待确认", "待确认"),
        ("已处理", "已处理")
    )
    lot_no = models.CharField(max_length=64, help_text='托盘追踪号')
    level = models.IntegerField(help_text='综合等级')
    deal_opinion = models.ForeignKey("DealSuggestion", help_text='综合处理意见id',
                                     on_delete=models.CASCADE, related_name='deal_opinions', blank=True, null=True)
    test_result = models.CharField(max_length=64, help_text="综合检测结果")
    reason = models.CharField(max_length=64, help_text="不合格原因")
    status = models.CharField(max_length=16, help_text="状态", choices=CHOICE)
    deal_result = models.CharField(max_length=64, help_text="处理结果")
    deal_user = models.CharField(max_length=8, help_text="处理人", blank=True, null=True)
    confirm_user = models.CharField(max_length=8, help_text="确认人", blank=True, null=True)
    be_warehouse_out = models.BooleanField(help_text="是否需要出库", default=False)
    warehouse_out_time = models.DateTimeField(help_text="计划出库时间", blank=True, null=True)
    deal_time = models.DateTimeField(help_text="处理时间", blank=True, null=True)
    confirm_time = models.DateTimeField(help_text="确认时间", blank=True, null=True)
    deal_suggestion = models.CharField(max_length=256, help_text="综合处理意见")
    production_factory_date = models.DateTimeField(help_text='生产时间')
    print_time = models.DateTimeField(help_text='第一次打印时间', null=True)
    valid_time = models.IntegerField(help_text='有效时间', null=True)

    class Meta:
        db_table = 'material_deal_result'
        verbose_name_plural = verbose_name = '胶料处理结果'
