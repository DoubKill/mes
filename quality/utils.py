import requests
import xlrd
import xlwt
from django.http import HttpResponse
from io import BytesIO

from rest_framework import serializers

from mes.conf import WMS_URL
from quality.models import MaterialTestOrder, MaterialDataPointIndicator, MaterialDealResult, MaterialTestMethod
from production.models import PalletFeedbacks


# def print_mdr(filename: str, queryset):
#     """不合格品打印功能"""
#     response = HttpResponse(content_type='application/vnd.ms-excel')
#     # response['Content-Disposition'] = 'attachment;filename= ' + filename.encode('gbk').decode('ISO-8859-1') + '.xlsx'
#     if queryset:
#         # 创建工作簿
#         style = xlwt.XFStyle()
#         style.alignment.wrap = 1
#         ws = xlwt.Workbook(encoding='utf-8')
#
#         # 添加第一页数据表
#         w = ws.add_sheet('sheet1')  # 新建sheet（sheet的名称为"sheet1"）
#         for j in [1, 4, 5, 7]:
#             first_col = w.col(j)
#             first_col.width = 256 * 20
#         # 写入表头
#         w.write(0, 0, u'NO')
#         w.write(0, 1, u'生产日期')
#         w.write(0, 2, u'机台')
#         w.write(0, 3, u'班次')
#         w.write(0, 4, u'胶料编码')
#         w.write(0, 5, u'lot追踪号')
#         w.write(0, 6, u'等级')
#         w.write(0, 7, u'不合格原因')
#         w.write(0, 8, u'状态')
#         w.write(0, 9, u'是否出库')
#         w.write(0, 10, u'出库时间')
#         w.write(0, 11, u'处理意见')
#         w.write(0, 12, u'检测结果')
#         w.write(0, 13, u'处理人')
#         w.write(0, 14, u'确认人')
#         # 写入数据
#         excel_row = 1
#         for obj in queryset:
#             drds = DealResultDealSerializer()
#             product_info = drds.get_product_info(obj)
#             # 写入每一行对应的数据
#             w.write(excel_row, 0, excel_row)
#             w.write(excel_row, 1, obj.production_factory_date.strftime("%Y-%m-%d %H:%M:%S"))
#             w.write(excel_row, 2, product_info.get('production_equip_no', None))
#             w.write(excel_row, 3, product_info.get('production_class', None))
#             w.write(excel_row, 4, product_info.get('product_no', None))
#             w.write(excel_row, 5, obj.lot_no)
#             w.write(excel_row, 6, obj.level)
#             w.write(excel_row, 7, obj.reason)
#             w.write(excel_row, 8, obj.status)
#             w.write(excel_row, 9, 'Y' if obj.be_warehouse_out else 'N')
#             w.write(excel_row, 10,
#                     obj.warehouse_out_time.strftime("%Y-%m-%d %H:%M:%S") if obj.warehouse_out_time else None)
#             w.write(excel_row, 11, obj.deal_suggestion)
#             w.write(excel_row, 12, obj.deal_result)
#             w.write(excel_row, 13, obj.deal_user)
#             w.write(excel_row, 14, obj.confirm_user)
#             excel_row += 1
#         # 写出到IO
#         output = BytesIO()
#         ws.save(output)
#         # 重新定位到开始
#         output.seek(0)
#         response.write(output.getvalue())
#     return response


def get_cur_sheet(excel_file):
    """
    获取当前工作sheet
    @param excel_file: excel模板文件
    @return: 当前工作sheet
    """
    file_name = excel_file.name
    if not file_name.split('.')[-1] in ['xls', 'xlsx', 'xlsm']:
        raise serializers.ValidationError('文件格式错误,仅支持 xls、xlsx、xlsm文件')
    try:
        data = xlrd.open_workbook(filename=None, file_contents=excel_file.read())
        cur_sheet = data.sheets()[0]
    except Exception:
        raise serializers.ValidationError('打开文件错误')
    return cur_sheet


def get_sheet_data(sheet, start_row=1):
    """
    获取excel文件所有数据
    @param start_row: 开始取数据的行数
    @param sheet:当前工作sheet
    @return: sheet列表数据
    """
    rows_num = sheet.nrows  # sheet行数
    if rows_num <= start_row:
        return []
    ret = [None] * (rows_num - start_row)
    for i in range(start_row, rows_num):
        ret[i - start_row] = sheet.row_values(i)
    return ret


def export_mto():
    """快检数据导入模板"""
    response = HttpResponse(content_type='application/vnd.ms-excel')
    filename = '快检数据导入模板'
    response['Content-Disposition'] = 'attachment;filename= ' + filename.encode('gbk').decode('ISO-8859-1') + '.xls'
    # 创建工作簿
    style = xlwt.XFStyle()
    style.alignment.wrap = 1
    ws = xlwt.Workbook(encoding='utf-8')

    # 添加第一页数据表
    w = ws.add_sheet('快检数据导入模板')  # 新建sheet（sheet的名称为"sheet1"）
    for j in [0, 1, 2, 3, 4, 5, 9]:
        first_col = w.col(j)
        first_col.width = 256 * 20
    # 写入表头
    w.write(0, 0, u'检测数据录入 说明:每次只能导入同批次生产数据！！！！')
    w.write(1, 0, u'胶料规格编码')
    w.write(1, 1, u'判定日期(2020/01/01)')
    w.write(1, 2, u'密炼日期(2020/01/01)')
    w.write(1, 3, u'班次（早、中、夜）')
    w.write(1, 4, u'机台（Z01-Z15）')
    w.write(1, 5, u'检测班组(A,B,C）')
    w.write(1, 6, u'车次')
    w.write(1, 7, u'MH')
    w.write(1, 8, u'ML')
    w.write(1, 9, u'TC10')
    w.write(1, 10, u'TC50')
    w.write(1, 11, u'TC90')
    w.write(1, 12, u'比重值')
    w.write(1, 13, u'ML(1+4)')
    w.write(1, 14, u'硬度值')
    w.write(1, 15, u'M300')
    w.write(1, 16, u'扯断强度')
    w.write(1, 17, u'伸长率%')
    w.write(1, 18, u'焦烧')
    w.write(1, 19, u'钢拔')
    w.write(1, 20, u'是否合格（Y：合格 N：不合格）非必填')

    output = BytesIO()
    ws.save(output)
    # 重新定位到开始
    output.seek(0)
    response.write(output.getvalue())
    return response


def update_wms_quality_result(data_list):
    """
    更新检测结果至WMS
    @param data_list:
    @return:
    """
    url = WMS_URL + '/MESApi/UpdateTestingResult'
    data = {"TestingType": 2, "SpotCheckDetailList": data_list}
    headers = {"Content-Type": "application/json ;charset=utf-8"}
    try:
        ret = requests.post(url, json=data, headers=headers, timeout=10)
    except Exception as e:
        pass


def gen_pallet_test_result(lot_nos):
    """根据条码检测信息，生成快检卡片信息"""
    lot_nos = set(lot_nos)
    for lot_no in lot_nos:
        pfb_obj = PalletFeedbacks.objects.filter(lot_no=lot_no).first()
        if not pfb_obj:
            continue
        test_orders = MaterialTestOrder.objects.filter(lot_no=lot_no)
        passed_order_count = 0
        unqualified_order_count = 0
        pass_suggestion = "放行"

        test_product_flat = False  # 是否为试验料标记
        pn = pfb_obj.product_no.split('-')[2]
        if pn.startswith('T'):
            test_orders.update(is_experiment=True)
            # 判断是否所有项目都不判级
            if not MaterialTestMethod.objects.filter(delete_flag=False,
                                                     is_judged=True,
                                                     material__material_no=pfb_obj.product_no).exists():
                test_product_flat = True

        continue_flag = False
        data_points = set(MaterialDataPointIndicator.objects.filter(
            material_test_method__material__material_no=pfb_obj.product_no,
            material_test_method__is_judged=True,
            delete_flag=False).values_list('data_point__name', flat=True))

        for test_order in test_orders:
            test_results = test_order.order_results.filter()
            if test_product_flat:
                if test_results.filter(level=2).exists():
                    test_order.is_qualified = False
                else:
                    test_order.is_qualified = True
            else:
                # 判断改车次检测是否合格
                if test_results.filter(level=2, is_judged=True).exists():
                    test_order.is_qualified = False
                    unqualified_order_count += 1
                else:
                    test_order.is_qualified = True
                # 判断改车次检测是否通过PASS
                test_order_passed_count = test_results.filter(is_passed=True, is_judged=True).count()
                test_order_unqualified_count = test_results.filter(level=2, is_judged=True).count()
                if test_order_passed_count == test_order_unqualified_count == 1:
                    pass_suggestion = list(test_results.filter(
                        is_passed=True, is_judged=True).values_list('pass_suggestion', flat=True))[0]
                    test_order.is_passed = True
                    passed_order_count += 1
                else:
                    test_order.is_passed = False
                # 判定所有必检测数据点都是否已检测完成
                common_data_points = data_points & set(test_results.values_list('data_point_name', flat=True))
                if not len(data_points) == len(common_data_points):
                    continue_flag = True
            test_order.save()

        if test_product_flat:
            level = 1
            test_result = '试验'
            deal_suggestion = '试验'
        else:
            # 1、不合格车数以及pass章车数相等且大于0，则判定为PASS章
            if 0 < passed_order_count == unqualified_order_count > 0:
                level = 1
                test_result = 'PASS'
                deal_suggestion = pass_suggestion
            # 2、所有车次都合格
            elif unqualified_order_count == 0:
                level = 1
                test_result = '一等品'
                deal_suggestion = '合格'
            # 3、不合格
            else:
                level = 3
                test_result = '三等品'
                deal_suggestion = '不合格'
        mdr = MaterialDealResult.objects.filter(lot_no=lot_no).first()
        if mdr:
            mdr.level = level
            mdr.test_result = test_result
            mdr.level = level
            mdr.deal_result = '一等品' if level == 1 else '三等品'
            mdr.deal_suggestion = deal_suggestion
            mdr.update_store_test_flag = 4
            mdr.deal_suggestion = deal_suggestion
            mdr.deal_suggestion = deal_suggestion
            mdr.save()
        else:
            if continue_flag:
                continue
            # 取检测车次
            test_trains_set = set(test_orders.values_list('actual_trains', flat=True))
            # 取托盘反馈生产车次
            actual_trains_set = {i for i in range(pfb_obj.begin_trains, pfb_obj.end_trains + 1)}

            common_trains_set = actual_trains_set & test_trains_set
            # 判断托盘反馈车次都存在检测数据
            if not len(actual_trains_set) == len(common_trains_set):
                continue

            deal_result_dict = {
                'level': level,
                'test_result': test_result,
                'reason': 'reason',
                'status': '待处理',
                'deal_result': '一等品' if level == 1 else '三等品',
                'production_factory_date': pfb_obj.end_time,
                'deal_suggestion': deal_suggestion,
                'product_no': pfb_obj.product_no,
                'classes': pfb_obj.classes,
                'equip_no': pfb_obj.equip_no,
                'factory_date': pfb_obj.factory_date,
                'begin_trains': pfb_obj.begin_trains,
                'end_trains': pfb_obj.end_trains,
                'update_store_test_flag': 4
            }
            MaterialDealResult.objects.update_or_create(defaults=deal_result_dict, **{'lot_no': lot_no})