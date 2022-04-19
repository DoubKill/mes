
"""
    更新wms物料检测结果信息
"""
import json
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

from quality.models import ExamineMaterial, MaterialInspectionRegistration
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

    # 更新总部检测结果
    inspection_materials = MaterialInspectionRegistration.objects.filter(quality_status='待检')
    inspection_url = 'http://10.1.10.136/zcxjws_web/zcxjws/pc/zc/getCkdtm.io'
    for inspection_material in inspection_materials:
        try:
            json_data = {"fac": "AJ1", "tmh": inspection_material.tracking_num}
            ret = requests.post(inspection_url, json=json_data, timeout=10)
        except Exception:
            logger.error('查询总部质检结果失败，网络异常！')
            continue
        inspection_data = json.loads(ret.text)
        obj = inspection_data.get('obj')
        if not obj:
            continue
        else:
            zjzt = obj[0].get('zjzt')
            if not zjzt:
                continue
            check_result = None
            if zjzt == '合格品':
                quality_status = '合格'
                check_result = 1
            elif zjzt == '待检品':
                quality_status = '待检'
            else:
                quality_status = '不合格'
                check_result = 2
            inspection_material.quality_status = quality_status
            inspection_material.save()

            # 将总部检测结果更新到立库
            if check_result:
                inspection_data_list = [{
                            "BatchNo": inspection_material.batch,
                            "MaterialCode": inspection_material.material_no,
                            "CheckResult": check_result
                        }]
                update_wms_quality_result(inspection_data_list)

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