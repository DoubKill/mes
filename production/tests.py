from django.test import TestCase

# Create your tests here.
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()
from basics.models import Equip
from production.models import TrainsFeedbacks, EquipStatus, ProcessFeedback, ExpendMaterial
import datetime

e_set = Equip.objects.all()
for e_obj in e_set:
    for i in range(1, 20):
        plan_classes_uid = 123
        tfb_obk = TrainsFeedbacks.objects.create(plan_classes_uid=plan_classes_uid, plan_trains=19, actual_trains=i,
                                                 bath_no=i, equip_no=e_obj.equip_no, product_no='123', plan_weight=12.1,
                                                 actual_weight=1.2, begin_time=datetime.datetime.now(),
                                                 end_time=datetime.datetime.now(), operation_user='user', classes='早班',
                                                 product_time=datetime.datetime.now(),
                                                 factory_date=datetime.date.today(),
                                                 control_mode='123', operating_type='123', evacuation_time=123,
                                                 evacuation_temperature=234, evacuation_energy=34546,
                                                 interval_time=345345,
                                                 mixer_time=89, evacuation_power='345', consum_time=234, gum_weight=12.3,
                                                 cb_weight=234234.3, oil1_weight=12.3, oil2_weight=75.4, add_gum_time=788,
                                                 add_cb_time=234, add_oil1_time=7897, add_oil2_time=3543)

        for j in range(1, 12):
            EquipStatus.objects.create(equip_no=tfb_obk.equip_no,
                                       plan_classes_uid=tfb_obk.plan_classes_uid,
                                       product_time=tfb_obk.begin_time,
                                       temperature=j, rpm=j, energy=j, power=j, pressure=j, status=str(j),
                                       current_trains=i)

            ProcessFeedback.objects.create(plan_classes_uid=tfb_obk.plan_classes_uid,
                                           equip_no=tfb_obk.equip_no,
                                           product_no=tfb_obk.product_no,
                                           current_trains=tfb_obk.actual_trains, sn=j, condition='das', time=j,
                                           temperature=j, power=j, energy=j, action='ui', rpm=j, pressure=j,
                                           product_time=datetime.datetime.now())

            ExpendMaterial.objects.create(equip_no=tfb_obk.equip_no,
                                          plan_classes_uid=tfb_obk.plan_classes_uid,
                                          product_no=tfb_obk.product_no,
                                          trains=tfb_obk.actual_trains, delete_flag=False,
                                          plan_weight=j,
                                          actual_weight=j,
                                          material_no='ert',
                                          material_type='dfg',
                                          material_name='gbdf',
                                          product_time=datetime.datetime.now()
                                          )
