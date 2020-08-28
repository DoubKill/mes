import re

from django.test import TestCase

# Create your tests here.
import datetime
import time as t
import os
import random
import uuid
import django

from add_test_data import random_str
from basics.models import Equip, PlanSchedule, WorkSchedulePlan
from recipe.models import ProductBatching, ProductBatchingDetail, Material

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from plan.models import ProductClassesPlan, ProductDayPlan, MaterialDemanded
from production.models import TrainsFeedbacks, PalletFeedbacks, EquipStatus, PlanStatus
from system.models import User
from django.db.transaction import atomic
from plan.uuidfield import UUidTools


def strtoint(equip_no):
    equip_list = re.findall(r'\d+', equip_no)
    equip_int = ''
    for i in equip_list:
        equip_int += i
    return int(equip_int)


def random_name():
    user_dict = User.objects.values('username')
    name_list = []
    for _ in user_dict:
        name_list.append(_['username'])
    return random.choice(name_list)


def random_status():
    status_list = ['等待', '运行中', '完成']
    return random.choice(status_list)


def add_batching_detail():
    pb_set = ProductBatching.objects.all()[:30]
    m_set = Material.objects.all()[:3]
    for pb_obj in pb_set:
        for m_obj in m_set:
            ProductBatchingDetail.objects.create(product_batching=pb_obj, sn=1, material=m_obj,actual_weight=100,
                                                 standard_error=12.12,auto_flag=1)


def add_product_plan():
    e_set = Equip.objects.all()[:3]
    p_set = ProductBatching.objects.all()[:3]
    ps_set = PlanSchedule.objects.all()[:3]
    ws_set = WorkSchedulePlan.objects.all()[:3]

    i = 1
    for e_obj in e_set:
        for p_obj in p_set:
            for ps_obj in ps_set:
                pdp_obj = ProductDayPlan.objects.create(equip=e_obj, product_batching=p_obj, plan_schedule=ps_obj)
                for ws_obj in ws_set:
                    pcp_obj = ProductClassesPlan.objects.create(product_day_plan=pdp_obj, sn=i, plan_trains=i, time=i,
                                                                weight=i, unit='包', work_schedule_plan=ws_obj,
                                                                plan_classes_uid=UUidTools.uuid1_hex(), note='备注')
                    details = pcp_obj.product_day_plan.product_batching.batching_details.all()
                    for detail in details:
                        MaterialDemanded.objects.create(product_classes_plan=pcp_obj,
                                                        work_schedule_plan=pcp_obj.work_schedule_plan,
                                                        material=detail.material, material_demanded=i,
                                                        plan_classes_uid=pcp_obj.plan_classes_uid)
                    i += 1


def add_product():
    pcp_set = ProductClassesPlan.objects.all()[:30]
    # pcp_set = ProductClassesPlan.objects.all()
    for pcp_obj in pcp_set:
        num = pcp_obj.weight / pcp_obj.plan_trains
        # for i in range(1, pcp_obj.plan_trains + 1):
        user_name = random_name()
        for i in range(1, 5):
            t = TrainsFeedbacks.objects.create(plan_classes_uid=pcp_obj.plan_classes_uid,
                                               plan_trains=pcp_obj.plan_trains,
                                               actual_trains=i, bath_no=i,
                                               equip_no=pcp_obj.product_day_plan.equip.equip_no,
                                               product_no=pcp_obj.product_day_plan.product_batching.stage_product_batch_no,
                                               plan_weight=pcp_obj.weight,
                                               actual_weight=num * i,
                                               begin_time=datetime.datetime.now(),
                                               end_time=datetime.datetime.now(),
                                               operation_user=user_name,
                                               classes=pcp_obj.work_schedule_plan.classes.global_name)

            print(t)
            p = PalletFeedbacks.objects.create(plan_classes_uid=pcp_obj.plan_classes_uid,
                                               bath_no=i, equip_no=pcp_obj.product_day_plan.equip.equip_no,
                                               product_no=pcp_obj.product_day_plan.product_batching.stage_product_batch_no,
                                               plan_weight=pcp_obj.weight,
                                               actual_weight=num * i,
                                               begin_time=datetime.datetime.now(),
                                               end_time=datetime.datetime.now(),
                                               operation_user=user_name,
                                               begin_trains=i - 1, end_trains=i,
                                               pallet_no='托盘（虽然我也不知道是啥意思）',
                                               barcode=i * 100,
                                               classes=pcp_obj.work_schedule_plan.classes.global_name,
                                               lot_no='追踪号'
                                               )
            print(p)
            e = EquipStatus.objects.create(plan_classes_uid=pcp_obj.plan_classes_uid,
                                           equip_no=pcp_obj.product_day_plan.equip.equip_no,
                                           temperature=36.7,
                                           rpm=1.1, energy=2.2, power=3.3, pressure=4.4, status=random_status(),
                                           current_trains=i, product_time=datetime.datetime.now())
            print(e)
            ps = PlanStatus.objects.create(plan_classes_uid=pcp_obj.plan_classes_uid,
                                           equip_no=pcp_obj.product_day_plan.equip.equip_no,
                                           product_no=pcp_obj.product_day_plan.product_batching.stage_product_batch_no,
                                           status=random_status(), operation_user=user_name)
            print(ps)


if __name__ == '__main__':
    add_batching_detail()
    add_product_plan()
    add_product()
    # add_work()
