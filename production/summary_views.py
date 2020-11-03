import copy

from django.db.models import Sum, F, Min, Max, Avg
from django.db.models.functions import TruncMonth
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.views import APIView

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


class ClassesBanBurySummaryView(ListAPIView):
    """班次密炼统计"""
    queryset = TrainsFeedbacks.objects.all()

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
            kwargs['begin_time__date__gte'] = st
        if et:
            kwargs['end_time__date__lte'] = et
        if equip_no:
            kwargs['equip_no__icontains'] = equip_no
        if product_no:
            kwargs['product_no__icontains'] = product_no

        # 默认需要分组的字段
        group_by_fields = ['plan_classes_uid', 'equip_no', 'product_no']
        if day_type == '2':  # 按照工厂日期
            dimension_type['2'] = ['factory_data']
            dimension_type['1'][-1] = 'factory_data'
            kwargs.pop('begin_time__date__gte', None)
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
            data = TrainsFeedbacks.objects.annotate(
                month=TruncMonth('end_time')).filter(**kwargs).values(*group_by_fields).annotate(
                total_trains=Max('actual_trains'),
                total_time=Sum(F('end_time') - F('begin_time')) / 1000000,
                min_train_time=Min(F('end_time') - F('begin_time')) / 1000000,
                max_train_time=Max(F('end_time') - F('begin_time')) / 1000000,
                avg_train_time=Avg(F('end_time') - F('begin_time')) / 1000000
            )
        else:
            data = TrainsFeedbacks.objects.filter(**kwargs).values(*group_by_fields).annotate(
                total_trains=Max('actual_trains'),
                total_time=Sum(F('end_time') - F('begin_time')) / 1000000,
                min_train_time=Min(F('end_time') - F('begin_time')) / 1000000,
                max_train_time=Max(F('end_time') - F('begin_time')) / 1000000,
                avg_train_time=Avg(F('end_time') - F('begin_time')) / 1000000
            )
        ret = {}
        for item in data:
            item_key = ''.join([str(item[i]) for i in query_group_by_field]) + item['equip_no'] + item['product_no']
            if item_key not in ret:
                ret[item_key] = item
            else:
                ret[item_key]['total_trains'] += item['total_trains']
                ret[item_key]['total_time'] += item['total_time']

        page = self.paginate_queryset(list(ret.values()))
        return self.get_paginated_response(page)


class EquipBanBurySummaryView(ListAPIView):
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
            kwargs['begin_time__date__gte'] = st
        if et:
            kwargs['end_time__date__lte'] = et
        if equip_no:
            kwargs['equip_no__icontains'] = equip_no

        # 默认需要分组的字段
        group_by_fields = ['plan_classes_uid', 'equip_no']
        if day_type == '2':  # 按照工厂日期
            dimension_type['2'] = ['factory_data']
            dimension_type['1'][-1] = 'factory_data'
            kwargs.pop('begin_time__date__gte', None)
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
            data = TrainsFeedbacks.objects.annotate(
                month=TruncMonth('end_time')).filter(**kwargs).values(*group_by_fields).annotate(
                total_trains=Max('actual_trains'),
                total_time=Sum(F('end_time') - F('begin_time')) / 1000000,
            )
        else:
            data = TrainsFeedbacks.objects.filter(**kwargs).values(*group_by_fields).annotate(
                total_trains=Max('actual_trains'),
                total_time=Sum(F('end_time') - F('begin_time')) / 1000000,
            )
        ret = {}
        for item in data:
            item_key = ''.join([str(item[i]) for i in query_group_by_field]) + item['equip_no']
            if item_key not in ret:
                ret[item_key] = item
            else:
                ret[item_key]['total_trains'] += item['total_trains']
                ret[item_key]['total_time'] += item['total_time']

        page = self.paginate_queryset(list(ret.values()))
        return self.get_paginated_response(page)


class CollectTrainsFeedbacksList(ListAPIView):
    """胶料单车次时间汇总"""
    queryset = TrainsFeedbacks.objects.filter(delete_flag=False)
    serializer_class = CollectTrainsFeedbacksSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = CollectTrainsFeedbacksFilter
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            if serializer.data:
                sum_time = datetime.timedelta(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0,
                                              weeks=0)
                max_time = serializer.data[0]['time_consuming']
                min_time = serializer.data[0]['time_consuming']
                for train_dict in serializer.data:
                    if train_dict['time_consuming'] > max_time:
                        max_time = train_dict['time_consuming']
                    if train_dict['time_consuming'] < min_time:
                        min_time = train_dict['time_consuming']
                    sum_time += train_dict['time_consuming']
                avg_time = sum_time / len(serializer.data)
                train_list = serializer.data
                train_list.append(
                    {'sum_time': sum_time, 'max_time': max_time, 'min_time': min_time, 'avg_time': avg_time})
            else:
                train_list = serializer.data
                train_list.append(
                    {'sum_time': None, 'max_time': None, 'min_time': None, 'avg_time': None})
            return self.get_paginated_response(train_list)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CutTimeCollect(APIView):
    """规格切换时间汇总"""

    def get(self, request, *args, **kwargs):
        # 筛选工厂
        params = request.query_params
        st = params.get("st", None)  # 开始时间
        et = params.get("et", None)  # 结束时间
        # dimension = params.get("dimension", None)  # 时间跨度 1：班次  2：日 3：月
        # day_type = params.get("day_type", None)  # 日期类型 1：自然日  2：工厂日
        equip_no = params.get("equip_no", None)  # 设备编号
        # product_no = params.get("product_no", None)  # 胶料编码
        try:
            page = int(params.get("page", 1))
            page_size = int(params.get("page_size", 10))
        except Exception as e:
            return Response("page和page_size必须是int", status=400)
        dict_filter = {}
        if equip_no:  # 设备
            dict_filter['equip_no'] = equip_no
        if st:
            dict_filter['end_time__date__gte'] = st
        if et:
            dict_filter['end_time__date__lte'] = et
        # 统计过程
        return_list = []
        tfb_equip_uid_list = TrainsFeedbacks.objects.filter(delete_flag=False, **dict_filter).values('equip_no',
                                                                                                     'plan_classes_uid').annotate().distinct()
        if not tfb_equip_uid_list:
            return_list.append(
                {'sum_time': None, 'max_time': None, 'min_time': None, 'avg_time': None})
            return Response({'results': return_list})
        for tfb_equip_uid_dict in tfb_equip_uid_list:
            # 这里也要加筛选
            if st:
                tfb_equip_uid_dict['end_time__date__gte'] = st
            if et:
                tfb_equip_uid_dict['end_time__date__lte'] = et

            tfb_pn = TrainsFeedbacks.objects.filter(delete_flag=False, **tfb_equip_uid_dict).values()
            for i in range(len(tfb_pn) - 1):
                if tfb_pn[i]['product_no'] != tfb_pn[i + 1]['product_no']:
                    time_consuming = tfb_pn[i + 1]['begin_time'] - tfb_pn[i]['end_time']
                    return_dict = {
                        'time': tfb_pn[i]['end_time'].strftime("%Y-%m-%d %H:%M:%S"),
                        'plan_classes_uid': tfb_equip_uid_dict['plan_classes_uid'],
                        'equip_no': tfb_equip_uid_dict['equip_no'],
                        'cut_ago_product_no': tfb_pn[i]['product_no'],
                        'cut_later_product_no': tfb_pn[i + 1]['product_no'],
                        'time_consuming': time_consuming}
                    return_list.append(return_dict)

        # 分页
        counts = len(return_list)
        return_list = return_list[(page - 1) * page_size:page_size * page]

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
        return Response({'count': counts, 'results': return_list})
