"""
同步不入库原因的数据
"""

import os
import sys
import django
import datetime
import logging

logger = logging.getLogger('error_log')


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes.settings')
django.setup()

from django.db.transaction import atomic
from production.models import RubberCannotPutinReason
from mes.common_code import SqlClient

EQUIP_CONFIG = {
    "Z01": {"HOST": "10.4.23.61", "USER": "sa", "NAME": "GZSFJ", "PASSWORD": "123"},
    "Z02": {"HOST": "10.4.23.62", "USER": "sa", "NAME": "GZSFJ", "PASSWORD": "123"},
    "Z03": {"HOST": "10.4.23.63", "USER": "sa", "NAME": "GZSFJ", "PASSWORD": "123"},
    "Z04": {"HOST": "10.4.23.64", "USER": "sa", "NAME": "GZSFJ", "PASSWORD": "123"},
    "Z05": {"HOST": "10.4.23.65", "USER": "sa", "NAME": "GZSFJ", "PASSWORD": "123"},
    "Z06": {"HOST": "10.4.23.66", "USER": "sa", "NAME": "GZSFJ", "PASSWORD": "123"},
    "Z07": {"HOST": "10.4.23.67", "USER": "sa", "NAME": "GZSFJ", "PASSWORD": "123"},
    "Z08": {"HOST": "10.4.23.68", "USER": "sa", "NAME": "GZSFJ", "PASSWORD": "123"},
    "Z09": {"HOST": "10.4.23.69", "USER": "sa", "NAME": "GZSFJ", "PASSWORD": "123"},
    "Z10": {"HOST": "10.4.23.70", "USER": "sa", "NAME": "GZSFJ", "PASSWORD": "123"},
    "Z11": {"HOST": "10.4.23.71", "USER": "sa", "NAME": "GZSFJ", "PASSWORD": "123"},
    "Z12": {"HOST": "10.4.23.72", "USER": "sa", "NAME": "GZSFJ", "PASSWORD": "123"},
    "Z13": {"HOST": "10.4.23.73", "USER": "sa", "NAME": "GZSFJ", "PASSWORD": "123"},
    "Z14": {"HOST": "10.4.23.74", "USER": "sa", "NAME": "GZSFJ", "PASSWORD": "123"},
    "Z15": {"HOST": "10.4.23.75", "USER": "sa", "NAME": "GZSFJ", "PASSWORD": "123"},
}


@atomic
def main():
    equip_list = ['Z%.2d' % i for i in range(1, 16)]
    for equip in equip_list:
        obj = RubberCannotPutinReason.objects.filter(machine_no=equip).order_by('id').last()
        if obj:
            last_time = obj.input_datetime.strftime('%Y-%m-%d %H:%M:%S')
        else:
            last_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sql = f"""
                    SELECT
                    a.cause,
                    b.datetime,
                    a.machineno,
                    a.lotNO,
                    b.palletno,
                    b.producecode,
                    b.actual_weight,
                    a.lasttime,
                FROM
                    collect_ploy_cause AS a
                    LEFT JOIN collect_ploy AS b ON a.LotNO = b.LotNO 
                WHERE a.lasttime > '{last_time}'
                """
        equip_conf = dict(
            host=EQUIP_CONFIG[equip]['HOST'],
            user=EQUIP_CONFIG[equip]['USER'],
            database=EQUIP_CONFIG[equip]['NAME'],
            password=EQUIP_CONFIG[equip]['PASSWORD'])
        try:
            sc = SqlClient(sql=sql, **equip_conf)
        except:
            logger.error(msg=f'{equip}机台数据库连接失败{datetime.datetime.now()}')
            continue
        temp = sc.all()
        sc.close()
        for item in temp:
            if item[8]:
                RubberCannotPutinReason.objects.create(
                    reason_name=item[0].strip(),
                    factory_date=item[1],
                    machine_no='Z%.2d' % item[2],
                    pallet_no=item[3].strip(),
                    lot_no=item[4].strip(),
                    production_no=item[5].strip(),
                    actual_weight=item[6],
                    input_datetime=item[7],
                )
            else:  # 删除的不入库原因，mes中对应的也删除
                RubberCannotPutinReason.objects.filter(lot_no=item[4]).delete()


if __name__ == '__main__':
    main()
