import os
from datetime import datetime, timedelta

import django
from django.db.models import Sum, Q

from plan.utils import calculate_equip_recipe_avg_mixin_time, calculate_product_stock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()


from basics.models import Equip, GlobalCode
from plan.models import ProductClassesPlan, SchedulingEquipCapacity, SchedulingProductDemandedDeclare, \
    SchedulingRecipeMachineSetting, SchedulingResult
from production.models import TrainsFeedbacks
from inventory.models import BzFinalMixingRubberInventoryLB, BzFinalMixingRubberInventory, ProductStockDailySummary
from recipe.models import ProductBatching, ProductBatchingDetail


class Node(object):
    """节点"""

    def __init__(self, value):
        self.value = value
        self.next = None


class APSLink(object):

    def __init__(self, head=None):
        self.head = head
        self.total_time = 0

    def is_full(self):
        return self.total_time > 24