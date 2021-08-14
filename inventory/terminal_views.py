import datetime
import json

from suds.client import Client
from django.db.models import Count, Max, Q
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.mixins import CreateModelMixin, ListModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from inventory.filters import DispatchLogFilter
from inventory.models import DispatchPlan, DispatchLog, Sulfur
from inventory.serializers import DispatchPlanSerializer, DispatchLogCreateSerializer, DispatchLogSerializer, \
    TerminalDispatchPlanUpdateSerializer, SulfurAutoPlanSerializer
from mes.derorators import api_recorder


@method_decorator([api_recorder], name="dispatch")
class TerminalDispatchViewSet(ListModelMixin,
                              UpdateModelMixin,
                              GenericViewSet):
    """
    list:
        发货单列表
    update:
        完成/关闭发货
    """
    queryset = DispatchPlan.objects.filter(status__in=(2, 4))
    serializer_class = DispatchPlanSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = None

    def get_serializer_class(self):
        if self.action == 'update':
            return TerminalDispatchPlanUpdateSerializer
        else:
            return DispatchPlanSerializer


@method_decorator([api_recorder], name="dispatch")
class TerminalDispatchLogViewSet(CreateModelMixin,
                                 ListModelMixin,
                                 GenericViewSet):
    """
    list:
        发货履历列表
    create:
        新建/撤销发货
    """
    queryset = DispatchLog.objects.filter(delete_flag=False)
    filter_backends = [DjangoFilterBackend]
    filter_class = DispatchLogFilter
    permission_classes = (IsAuthenticated,)
    pagination_class = None

    def get_queryset(self):
        if self.request.query_params.get('cancel'):  # 查看可以撤销的发货记录
            data = DispatchLog.objects.values(
                'lot_no', 'order_no').annotate(max_id=Max('id'), count=Count('id'))
            max_ids2 = [item['max_id'] for item in data]
            return self.queryset.filter(id__in=max_ids2, status=1)
        else:
            return self.queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return DispatchLogCreateSerializer
        else:
            return DispatchLogSerializer


@method_decorator([api_recorder], name='dispatch')
class SulfurAutoPlanViewSet(GenericViewSet, ListModelMixin, CreateModelMixin):
    """
    list : 出库
    post： 入库
    """
    queryset = Sulfur.objects.all()
    serializer_class = SulfurAutoPlanSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('lot_no',)

    def list(self, request, *args, **kwargs):
        if self.request.query_params.get('last'):
            queryset = self.get_queryset().filter(sulfur_status=1).last()
            serializer = self.get_serializer(queryset)
            message = None
        else:
            queryset = self.filter_queryset(self.get_queryset())
            queryset.update(sulfur_status=2)
            serializer = self.get_serializer(queryset, many=True)
            message = '出库成功'
        return Response({
            'success': True,
            'message': message,
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):

            tmh = serializer.validated_data.get('lot_no')
            if not tmh:
                raise ValidationError('请输入条码号')  # BHZ12105311651140001
            url = 'http://10.1.10.157:9091/WebService.asmx?wsdl'
            try:
                client = Client(url)
                json_data = {"tofac": "AJ1", "tmh": tmh}
                data = client.service.FindZcdtmList(json.dumps(json_data))
            except Exception:
                raise ValidationError('网络异常！')
            data = json.loads(data)
            ret = data.get('Table')[0]

            if not ret:
                raise ValidationError('未找到该条码对应物料信息！')
            depot_site = serializer.validated_data.get('depot_site')
            enter_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            state = serializer.validated_data.get('state')

            try:
                name = ret['WLMC']
                provider = ret['WLDWMC']
                ZL = ret['ZL']  # 重量
                SL = ret['SL']  # 数量
            except:
                raise ValidationError('原材料数据有误')

            if state:
                Sulfur.objects.create(name=name, product_no=name, provider=provider, lot_no=tmh, num=SL, weight=ZL,
                                      depot_site=depot_site, enter_time=enter_time, sulfur_status=1)
                return Response({
                    'success': True,
                    'message': '入库成功',
                    'data': {
                        'lot_no': tmh,
                        'weight': ZL
                        }
                })
            else:
                return Response({
                    'success': True,
                    'message': None,
                    'data': {
                        'lot_no': tmh
                    }
            })