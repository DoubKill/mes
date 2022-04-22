
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

"""
    总部、安吉检测有一个不合格则直接更新成不合格，
    两边都合格才更新成合格
    总部待检超过10天还查不到检测结果，则判定成不合格
"""


def update_inspection_registration():
    """更新送检原材料的总部检测结果"""
    ex_time = datetime.now() - timedelta(days=10)
    inspection_materials = MaterialInspectionRegistration.objects.filter(quality_status='待检',
                                                                         create_time__gte=ex_time)
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
                quality_status = '不合格'
            else:
                if zjzt == '合格品':
                    quality_status = '合格'
                elif zjzt == '待检品':
                    quality_status = '待检'
                else:
                    quality_status = '不合格'
            inspection_material.quality_status = quality_status
            inspection_material.save()

            # 总部检测不合格则直接更新立库检测结果为不合格
            if quality_status == '不合格':
                inspection_data_list = [{
                            "BatchNo": inspection_material.batch,
                            "MaterialCode": inspection_material.material_no,
                            "CheckResult": 2
                        }]
                update_wms_quality_result(inspection_data_list)


def main():
    ex_time = datetime.now() - timedelta(days=7)
    materials = ExamineMaterial.objects.filter(Q(status=1) | Q(status=2, create_time__gte=ex_time))
    url = WMS_URL + '/MESApi/UpdateTestingResult'
    for m in materials:
        if WmsNucleinManagement.objects.filter(locked_status='已锁定',
                                               batch_no=m.batch,
                                               material_no=m.wlxxid).exists():
            continue

        # 有手动放行记录，则不管
        if WMSExceptHandle.objects.filter(batch_no=m.batch).exists():
            continue
        if not m.qualified:  # 安吉检测不合格则直接更新不合格
            checkout_result = 2
        else:
            inspection_material = MaterialInspectionRegistration.objects.filter(
                batch=m.batch, material_no=m.wlxxid).first()
            if not inspection_material:  # 安吉检测合格，但未录入总部送检数据，则直接更新合格
                checkout_result = 1
            else:
                if inspection_material.quality_status == '不合格':  # 安吉检测合格，且录入总部送检数据，总部不合格，则更新成不合格
                    checkout_result = 2
                elif inspection_material.quality_status == '合格':  # 安吉检测合格，且录入总部送检数据，总部合格，则更新成合格
                    checkout_result = 1
                else:
                    continue

        data = {
                "TestingType": 2,
                "SpotCheckDetailList": [{
                    "BatchNo": m.batch,
                    "MaterialCode": m.wlxxid,
                    "CheckResult": checkout_result
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
    update_inspection_registration()
    main()