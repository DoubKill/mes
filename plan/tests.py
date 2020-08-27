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
from basics.models import Equip, PlanSchedule
from recipe.models import ProductBatching

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from plan.models import ProductClassesPlan, ProductDayPlan
from production.models import TrainsFeedbacks, PalletFeedbacks, EquipStatus, PlanStatus
from system.models import User
from django.db.transaction import atomic


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


def add_product_plan():
    e_set = Equip.objects.all()[:3]
    p_set = ProductBatching.objects.all()[:3]
    ps_set = PlanSchedule.objects.all()[:3]
    for e_obj in e_set:
        for p_obj in p_set:
            for ps_obj in ps_set:
                ProductDayPlan.objects.create(equip=e_obj, product_batching=p_obj, plan_schedule=ps_obj)



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
                                               begin_trains=i, end_trains=1,
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
    add_product()
    # add_work()
