import uuid
import time


i = 0


class UUidTools(object):
    @staticmethod
    def uuid1_hex():
        global i
        i += 1
        return uuid.uuid1(i)

