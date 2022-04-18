
"""
    更新wms物料检测结果信息
"""

import os
import sys
from datetime import datetime, timedelta

import django
import requests
from django.db.models import Q

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from quality.models import ExamineMaterial
from inventory.models import WmsNucleinManagement, WMSExceptHandle

from mes.conf import WMS_URL
from quality.utils import update_wms_quality_result

import logging
logger = logging.getLogger('quality_log')


def main():
    ex_time = datetime.now() - timedelta(days=7)
    materials = ExamineMaterial.objects.filter(Q(status=1) | Q(status=2, create_time__gte=ex_time)).filter(qualified=False)
    url = WMS_URL + '/MESApi/UpdateTestingResult'
    for m in materials:
        if WmsNucleinManagement.objects.filter(locked_status='已锁定',
                                               batch_no=m.batch,
                                               material_no=m.wlxxid).exists():
            continue
        if WMSExceptHandle.objects.filter(batch_no=m.batch).exists():
            continue
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

    # 核酸检测锁定（设定不合格）
    data_list = [{
                    "BatchNo": w.batch_no,
                    "MaterialCode": w.material_no,
                    "CheckResult": 2
                } for w in WmsNucleinManagement.objects.filter(
        locked_status='已锁定', created_date__gte=ex_time)]
    if data_list:
        update_wms_quality_result(data_list)


if __name__ == '__main__':
    main()