from django.db import models
from django.db.models import Sum

from basics.models import Equip, PlanSchedule, ClassesDetail, WorkSchedulePlan
from recipe.models import ProductBatching, Material, WeighCntType
from system.models import AbstractEntity, User


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
                                        max_length=64)
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
        (2, '已下发'),
        (3, '执行中'),
        (4, '已完成')
    )
    work_schedule_plan = models.ForeignKey(WorkSchedulePlan, on_delete=models.CASCADE)
    weigh_cnt_type = models.ForeignKey(WeighCntType, on_delete=models.CASCADE)
    status = models.PositiveIntegerField(choices=PLAN_STATUSES, default=1)
    send_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    send_time = models.DateTimeField(null=True, blank=True)
    equip = models.ForeignKey(Equip, blank=True, null=True, on_delete=models.SET_NULL)

    plan_classes_uid = models.CharField('计划唯一编码', max_length=64, unique=True, null=True)


    class Meta:
        unique_together = ('work_schedule_plan', 'weigh_cnt_type')
        db_table = 'batching_classes_plan'
        verbose_name_plural = verbose_name = '配料日班次计划'

    def plan_package(self):  # 计划包数
        plan_sum_trains = ProductClassesPlan.objects.filter(
            delete_flag=False,
            work_schedule_plan=self.work_schedule_plan,
            product_batching=self.weigh_cnt_type.weigh_batching.product_batching
        ).aggregate(plan_sum_trains=Sum('plan_trains')).get('plan_sum_trains')
        return (plan_sum_trains if plan_sum_trains else 0) * self.weigh_cnt_type.package_cnt

    def single_weight(self):  # 单包重量
        standard_sum_weight = self.weigh_cnt_type \
            .weighbatchingdetail_set.aggregate(standard_sum_weight=Sum('standard_weight'))
        return standard_sum_weight.get('standard_sum_weight')
