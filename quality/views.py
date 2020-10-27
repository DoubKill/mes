from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from mes.derorators import api_recorder
from quality.filters import TestMethodFilter, DataPointFilter, \
    MaterialTestMethodFilter, MaterialDataPointIndicatorFilter, MaterialTestOrderFilter
from quality.models import TestIndicator, MaterialDataPointIndicator, TestMethod, MaterialTestOrder, \
    MaterialTestMethod, TestType, DataPoint
from quality.serializers import MaterialDataPointIndicatorSerializer, \
    MaterialTestOrderSerializer, MaterialTestOrderListSerializer, \
    MaterialTestMethodSerializer, TestMethodSerializer, TestTypeSerializer, DataPointSerializer
from recipe.models import Material, ProductBatching


@method_decorator([api_recorder], name="dispatch")
class TestIndicatorListView(ListAPIView):
    """试验指标列表"""
    queryset = TestIndicator.objects.all()

    def list(self, request, *args, **kwargs):
        data = TestIndicator.objects.values('id', 'name')
        return Response(data)


@method_decorator([api_recorder], name="dispatch")
class TestTypeViewSet(ModelViewSet):
    """试验类型管理"""
    queryset = TestType.objects.filter(delete_flag=False)
    serializer_class = TestTypeSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('test_indicator', )

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
    permission_classes = (IsAuthenticated, )
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