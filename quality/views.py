from django.db.transaction import atomic
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet, ViewSet

from basics.models import GlobalCodeType
from basics.serializers import GlobalCodeSerializer
from mes.common_code import CommonDeleteMixin
from mes.paginations import SinglePageNumberPagination
from mes.derorators import api_recorder
from plan.models import ProductClassesPlan
from production.models import PalletFeedbacks
from quality.filters import TestMethodFilter, DataPointFilter, \
    MaterialTestMethodFilter, MaterialDataPointIndicatorFilter, MaterialTestOrderFilter, MaterialDealResulFilter, \
    DealSuggestionFilter, PalletFeedbacksTestFilter
from quality.models import TestIndicator, MaterialDataPointIndicator, TestMethod, MaterialTestOrder, \
    MaterialTestMethod, TestType, DataPoint, DealSuggestion, MaterialDealResult, LevelResult
from quality.serializers import MaterialDataPointIndicatorSerializer, \
    MaterialTestOrderSerializer, MaterialTestOrderListSerializer, \
    MaterialTestMethodSerializer, TestMethodSerializer, TestTypeSerializer, DataPointSerializer, \
    DealSuggestionSerializer, DealResultDealSerializer, MaterialDealResultListSerializer, LevelResultSerializer
from recipe.models import Material, ProductBatching


@method_decorator([api_recorder], name="dispatch")
class TestIndicatorListView(ListAPIView):
    """试验指标列表"""
    queryset = TestIndicator.objects.filter(delete_flag=False)

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
                        {'id': 1,
                         'name': test_method.name,
                         'allowed': allowed,
                         'data_points': data_points}
                    ]
                }
                ret[indicator_name] = data
            else:
                ret[indicator_name]['methods'].append(
                    {'id': 1, 'name': test_method.name, 'allowed': allowed, 'data_points': data_points})

        for item in test_indicator_names:
            if item not in ret:
                ret[item] = {'test_indicator': item, 'methods': []}
        return Response(ret.values())


# class MaterialTestIndicatorsTabView(ListAPIView):
#     """获取原材料及其试验类型表格数据，参数：?material_no=xxx"""
#     permission_classes = (IsAuthenticated, )
#     queryset = Material.objects.all()
#
#     def list(self, request, *args, **kwargs):
#         material_no = self.request.query_params.get('material_no')
#         material_data = MaterialTestMethod.objects.filter(delete_flag=False)
#         if material_no:
#             material_data = material_data.filter(material__material_no__icontains=material_no)
#         material_ids = set(material_data.values_list('material_id', flat=True))
#         materials = Material.objects.filter(id__in=material_ids)
#         page_materials = self.paginate_queryset(materials)
#         test_indicators = TestIndicator.objects.all()
#         ret = []
#         for material in page_materials:
#             material_data = {'material_id': material.id,
#                              'material_no': material.material_no,
#                              'material_name': material.material_name,
#                              'test_data_detail': {}
#                              }
#             for test_indicator in test_indicators:
#                 if MaterialDataPointIndicator.objects.filter(
#                         material_test_data_point__material_test_method__test_method__test_type__test_indicator=
#                         test_indicator,
#                         material_test_data_point__material_test_method__material=material).exists():
#                     material_data['test_data_detail'][test_indicator.id] = {'test_type_name': test_indicator.name,
#                                                                             'indicator_exists': True}
#                 else:
#                     material_data['test_data_detail'][test_indicator.id] = {'test_type_name': test_indicator.name,
#                                                                             'indicator_exists': False}
#             ret.append(material_data)
#         return self.get_paginated_response(ret)


# class MatIndicatorsTabView(APIView):
#     """根据原材料编号和试验方法获取判断标准表格数据， 参数：material_no=胶料编号&test_method_id=试验方法id"""
#     def get(self, request):
#         material_no = self.request.query_params.get('material_no', 'BS1485')
#         test_method_id = self.request.query_params.get('test_method_id', 7)
#         if not all([material_no, test_method_id]):
#             raise ValidationError('参数不足')
#         test_data = MaterialTestMethodDataPoint.objects.filter(
#             material_test_method__material__material_no=material_no,
#             material_test_method__test_method_id=test_method_id)
#         s = MaterialDataPointListSerializer(instance=test_data, many=True)
#         ret = {}
#         for item in s.data:
#             mat_indicators = item['mat_indicators']
#             for mat_indicator in mat_indicators:
#                 if item['name'] not in ret:
#                     ret[mat_indicator['result']] = {"level": mat_indicator['level'],
#                                                     "result": mat_indicator['result'],
#                                                     item['name']: {
#                                                          'id': mat_indicator['id'],
#                                                          "upper_limit": mat_indicator['upper_limit'],
#                                                          "lower_limit": mat_indicator['lower_limit']}
#                                                     }
#                 else:
#                     ret[mat_indicator['result']][item['name']] = {
#                         'id': mat_indicator['id'],
#                         "upper_limit": mat_indicator['upper_limit'],
#                         "lower_limit": mat_indicator['lower_limit']
#                         }
#         return Response(ret.values())


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
    queryset = MaterialTestOrder.objects.filter(delete_flag=False)
    serializer_class = MaterialTestOrderSerializer
    filter_backends = (DjangoFilterBackend,)
    permission_classes = (IsAuthenticated,)
    filter_class = MaterialTestOrderFilter

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


class MaterialDealResultViewSet(CommonDeleteMixin, ModelViewSet):
    """胶料处理结果
    list: 查询胶料处理结果列表
    post: 创建胶料处理结果
    put: 创建胶料处理结果
    """
    queryset = MaterialDealResult.objects.filter(delete_flag=False)
    serializer_class = DealResultDealSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_class = MaterialDealResulFilter


class MaterialDealStatusListView(APIView):
    """胶料状态列表"""

    def get(self, request):
        filter_set = MaterialDealResult.objects.filter(delete_flag=False).values("status").annotate()
        return Response(filter_set)


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
        pfb_queryset = MaterialDealResult.objects.filter(**filter_dict)
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
        if instance.delete_flag:
            instance.delete_flag = False
        else:
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