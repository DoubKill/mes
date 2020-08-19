# coding: utf-8
"""计划模块初始化脚本"""
import datetime
import os
import random
import string

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()
from basics.models import PlanSchedule, ClassesDetail, WorkSchedule
from recipe.models import ProductBatching
from plan.models import ProductDayPlan, ProductClassesPlan, ProductBatchingDayPlan, ProductBatchingClassesPlan, \
    MaterialDemanded, MaterialRequisitionClasses
from plan.uuidfield import UUidTools
from django.db.transaction import atomic


@atomic()
def add_product_day_plan():
    for i in range(19, 21):
        for pd_obj in ProductBatching.objects.filter().all():
            for ps_obj in PlanSchedule.objects.filter().all():
                instance = ProductDayPlan.objects.create(equip_id=i, product_batching=pd_obj, plan_schedule=ps_obj)
                j = 1
                cd_queryset = ClassesDetail.objects.filter(
                    work_schedule=WorkSchedule.objects.filter(plan_schedule=instance.plan_schedule).first())
                for cd_obj in cd_queryset:
                    pcp_obj = ProductClassesPlan.objects.create(product_day_plan=instance, sn=j, plan_trains=j,
                                                                time=instance.product_batching.batching_time_interval,
                                                                weight=instance.product_batching.batching_weight,
                                                                unit='kg',
                                                                classes_detail=cd_obj,
                                                                plan_classes_uid=UUidTools.uuid1_hex())
                    for pbd_obj in instance.product_batching.batching_details.all():
                        MaterialDemanded.objects.create(classes=pcp_obj.classes_detail,
                                                        material=pbd_obj.material,
                                                        material_demanded=pbd_obj.actual_weight * pcp_obj.plan_trains,
                                                        plan_classes_uid=pcp_obj.plan_classes_uid,
                                                        plan_schedule=instance.plan_schedule)
                    j += 1


if __name__ == '__main__':
    print('开始新增数据')
    add_product_day_plan()
    print('胶料计划新增成功')
