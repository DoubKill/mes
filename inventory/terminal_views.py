from django.db.models import Count, Max, Q
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.mixins import CreateModelMixin, ListModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from inventory.filters import DispatchLogFilter
from inventory.models import DispatchPlan, DispatchLog
from inventory.serializers import DispatchPlanSerializer, DispatchLogCreateSerializer, DispatchLogSerializer, \
    TerminalDispatchPlanUpdateSerializer
from mes.derorators import api_recorder


@method_decorator([api_recorder], name="dispatch")
class TerminalDispatchViewSet(ListModelMixin,
                              UpdateModelMixin,
                              GenericViewSet):
    """
    list:
        发货单列表
    create:
        完成发货
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
