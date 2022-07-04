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
from inventory.models import OutBoundDeliveryOrderDetail, BzFinalMixingRubberInventory, BzFinalMixingRubberInventoryLB


def main():

    mixin_working_cnt = BzFinalMixingRubberInventory.objects.using('bz').filter(location_status='工作货位').count()
    final_working_cnt = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(
        store_name="炼胶库", location_status='工作货位').count()
    if mixin_working_cnt < 6:
        cnt1 = 6 - mixin_working_cnt
        mixin_out_bound_orders = OutBoundDeliveryOrderDetail.objects.filter(
            outbound_delivery_order__warehouse='混炼胶库',
            status=1).order_by('inventory_time')[:cnt1]
        for order in mixin_out_bound_orders:
            data1 = [{'WORKID': order.order_no,
                      'MID': order.outbound_delivery_order.product_no,
                      'PICI': "1",
                      'RFID': order.pallet_no,
                      'STATIONID': order.outbound_delivery_order.station,
                      'SENDDATE': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]
            req_data = {
                'msgId': order.outbound_delivery_order.order_no,
                'OUTTYPE': '快检出库',
                "msgConut": '1',
                "SENDUSER": 'MES',
                "items": data1
            }
            json_data = json.dumps(req_data, ensure_ascii=False)
            sender = OUTWORKUploader(end_type="指定出库")
            result = sender.request(order.outbound_delivery_order.order_no, '指定出库', '1', 'MES', json_data)
            logger.info('混炼胶库任务号：{},北自反馈信息：{}'.format(order.order_no, result))
            order.status = 2
            order.save()
    if final_working_cnt < 6:
        cnt2 = 6 - final_working_cnt
        final_out_bound_orders = OutBoundDeliveryOrderDetail.objects.filter(
            outbound_delivery_order__warehouse='终炼胶库',
            status=1).order_by('inventory_time')[:cnt2]
        for order in final_out_bound_orders:
            data2 = [{'WORKID': order.order_no,
                      'MID': order.outbound_delivery_order.product_no,
                      'PICI': "1",
                      'RFID': order.pallet_no,
                      'STATIONID': order.outbound_delivery_order.station,
                      'SENDDATE': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                      'STOREDEF_ID': 1}]
            req_data = {
                'msgId': order.outbound_delivery_order.order_no,
                'OUTTYPE': '快检出库',
                "msgConut": '1',
                "SENDUSER": 'MES',
                "items": data2
            }
            json_data = json.dumps(req_data, ensure_ascii=False)
            sender = OUTWORKUploaderLB(end_type="指定出库")
            result = sender.request(order.outbound_delivery_order.order_no, '指定出库', '1', 'MES', json_data)
            logger.info('终炼胶库任务号：{},北自反馈信息：{}'.format(order.order_no, result))
            order.status = 2
            order.save()


if __name__ == '__main__':
    main()