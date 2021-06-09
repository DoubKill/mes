
"""
    更新wms物料检测结果信息
"""

import os
import sys

import django
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from quality.models import ExamineMaterial

from mes.conf import WMS_URL

import logging
logger = logging.getLogger('quality_log')


def main():
    materials = ExamineMaterial.objects.filter(status=1)
    url = WMS_URL + '/MESApi/UpdateTestingResult'
    for m in materials:
        data = {
                "TestingType": 2,
                "SpotCheckDetailList": [{
                    "BatchNo": m.batch,
                    "MaterialCode": m.wlxxid,
                    "CheckResult": 1 if m.qualified else 2
                }]
            }
        headers = {"Content-Type": "application/json ;charset=utf-8"}
        try:
            r = requests.post(url, json=data, headers=headers, timeout=5)
            r = r.json()
        except Exception as e:
            logger.error(e)
            continue
        status = r.get('state')
        if not status == 1:
            logger.error('wms error msg: {}'.format(r.get('msg')))
        m.status = 2 if status == 1 else 3
        m.save()


if __name__ == '__main__':
    main()