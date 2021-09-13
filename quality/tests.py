from django.test import TestCase

# Create your tests here.


stuDictList = [
    {"name": "中飞", "power": 96, "tellegent": 30},
    {"name": "哎亮", "power": 40, "tellegent": 99},
    {"name": "周瑜", "power": 79, "tellegent": 93},
    {"name": "赵云", "power": 97, "tellegent": 86},
]

def func(ele):
    return ele["name"]

new_list = sorted(stuDictList, key=lambda x: x['name'])
print("排序结果{}".format(new_list))


