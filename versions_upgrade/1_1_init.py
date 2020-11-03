import os
import sys

import django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from production.models import TrainsFeedbacks, PalletFeedbacks
from plan.models import ProductClassesPlan


def add_permissions():
    """增加快检相关权限"""
    pass


def add_factory_data():
    """补充车次反馈和托盘反馈中的factory_date字段"""
    train_feed_backs = TrainsFeedbacks.objects.all()
    for train_feed_back in train_feed_backs:
        plan_classes_uid = train_feed_back.plan_classes_uid
        classes_plan = ProductClassesPlan.objects.filter(plan_classes_uid=plan_classes_uid).first()
        if classes_plan:
            train_feed_back.factory_data = classes_plan.work_schedule_plan.plan_schedule.day_time
            train_feed_back.save()

    pallet_feed_backs = PalletFeedbacks.objects.all()
    for pallet_feed_back in pallet_feed_backs:
        plan_classes_uid = pallet_feed_back.plan_classes_uid
        classes_plan = ProductClassesPlan.objects.filter(plan_classes_uid=plan_classes_uid).first()
        if classes_plan:
            pallet_feed_back.factory_data = classes_plan.work_schedule_plan.plan_schedule.day_time
            pallet_feed_back.save()


if __name__ == '__main__':
    add_permissions()
    add_factory_data()