import os
import time

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()
from tasks import update_wms_kjjg
import datetime
from inventory.models import BzFinalMixingRubberInventory, BzFinalMixingRubberInventoryLB
from production.models import PalletFeedbacks
from quality.models import MaterialDealResult
from mes.conf import SEND_COUNT
import logging

logger = logging.getLogger('send_log')

"""定时任务，将胶料处理结果发送给北自"""


def send_bz():
    ex_time = datetime.datetime.now() - datetime.timedelta(days=3)
    deal_results = MaterialDealResult.objects.filter(update_store_test_flag__gt=1, created_date__gte=ex_time)
    for mdr_obj in deal_results:
        pfb_obj = PalletFeedbacks.objects.filter(lot_no=mdr_obj.lot_no).first()
        bz_obj = BzFinalMixingRubberInventory.objects.using('bz').filter(lot_no=mdr_obj.lot_no).last()
        ware = '混炼'
        if not bz_obj:
            bz_obj = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(lot_no=mdr_obj.lot_no).last()
            ware = "终炼"
        if bz_obj:
            try:
                test_result = mdr_obj.test_result
                if test_result == '三等品':
                    zjzt = '三等品'
                else:
                    zjzt = '一等品'
                # 4、update_store_test_flag这个字段用choise 1对应成功 2对应失败 3对应库存线边库都没有
                msg_ids = ''.join(str(time.time()).split('.'))
                item = []
                item_dict = {"WORKID": str(int(msg_ids) + 1),
                             "MID": pfb_obj.product_no,
                             "PICI": str(bz_obj.bill_id),
                             "RFID": pfb_obj.pallet_no,
                             "DJJG": zjzt,
                             "SENDDATE": datetime.datetime.now().strftime('%Y%m%d %H:%M:%S')}
                item.append(item_dict)
                # 向北自发送数据
                res = update_wms_kjjg(ware, items=item)
                if not res:  # res为空代表成功
                    mdr_obj.update_store_test_flag = 1
                    mdr_obj.save()
                    logger.info("向北自发送数据,发送成功")
                # else:
                #     mdr_obj.update_store_test_flag = 2
                #     temp_count = mdr_obj.send_count + 1
                #     mdr_obj.send_count = temp_count
                #     mdr_obj.save()
                #     logger.error(f"发送失败{res}")
            except Exception as e:
                logger.error(f"调北自接口发生异常：{e}")
        # else:  # 两个库都没有
        #     mdr_obj.update_store_test_flag = 3
        #     temp_count = mdr_obj.send_count + 1
        #     mdr_obj.send_count = temp_count
        #     mdr_obj.save()
        #     logger.error(f"没有发送，库存和线边库里都没有lot_no:{mdr_obj.lot_no}")


if __name__ == '__main__':
    try:
        send_bz()
    except Exception as e:
        logger.error(e)
