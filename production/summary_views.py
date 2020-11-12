from django.db import connection
from django.db.models import Q, Max
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


@method_decorator([api_recorder], name="dispatch")
class ClassesBanBurySummaryView(ListAPIView):
    """班次密炼统计"""
    queryset = TrainsFeedbacks.objects.all()

    @staticmethod
    def get_class_dimension_page_data(page):
        factory_dates = set([str(item['date']) for item in page])
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
            key = str(value['date']) + value['classes']
            if key in schedule_plans_dict:
                value['classes_time'] = (schedule_plans_dict[key]['end_time']
                                         - schedule_plans_dict[key]['start_time']).seconds
        return page

    def list(self, request, *args, **kwargs):
        st = self.request.query_params.get('st')  # 开始时间
        et = self.request.query_params.get('et')  # 结束时间
        dimension = self.request.query_params.get('dimension', '2')  # 维度 1：班次  2：日 3：月
        day_type = self.request.query_params.get('day_type', '2')  # 日期类型 1：自然日  2：工厂日
        equip_no = self.request.query_params.get('equip_no')  # 设备编号
        product_no = self.request.query_params.get('product_no')  # 胶料编码

        where_str = """not(CLASSES=' ') """

        if day_type == '1':  # 按照自然日
            group_date_field = 'end_time'
        else:  # 按照工厂日期
            group_date_field = 'factory_date'
            where_str += 'and factory_date is not null '

        if dimension == '3':  # 按照月份分组
            date_format = 'yyyy-mm'
        else:
            date_format = 'yyyy-mm-dd'

        select_str = """plan_classes_uid,
                    equip_no,
                    product_no,
                   to_char({}, '{}'),
                   MAX(actual_trains) AS max_trains,
                   MIN(actual_trains) AS min_trains,
                   max(ceil(
                    (To_date(to_char(END_TIME,'yyyy-mm-dd hh24:mi:ss') , 'yyyy-mm-dd hh24-mi-ss')
                     - To_date(to_char(BEGIN_TIME,'yyyy-mm-dd hh24:mi:ss'), 'yyyy-mm-dd hh24-mi-ss')
                    ) * 24 * 60 * 60 )) as max_train_time,
                    min(ceil(
                    (To_date(to_char(END_TIME,'yyyy-mm-dd hh24:mi:ss') , 'yyyy-mm-dd hh24-mi-ss')
                     - To_date(to_char(BEGIN_TIME,'yyyy-mm-dd hh24:mi:ss'), 'yyyy-mm-dd hh24-mi-ss')
                    ) * 24 * 60 * 60 )) as min_train_time,
                   sum(ceil(
                    (To_date(to_char(END_TIME,'yyyy-mm-dd hh24:mi:ss') , 'yyyy-mm-dd hh24-mi-ss')
                     - To_date(to_char(BEGIN_TIME,'yyyy-mm-dd hh24:mi:ss'), 'yyyy-mm-dd hh24-mi-ss')
                    ) * 24 * 60 * 60 )) as total_time""".format(group_date_field, date_format)

        group_by_str = """plan_classes_uid,
                   equip_no,
                   product_no,
                   to_char({}, '{}')""".format(group_date_field, date_format)

        if dimension == '1':
            group_by_str += ' ,classes'
            select_str += ' ,classes'

        if equip_no:
            where_str += """and equip_no like '%{}%' """.format(equip_no)
        if product_no:
            where_str += """and product_no like '%{}%' """.format(product_no)

        if st:
            try:
                datetime.datetime.strptime(st, "%Y-%m-%d")
            except Exception:
                raise ValidationError("开始日期格式错误")
            if day_type == '1':
                where_str += """and to_char(end_time, 'yyyy-mm-dd') >= '{}' """.format(st)
            else:
                where_str += """and to_char(factory_date, 'yyyy-mm-dd') >= '{}' """.format(st)

        if et:
            try:
                datetime.datetime.strptime(et, "%Y-%m-%d")
            except Exception:
                raise ValidationError("结束日期格式错误")
            if day_type == '1':
                where_str += """and to_char(end_time, 'yyyy-mm-dd') <= '{}' """.format(et)
            else:
                where_str += """and to_char(factory_date, 'yyyy-mm-dd') <= '{}' """.format(et)

        sql = """
            SELECT {}
           FROM
           trains_feedbacks
           where {}
           GROUP BY
           {}""".format(select_str, where_str, group_by_str)
        ret = {}
        cursor = connection.cursor()
        cursor.execute(sql)
        data = cursor.fetchall()
        for item in data:
            query_group_by_index = [3]
            item_dict = {
                'equip_no': item[1],
                'product_no': item[2],
                'max_trains': item[4],
                'min_trains': item[5],
                'max_train_time': item[6],
                'min_train_time': item[7],
                'total_time': item[8],
                'date': item[3]
            }
            if dimension == '1':
                query_group_by_index.append(-1)
                item_dict['classes'] = item[-1]
            diff_trains = item[4] - item[5] + 1
            item_key = ''.join([str(item[i]) for i in query_group_by_index]) + item[1] + item[2]
            if item_key not in ret:
                item_dict['total_trains'] = diff_trains
                ret[item_key] = item_dict
            else:
                ret[item_key]['total_trains'] += diff_trains
                ret[item_key]['total_time'] += item_dict['total_time']
                if ret[item_key]['max_train_time'] < item[6]:
                    ret[item_key]['max_train_time'] = item[6]
                if ret[item_key]['min_train_time'] > item[7]:
                    ret[item_key]['min_train_time'] = item[7]

        page = self.paginate_queryset(list(ret.values()))
        if day_type == '2' and dimension == '1':
            page = self.get_class_dimension_page_data(page)

        return self.get_paginated_response(page)


@method_decorator([api_recorder], name="dispatch")
class EquipBanBurySummaryView(ClassesBanBurySummaryView):
    """机台密炼统计"""
    queryset = TrainsFeedbacks.objects.all()

    def list(self, request, *args, **kwargs):
        st = self.request.query_params.get('st')  # 开始时间
        et = self.request.query_params.get('et')  # 结束时间
        dimension = self.request.query_params.get('dimension', '2')  # 维度 1：班次  2：日 3：月
        day_type = self.request.query_params.get('day_type', '2')  # 日期类型 1：自然日  2：工厂日
        equip_no = self.request.query_params.get('equip_no')  # 设备编号

        where_str = """not(CLASSES=' ') """

        if day_type == '1':  # 按照自然日
            group_date_field = 'end_time'
        else:  # 按照工厂日期
            group_date_field = 'factory_date'
            where_str += 'and factory_date is not null '

        if dimension == '3':  # 按照月份分组
            date_format = 'yyyy-mm'
        else:
            date_format = 'yyyy-mm-dd'

        select_str = """plan_classes_uid,
                            equip_no,
                           to_char({}, '{}'),
                           MAX(actual_trains) AS max_trains,
                           MIN(actual_trains) AS min_trains,
                           sum(ceil(
                            (To_date(to_char(END_TIME,'yyyy-mm-dd hh24:mi:ss') , 'yyyy-mm-dd hh24-mi-ss')
                             - To_date(to_char(BEGIN_TIME,'yyyy-mm-dd hh24:mi:ss'), 'yyyy-mm-dd hh24-mi-ss')
                            ) * 24 * 60 * 60 )) as total_time""".format(group_date_field, date_format)

        group_by_str = """plan_classes_uid,
                           equip_no,
                           to_char({}, '{}')""".format(group_date_field, date_format)

        if dimension == '1':
            group_by_str += ' ,classes'
            select_str += ' ,classes'

        if equip_no:
            where_str += """and equip_no like '%{}%' """.format(equip_no)

        if st:
            try:
                datetime.datetime.strptime(st, "%Y-%m-%d")
            except Exception:
                raise ValidationError("开始日期格式错误")
            if day_type == '1':
                where_str += """and to_char(end_time, 'yyyy-mm-dd') >= '{}' """.format(st)
            else:
                where_str += """and to_char(factory_date, 'yyyy-mm-dd') >= '{}' """.format(st)

        if et:
            try:
                datetime.datetime.strptime(et, "%Y-%m-%d")
            except Exception:
                raise ValidationError("结束日期格式错误")
            if day_type == '1':
                where_str += """and to_char(end_time, 'yyyy-mm-dd') <= '{}' """.format(et)
            else:
                where_str += """and to_char(factory_date, 'yyyy-mm-dd') <= '{}' """.format(et)

        sql = """
                    SELECT {}
                   FROM
                   trains_feedbacks
                   where {}
                   GROUP BY
                   {}""".format(select_str, where_str, group_by_str)
        ret = {}
        cursor = connection.cursor()
        cursor.execute(sql)
        data = cursor.fetchall()
        for item in data:
            query_group_by_index = [2]
            item_dict = {
                'equip_no': item[1],
                'max_trains': item[3],
                'min_trains': item[4],
                'total_time': item[5],
                'date': item[2]
            }
            if dimension == '1':
                query_group_by_index.append(-1)
                item_dict['classes'] = item[-1]
            diff_trains = item[3] - item[4] + 1
            item_key = ''.join([str(item[i]) for i in query_group_by_index]) + item[1] + item[2]
            if item_key not in ret:
                item_dict['total_trains'] = diff_trains
                ret[item_key] = item_dict
            else:
                ret[item_key]['total_trains'] += diff_trains
                ret[item_key]['total_time'] += item_dict['total_time']

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
            avg_time = sum_time / len(tfb_set)
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
        tfb_equip_uid_list = TrainsFeedbacks.objects.filter(delete_flag=False, **dict_filter).values(
            'plan_classes_uid').annotate(et=Max("end_time")).distinct().values('plan_classes_uid', 'et')
        tfb_equip_uid_list = list(tfb_equip_uid_list)
        tfb_equip_uid_list.sort(key=lambda x: x["et"], reverse=False)
        if not tfb_equip_uid_list:
            return_list.append(
                {'sum_time': None, 'max_time': None, 'min_time': None, 'avg_time': None})
            return Response({'results': return_list})
        for j in range(len(tfb_equip_uid_list) - 1):
            tfb_equip_uid_list[j].pop('et', None)
            tfb_equip_uid_list[j + 1].pop('et', None)
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
        if st:  # 第二天的头一条
            mst = datetime.datetime.strptime(st, "%Y-%m-%d") + datetime.timedelta(days=1)
            m_tfb_obj = TrainsFeedbacks.objects.filter(delete_flag=False, equip_no=equip_no,
                                                       end_time__date=mst).first()
            if m_tfb_obj:
                tfb_equip_uid_dict = tfb_equip_uid_list[-1]
                tfb_equip_uid_dict['end_time__date'] = st

                tfb_pn_age = TrainsFeedbacks.objects.filter(delete_flag=False, **tfb_equip_uid_dict).last()
                if tfb_pn_age.plan_classes_uid != m_tfb_obj.plan_classes_uid:
                    return_dict = {
                        'time': tfb_pn_age.end_time.strftime("%Y-%m-%d"),
                        'plan_classes_uid_age': tfb_pn_age.plan_classes_uid,
                        'plan_classes_uid_later': m_tfb_obj.plan_classes_uid,
                        'equip_no': tfb_pn_age.equip_no,
                        'cut_ago_product_no': tfb_pn_age.product_no,
                        'cut_later_product_no': m_tfb_obj.product_no,
                        'time_consuming': m_tfb_obj.begin_time - tfb_pn_age.end_time}
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

        # 分页
        counts = len(return_list)
        return_list = return_list[(page - 1) * page_size:page_size * page]
        return_list.append(
            {'sum_time': sum_time, 'max_time': max_time, 'min_time': min_time, 'avg_time': avg_time})
        return Response({'count': counts, 'results': return_list})
