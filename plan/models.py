from django.db import models
from django.db.models import Sum

from basics.models import Equip, PlanSchedule, ClassesDetail, WorkSchedulePlan
from recipe.models import ProductBatching, Material, WeighCntType
from system.models import AbstractEntity, User
from basics.models import Equip, PlanSchedule, ClassesDetail, WorkSchedulePlan, GlobalCode, EquipCategoryAttribute
from recipe.models import ProductBatching, Material
from system.models import AbstractEntity


# Create your models here.
class ProductDayPlan(AbstractEntity):
    """胶料日计划表"""
    equip = models.ForeignKey(Equip, on_delete=models.CASCADE, help_text='机台id', verbose_name='机台id',
                              related_name='equip_product_day_plan')
    product_batching = models.ForeignKey(ProductBatching, on_delete=models.CASCADE, help_text='配料id',
                                         verbose_name='配料id',
                                         related_name='pb_day_plan')
    plan_schedule = models.ForeignKey(PlanSchedule, on_delete=models.CASCADE, help_text='排班计划id',
                                      verbose_name='排班计划id',
                                      related_name='ps_day_plan')

    class Meta:
        # unique_together = (("product_batching", "plan_schedule"),)
        db_table = 'product_day_plan'
        verbose_name_plural = verbose_name = '胶料日计划'


class ProductClassesPlan(AbstractEntity):
    """胶料日班次计划表"""
    product_day_plan = models.ForeignKey(ProductDayPlan, on_delete=models.CASCADE, help_text='胶料日计划id',
                                         verbose_name='胶料日计划id',
                                         related_name='pdp_product_classes_plan', null=True)
    sn = models.PositiveIntegerField(verbose_name='顺序', help_text='顺序')
    plan_trains = models.PositiveIntegerField(verbose_name='车次', help_text='车次')
    time = models.DecimalField(help_text='时间（分钟）', blank=True, null=True, decimal_places=2, max_digits=8)
    weight = models.DecimalField(verbose_name='重量', help_text='重量',
                                 decimal_places=3, max_digits=8, blank=True, null=True)
    unit = models.CharField(max_length=8, help_text='单位', verbose_name='单位')
    work_schedule_plan = models.ForeignKey(WorkSchedulePlan, on_delete=models.CASCADE, help_text='班次id',
                                           verbose_name='排班详情id', related_name='cd_product_classes_plan')
    plan_classes_uid = models.CharField(verbose_name='班次计划唯一码', help_text='班次计划唯一码',
                                        max_length=64, unique=True)
    note = models.CharField(max_length=64, help_text='备注', blank=True, null=True)
    equip = models.ForeignKey(Equip, on_delete=models.CASCADE, help_text='机台id', verbose_name='机台id',
                              related_name='equip_product_classes_plan', null=True, blank=True)
    product_batching = models.ForeignKey(ProductBatching, on_delete=models.CASCADE, help_text='配料id',
                                         verbose_name='配料id',
                                         related_name='pb_product_classes_plan', null=True, blank=True)
    status = models.CharField(max_length=64, help_text='状态:等待、已下达、运行中、完成', verbose_name='状态',
                              choices=(('已保存', '已保存'), ('等待', '等待'), ('已下达', '已下达'), ('运行中', '运行中'), ('完成', '完成'),
                                       ('待停止', '待停止')), null=True, blank=True)

    @property
    def total_time(self):
        return self.time * 60

    class Meta:
        db_table = 'product_classes_plan'
        verbose_name_plural = verbose_name = '胶料日班次计划'


class ProductBatchingDayPlan(AbstractEntity):
    """配料小料日计划表"""
    equip = models.ForeignKey(Equip, on_delete=models.CASCADE, help_text='机台id', verbose_name='机台id',
                              related_name='equip_product_batching_day_plan')
    product_batching = models.ForeignKey(ProductBatching, on_delete=models.CASCADE, help_text='配料id',
                                         verbose_name='配料id',
                                         related_name='pb_product_batching_day_plan')
    plan_schedule = models.ForeignKey(PlanSchedule, on_delete=models.CASCADE, help_text='排班计划id',
                                      verbose_name='排班计划id',
                                      related_name='ps_product_batching_day_plan')
    bags_total_qty = models.PositiveIntegerField(verbose_name='日计划袋数', help_text='日计划袋数')
    product_day_plan = models.ForeignKey(ProductDayPlan, on_delete=models.CASCADE, help_text='炼胶日计划id',
                                         verbose_name='炼胶日计划id',
                                         related_name='pdp_product_batching_day_plan', null=True, default=None)

    class Meta:
        db_table = 'product_batching_day_plan'
        verbose_name_plural = verbose_name = '配料小料日计划'


class ProductBatchingClassesPlan(AbstractEntity):
    """配料料日班次计划表"""
    product_batching_day_plan = models.ForeignKey(ProductBatchingDayPlan, on_delete=models.CASCADE,
                                                  help_text='配料日计划id',
                                                  verbose_name='配料日计划id',
                                                  related_name='pdp_product_batching_classes_plan')
    sn = models.PositiveIntegerField(verbose_name='顺序', help_text='顺序')
    bags_qty = models.PositiveIntegerField(verbose_name='袋数', help_text='袋数')
    # time = models.TimeField(verbose_name='时间', help_text='时间')
    # weight = models.DecimalField(verbose_name='重量', help_text='重量',
    #                              decimal_places=2, max_digits=8, blank=True, null=True)
    unit = models.CharField(max_length=8, help_text='单位', verbose_name='单位')
    classes_detail = models.ForeignKey(ClassesDetail, on_delete=models.CASCADE, help_text='班次id',
                                       verbose_name='班次id',
                                       related_name='cd_product_batching_classes_plan')
    plan_classes_uid = models.CharField(verbose_name='班次计划唯一码', help_text='班次计划唯一码', max_length=64)

    class Meta:
        db_table = 'product_batching_classes_plan'
        verbose_name_plural = verbose_name = '配料料日班次计划'


class MaterialDemanded(AbstractEntity):
    """原材料需求量表"""
    product_classes_plan = models.ForeignKey(ProductClassesPlan, on_delete=models.CASCADE, help_text='胶料日班次计划表id',
                                             verbose_name='胶料日班次计划表id')
    work_schedule_plan = models.ForeignKey(WorkSchedulePlan, on_delete=models.CASCADE, help_text='班次id',
                                           verbose_name='排班详情id')
    material = models.ForeignKey(Material, on_delete=models.CASCADE, help_text='原材料id',
                                 verbose_name='原材料id',
                                 related_name='m_material_demanded')
    material_demanded = models.PositiveIntegerField(verbose_name='原材料需求重量', help_text='原材料需求重量')
    plan_classes_uid = models.CharField(max_length=128, verbose_name='班次计划唯一码', help_text='班次计划唯一码', null=True)

    class Meta:
        db_table = 'material_demanded'
        verbose_name_plural = verbose_name = '原材料需求量'


class MaterialRequisitionClasses(AbstractEntity):
    """领料日班次计划表"""
    material_demanded = models.ManyToManyField(MaterialDemanded,
                                               help_text='原材料需求量id',
                                               verbose_name='原材料需求量id',
                                               related_name='md_material_requisition_classes')
    # sn = models.PositiveIntegerField(verbose_name='顺序', help_text='顺序',null=True)
    weight = models.DecimalField(verbose_name='重量', help_text='重量',
                                 decimal_places=2, max_digits=8, blank=True, null=True)
    unit = models.CharField(max_length=64, help_text='单位', verbose_name='单位')
    classes_detail = models.ForeignKey(ClassesDetail, on_delete=models.CASCADE, help_text='班次id',
                                       verbose_name='班次id',
                                       related_name='cd_material_requisition_classes', null=True)
    plan_classes_uid = models.CharField(max_length=64, verbose_name='班次计划唯一码', help_text='班次计划唯一码', null=True)

    class Meta:
        db_table = 'material_requisition_classes'
        verbose_name_plural = verbose_name = '领料日班次计划'


class BatchingClassesPlan(AbstractEntity):
    """配料日班次计划"""
    PLAN_STATUSES = (
        (1, '未下发'),
        (2, '已下发')
    )
    work_schedule_plan = models.ForeignKey(WorkSchedulePlan, on_delete=models.CASCADE)
    weigh_cnt_type = models.ForeignKey(WeighCntType, on_delete=models.CASCADE)
    plan_batching_uid = models.CharField('计划唯一编码', max_length=64, unique=True)
    plan_package = models.PositiveIntegerField(default=0, help_text='包数')
    package_changed = models.BooleanField(default=False)
    status = models.PositiveIntegerField(choices=PLAN_STATUSES, default=1)

    class Meta:
        # unique_together = ('work_schedule_plan', 'weigh_cnt_type')
        db_table = 'batching_classes_plan'
        verbose_name_plural = verbose_name = '配料日班次计划'

    @property
    def undistributed_package(self):
        sum_package = self.equip_plans.aggregate(sum_package=Sum('packages'))['sum_package']
        sum_package = sum_package if sum_package else 0
        return self.plan_package - sum_package

    def plan_package_from_product_classes_plan(self):  # 计划包数
        plan_sum_trains = ProductClassesPlan.objects.filter(
            delete_flag=False,
            work_schedule_plan=self.work_schedule_plan,
            product_batching=self.weigh_cnt_type.product_batching
        ).aggregate(plan_sum_trains=Sum('plan_trains')).get('plan_sum_trains')
        return (plan_sum_trains if plan_sum_trains else 0) * self.weigh_cnt_type.package_cnt

    def single_weight(self):  # 单包重量
        standard_sum_weight = self.weigh_cnt_type.weight_details.aggregate(standard_sum_weight=Sum('standard_weight'))
        return standard_sum_weight.get('standard_sum_weight')


class BatchingClassesEquipPlan(models.Model):

    batching_class_plan = models.ForeignKey(BatchingClassesPlan, help_text='小料配料计划id', on_delete=models.CASCADE,
                                            related_name='equip_plans')
    send_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    send_time = models.DateTimeField(null=True, blank=True)
    equip = models.ForeignKey(Equip, blank=True, null=True, on_delete=models.SET_NULL)
    package_changed = models.BooleanField(default=False)
    packages = models.IntegerField(help_text='包数', default=0)

    class Meta:
        db_table = 'batching_classes_equip_plan'
        verbose_name_plural = verbose_name = '小料配料机台计划'

# class BatchingProductPlanRelation(models.Model):
#     batching_classes_plan = models.ForeignKey(BatchingClassesPlan, on_delete=models.CASCADE)
#     product_classes_plan = models.ForeignKey(ProductClassesPlan, on_delete=models.CASCADE)
#
#     class Meta:
#         db_table = 'batching_product_plan_relation'
#         verbose_name_plural = verbose_name = '配料日计划和胶料日计划关连'
#
#
# class BatchingClassesDemand(models.Model):
#     batching_classes_plan = models.ForeignKey(BatchingClassesPlan, on_delete=models.CASCADE,
#                                               related_name='classes_demands')
#     material = models.ForeignKey(Material, help_text='原材料', on_delete=models.CASCADE)
#     plan_weight = models.DecimalField(help_text='重量', decimal_places=2, max_digits=8)
#     actual_weight = models.DecimalField(help_text='重量', decimal_places=2, max_digits=8, default=0)
#
#     class Meta:
#         db_table = 'batching_classes_demand'
#         verbose_name_plural = verbose_name = '班次小料需求量'


class SchedulingParamsSetting(models.Model):
    scheduling_type = models.CharField(max_length=32, help_text='排程方式选择(传统方式/优化算法)')
    scheduling_during_time = models.IntegerField(help_text='自动排程期间（小时）')
    scheduling_interval_trains = models.IntegerField(help_text='前后工序间隔车数（车）')
    scheduling_adaptable_trains = models.IntegerField(help_text='现场可修改计划数量（车）', blank=True, null=True)
    min_stock_trains = models.FloatField(help_text='确保最低库存量（天）')
    scheduling_auto_time = models.CharField(max_length=32, help_text='排程参数自动统计时间', blank=True, null=True)
    standing_time = models.IntegerField(help_text='无S打加S放置期时间（小时）', blank=True, null=True)
    pkg_count = models.IntegerField(help_text='小料包一车包数')
    validity = models.IntegerField(help_text='小料包有效期（小时）', blank=True, null=True)
    mixing_summary_st_time = models.IntegerField(help_text='开始密炼时间统计范围（秒）', blank=True, null=True)
    mixing_summary_et_time = models.IntegerField(help_text='结束密炼时间统计范围（秒）', blank=True, null=True)
    mixing_interval_st_time = models.IntegerField(help_text='开始密炼间隔时间统计范围（秒）', blank=True, null=True)
    mixing_interval_et_time = models.IntegerField(help_text='结束密炼间隔时间统计范围（秒）', blank=True, null=True)
    use_flag = models.BooleanField(help_text='是否考虑物料齐套')
    mixing_place_interval_time = models.FloatField(help_text='混炼各段次之间放置时间（小时）', blank=True, null=True)

    class Meta:
        db_table = 'aps_params_setting'
        verbose_name_plural = verbose_name = '自动排程参数设定'


class SchedulingRecipeMachineSetting(AbstractEntity):
    rubber_type = models.CharField(max_length=32, help_text='胶料类别')
    product_no = models.CharField(max_length=32, help_text='胶料代码')
    stage = models.CharField(max_length=32, help_text='胶料段次')
    mixing_main_machine = models.CharField(max_length=128, help_text='混炼主机台')
    mixing_vice_machine = models.CharField(max_length=128, help_text='混炼辅机台', blank=True, null=True)
    final_main_machine = models.CharField(max_length=128, help_text='终炼主机台')
    final_vice_machine = models.CharField(max_length=128, help_text='终炼辅机台', blank=True, null=True)

    class Meta:
        db_table = 'aps_recipe_machine_setting'
        verbose_name_plural = verbose_name = '定机表'
        unique_together = ('rubber_type', 'product_no', 'stage')


class SchedulingEquipCapacity(AbstractEntity):
    equip_no = models.CharField(max_length=16, help_text='机台号')
    product_no = models.CharField(max_length=32, help_text='胶料代码')
    avg_mixing_time = models.IntegerField(help_text='平均工作时间（秒）')
    avg_interval_time = models.IntegerField(help_text='平均间隔时间（秒）')
    avg_rubbery_quantity = models.FloatField(help_text='*平均加胶量(kg)')

    class Meta:
        db_table = 'aps_equip_capacity'
        verbose_name_plural = verbose_name = '机台生产能力'


class SchedulingWashRule(AbstractEntity):
    rule_no = models.CharField(max_length=64, help_text='规则编号', unique=True)
    rule_name = models.CharField(max_length=64, help_text='规则名称')
    previous_spec = models.CharField(max_length=64, help_text='前规格', blank=True, null=True)
    following_spec = models.CharField(max_length=64, help_text='后规格', blank=True, null=True)
    note = models.CharField(max_length=256, help_text='备注', blank=True, null=True)
    use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)

    class Meta:
        db_table = 'aps_wash_rule'
        verbose_name_plural = verbose_name = '洗车放置规则'


class SchedulingWashRuleDetail(AbstractEntity):
    wash_rule = models.ForeignKey(SchedulingWashRule, on_delete=models.CASCADE, related_name='rule_details')
    # ordering = models.IntegerField(help_text='序号')
    process = models.CharField(max_length=64, help_text='处理', blank=True, null=True)
    spec_params = models.CharField(max_length=64, help_text='处理参数（规格/单位）', blank=True, null=True)
    quantity_params = models.IntegerField(help_text='处理参数（车数/数量）', blank=True, null=True)

    class Meta:
        db_table = 'aps_wash_rule_detail'
        verbose_name_plural = verbose_name = '洗车放置规则详情'


class SchedulingWashPlaceKeyword(AbstractEntity):
    keyword_no = models.CharField(max_length=64, help_text='编号', unique=True)
    keyword_name = models.CharField(max_length=64, help_text='名称', unique=True)
    product_nos = models.CharField(max_length=512, help_text='胶料代码')
    note = models.CharField(max_length=256, help_text='备注', blank=True, null=True)

    class Meta:
        db_table = 'aps_wash_place_keyword'
        verbose_name_plural = verbose_name = '胶料/单位关键字定义'


class SchedulingWashPlaceOperaKeyword(AbstractEntity):
    keyword_no = models.CharField(max_length=64, help_text='编号', unique=True)
    keyword_name = models.CharField(max_length=64, help_text='名称', unique=True)
    note = models.CharField(max_length=256, help_text='备注', blank=True, null=True)

    class Meta:
        db_table = 'aps_wash_place_opera_keyword'
        verbose_name_plural = verbose_name = '处理关键字定义'


class SchedulingProductDemandedDeclare(AbstractEntity):
    order_no = models.CharField(max_length=64, help_text='单号')
    factory = models.CharField(max_length=64, help_text='分厂')
    factory_date = models.DateField(help_text='工厂日期', verbose_name='工厂日期')
    product_no = models.CharField(max_length=64, help_text='胶料代码')
    today_demanded = models.FloatField(help_text='当日需求（吨）')
    tomorrow_demanded = models.FloatField(help_text='明日需求（吨）', default=0)
    current_stock = models.FloatField(help_text='当前库存（吨）', default=0)
    underway_stock = models.FloatField(help_text='在途库存（吨）', default=0)
    status = models.CharField(max_length=64, help_text='状态', default='未确认')

    class Meta:
        db_table = 'aps_product_demanded_declare'
        verbose_name_plural = verbose_name = '分厂胶料计划申报'


class SchedulingProductSafetyParams(AbstractEntity):
    factory = models.CharField(max_length=64, help_text='分厂')
    product_no = models.CharField(max_length=64, help_text='胶料代码')
    safety_stock = models.FloatField(help_text='安全库存（吨）')
    safety_factor = models.FloatField(help_text='安全库存系数')
    daily_usage = models.FloatField(help_text='日均用量（吨）')
    use_flag = models.BooleanField(help_text='是否启用', verbose_name='是否启用', default=True)

    class Meta:
        db_table = 'aps_product_safety_params'
        verbose_name_plural = verbose_name = '分厂胶料计划申报'


class SchedulingProductDemandedDeclareSummary(models.Model):
    sn = models.IntegerField(help_text='顺序')
    factory_date = models.DateField(help_text='工厂日期', verbose_name='工厂日期')
    product_no = models.CharField(max_length=64, help_text='胶料代码')
    plan_weight = models.FloatField(help_text='计划总用量（吨）', default=0)
    workshop_weight = models.FloatField(help_text='车间总库存（吨）', default=0)
    current_stock = models.FloatField(help_text='立体库总库存（吨）', default=0)
    desc = models.CharField(max_length=128, help_text='备注（加硫不合格待处理）', blank=True, null=True)
    target_stock = models.FloatField(help_text='目标总库存量（吨）', default=0)
    available_time = models.FloatField(help_text='可用时间', default=0)
    demanded_weight = models.FloatField(help_text='需生产量（吨）', default=0)

    def save(self, *args, **kwargs):
        self.available_time = round((self.workshop_weight + self.current_stock) / self.plan_weight, 2)
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'aps_product_demanded_declare_summary'
        verbose_name_plural = verbose_name = '分厂胶料计划申报汇总'


class SchedulingResult(models.Model):
    factory_date = models.DateField(help_text='排程日期', verbose_name='排程日期')
    schedule_no = models.CharField(max_length=64, help_text='排程编号', db_index=True)
    equip_no = models.CharField(max_length=64, help_text='机台', verbose_name='机台')
    sn = models.IntegerField(help_text='顺序')
    recipe_name = models.CharField(max_length=64, help_text='配方名称')
    time_consume = models.FloatField(help_text='耗时(h)', default=0)
    plan_trains = models.IntegerField(help_text='车数')
    desc = models.CharField(max_length=64, help_text='备注', null=True, blank=True)
    created_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    status = models.CharField(max_length=8, help_text='下发状态（未下发/已下发）', default='未下发')

    class Meta:
        db_table = 'aps_result'
        verbose_name_plural = verbose_name = '排程结果'


# class SchedulingRecipeMachineRelationHistory(models.Model):
#     schedule_no = models.CharField(max_length=64, help_text='排程编号', db_index=True)
#     equip_no = models.CharField(max_length=64, help_text='机台', verbose_name='机台')
#     recipe_name = models.CharField(max_length=64, help_text='配方名称')
#     batching_weight = models.FloatField(help_text='产出重量')
#     devoted_weight = models.FloatField(help_text='投入重量')
#     dev_type = models.CharField(max_length=64, help_text='机型')
#
#     class Meta:
#         db_table = 'aps_recipe_machine_result_history'
#         verbose_name_plural = verbose_name = '排程机台配方投入产出履历'


class SchedulingEquipShutDownPlan(AbstractEntity):
    equip_no = models.CharField(max_length=64, help_text='机台', verbose_name='机台')
    down_type = models.CharField(max_length=64, help_text='停机类型')
    begin_time = models.DateTimeField(help_text='开始停机时间')
    duration = models.FloatField(help_text='停机时长（小时）')
    desc = models.CharField(max_length=64, help_text='备注', null=True)

    class Meta:
        db_table = 'aps_equip_shutdown_plan'
        verbose_name_plural = verbose_name = '分厂胶料计划申报'
