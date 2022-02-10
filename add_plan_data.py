# coding: utf-8
"""
    说明：添加当天的计划数据，每天跑一次
"""

import datetime
import os
import random
import django
import uuid

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from plan.models import ProductDayPlan, ProductClassesPlan
from recipe.models import ProductBatching
from basics.models import Equip, PlanSchedule, WorkSchedulePlan
from production.models import PlanStatus


def main():
    # ProductDayPlan.objects.all().delete()
    ps = PlanSchedule.objects.filter(day_time=datetime.datetime.now().date()).first()
    for pb in ProductBatching.objects.filter(used_type=4):
        equip_ids = list(Equip.objects.filter(category=pb.dev_type).values_list('id', flat=True))
        if equip_ids:
            pdp = ProductDayPlan.objects.create(
                plan_schedule=ps,
                product_batching=pb,
                equip_id=random.choice(equip_ids))
            for name in ['早班', '夜班']:
                wsp = WorkSchedulePlan.objects.filter(plan_schedule=ps, classes__global_name=name).first()
                pcp = ProductClassesPlan.objects.create(
                    weight=random.randint(200, 500),
                    product_day_plan=pdp,
                    sn=1,
                    plan_trains=random.randint(20, 50),
                    unit='车',
                    work_schedule_plan=wsp,
                    plan_classes_uid=uuid.uuid1(),
                    equip=pdp.equip,
                    product_batching=pdp.product_batching,
                    status=random.choice(['已保存', '等待', '已下达', '运行中', '待停止'])
                )
                PlanStatus.objects.create(
                    plan_classes_uid=pcp.plan_classes_uid,
                    equip_no=pcp.equip.equip_no,
                    product_no=pcp.product_batching.stage_product_batch_no,
                    status=pcp.status
                )


if __name__ == '__main__':
    main()