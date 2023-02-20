import os
import time

import django
from django.db.models import Q

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

    lb_objs = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(store_name='炼胶库')
    for lb_obj in lb_objs:
        lot_no = lb_obj.lot_no
        if lot_no:
            if lot_no.startswith('AAJ1Z'):
                mdr = MaterialDealResult.objects.filter(lot_no=lot_no).first()
                if mdr:
                    test_result = mdr.test_result
                    if test_result == '三等品':
                        zjzt = '三等品'
                    else:
                        zjzt = '一等品'
                    if lb_obj.quality_level == zjzt:
                        continue
                    msg_ids = ''.join(str(time.time()).split('.'))
                    item = []
                    item_dict = {"WORKID": str(int(msg_ids) + 1),
                                 "MID": lb_obj.material_no,
                                 "PICI": str(lb_obj.bill_id),
                                 "RFID": lb_obj.container_no,
                                 "DJJG": zjzt,
                                 "SENDDATE": datetime.datetime.now().strftime('%Y%m%d %H:%M:%S')}
                    item.append(item_dict)
                    # 向北自发送数据
                    res = update_wms_kjjg('终炼', items=item)
                    if not res:  # res为空代表成功
                        logger.info("条码：{},更新北自立库品质状态成功！".format(lot_no))

    bz_objs = BzFinalMixingRubberInventory.objects.using('bz').all()
    for bz_obj in bz_objs:
        lot_no = bz_obj.lot_no
        if lot_no:
            if lot_no.startswith('AAJ1Z'):
                mdr = MaterialDealResult.objects.filter(lot_no=lot_no).first()
                if mdr:
                    test_result = mdr.test_result
                    if test_result == '三等品':
                        zjzt = '三等品'
                    else:
                        zjzt = '一等品'
                    if bz_obj.quality_level == zjzt:
                        continue
                    msg_ids = ''.join(str(time.time()).split('.'))
                    item = []
                    item_dict = {"WORKID": str(int(msg_ids) + 1),
                                 "MID": bz_obj.material_no,
                                 "PICI": str(bz_obj.bill_id),
                                 "RFID": bz_obj.container_no,
                                 "DJJG": zjzt,
                                 "SENDDATE": datetime.datetime.now().strftime('%Y%m%d %H:%M:%S')}
                    item.append(item_dict)
                    # 向北自发送数据
                    res = update_wms_kjjg('混炼', items=item)
                    if not res:  # res为空代表成功
                        logger.info("条码：{},更新北自立库品质状态成功！".format(lot_no))

    # ex_time = datetime.datetime.now() - datetime.timedelta(days=3)
    # deal_results = MaterialDealResult.objects.filter(
    #     Q(update_store_test_flag=4) |
    #     Q(update_store_test_flag__in=(2, 3), created_date__gte=ex_time))
    # for mdr_obj in deal_results:
    #     pfb_obj = PalletFeedbacks.objects.filter(lot_no=mdr_obj.lot_no).first()
    #     bz_obj = BzFinalMixingRubberInventory.objects.using('bz').filter(lot_no=mdr_obj.lot_no).last()
    #     ware = '混炼'
    #     if not bz_obj:
    #         bz_obj = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(lot_no=mdr_obj.lot_no).last()
    #         ware = "终炼"
    #     if bz_obj:
    #         try:
    #             test_result = mdr_obj.test_result
    #             if test_result == '三等品':
    #                 zjzt = '三等品'
    #             else:
    #                 zjzt = '一等品'
    #             # 4、update_store_test_flag这个字段用choise 1对应成功 2对应失败 3对应库存线边库都没有
    #             msg_ids = ''.join(str(time.time()).split('.'))
    #             item = []
    #             item_dict = {"WORKID": str(int(msg_ids) + 1),
    #                          "MID": pfb_obj.product_no,
    #                          "PICI": str(bz_obj.bill_id),
    #                          "RFID": bz_obj.container_no,
    #                          "DJJG": zjzt,
    #                          "SENDDATE": datetime.datetime.now().strftime('%Y%m%d %H:%M:%S')}
    #             item.append(item_dict)
    #             # 向北自发送数据
    #             res = update_wms_kjjg(ware, items=item)
    #             if not res:  # res为空代表成功
    #                 if ware == '混炼':
    #                     ts = BzFinalMixingRubberInventory.objects.using('bz').filter(lot_no=mdr_obj.lot_no).first()
    #                 else:
    #                     ts = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(lot_no=mdr_obj.lot_no).first()
    #                 if not ts:
    #                     update_store_test_flag = 1
    #                 else:
    #                     if ts.quality_level == zjzt:
    #                         update_store_test_flag = 1
    #                         logger.info("条码：{},更新北自立库品质状态成功！".format(mdr_obj.lot_no))
    #                     else:
    #                         update_store_test_flag = 2
    #                         logger.info("条码：{},更新北自立库品质状态失败，原因未知！".format(mdr_obj.lot_no))
    #                 mdr_obj.update_store_test_flag = update_store_test_flag
    #                 mdr_obj.save()
    #             else:
    #                 mdr_obj.update_store_test_flag = 2
    #                 # temp_count = mdr_obj.send_count + 1
    #                 # mdr_obj.send_count = temp_count
    #                 mdr_obj.save()
    #                 logger.error("条码：{}，更新北自立库品质状态失败，原因：{}".format(mdr_obj.lot_no, res))
    #         except Exception as e:
    #             logger.error(f"请求北自接口发生异常：{e}")
    #     else:  # 两个库都没有
    #         mdr_obj.update_store_test_flag = 3
    #         # temp_count = mdr_obj.send_count + 1
    #         # mdr_obj.send_count = temp_count
    #         mdr_obj.save()
    #         logger.error("条码：{},更新北自立库品质状态失败，库存未找到！".format(mdr_obj.lot_no))


if __name__ == '__main__':
    try:
        send_bz()
    except Exception as e:
        logger.error(e)
