from django.test import TestCase

# Create your tests here.
import json
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from inventory.models import BzFinalMixingRubberInventory, MaterialInventory
from production.models import PalletFeedbacks
from quality.models import MaterialDealResult
from django.db.models import Q

pfb_set = PalletFeedbacks.objects.all()
mdr_set = MaterialDealResult.objects.all()
bz_set = BzFinalMixingRubberInventory.objects.using('bz').all()
mi_set = MaterialInventory.objects.all()

for mdr_obj in mdr_set:
    pfb_obj = PalletFeedbacks.objects.filter(lot_no=mdr_obj.lot_no).first()
    bz_obj = BzFinalMixingRubberInventory.objects.using('bz').filter(
        Q(container_no=pfb_obj.pallet_no) | Q(lot_no=mdr_obj.lot_no)).last()
    mi_obj = MaterialInventory.objects.filter(Q(container_no=pfb_obj.pallet_no) | Q(lot_no=mdr_obj.lot_no)).last()
    if bz_obj or mi_obj:
        print(mdr_obj, pfb_obj.pallet_no, pfb_obj.equip_no, pfb_obj.product_no, bz_obj, mi_obj)
