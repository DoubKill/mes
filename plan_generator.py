import datetime
import os
import random
import uuid

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from basics.models import Equip, PlanSchedule, WorkSchedule
from plan.models import ProductDayPlan, ProductClassesPlan
from recipe.models import ProductBatching


def run():
    equip_set = Equip.objects.filter(equip_name__icontains="混炼")
    equip_count = equip_set.count()
    pb_set = ProductBatching.objects.filter(delete_flag=False)
    pb_count = pb_set.count()
    ps_set = PlanSchedule.objects.filter(delete_flag=False)
    # 目前工序只有密炼
    project_list = ["密炼"]
    ws_set = WorkSchedule.objects.filter(schedule_name__in=project_list, delete_flag=False)
    for ps in ps_set:
        equip = equip_set[random.randint(0, equip_count-1)]
        pb = pb_set[random.randint(0, pb_count-1)]
        ProductDayPlan.objects.create(equip=equip, product_batching=pb, plan_schedule=ps)
    day_plan_set = ProductDayPlan.objects.filter(delete_flag=False)
    # sn的规则?
    sn = 1
    init_ps_id = None
    for day_plan in day_plan_set:
        if init_ps_id == day_plan.plan_schedule:
            sn += 1
        else:
            init_ps_id = day_plan.plan_schedule
        for ws in ws_set:
            mn_uid = None
            an_uid = None
            nt_uid = None
            for cs in ws.classesdetail_set.filter(delete_flag=False):
                cs_name = cs.classes.global_name
                if cs_name == "早班":
                    uid = mn_uid if mn_uid else uuid.uuid1()
                elif cs_name == "中班":
                    uid = an_uid if an_uid else uuid.uuid1()
                elif cs_name == "晚班":
                    uid = nt_uid if nt_uid else uuid.uuid1()
                else:
                    # 暂不做其他班次的处理
                    continue
                ProductClassesPlan.objects.create(sn=sn, product_day_plan=day_plan, plan_classes_uid=uid,
                                                  classes_detail=cs, unit="kg", plan_trains=50, weight=250,
                                                  time=datetime.datetime.now())


if __name__ == "__main__":
    run()
