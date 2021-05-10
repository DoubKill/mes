# -*- coding: UTF-8 -*-

import os
import sys
import logging
import django
from django.db.models import Max

from suds.client import Client
import json
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from recipe.models import ZCMaterial

logger = logging.getLogger("error_log")


def main():
    url = 'http://10.1.10.157:9091/WebService.asmx?wsdl'
    max_create_date = ZCMaterial.objects.aggregate(max_time=Max('created_date'))['max_time']
    if not max_create_date:
        max_create_date = '2021-01-01 00:00:00'
    try:
        client = Client(url)
        json_data = {"bgsj": str(max_create_date)}
        data = client.service.FindWlxxInfo(json.dumps(json_data))
        data = json.loads(data)
    except Exception as e:
        logger.error('connect zc erp system error: {}'.format(e))
        return
    if isinstance(data, list):
        for item in data:
            default = {'wlxxid': item.pop('wlxxid', None)}
            kwargs = {
                'material_no': item['wlbh'],
                'material_name': item['wlmc'],
                'jybj': item['jybj'],
                'bgsj': item['bgsj'],
            }
            ZCMaterial.objects.update_or_create(defaults=default, **kwargs)


if __name__ == '__main__':
    main()