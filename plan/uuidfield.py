import time
import uuid


class UUidTools(object):
    """随机生成唯一码 后期按照规则改动"""

    @staticmethod
    def uuid1_hex():
        return uuid.uuid1(int(time.time()))