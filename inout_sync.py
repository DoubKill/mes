import datetime
import os

import django
from django.forms import model_to_dict

from inventory.models import *

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()


def material_sync():
    # 原材料出入库履历同步
    def inner():
        type_map = {1: "入库"}
        material_log = MaterialInventoryLog.objects.filter(order_type="入库").order_by('id').last()
        need_time = material_log.fin_time if material_log else datetime.datetime.strptime("2000-01-01 00:00:00", '%Y%m%d %H:%M:%S')
        wait_qs = MaterialInHistory.objects.using('wms').filter(task__fin_time__gt=need_time).select_related("task")[:1000].iterator()
        for i in wait_qs:
            # i.get("id
            i_dict = model_to_dict(i)
            inout_type = i_dict["inout_type"]
            i_dict["inout_type"] = type_map.get(inout_type) if type_map.get(inout_type) else "入库"
            temp = {**i_dict}
            temp.update(warehouse_no="0004",
                        warehouse_name="原材料库",
                        quality_status="暂无",
                        order_type="入库",
                        io_location="暂无",
                        dst_location="暂无",
                        inout_reason="物料入库",
                        initiator=i.task.initiator,
                        start_time=i.task.start_time,
                        fin_time=i.task.fin_time)
            MaterialInventoryLog.objects.create(**temp)
        pass

    def out():
        type_map = {1: "出库"}
        material_log = MaterialInventoryLog.objects.filter(order_type="出库").order_by('id').last()
        need_time = material_log.fin_time if material_log else datetime.datetime.strptime("2000-01-01 00:00:00",
                                                                                          '%Y%m%d %H:%M:%S')
        wait_qs = MaterialInHistory.objects.using('wms').filter(task__fin_time__gt=need_time).select_related("task")[
                  :1000].iterator()
        for i in wait_qs:
            # i.get("id
            i_dict = model_to_dict(i)
            inout_type = i_dict["inout_type"]
            i_dict["inout_type"] = type_map.get(inout_type) if type_map.get(inout_type) else "出库"
            temp = {**i_dict}
            temp.update(warehouse_no="0004",
                        warehouse_name="原材料库",
                        quality_status="暂无",
                        order_type="出库",
                        io_location="暂无",
                        dst_location="暂无",
                        inout_reason="物料出库投产",
                        initiator=i.task.initiator,
                        start_time=i.task.start_time,
                        fin_time=i.task.fin_time)
            MaterialInventoryLog.objects.create(**temp)
        pass

    inner()
    out()


def mix_rubber_sync():
    def inner():
        mix_rubber_log = InventoryLog.objects.filter(order_type="入库").order_by('id').last()
        need_time = mix_rubber_log.start_time if mix_rubber_log else datetime.datetime.strptime("2000-01-01 00:00:00", '%Y%m%d %H:%M:%S')
        wait_qs = MixGumInInventoryLog.objects.using('wms').filter(start_time__gt=need_time)[:1000].iterator()
        for i in wait_qs:
            # i.get("id
            i_dict = model_to_dict(i)
            temp = {**i_dict}
            temp.update(warehouse_no="0001",
                        warehouse_name="混料胶库",
                        quality_status="暂无",
                        order_type="入库",
                        io_location="暂无",
                        dst_location="暂无",
                        inout_reason="物料出库投产",
                        initiator=i.task.initiator,
                        start_time=i.task.start_time,
                        fin_time=i.task.fin_time)
            InventoryLog.objects.create(**temp)
        pass
    def out():
        mix_rubber_log = InventoryLog.objects.filter(order_type="入库").order_by('id').last()
        need_time = mix_rubber_log.start_time if mix_rubber_log else datetime.datetime.strptime("2000-01-01 00:00:00",
                                                                                              '%Y%m%d %H:%M:%S')
        wait_qs = MixGumInInventoryLog.objects.using('wms').filter(start_time__gt=need_time)[:1000].iterator()
        for i in wait_qs:
            # i.get("id
            i_dict = model_to_dict(i)
            temp = {**i_dict}
            temp.update(warehouse_no="0001",
                        warehouse_name="混炼胶库",
                        quality_status="暂无",
                        order_type="出库",
                        io_location="暂无",
                        dst_location="暂无",
                        inout_reason="物料出库投产",
                        initiator=i.task.initiator,
                        fin_time=i.task.fin_time)
            InventoryLog.objects.create(**temp)
        pass
    inner()
    out()

def final_lb_rubber_sync():
    pass
