from django.db.models import Sum, F, Min, Max, Avg
from django.db.models.functions import TruncMonth
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView

from production.models import TrainsFeedbacks

DIMENSION_TYPE = {
    '1': 'classes',
    '2': 'end_time__date',
    '3': 'month'
}


class ClassesBanBurySummaryView(ListAPIView):
    """班次密炼统计"""
    queryset = TrainsFeedbacks.objects.all()

    def list(self, request, *args, **kwargs):
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
        if day_type:
            if day_type == '2':  # 按照工厂日期
                DIMENSION_TYPE['2'] = 'factory_data'

        # 默认需要分组的字段
        group_by_fields = ['plan_classes_uid', 'equip_no', 'product_no']
        try:
            query_group_by_field = DIMENSION_TYPE[dimension]  # 从前端获取的分组字段
        except Exception:
            raise ValidationError('参数错误')
        group_by_fields.append(query_group_by_field)

        if dimension == '3':
            # 按月的维度分组，查询写法不一样
            data = TrainsFeedbacks.objects.annotate(
                month=TruncMonth('end_time')).filter(**kwargs).values(*group_by_fields).annotate(
                            total_trains=Max('actual_trains'),
                            total_time=Sum(F('end_time') - F('begin_time'))/1000000,
                            min_train_time=Min(F('end_time') - F('begin_time'))/1000000,
                            max_train_time=Max(F('end_time') - F('begin_time'))/1000000,
                            avg_train_time=Avg(F('end_time') - F('begin_time'))/1000000
                        )
        else:
            data = TrainsFeedbacks.objects.filter(**kwargs).values(*group_by_fields).annotate(
                total_trains=Max('actual_trains'),
                total_time=Sum(F('end_time') - F('begin_time'))/1000000,
                min_train_time=Min(F('end_time') - F('begin_time'))/1000000,
                max_train_time=Max(F('end_time') - F('begin_time'))/1000000,
                avg_train_time=Avg(F('end_time') - F('begin_time'))/1000000
            )
        ret = {}
        for item in data:
            item_key = str(item[query_group_by_field]) + item['equip_no'] + item['product_no']
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
        if day_type:
            if day_type:
                if day_type == '2':  # 按照工厂日期
                    DIMENSION_TYPE['2'] = 'factory_data'

        # 默认需要分组的字段
        group_by_fields = ['plan_classes_uid', 'equip_no']
        try:
            query_group_by_field = DIMENSION_TYPE[dimension]  # 从前端获取的分组字段
        except Exception:
            raise ValidationError('参数错误')
        group_by_fields.append(query_group_by_field)

        if dimension == '3':
            # 按月的维度分组，查询写法不一样
            data = TrainsFeedbacks.objects.annotate(
                month=TruncMonth('end_time')).filter(**kwargs).values(*group_by_fields).annotate(
                            total_trains=Max('actual_trains'),
                            total_time=Sum(F('end_time') - F('begin_time'))/1000000,
                        )
        else:
            data = TrainsFeedbacks.objects.filter(**kwargs).values(*group_by_fields).annotate(
                total_trains=Max('actual_trains'),
                total_time=Sum(F('end_time') - F('begin_time'))/1000000,
            )
        ret = {}
        for item in data:
            item_key = str(item[query_group_by_field]) + item['equip_no']
            if item_key not in ret:
                ret[item_key] = item
            else:
                ret[item_key]['total_trains'] += item['total_trains']
                ret[item_key]['total_time'] += item['total_time']

        page = self.paginate_queryset(list(ret.values()))
        return self.get_paginated_response(page)