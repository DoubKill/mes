import os
import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()
from tasks import update_wms_kjjg
import datetime
from inventory.models import BzFinalMixingRubberInventory, BzFinalMixingRubberInventoryLB
from mes.common_code import order_no
from production.models import PalletFeedbacks
from quality.models import MaterialTestOrder, MaterialDealResult
from mes.conf import SEND_COUNT
import logging

logger = logging.getLogger('send_log')

"""定时任务，将胶料处理结果发送给北自"""


def send_bz():
    deal_results = MaterialDealResult.objects.exclude(
        update_store_test_flag=1).filter(send_count__lt=SEND_COUNT)
    for mdr_obj in deal_results:
        pfb_obj = PalletFeedbacks.objects.filter(lot_no=mdr_obj.lot_no).first()
        bz_obj = BzFinalMixingRubberInventory.objects.using('bz').filter(lot_no=mdr_obj.lot_no).last()
        ware = '混炼'
        if not bz_obj:
            bz_obj = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(lot_no=mdr_obj.lot_no).last()
            ware = "终炼"
        if bz_obj:
            try:
                # 4、update_store_test_flag这个字段用choise 1对应成功 2对应失败 3对应库存线边库都没有
                msg_ids = order_no()
                mto_obj = MaterialTestOrder.objects.filter(lot_no=mdr_obj.lot_no).first()
                item = []
                item_dict = {"WORKID": str(int(msg_ids) + 1),
                             "MID": mto_obj.product_no,
                             "PICI": str(pfb_obj.plan_classes_uid),
                             "RFID": pfb_obj.pallet_no,
                             "DJJG": mdr_obj.deal_result,
                             "SENDDATE": datetime.datetime.now().strftime('%Y%m%d %H:%M:%S')}
                item.append(item_dict)
                # 向北自发送数据
                res = update_wms_kjjg(ware, items=item)
                if not res:  # res为空代表成功
                    mdr_obj.update_store_test_flag = 1
                    mdr_obj.save()
                    logger.info("向北自发送数据,发送成功")
                else:
                    mdr_obj.update_store_test_flag = 2
                    temp_count = mdr_obj.send_count + 1
                    mdr_obj.send_count = temp_count
                    mdr_obj.save()
                    logger.error(f"发送失败{res}")
            except Exception as e:
                logger.error(f"调北自接口发生异常：{e}")
        else:  # 两个库都没有
            mdr_obj.update_store_test_flag = 3
            temp_count = mdr_obj.send_count + 1
            mdr_obj.send_count = temp_count
            mdr_obj.save()
            logger.error(f"没有发送，库存和线边库里都没有lot_no:{mdr_obj.lot_no}")


if __name__ == '__main__':
    try:
        send_bz()
    except Exception as e:
        logger.error(e)
