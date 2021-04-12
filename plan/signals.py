import uuid

from django.core.exceptions import ObjectDoesNotExist
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
                weigh_cnt_type__product_batching=product_classes_plan.product_batching
            ).update(delete_flag=True)
    else:
        try:
            for cnt_type in product_classes_plan.product_batching.weight_cnt_types.filter(delete_flag=False):
                batching_classes_plan = BatchingClassesPlan.objects.filter(
                    work_schedule_plan=product_classes_plan.work_schedule_plan,
                    weigh_cnt_type=cnt_type,
                    delete_flag=False).first()
                created = False
                if not batching_classes_plan:
                    batching_classes_plan = BatchingClassesPlan.objects.create(
                        work_schedule_plan=product_classes_plan.work_schedule_plan,
                        weigh_cnt_type=cnt_type,
                        plan_batching_uid=uuid.uuid1().hex)
                    created = True
                plan_package_from_product_classes_plan = batching_classes_plan \
                    .plan_package_from_product_classes_plan()
                if not created:
                    if plan_package_from_product_classes_plan != batching_classes_plan.plan_package:
                        batching_classes_plan.package_changed = True
                batching_classes_plan.plan_package = plan_package_from_product_classes_plan
                batching_classes_plan.save()
        except ObjectDoesNotExist as e:
            pass
