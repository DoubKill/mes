# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/7/27
name: 
"""
from inventory.models import MixGumInInventoryLog, MixGumOutInventoryLog

COMMON_READ_ONLY_FIELDS = ('created_date', 'last_updated_date', 'delete_date',
                           'delete_flag', 'created_user', 'last_updated_user',
                           'delete_user')

PROJECT_API_TREE = {
    "basic": (),
    "system": (),
    "repice": (),
    "plan": (),
    "production": ('trains-feedbacks', 'pallet-feedbacks'),
}

SYNC_SYSTEM_NAME = "上辅机群控"

EQUIP_LIST = ['Z01', 'Z02', 'Z03', 'Z04', 'Z05', 'Z06', 'Z07', 'Z08', 'Z09', 'Z10', 'Z11', 'Z12', 'Z13', 'Z14', 'Z15']

BZ_USR = "GZ_MES"

BZ_PASSWORD = "mes@_123"

BZ_HOST = "10.4.23.101"

WMS_CONF = dict(host='10.4.24.25', user='sa', database='zhada_wms_zhongc', password='Admin123$')

STATION_LOCATION_MAP = {
    "一层前端": ["3", "4"],
    "一层后端": [],  # 暂未给出
    "二层前端": ["1", "2"],
    "二层后端": ["1", "2"]
}

INVENTORY_MAP = {
        ("bz", "混炼胶库", "no1"): {"入库": MixGumInInventoryLog, "出库": MixGumOutInventoryLog, "出入库": None},
        ("lb", "终炼胶库", "no2"): {},
        ("wms", "原材料库", "no3"): {},
    }


SEND_COUNT = 3