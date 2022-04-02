import os
from datetime import datetime, timedelta

import django
from django.db.models import Sum, Q

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()


from basics.models import Equip, GlobalCode
from plan.models import ProductClassesPlan, SchedulingEquipCapacity, SchedulingProductDemandedDeclare, \
    SchedulingRecipeMachineSetting, SchedulingResult
from production.models import TrainsFeedbacks
from inventory.models import BzFinalMixingRubberInventoryLB, BzFinalMixingRubberInventory, ProductStockDailySummary
from recipe.models import ProductBatching, ProductBatchingDetail


# TODO 根据历史数据，计算各个配方在不同机台每车的平均密炼时间（根据trains_feedbacks表，每天定时任务去计算一次）
# TODO 统计胶片库库存数据（根据基础设置的时间点，每天定时统计）

def calculate_equip_left_time():
    """
        计算机台计划剩余密炼时间（秒）
    """
    ret = {}
    for equip in Equip.objects.filter(category__equip_type__global_name='密炼设备').order_by('equip_no'):
        current_plan = ProductClassesPlan.objects.filter(
            equip__equip_no=equip.equip_no, status='运行中').order_by('id').last()
        if current_plan:
            last_trains_feedback = TrainsFeedbacks.objects.filter(
                plan_classes_uid=current_plan.plan_classes_uid).order_by('id').last()
            product_no = current_plan.product_batching.stage_product_batch_no
            actual_trains = last_trains_feedback.actual_trains if last_trains_feedback else 0
            plan_trains = current_plan.plan_trains
            left_trains = plan_trains - actual_trains
            avg_train_mixin_time = calculate_equip_recipe_avg_mixin_time(equip.equip_no, product_no)
            left_time = left_trains * avg_train_mixin_time
        else:
            left_time = 0
        ret[equip.equip_no] = left_time
    # print(ret)


def calculate_product_available_time():
    """
        根据分厂每日申报量，统计剩余可用天数（FM和RFM段次的料）
    """
    data = SchedulingProductDemandedDeclare.objects.filter(
        factory_date=datetime.now().date()
    ).values('product_no').annotate(s=Sum('today_demanded')).values('product_no', 's')
    ret = []
    for item in data:
        # 查询胶片库存量（终炼）
        t1 = BzFinalMixingRubberInventoryLB.objects.using('lb').filter(
              Q(material_no__icontains='-FM-{}'.format(item['product_no'])) |
              Q(material_no__icontains='-RFM-{}'.format(item['product_no']))
             ).aggregate(s=Sum('total_weight'))['s']
        t2 = BzFinalMixingRubberInventory.objects.using('bz').filter(
              Q(material_no__icontains='-FM-{}'.format(item['product_no'])) |
              Q(material_no__icontains='-RFM-{}'.format(item['product_no']))
             ).aggregate(s=Sum('total_weight'))['s']
        total_weight = float(t1) if t1 else 0 + float(t2) if t2 else 0
        ret.append(
            {'stock_weight': round(total_weight/1000, 2),
             'demanded_weight': round(item['s'], 2),
             'available_time': round(total_weight/1000/item['s'], 1),
             'product_no': item['product_no']
             }
        )
    # 按可用天数排序
    ret.sort(key=lambda x: x['available_time'])
    # print(ret)


def calculate_product_stock(factory_date, product_no, stage):
    """
    计算胶料现有库存量
    @param factory_date: 工厂日期
    @param product_no: 胶料代码
    @param stage: 段次
    @return: 库存总重量
    """
    s = ProductStockDailySummary.objects.filter(
        factory_date=factory_date,
        stage=stage,
        product_no=product_no).first()
    return s.stock_weight + s.area_weight if s else 0


def calculate_equip_recipe_avg_mixin_time(equip_no, recipe_name):
    """
    查找机台配方每车平均密炼时间
    @param equip_no: 机台编号
    @param recipe_name: 配方名称
    """
    capacity = SchedulingEquipCapacity.objects.filter(
        equip_no=equip_no, product_no=recipe_name).first()
    if capacity:
        avg_mixin_time = capacity.avg_mixing_time + capacity.avg_interval_time
    else:
        # TODO 如果该配方没有历史生产数据，密炼一车所消耗的时间默认值为多少？
        avg_mixin_time = 150
    return avg_mixin_time


def calculate_product_plan_trains(factory_date, product_no, need_weight):
    """
    根据需求重量、定机表数据，安排机台生产计划
    @param factory_date: 工厂日期
    @param need_weight: 需求重量(吨)
    @param product_no:胶料代码
    """
    need_weight = need_weight * 1000
    stock_weight = 0
    ret = []
    stages = list(GlobalCode.objects.filter(global_type__type_name='胶料段次').values_list('global_name', flat=True))
    ms = SchedulingRecipeMachineSetting.objects.filter(product_no=product_no).first()
    if not ms:
        raise ValueError('未找到胶料代码{}定机表数据！'.format(product_no))
    product_batching = ProductBatching.objects.using('SFJ').filter(
        stage_product_batch_no__icontains='-FM-{}'.format(product_no),
        equip__equip_no=ms.main_machine_FM,
        used_type=4
    ).values('id', 'batching_weight', 'equip__equip_no', 'stage_product_batch_no', 'equip__category__category_name')

    while product_batching:
        product_batching = product_batching[0]
        batching_weight = float(product_batching['batching_weight'])
        c_pb = ProductBatchingDetail.objects.using('SFJ').filter(
            product_batching=product_batching['id'],
            delete_flag=False,
            material__material_type__global_name__in=stages).first()
        plan_trains = int((need_weight - stock_weight) / batching_weight)
        # i = str(plan_trains).split('.')[-1]
        # if int(i) < 5 and '-FM' not in product_batching['stage_product_batch_no']:
        #     plan_trains = int(plan_trains - 1)
        # else:
        #     plan_trains = int(plan_trains)
        avg_mixin_time = calculate_equip_recipe_avg_mixin_time(product_batching['equip__equip_no'],
                                                               product_batching['stage_product_batch_no'])
        if c_pb:
            devoted_weight = float(c_pb.actual_weight)
            ret.append({'recipe_name': product_batching['stage_product_batch_no'],
                        'equip_no': product_batching['equip__equip_no'],
                        'batching_weight': batching_weight,
                        'devoted_weight': devoted_weight,
                        'plan_trains': plan_trains,
                        'time_consume': round(avg_mixin_time * plan_trains / 3600, 2),
                        'dev_type': product_batching['equip__category__category_name'],
                        'stock_weight': stock_weight
                        })
            try:
                stage = c_pb.material.material_no.split('-')[1]
            except Exception:
                raise ValueError('物料名称错误')
            stock_weight = calculate_product_stock(factory_date, product_no, stage)
            # ms = SchedulingRecipeMachineSetting.objects.filter(product_no=product_no).first()
            if not ms:
                raise ValueError('未找到胶料代码{}定机表数据！'.format(product_no))
            try:
                if stage == 'HMB':
                    mixin_main_equip = ms.main_machine_HMB
                elif stage == 'CMB':
                    mixin_main_equip = ms.main_machine_CMB
                elif stage == '1MB':
                    mixin_main_equip = ms.main_machine_1MB
                elif stage == '2MB':
                    mixin_main_equip = ms.main_machine_2MB
                else:
                    mixin_main_equip = ms.main_machine_3MB
            except Exception as e:
                raise ValueError(e)
            need_weight = float(plan_trains * devoted_weight)
            product_batching = ProductBatching.objects.using('SFJ').filter(
                stage_product_batch_no__icontains='-{}-{}'.format(stage, product_no),
                equip__equip_no=mixin_main_equip,
                used_type=4
            ).values('id', 'batching_weight', 'equip__equip_no', 'stage_product_batch_no', 'equip__category__category_name')
        else:
            ret.append({'recipe_name': product_batching['stage_product_batch_no'],
                        'equip_no': product_batching['equip__equip_no'],
                        'batching_weight': batching_weight,
                        'devoted_weight': 0,
                        'plan_trains': plan_trains,
                        'time_consume': round(avg_mixin_time * plan_trains / 3600, 2),
                        'dev_type': product_batching['equip__category__category_name'],
                        'stock_weight': stock_weight
                        })
            product_batching = None
    # ret = filter(lambda x: x['plan_trains'] >= 0, ret)
    return list(ret)[::-1]


def extend_last_aps_result(factory_date, schedule_no):
    """
    继承前一天未打完的排程计划
    @param factory_date: 日期
    @param schedule_no: 新的排程单号
    @return:
    """
    equip_tree_data = {
        'Z01': [],
        'Z02': [],
        'Z03': [],
        'Z04': [],
        'Z05': [],
        'Z06': [],
        'Z07': [],
        'Z08': [],
        'Z09': [],
        'Z10': [],
        'Z11': [],
        'Z12': [],
        'Z13': [],
        'Z14': [],
        'Z15': [],
    }

    yesterday = factory_date - timedelta(1)
    yesterday_last_res = SchedulingResult.objects.filter(factory_date=yesterday).order_by('id').last()
    if yesterday_last_res:
        for equip_no in Equip.objects.filter(
                category__equip_type__global_name='密炼设备').values_list('equip_no', flat=True).order_by('equip_no'):
            query_set = SchedulingResult.objects.filter(
                schedule_no=yesterday_last_res.schedule_no,
                equip_no=equip_no)
            if not query_set:
                continue
            # 找到昨天夜班最后一条计划，与该机台昨天排程的计划对比。
            yesterday_plan = ProductClassesPlan.objects.using('SFJ').filter(
                equip__equip_no=equip_no,
                work_schedule_plan__plan_schedule__day_time=yesterday,
                status__in=('运行中', '完成', '停止')
            ).order_by('-id').values('product_batching__stage_product_batch_no', 'plan_classes_uid')
            if yesterday_plan:
                recipe_name = yesterday_plan[0]['product_batching__stage_product_batch_no'] # 配方名称
                plan_classes_uid = yesterday_plan[0]['plan_classes_uid']  # 计划编号
                q = query_set.filter(recipe_name=recipe_name).order_by('sn').last()
                if q:
                    # 获取计划完成车次
                    tfb_obj = TrainsFeedbacks.objects.using('SFJ').filter(
                        plan_classes_uid=plan_classes_uid).order_by('-id').values('actual_trains')
                    if tfb_obj:
                        finished_trains = tfb_obj[0]['actual_trains']
                    else:
                        finished_trains = 0

                    if finished_trains < q.plan_trains:
                        unfinished_plan = query_set.filter(id__gte=q.id)
                    else:
                        unfinished_plan = query_set.filter(id__gt=q.id)
                    idx = 1
                    for plan in unfinished_plan:
                        if plan.id == q.id:
                            plan_trains = plan.plan_trains - finished_trains
                            time_consume = round(
                                calculate_equip_recipe_avg_mixin_time(equip_no, plan.recipe_name) * plan_trains / 3600,
                                2)
                        else:
                            plan_trains = plan.plan_trains
                            time_consume = plan.time_consume
                        equip_tree_data[equip_no].append({'recipe_name': plan.recipe_name,
                                                          'equip_no': equip_no,
                                                          'batching_weight': 0,
                                                          'devoted_weight': 0,
                                                          'plan_trains': plan_trains,
                                                          'time_consume': time_consume,
                                                          'stock_weight': 0,
                                                          'extend_flag': True,
                                                          'desc': '继承前一天计划'
                                                          })
                        # SchedulingResult.objects.create(factory_date=factory_date,
                        #                                 schedule_no=schedule_no,
                        #                                 equip_no=equip_no,
                        #                                 sn=idx,
                        #                                 recipe_name=plan.recipe_name,
                        #                                 time_consume=time_consume,
                        #                                 plan_trains=plan_trains,
                        #                                 desc=plan.desc)
                        # idx += 1
    return equip_tree_data


# [{'product_no': 'C-FM-J260-01', 'equip_no': 'Z09', 'batching_weight': 462.45, 'devoted_weight': 450.0, 'plan_trains': 25.9, 'consume_time': 3108},
#  {'product_no': 'C-2MB-J260-01', 'equip_no': 'Z01', 'batching_weight': 666.0, 'devoted_weight': 666.0, 'plan_trains': 16.5, 'consume_time': 1980},
#  {'product_no': 'C-1MB-J260-01', 'equip_no': 'Z03', 'batching_weight': 888.0, 'devoted_weight': 0, 'plan_trains': 11.5, 'consume_time': 1380}]


class Node(object):
    """节点"""

    def __init__(self, value):
        self.value = value
        self.next = None
        self.time_enough = True


class APSLink(object):

    def __init__(self, equip_no, schedule_no, head=None):
        self.head = head
        t = SchedulingResult.objects.filter(
            schedule_no=schedule_no, equip_no=equip_no).aggregate(t=Sum('time_consume'))['t']
        self.total_time = t if t else 0

    def is_full(self):
        return int(self.total_time / 3600) > 24

    def append(self, value: dict):
        if self.is_full():
            return
        node = Node(value)
        if self.head is None:
            self.head = node
        else:
            c_node = self.head
            c_product_no = c_node.value['product_no']
            n_c_product_no = value['product_no']
            while c_node.next:
                if not c_node.time_enough and not c_product_no.split('-')[2] == n_c_product_no.split('-')[2]:
                    n_node = c_node.next
                    node.next = n_node
                    c_node.time_enough = True
                    break
                c_node = c_node.next
            c_node.next = node

            # 同一物料不同段次，判断是否来得及补料
            if c_product_no.split('-')[2] == n_c_product_no.split('-')[2]:
                if c_node.value['consume_time'] / 3600 < 1:  # 补料时间从配置中获取
                    c_node.time_enough = False
        self.total_time += value['consume_time']

    def travel(self):
        c_node = self.head
        ret = []
        while c_node:
            # print(c_node.value, c_node.time_enough)
            ret.append(c_node.value)
            c_node = c_node.next
        return ret


def find_wait_time(equip_no, recipe_name, equip_tree):
    # 获取上段次打完总耗时"
    wt = 0
    for e_item in equip_tree[equip_no]:
        wt += e_item['time_consume']
        if e_item['recipe_name'] == recipe_name and not e_item.get('extend_flag'):
            if e_item['time_consume'] <= 1:  # 从配置中获取供料最少时间
                wt = wt - e_item['time_consume'] + 1
            break
    return wt


def plan_sort(product_demanded_rains, equip_tree_data):
    unsorted_plan = []

    unsorted_final_plan = []

    unsorted_final_plan2 = []

    # 先排混炼，最后排终炼

    for idx in range(6):
        # 排上次剩余的供料不足计划
        # for p in unsorted_plan:
        #     if p.get('sorted_flag'):
        #         continue
        #     stage = p['stage']
        #     equip_no = p['equip_no']
        #     product_no = p['recipe_name'].split('-')[2]
        #     p_stages = [i['stage'] for i in product_demanded_rains[product_no]]
        #     previous_plan = product_demanded_rains[product_no][p_stages.index(stage)-1]
        #     previous_equip = previous_plan['equip_no']
        #     previous_stage_recipe_name = previous_plan['recipe_name']
        #     wait_time = find_wait_time(previous_equip, previous_stage_recipe_name)
        #     t = 0
        #     for i, tree in enumerate(equip_tree[equip_no]):
        #         t += tree['time_consume']
        #         if t > wait_time:
        #             # 找到供料合理时间点进行插入
        #             product_nos = list(product_demanded_rains.keys())
        #             try:
        #                 next_stage_recipe_name = equip_tree[equip_no][i + 1]['recipe_name']
        #             except IndexError:
        #                 next_stage_recipe_name = None
        #             if next_stage_recipe_name:
        #                 if product_nos.index(next_stage_recipe_name.split('-')[2]) < product_nos.index(
        #                         product_no):
        #                     continue
        #             equip_tree[equip_no].insert(i + 1, p)
        #             p['sorted_flag'] = True
        #             break

        for product_no, t_item in product_demanded_rains.items():
            try:
                current_procedure = t_item[idx]
            except IndexError:
                continue
            if current_procedure.get('unsorted_flag') or current_procedure['plan_trains'] == 0:
                continue
            stage = current_procedure['recipe_name'].split('-')[1]
            equip_no = current_procedure['equip_no']
            if idx == 0:
                # 混炼第一段直接按顺序排，不需要考虑物料库存量
                if stage != 'FM':
                    equip_tree_data[equip_no].append(current_procedure)
            else:
                if stage == 'FM':
                    continue
                else:
                    # 混炼非第一段次排程
                    previous_equip = t_item[idx - 1]['equip_no']
                    previous_stage_recipe_name = t_item[idx - 1]['recipe_name']
                    wait_time = find_wait_time(previous_equip, previous_stage_recipe_name, equip_tree_data)
                    t = 0
                    for i, tree in enumerate(equip_tree_data[equip_no]):
                        t += tree['time_consume']
                        if t >= wait_time:
                            # 找到供料合理时间点进行插入
                            product_nos = list(product_demanded_rains.keys())
                            try:
                                next_stage_recipe_name = equip_tree_data[equip_no][i + 1]['recipe_name']
                            except IndexError:
                                next_stage_recipe_name = None
                            if next_stage_recipe_name:
                                if product_nos.index(next_stage_recipe_name.split('-')[2]) < product_nos.index(product_no):
                                    continue
                            equip_tree_data[equip_no].insert(i + 1, current_procedure)
                            break
                        if i+1 == len(equip_tree_data[equip_no]):
                            # 防止供料不足情况发生，暂时不排
                            for n in t_item[idx:-1]:
                                unsorted_plan.append(n)
                                n['unsorted_flag'] = True

    for p in unsorted_plan:
        if p.get('sorted_flag'):
            continue
        p['desc'] = '供料不足，需调整！'
        equip_tree_data[p['equip_no']].append(p)

    # 排终炼计划
    for product_no, t_item in product_demanded_rains.items():
        try:
            current_procedure = t_item[-1]
        except IndexError:
            continue
        try:
            previous_stage_plan = t_item[-2]
        except Exception:
            continue
        previous_stage_stock = previous_stage_plan.get('stock_weight', 0)
        if not previous_stage_stock:
            unsorted_final_plan.append(current_procedure)
        else:
            devoted_weight = current_procedure['devoted_weight']
            trains = int(previous_stage_stock/devoted_weight)
            equip_tree_data[current_procedure['equip_no']].append({'equip_no': current_procedure['equip_no'],
                                                              'recipe_name': current_procedure['recipe_name'],
                                                              'time_consume': round(trains/current_procedure['plan_trains']*current_procedure['time_consume'], 1),
                                                              'plan_trains': trains,
                                                              'stage': current_procedure['recipe_name'].split('-')[2],
                                                              'desc': '消耗库存'})
            current_procedure['plan_trains'] -= trains
            if current_procedure['plan_trains'] > 0:
                unsorted_final_plan.append(current_procedure)

    for final_plan in unsorted_final_plan:
        equip_no = final_plan['equip_no']
        product_no = final_plan['recipe_name'].split('-')[2]
        previous_plan = product_demanded_rains[product_no][-2]
        previous_equip = previous_plan['equip_no']
        previous_stage_recipe_name = previous_plan['recipe_name']
        wait_time = find_wait_time(previous_equip, previous_stage_recipe_name, equip_tree_data)
        t = 0
        for i, tree in enumerate(equip_tree_data[equip_no]):
            t += tree['time_consume']
            if t >= wait_time:
                # 找到供料合理时间点进行插入
                product_nos = list(product_demanded_rains.keys())
                try:
                    next_stage_recipe_name = equip_tree_data[equip_no][i + 1]['recipe_name']
                except IndexError:
                    next_stage_recipe_name = None
                if next_stage_recipe_name:
                    try:
                        if product_nos.index(next_stage_recipe_name.split('-')[2]) < product_nos.index(product_no):
                            continue
                    except Exception:
                        continue
                equip_tree_data[equip_no].insert(i + 1, final_plan)
                break
            if i + 1 == len(equip_tree_data[equip_no]):
                # 防止供料不足情况发生，暂时不排
                unsorted_final_plan2.append(final_plan)

    for final_plan in unsorted_final_plan2:
        final_plan['desc'] = '供料不足，需调整！'
        equip_tree_data[final_plan['equip_no']].append(final_plan)

    # print(sum([len(i) for i in equip_tree_data.values()]))
    # print(len(unsorted_plan))
    # print(equip_tree_data)
    # print(unsorted_plan)
    return equip_tree_data


if __name__ == '__main__':
    # calculate_equip_left_time()
    # calculate_product_available_time()
    # print(calculate_product_plan_trains('2022-01-13', 'K109', 9.9))
    a = APSLink()
    a.append({'product_no': 'C-1MB-J260-01', 'equip_no': 'Z03', 'batching_weight': 888.0, 'devoted_weight': 0, 'plan_trains': 11.5, 'consume_time': 2222})
    a.append({'product_no': 'C-2MB-J260-01', 'equip_no': 'Z09', 'batching_weight': 462.45, 'devoted_weight': 450.0, 'plan_trains': 25.9, 'consume_time': 6666})
    a.append({'product_no': 'C-3MB-J260-01', 'equip_no': 'Z09', 'batching_weight': 462.45, 'devoted_weight': 450.0, 'plan_trains': 25.9, 'consume_time': 6666})
    a.append({'product_no': 'C-1MB-C590-01', 'equip_no': 'Z09', 'batching_weight': 462.45, 'devoted_weight': 450.0, 'plan_trains': 25.9, 'consume_time': 6666})
    a.append({'product_no': 'C-2MB-C590-01', 'equip_no': 'Z09', 'batching_weight': 462.45, 'devoted_weight': 450.0, 'plan_trains': 25.9, 'consume_time': 6666})
    # a.travel()
    b = APSLink()
    b.travel()



# 1、哪些段次的胶料算作现有库存，只是FM的吗？
# 答：FM和RFM段次

# 3、同一段次配方，实际会不会出现不同版本？（例如FM-C590-01和FM-C590-02会不会同时存在）
# 答：如果存在不同版本的配方，计划员需要备注具体版本

# 1、根据定机表，什么场景下会把计划排到辅机台？
# 答：当主机台故障或计划无法满足供应生产时会安排辅机台（解释有点模糊，回头当面详细讨论）

