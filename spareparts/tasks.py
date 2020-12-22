# 将excel数据写入mysql
import os

import xlrd
import xlwt
from django.http import HttpResponse
from io import BytesIO

from rest_framework.exceptions import ValidationError
from xlrd import xldate_as_datetime

from basics.models import GlobalCode, GlobalCodeType
from inventory.models import WarehouseInfo
from mes import settings
from spareparts.models import SpareType, Spare, SpareLocation, SpareLocationBinding, SpareInventory


def spare_wrdb(filename, upload_root):
    # 打开上传 excel 表格
    readboot = xlrd.open_workbook(upload_root + "/" + filename)
    sheet = readboot.sheet_by_index(0)
    # 获取excel的行和列
    nrows = sheet.nrows  # 行
    ncols = sheet.ncols  # 列
    for i in range(1, nrows):
        row = sheet.row_values(i)
        st_obj = SpareType.objects.filter(name=row[1]).first()
        if not st_obj:
            st_obj = SpareType.objects.create(no=row[1], name=row[1])
        s_obj = Spare.objects.filter(no=row[2]).first()
        if not s_obj:
            Spare.objects.create(no=row[2], name=row[3], type=st_obj, unit=row[7], upper=row[6], lower=row[5],
                                 cost=row[4])


def spare_inventory_wrdb(filename, upload_root):
    # 打开上传 excel 表格
    readboot = xlrd.open_workbook(upload_root + "/" + filename)
    sheet = readboot.sheet_by_index(0)
    # 获取excel的行和列
    nrows = sheet.nrows  # 行
    ncols = sheet.ncols  # 列
    for i in range(1, nrows):
        row = sheet.row_values(i)
        # print(row[1])  # 物料类型
        # print(row[2])  # 物料编码
        # print(row[3])  # 物料名称
        # print(row[4])  # 库存位
        # print(row[5])  # 库存位类型
        # print(row[6])  # 数量
        # print(row[7])  # 单价
        # print(row[8])  # 总价
        gc_obj = GlobalCode.objects.filter(global_no=row[5]).first()
        if not gc_obj:
            gct_obj = GlobalCodeType.objects.filter(type_name='备品备件类型').first()
            gc_obj = GlobalCode.objects.create(global_type=gct_obj, global_no=row[5], global_name=row[5])

        sl_obj = SpareLocation.objects.filter(name=row[4]).first()
        if not sl_obj:
            sl_obj = SpareLocation.objects.create(no=row[4], name=row[4], type=gc_obj)

        st_obj = SpareType.objects.filter(name=row[1]).first()
        if not st_obj:
            st_obj = SpareType.objects.create(no=row[1], name=row[1])

        s_obj = Spare.objects.filter(no=row[2]).first()
        if not s_obj:
            raise ValidationError(f'请先导入{row[2]}物料')

        slb_obj = SpareLocationBinding.objects.filter(location=sl_obj, spare=s_obj).first()
        if not slb_obj:
            slb_obj = SpareLocationBinding.objects.create(location=sl_obj, spare=s_obj)
        whi_obj = WarehouseInfo.objects.filter(name='备品备件仓库').first()
        SpareInventory.objects.create(spare=s_obj, qty=row[6], unit=s_obj.unit, location=sl_obj, total_count=row[8],
                                      warehouse_info=whi_obj)


def spare_upload(request, type):
    # 根name取 file 的值
    file = request.FILES.get('file')
    # 创建upload文件夹
    spareparts_root = os.path.join(settings.BASE_DIR, 'spareparts')
    upload_root = os.path.join(spareparts_root, 'upload')

    if not os.path.exists(upload_root):
        os.makedirs(upload_root)
    # try:
    if file is None:
        return HttpResponse('请选择要上传的文件')
    # 循环二进制写入
    with open(upload_root + "/" + file.name, 'wb') as f:
        for i in file.readlines():
            f.write(i)

    # # 写入 mysql
    if type == 1:
        spare_wrdb(file.name, upload_root)
    elif type == 2:
        spare_inventory_wrdb(file.name, upload_root)

    # except Exception as e:
    #     print(e)
    #     return HttpResponse(e)


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


def spare_inventory_template():
    """备品备件导入模板"""
    response = HttpResponse(content_type='application/vnd.ms-excel')
    filename = '备品备件入库信息'
    response['Content-Disposition'] = 'attachment;filename= ' + filename.encode('gbk').decode('ISO-8859-1') + '.xls'
    # 创建工作簿
    style = xlwt.XFStyle()
    style.alignment.wrap = 1
    ws = xlwt.Workbook(encoding='utf-8')

    # 添加第一页数据表
    w = ws.add_sheet('备品备件入库信息')  # 新建sheet（sheet的名称为"sheet1"）
    # for j in [1, 4, 5, 7]:
    #     first_col = w.col(j)
    #     first_col.width = 256 * 20
    # 写入表头
    w.write(0, 0, u'No')
    w.write(0, 1, u'物料类型')
    w.write(0, 2, u'物料编码')
    w.write(0, 3, u'物料名称')
    w.write(0, 4, u'库存位')
    w.write(0, 5, u'库存位类型')
    w.write(0, 6, u'数量')
    w.write(0, 7, u'单价（元）')
    w.write(0, 8, u'总价')

    output = BytesIO()
    ws.save(output)
    # 重新定位到开始
    output.seek(0)
    response.write(output.getvalue())
    return response
