import json

from mes.common_code import DecimalEncoder
from quality.models import MaterialDealResult, MaterialDataPointIndicator, QualifiedRangeDisplay
from quality.serializers import MaterialDealResultListSerializer
import logging

logger = logging.getLogger('send_log')


def receive_deal_result(lot_no):
    """将快检信息综合管理接口(就是打印的卡片信息)封装成一个类，需要的时候就调用一下"""
    mdr_obj = MaterialDealResult.objects.filter(lot_no=lot_no).exclude(status='复测').last()
    if mdr_obj:
        serializers = MaterialDealResultListSerializer(instance=mdr_obj)
        results = serializers.data
        results = json.dumps(results, cls=DecimalEncoder)
        return results
