# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/7/27
name: 
"""
from django.conf import settings

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

if settings.DEBUG:
    HF_CONF = {'host': '10.10.120.40', 'user': 'sa', 'password': 'Gz@admin', 'database': 'hongfang'}
else:
    HF_CONF = {'host': '10.4.24.25', 'user': 'sa', 'password': 'Admin123', 'database': 'wcs_aj_Storage'}

WMS_CONF = dict(host=settings.DATABASES['wms']['HOST'],
                user=settings.DATABASES['wms']['USER'],
                database=settings.DATABASES['wms']['NAME'],
                password=settings.DATABASES['wms']['PASSWORD'])
WMS_URL = "http://10.4.24.25:8169"   # 原材料库地址

TH_URL = "http://10.4.24.33:8169/"  # 炭黑库地址
TH_CONF = dict(host=settings.DATABASES['cb']['HOST'],
               user=settings.DATABASES['cb']['USER'],
               database=settings.DATABASES['cb']['NAME'],
               password=settings.DATABASES['cb']['PASSWORD'])

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
