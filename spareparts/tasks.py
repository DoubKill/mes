# 将excel数据写入mysql
import os

import xlrd
import xlwt
from django.http import HttpResponse
from io import BytesIO

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


def spare_template():
    """备品备件基本信息导入模板"""
    response = HttpResponse(content_type='application/vnd.ms-excel')
    filename = '备品备件基本信息'
    response['Content-Disposition'] = 'attachment;filename= ' + filename.encode('gbk').decode('ISO-8859-1') + '.xls'
    # 创建工作簿
    style = xlwt.XFStyle()
    style.alignment.wrap = 1
    ws = xlwt.Workbook(encoding='utf-8')

    # 添加第一页数据表
    w = ws.add_sheet('备品备件基本信息')  # 新建sheet（sheet的名称为"sheet1"）
    # for j in [1, 4, 5, 7]:
    #     first_col = w.col(j)
    #     first_col.width = 256 * 20
    # 写入表头
    w.write(0, 0, u'No')
    w.write(0, 1, u'物料类型')
    w.write(0, 2, u'物料编码')
    w.write(0, 3, u'物料名称')
    w.write(0, 4, u'单价（元）')
    w.write(0, 5, u'安全库存下限')
    w.write(0, 6, u'安全库存上限')
    w.write(0, 7, u'单位')
    output = BytesIO()
    ws.save(output)
    # 重新定位到开始
    output.seek(0)
    response.write(output.getvalue())
    return response
