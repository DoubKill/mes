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
        m_list = results.pop('mtr_list', [])  # 这里不用序列化的方法了 因为要加合格区间 在原本的序列化里加了 会影响web页面的 所以重写一个
        trains = []
        for i in m_list:
            if i != 'table_head':
                trains.append({'train': i, 'content': m_list[i]})
        indicators = []
        for indicator_name, points in m_list['table_head'].items():
            point_head = []
            for point in points:
                indicator = MaterialDataPointIndicator.objects.filter(
                    data_point__name=point,
                    material_test_method__material__material_name=results['product_no'],
                    level=1).first()
                if indicator:
                    point_head.append(
                        {"point": point,
                         "upper_limit": indicator.upper_limit,
                         "lower_limit": indicator.lower_limit}
                    )
                else:
                    point_head.append(
                        {"point": point,
                         "upper_limit": None,
                         "lower_limit": None}
                    )
            indicators.append({'point': indicator_name, 'point_head': point_head})
        mtr_list = {'trains': trains, 'table_head': indicators}
        results['mtr_list'] = mtr_list
        results['range_showed'] = QualifiedRangeDisplay.objects.first().is_showed
        results = json.dumps(results, cls=DecimalEncoder)
        return results
