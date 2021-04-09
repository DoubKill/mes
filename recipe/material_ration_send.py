import logging
import os
import sys

import django
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from inventory.conf import wms_ip, wms_port
from recipe.models import MaterialAttribute

logger = logging.getLogger("send_log")


def send(material_no, material_name, ratio):
    url = f"http://{wms_ip}:{wms_port}/MESApi/UpdateMaterialTestingRatio"
    body = {
        "MaterialCode": material_no,
        "MaterialName": material_name,
        "Ratio ": ratio
    }
    try:
        ret = requests.post(url, data=body)
        data = ret.json()
        if data.get("state"):
            MaterialAttribute.objects.filter(material__material_no=material_no,
                                             material__material_name=material_name).update(send_flag=True)
    except Exception as e:
        logger.error(f"抽检比例发送异常:{e}")


if __name__ == '__main__':
    ratio_set = MaterialAttribute.objects.filter(send_flag=False).select_related("material")
    for x in ratio_set:
        send(x.material.material_no, x.material.material_name, x.ratio)
