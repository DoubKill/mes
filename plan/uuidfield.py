import uuid
import time

i = 0


class UUidTools(object):
    """随机生成唯一码 后期按照规则改动"""

    @staticmethod
    def uuid1_hex():
        global i
        i += 1
        return uuid.uuid1(i)
