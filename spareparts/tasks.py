# 将excel数据写入mysql
import os

import xlrd
from django.http import HttpResponse
from xlrd import xldate_as_datetime

from mes import settings


def wrdb(filename):
    # 打开上传 excel 表格
    readboot = xlrd.open_workbook(settings.UPLOAD_ROOT + "/" + filename)
    sheet = readboot.sheet_by_index(0)
    # 获取excel的行和列
    nrows = sheet.nrows
    ncols = sheet.ncols
    print(ncols, nrows)
    sql = "insert into working_hours (jobnum,name,workingtime,category,project,date,createtime) VALUES"
    for i in range(1, nrows):
        row = sheet.row_values(i)
        jobnum = row[4]
        name = row[5]
        workingtime = row[2]
        category = row[8]
        project = row[1]
        date = xldate_as_datetime(row[3], 0).strftime('%Y/%m/%d')


#         values = "('%s','%s','%s','%s','%s','%s','%s')"%(jobnum,name,workingtime,category,project,date,datetime.datetime.now())
#         sql = sql + values +","
# 　   # 为了提高运行效率，一次性把数据 insert 进数据库  　
#     sql = sql[:-1]
#     # 写入数据库
#     # DataConnection 是自定义的公共模块，用的是第三方库，用来操作数据库。没有用 ORM ，后续有 group by 等复杂 sql 不好操作。
#     DataConnection.MysqlConnection().insert('work',sql)


def upload(request):
    # 根name取 file 的值
    file = request.FILES.get('file')
    print('uplaod:%s' % file)
    # 创建upload文件夹
    if not os.path.exists(settings.UPLOAD_ROOT):
        os.makedirs(settings.UPLOAD_ROOT)
    try:
        if file is None:
            return HttpResponse('请选择要上传的文件')
        # 循环二进制写入
        with open(settings.UPLOAD_ROOT + "/" + file.name, 'wb') as f:
            for i in file.readlines():
                f.write(i)

        # 写入 mysql
        wrdb(file.name)
    except Exception as e:
        return HttpResponse(e)

    return HttpResponse('导入成功')
