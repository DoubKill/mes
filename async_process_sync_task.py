# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/8/25
name: 
"""
import functools
import json
import os
import socket
import time

import django
import logging

import requests
from django.db.models import Exists

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()


from system.models import SystemConfig, ChildSystemInfo, AsyncUpdateContent


logger = logging.getLogger("async_log")


def one_instance(func):
    '''
    如果已经有实例在跑则退出
    '''
    @functools.wraps(func)
    def f(*args,**kwargs):
        try:
        # 全局属性，否则变量会在方法退出后被销毁
            global s
            s = socket.socket()
            host = socket.gethostname()
            s.bind((host, 60124))
        except:
            print('already has an instance, this script will not be excuted')
            return
        return func(*args,**kwargs)
    return f


class SystemSync(object):


    # 设置单例模式
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_inst'):
            cls._inst = super(SystemSync, cls).__new__(cls, *args, **kwargs)
        return cls._inst

    def __init__(self):
        self.sync_data_list = []

    # 获取当前系统状态
    @property
    def if_system_online(cls):
        config_value = SystemConfig.objects.filter(config_name="system_name").first().config_value
        child_system = ChildSystemInfo.objects.filter(system_name=config_value).first()
        if child_system:
            cls.system_name = config_value
            # 必须为联网状态切改状态在当前不可更改
            if child_system.status == "联网" and child_system.status_lock:
                return True
            return False
        return False

    # 进行同步
    def sync(self):
        if self.if_system_online:

            sync_set = AsyncUpdateContent.objects.filter(Exists(ChildSystemInfo.objects.filter(system_name=)), recv_flag=False)
            for instance in sync_set:
                id = instance.id
                # 若dst_address是存入全量接口url 改参数冗余暂时不处理
                model_name = instance.src_table_name
                body_data = instance.content
                address = instance.dst_address
                method = instance.method
                headers = {
                    "Content-Type": "application/json; charset=UTF-8",
                    "TAG": True
                }
                try:
                    ret = requests.request(method, address, json=json.loads(body_data), headers=headers)
                except Exception as e:
                    logger.error(f"{address}|网络异常，详情：{e}")
                    break
                if ret.status_code < 300:
                    self.sync_feedback(id)
                else:
                    logger.error(f"{address}|同步失败，详情：{ret.text}")
        logger.warning("系统未联网，同步未执行")

    # 同步成功修改异步更新表状态
    def sync_feedback(self, id):
        try:
            instance = AsyncUpdateContent.objects.get(id=id)
            instance.recv_flag = True
            instance.save()
        except Exception as e:
            logger.error(f"同步反馈结果写入失败，详情：{e}")


@one_instance
def run():
    while True:
        runner = SystemSync()
        runner.sync()
        time.sleep(3)

if __name__ == '__main__':
    run()