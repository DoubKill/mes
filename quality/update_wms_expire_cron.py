"""
    更新wms过期物料信息
"""
import os
import sys
from datetime import datetime, timedelta

import django


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from inventory.models import WmsInventoryStock, WmsInventoryMaterial, WMSExceptHandle
from django.db.models import Min


def main():
    now_time = datetime.now()
    for m in WmsInventoryMaterial.objects.using('wms').filter(is_validity=1, material_no='3C25B2A7-84B9-40D9-BA8C-02100EA3D5AD'):
        period_of_validity = m.period_of_validity
        min_storage_time = WmsInventoryStock.objects.using('wms').filter(
            material_no=m.material_no).aggregate(min_time=Min('in_storage_time'))['min_time']
        if min_storage_time:
            min_expire_inventory_time = now_time - timedelta(days=period_of_validity)
            if min_storage_time >= min_expire_inventory_time:
                continue
            else:
                expired_batch_data = set(WmsInventoryStock.objects.using('wms').filter(
                    material_no=m.material_no,
                    in_storage_time__lt=min_expire_inventory_time
                ).values_list('batch_no', flat=True))
                for batch in expired_batch_data:
                    if WMSExceptHandle.objects.filter(batch_no=batch, material_code=m.material_no).exists():
                        min_expire_inventory_time -= timedelta(days=period_of_validity)
                    WmsInventoryStock.objects.using('wms').filter(
                        material_no=m.material_no,
                        batch_no=batch,
                        in_storage_time__lt=min_expire_inventory_time
                    ).update(quality_status=4)


if __name__ == '__main__':
    main()