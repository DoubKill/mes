from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from production.models import TrainsFeedbacks, PalletFeedbacks, EquipStatus, PlanStatus, ExpendMaterial, OperationLog, \
    QualityControl
from production.serializers import QualityControlSerializer, OperationLogSerializer, ExpendMaterialSerializer, \
    PlanStatusSerializer, EquipStatusSerializer, PalletFeedbacksSerializer, TrainsFeedbacksSerializer


class TrainsFeedbacksViewSet(mixins.CreateModelMixin,
                             mixins.RetrieveModelMixin,
                             mixins.ListModelMixin,
                             GenericViewSet):
    queryset = TrainsFeedbacks.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = TrainsFeedbacksSerializer
    filter_backends = (DjangoFilterBackend,)


class PalletFeedbacksViewSet(mixins.CreateModelMixin,
                             mixins.RetrieveModelMixin,
                             mixins.ListModelMixin,
                             GenericViewSet):
    queryset = PalletFeedbacks.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = PalletFeedbacksSerializer


class EquipStatusViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.ListModelMixin,
                         GenericViewSet):
    queryset = EquipStatus.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = EquipStatusSerializer


class PlanStatusViewSet(mixins.CreateModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        GenericViewSet):
    queryset = PlanStatus.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = PlanStatusSerializer


class ExpendMaterialViewSet(mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.ListModelMixin,
                            GenericViewSet):
    queryset = ExpendMaterial.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = ExpendMaterialSerializer


class OperationLogViewSet(mixins.CreateModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.ListModelMixin,
                          GenericViewSet):
    queryset = OperationLog.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = OperationLogSerializer


class QualityControlViewSet(mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.ListModelMixin,
                            GenericViewSet):
    queryset = QualityControl.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = QualityControlSerializer
