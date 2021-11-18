import os
import sys
import django

from django.db.models import Max

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes.settings')
django.setup()

from equipment.models import EquipWarehouseArea, EquipWarehouseLocation

def main():

    s = ['备品备件货架', '立体库Z8面1楼', '备品备件地面']
    for area_name in s:
        area = EquipWarehouseArea.objects.filter(area_name=area_name).first()
        if area:
            barcode = EquipWarehouseLocation.objects.filter(
                equip_warehouse_area=area).aggregate(
                location_barcode=Max('location_barcode'))
            location_barcode = str('%04d' % (int(barcode['location_barcode'][5:]) + 1)) if barcode.get(
                'location_barcode') else '0001'
            area_barcode = area.area_barcode[2:]
            """
            29C-6-12
            a最大取29，大写写字母,A,B,C三个,b最大取6，c最大取12
            """
            i1 = range(1, 30)
            i2 = ['A', 'B', 'C']
            i3 = range(1, 7)
            i4 = range(1, 13)

            for j1 in i1:
                for j2 in i2:
                    for j3 in i3:
                        for j4 in i4:
                            EquipWarehouseLocation.objects.create(
                            equip_warehouse_area=area,
                            location_name=f'{j1}{j2}-{j3}-{j4}',
                            desc=f'{j1}{j2}-{j3}-{j4}',
                            location_barcode='KW' + area_barcode + location_barcode,
                            )






if __name__ == '__main__':
    main()
