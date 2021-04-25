from django.db import connection
from django.db.models import Q, Max, Sum, Count, F, DecimalField
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.views import APIView

from basics.models import WorkSchedulePlan, Equip
from inventory.models import InventoryLog, DispatchLog, FinalGumInInventoryLog, MixGumInInventoryLog
from mes import settings
from mes.common_code import get_weekdays
from mes.derorators import api_recorder
from plan.models import ProductClassesPlan
from production.filters import CollectTrainsFeedbacksFilter
from production.models import TrainsFeedbacks
from production.serializers import CollectTrainsFeedbacksSerializer
import datetime
from rest_framework.response import Response

from quality.models import MaterialTestOrder


@method_decorator([api_recorder], name="dispatch")
class ClassesBanBurySummaryView(ListAPIView):
    """班次密炼统计"""
    queryset = TrainsFeedbacks.objects.all()
    pagination_class = None

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
                   to_char({}, '{}') AS "date",
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
        classes_order = ''

        if dimension == '1':
            group_by_str += ' ,classes'
            select_str += ' ,classes'
            classes_order = ',classes desc'
        order_by_str = """ "date",product_no {}, equip_no""".format(classes_order)

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
           GROUP BY {}
           order by {};""".format(select_str, where_str, group_by_str, order_by_str)
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

        data = ret.values()
        if day_type == '2' and dimension == '1':
            data = self.get_class_dimension_page_data(ret.values())

        return Response(data)


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
                           to_char({}, '{}') AS "date",
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
                   GROUP BY {}
                   order by "date";""".format(select_str, where_str, group_by_str)
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

        data = ret.values()
        if day_type == '2' and dimension == '1':
            data = self.get_class_dimension_page_data(ret.values())

        return Response(data)


@method_decorator([api_recorder], name="dispatch")
class CollectTrainsFeedbacksList(ListAPIView):
    """胶料单车次时间汇总"""
    queryset = TrainsFeedbacks.objects.filter(delete_flag=False).order_by('product_time', 'actual_trains')
    serializer_class = CollectTrainsFeedbacksSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = CollectTrainsFeedbacksFilter
    permission_classes = (IsAuthenticatedOrReadOnly,)


@method_decorator([api_recorder], name="dispatch")
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
            dict_filter['factory_date'] = st
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
            dict_filter['factory_date'] = st
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
                tfb_equip_uid_dict_ago['factory_date'] = st
                tfb_equip_uid_dict_later['factory_date'] = st

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
                tfb_equip_uid_dict['factory_date'] = st

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


@method_decorator([api_recorder], name="dispatch")
class IndexOverview(APIView):
    """首页-今日概况"""

    @staticmethod
    def get_current_factory_date():
        # 获取当前时间的工厂日期，开始、结束时间
        now = datetime.datetime.now()
        current_work_schedule_plan = WorkSchedulePlan.objects.filter(
            start_time__lte=now,
            end_time__gte=now,
            plan_schedule__work_schedule__work_procedure__global_name='密炼'
        ).first()
        if current_work_schedule_plan:
            date_now = str(current_work_schedule_plan.plan_schedule.day_time)
            begin_time = str(current_work_schedule_plan.start_time)
            end_time = str(current_work_schedule_plan.end_time)
        else:
            date_now = str(now.date())
            begin_time = date_now + '00:00:01'
            end_time = date_now + '23:59:59'

        return date_now, begin_time, end_time

    def get(self, request):
        ret = {}
        factory_date, _, _ = self.get_current_factory_date()

        # 日计划量
        plan_data = ProductClassesPlan.objects.filter(
            work_schedule_plan__plan_schedule__day_time=factory_date,
            delete_flag=False
        ).aggregate(total_trains=Sum('plan_trains'),
                    total_weight=Sum(F('plan_trains') * F('product_batching__batching_weight'),
                                     output_field=DecimalField())/1000)

        # 日总产量
        # actual_weight = TrainsFeedbacks.objects.filter(
        #     factory_date=factory_date
        # ).aggregate(total_weight=Sum('actual_weight'))['total_weight']
        # actual_trains = TrainsFeedbacks.objects.filter(
        #     factory_date=factory_date
        # ).values('plan_classes_uid').annotate(max_trains=Max('actual_trains')).values_list('max_trains', flat=True)
        # actual_data = {'total_trains': sum(actual_trains), 'total_weight': actual_weight}
        actual_data = TrainsFeedbacks.objects.filter(
            factory_date=factory_date
        ).aggregate(total_trains=Count('id'),
                    total_weight=Sum('actual_weight')/1000)

        # 日入库量
        try:
            final_gum_data = FinalGumInInventoryLog.objects.using('lb').filter(
                start_time__date=factory_date).aggregate(
                total_trains=Count('qty'),
                total_weight=Sum('weight')/1000)
            final_gum_qyt = final_gum_data['total_trains'] if final_gum_data['total_trains'] else 0
            final_gum_weight = final_gum_data['total_weight'] if final_gum_data['total_weight'] else 0

            mix_gum_data = MixGumInInventoryLog.objects.using('bz').filter(
                start_time__date=factory_date).aggregate(
                total_trains=Count('qty'),
                total_weight=Sum('weight') / 1000)
            mix_gum_qyt = mix_gum_data['total_trains'] if mix_gum_data['total_trains'] else 0
            mix_gum_weight = mix_gum_data['total_weight'] if mix_gum_data['total_weight'] else 0
        except Exception:
            final_gum_qyt = final_gum_weight = 0
            mix_gum_qyt = mix_gum_weight = 0
        inbound_data = {
                        'total_trains': final_gum_qyt + mix_gum_qyt,
                        'total_weight': final_gum_weight + mix_gum_weight
        }

        # 日出库量
        outbound_data = InventoryLog.objects.filter(
            fin_time__date=factory_date
        ).aggregate(total_trains=Sum('qty'),
                    total_weight=Sum('weight')/1000)

        # 日发货量
        dispatch_data = DispatchLog.objects.filter(
            order_created_time=factory_date
        ).aggregate(total_trains=Sum('qty'),
                    total_weight=Sum('weight')/1000)

        # 日合格率
        qualified_count = MaterialTestOrder.objects.filter(production_factory_date=factory_date,
                                                            is_qualified=True).count()
        total_test_count = MaterialTestOrder.objects.filter(production_factory_date=factory_date).count()
        try:
            qualified_rate = round(qualified_count / total_test_count * 100, 2)
        except ZeroDivisionError:
            qualified_rate = 0
        except Exception:
            raise

        ret['plan_data'] = plan_data
        ret['actual_data'] = actual_data
        ret['qualified_rate'] = '{}%'.format(qualified_rate)
        ret['outbound_data'] = outbound_data
        ret['dispatch_data'] = dispatch_data
        ret['inbound_data'] = inbound_data
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class IndexProductionAnalyze(APIView):
    """首页-产量分析/合格率分析，参数?dimension=xxx   1:周；2:月"""

    def get(self, request):
        dimension = self.request.query_params.get('dimension', '1')
        if dimension == '1':  # 周
            date_range = get_weekdays(7)
        else:  # 月
            date_range = get_weekdays(datetime.datetime.now().day)
        if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.oracle':
            actual_extra_where_str = " where to_char(tf.factory_date, 'yyyy-mm-dd')>='{}' and to_char(tf.factory_date, 'yyyy-mm-dd')<='{}'".format(date_range[0], date_range[-1])
            plan_extra_where_str = " and to_char(ps.day_time, 'yyyy-mm-dd')>='{}' and to_char(ps.day_time, 'yyyy-mm-dd')<='{}'".format(date_range[0], date_range[-1])
        else:
            actual_extra_where_str = " where tf.factory_date>='{}' and tf.factory_date<='{}'".format(date_range[0], date_range[-1])
            plan_extra_where_str = " and ps.day_time>='{}' and ps.day_time<='{}'".format(date_range[0], date_range[-1])
        cursor = connection.cursor()

        plan_sql = """
                    select
                   day_time,
                   stage_name,
                   sum(plan_trains) as total_plan_trains
            from(
                select
                       ps.day_time,
                       (CASE
                        WHEN gc.global_name='FM' THEN '加硫'
                        ELSE '无硫' END) as stage_name,
                       sum(pcp.plan_trains) as plan_trains
                from
                    product_classes_plan pcp
                    inner join work_schedule_plan wsp on pcp.work_schedule_plan_id = wsp.id
                    inner join plan_schedule ps on wsp.plan_schedule_id = ps.id
                    inner join equip e on pcp.equip_id = e.id
                    inner join product_batching pb on pcp.product_batching_id = pb.id
                    inner join global_code gc on pb.stage_id = gc.id
                where pcp.delete_flag=0 {}
                group by ps.day_time, gc.global_name) tmp
            group by day_time, stage_name order by day_time;""".format(plan_extra_where_str)
        cursor.execute(plan_sql)
        plan_data = cursor.fetchall()

        actual_sql = """
                    select
                   factory_date,
                   stage_name,
                   sum(actual_trains) as total_acctual_trains
            from(
                select
                       tf.factory_date,
                       (CASE
                        WHEN gc.GLOBAL_NAME='FM' THEN '加硫'
                        ELSE '无硫' END) as stage_name,
                       count(tf.id) as actual_trains
                from
                    trains_feedbacks tf
                inner join product_classes_plan pcp on tf.plan_classes_uid=pcp.plan_classes_uid
                inner join product_batching pb on pb.ID=pcp.product_batching_id
                inner join global_code gc on gc.ID=pb.stage_id
                {}
                group by tf.factory_date, gc.global_name order by tf.factory_date) tmp
            group by factory_date, stage_name order by factory_date;""".format(actual_extra_where_str)

        cursor.execute(actual_sql)
        actual_data = cursor.fetchall()

        plan_data_dict = {}
        for item in plan_data:
            plan_date = item[0].strftime("%Y-%m-%d")
            if plan_date in plan_data_dict:
                plan_data_dict[plan_date][item[1]] = int(item[2])
            else:
                plan_data_dict[plan_date] = {item[1]: int(item[2])}
        actual_data_dict = {}
        for item in actual_data:
            actual_date = item[0].strftime("%Y-%m-%d")
            if actual_date in actual_data_dict:
                actual_data_dict[actual_date][item[1]] = int(item[2])
            else:
                actual_data_dict[actual_date] = {item[1]: int(item[2])}

        # 日合格率
        test_date_qualify_group = MaterialTestOrder.objects.filter(
            production_factory_date__in=date_range
        ).values('is_qualified', 'production_factory_date').annotate(count=Count('id'))
        test_date_group = MaterialTestOrder.objects.filter(
            production_factory_date__in=date_range
        ).values('production_factory_date').annotate(count=Count('id'))
        test_date_group_dict = {str(item['production_factory_date']): item for item in test_date_group}
        test_date_qualify_group_dict = {}
        for item in test_date_qualify_group:
            factory_date = str(item['production_factory_date'])
            if item['is_qualified']:
                test_date_qualify_group_dict[factory_date] = round(
                    item['count'] / test_date_group_dict[factory_date]['count'] * 100, 2)
                test_date_qualify_group_dict[factory_date] = {
                    'rate': round(item['count'] / test_date_group_dict[factory_date]['count'] * 100, 2),
                    'total': test_date_group_dict[factory_date]['count'],
                    'qualified_count': item['count']
                }
                continue
            test_date_qualify_group_dict[factory_date] = {
                'rate': 0,
                'total': test_date_group_dict[factory_date]['count'],
                'qualified_count': 0
            }

        plan_actual_data = {}
        qualified_rate_data = {}
        for date in date_range:
            qualified_rate_data[date] = {'rate': 0, 'total': 0, 'qualified_count': 0}
            plan_actual_data[date] = {
                                            'plan_trains': 0,
                                            'actual_trains': 0,
                                            'plan_add_sulfur_trains': 0,
                                            'plan_without_sulfur_trains': 0,
                                            'actual_add_sulfur_trains': 0,
                                            'actual_without_sulfur_trains': 0,
                                            'diff_trains': 0
                                        }
            if date in plan_data_dict:
                if '无硫' in plan_data_dict[date]:
                    without_sulfur_num = plan_data_dict[date]['无硫']
                    plan_actual_data[date]['plan_without_sulfur_trains'] = without_sulfur_num
                if '加硫' in plan_data_dict[date]:
                    add_sulfur_num = plan_data_dict[date]['加硫']
                    plan_actual_data[date]['plan_add_sulfur_trains'] = add_sulfur_num
                plan_actual_data[date]['plan_trains'] = plan_actual_data[date]['plan_add_sulfur_trains'] + plan_actual_data[date]['plan_without_sulfur_trains']

            if date in actual_data_dict:
                if '无硫' in actual_data_dict[date]:
                    without_sulfur_num = actual_data_dict[date]['无硫']
                    plan_actual_data[date]['actual_without_sulfur_trains'] = without_sulfur_num
                if '加硫' in actual_data_dict[date]:
                    add_sulfur_num = actual_data_dict[date]['加硫']
                    plan_actual_data[date]['actual_add_sulfur_trains'] = add_sulfur_num
                plan_actual_data[date]['actual_trains'] = plan_actual_data[date]['actual_without_sulfur_trains'] + plan_actual_data[date]['actual_add_sulfur_trains']

            plan_actual_data[date]['diff_trains'] = plan_actual_data[date]['plan_trains'] - \
                                                        plan_actual_data[date]['actual_trains']

            if date in test_date_qualify_group_dict:
                qualified_rate_data[date] = test_date_qualify_group_dict[date]
        return Response({'plan_actual_data': plan_actual_data,
                         'qualified_rate_data': qualified_rate_data,
                         'date_range': date_range})


@method_decorator([api_recorder], name="dispatch")
class IndexEquipProductionAnalyze(IndexOverview):
    """首页-机台产量分析, 参数?dimension=1:今天；2:昨天&st=开始日期&et=结束日期"""

    def get(self, request):
        dimension = self.request.query_params.get('dimension')
        st = self.request.query_params.get('st')
        et = self.request.query_params.get('et')

        factory_date, _, _ = self.get_current_factory_date()
        plan_query_params = {}
        actual_query_params = {}

        if dimension:
            if dimension == '1':  # 今天
                plan_query_params['work_schedule_plan__plan_schedule__day_time'] = factory_date
                actual_query_params['factory_date'] = factory_date
            elif dimension == '2':  # 昨天
                yesterday = datetime.datetime.strptime(factory_date, '%Y-%m-%d') - datetime.timedelta(days=1)
                plan_query_params['work_schedule_plan__plan_schedule__day_time'] = yesterday.date()
                actual_query_params['factory_date'] = yesterday.date()

        if st and et:
            if et > factory_date:
                raise ValidationError('结束日期不得大于当前工厂日期！')
            plan_query_params = {'work_schedule_plan__plan_schedule__day_time__gte': st,
                                 'work_schedule_plan__plan_schedule__day_time__lte': et}
            actual_query_params = {'factory_date__gte': st, 'factory_date__lte': et}

        equip_data = [equip.equip_no for equip in Equip.objects.filter(
            category__equip_type__global_name='密炼设备').order_by('equip_no')]

        # 当日计划与实际数据
        plan_data = ProductClassesPlan.objects.filter(**plan_query_params).filter(delete_flag=False).values(
            'equip__equip_no').annotate(plan_trains=Sum('plan_trains'))
        actual_data = TrainsFeedbacks.objects.filter(
            **actual_query_params).values('equip_no').annotate(actual_trains=Count('id'))

        plan_data_dict = {item['equip__equip_no']: item for item in plan_data}
        actual_data_dict = {item['equip_no']: item for item in actual_data}

        plan_actual_data = {}
        for equip_no in equip_data:
            plan_actual_data[equip_no] = {'plan_trains': 0, 'actual_trains': 0}
            if equip_no in plan_data_dict:
                plan_actual_data[equip_no]['plan_trains'] = plan_data_dict[equip_no]['plan_trains']
            if equip_no in actual_data_dict:
                plan_actual_data[equip_no]['actual_trains'] = actual_data_dict[equip_no]['actual_trains']
            plan_actual_data[equip_no]['diff_trains'] = plan_actual_data[equip_no]['plan_trains'] - \
                                                        plan_actual_data[equip_no]['actual_trains']
        return Response({'plan_actual_data': plan_actual_data,
                         'equip_data': equip_data})


@method_decorator([api_recorder], name="dispatch")
class IndexEquipMaintenanceAnalyze(IndexOverview):
    """首页-机台停机时间分析,参数?dimension=1:今天；2:昨天&st=开始日期&et=结束日期"""

    def get(self, request):
        dimension = self.request.query_params.get('dimension')
        st = self.request.query_params.get('st')
        et = self.request.query_params.get('et')
        factory_date, factory_begin_time, _ = self.get_current_factory_date()

        equip_data = [equip.equip_no for equip in Equip.objects.filter(
            category__equip_type__global_name='密炼设备').order_by('equip_no')]

        time_now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        end_time = "To_date('{}', 'yyyy-mm-dd hh24-mi-ss')".format(time_now)

        st_case_str = "emo.DOWN_TIME"
        if dimension:
            if dimension == '1':  # 今天
                date = factory_date
                begin_time = factory_begin_time
                extra_where_str = " and to_char(emo.FACTORY_DATE, 'yyyy-mm-dd')='{}'".format(date)
            elif dimension == '2':  # 昨天
                yesterday = datetime.datetime.strptime(factory_date, '%Y-%m-%d') - datetime.timedelta(days=1)
                date = str(yesterday.date())
                yesterday_begin_time = "{} 08:00:00".format(date)
                end_time = "To_date('{}', 'yyyy-mm-dd hh24-mi-ss')".format(factory_begin_time)
                begin_time = yesterday_begin_time
                extra_where_str = " and to_char(emo.FACTORY_DATE, 'yyyy-mm-dd')='{}'".format(date)
            else:  # 所有
                begin_time = None
                extra_where_str = ''
        elif st and et:
            if et > factory_date:
                raise ValidationError('结束日期不得大于当前工厂日期！')
            # et工厂结束时间
            et_end_time = str(
                (datetime.datetime.strptime(et, '%Y-%m-%d') + datetime.timedelta(days=1)).date()
            ) + " 08:00:00"
            if et == factory_date:
                et_end_time = time_now
            end_time = """To_date('{}', 'yyyy-mm-dd hh24-mi-ss')""".format(et_end_time)
            begin_time = st + " 08:00:00"  # st工厂日期开始时间
            extra_where_str = " and to_char(emo.FACTORY_DATE, 'yyyy-mm-dd')>='{}' and to_char(emo.FACTORY_DATE, 'yyyy-mm-dd')<='{}'".format(st, et)
        else:
            raise ValidationError('参数错误')
        if begin_time:
            st_case_str = """
                        (
                            case when emo.DOWN_TIME < to_date('{}', 'yyyy-mm-dd hh24-mi-ss')
                        THEN
                        to_date('{}', 'yyyy-mm-dd hh24-mi-ss')
                        else emo.DOWN_TIME
                        end
                        )
                        """.format(begin_time, begin_time)

        sql = """
        select
                equip_no,
                sum(ceil((To_date(to_char(et,'yyyy-mm-dd hh24:mi:ss') , 'yyyy-mm-dd hh24-mi-ss')
                             - To_date(to_char(st,'yyyy-mm-dd hh24:mi:ss'), 'yyyy-mm-dd hh24-mi-ss')
                            ) * 24 * 60 ))
            from (
                select
                       equip_no,
                       {} as st,
                       (CASE WHEN emo.end_time is null THEN {}
                         ELSE emo.end_time END) as et
                from EQUIP_MAINTENANCE_ORDER emo
                inner join EQUIP_PART ep on emo.equip_part_id = ep.id
                inner join EQUIP e on ep.equip_id = e.id
                where emo.DOWN_FLAG=1 {}) tmp
        group by equip_no;""".format(st_case_str, end_time, extra_where_str)

        cursor = connection.cursor()
        cursor.execute(sql)
        data = cursor.fetchall()
        data_dict = {item[0]: int(item[1]) for item in data}

        maintenance_data = {}
        for equip_no in equip_data:
            maintenance_data[equip_no] = {'minutes': 0}
            if equip_no in data_dict:
                maintenance_data[equip_no]['minutes'] += data_dict[equip_no]

        return Response({'maintenance_data': maintenance_data,
                         'equip_data': equip_data})