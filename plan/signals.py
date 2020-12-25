from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ProductClassesPlan, BatchingClassesPlan


@receiver(post_save, sender=ProductClassesPlan)
def product_classes_plan_save_handler(sender, **kwargs):
    product_classes_plan = kwargs['instance']
    if product_classes_plan.delete_flag:  # 所有相同排班 和 配方的计划被删除
        if not ProductClassesPlan.objects.filter(
                delete_flag=False,
                work_schedule_plan=product_classes_plan.work_schedule_plan,
                product_batching=product_classes_plan.product_batching).exists():
            BatchingClassesPlan.objects.filter(
                work_schedule_plan=product_classes_plan.work_schedule_plan,
                weigh_cnt_type__weigh_batching__product_batching=product_classes_plan.product_batching
            ).update(delete_flag=True)
    else:
        if product_classes_plan.product_batching.weighbatching:  # 如果计划关联胶料配方有小料配方
            for cnt_type in product_classes_plan.product_batching.weighbatching.weighcnttype_set.all():
                batching_classes_plan, created = BatchingClassesPlan.objects.get_or_create(
                    work_schedule_plan=product_classes_plan.work_schedule_plan,
                    weigh_cnt_type=cnt_type)
                if not created and batching_classes_plan.delete_flag:
                    batching_classes_plan.delete_flag = False
                    batching_classes_plan.save()
