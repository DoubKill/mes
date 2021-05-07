import json

from mes.common_code import DecimalEncoder
from quality.models import MaterialDealResult
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
        indicator = []

        for j in m_list['table_head']:
            point_head = []
            for m in m_list['table_head'][j]:
                s = m.rsplit('[', 1)
                if len(s) > 1:
                    limit = s[1].split('-')
                    point_head.append({"point": s[0], "upper_limit": limit[1], "lower_limit": limit[0]})
                else:
                    point_head.append({"point": s[0], "upper_limit": None, "lower_limit": None})
            indicator.append({'point': j, 'point_head': point_head})
        mtr_list = {'trains': trains, 'table_head': indicator}
        results['mtr_list'] = mtr_list
        results = json.dumps(results, cls=DecimalEncoder)
        return results
