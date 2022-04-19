import datetime

from django.db import models

# Create your models here.
from basics.models import GlobalCode, EquipCategoryAttribute, Equip
from recipe.models import Material
from system.models import AbstractEntity, User


class ZCKJConfig(models.Model):
    """中策诺甲快检数据库配置"""
    server = models.CharField(max_length=64, help_text='快检电脑ip地址')
    user = models.CharField(max_length=64, help_text='数据库用户名')
    password = models.CharField(max_length=64, help_text='数据库用户密码')
    name = models.CharField(max_length=64, help_text='数据库名称')
    use_flag = models.BooleanField(help_text='是否启用', default=True)

    def __str__(self):
        return self.server

    class Meta:
        db_table = 'zckj_config'
        verbose_name_plural = verbose_name = '中策诺甲快检数据库配置'


class SubMachine(models.Model):
    nj_machine = models.ForeignKey(ZCKJConfig, on_delete=models.CASCADE, related_name='sub_machines')
    max_rid = models.IntegerField(help_text='当前记录最大rid', default=1)
    nj_machine_no = models.CharField(max_length=64, help_text='诺甲系统设备编号')
    machine_no = models.CharField(max_length=64, help_text='MES设备编号')

    class Meta:
        db_table = 'zckj_sub_machine'
        verbose_name_plural = verbose_name = '中策诺甲机台数据'


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


class DataPointStandardError(AbstractEntity):
    """数据点判断误差"""
    TYPE_CHOICE = (
        (1, '闭区间'),
        (2, '开区间')
    )
    data_point = models.ForeignKey(DataPoint, help_text='数据点', on_delete=models.CASCADE,
                                   related_name='standard_errors')
    lower_value = models.DecimalField(decimal_places=2, max_digits=8, help_text='开始值')
    lv_type = models.PositiveIntegerField(help_text='开始值开闭合类型', choices=TYPE_CHOICE)
    upper_value = models.DecimalField(decimal_places=2, max_digits=8, help_text='结束值')
    uv_type = models.PositiveIntegerField(help_text='结束值开闭合类型', choices=TYPE_CHOICE)
    tracking_card = models.CharField(max_length=64, help_text='追踪卡')
    label = models.CharField(max_length=64, help_text='标志及处理')

    def __str__(self):
        return self.label

    class Meta:
        db_table = 'data_point_standard_error'
        verbose_name_plural = verbose_name = '数据点误差'


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
    is_judged = models.BooleanField(help_text='是否做为判定', default=True)
    is_print = models.BooleanField(help_text='是否做为判定', default=True)

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
    upper_limit = models.DecimalField(help_text='上限', decimal_places=3, max_digits=8)
    lower_limit = models.DecimalField(help_text='下限', decimal_places=3, max_digits=8)

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
    is_passed = models.BooleanField(help_text='是否通过pass章', default=False)

    class Meta:
        db_table = 'material_test_order'
        verbose_name_plural = verbose_name = '物料检测单'
        indexes = [models.Index(fields=['product_no']),
                   models.Index(fields=['lot_no']),
                   models.Index(fields=['production_factory_date']),
                   models.Index(fields=['production_equip_no'])]


class MaterialTestResult(AbstractEntity):
    """检测结果"""
    ORIGIN_CHOICE = (
        (0, '手工录入'),
        (1, '10.4.23.140'),
        (2, '10.4.23.141'),
    )
    data_point_indicator = models.ForeignKey(MaterialDataPointIndicator, help_text='数据评判指标id',
                                             on_delete=models.SET_NULL, blank=True, null=True)
    material_test_order = models.ForeignKey(MaterialTestOrder, help_text='物料检测单', on_delete=models.CASCADE,
                                            related_name='order_results')
    test_factory_date = models.DateTimeField(help_text='检测时间')
    value = models.DecimalField(help_text='检测值', decimal_places=3, max_digits=8)
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
    is_passed = models.BooleanField(help_text='是否通过pass章', default=False)
    pass_suggestion = models.CharField(max_length=64, help_text='pass意见', blank=True, null=True)
    is_judged = models.BooleanField(help_text='是否做为判定', default=True)

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
    level = models.IntegerField(help_text='综合等级，1为一等品，其他为三等品')
    deal_opinion = models.ForeignKey("DealSuggestion", help_text='综合处理意见id',
                                     on_delete=models.CASCADE, related_name='deal_opinions', blank=True, null=True)
    test_result = models.CharField(max_length=64, help_text="综合检测结果，一等品/三等品/PASS")
    reason = models.TextField(help_text="不合格原因")
    status = models.CharField(max_length=16, help_text="状态", choices=CHOICE)
    deal_result = models.CharField(max_length=64, help_text="处理结果，一等品/三等品")
    deal_user = models.CharField(max_length=64, help_text="处理人", blank=True, null=True)
    confirm_user = models.CharField(max_length=64, help_text="确认人", blank=True, null=True)
    be_warehouse_out = models.BooleanField(help_text="是否需要出库", default=False)
    warehouse_out_time = models.DateTimeField(help_text="计划出库时间", blank=True, null=True)
    deal_time = models.DateTimeField(help_text="处理时间", blank=True, null=True)
    confirm_time = models.DateTimeField(help_text="确认时间", blank=True, null=True)
    deal_suggestion = models.CharField(max_length=256, help_text="综合处理意见，合格/不合格/pass章处理意见")
    production_factory_date = models.DateTimeField(help_text='生产时间')
    print_time = models.DateTimeField(help_text='第一次打印时间', null=True)
    valid_time = models.IntegerField(help_text='有效时间', null=True)
    test_time = models.PositiveIntegerField(help_text='检测次数', null=True)
    update_store_test_flag = models.IntegerField(help_text='更新立库检测结果标志', choices=CHOICE1, default=4)  # 是否重新发起更新结果
    send_count = models.IntegerField(help_text='发送次数', default=0)
    product_no = models.CharField(max_length=64, help_text='产出胶料', verbose_name='产出胶料', null=True)
    classes = models.CharField(max_length=64, help_text='生产班次名', null=True)
    equip_no = models.CharField(max_length=64, help_text='机台', null=True)
    factory_date = models.DateField(help_text='工厂日期', null=True)
    is_deal = models.BooleanField(help_text='是否有过不合格处理', default=False)
    begin_trains = models.IntegerField(help_text='开始车次', verbose_name='开始车次', blank=True, null=True)
    end_trains = models.IntegerField(help_text='结束车次', verbose_name='结束车次', blank=True, null=True)

    class Meta:
        db_table = 'material_deal_result'
        verbose_name_plural = verbose_name = '胶料处理结果'
        indexes = [models.Index(fields=['factory_date']),
                   models.Index(fields=['equip_no']),
                   models.Index(fields=['classes']),
                   models.Index(fields=['product_no']),
                   models.Index(fields=['lot_no'])]


class LabelPrintLog(models.Model):
    result = models.ForeignKey(MaterialDealResult, on_delete=models.CASCADE, related_name='print_logs')
    location = models.CharField(max_length=64, help_text='打印位置', null=True)
    created_user = models.CharField(max_length=64, help_text='打印人', null=True)
    created_date = models.DateTimeField(verbose_name='打印时间', auto_now_add=True)

    class Meta:
        db_table = 'label_print_log'


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
        (3, "一层前端"),
        (4, "一层后端"),
        (5, "二层前端"),
        (6, "二层后端"),
        (7, "炼胶#出库口#1"),
        (8, "炼胶#出库口#2"),
        (9, "炼胶#出库口#3"),
        (10, "帘布#出库口#0"),
    )
    STATUS_CHOICE = (
        (0, '未打印'),
        (1, '已打印'),
        (2, '已下发')
    )
    label_type = models.PositiveIntegerField(help_text="标签类型", choices=TYPE_CHOICE, verbose_name="标签类型")
    lot_no = models.CharField(max_length=64, help_text="追踪条码", verbose_name="追踪条码")
    status = models.IntegerField(help_text='打印状态', choices=STATUS_CHOICE, verbose_name='打印状态')
    data = models.TextField(help_text="标签数据json集", verbose_name="标签数据json集")
    created_date = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    last_updated_date = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    def __str__(self):
        return self.lot_no

    class Meta:
        db_table = 'label_print'
        verbose_name_plural = verbose_name = '标签打印'


class QualifiedRangeDisplay(models.Model):
    """打印卡片显示合格区间配置"""
    is_showed = models.BooleanField()

    class Meta:
        db_table = 'qualified_range_display'
        verbose_name_plural = verbose_name = '合格区间显示'


class IgnoredProductInfo(AbstractEntity):
    """不做pass章的判定胶种"""
    product_no = models.CharField(max_length=64, help_text='胶料编码', verbose_name='胶料编码', unique=True)

    class Meta:
        db_table = 'ignored_product_info'
        verbose_name_plural = verbose_name = '不做pass章的判定胶种'


class UnqualifiedDealOrder(AbstractEntity):
    """不合格处置单"""
    unqualified_deal_order_uid = models.CharField(max_length=64, help_text='唯一码')
    department = models.CharField(max_length=64, help_text='发生部门', blank=True, null=True)
    deal_department = models.CharField(max_length=64, help_text='部门', blank=True, null=True)
    status = models.CharField(max_length=64, help_text='状态', blank=True, null=True)
    deal_user = models.CharField(max_length=64, help_text='经办人', blank=True, null=True)
    deal_date = models.DateField(help_text='经办日期', blank=True, null=True)
    reason = models.TextField(help_text='不合格情况', blank=True, null=True)
    t_deal_suggestion = models.TextField(help_text='技术部门处理意见', blank=True, null=True)
    c_deal_suggestion = models.TextField(help_text='检查部门处理意见', blank=True, null=True)
    t_deal_user = models.CharField(max_length=64, help_text='技术部门处理人', blank=True, null=True)
    t_deal_date = models.DateField(help_text='技术日期', blank=True, null=True)
    c_deal_user = models.CharField(max_length=64, help_text='检查部门处理人', blank=True, null=True)
    c_deal_date = models.DateField(help_text='检查日期', blank=True, null=True)
    c_agreed = models.NullBooleanField(help_text='检查科是否同意', default=None)
    desc = models.TextField(help_text='备注', blank=True, null=True)
    deal_method = models.CharField(max_length=64, help_text='处理方式', null=True)

    class Meta:
        db_table = 'unqualified_deal_order'
        verbose_name_plural = verbose_name = '不合格处置单'


class UnqualifiedDealOrderDetail(AbstractEntity):
    unqualified_deal_order = models.ForeignKey(UnqualifiedDealOrder, help_text='处置单',
                                               on_delete=models.CASCADE, related_name='deal_details')
    # unqualified_deal_order_detail_uid = models.CharField(max_length=64, help_text='唯一码')
    # material_test_order = models.OneToOneField(MaterialTestOrder, help_text='物料检测单',
    #                                            on_delete=models.CASCADE, related_name='unqualified_order')
    ordering = models.IntegerField(help_text='序号', null=True)
    lot_no = models.CharField(max_length=64, help_text='收皮条码', null=True)
    factory_date = models.DateField(help_text='工厂日期', null=True)
    equip_no = models.CharField(max_length=64, help_text='机台号', null=True)
    classes = models.CharField(max_length=64, help_text='班次', null=True)
    product_no = models.CharField(max_length=64, help_text='胶料名称', null=True)
    test_data = models.TextField(help_text='检测详情', null=True)
    is_release = models.NullBooleanField(help_text='是否放行', default=None)
    suggestion = models.CharField(max_length=100, help_text='处理结果', null=True)
    trains = models.CharField(max_length=64, help_text='车次', null=True)
    reason = models.CharField(max_length=200, help_text='不合格情况', null=True)

    class Meta:
        db_table = 'unqualified_deal_order_detail'
        verbose_name_plural = verbose_name = '不合格处置单详情'


class ProductReportEquip(AbstractEntity):
    """胶料快检上报设备"""
    STATUS_CHOICE = (
        (1, '正常'),
        (2, '异常'),
    )
    no = models.CharField(max_length=64, help_text='设备编号')
    ip = models.CharField(max_length=64, help_text='IP', unique=True)
    status = models.PositiveIntegerField(help_text='设备连接状态', choices=STATUS_CHOICE, default=1)
    test_indicator = models.ManyToManyField(TestIndicator, help_text='实验指标', related_name='test_indicator')

    class Meta:
        db_table = 'product_report_equip'
        verbose_name_plural = verbose_name = '胶料快检上报设备'


class ProductTestPlan(AbstractEntity):
    """检测计划"""
    STATUS_CHOICE = (
        (1, '待检测'),
        (2, '完成'),
        (4, '强制结束')
    )
    count = models.PositiveIntegerField(help_text='钢拔同一车次的检测次数(4/5)', default=4)
    plan_uid = models.CharField(max_length=64, help_text='计划编码')
    test_equip = models.ForeignKey(ProductReportEquip, on_delete=models.CASCADE, help_text='检测机台',
                                      related_name="product_test_plan")
    test_time = models.DateTimeField(help_text='检测时间')
    test_classes = models.CharField(max_length=64, help_text='检测班次')
    test_group = models.CharField(max_length=64, help_text='检测班组')
    test_user = models.CharField(max_length=64, help_text='检测人员')
    test_indicator_name = models.CharField(max_length=64, help_text='检测指标名称')
    test_method_name = models.CharField(max_length=64, help_text='试验方法名称')
    test_times = models.PositiveIntegerField(help_text='检验次数', default=1)
    test_interval = models.PositiveIntegerField(help_text='检验间隔', default=1)
    status = models.PositiveIntegerField(help_text='状态', choices=STATUS_CHOICE, default=1)

    class Meta:
        db_table = 'product_test_plan'
        verbose_name_plural = verbose_name = '胶料快检计划'


class ProductTestPlanDetail(models.Model):
    """检测计划详情"""
    STATUS_CHOICE = (
        (1, '待检测'),
        (2, '完成'),
        (3, '检测中'),
        (4, '强制结束')
    )
    equip_no = models.CharField(max_length=64, help_text="机台号", verbose_name='机台号', blank=True)
    test_plan = models.ForeignKey(ProductTestPlan, help_text='检测计划', on_delete=models.CASCADE, related_name=
                                  'product_test_plan_detail')
    product_no = models.CharField(max_length=64, help_text='胶料编码')
    factory_date = models.DateField(help_text='工厂日期')
    lot_no = models.CharField(max_length=64, help_text='收皮条码', null=True)
    production_classes = models.CharField(max_length=64, help_text='生产班次')
    production_group = models.CharField(max_length=64, help_text='生产班组')
    actual_trains = models.PositiveIntegerField(help_text='生产车次')
    value = models.CharField(max_length=200, help_text="检测结果值json格式,{'ML(1+4)': 12}", null=True)
    raw_value = models.TextField(null=True, help_text='检测原数据')
    test_time = models.DateTimeField(auto_now=True)
    status = models.PositiveIntegerField(help_text='状态', choices=STATUS_CHOICE, default=1)

    class Meta:
        db_table = 'product_test_plan_detail'
        verbose_name_plural = verbose_name = '胶料快检计划详情'

    @property
    def classes(self):
        return self.production_classes

    @property
    def values(self):
        return eval(self.value).get('l_4') if self.value else None


class ProductReportValue(models.Model):
    """胶料快检上报值"""
    ip = models.CharField(max_length=64, help_text='上报设备IP')
    created_date = models.DateTimeField(verbose_name='数据上报时间')
    value = models.FloatField(help_text='检测值')
    is_binding = models.BooleanField(help_text='是否绑定', default=False)

    class Meta:
        db_table = 'product_report_value'
        verbose_name_plural = verbose_name = '胶料快检上报值'


"""
    原料检测
"""


class MaterialEquipType(models.Model):
    """原材料设备类型"""
    type_name = models.CharField(max_length=64, help_text='设备类型名称', verbose_name='设备类型名称')
    examine_type = models.ManyToManyField('MaterialExamineType', help_text='检测类型')

    class Meta:
        db_table = 'material_equip_type'
        verbose_name_plural = verbose_name = '原材料设备类型'


class MaterialEquip(models.Model):
    """原材料检测设备"""
    equip_name = models.CharField(max_length=64, help_text='设备名称', verbose_name='设备名称')
    equip_type = models.ForeignKey(MaterialEquipType, help_text='设备类型', on_delete=models.CASCADE)

    class Meta:
        db_table = 'material_equip'
        verbose_name_plural = verbose_name = '原材料设备'


class ExamineValueUnit(models.Model):
    """检测值单位"""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'examine_value_unit'
        verbose_name_plural = verbose_name = '检测值单位'


class MaterialExamineType(models.Model):
    """原材料检测类型"""
    INTERVAL_TYPES = (
        (1, '上下限'),  # 闭区间
        (2, '<='),
        (3, '>='),
        (4, '外观确认')  # 离散值
    )
    interval_type = models.IntegerField(choices=INTERVAL_TYPES, help_text="比值类型?")
    name = models.CharField(max_length=200, unique=True, help_text="类型完整名称")
    actual_name = models.CharField(max_length=200, help_text="类型名称")
    limit_value = models.FloatField(help_text='边界值', null=True, blank=True)
    unit = models.ForeignKey(ExamineValueUnit, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'material_examine_type'
        verbose_name_plural = verbose_name = '原材料检测类型'


class MaterialExamineRatingStandard(models.Model):
    """评级标准
       相同检测类型，区间不能重叠
    """
    examine_type = models.ForeignKey(MaterialExamineType, on_delete=models.CASCADE, related_name="standards")
    upper_limit_value = models.FloatField()
    lower_limiting_value = models.FloatField()
    level = models.PositiveIntegerField()

    class Meta:
        # unique_together = ('examine_type', 'level')
        db_table = 'material_examine_rating_standard'
        verbose_name_plural = verbose_name = '评级标准'


class ExamineMaterial(models.Model):
    """检测原材料"""
    STATUSES = (
        (1, '检测状态未同步'),
        (2, '检测状态已同步'),
        (3, '同步失败'),
    )
    material_meta = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200, help_text='原材料名称')
    sample_name = models.CharField(max_length=200, help_text='样品名称', null=True, blank=True)
    batch = models.CharField(max_length=200, help_text='批次号')
    supplier = models.CharField(max_length=200, help_text='产地', blank=True, null=True)
    status = models.IntegerField(choices=STATUSES, default=1)
    tmh = models.CharField(max_length=64, help_text='条码号， 总厂wms查询条件', blank=True, null=True)
    wlxxid = models.CharField(max_length=64, help_text='物料信息ID, 对应吒达物料编码', blank=True, null=True)
    qualified = models.BooleanField(help_text='是否合格', default=False)
    process_mode_handle_user = models.ForeignKey(User, help_text='经办人', on_delete=models.SET_NULL,
                                                 null=True, blank=True)
    process_mode_time = models.DateTimeField(null=True, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    deal_status = models.CharField(max_length=8, help_text='处理状态（已处理/未处理）', default='未处理')
    deal_result = models.CharField(max_length=16, help_text='处理结果（放行/不放行）', blank=True,  null=True)
    desc = models.CharField(max_length=256, help_text='处理说明', blank=True,  null=True)
    deal_username = models.CharField(max_length=64, help_text='处理人', blank=True,  null=True)
    deal_time = models.DateTimeField(help_text='处理时间', blank=True,  null=True)

    class Meta:
        db_table = 'examine_material'
        verbose_name_plural = verbose_name = '检测原材料'


class MaterialExamineResult(models.Model):
    """检测结果"""
    material = models.ForeignKey(ExamineMaterial, related_name='examine_results', on_delete=models.PROTECT)
    examine_date = models.DateField(help_text='检测日期', null=True, blank=True)
    transport_date = models.DateField(help_text='收货日期', null=True, blank=True)
    # examine_types = models.ManyToManyField(MaterialExamineType, through=MaterialSingleTypeExamineResult)
    qualified = models.BooleanField(help_text='是否合格')
    re_examine = models.BooleanField(help_text='是否为复测')
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    recorder = models.ForeignKey(User, help_text='记录人', on_delete=models.CASCADE,
                                 related_name='record_material_examine_result')
    sampling_user = models.ForeignKey(User, help_text='抽样人', on_delete=models.CASCADE,
                                      related_name='sample_material_examine_result')

    class Meta:
        db_table = 'material_examine_result'
        verbose_name_plural = verbose_name = '检测结果'

    def newest_qualified(self):
        result = self.material.examine_results.order_by('-examine_date', '-create_time')[0]
        return result.qualified if result else None


class MaterialSingleTypeExamineResult(models.Model):
    """单类型检测结果"""
    material_examine_result = models.ForeignKey(MaterialExamineResult, on_delete=models.SET_NULL, null=True,
                                                blank=True, related_name="single_examine_results")
    type = models.ForeignKey(MaterialExamineType, on_delete=models.SET_NULL, null=True, blank=True)
    mes_decide_qualified = models.NullBooleanField('mes判定是否合格')
    value = models.FloatField(null=True)
    # other_system_decide_qualified = models.NullBooleanField('其他系统判定是否合格')
    equipment = models.ForeignKey(MaterialEquip, verbose_name='检测机台', on_delete=models.SET_NULL,
                                  null=True, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        # unique_together = ('material_examine_result', 'type')
        db_table = 'material_single_type_examine_result'
        verbose_name_plural = verbose_name = '单类型检测结果'

#
# class UnqualifiedMaterialProcessMode(models.Model):
#     """不合格原材料处理方式"""
#     material = models.ForeignKey(ExamineMaterial, related_name='unqualified_processes', on_delete=models.CASCADE)
#     mode = models.CharField(max_length=200, unique=True)
#     create_user = models.ForeignKey(User, on_delete=models.CASCADE)
#     create_time = models.DateTimeField(auto_now_add=True)
#
#     class Meta:
#         db_table = 'unqualified_material_process_mode'
#         verbose_name_plural = verbose_name = '不合格原材料处理方式'


class MaterialInspectionRegistration(AbstractEntity):
    tracking_num = models.CharField(max_length=64, help_text='条码号， 总厂wms查询条件', blank=True, null=True)
    quality_status = models.CharField(max_length=8, help_text='品质状态,待检/合格/不合格', default='待检')
    material_name = models.CharField(max_length=200, help_text='原材料名称')
    material_no = models.CharField(max_length=64, help_text='物料编码', blank=True, null=True)
    batch = models.CharField(max_length=200, help_text='批次号')

    class Meta:
        db_table = 'material_inspection_registration'
        verbose_name_plural = verbose_name = '原材料总部送检条码登记'


class MaterialReportEquip(AbstractEntity):
    """原材料快检上报设备"""
    no = models.CharField(max_length=64, help_text='设备编号')
    ip = models.CharField(max_length=64, help_text='IP', unique=True)
    type = models.ForeignKey(MaterialExamineType, on_delete=models.CASCADE, help_text='检测类型')

    class Meta:
        db_table = 'material_report_equip'
        verbose_name_plural = verbose_name = '原材料快检上报设备'


class MaterialReportValue(models.Model):
    """原材料快检上报值"""
    ip = models.CharField(max_length=64, help_text='上报设备IP')
    created_date = models.DateTimeField(verbose_name='数据上报时间')
    value = models.FloatField(help_text='检测值')
    is_binding = models.BooleanField(help_text='是否绑定', default=False)

    class Meta:
        db_table = 'material_report_value'
        verbose_name_plural = verbose_name = '原材料快检上报值'


class RubberMaxStretchTestResult(models.Model):
    """物性、刚拔检测数据详情"""

    product_test_plan_detail = models.ForeignKey(ProductTestPlanDetail, help_text='检测计划任务',
                                                 on_delete=models.CASCADE, related_name='test_results')
    ordering = models.IntegerField(help_text='检测次序（刚拔5次、物性3次）')
    speed = models.FloatField(help_text='速度', null=True)
    thickness = models.FloatField(help_text='厚度（物性）', null=True)
    width = models.FloatField(help_text='宽度（物性）', null=True)
    ds1 = models.FloatField(help_text='ds1', null=True)
    ds2 = models.FloatField(help_text='ds2', null=True)
    ds3 = models.FloatField(help_text='ds3', null=True)
    ds4 = models.FloatField(help_text='ds4', null=True)
    max_strength = models.FloatField(help_text='最大力', null=True)
    max_length = models.FloatField(help_text='最大伸长', null=True)
    end_strength = models.FloatField(help_text='结束力', null=True)
    end_length = models.FloatField(help_text='结束伸长', null=True)
    break_strength = models.FloatField(help_text='断裂强力', null=True)
    break_length = models.FloatField(help_text='断裂伸长', null=True)
    yield_strength = models.FloatField(help_text='屈服强度', null=True)
    yield_length = models.FloatField(help_text='屈服伸长', null=True)
    n1 = models.FloatField(help_text='n1（物性）', null=True)
    n2 = models.FloatField(help_text='n2（物性）', null=True)
    n3 = models.FloatField(help_text='n3（物性）', null=True)
    test_time = models.CharField(max_length=64, help_text='检测时间', null=True)
    test_method = models.CharField(max_length=64, help_text='检测方法', null=True)
    result = models.CharField(max_length=64, help_text='检测结果')

    class Meta:
        db_table = 'rubber_max_stretch_test_result'
        verbose_name_plural = verbose_name = '刚拔物性检测数据详情'


class MaterialTestPlan(models.Model):
    STATUS_CHOICE = (
        (1, '待检测'),
        (2, '完成'),
        (4, '结束检测')
    )
    material_report_equip = models.ForeignKey(MaterialReportEquip, help_text='检测机台', on_delete=models.CASCADE)
    plan_uid = models.CharField(max_length=64, help_text='计划编号', null=True, blank=True)
    test_time = models.DateField(help_text='检测日期')
    test_classes = models.CharField(max_length=64, help_text='生产班次')
    test_group = models.CharField(max_length=64, help_text='生产班组')
    test_method = models.ForeignKey(MaterialExamineType, help_text='检测方法', on_delete=models.CASCADE)
    status = models.PositiveIntegerField(help_text='状态', choices=STATUS_CHOICE, default=1)

    class Meta:
        db_table = 'material_test_plan'
        verbose_name_plural = verbose_name = '原材料检测计划'


class MaterialTestPlanDetail(models.Model):
    STATUS_CHOICE = (
        (1, '待检测'),
        (2, '完成'),
        (4, '结束检测')
    )
    material_test_plan = models.ForeignKey(MaterialTestPlan, help_text='原材料检测计划', on_delete=models.CASCADE, related_name='material_list')
    material = models.ForeignKey(ExamineMaterial, help_text='原材料', on_delete=models.PROTECT)
    value = models.FloatField(null=True, help_text='检测值')
    flat = models.NullBooleanField(help_text='是否合格', default=None)
    status = models.PositiveIntegerField(help_text='状态', choices=STATUS_CHOICE, default=1)
    transport_date = models.DateField(help_text='收货日期', null=True, blank=True)
    recorder = models.ForeignKey(User, help_text='记录人', on_delete=models.CASCADE, related_name='material_plan_detail')
    sampling_user = models.ForeignKey(User, help_text='抽样人', on_delete=models.CASCADE, related_name='material_test_plan_detail')

    class Meta:
        db_table = 'material_test_plan_detail'
        verbose_name_plural = verbose_name = '原材料检测计划详情'
