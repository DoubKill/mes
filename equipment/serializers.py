from basics.models import Equip
from mes.base_serializer import BaseModelSerializer

class EquipRealtimeSerializer(BaseModelSerializer):

    class Meta:
        model = Equip
        fields = "__all__"