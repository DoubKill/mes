import json

from mes.common_code import order_no, DecimalEncoder
from quality.models import MaterialDealResult, MaterialTestOrder, MaterialTestResult, LevelResult, \
    MaterialDataPointIndicator, MaterialTestMethod
from production.models import PalletFeedbacks
from quality.serializers import MaterialDealResultListSerializer
from django.db.models import Max, Min, Q
import logging

logger = logging.getLogger('send_log')


def synthesize_to_material_deal_result(mdr_lot_no):
    """等级综合判定"""
    # 1、先找到这个胶料所有指标
    logger.error("1、先找到这个胶料所有指标")
    mto_set_all = MaterialTestOrder.objects.filter(lot_no=mdr_lot_no).values_list('product_no', flat=True)
    mto_product_no_list = list(mto_set_all)
    mtm_set = MaterialTestMethod.objects.filter(material__material_name__in=mto_product_no_list).all()
    name_list = []
    for mtm_obj in mtm_set:
        name = mtm_obj.test_method.test_type.test_indicator.name
        name_list.append(name)

    # 2、 判断是否所有车次都有
    logger.error("2、 判断是否所有车次都有")
    actual_trains_list = MaterialTestOrder.objects.filter(lot_no=mdr_lot_no).values_list('actual_trains', flat=True)
    train_liat = list(actual_trains_list)
    pfb_obj = PalletFeedbacks.objects.filter(lot_no=mdr_lot_no).first()
    for i in range(pfb_obj.begin_trains, pfb_obj.end_trains + 1):
        if i not in train_liat:
            return

    # 3、判断快检这边是不是所有的指标都有
    logger.error("3、判断快检这边是不是所有的指标都有")
    mto_set = MaterialTestOrder.objects.filter(lot_no=mdr_lot_no).all()
    for mto_obj in mto_set:
        test_indicator_name_list = []
        mtr_dpn_list = mto_obj.order_results.all().values('test_indicator_name').annotate(
            max_test_time=Max('test_times'))
        for mtr_dpn_dict in mtr_dpn_list:
            test_indicator_name_list.append(mtr_dpn_dict['test_indicator_name'])
        test_indicator_name_list = list(set(test_indicator_name_list))
        for name in name_list:
            if name not in test_indicator_name_list:  # 必须胶料所有的指标快检这边都有 没有就return
                return

    # 4、分析流程
    logger.error("4、分析流程")
    mdr_dict = {}
    mdr_dict['lot_no'] = mdr_lot_no
    level_list = []
    for mto_obj in mto_set:
        mrt_list = mto_obj.order_results.all().values('data_point_name').annotate(max_test_time=Max('test_times'))
        for mrt_dict in mrt_list:
            mrt_dict_obj = MaterialTestResult.objects.filter(material_test_order=mto_obj,
                                                             data_point_name=mrt_dict['data_point_name'],
                                                             test_times=mrt_dict['max_test_time']).last()
            level_list.append(mrt_dict_obj)
    max_mtr = level_list[0]
    # 找到检测次数最多的几条 每一条的等级进行比较选出做大的
    reason = ''
    exist_data_point_indicator = True  # 是否超出区间范围
    quality_sign = True  # 快检判定何三等品
    for mtr_obj in level_list:
        if not mtr_obj.mes_result:  # mes没有数据
            if not mtr_obj.result:  # 快检也没有数据
                reason = reason + f'{mtr_obj.material_test_order.actual_trains}车{mtr_obj.data_point_name}指标{mtr_obj.value}不在一等品判定区间，\n'
                exist_data_point_indicator = False
            elif mtr_obj.result not in ['一等品', '合格', None, '']:
                reason = reason + f'{mtr_obj.material_test_order.actual_trains}车{mtr_obj.data_point_name}指标{mtr_obj.value}在快检判为{mtr_obj.result}，\n'
                quality_sign = False

        elif mtr_obj.mes_result in ['一等品', '合格']:
            if mtr_obj.result not in ['一等品', '合格', None, '']:
                reason = reason + f'{mtr_obj.material_test_order.actual_trains}车{mtr_obj.data_point_name}指标{mtr_obj.value}在快检判为{mtr_obj.result}，\n'
                quality_sign = False

        elif mtr_obj.mes_result not in ['一等品', '合格']:
            if mtr_obj.data_point_indicator:
                reason = reason + f'{mtr_obj.material_test_order.actual_trains}车{mtr_obj.data_point_name}指标{mtr_obj.value}在[{mtr_obj.data_point_indicator.lower_limit}:{mtr_obj.data_point_indicator.upper_limit}]，\n'
            else:
                reason = reason + f'{mtr_obj.material_test_order.actual_trains}车{mtr_obj.data_point_name}指标{mtr_obj.value}不在一等品判断区间内，\n'
                exist_data_point_indicator = False
        if not max_mtr.data_point_indicator:
            max_mtr = mtr_obj
            continue
        if not mtr_obj.data_point_indicator:
            continue
        if mtr_obj.level > max_mtr.level:
            max_mtr = mtr_obj

    mdr_dict['reason'] = reason
    mdr_dict['status'] = '待处理'

    if exist_data_point_indicator:
        if quality_sign:
            mdr_dict['level'] = max_mtr.level
            if max_mtr.mes_result in ['合格', '一等品']:
                mdr_dict['deal_result'] = '一等品'
            else:
                mdr_dict['deal_result'] = '三等品'
        else:
            mdr_dict['level'] = 3
            mdr_dict['deal_result'] = '三等品'
    else:
        mdr_dict['level'] = 3
        mdr_dict['deal_result'] = '三等品'

    pfb_obj = PalletFeedbacks.objects.filter(lot_no=mdr_lot_no).last()
    mdr_dict['production_factory_date'] = pfb_obj.begin_time

    iir_mdr_obj = MaterialDealResult.objects.filter(lot_no=mdr_lot_no).order_by('test_time').last()
    if iir_mdr_obj:
        mdr_dict['test_time'] = iir_mdr_obj.test_time + 1
        MaterialDealResult.objects.filter(lot_no=mdr_lot_no).update(status='复测')
        mdr_obj = MaterialDealResult.objects.create(**mdr_dict)
    else:
        mdr_dict['test_time'] = 1
        mdr_obj = MaterialDealResult.objects.create(**mdr_dict)


# 不在调用序列化的方法了 序列化里的方法是给web端用的 直接改的话会影响到web前端的展示 这里复制一下 修改一点直接给打印机用
def get_mtr_list(obj):
    mtr_list_return = {}
    # 找到每个车次检测次数最多的那一条
    table_head_count = {}
    mto_set = MaterialTestOrder.objects.filter(lot_no=obj.lot_no).all()
    for mto_obj in mto_set:
        if not mto_obj:
            continue
        mtr_list_return[mto_obj.actual_trains] = []
        # 先弄出表头
        table_head = mto_obj.order_results.all().values('test_indicator_name',
                                                        'data_point_name').annotate().distinct()
        for table_head_dict in table_head:
            if table_head_dict['test_indicator_name'] not in table_head_count.keys():
                table_head_count[table_head_dict['test_indicator_name']] = []
            table_head_count[table_head_dict['test_indicator_name']].append(table_head_dict['data_point_name'])
            table_head_count[table_head_dict['test_indicator_name']] = list(
                set(table_head_count[table_head_dict['test_indicator_name']]))
        # 根据test_indicator_name分组找到啊test_times最大的
        mtr_list = mto_obj.order_results.all().values('test_indicator_name', 'data_point_name').annotate(
            max_test_times=Max('test_times')).values('test_indicator_name', 'data_point_name',
                                                     'max_test_times',
                                                     )
        mtr_max_list = []
        for mtr_max_obj in mtr_list:
            # 根据分组找到数据
            mtr_obj = MaterialTestResult.objects.filter(material_test_order=mto_obj,
                                                        test_indicator_name=mtr_max_obj['test_indicator_name'],
                                                        data_point_name=mtr_max_obj['data_point_name'],
                                                        test_times=mtr_max_obj['max_test_times']).last()
            if mtr_obj.level == 1:
                result = '一等品'
            else:
                result = '三等品'
            # 判断加减
            data_point_name = mtr_obj.data_point_name  # 数据点名称
            test_method_name = mtr_obj.test_method_name  # 试验方法名称
            test_indicator_name = mtr_obj.test_indicator_name  # 检测指标名称
            product_no = mtr_obj.material_test_order.product_no  # 胶料编码

            # 根据material-test-orders接口逻辑找到data_point_indicator
            material_test_method = MaterialTestMethod.objects.filter(
                material__material_no=product_no,
                test_method__name=test_method_name,
                test_method__test_type__test_indicator__name=test_indicator_name,
                data_point__name=data_point_name,
                data_point__test_type__test_indicator__name=test_indicator_name).first()
            add_subtract = None  # 页面的加减
            limit = None
            if material_test_method:
                indicator = MaterialDataPointIndicator.objects.filter(
                    material_test_method=material_test_method,
                    data_point__name=data_point_name,
                    data_point__test_type__test_indicator__name=test_indicator_name, level=1).first()
                if indicator:  # 判断value与上下限的比较
                    limit = f"{indicator.lower_limit}-{indicator.upper_limit}"
                    table_head_count[test_indicator_name].remove(data_point_name)
                    table_head_count[test_indicator_name].append(f'{data_point_name}({limit})')
                    table_head_count[test_indicator_name] = list(set(table_head_count[test_indicator_name]))
                    if mtr_obj.value > indicator.upper_limit:
                        add_subtract = '+'
                    elif mtr_obj.value < indicator.lower_limit:
                        add_subtract = '-'

            mtr_max_list.append(
                {'test_indicator_name': mtr_obj.test_indicator_name,
                 'data_point_name': f'{mtr_obj.data_point_name}({limit})' if limit else mtr_obj.data_point_name,
                 # 'data_point_name': mtr_obj.data_point_name,
                 'value': mtr_obj.value,
                 'result': result,
                 'max_test_times': mtr_obj.level,
                 'add_subtract': add_subtract})

        for mtr_dict in mtr_max_list:
            mtr_dict['status'] = f"{mtr_dict['max_test_times']}:{mtr_dict['result']}"
            mtr_list_return[mto_obj.actual_trains].append(mtr_dict)

    table_head_top = {}
    for i in sorted(table_head_count.items(), key=lambda x: len(x[1]), reverse=False):
        table_head_top[i[0]] = i[-1]
    mtr_list_return['table_head'] = table_head_top
    for value in mtr_list_return.values():  # 将每个数据点排序
        if isinstance(value, list):
            value.sort(key=lambda x: x['data_point_name'], reverse=False)
        else:
            for i in value.values():
                i.sort(reverse=False)
    return mtr_list_return


def receive_deal_result(lot_no):
    """将快检信息综合管理接口(就是打印的卡片信息)封装成一个类，需要的时候就调用一下"""
    mdr_obj = MaterialDealResult.objects.filter(lot_no=lot_no).exclude(status='复测').last()
    if mdr_obj:
        mdrls = MaterialDealResultListSerializer()
        results = {}
        # id
        results['id'] = mdr_obj.id
        # day_time
        results['day_time'] = str(mdrls.get_day_time(mdr_obj))
        # lot_no
        results['lot_no'] = mdr_obj.lot_no
        # classes_group
        results['classes_group'] = mdrls.get_classes_group(mdr_obj)
        # equip_no
        results['equip_no'] = mdrls.get_equip_no(mdr_obj)
        # product_no
        results['product_no'] = mdrls.get_product_no(mdr_obj)
        # actual_weight
        results['actual_weight'] = mdrls.get_actual_weight(mdr_obj)
        # residual_weight
        results['residual_weight'] = mdrls.get_residual_weight(mdr_obj)
        # production_factory_date
        results['production_factory_date'] = str(mdr_obj.production_factory_date)
        # valid_time
        results['valid_time'] = mdrls.get_valid_time(mdr_obj)
        # test
        results['test'] = mdrls.get_test(mdr_obj)
        # print_time
        results['print_time'] = mdr_obj.print_time.strftime("%Y-%m-%d %H:%M:%S") if mdr_obj.print_time else None
        # deal_user
        results['deal_user'] = mdrls.get_deal_user(mdr_obj)
        # deal_time
        results['deal_time'] = mdrls.get_deal_time(mdr_obj)
        # mtr_list
        m_list = get_mtr_list(mdr_obj)  # 这里不用序列化的方法了 因为要加合格区间 在原本的序列化里加了 会影响web页面的 所以重写一个
        # m_list = mdrls.get_mtr_list(mdr_obj)
        trains = []
        for i in m_list:
            if i != 'table_head':
                trains.append({'train': i, 'content': m_list[i]})
        indicator = []
        for j in m_list['table_head']:
            indicator.append({'point': j, 'point_head': m_list['table_head'][j]})
        mtr_list = {'trains': trains, 'table_head': indicator}
        results['mtr_list'] = mtr_list

        # actual_trains
        results['actual_trains'] = mdrls.get_actual_trains(mdr_obj)
        # operation_user
        results['operation_user'] = mdrls.get_operation_user(mdr_obj)
        # deal_result
        results['deal_result'] = mdr_obj.deal_result
        # deal_suggestion
        results['deal_suggestion'] = mdrls.get_deal_suggestion(mdr_obj)
        results = json.dumps(results, cls=DecimalEncoder)
        return results
    else:
        # results = {"id": None, "day_time": "", "lot_no": "", "classes_group": "", "equip_no": "", "product_no": "",
        #  "actual_weight": None, "residual_weight": None, "production_factory_date": "", "valid_time": None,
        #  "test": {"test_status": "", "test_factory_date": "", "test_class": "", "test_user": "", "test_note": None,
        #           "result": None, "pallet_no": ""}, "print_time": None, "deal_user": None, "deal_time": None,
        #  "mtr_list": {"": [
        #      {"test_indicator_name": "", "data_point_name": "", "value": None, "result": "", "max_test_times": None,
        #       "add_subtract": None, "status": ""},
        #      {"test_indicator_name": "", "data_point_name": "", "value": None, "result": "", "max_test_times": None,
        #       "add_subtract": None, "status": ""},
        #      {"test_indicator_name": "", "data_point_name": "", "value": None, "result": "", "max_test_times": None,
        #       "add_subtract": None, "status": ""},
        #      {"test_indicator_name": "", "data_point_name": "", "value": None, "result": "", "max_test_times": None,
        #       "add_subtract": None, "status": ""},
        #      {"test_indicator_name": "", "data_point_name": "", "value": None, "result": "", "max_test_times": None,
        #       "add_subtract": None, "status": ""},
        #      {"test_indicator_name": "", "data_point_name": "", "value": None, "result": "", "max_test_times": None,
        #       "add_subtract": None, "status": ""},
        #      {"test_indicator_name": "", "data_point_name": "", "value": None, "result": "", "max_test_times": None,
        #       "add_subtract": None, "status": ""}], "": [
        #      {"test_indicator_name": "", "data_point_name": "", "value": None, "result": "", "max_test_times": None,
        #       "add_subtract": None, "status": ""},
        #      {"test_indicator_name": "", "data_point_name": "", "value": None, "result": "", "max_test_times": None,
        #       "add_subtract": None, "status": ""},
        #      {"test_indicator_name": "", "data_point_name": "", "value": None, "result": "", "max_test_times": None,
        #       "add_subtract": None, "status": ""},
        #      {"test_indicator_name": "", "data_point_name": "", "value": None, "result": "", "max_test_times": None,
        #       "add_subtract": None, "status": ""},
        #      {"test_indicator_name": "", "data_point_name": "", "value": None, "result": "", "max_test_times": None,
        #       "add_subtract": None, "status": ""},
        #      {"test_indicator_name": "", "data_point_name": "", "value": None, "result": "", "max_test_times": None,
        #       "add_subtract": None, "status": ""},
        #      {"test_indicator_name": "", "data_point_name": "", "value": None, "result": "", "max_test_times": None,
        #       "add_subtract": None, "status": ""}],
        #               "table_head": {"\u95e8\u5c3c": ["ML1+4"], "\u6bd4\u91cd": ["\u6bd4\u91cd\u503c"],
        #                              "\u786c\u5ea6": ["\u786c\u5ea6\u503c"],
        #                              "\u6d41\u53d8": ["MH", "TC10", "TC50", "TC90"]}}, "actual_trains": "",
        #  "operation_user": "", "deal_result": "", "deal_suggestion": None}
        pass
