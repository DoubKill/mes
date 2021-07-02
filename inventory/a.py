# import datetime
#
#
# a = '2012-10-12 12:21:26'
#
# ss = datetime.datetime.strptime(a,'%Y-%m-%d %H:%M:%S')
# # ss = a.strftime('%Y-%m-%d %H:%M:%S')
#
# print(ss)

# import datetime
#
# s = {'name': None, 'product_no': '1001', 'provider': '某某化工', 'lot_no': '0001', 'sulfur_status': 1, 'depot_name': '1#', 'depot_site_name': '1-1'}
#
# enter_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
# s.update({"name":enter_time})
#
# print(s)

import json
import pandas as pd


# lst = [
#        {'name': '硫磺1001', 'product_no': '1001', 'provider': '某某化工', 'lot_no': '0001', 'num': 1},
#        {'name': '硫磺1002', 'product_no': '1002', 'provider': '某某化工', 'lot_no': '0002', 'num': 1},
#        {'name': '硫磺1001', 'product_no': '1001', 'provider': '某某化工', 'lot_no': '0001', 'num': 1}
# ]
#
#
# data = json.loads(pd.DataFrame(lst).groupby('product_no').sum().reset_index().to_json(orient='records'))
#
#
# print(data)

lst =         [{'name': '硫磺1001', 'product_no': '1001', 'provider': '某某化工', 'lot_no': '0001'},
         {'name': '硫磺1002', 'product_no': '1002', 'provider': '某某化工', 'lot_no': '0002'},
          {'name': '硫磺1001', 'product_no': '1001', 'provider': '某某化工', 'lot_no': '0001'}]

c = {i['name']: {} for i in lst}

for i in lst:

       if not c[i['name']]:
              i.update({"num": 1})
              c[i['name']].update(i)
       else:
              c[i['name']]['num'] += 1
print(c.values())

"""
dict_values([{'name': '硫磺1001', 'product_no': '1001', 'provider': '某某化工', 'lot_no': '0001', 'num': 2}, 
{'name': '硫磺1002', 'product_no': '1002', 'provider': '某某化工', 'lot_no': '0002', 'num': 1}])
"""

"""
   api/v1/inventory/sulfur-depot/",     库区
   api/v1/inventory/sulfur-depot-site/",     库位
   api/v1/inventory/sulfur-data/",      出入库管理
   api/v1/inventory/sulfur-resume/",   
   api/v1/inventory/depot-sulfur-info/",
   api/v1/inventory/sulfur-resume/"

"""