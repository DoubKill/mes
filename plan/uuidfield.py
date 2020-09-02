import time
import uuid
import datetime

i = 0


class UUidTools(object):
    """随机生成唯一码 后期按照规则改动"""

    @staticmethod
    def uuid1_hex(equip_no):
        global i
        i += 1
        only_no = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(i).rjust(2, '0') + equip_no
        return only_no
