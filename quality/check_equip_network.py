
"""
    检查门尼、流变设备网络状态
"""

import os
import sys

import django
import logging
logger = logging.getLogger('quality_log')


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from quality.models import ProductReportEquip


def main():
    for equip in ProductReportEquip.objects.all():
        hostname = equip.ip
        response = os.system("ping -c 1 " + hostname)
        if response == 0:
            equip.status = 1
        else:
            equip.status = 2
        equip.save()


if __name__ == '__main__':
    main()
