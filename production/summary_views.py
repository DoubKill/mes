import copy

from django.db.models import Sum, F, Min, Max, Avg, Q
from django.db.models.functions import TruncMonth
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.views import APIView

from basics.models import WorkSchedulePlan
from mes.derorators import api_recorder
from production.filters import CollectTrainsFeedbacksFilter
from production.models import TrainsFeedbacks
from production.serializers import CollectTrainsFeedbacksSerializer
import datetime
from rest_framework.response import Response

DIMENSION_TYPE = {
    '1': ['classes', 'end_time__date'],
    '2': ['end_time__date'],
    '3': ['month']
}


@method_decorator([api_recorder], name="dispatch")
class ClassesBanBurySummaryView(ListAPIView):
    """班次密炼统计"""
    queryset = TrainsFeedbacks.objects.all()

    @staticmethod
    def get_class_dimension_page_data(page):
        factory_dates = set([str(item['factory_date']) for item in page])
        classes = set([item['classes'] for item in page])
        schedule_plans = WorkSchedulePlan.objects.filter(
            plan_schedule__work_schedule__schedule_name='三班两运转').filter(
            Q(plan_schedule__day_time__in=factory_dates) | Q(classes__global_name__in=classes)).values(
            'plan_schedule__day_time', 'classes__global_name', 'start_time', 'end_time'
        )
        schedule_plans_dict = {
            str(schedule_plan['plan_schedule__day_time']) + schedule_plan['classes__global_name']:
                schedule_plan for schedule_plan in schedule_plans}
        """如果是按照工厂时间并且是按照班次分组则需要找出该班次的总时间"""
        for value in page:
            key = str(value['factory_date']) + value['classes']
            if key in schedule_plans_dict:
                value['classes_time'] = (schedule_plans_dict[key]['end_time']
                                         - schedule_plans_dict[key]['start_time']).seconds
        return page

    def list(self, request, *args, **kwargs):
        dimension_type = copy.deepcopy(DIMENSION_TYPE)
        st = self.request.query_params.get('st')  # 开始时间
        et = self.request.query_params.get('et')  # 结束时间
        dimension = self.request.query_params.get('dimension', '2')  # 维度 1：班次  2：日 3：月
        day_type = self.request.query_params.get('day_type', '2')  # 日期类型 1：自然日  2：工厂日
        equip_no = self.request.query_params.get('equip_no')  # 设备编号
        product_no = self.request.query_params.get('product_no')  # 胶料编码

        kwargs = {}
        if st:
            kwargs['end_time__date__gte'] = st
        if et:
            kwargs['end_time__date__lte'] = et
        if equip_no:
            kwargs['equip_no__icontains'] = equip_no
        if product_no:
            kwargs['product_no__icontains'] = product_no

        # 默认需要分组的字段
        group_by_fields = ['plan_classes_uid', 'equip_no', 'product_no']
        if day_type == '2':  # 按照工厂日期
            dimension_type['2'] = ['factory_date']
            dimension_type['1'][-1] = 'factory_date'
            kwargs.pop('end_time__date__gte', None)
            kwargs.pop('end_time__date__lte', None)
            if st:
                kwargs['factory_date__gte'] = st
            if et:
                kwargs['factory_date__lte'] = et

        try:
            query_group_by_field = dimension_type[dimension]  # 从前端获取的分组字段
        except Exception:
            raise ValidationError('参数错误')
        group_by_fields.extend(query_group_by_field)

        if dimension == '3':
            # 按月的维度分组，查询写法不一样
            data = TrainsFeedbacks.objects.exclude(classes='').annotate(
                month=TruncMonth('end_time')).filter(**kwargs).values(*group_by_fields).annotate(
                max_trains=Max('actual_trains'),
                min_trains=Min('actual_trains'),
                total_time=Sum(F('end_time') - F('begin_time')) / 1000000,
                min_train_time=Min(F('end_time') - F('begin_time')) / 1000000,
                max_train_time=Max(F('end_time') - F('begin_time')) / 1000000,
                avg_train_time=Avg(F('end_time') - F('begin_time')) / 1000000
            )
        else:
            data = TrainsFeedbacks.objects.exclude(classes='').filter(**kwargs).values(*group_by_fields).annotate(
                max_trains=Max('actual_trains'),
                min_trains=Min('actual_trains'),
                total_time=Sum(F('end_time') - F('begin_time')) / 1000000,
                min_train_time=Min(F('end_time') - F('begin_time')) / 1000000,
                max_train_time=Max(F('end_time') - F('begin_time')) / 1000000,
                avg_train_time=Avg(F('end_time') - F('begin_time')) / 1000000
            )
        ret = {}
        for item in data:
            diff_trains = item['max_trains'] - item['min_trains'] + 1
            item_key = ''.join([str(item[i]) for i in query_group_by_field]) + item['equip_no'] + item['product_no']
            if item_key not in ret:
                item['total_trains'] = diff_trains
                ret[item_key] = item
            else:
                ret[item_key]['total_trains'] += diff_trains
                ret[item_key]['total_time'] += item['total_time']

        page = self.paginate_queryset(list(ret.values()))
        if day_type == '2' and dimension == '1':
            page = self.get_class_dimension_page_data(page)

        return self.get_paginated_response(page)


@method_decorator([api_recorder], name="dispatch")
class EquipBanBurySummaryView(ClassesBanBurySummaryView):
    """机台密炼统计"""
    queryset = TrainsFeedbacks.objects.all()

    def list(self, request, *args, **kwargs):
        dimension_type = copy.deepcopy(DIMENSION_TYPE)
        st = self.request.query_params.get('st')  # 开始时间
        et = self.request.query_params.get('et')  # 结束时间
        dimension = self.request.query_params.get('dimension', '2')  # 维度 1：班次  2：日 3：月
        day_type = self.request.query_params.get('day_type', '2')  # 日期类型 1：自然日  2：工厂日
        equip_no = self.request.query_params.get('equip_no')  # 设备编号

        kwargs = {}
        if st:
            kwargs['end_time__date__gte'] = st
        if et:
            kwargs['end_time__date__lte'] = et
        if equip_no:
            kwargs['equip_no__icontains'] = equip_no

        # 默认需要分组的字段
        group_by_fields = ['plan_classes_uid', 'equip_no']
        if day_type == '2':  # 按照工厂日期
            dimension_type['2'] = ['factory_date']
            dimension_type['1'][-1] = 'factory_date'
            kwargs.pop('end_time__date__gte', None)
            kwargs.pop('end_time__date__lte', None)
            if st:
                kwargs['factory_date__gte'] = st
            if et:
                kwargs['factory_date__lte'] = et

        try:
            query_group_by_field = dimension_type[dimension]  # 从前端获取的分组字段
        except Exception:
            raise ValidationError('参数错误')
        group_by_fields.extend(query_group_by_field)

        if dimension == '3':
            # 按月的维度分组，查询写法不一样
            data = TrainsFeedbacks.objects.exclude(classes='').annotate(
                month=TruncMonth('end_time')).filter(**kwargs).values(*group_by_fields).annotate(
                max_trains=Max('actual_trains'),
                min_trains=Min('actual_trains'),
                total_time=Sum(F('end_time') - F('begin_time')) / 1000000,
            )
        else:
            data = TrainsFeedbacks.objects.exclude(classes='').filter(**kwargs).values(*group_by_fields).annotate(
                max_trains=Max('actual_trains'),
                min_trains=Min('actual_trains'),
                total_time=Sum(F('end_time') - F('begin_time')) / 1000000,
            )
        ret = {}
        for item in data:
            diff_trains = item['max_trains'] - item['min_trains'] + 1
            item_key = ''.join([str(item[i]) for i in query_group_by_field]) + item['equip_no']
            if item_key not in ret:
                item['total_trains'] = diff_trains
                ret[item_key] = item
            else:
                ret[item_key]['total_trains'] += diff_trains
                ret[item_key]['total_time'] += item['total_time']

        page = self.paginate_queryset(list(ret.values()))
        if day_type == '2' and dimension == '1':
            page = self.get_class_dimension_page_data(page)

        return self.get_paginated_response(page)


@method_decorator([api_recorder], name="dispatch")
class CollectTrainsFeedbacksList(ListAPIView):
    """胶料单车次时间汇总"""
    queryset = TrainsFeedbacks.objects.filter(delete_flag=False)
    serializer_class = CollectTrainsFeedbacksSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = CollectTrainsFeedbacksFilter
    permission_classes = (IsAuthenticatedOrReadOnly,)


class SumCollectTrains(APIView):
    """胶料单车次时间汇总最大最小平均时间"""

    def get(self, request, *args, **kwargs):
        params = request.query_params
        st = params.get("st", None)  # 开始时间
        classes = params.get("classes", None)  # 班次
        equip_no = params.get("equip_no", None)  # 设备编号
        product_no = params.get("product_no", None)  # 胶料编码
        dict_filter = {'delete_flag': False}
        if st:
            dict_filter['begin_time__date'] = st
        if classes:
            dict_filter['classes'] = classes
        if equip_no:
            dict_filter['equip_no'] = equip_no
        if product_no:
            dict_filter['product_no__icontains'] = product_no
        tfb_set = TrainsFeedbacks.objects.filter(**dict_filter).values()
        for tfb_obj in tfb_set:
            if not tfb_obj['end_time'] or not tfb_obj['begin_time']:
                tfb_obj['time_consuming'] = None
            else:
                tfb_obj['time_consuming'] = tfb_obj['end_time'] - tfb_obj['begin_time']
        if tfb_set:
            sum_time = datetime.timedelta(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0,
                                          weeks=0)
            max_time = tfb_set[0]['time_consuming']
            min_time = tfb_set[0]['time_consuming']
            for tfb_obj in tfb_set:
                if tfb_obj['time_consuming'] > max_time:
                    max_time = tfb_obj['time_consuming']
                if tfb_obj['time_consuming'] < min_time:
                    min_time = tfb_obj['time_consuming']
                sum_time += tfb_obj['time_consuming']
            avg_time = sum_time / len(tfb_obj)
            return Response(
                {'results': {'sum_time': sum_time, 'max_time': max_time, 'min_time': min_time, 'avg_time': avg_time}})
        else:
            return Response({'results': {'sum_time': None, 'max_time': None, 'min_time': None, 'avg_time': None}})


@method_decorator([api_recorder], name="dispatch")
class CutTimeCollect(APIView):
    """规格切换时间汇总"""

    def get(self, request, *args, **kwargs):
        # 筛选工厂
        params = request.query_params
        st = params.get("st", None)  # 一天的
        # et = params.get("et", None)  # 结束时间
        equip_no = params.get("equip_no", None)  # 设备编号
        try:
            page = int(params.get("page", 1))
            page_size = int(params.get("page_size", 10))
        except Exception as e:
            return Response("page和page_size必须是int", status=400)
        dict_filter = {}
        if equip_no:  # 设备
            dict_filter['equip_no'] = equip_no
        if st:
            dict_filter['end_time__date'] = st
        # 统计过程
        return_list = []
        tfb_equip_uid_list = TrainsFeedbacks.objects.filter(delete_flag=False, **dict_filter).values('equip_no',
                                                                                                     'plan_classes_uid').annotate().distinct()
        if not tfb_equip_uid_list:
            return_list.append(
                {'sum_time': None, 'max_time': None, 'min_time': None, 'avg_time': None})
            return Response({'results': return_list})
        for j in range(len(tfb_equip_uid_list) - 1):
            tfb_equip_uid_dict_ago = tfb_equip_uid_list[j]
            tfb_equip_uid_dict_later = tfb_equip_uid_list[j + 1]
            # 这里也要加筛选
            if st:
                tfb_equip_uid_dict_ago['end_time__date'] = st
                tfb_equip_uid_dict_later['end_time__date'] = st

            tfb_pn_age = TrainsFeedbacks.objects.filter(delete_flag=False, **tfb_equip_uid_dict_ago).last()
            tfb_pn_later = TrainsFeedbacks.objects.filter(delete_flag=False, **tfb_equip_uid_dict_later).first()
            return_dict = {
                'time': tfb_pn_age.end_time.strftime("%Y-%m-%d"),
                'plan_classes_uid_age': tfb_pn_age.plan_classes_uid,
                'plan_classes_uid_later': tfb_pn_later.plan_classes_uid,
                'equip_no': tfb_pn_age.equip_no,
                'cut_ago_product_no': tfb_pn_age.product_no,
                'cut_later_product_no': tfb_pn_later.product_no,
                'time_consuming': tfb_pn_later.begin_time - tfb_pn_age.end_time}
            return_list.append(return_dict)

        if not return_list:
            return_list.append(
                {'sum_time': None, 'max_time': None, 'min_time': None, 'avg_time': None})
            return Response({'results': return_list})
            # 统计最大、最小、综合、平均时间
        sum_time = datetime.timedelta(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0,
                                      weeks=0)
        max_time = return_list[0]['time_consuming']
        min_time = return_list[0]['time_consuming']
        for train_dict in return_list:
            if train_dict['time_consuming'] > max_time:
                max_time = train_dict['time_consuming']
            if train_dict['time_consuming'] < min_time:
                min_time = train_dict['time_consuming']
            sum_time += train_dict['time_consuming']
        avg_time = sum_time / len(return_list)
        return_list.append(
            {'sum_time': sum_time, 'max_time': max_time, 'min_time': min_time, 'avg_time': avg_time})
        # 分页
        counts = len(return_list)
        return_list = return_list[(page - 1) * page_size:page_size * page]

        return Response({'count': counts, 'results': return_list})
