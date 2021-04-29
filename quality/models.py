from django.db import models

# Create your models here.
from basics.models import GlobalCode
from recipe.models import Material
from system.models import AbstractEntity, User


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


# 统计用中间表 BatchYear BatchMonth BatchDay Batch Lot Train Indicator TestDataPoint TestResult

class BatchYear(models.Model):
    """统计用中间表 add by fq   年批次"""
    date = models.DateField()  # 只有年月 月为当年第一月


class BatchMonth(models.Model):
    """统计用中间表 add by fq   月批次"""
    date = models.DateField()  # 只有年月 日为当月第一天


class BatchDay(models.Model):
    """统计用中间表 add by fq   日批次"""
    date = models.DateField()


class BatchEquip(models.Model):
    production_equip_no = models.CharField(max_length=64, help_text='机台')


class BatchClass(models.Model):
    production_class = models.CharField(max_length=64, help_text='生产班次名')


class BatchProductNo(models.Model):
    product_no = models.CharField(max_length=64, help_text='胶料编码')


class Batch(models.Model):
    """统计用中间表 add by fq   一批次"""
    production_factory_date = models.DateField(help_text='工厂日期')
    batch_year = models.ForeignKey(BatchYear, on_delete=models.SET_NULL, null=True, blank=True)
    batch_month = models.ForeignKey(BatchMonth, on_delete=models.SET_NULL, null=True, blank=True)
    batch_day = models.ForeignKey(BatchDay, on_delete=models.SET_NULL, null=True, blank=True)
    batch_equip = models.ForeignKey(BatchEquip, on_delete=models.SET_NULL, null=True, blank=True)
    batch_class = models.ForeignKey(BatchClass, on_delete=models.SET_NULL, null=True, blank=True)
    batch_product_no = models.ForeignKey(BatchProductNo, on_delete=models.SET_NULL, null=True, blank=True)


class Lot(models.Model):
    """统计用中间表 add by fq   一拖胶"""
    lot_no = models.CharField('收皮条码', max_length=64, help_text='收皮条码')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True)


class Train(models.Model):
    """统计用中间表 add by fq   一车胶"""
    lot = models.ForeignKey(Lot, on_delete=models.SET_NULL, null=True, blank=True)
    actual_trains = models.PositiveIntegerField('车次')


class Indicator(models.Model):
    """统计用中间表 add by fq"""
    name = models.CharField('检测指标名称', max_length=64)


class TestDataPoint(models.Model):
    """统计用中间表 add by fq"""
    name = models.CharField('数据点名称', max_length=64)
    indicator = models.ForeignKey(Indicator, on_delete=models.SET_NULL, null=True, blank=True)
    data_point_indicator = models.ForeignKey(MaterialDataPointIndicator, help_text='数据评判指标id', on_delete=models.CASCADE,
                                             blank=True, null=True)


class TestResult(models.Model):
    """统计用中间表 add by fq   测试结果"""
    train = models.ForeignKey(Train, on_delete=models.CASCADE)
    max_times = models.PositiveIntegerField(help_text='检验次数', default=0)
    point = models.ForeignKey(TestDataPoint, on_delete=models.SET_NULL, null=True, blank=True)
    qualified = models.NullBooleanField(max_length=64, default=None)
    value = models.DecimalField(help_text='检测值', decimal_places=2, max_digits=8, null=True, blank=True)


# 统计用中间表结束


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
    production_factory_date = models.DateField(help_text='工厂日期')
    note = models.TextField(max_length=100, help_text='备注', blank=True, null=True)
    is_qualified = models.BooleanField(help_text='是否合格', default=True)

    class Meta:
        db_table = 'material_test_order'
        verbose_name_plural = verbose_name = '物料检测单'


class MaterialTestResult(AbstractEntity):
    """检测结果"""
    ORIGIN_CHOICE = (
        (0, '手工录入'),
        (1, '10.4.23.140'),
        (2, '10.4.23.141'),
    )
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
    machine_name = models.CharField(max_length=64, help_text='试验机台名称', blank=True, null=True)
    level = models.IntegerField(help_text='等级', blank=True, null=True)
    origin = models.IntegerField(help_text='数据来源', default=0)

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
        ("已处理", "已处理"),
        ("复测", "复测"),
    )
    CHOICE1 = (
        (1, "成功"),
        (2, "失败"),
        (3, "库存、线边库都没有"),
        (4, "创建"),
    )
    lot_no = models.CharField(max_length=64, help_text='托盘追踪号')
    level = models.IntegerField(help_text='综合等级')
    deal_opinion = models.ForeignKey("DealSuggestion", help_text='综合处理意见id',
                                     on_delete=models.CASCADE, related_name='deal_opinions', blank=True, null=True)
    test_result = models.CharField(max_length=64, help_text="综合检测结果")
    reason = models.TextField(help_text="不合格原因")
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
    test_time = models.PositiveIntegerField(help_text='检测次数', null=True)
    update_store_test_flag = models.IntegerField(help_text='更新立库检测结果标志', choices=CHOICE1, default=4)  # 是否重新发起更新结果

    class Meta:
        db_table = 'material_deal_result'
        verbose_name_plural = verbose_name = '胶料处理结果'


class LevelResult(AbstractEntity):
    """等级和结果"""
    deal_result = models.CharField(max_length=64, help_text="检测结果")
    level = models.PositiveIntegerField(help_text='等级')

    class Meta:
        unique_together = ('deal_result', 'level')
        db_table = 'level_result'
        verbose_name_plural = verbose_name = '等级和结果'


class LabelPrint(models.Model):
    """标签打印对列表"""
    TYPE_CHOICE = (
        (1, "收皮"),
        (2, "快检"),
        (3, "混炼一层前端"),
        (4, "混炼一层后端"),
        (5, "混炼二层前端"),
        (6, "混炼二层后端"),
        (7, "炼胶#出库口#1"),
        (8, "炼胶#出库口#2"),
        (9, "炼胶#出库口#3"),
        (10, "帘布#出库口#0"),
    )
    STATUS_CHOICE = (
        (0, '未打印'),
        (1, '已打印')
    )
    label_type = models.PositiveIntegerField(help_text="标签类型", choices=TYPE_CHOICE, verbose_name="标签类型")
    lot_no = models.CharField(max_length=64, help_text="追踪条码", verbose_name="追踪条码")
    status = models.IntegerField(help_text='打印状态', choices=STATUS_CHOICE, verbose_name='打印状态')
    data = models.TextField(help_text="标签数据json集", verbose_name="标签数据json集")

    def __str__(self):
        return self.lot_no

    class Meta:
        db_table = 'label_print'
        verbose_name_plural = verbose_name = '标签打印'


class UnqualifiedDealOrder(AbstractEntity):
    """不合格处置单"""
    unqualified_deal_order_uid = models.CharField(max_length=64, help_text='唯一码')
    department = models.CharField(max_length=64, help_text='发生部门', blank=True, null=True)
    deal_department = models.CharField(max_length=64, help_text='部门', blank=True, null=True)
    status = models.CharField(max_length=64, help_text='状态', blank=True, null=True)
    deal_user = models.CharField(max_length=64, help_text='经办人', blank=True, null=True)
    deal_date = models.DateField(max_length=64, help_text='经办日期', blank=True, null=True)
    reason = models.TextField(help_text='原因', blank=True, null=True)
    t_deal_suggestion = models.TextField(help_text='技术部门处理意见', blank=True, null=True)
    c_deal_suggestion = models.TextField(help_text='检查部门处理意见', blank=True, null=True)
    t_deal_user = models.CharField(max_length=64, help_text='技术部门处理人', blank=True, null=True)
    t_deal_date = models.DateField(help_text='技术日期', blank=True, null=True)
    c_deal_user = models.CharField(max_length=64, help_text='检查部门处理人', blank=True, null=True)
    c_deal_date = models.DateField(help_text='检查日期', blank=True, null=True)
    desc = models.TextField(help_text='描述', blank=True, null=True)

    class Meta:
        db_table = 'unqualified_deal_order'
        verbose_name_plural = verbose_name = '不合格处置单'


class UnqualifiedDealOrderDetail(AbstractEntity):
    unqualified_deal_order = models.ForeignKey(UnqualifiedDealOrder, help_text='处置单',
                                               on_delete=models.CASCADE, related_name='deal_details')
    unqualified_deal_order_detail_uid = models.CharField(max_length=64, help_text='唯一码')
    material_test_order = models.OneToOneField(MaterialTestOrder, help_text='物料检测单',
                                               on_delete=models.CASCADE, related_name='unqualified_order')

    class Meta:
        db_table = 'unqualified_deal_order_detail'
        verbose_name_plural = verbose_name = '不合格处置单详情'


"""
    原料检测
"""


class TestIndicatorRaw(AbstractEntity):
    """检测指标"""
    no = models.CharField(max_length=64, help_text='指标编号', unique=True)
    name = models.CharField(max_length=64, help_text='指标名称', unique=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'test_indicator_raw'
        verbose_name_plural = verbose_name = '原料检测指标'


class TestTypeRaw(AbstractEntity):
    """原料试验类型"""
    no = models.CharField(max_length=64, help_text='类型编号', unique=True)
    name = models.CharField(max_length=64, help_text='类型名称', unique=True)
    test_indicator = models.ForeignKey(TestIndicatorRaw, help_text='检测指标',
                                       on_delete=models.CASCADE, related_name='indicator_types_raw')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'test_type_raw'
        verbose_name_plural = verbose_name = '原料试验类型'


class DataPointRaw(AbstractEntity):
    """原料数据点"""
    no = models.CharField(max_length=64, help_text='数据点编号', unique=True)
    name = models.CharField(max_length=64, help_text='数据点名称')
    unit = models.CharField(max_length=64, help_text='单位')
    test_type = models.ForeignKey(TestTypeRaw, help_text='试验类型', on_delete=models.CASCADE,
                                  related_name='type_points_raw')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'data_point_raw'
        verbose_name_plural = verbose_name = '原料数据点'
        unique_together = ('name', 'test_type')


class TestMethodRaw(AbstractEntity):
    """原料试验方法"""
    no = models.CharField(max_length=64, help_text='试验方法编号', unique=True)
    name = models.CharField(max_length=64, help_text='试验方法名称', unique=True)
    test_type = models.ForeignKey(TestTypeRaw, help_text='试验类型', on_delete=models.CASCADE,
                                  related_name='type_methods_raw')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'test_method_raw'
        verbose_name_plural = verbose_name = '原料试验方法'


class MaterialTestMethodRaw(AbstractEntity):
    """原料物料试验方法"""
    material = models.ForeignKey(Material, help_text='原材料', on_delete=models.CASCADE, related_name='mat_methods_raw')
    test_method = models.ForeignKey(TestMethodRaw, help_text='试验方法', on_delete=models.CASCADE)
    data_point = models.ManyToManyField(DataPointRaw, help_text='数据点', related_name='point_methods_raw')

    def __str__(self):
        return self.test_method.name

    class Meta:
        db_table = 'material_test_methods_raw'
        verbose_name_plural = verbose_name = '原料物料试验方法'
        unique_together = ('material', 'test_method')


class MaterialDataPointIndicatorRaw(AbstractEntity):
    """原料数据点评判指标"""
    material_test_method = models.ForeignKey(MaterialTestMethodRaw, help_text='物料试验方法',
                                             on_delete=models.CASCADE, related_name='mat_indicators_raw')
    data_point = models.ForeignKey(DataPointRaw, help_text='数据点', on_delete=models.CASCADE,
                                   related_name='point_indicators_raw')
    level = models.PositiveIntegerField(help_text='等级')
    result = models.CharField(max_length=64, help_text='结果')
    upper_limit = models.DecimalField(help_text='上限', decimal_places=2, max_digits=8)
    lower_limit = models.DecimalField(help_text='下限', decimal_places=2, max_digits=8)

    def __str__(self):
        return '{}-{}'.format(self.material_test_method, self.level)

    class Meta:
        db_table = 'material_data_indicator_raw'
        verbose_name_plural = verbose_name = '原料数据点评判指标'


class LevelResultRaw(AbstractEntity):
    """原料等级和结果"""
    deal_result = models.CharField(max_length=64, help_text="检测结果")
    level = models.PositiveIntegerField(help_text='等级')

    class Meta:
        unique_together = ('deal_result', 'level')
        db_table = 'level_result_raw'
        verbose_name_plural = verbose_name = '原料等级和结果'


class MaterialTestOrderRaw(AbstractEntity):
    lot_no = models.CharField(max_length=64, help_text='条形码')
    material = models.ForeignKey(Material, help_text='原材料', on_delete=models.CASCADE)
    batch_no = models.CharField(max_length=64, help_text='批次号', blank=True, null=True)
    storage_date = models.DateField(help_text='入库日期')
    is_qualified = models.BooleanField(help_text='是否合格', default=True)
    supplier_name = models.CharField(max_length=64, help_text='厂家信息', blank=True, null=True)

    class Meta:
        db_table = 'material_test_order_raw'
        verbose_name_plural = verbose_name = '原料检测单'


class MaterialTestResultRaw(AbstractEntity):
    """检测结果"""
    material_test_order = models.ForeignKey(MaterialTestOrderRaw, help_text='物料检测单', on_delete=models.CASCADE,
                                            related_name='order_results_raw')
    data_point_indicator = models.ForeignKey(MaterialDataPointIndicatorRaw, help_text='数据评判指标id',
                                             on_delete=models.CASCADE, null=True)
    value = models.DecimalField(help_text='检测值', decimal_places=2, max_digits=8)
    test_times = models.PositiveIntegerField(help_text='检验次数')
    data_point = models.ForeignKey(DataPointRaw, help_text='数据点', on_delete=models.CASCADE,
                                   related_name='result_points_raw')
    test_method = models.ForeignKey(TestMethodRaw, help_text='试验方法', on_delete=models.CASCADE,
                                    related_name='method_points_raw')
    level = models.PositiveIntegerField(help_text='等级')
    result = models.CharField(max_length=64, help_text='检测结果')

    class Meta:
        db_table = 'material_test_result_raw'
        verbose_name_plural = verbose_name = '检测结果'


class UnqualifiedMaterialDealResult(models.Model):
    STATUS_CHOICE = (
        (1, '待处理'),
        (2, '待确认'),
        (3, '已处理'),
        (4, '驳回'),
    )
    material_test_order_raw = models.OneToOneField(MaterialTestOrderRaw, on_delete=models.CASCADE,
                                                   related_name='deal_result')
    unqualified_reason = models.CharField(max_length=256, help_text='不合格原因', blank=True, null=True)
    status = models.PositiveIntegerField(help_text='状态', default=1, choices=STATUS_CHOICE)
    release_result = models.CharField(max_length=64, help_text='放行处理', blank=True, null=True)
    unqualified_result = models.CharField(max_length=64, help_text='不合格处理', blank=True, null=True)
    deal_user = models.ForeignKey(User, help_text='处理人', blank=True, null=True, on_delete=models.CASCADE,
                                  related_name='deal_user_result')
    confirm_user = models.ForeignKey(User, help_text='确认人', blank=True, null=True, on_delete=models.CASCADE,
                                     related_name='confirm_user_result')
    is_delivery = models.BooleanField(help_text='是否出库', default=False)

    class Meta:
        db_table = 'unqualified_material_deal_result'
        verbose_name_plural = verbose_name = '不合格处理结果'