"""
    小料对接接口封装
"""
import json
import re
from datetime import datetime
from decimal import Decimal

import requests
from django.db.models import Sum, Q, Count
from django.db.transaction import atomic
from suds.client import Client

from basics.models import WorkSchedulePlan
from inventory.conf import cb_ip, cb_port
from inventory.utils import wms_out
from mes.settings import DATABASES
from plan.models import BatchingClassesPlan
from recipe.models import ProductBatching, ProductBatchingDetail, ProductBatchingEquip
from terminal.models import WeightTankStatus, RecipePre, RecipeMaterial, Plan, Bin, ToleranceRule


class INWeighSystem(object):
    equip_no_ip = {k: v.get("HOST", "10.4.23.79") for k, v in DATABASES.items()}

    def __init__(self, equip_no: str):
        url = f"http://{self.equip_no_ip.get(equip_no, '10.4.23.79')}:9000/xlserver?wsdl"
        self.weigh_system = Client(url)

    def stop(self, data):
        """

        :param data: stop_data = {
                        "plan_no": "210517091223",  # 计划操作编号
                        "action": "1",  # 具体计划的操作方式
                    }
        :return:
        """
        stop_plan = self.weigh_system.service.stop_plan(*data.values())  # 停止计划
        return stop_plan

    def door_info(self, data):
        """

        :param data:  door_info = {
                        "开门信号1": "1",   # 称量系统 A料仓 1~11  例开A6号料仓门传"6"
                        "开门信号2": "2"    # 称量系统 B料仓 1~11  例开B6号料仓门传"6"
                    }
        :return:
        """
        door_info = self.weigh_system.service.open_door(*data.values())  # 开门信号及料仓信号反馈
        return door_info

    def update_trains(self, data):
        """
        :param data: update_trains = {
                        "plan_no": "210517091223",  # 计划操作编号
                        "action": "1",               # 具体计划的操作方式
                        "num": 122                  # 需修改的车次
                    }
        :return:
        """
        update_trains = self.weigh_system.service.update_num(*data.values())  # 更新计划车次
        return update_trains

    def reload_plan(self, data):
        """

        :param data: reload_data = {
                        "plan_no": "210517091223",  # 计划操作编号
                        "action": "1",  # 具体计划的操作方式
                    }
        :return:
        """
        reload_plan = self.weigh_system.service.reload_plan(*data.values())  # 重传计划/配方
        return reload_plan

    def issue_plan(self, data):
        """
        mes上调用易控接口将计划下发到plc
        :param data: issue_data = {
                "plan_no": "99c4fd9e914f11eb88870050568ff1ef",
                "recipe_no": "	C-FM-C590-06",
                "num": 100,
                "action": "1"
                }
        :return:
        """
        issue = self.weigh_system.service.plan_down(*data.values())  # 重传计划/配方
        return issue

    def add_plan(self, data):
        """
        数据库写入计划之后调用接口通知易控
        :param data: plan_data = {
                        "plan_no": "210517091223",  # 计划操作编号
                        "action": "1",  # 具体计划的操作方式
                    }
        :return:
        """
        add = self.weigh_system.service.plan_add(*data.values())
        return add


class TankStatusSync(object):
    equip_no_ip = {k: v.get("HOST", "10.4.23.79") for k, v in DATABASES.items()}

    def __init__(self, equip_no: str):
        self.url = f"http://{self.equip_no_ip.get(equip_no, '10.4.23.79')}:9000/xlserver"
        self.queryset = WeightTankStatus.objects.filter(equip_no=equip_no, use_flag=True)
        self.equip_no = equip_no

    @atomic
    def sync(self, signal_a='0', signal_b='0'):
        """
        signal_a: 开门信号1['1'表示开1A罐门, 默认'0'表示查询料罐状态]
        signal_b: 开门信号1['2'表示开2B罐门, 默认'0'表示查询料罐状态]
        """
        headers = {"Content-Type": "text/xml; charset=utf-8",
                   "SOAPAction": "http://tempuri.org/INXWebService/open_door"}
        send_data = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
                   <soapenv:Header/>
                   <soapenv:Body>
                      <tem:open_door>
                         <!--Optional:-->
                         <tem:开门信号1>{}</tem:开门信号1>
                         <!--Optional:-->
                         <tem:开门信号2>{}</tem:开门信号2>
                      </tem:open_door>
                   </soapenv:Body>
                </soapenv:Envelope>""".format(signal_a, signal_b)
        door_info = requests.post(self.url, data=send_data.encode('utf-8'), headers=headers, timeout=5)
        res = door_info.content.decode('utf-8')
        rep_json = re.findall(r'<open_doorResult>(.*)</open_doorResult>', res)[0]
        data = json.loads(rep_json)
        if not data:
            raise ValueError('获取料罐信息失败, 返回数据为空')
        for x in self.queryset:
            temp_no = x.tank_no
            # 万龙表里的罐号跟接口里的罐号不一致，需要做个转换
            tank_no = temp_no[-1] + temp_no[0:-1]
            high_level = tank_no + "_high_level"
            low_level = tank_no + "_low_level"
            material_name = tank_no + "_name"
            door_status = tank_no + "_door"
            x.open_flag = data.get(door_status) if data.get(door_status) else False
            # 默认正常
            status = 3
            # 高位有料表示高位报警
            if data.get(high_level):
                status = 2
            # 低位有料表示地位报警
            elif data.get(low_level):
                status = 1
            x.status = status
            x.material_name = data.get(material_name)
            x.material_no = data.get(material_name)
            x.save()


class CarbonDeliverySystem(object):
    """获取炭黑罐与输送线信息"""
    def __init__(self):
        # url = "http://10.4.23.25:9000/shusong?wsdl"
        # self.carbon_system = Client(url)
        self.url = "http://10.4.23.25:9000/shusong"

    def carbon_info(self):
        # carbon_tank_details = json.loads(self.carbon_system.service.GetCarbonTankLevel())
        headers = {"Content-Type": "text/xml; charset=utf-8",
                   "SOAPAction": "http://tempuri.org/INXWebService/GetCarbonTankLevel"}
        send_data = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
                       <soapenv:Header/>
                       <soapenv:Body>
                          <tem:GetCarbonTankLevel>
                             <!--Optional:-->
                             <tem:MachineNumber>1</tem:MachineNumber>
                          </tem:GetCarbonTankLevel>
                       </soapenv:Body>
                    </soapenv:Envelope>"""
        door_info = requests.post(self.url, data=send_data.encode('utf-8'), headers=headers, timeout=5)
        res = door_info.content.decode('utf-8')
        rep_json = re.findall(r'<GetCarbonTankLevelResult>(.*)</GetCarbonTankLevelResult>', res)[0]
        carbon_tank_details = json.loads(rep_json)

        level_info = {0: '报警位', 1: '高位', 2: '中位', 3: '低位'}
        carbon_tank_info = {}
        for i in carbon_tank_details:
            equip_id = i[-5: -2]
            tail_info = i[-6:]
            if equip_id not in carbon_tank_info:
                carbon_tank_info[equip_id] = []
            level_status = carbon_tank_details["tank_level_status" + tail_info]
            tank_level_status = '空罐' if level_status.find('1') == -1 else level_info[level_status.find('1')]
            tank_material_name = carbon_tank_details["tank_material_name" + tail_info]
            item = {'tank_no': int(i[-1:]), "tank_level_status": tank_level_status, "tank_material_name": tank_material_name}
            if item not in carbon_tank_info[equip_id]:
                carbon_tank_info[equip_id].append(item)
        return carbon_tank_info

    def line_info(self):
        # line_info = json.loads(self.carbon_system.service.FeedingPortToCarbonTankRelation())
        headers = {"Content-Type": "text/xml; charset=utf-8",
                   "SOAPAction": "http://tempuri.org/INXWebService/FeedingPortToCarbonTankRelation"}
        send_data = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
                       <soapenv:Header/>
                       <soapenv:Body>
                          <tem:FeedingPortToCarbonTankRelation>
                             <!--Optional:-->
                             <tem:Request>1</tem:Request>
                          </tem:FeedingPortToCarbonTankRelation>
                       </soapenv:Body>
                    </soapenv:Envelope>"""
        door_info = requests.post(self.url, data=send_data.encode('utf-8'), headers=headers, timeout=5)
        res = door_info.content.decode('utf-8')
        rep_json = re.findall(r'<FeedingPortToCarbonTankRelationResult>(.*)</FeedingPortToCarbonTankRelationResult>', res)[0]
        line_info = json.loads(rep_json)
        return line_info


def out_task_carbon(task_id, station_no, material_no, material_name, need_weight):
    url = f"http://{cb_ip}:{cb_port}/MESApi/AllocateWeightDelivery"
    data = {
            "taskNumber": task_id,
            "entranceCode": station_no,
            "allocationInventoryDetails": [{
                "materialCode": material_no,
                "materialName": material_name,
                "weightOfActual ": need_weight
            }]
        }
    try:
        rep_dict = wms_out(url, data)
    except:
        raise ConnectionError("原材料wms调用失败，请联系wms维护人员")
    return rep_dict


def material_out_barcode(bar_code):
    """获取出库条码信息"""
    url = 'http://10.1.10.157:9091/WebService.asmx?wsdl'
    try:
        client = Client(url)
        json_data = {"tofac": "AJ1", "tmh": bar_code}
        data = client.service.FindZcdtmList(json.dumps(json_data))
    except Exception:
        raise ValueError('网络异常')
    data = json.loads(data)
    ret = data.get('Table')
    return ret[0] if ret else ''


# @atomic()
def issue_recipe(recipe_no, equip_no):
    recipe = ProductBatching.objects.exclude(used_type__in=[6, 7]).filter(stage_product_batch_no=recipe_no,
                                                                 dev_type__isnull=False, batching_type=2).last()
    weigh_recipe_name = f"{recipe.stage_product_batch_no}({recipe.dev_type.category_no})"
    time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    temp = recipe.weight_cnt_types.filter(delete_flag=False, package_type=1).last()
    weight = temp.weight_details.filter(delete_flag=False).aggregate(total_weight=Sum('standard_weight'))[
        'total_weight'] if temp else 0
    error = temp.weight_details.filter(delete_flag=False).aggregate(total_error=Sum('standard_error'))[
        'total_error'] if temp else 0
    default = {
        "ver": recipe.versions,
        "remark1": recipe.dev_type.category_no,
        "weight": weight,
        "error": error,
        "time": time_now,
        "use_not": 0 if recipe.used_type == 4 else 1
    }
    RecipePre.objects.using(equip_no).update_or_create(defaults=default, **{
        "name": weigh_recipe_name})
    weigh_details = temp.weight_details.filter(delete_flag=False) if temp else []
    weigh_data_list = [
        RecipeMaterial(recipe_name=weigh_recipe_name, name=x.material.material_name, weight=x.standard_weight,
                       error=x.standard_error, time=time_now) for x in weigh_details]
    RecipeMaterial.objects.using(equip_no).filter(recipe_name=weigh_recipe_name).delete()
    RecipeMaterial.objects.using(equip_no).bulk_create(weigh_data_list)


# @atomic()
def issue_plan(plan_no : str, equip_no : str, username: str="mes") -> str:
    plan = BatchingClassesPlan.objects.filter(plan_batching_uid=plan_no).last()
    time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    weigh_recipe_name = f"{plan.weigh_cnt_type.product_batching.stage_product_batch_no}({plan.weigh_cnt_type.product_batching.dev_type.category_no})"
    default = {
        "recipe": weigh_recipe_name,
        "recipe_ver": plan.weigh_cnt_type.product_batching.versions,
        "starttime": time_now,
        "grouptime": plan.work_schedule_plan.classes.global_name,
        "oper": username,
        "state": "等待",
        "setno": plan.plan_package,
        "actno": 0,
        "order_by": 1,
        # "date_time": plan.work_schedule_plan.plan_schedule.day_time.strftime('%Y-%m-%d'),
        "date_time": datetime.now().strftime('%Y-%m-%d'),
        "addtime": time_now
    }
    instance, flag = Plan.objects.using(equip_no).get_or_create(defaults=default, **{
        "planid": plan_no})
    if flag == False:
        return "配料计划已下达"
    return "配料计划下达成功"


@atomic()
def sync_tank(equip_no):
    queryset = WeightTankStatus.objects.filter(equip_no=equip_no)
    # 建议料罐表里增加条码字段
    for x in queryset:
        tank_no = x.get("tank_no")
        default = {
            "name": x.get("material_name"),
            "code": x.get("barcode")
        }
        Bin.objects.using(equip_no).update_or_create(default=default, **{"bin": tank_no})


def delete_plan(equip_no, plan_no):
    Plan.objects.using(equip_no).filter(planid=plan_no).delete()


class CLSystem(object):
    equip_no_ip = {k: v.get("HOST", "10.4.23.79") for k, v in DATABASES.items()}

    def __init__(self, equip_no: str):
        self.url = f"http://{self.equip_no_ip.get(equip_no, '10.4.23.79')}:9000/xlserver?wsdl"

    def door_info(self, door_1, door_2):
        headers = {"Content-Type": "text/xml; charset=utf-8",
                   "SOAPAction": "http://tempuri.org/INXWebService/open_door"}
        data = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
       <soapenv:Header/>
       <soapenv:Body>
          <tem:open_door>
             <!--Optional:-->
             <tem:开门信号1>{}</tem:开门信号1>
             <!--Optional:-->
             <tem:开门信号2>{}</tem:开门信号2>
          </tem:open_door>
       </soapenv:Body>
    </soapenv:Envelope>""".format(door_1, door_2)
        ret = requests.post(self.url, data=data.encode('utf-8'), headers=headers, timeout=5)
        return ret

    def add_plan(self, plan_no):
        headers = {"Content-Type": "text/xml; charset=utf-8",
                   "SOAPAction": "http://tempuri.org/INXWebService/plan_add"}

        data = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
               <soapenv:Header/>
               <soapenv:Body>
                  <tem:plan_add>
                     <!--Optional:-->
                     <tem:plan_no>{}</tem:plan_no>
                     <!--Optional:-->
                     <tem:action>1</tem:action>
                  </tem:plan_add>
               </soapenv:Body>
            </soapenv:Envelope>""".format(plan_no)
        ret = requests.post(self.url, data=data.encode('utf-8'), headers=headers, timeout=5)
        return ret

    def issue_plan(self, plan_no, recipe_no, num):
        headers = {"Content-Type": "text/xml; charset=utf-8",
                   "SOAPAction": "http://tempuri.org/INXWebService/plan_down"}

        data = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
               <soapenv:Header/>
               <soapenv:Body>
                  <tem:plan_down>
                     <!--Optional:-->
                     <tem:plan_no>{}</tem:plan_no>
                     <!--Optional:-->
                     <tem:recipe_no>{}</tem:recipe_no>
                     <!--Optional:-->
                     <tem:num>{}</tem:num>
                     <!--Optional:-->
                     <tem:action>1</tem:action>
                  </tem:plan_down>
               </soapenv:Body>
            </soapenv:Envelope>""".format(plan_no, recipe_no, num)
        ret = requests.post(self.url, data=data.encode('utf-8'), headers=headers, timeout=5)
        return ret

    def reload_plan(self, plan_no, recipe_no):
        headers = {"Content-Type": "text/xml; charset=utf-8",
                   "SOAPAction": "http://tempuri.org/INXWebService/reload_plan"}

        data = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
               <soapenv:Header/>
               <soapenv:Body>
                  <tem:reload_plan>
                     <!--Optional:-->
                     <tem:plan_no>{}</tem:plan_no>
                     <!--Optional:-->
                     <tem:action>1</tem:action>
                     <!--Optional:-->
                     <tem:recipe_no>{}</tem:recipe_no>
                  </tem:reload_plan>
               </soapenv:Body>
            </soapenv:Envelope>""".format(plan_no, recipe_no)
        ret = requests.post(self.url, data=data.encode('utf-8'), headers=headers, timeout=5)
        return ret

    def stop(self, plan_no):
        headers = {"Content-Type": "text/xml; charset=utf-8",
                   "SOAPAction": "http://tempuri.org/INXWebService/stop_plan"}

        data = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
               <soapenv:Header/>
               <soapenv:Body>
                  <tem:stop_plan>
                     <!--Optional:-->
                     <tem:plan_no>{}</tem:plan_no>
                     <!--Optional:-->
                     <tem:action>1</tem:action>
                  </tem:stop_plan>
               </soapenv:Body>
            </soapenv:Envelope>""".format(plan_no)
        ret = requests.post(self.url, data=data.encode('utf-8'), headers=headers, timeout=5)
        return ret

    def update_trains(self, plan_no, number):
        headers = {"Content-Type": "text/xml; charset=utf-8",
                   "SOAPAction": "http://tempuri.org/INXWebService/update_num"}

        data = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
               <soapenv:Header/>
               <soapenv:Body>
                  <tem:update_num>
                     <!--Optional:-->
                     <tem:plan_no>{}</tem:plan_no>
                     <!--Optional:-->
                     <tem:action>1</tem:action>
                     <!--Optional:-->
                     <tem:number>{}</tem:number>
                  </tem:update_num>
               </soapenv:Body>
            </soapenv:Envelope>""".format(plan_no, number)
        ret = requests.post(self.url, data=data.encode('utf-8'), headers=headers, timeout=5)
        return ret


def get_tolerance(batching_equip, standard_weight, material_name=None, project_name='单个化工重量', only_num=None):
    if not standard_weight:
        standard_weight = 0
    standard_weight = Decimal(standard_weight)
    # 人工单配细料硫磺包
    if batching_equip:
        type_name = '硫磺' if batching_equip.startswith('S') else '细料'
        if '单个' not in project_name:
            project_name = f"整包{type_name}重量"
        rule = ToleranceRule.objects.filter(distinguish__keyword_name=f"{type_name}称量",
                                            project__keyword_name=project_name, use_flag=True,
                                            small_num__lt=standard_weight, big_num__gte=standard_weight).first()
    # 人工单配配方或通用(所有量程)
    else:
        rule = ToleranceRule.objects.filter(distinguish__re_str__icontains=material_name, use_flag=True).first()
    tolerance = f"{rule.handle.keyword_name}{rule.standard_error}{rule.unit}" if rule else ""
    if tolerance:
        if rule.unit == '%':
            handle_num = round(rule.standard_error / 100 * standard_weight, 3)
            tolerance = f"{rule.handle.keyword_name}{handle_num}kg" if not only_num else handle_num
        else:
            if only_num:
                tolerance = rule.standard_error
    else:
        if only_num:
            tolerance = 0
    return tolerance


def get_manual_materials(product_no, dev_type, batching_equip, equip_no=None):
    product_no_dev = re.split(r'\(|\（|\[', product_no)[0]
    if not equip_no:
        equip_recipes = ProductBatchingEquip.objects.filter(is_used=True, type=4,
                                                            product_batching__stage_product_batch_no=product_no_dev,
                                                            product_batching__dev_type__category_name=dev_type)\
            .values('equip_no').annotate(num=Count('id', filter=Q(feeding_mode__startswith='C')))
        if not equip_recipes:
            raise ValueError(f"未找到配方{product_no}配料信息")
        handle_equip_recipe = [i['equip_no'] for i in equip_recipes if i['num'] == 0]
        if not handle_equip_recipe:
            raise ValueError(f"未找到配方{product_no}通用配料信息")
        equip_no = handle_equip_recipe[0]
    mes_recipe = ProductBatchingEquip.objects.filter(is_used=True, equip_no=equip_no, type=4,
                                                     feeding_mode__startswith=batching_equip[0],
                                                     product_batching__stage_product_batch_no=product_no_dev,
                                                     product_batching__dev_type__category_name=dev_type)
    # 机配物料
    machine_material = list(RecipeMaterial.objects.using(batching_equip).filter(recipe_name=product_no).values_list('name', flat=True))
    # 人工配物料信息
    manual_material = []
    for i in mes_recipe:
        if i.handle_material_name not in machine_material:
            manual_material.append({'material_name': i.material.material_name, 'tolerance': i.cnt_type_detail_equip.standard_error,
                                    'material__material_name': i.material.material_name,
                                    'standard_weight': i.cnt_type_detail_equip.standard_weight})
    return manual_material


def get_current_factory_date():
    # 获取当前时间的工厂日期，开始、结束时间
    now = datetime.now()
    current_work_schedule_plan = WorkSchedulePlan.objects.filter(
        start_time__lte=now,
        end_time__gte=now,
        plan_schedule__work_schedule__work_procedure__global_name='密炼'
    ).first()
    res = {'factory_date': current_work_schedule_plan.plan_schedule.day_time, 'classes': current_work_schedule_plan.classes.global_name} if current_work_schedule_plan else {}
    return res
