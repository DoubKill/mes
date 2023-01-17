
"""
    更新wms物料检测结果信息（只以总部检测结果为准）
"""
import json
import os
import sys
from datetime import datetime, timedelta

import django
import requests


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from quality.models import MaterialInspectionRegistration
from inventory.models import WmsInventoryStock, WmsNucleinManagement
from quality.utils import update_wms_quality_result
from django.db.models import Min

import logging
logger = logging.getLogger('quality_log')


def main1():
    """更新原材料库检测结果"""
    stocks = WmsInventoryStock.objects.using('wms').exclude(material_name__icontains='托盘').filter(
        quality_status=5).values('material_no', 'batch_no', 'material_name').annotate(lot_no=Min('lot_no'))
    inspection_url = 'http://10.1.10.136/zcxjws_web/zcxjws/pc/zc/getCkdtm.io'
    for item in stocks:
        lot_no = item['lot_no']
        batch_no = item['batch_no']
        if not batch_no:
            continue
        material_no = item['material_no']
        material_name = item['material_name']
        try:
            json_data = {"fac": "AJ1", "tmh": lot_no}
            ret = requests.post(inspection_url, json=json_data, timeout=10)
        except Exception:
            logger.error('查询总部质检结果失败，网络异常！')
            continue
        inspection_data = json.loads(ret.text)
        obj = inspection_data.get('obj')
        if not obj:
            logger.error('未查到此条码检测信息:{}！'.format(lot_no))
            continue
        else:
            zjzt = obj[0].get('zjzt')
            logger.error('原材料:{} 批次号:{} 总部检测结果为:{}！'.format(material_no, batch_no, zjzt))
            if not zjzt:
                quality_status = 3
            else:
                if zjzt in ('合格品', '紧急放行', '免检'):
                    quality_status = 1
                elif zjzt == '待检品':
                    continue
                else:
                    quality_status = 3
            rest = MaterialInspectionRegistration.objects.filter(
                material_no=material_no, batch=batch_no).first()
            if rest:
                rest.quality_status = '合格' if quality_status == 1 else '不合格'
                rest.save()
            else:
                MaterialInspectionRegistration.objects.create(
                    material_no=material_no,
                    batch=batch_no,
                    quality_status='合格' if quality_status == 1 else '不合格',
                    tracking_num=lot_no,
                    material_name=material_name
                )
            WmsInventoryStock.objects.using('wms').filter(
                material_no=material_no,
                batch_no=batch_no,
                quality_status__in=(1, 5)).update(quality_status=quality_status)

    ex_time = datetime.now() - timedelta(days=7)
    # 核酸检测锁定（设定不合格）
    data_list = [{
                    "BatchNo": w.batch_no,
                    "MaterialCode": w.material_no,
                    "CheckResult": 2
                } for w in WmsNucleinManagement.objects.filter(
        locked_status='已锁定', created_date__gte=ex_time)]
    if data_list:
        update_wms_quality_result(data_list)


def main2():
    """更新炭黑库检测结果"""
    stocks = WmsInventoryStock.objects.using('cb').exclude(material_name__icontains='托盘').filter(
        quality_status=5).values('material_no', 'batch_no', 'material_name').annotate(lot_no=Min('lot_no'))
    inspection_url = 'http://10.1.10.136/zcxjws_web/zcxjws/pc/zc/getCkdtm.io'
    for item in stocks:
        lot_no = item['lot_no']
        batch_no = item['batch_no']
        if not batch_no:
            continue
        material_no = item['material_no']
        material_name = item['material_name']
        try:
            json_data = {"fac": "AJ1", "tmh": lot_no}
            ret = requests.post(inspection_url, json=json_data, timeout=10)
        except Exception:
            logger.error('查询总部质检结果失败，网络异常！')
            continue
        inspection_data = json.loads(ret.text)
        obj = inspection_data.get('obj')
        if not obj:
            logger.error('炭黑库：未查到此条码检测信息:{}！'.format(lot_no))
            continue
        else:
            zjzt = obj[0].get('zjzt')
            logger.error('炭黑:{} 批次号:{} 总部检测结果为:{}！'.format(material_no, batch_no, zjzt))
            if not zjzt:
                quality_status = 3
            else:
                if zjzt in ('合格品', '紧急放行', '免检'):
                    quality_status = 1
                elif zjzt == '待检品':
                    continue
                else:
                    quality_status = 3
            # rest = MaterialInspectionRegistration.objects.filter(
            #     material_no=material_no, batch=batch_no).first()
            # if rest:
            #     rest.quality_status = '合格' if quality_status == 1 else '不合格'
            #     rest.save()
            # else:
            #     MaterialInspectionRegistration.objects.create(
            #         material_no=material_no,
            #         batch=batch_no,
            #         quality_status='合格' if quality_status == 1 else '不合格',
            #         tracking_num=lot_no,
            #         material_name=material_name
            #     )
            WmsInventoryStock.objects.using('cb').filter(
                material_no=material_no,
                batch_no=batch_no,
                quality_status__in=(1, 5)).update(quality_status=quality_status)


if __name__ == '__main__':
    main1()
    main2()