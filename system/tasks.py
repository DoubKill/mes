import os
import sys

import django
import requests
import logging

from django.conf import settings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()
logger = logging.getLogger('sync_log')

from system.models import DataSynchronization
from basics.models import GlobalCodeType, GlobalCode, WorkSchedule, ClassesDetail, EquipCategoryAttribute, Equip, \
    PlanSchedule, WorkSchedulePlan
from recipe.models import Material, ProductInfo, MaterialAttribute, MaterialSupplier

TYPE_CHOICE = (
    (1, '公共代码类型'),
    (2, '公共代码'),
    (3, '倒班管理'),
    (4, '倒班条目'),
    (5, '设备种类属性'),
    (6, '设备'),
    (7, '排班管理'),
    (8, '排班详情'),
    (9, '原材料'),
    (10, '胶料代码'),
    (11, '原材料属性'),
    (12, '原材料产地')
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
        ret = self.model.objects.exclude(id__in=self.loaded).values(*self.upload_fields)
        for data in ret:
            try:
                res = self.request(data)
                logger.info(res)
                DataSynchronization.objects.create(type=self.type, obj_id=data['id'])
            except Exception as e:
                logger.error('同步{}失败,  id:{},  data:{}, message:{}'.format(self.__doc__, data['id'], data, e))
                continue


class GlobalCodeTypeUploader(BaseUploader):
    """公共代码类型"""
    path = "api/v1/datain/global_code_type_receive/"
    type = 1
    upload_fields = ('id', 'type_no', 'type_name', 'description', 'use_flag')
    model = GlobalCodeType


class GlobalCodeUploader(BaseUploader):
    """公共代码"""
    path = "api/v1/datain/global_code-receive/"
    type = 2
    upload_fields = ('id', 'global_type__type_no', 'global_no', 'global_name', 'description', 'use_flag')
    model = GlobalCode


class WorkScheduleUploader(BaseUploader):
    """倒班管理"""
    path = "api/v1/datain/work_schedule-receive/"
    type = 3
    upload_fields = ('id', 'schedule_no', 'schedule_name', 'period', 'description', 'use_flag', 'work_procedure__global_no')
    model = WorkSchedule


class ClassesDetailUploader(BaseUploader):
    """倒班条目"""
    path = "api/v1/datain/classes_detail_receive/"
    type = 4
    upload_fields = ('id', 'work_schedule__schedule_no', 'classes__global_no', 'description', 'start_time', 'end_time')
    model = ClassesDetail


class EquipCategoryAttributeUploader(BaseUploader):
    """设备种类属性"""
    path = "api/v1/datain/equip_category_attribute_receive/"
    type = 5
    upload_fields = (
        'id', 'equip_type__global_no', 'category_no', 'category_name', 'volume', 'description', 'process__global_no',
        'use_flag')
    model = EquipCategoryAttribute


class EquipUploader(BaseUploader):
    """设备"""
    path = "api/v1/datain/equip_receive/"
    type = 6
    upload_fields = (
        'id', 'category__category_no', 'parent', 'equip_no', 'equip_name', 'use_flag', 'description', 'count_flag',
        'equip_level__global_no')
    model = Equip


class PlanScheduleUploader(BaseUploader):
    """排班管理"""
    path = "api/v1/datain/plan_schedule_receive/"
    type = 7
    upload_fields = ('id', 'plan_schedule_no', 'day_time', 'work_schedule__schedule_no')
    model = PlanSchedule


class WorkSchedulePlanUploader(BaseUploader):
    """排班详情"""
    path = "api/v1/datain/work_schedule_plan_receive/"
    type = 8
    upload_fields = (
        'id', 'work_schedule_plan_no', 'classes__global_no', 'rest_flag', 'plan_schedule__plan_schedule_no',
        'group__global_no', 'start_time', 'end_time')
    model = WorkSchedulePlan


class MaterialUploader(BaseUploader):
    """原材料"""
    path = "api/v1/datain/material_receive/"
    type = 9
    upload_fields = ('id', 'material_no', 'material_name', 'for_short', 'material_type__global_no', 'use_flag')
    model = Material


class ProductInfoUploader(BaseUploader):
    """原材料"""
    path = "api/v1/datain/product_info_receive/"
    type = 10
    upload_fields = ('id', 'product_no', 'product_name')
    model = ProductInfo


class MaterialAttributeUploader(BaseUploader):
    """原材料属性"""
    path = "api/v1/datain/material_attr_receive/"
    type = 11
    upload_fields = ('id', 'material__material_no', 'safety_inventory', 'period_of_validity', 'validity_unit')
    model = MaterialAttribute


class MaterialSupplierUploader(BaseUploader):
    """原材料产地"""
    path = "api/v1/datain/material_supplier_receive/"
    type = 12
    upload_fields = ('id', 'material__material_no', 'supplier_no', 'provenance', 'use_flag')
    model = MaterialSupplier


if __name__ == '__main__':

    for uploader in (GlobalCodeTypeUploader, GlobalCodeUploader, WorkScheduleUploader,
                     ClassesDetailUploader, EquipCategoryAttributeUploader, EquipUploader, PlanScheduleUploader,
                     WorkSchedulePlanUploader, MaterialUploader, ProductInfoUploader,
                     MaterialAttributeUploader, MaterialSupplierUploader):
        uploader().upload()
