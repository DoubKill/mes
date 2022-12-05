"""
   补充车次重复数据，每天八点半修复前一天计划（除了4号机）
"""

import os
import sys
import django
import datetime
import logging

from django.db.models import Min, Max, Count
from django.forms import model_to_dict

logger = logging.getLogger('error_log')


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes.settings')
django.setup()

from production.models import TrainsFeedbacks


def main():
    factory_date = (datetime.datetime.now() - datetime.timedelta(days=1)).date()
    trains_data = TrainsFeedbacks.objects.exclude(equip_no='Z04').filter(
        factory_date=factory_date
    ).values('plan_classes_uid').annotate(min_train=Min('actual_trains'),
                                          max_train=Max('actual_trains'),
                                          trains_cnt=Count('id'))
    for item in trains_data:
        # min_train_num = item['min_train']  # 最小车次号
        max_train_num = item['max_train']  # 最大车次号
        trains_cnt = item['trains_cnt']
        plan_classes_uid = item['plan_classes_uid']
        if item['max_train'] == item['trains_cnt']:
            continue
        copy_train = TrainsFeedbacks.objects.filter(
                factory_date=factory_date,
                plan_classes_uid=plan_classes_uid).order_by('actual_trains').first()
        copy_date = model_to_dict(copy_train)
        copy_date['operation_user'] = '自动补录'
        pd_trains = list(TrainsFeedbacks.objects.filter(
            factory_date=factory_date,
            plan_classes_uid=plan_classes_uid).values_list('actual_trains', flat=True))
        if max_train_num > trains_cnt:  # 最大车次号比车次条数多，需要补录车次报表数据（车次报表数据缺失）
            need_trains = max_train_num - trains_cnt
            trains_nums = set([i for i in range(1, max_train_num+1)]) - set(pd_trains)
            if need_trains == len(trains_nums):
                for train in trains_nums:
                    copy_date.pop('id', None)
                    copy_date['actual_trains'] = train
                    TrainsFeedbacks.objects.create(**copy_date)
            elif need_trains < len(trains_nums):
                for train in list(trains_nums)[:need_trains]:
                    copy_date.pop('id', None)
                    copy_date['actual_trains'] = train
                    TrainsFeedbacks.objects.create(**copy_date)
            else:
                for i in range(need_trains):
                    copy_date.pop('id', None)
                    copy_date['actual_trains'] = 1
                    TrainsFeedbacks.objects.create(**copy_date)
        else:   # 条数比最大车次号多,需要删除重复数据（有可能是车次重复了）
            pass
            # del_train_nums = trains_cnt - max_train_num
            # a = []
            # b = []
            # for t in pd_trains:
            #     if t in a:
            #         b.append(t)
            #     else:
            #         a.append(t)
            # if len(set(b)) == del_train_nums:
            #     for j in b:
            #         obj = TrainsFeedbacks.objects.filter(
            #             factory_date=factory_date,
            #             plan_classes_uid=plan_classes_uid,
            #             actual_trains=j
            #         ).first()
            #         obj.delete()


if __name__ == '__main__':
    main()
