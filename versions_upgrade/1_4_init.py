# 将晚班统一修改为夜班


import os
import sys

import django
from django.db.transaction import atomic

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()


from basics.models import GlobalCode
from production.models import TrainsFeedbacks, PalletFeedbacks


@atomic()
def change_classes():
    GlobalCode.objects.filter(global_name='晚班').update(global_name='夜班')
    TrainsFeedbacks.objects.filter(classes='晚班').update(classes='夜班')
    PalletFeedbacks.objects.filter(classes='晚班').update(classes='夜班')


if __name__ == '__main__':
    change_classes()
