import logging

import requests

from inventory.conf import wms_ip, wms_port

logger = logging.getLogger("send_log")

def send():
    url = f"http://{wms_ip}:{wms_port}/MESApi/UpdateTestingResult"
    body = {
        "TestingType": 1,  #  1全检  2抽检
        "SpotCheckDetailList": [{
            "BatchNo": "string",
            "CheckResult": 1     # 1合格， 2不合格
        }],
        "AllCheckDetailList": [{
            "TrackingNumber": "string",
            "CheckResult": 1
        }]
    }
    try:
        ret = requests.post(url, data=body)
        data = ret.json()
        if data.get("state"):
            # 快检结果是否已发送标记为发送
            pass
        pass
    except Exception as e:
        logger.error(f"原材料快检结果发送{e}")

if __name__ == '__main__':
    pass