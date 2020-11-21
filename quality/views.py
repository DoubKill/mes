import datetime

from django.utils import timezone
from datetime import timedelta
import requests
from django.db.models import Q
from django.db.transaction import atomic
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet
from basics.models import GlobalCodeType
from basics.serializers import GlobalCodeSerializer
from mes.common_code import CommonDeleteMixin
from mes.paginations import SinglePageNumberPagination
from mes.derorators import api_recorder
from plan.models import ProductClassesPlan
from production.models import PalletFeedbacks, TrainsFeedbacks
from quality.filters import TestMethodFilter, DataPointFilter, \
    MaterialTestMethodFilter, MaterialDataPointIndicatorFilter, MaterialTestOrderFilter, MaterialDealResulFilter, \
    DealSuggestionFilter, PalletFeedbacksTestFilter
from quality.models import TestIndicator, MaterialDataPointIndicator, TestMethod, MaterialTestOrder, \
    MaterialTestMethod, TestType, DataPoint, DealSuggestion, MaterialDealResult, LevelResult, MaterialTestResult, \
    LabelPrint, Batch, TestDataPoint, BatchMonth, BatchDay, BatchProductNo, BatchEquip, BatchClass
from quality.serializers import MaterialDataPointIndicatorSerializer, \
    MaterialTestOrderSerializer, MaterialTestOrderListSerializer, \
    MaterialTestMethodSerializer, TestMethodSerializer, TestTypeSerializer, DataPointSerializer, \
    DealSuggestionSerializer, DealResultDealSerializer, MaterialDealResultListSerializer, LevelResultSerializer, \
    TestIndicatorSerializer, LabelPrintSerializer, BatchMonthSerializer, BatchDaySerializer, \
    BatchCommonSerializer, BatchProductNoSerializer, BatchProductNoDaySerializer, BatchProductNoMonthSerializer
from django.db.models import Q
from django.db.models import Count
from django.db.models import FloatField
from quality.utils import print_mdr
from recipe.models import Material, ProductBatching
import logging
from django.db.models import Max, Sum

logger = logging.getLogger('send_log')


@method_decorator([api_recorder], name="dispatch")
class TestIndicatorViewSet(ModelViewSet):
    """试验指标列表"""
    queryset = TestIndicator.objects.filter(delete_flag=False)
    serializer_class = TestIndicatorSerializer

    def list(self, request, *args, **kwargs):
        data = self.queryset.values('id', 'name')
        return Response(data)


@method_decorator([api_recorder], name="dispatch")
class TestTypeViewSet(ModelViewSet):
    """试验类型管理"""
    queryset = TestType.objects.filter(delete_flag=False)
    serializer_class = TestTypeSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('test_indicator',)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'name')
            return Response({'results': data})
        return super().list(self, request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class DataPointViewSet(ModelViewSet):
    """试验类型数据点管理"""
    queryset = DataPoint.objects.filter(delete_flag=False)
    serializer_class = DataPointSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = DataPointFilter
    pagination_class = None

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'name', 'unit')
            return Response({'results': data})
        return super().list(self, request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class TestMethodViewSet(ModelViewSet):
    """试验方法管理"""
    queryset = TestMethod.objects.filter(delete_flag=False)
    serializer_class = TestMethodSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = TestMethodFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'name')
            return Response({'results': data})
        return super().list(self, request, *args, **kwargs)


@method_decorator([api_recorder], name="dispatch")
class TestIndicatorDataPointListView(ListAPIView):
    """获取试验指标及其所有的试验方法数据点"""
    queryset = TestIndicator.objects.filter(delete_flag=False)

    def list(self, request, *args, **kwargs):
        ret = []
        test_indicators = TestIndicator.objects.all()
        for test_indicator in test_indicators:
            data_names = set(DataPoint.objects.filter(
                test_type__test_indicator=test_indicator).values_list('name', flat=True))
            data = {'test_type_id': test_indicator.id,
                    'test_type_name': test_indicator.name,
                    'data_indicator_detail': [data_name for data_name in data_names]
                    }
            ret.append(data)
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class MaterialTestIndicatorMethods(APIView):
    """获取原材料指标试验方法"""

    def get(self, request):
        material_no = self.request.query_params.get('material_no')
        try:
            material = Material.objects.get(material_no=material_no)
        except Exception:
            raise ValidationError('该胶料不存在')
        ret = {}
        test_indicator_names = TestIndicator.objects.values_list('name', flat=True)
        test_methods = TestMethod.objects.all()
        for test_method in test_methods:
            indicator_name = test_method.test_type.test_indicator.name
            allowed = True
            data_points = None
            mat_test_method = MaterialTestMethod.objects.filter(
                material=material,
                test_method=test_method).first()
            if not mat_test_method:
                allowed = False
            else:
                if not MaterialDataPointIndicator.objects.filter(material_test_method=mat_test_method).exists():
                    allowed = False
                else:
                    data_points = mat_test_method.data_point.values('id', 'name', 'unit')
            if indicator_name not in ret:
                data = {
                    'test_indicator': indicator_name,
                    'methods': [
                        {'id': test_method.id,
                         'name': test_method.name,
                         'allowed': allowed,
                         'data_points': data_points}
                    ]
                }
                ret[indicator_name] = data
            else:
                ret[indicator_name]['methods'].append(
                    {'id': test_method.id, 'name': test_method.name, 'allowed': allowed, 'data_points': data_points})

        for item in test_indicator_names:
            if item not in ret:
                ret[item] = {'test_indicator': item, 'methods': []}
        return Response(ret.values())


@method_decorator([api_recorder], name="dispatch")
class MaterialTestOrderViewSet(mixins.CreateModelMixin,
                               mixins.ListModelMixin,
                               GenericViewSet):
    """
    list:
        列表展示
    create:
        手工录入数据
    """
    queryset = MaterialTestOrder.objects.filter(delete_flag=False
                                                ).prefetch_related('order_results')
    serializer_class = MaterialTestOrderSerializer
    filter_backends = (DjangoFilterBackend,)
    permission_classes = (IsAuthenticated,)
    filter_class = MaterialTestOrderFilter
    pagination_class = None

    def get_serializer_class(self):
        if self.action == 'create':
            return MaterialTestOrderSerializer
        else:
            return MaterialTestOrderListSerializer

    def create(self, request, *args, **kwargs):
        data = request.data
        if not isinstance(data, list):
            raise ValidationError('参数错误')
        for item in data:
            s = MaterialTestOrderSerializer(data=item, context={'request': request})
            if not s.is_valid():
                raise ValidationError(s.errors)
            s.save()
        return Response('新建成功')


@method_decorator([api_recorder], name="dispatch")
class MaterialTestMethodViewSet(ModelViewSet):
    """物料试验方法"""
    queryset = MaterialTestMethod.objects.filter(delete_flag=False)
    serializer_class = MaterialTestMethodSerializer
    filter_backends = (DjangoFilterBackend,)
    permission_classes = (IsAuthenticated,)
    filter_class = MaterialTestMethodFilter


@method_decorator([api_recorder], name="dispatch")
class MaterialDataPointIndicatorViewSet(ModelViewSet):
    """物料数据点评判指标"""
    queryset = MaterialDataPointIndicator.objects.filter(delete_flag=False)
    serializer_class = MaterialDataPointIndicatorSerializer
    filter_backends = (DjangoFilterBackend,)
    permission_classes = (IsAuthenticated,)
    filter_class = MaterialDataPointIndicatorFilter
    pagination_class = None


@method_decorator([api_recorder], name="dispatch")
class ProductBatchingMaterialListView(ListAPIView):
    """胶料原材料列表"""
    queryset = Material.objects.filter(delete_flag=False)

    def list(self, request, *args, **kwargs):
        batching_no = set(ProductBatching.objects.values_list('stage_product_batch_no', flat=True))
        material_data = self.queryset.filter(material_no__in=batching_no).values('id', 'material_no')
        return Response(material_data)


@method_decorator([api_recorder], name="dispatch")
class DealSuggestionViewSet(CommonDeleteMixin, ModelViewSet):
    """处理意见
        list: 查询处理意见列表
        retrive: 查询处理意见详情
        post: 新增处理意见
        put: 修改处理意见
    """
    queryset = DealSuggestion.objects.filter(delete_flag=False)
    serializer_class = DealSuggestionSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = DealSuggestionFilter
    pagination_class = SinglePageNumberPagination


@method_decorator([api_recorder], name="dispatch")
class MaterialDealResultViewSet(CommonDeleteMixin, ModelViewSet):
    """胶料处理结果
    list: 查询胶料处理结果列表
    post: 创建胶料处理结果
    put: 创建胶料处理结果
    """
    queryset = MaterialDealResult.objects.filter(~Q(deal_result="一等品")).filter(~Q(status="复测")).filter(
        delete_flag=False)
    serializer_class = DealResultDealSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialDealResulFilter


@method_decorator([api_recorder], name="dispatch")
class MaterialDealStatusListView(APIView):
    """胶料状态列表"""

    def get(self, request):
        filter_set = MaterialDealResult.objects.filter(delete_flag=False).values("status").annotate()
        return Response(filter_set)


@method_decorator([api_recorder], name="dispatch")
class DealTypeView(APIView):

    def post(self, request):
        data = request.data
        gct = GlobalCodeType.objects.filter(type_name="处理类型").first()
        if not gct:
            raise ValidationError("请先在基础信息管理下的公用代码管理内启用/创建'处理类型'")
        data.update(global_type=gct.id)
        serializer = GlobalCodeSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "ok"}, status=status.HTTP_201_CREATED)


@method_decorator([api_recorder], name="dispatch")
class MaterialDealResultUpdateValidTime(APIView):
    # 快检信息综合管理修改有效时间
    @atomic()
    def post(self, request):
        id = self.request.data.get('id', None)
        valid_time = self.request.data.get('valid_time', None)
        if not id or not valid_time:
            raise ValidationError('id或有效时间必传')
        MaterialDealResult.objects.filter(id=id).update(valid_time=valid_time)
        return Response('修改成功')


@method_decorator([api_recorder], name="dispatch")
class PalletFeedbacksTestListView(ListAPIView):
    # 快检信息综合管里
    queryset = MaterialDealResult.objects.filter(delete_flag=False)
    serializer_class = MaterialDealResultListSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = PalletFeedbacksTestFilter

    def get_queryset(self):
        equip_no = self.request.query_params.get('equip_no', None)
        product_no = self.request.query_params.get('product_no', None)
        day_time = self.request.query_params.get('day_time', None)
        classes = self.request.query_params.get('classes', None)
        schedule_name = self.request.query_params.get('schedule_name', None)
        filter_dict = {'delete_flag': False}
        pfb_filter = {}
        pcp_filter = {}
        if day_time:
            pcp_filter['work_schedule_plan__plan_schedule__day_time'] = day_time
        if schedule_name:
            pcp_filter['work_schedule_plan__plan_schedule__work_schedule__schedule_name'] = schedule_name
        if pcp_filter:
            pcp_uid_list = ProductClassesPlan.objects.filter(**pcp_filter).values_list('plan_classes_uid', flat=True)
            pfb_filter['plan_classes_uid__in'] = list(pcp_uid_list)

        if equip_no:
            pfb_filter['equip_no'] = equip_no
        if product_no:
            pfb_filter['product_no__icontains'] = product_no
        if classes:
            pfb_filter['classes'] = classes
        if pfb_filter:
            pfb_product_list = PalletFeedbacks.objects.filter(**pfb_filter).values_list('lot_no', flat=True)
            filter_dict['lot_no__in'] = list(pfb_product_list)
        pfb_queryset = MaterialDealResult.objects.filter(**filter_dict).exclude(status='复测')
        return pfb_queryset


@method_decorator([api_recorder], name="dispatch")
class LevelResultViewSet(ModelViewSet):
    """等级和结果"""
    queryset = LevelResult.objects.filter(delete_flag=False)
    serializer_class = LevelResultSerializer
    filter_backends = (DjangoFilterBackend,)
    permission_classes = (IsAuthenticated,)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        mdp_set = MaterialDataPointIndicator.objects.filter(level=instance.level, result=instance.deal_result,
                                                            delete_flag=False)
        if mdp_set:
            raise ValidationError('该等级已被使用，不能删除')
        instance.delete_flag = True
        instance.last_updated_user = request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'deal_result', 'level')
            return Response({'results': data})
        return super().list(self, request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        deal_result = self.request.data.get('deal_result', None)
        level = self.request.data.get('level', None)
        if not deal_result or not level:
            raise ValidationError('等级和检测结果必传')
        lr_obj = LevelResult.objects.filter(deal_result=deal_result, level=level, delete_flag=False).first()
        if lr_obj:
            raise ValidationError('不可重复新建')
        lr_obj = LevelResult.objects.filter(deal_result=deal_result, level=level, delete_flag=True).first()
        if lr_obj:
            lr_obj.delete_flag = False
            lr_obj.save()
            return Response('新建成功')
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


@method_decorator([api_recorder], name="dispatch")
class ProductDayStatistics(APIView):
    """胶料日合格率统计"""

    def get(self, request, *args, **kwargs):
        params = request.query_params
        month_time = params.get('ym_time', datetime.datetime.now()).month
        year_time = params.get('ym_time', datetime.datetime.now()).year
        pass_type = params.get('pass_type', '1')  # 1:综合合格率  2：一次合格率  3：流变合格率
        pass_dict = {'1': ['门尼', '比重', '硬度', '流变'], '2': ['门尼', '比重', '硬度'], '3': ['流变']}
        test_indicator_name_dict = pass_dict[pass_type]
        product_no_list = MaterialTestOrder.objects.filter(delete_flag=False,
                                                           production_factory_date__year=year_time,
                                                           production_factory_date__month=month_time).values(
            'product_no').annotate().distinct()
        ruturn_pass = []
        for product_no_dict in product_no_list:
            return_dict = {}
            return_dict['product_no'] = product_no_dict['product_no']
            for day_time in range(1, int(datetime.datetime.now().day) + 1):
                lot_no_list = MaterialTestOrder.objects.filter(delete_flag=False,
                                                               production_factory_date__year=year_time,
                                                               production_factory_date__month=month_time,
                                                               production_factory_date__day=day_time,
                                                               **product_no_dict).values('lot_no').annotate().distinct()

                # mto_count = lot_no_list.count()
                mto_count = 0  # 粒度比等级综合判定更细，是基于每一车的。而不是每一托的
                if lot_no_list.count() == 0:
                    continue
                pass_count = 0

                for lot_no_dict in lot_no_list:
                    mto_set = MaterialTestOrder.objects.filter(delete_flag=False,
                                                               production_factory_date__year=year_time,
                                                               production_factory_date__month=month_time,
                                                               production_factory_date__day=day_time,
                                                               **product_no_dict, **lot_no_dict).all()
                    if not mto_set:
                        continue
                    mto_count += mto_set.count()
                    for mto_obj in mto_set:
                        level_list = []

                        mrt_list = mto_obj.order_results.filter(
                            test_indicator_name__in=test_indicator_name_dict).all().values('data_point_name').annotate(
                            max_test_time=Max('test_times'))
                        for mrt_dict in mrt_list:
                            mrt_dict_obj = MaterialTestResult.objects.filter(material_test_order=mto_obj,
                                                                             data_point_name=mrt_dict[
                                                                                 'data_point_name'],
                                                                             test_times=mrt_dict[
                                                                                 'max_test_time']).last()
                            level_list.append(mrt_dict_obj)
                        quality_sign = True
                        for mtr_obj in level_list:
                            if not mtr_obj.mes_result:  # mes没有数据
                                if not mtr_obj.result:  # 快检也没有数据
                                    quality_sign = False
                                elif mtr_obj.result != '一等品':
                                    quality_sign = False

                            elif mtr_obj.mes_result == '一等品':
                                if mtr_obj.result not in ['一等品', None]:
                                    quality_sign = False

                            elif mtr_obj.mes_result != '一等品':
                                quality_sign = False

                        if quality_sign:
                            pass_count += 1
                percent_of_pass = str((pass_count / mto_count) * 100) + '%'
                return_dict[f'{month_time}-{day_time}'] = percent_of_pass
            ruturn_pass.append(return_dict)
        return Response(ruturn_pass)


@method_decorator([api_recorder], name="dispatch")
class LabelPrintViewSet(mixins.CreateModelMixin,
                        mixins.UpdateModelMixin,
                        GenericViewSet):
    """
    list: 获取一条打印标签
    create: 存储一条打印标签
    """
    queryset = LabelPrint.objects.all()
    serializer_class = LabelPrintSerializer
    permission_classes = ()
    authentication_classes = ()

    def list(self, request, *args, **kwargs):
        instance = self.get_queryset().filter(label_type=2, status=0).first()
        if instance:
            serializer = self.get_serializer(instance)
            data = serializer.data
        else:
            data = {}
        return Response(data)


@method_decorator([api_recorder], name="dispatch")
class DealSuggestionView(APIView):
    """处理意见展示"""

    def get(self, request, *args, **kwargs):
        queryset = MaterialDealResult.objects.filter(delete_flag=False).values('deal_suggestion').annotate().distinct()
        return Response(queryset.values_list('deal_suggestion', flat=True))


@method_decorator([api_recorder], name="dispatch")
class MaterialTestResultHistoryView(APIView):
    """试验结果数据展开列表， 参数：?test_order_id=检测单id"""

    def get(self, request):
        test_order_id = self.request.query_params.get('test_order_id')
        try:
            test_order = MaterialTestOrder.objects.get(id=test_order_id)
        except Exception:
            raise ValidationError('参数错误')
        data = MaterialTestResult.objects.filter(material_test_order=test_order).all()
        max_test_times = MaterialTestResult.objects.filter(material_test_order=test_order
                                                           ).aggregate(max_time=Max('test_times'))['max_time']
        ret = {i: {} for i in range(1, max_test_times + 1)}

        for item in data:
            indicator_name = item.test_indicator_name
            data_point_name = item.data_point_name
            test_times = item.test_times
            test_result = {
                'value': item.value,
                'result': item.result,
                'mes_result': item.mes_result,
                'machine_name': item.machine_name,
                'level': item.level,
                'test_times': item.test_times
            }
            if indicator_name not in ret[test_times]:
                ret[test_times][indicator_name] = {data_point_name: test_result}
            else:
                ret[test_times][indicator_name][data_point_name] = test_result
        return Response(ret)


@method_decorator([api_recorder], name="dispatch")
class ProductDayDetail(APIView):
    """胶料日合格率详细信息统计"""

    # 伪代码
    def get(self, request, *args, **kwargs):
        params = request.query_params
        month_time = params.get('ym_time', datetime.datetime.now()).month
        year_time = params.get('ym_time', datetime.datetime.now()).year
        product_no = params.get('product_no', 'C-FM-UC109-001')
        pass_dict = {'1': ['门尼', '比重', '硬度', '流变'], '2': ['门尼', '比重', '硬度'], '3': ['流变']}
        name_dict = {'1': '综合合格率', '2': '一次合格率', '3': '流变合格率'}

        ruturn_pass = []
        return_dict = {}

        for day_time in range(1, int(datetime.datetime.now().day) + 1):
            # 1、胶料编码
            return_dict['product_no'] = product_no
            lot_no_list = MaterialTestOrder.objects.filter(delete_flag=False,
                                                           production_factory_date__year=year_time,
                                                           production_factory_date__month=month_time,
                                                           production_factory_date__day=day_time,
                                                           product_no=product_no).values('lot_no').annotate().distinct()

            mto_count = lot_no_list.count()
            if mto_count == 0:
                continue
            return_dict = {}
            # 2、当天的日期也要返回给前端
            return_dict['day_time'] = str(year_time) + '-' + str(month_time) + '-' + str(day_time)
            # 3、计算产量 车次
            plan_classes_uid_list = MaterialTestOrder.objects.filter(delete_flag=False,
                                                                     production_factory_date__year=year_time,
                                                                     production_factory_date__month=month_time,
                                                                     production_factory_date__day=day_time,
                                                                     product_no=product_no).values(
                'plan_classes_uid').annotate().distinct().values_list('plan_classes_uid', flat=True)
            tfb_train_list = TrainsFeedbacks.objects.filter(end_time__year=year_time, end_time__month=month_time,
                                                            end_time__day=day_time,
                                                            plan_classes_uid__in=plan_classes_uid_list).values(
                'plan_classes_uid').annotate(max_train=Max('actual_trains')).aggregate(sum_train=Sum('max_train'))
            return_dict['sum_train'] = tfb_train_list['sum_train']

            # 4、 循环三种指标类型，得到合格率
            for tin_key in pass_dict.keys():
                pass_count = 0
                test_indicator_name_dict = pass_dict[tin_key]

                for lot_no_dict in lot_no_list:
                    mto_set = MaterialTestOrder.objects.filter(delete_flag=False,
                                                               production_factory_date__year=year_time,
                                                               production_factory_date__month=month_time,
                                                               production_factory_date__day=day_time,
                                                               product_no=product_no, **lot_no_dict).all()
                    if not mto_set:
                        continue
                    level_list = []
                    for mto_obj in mto_set:
                        mrt_list = mto_obj.order_results.filter(
                            test_indicator_name__in=test_indicator_name_dict).all().values('data_point_name').annotate(
                            max_test_time=Max('test_times'))
                        for mrt_dict in mrt_list:
                            mrt_dict_obj = MaterialTestResult.objects.filter(material_test_order=mto_obj,
                                                                             data_point_name=mrt_dict[
                                                                                 'data_point_name'],
                                                                             test_times=mrt_dict[
                                                                                 'max_test_time']).last()
                            level_list.append(mrt_dict_obj)
                    quality_sign = True
                    for mtr_obj in level_list:
                        if not mtr_obj.mes_result:  # mes没有数据
                            if not mtr_obj.result:  # 快检也没有数据
                                quality_sign = False
                            elif mtr_obj.result != '一等品':
                                quality_sign = False

                        elif mtr_obj.mes_result == '一等品':
                            if mtr_obj.result not in ['一等品', None]:
                                quality_sign = False

                        elif mtr_obj.mes_result != '一等品':
                            quality_sign = False

                    if quality_sign:
                        pass_count += 1
                percent_of_pass = str((pass_count / mto_count) * 100) + '%'
                return_dict[name_dict[tin_key]] = percent_of_pass

            # 5、计算每个数据点超出的上下限
            point_count = {}
            point_upper = {}
            point_lower = {}
            for lot_no_dict in lot_no_list:
                mto_set = MaterialTestOrder.objects.filter(delete_flag=False,
                                                           production_factory_date__year=year_time,
                                                           production_factory_date__month=month_time,
                                                           production_factory_date__day=day_time,
                                                           product_no=product_no, **lot_no_dict).all()
                if not mto_set:
                    continue

                for mto_obj in mto_set:
                    mrt_list = mto_obj.order_results.filter().all().values('data_point_name').annotate(
                        max_test_time=Max('test_times'))

                    for mrt_dict in mrt_list:
                        level_list = []
                        mtr_obj = MaterialTestResult.objects.filter(material_test_order=mto_obj,
                                                                    data_point_name=mrt_dict[
                                                                        'data_point_name'],
                                                                    test_times=mrt_dict[
                                                                        'max_test_time']).last()
                        if not mtr_obj.data_point_indicator:
                            continue
                        if mrt_dict['data_point_name'] not in point_count.keys():
                            point_count[mrt_dict['data_point_name']] = 0
                        point_count[mrt_dict['data_point_name']] += 1
                        mdp_obj = MaterialDataPointIndicator.objects.filter(
                            material_test_method=mtr_obj.data_point_indicator.material_test_method,
                            data_point=mtr_obj.data_point_indicator.data_point, result='一等品').first()

                        if mtr_obj.data_point_indicator:
                            if mtr_obj.value > mdp_obj.upper_limit:
                                if mrt_dict['data_point_name'] not in point_upper.keys():
                                    point_upper[mrt_dict['data_point_name']] = 0
                                point_upper[mrt_dict['data_point_name']] += 1
                            elif mtr_obj.value < mdp_obj.lower_limit:
                                if mrt_dict['data_point_name'] not in point_lower.keys():
                                    point_lower[mrt_dict['data_point_name']] = 0
                                point_lower[mrt_dict['data_point_name']] += 1

            for point in point_count.keys():
                return_dict[point] = {}
                if point in point_upper.keys():
                    return_dict[point]['+'] = point_upper[point]
                    return_dict[point]['+%'] = str((point_upper[point] / point_count[point]) * 100) + '%'
                if point in point_lower.keys():
                    return_dict[point]['-'] = point_lower[point]
                    return_dict[point]['-%'] = str((point_lower[point] / point_count[point]) * 100) + '%'
            ruturn_pass.append(return_dict)
        return Response(ruturn_pass)


class PrintMaterialDealResult(APIView):
    """不合格品打印功能"""

    def get(self, request, *args, **kwargs):
        day = self.request.query_params.get('day', None)
        status = self.request.query_params.get('status', None)
        filter_dict = {}
        if day:
            filter_dict['production_factory_date__icontains'] = day
        if status:
            filter_dict['status'] = status
        MaterialDealResult.objects.filter()
        mdr_set = MaterialDealResult.objects.filter(~Q(deal_result="一等品")).filter(~Q(status="复测")).filter(**filter_dict,
                                                                                                          delete_flag=False)
        return print_mdr("results", mdr_set)


def get_statics_query_dates(query_params):
    start_time = query_params.get('start_time')
    end_time = query_params.get('end_time')
    try:
        start_time = datetime.datetime.strptime(start_time, '%Y-%m') \
            if start_time else timezone.now() - timedelta(days=365)
        end_time = datetime.datetime.strptime(end_time, '%Y-%m') \
            if end_time else timezone.now()
    except ValueError:
        raise ValidationError('日期格式:yyyy-mm')
    return start_time, end_time


class BatchMonthStatisticsView(ReadOnlyModelViewSet):
    queryset = BatchMonth.objects.all()
    serializer_class = BatchMonthSerializer

    @action(detail=False)
    def statistic_headers(self, request):
        result = {
            'points': TestDataPoint.objects.values_list('name', flat=True).distinct(),
            'equips': BatchEquip.objects.values_list('production_equip_no', flat=True).distinct(),
            'classes': BatchClass.objects.values_list('production_class', flat=True).distinct()
        }
        return Response(result)

    def get_queryset(self):
        start_time, end_time = get_statics_query_dates(self.request.query_params)
        batches = BatchMonth.objects.filter(date__gte=start_time,
                                            date__lte=end_time)
        if batches:
            batches = BatchCommonSerializer.batch_annotate(batches)
            batches = batches.order_by('date')
        return batches


def get_statics_query_date(query_params):
    date = query_params.get('date')
    try:
        date = datetime.datetime.strptime(date, '%Y-%m') if date else timezone.now()
    except ValueError:
        raise ValidationError('日期格式:yyyy-mm')
    return date


class BatchDayStatisticsView(ReadOnlyModelViewSet):
    queryset = BatchDay.objects.all()
    serializer_class = BatchDaySerializer

    def get_queryset(self):
        date = get_statics_query_date(self.request.query_params)
        batches = BatchDay.objects.filter(date__year=date.year,
                                          date__month=date.month)
        if batches:
            batches = BatchCommonSerializer.batch_annotate(batches)
            batches = batches.order_by('date')

        return batches


class BatchProductNoDayStatisticsView(ReadOnlyModelViewSet):
    queryset = BatchProductNo.objects.all()
    serializer_class = BatchProductNoDaySerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ['product_no']

    def get_queryset(self):
        date = get_statics_query_date(self.request.query_params)
        return BatchProductNo.objects.filter(
            batch__batch_month__date__year=date.year,
            batch__batch_month__date__month=date.month).distinct()


class BatchProductNoMonthStatisticsView(ReadOnlyModelViewSet):
    queryset = BatchProductNo.objects.all()
    serializer_class = BatchProductNoMonthSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ['product_no']

    def get_queryset(self):
        start_time, end_time = get_statics_query_dates(self.request.query_params)
        return BatchProductNo.objects.filter(
            batch__batch_month__date__gte=start_time,
            batch__batch_month__date__lte=end_time).distinct()
