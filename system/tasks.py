import os

import django
import requests
import logging

from mes import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()
logger = logging.getLogger('sync_log')

from system.models import DataSynchronization
from basics.models import GlobalCodeType

TYPE_CHOICE = (
        (1, '公共代码类型'),
        (2, '公共代码'),
        (3, '倒班管理'),
        (4, '倒班条目'),
        (5, '设备种类属性'),
        (6, '设备'),
        (7, '排班管理'),
        (8, '排班详情'),
        (9, '原材料')
    )


class BaseUploader(object):
    path = ""
    type = ""
    upload_fields = ()
    model = ''

    def __init__(self):
        if not all([self.path, self.type, self.upload_fields, self.model]):
            raise
        self.endpoint = settings.AUXILIARY_URL
        self.session = requests.Session()
        model_type = getattr(self, 'type', None)
        self.loaded = list(DataSynchronization.objects.filter(type=model_type).values_list('obj_id', flat=True))

    def request(self, data):
        url = self.endpoint + self.path
        resp = self.session.post(url, data=data)
        if resp.status_code != 201:
            raise Exception(resp.content)
        return resp.json()

    def upload(self):
        ret = self.model.objects.filter(id=13).values(*self.upload_fields)
        for data in ret:
            try:
                res = self.request(data)
                logger.info(res)
                DataSynchronization.objects.get_or_create(type=self.type, obj_id=data['id'])
            except Exception as e:
                logger.error('同步{}:{}失败  id:{}  msg:{}'.format(self.__doc__, data['type_no'], data['type_name'], e))
                continue


class GlobalCodeTypeUploader(BaseUploader):
    """公共代码类型"""
    path = "api/v1/basics/global-types/"
    type = 1
    upload_fields = ('id', 'type_no', 'type_name', 'description', 'use_flag')
    model = GlobalCodeType


class GlobalCodeUploader(BaseUploader):
    """公共代码"""
    pass


if __name__ == '__main__':
    pass