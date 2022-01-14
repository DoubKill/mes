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
    print(ret)


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
    print(ret)


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
        product_no__icontains='-{}-{}'.format(stage, product_no)).aggregate(s=Sum('stock_weight'))['s']
    return s if s else 0


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
        equip__equip_no=ms.final_main_machine
    ).values('id', 'batching_weight', 'equip__equip_no', 'stage_product_batch_no', 'equip__category__category_name')

    while product_batching:
        product_batching = product_batching[0]
        batching_weight = float(product_batching['batching_weight'])
        c_pb = ProductBatchingDetail.objects.using('SFJ').filter(
            product_batching=product_batching['id'],
            delete_flag=False,
            material__material_type__global_name__in=stages).first()
        plan_trains = round((need_weight - stock_weight) / batching_weight, 1)
        i = str(plan_trains).split('.')[-1]
        if int(i) < 5:
            plan_trains = int(plan_trains - 1)
        else:
            plan_trains = int(plan_trains)
        avg_mixin_time = calculate_equip_recipe_avg_mixin_time(product_batching['equip__equip_no'],
                                                               product_batching['stage_product_batch_no'])
        if c_pb:
            devoted_weight = float(c_pb.actual_weight)
            ret.append({'product_no': product_batching['stage_product_batch_no'],
                        'equip_no': product_batching['equip__equip_no'],
                        'batching_weight': batching_weight,
                        'devoted_weight': devoted_weight,
                        'plan_trains': plan_trains,
                        'consume_time': round(avg_mixin_time * plan_trains / 3600, 2),
                        'dev_type': product_batching['equip__category__category_name']
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
                mixin_main_equip = ms.mixing_main_machine.split('/')[0]
            except Exception as e:
                raise ValueError(e)
            need_weight = float(plan_trains * devoted_weight)
            product_batching = ProductBatching.objects.using('SFJ').filter(
                stage_product_batch_no__icontains='-{}-{}'.format(stage, product_no),
                equip__equip_no=mixin_main_equip
            ).values('id', 'batching_weight', 'equip__equip_no', 'stage_product_batch_no', 'equip__category__category_name')
        else:
            ret.append({'product_no': product_batching['stage_product_batch_no'],
                        'equip_no': product_batching['equip__equip_no'],
                        'batching_weight': batching_weight,
                        'devoted_weight': 0,
                        'plan_trains': plan_trains,
                        'consume_time': round(avg_mixin_time * plan_trains / 3600, 2),
                        'dev_type': product_batching['equip__category__category_name']
                        })
            product_batching = None
    return ret[::-1]


def extend_last_aps_result(factory_date, schedule_no):
    """
    继承前一天未打完的排程计划
    @param factory_date: 日期
    @param schedule_no: 新的排程单号
    @return:
    """
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
                        unfinished_plan = query_set.filter(sn__gte=q.sn)
                    else:
                        unfinished_plan = query_set.filter(sn__gt=q.sn)
                    idx = 1
                    for plan in unfinished_plan:
                        if plan.sn == q.sn:
                            plan_trains = plan.plan_trains - finished_trains
                            time_consume = round(
                                calculate_equip_recipe_avg_mixin_time(equip_no, plan.recipe_name) * plan_trains / 3600,
                                2)
                        else:
                            plan_trains = plan.plan_trains
                            time_consume = plan.time_consume
                        SchedulingResult.objects.create(factory_date=factory_date,
                                                        schedule_no=schedule_no,
                                                        equip_no=equip_no,
                                                        sn=idx,
                                                        recipe_name=plan.recipe_name,
                                                        time_consume=time_consume,
                                                        plan_trains=plan_trains,
                                                        desc=plan.desc)
                        idx += 1


# [{'product_no': 'C-FM-J260-01', 'equip_no': 'Z09', 'batching_weight': 462.45, 'devoted_weight': 450.0, 'plan_trains': 25.9, 'consume_time': 3108},
#  {'product_no': 'C-2MB-J260-01', 'equip_no': 'Z01', 'batching_weight': 666.0, 'devoted_weight': 666.0, 'plan_trains': 16.5, 'consume_time': 1980},
#  {'product_no': 'C-1MB-J260-01', 'equip_no': 'Z03', 'batching_weight': 888.0, 'devoted_weight': 0, 'plan_trains': 11.5, 'consume_time': 1380}]


if __name__ == '__main__':
    # calculate_equip_left_time()
    # calculate_product_available_time()
    print(calculate_product_plan_trains('2022-01-13', 'K109', 9.9))



# 1、哪些段次的胶料算作现有库存，只是FM的吗？
# 答：FM和RFM段次

# 3、同一段次配方，实际会不会出现不同版本？（例如FM-C590-01和FM-C590-02会不会同时存在）
# 答：如果存在不同版本的配方，计划员需要备注具体版本

# 1、根据定机表，什么场景下会把计划排到辅机台？
# 答：当主机台故障或计划无法满足供应生产时会安排辅机台（解释有点模糊，回头当面详细讨论）

