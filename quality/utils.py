import xlwt
from django.http import HttpResponse
from io import BytesIO

from quality.serializers import DealResultDealSerializer


def print_mdr(filename: str, queryset):
    """不合格品打印功能"""
    response = HttpResponse(content_type='application/vnd.ms-excel')
    # response['Content-Disposition'] = 'attachment;filename= ' + filename.encode('gbk').decode('ISO-8859-1') + '.xlsx'
    if queryset:
        # 创建工作簿
        style = xlwt.XFStyle()
        style.alignment.wrap = 1
        ws = xlwt.Workbook(encoding='utf-8')

        # 添加第一页数据表
        w = ws.add_sheet('sheet1')  # 新建sheet（sheet的名称为"sheet1"）
        for j in [1, 4, 5, 7]:
            first_col = w.col(j)
            first_col.width = 256 * 20
        # 写入表头
        w.write(0, 0, u'NO')
        w.write(0, 1, u'生产日期')
        w.write(0, 2, u'机台')
        w.write(0, 3, u'班次')
        w.write(0, 4, u'胶料编码')
        w.write(0, 5, u'lot追踪号')
        w.write(0, 6, u'等级')
        w.write(0, 7, u'不合格原因')
        w.write(0, 8, u'状态')
        w.write(0, 9, u'是否出库')
        w.write(0, 10, u'出库时间')
        w.write(0, 11, u'处理意见')
        w.write(0, 12, u'检测结果')
        w.write(0, 13, u'处理人')
        w.write(0, 14, u'确认人')
        # 写入数据
        excel_row = 1
        for obj in queryset:
            drds = DealResultDealSerializer()
            product_info = drds.get_product_info(obj)
            # 写入每一行对应的数据
            w.write(excel_row, 0, excel_row)
            w.write(excel_row, 1, obj.production_factory_date.strftime("%Y-%m-%d %H:%M:%S"))
            w.write(excel_row, 2, product_info.get('production_equip_no', None))
            w.write(excel_row, 3, product_info.get('production_class', None))
            w.write(excel_row, 4, product_info.get('product_no', None))
            w.write(excel_row, 5, obj.lot_no)
            w.write(excel_row, 6, obj.level)
            w.write(excel_row, 7, obj.reason)
            w.write(excel_row, 8, obj.status)
            w.write(excel_row, 9, 'Y' if obj.be_warehouse_out else 'N')
            w.write(excel_row, 10,
                    obj.warehouse_out_time.strftime("%Y-%m-%d %H:%M:%S") if obj.warehouse_out_time else None)
            w.write(excel_row, 11, obj.deal_suggestion)
            w.write(excel_row, 12, obj.deal_result)
            w.write(excel_row, 13, obj.deal_user)
            w.write(excel_row, 14, obj.confirm_user)
            excel_row += 1
        # 写出到IO
        output = BytesIO()
        ws.save(output)
        # 重新定位到开始
        output.seek(0)
        response.write(output.getvalue())
    return response
