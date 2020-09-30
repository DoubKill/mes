# -*- coding: UTF-8 -*-
"""
auther: 
datetime: 2020/7/27
name: 
"""

COMMON_READ_ONLY_FIELDS = ('created_date', 'last_updated_date', 'delete_date',
                           'delete_flag', 'created_user', 'last_updated_user',
                           'delete_user')

PROJECT_API_TREE = {
    "basic": (),
    "system": (),
    "repice": (),
    "plan": (),
    "production": ('trains-feedbacks', 'pallet-feedbacks'),
}

SYNC_SYSTEM_NAME = "上辅机群控"

EQUIP_LIST = ['Z01', 'Z02', 'Z03', 'Z04', 'Z05', 'Z06', 'Z07', 'Z08', 'Z09', 'Z10', 'Z11', 'Z12', 'Z13', 'Z14', 'Z15']