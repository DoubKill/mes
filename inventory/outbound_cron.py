"""
    定时发起出库任务
"""


import datetime
import json
import os
import sys

import django
import logging


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()
logger = logging.getLogger('sync_log')
from inventory.utils import OUTWORKUploader, OUTWORKUploaderLB
from inventory.models import OutBoundDeliveryOrderDetail


def main():

    mixin_out_bound_orders = OutBoundDeliveryOrderDetail.objects.filter(
        outbound_delivery_order__warehouse='混炼胶库',
        status=1).order_by('inventory_time')
    for mixin_order in mixin_out_bound_orders:
        data1 = [{'WORKID': mixin_order.order_no,
                  'MID': mixin_order.outbound_delivery_order.product_no,
                  'PICI': "1",
                  'RFID': mixin_order.pallet_no,
                  'STATIONID': mixin_order.outbound_delivery_order.station,
                  'SENDDATE': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]
        req_data = {
            'msgId': mixin_order.outbound_delivery_order.order_no,
            'OUTTYPE': '快检出库',
            "msgConut": '1',
            "SENDUSER": 'MES',
            "items": data1
        }
        json_data = json.dumps(req_data, ensure_ascii=False)
        sender = OUTWORKUploader(end_type="指定出库")
        mixin_result = sender.request(mixin_order.outbound_delivery_order.order_no, '指定出库', '1', 'MES', json_data)
        logger.info('混炼胶库任务号：{},北自反馈信息：{}'.format(mixin_order.order_no, mixin_result))
        mixin_state = 2
        if mixin_result is not None:
            try:
                items = mixin_result['items']
                msg = items[0]['msg']
            except:
                msg = mixin_result[0]['msg']
            if "TRUE" not in msg:  # 失败
                mixin_state = 5
        mixin_order.status = mixin_state
        mixin_order.save()

    final_out_bound_orders = OutBoundDeliveryOrderDetail.objects.filter(
        outbound_delivery_order__warehouse='终炼胶库',
        status=1).order_by('inventory_time')
    for final_order in final_out_bound_orders:
        data2 = [{'WORKID': final_order.order_no,
                  'MID': final_order.outbound_delivery_order.product_no,
                  'PICI': "1",
                  'RFID': final_order.pallet_no,
                  'STATIONID': final_order.outbound_delivery_order.station,
                  'SENDDATE': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                  'STOREDEF_ID': 1}]
        req_data = {
            'msgId': final_order.outbound_delivery_order.order_no,
            'OUTTYPE': '快检出库',
            "msgConut": '1',
            "SENDUSER": 'MES',
            "items": data2
        }
        json_data = json.dumps(req_data, ensure_ascii=False)
        sender = OUTWORKUploaderLB(end_type="指定出库")
        final_result = sender.request(final_order.outbound_delivery_order.order_no, '指定出库', '1', 'MES', json_data)
        logger.info('终炼胶库任务号：{},北自反馈信息：{}'.format(final_order.order_no, final_result))
        final_state = 2
        if final_result is not None:
            try:
                items = final_result['items']
                msg = items[0]['msg']
            except:
                msg = final_result[0]['msg']
            if "TRUE" not in msg:  # 失败
                final_state = 5
        final_order.status = final_state
        final_order.save()


if __name__ == '__main__':
    main()