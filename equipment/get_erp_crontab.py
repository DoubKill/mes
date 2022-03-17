"""
获取erp备件信息和备件入库单据
"""

import os
import sys
import json
import requests
import django
import datetime
import logging


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes.settings')
django.setup()
logger = logging.getLogger('get_erp_log')

from django.db.transaction import atomic
from rest_framework.views import APIView
from equipment.models import EquipSpareErp, EquipComponentType, EquipWarehouseOrder, EquipWarehouseOrderDetail


class GetSpare(APIView):
    @atomic
    def get(self, *args, **kwargs):
        last = EquipSpareErp.objects.filter(sync_date__isnull=False).order_by('sync_date').last()  # 第一次先在数据库插入一条假数据
        last_time = (last.sync_date + datetime.timedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S')
        url = 'http://10.1.10.136/zcxjws_web/zcxjws/pc/jc/getbjwlxx.io'
        try:
            res = requests.post(url=url, json={"syncDate": last_time}, timeout=10)
        except Exception:
            logger.info(msg=f'网络异常, time: {datetime.datetime.now()}')
            return '网络异常'
        if res.status_code != 200:
            logger.info(msg=f'请求失败, time: {datetime.datetime.now()}')
            return '请求失败'
        data = json.loads(res.content)
        if not data.get('flag'):
            logger.info(msg=f"{data.get('message')}, time: {datetime.datetime.now()}")
            return data.get('message')
        ret = data.get('obj')
        for item in ret:
            equip_component_type = EquipComponentType.objects.filter(component_type_name=item['wllb']).first()
            if not equip_component_type:
                code = EquipComponentType.objects.order_by('component_type_code').last().component_type_code
                component_type_code = code[0:4] + '%03d' % (int(code[-3:]) + 1) if code else '001'
                equip_component_type = EquipComponentType.objects.create(component_type_code=component_type_code,
                                                                         component_type_name=item['wllb'], use_flag=True)
                # logger.info(msg=f"同步失败,{item['wllb']}分类不存在, time: {datetime.datetime.now()}")
                # return f"同步失败,{item['wllb']}分类不存在"
            if item['state'] != '启用':
                continue
            if EquipSpareErp.objects.filter(spare_code=item['wlbh']).exists():
                continue
            EquipSpareErp.objects.update_or_create(
                defaults={"spare_code": item['wlbh'],
                          "spare_name": item['wlmc'],
                          "equip_component_type": equip_component_type,
                          "specification": item['gg'],
                          "unit": item['bzdwmc'],
                          "unique_id": item['wlxxid'],
                          "sync_date": datetime.datetime.now()
                          }, **{"unique_id": item['wlxxid']})
            # EquipSpareErp.objects.create(
            #     spare_code=item['wlbh'],
            #     spare_name=item['wlmc'],
            #     equip_component_type=equip_component_type,
            #     specification=item['gg'],
            #     unit=item['bzdwmc'],
            #     unique_id=item['wlxxid'],
            #     sync_date=datetime.datetime.now()
            # )
        return '同步完成'


class GetSpareOrder(APIView):
    @atomic
    def get(self):
        # 获取最新的单据
        last = EquipWarehouseOrder.objects.filter(processing_time__isnull=False).order_by('processing_time').last()  # 第一次先在数据库插入一条假数据
        last_time = (last.processing_time + datetime.timedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S')
        json_data = {"ztmc": "zcaj", "clsj": last_time, 'djbh': None}
        # 获取数据
        url = 'http://10.1.10.136/zcxjws_web/zcxjws/pc/zc/getkclld.io'
        try:
            res = requests.post(url=url, json=json_data, timeout=10)
        except Exception:
            logger.info(msg=f'网络异常, time: {datetime.datetime.now()}')
            return '网络异常'
        if res.status_code != 200:
            logger.info(msg=f'请求失败, time: {datetime.datetime.now()}')
            return '请求失败'
        data = json.loads(res.content)
        if not data.get('flag'):
            logger.info(msg=f"{data.get('message')}, time: {datetime.datetime.now()}")
            return data.get('message')
        lst = data.get('obj')
        for dic in lst:
            order = dic.get('lld')
            order_detail = dic.get('lldmx')  # list
            if EquipWarehouseOrder.objects.filter(barcode=order.get('djbh')):
                continue
            res = EquipWarehouseOrder.objects.filter(created_date__gt=datetime.date.today(), status__in=[1, 2, 3]).order_by('id').last()
            if res:
                order_id = res.order_id[:10] + str('%04d' % (int(res.order_id[11:]) + 1))
            else:
               order_id = 'RK' + str(datetime.date.today().strftime('%Y%m%d')) + '0001'
            order = EquipWarehouseOrder.objects.create(
                order_id=order_id,
                submission_department='设备科',
                status=1,
                barcode=order.get('djbh'),
                processing_time=order.get('clsj')
            )
            for spare in order_detail:
                equip_spare = EquipSpareErp.objects.filter(unique_id=spare.get('wlxxid')).first()
                if not equip_spare:
                    equip_spare = EquipSpareErp.objects.create(unique_id=spare.get('wlxxid'))
                    # logger.info(msg=f"调用库存领料单接口失败，单据中备件不存在，请先去同步erp备件, time: {datetime.datetime.now()}")
                    # continue
                kwargs = {'equip_warehouse_order': order,
                          'equip_spare': equip_spare,
                          'plan_in_quantity': spare.get('cksl')}
                EquipWarehouseOrderDetail.objects.create(**kwargs)
        return '请求成功'


if __name__ == '__main__':
    get_spare = GetSpare()
    get_spare.get()
    get_spare_order = GetSpareOrder()
    get_spare_order.get()
