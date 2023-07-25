import os
import sys
from multiprocessing.pool import ThreadPool

import django
from django.db.models import Sum, Count, Q
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from basics.models import Equip, GlobalCode
from mes.conf import JZ_EQUIP_NO
from production.models import ManualWeightOutput, SetThePrice, EmployeeAttendanceRecords, PerformanceJobLadder, IndependentPostTemplate
from production.utils import actual_clock_data
from terminal.models import JZPlan, JZReportBasic, ReportBasic, Plan


class SummaryOfWeighingOutput(object):

    def concat_user_package(self, equip_no, result, factory_date, users, work_times, user_result, qty_data, manual_data):
        dic = {'equip_no': equip_no, 'hj': 0}
        plan_model, report_basic = [JZPlan, JZReportBasic] if equip_no in JZ_EQUIP_NO else [Plan, ReportBasic]
        data = plan_model.objects.using(equip_no).filter(actno__gt=1, date_time__istartswith=factory_date).values('date_time', 'grouptime').annotate(
            count=Sum('actno'))
        for item in data:
            date = item['date_time']
            day = int(date.split('-')[2])  # 2  早班
            classes = item['grouptime']  # 早班/ 中班 / 夜班
            filter_classes = classes if equip_no not in JZ_EQUIP_NO else ('早' if classes == '早班' else ('晚' if classes == '夜班' else '中'))
            manual_count = manual_data.get(f'{equip_no}_{date}_{filter_classes}', 0)
            dic[f'{day}{classes}'] = item['count'] + manual_count
            dic['hj'] = dic.get('hj', 0) + item['count'] + manual_count
            names = users.get(f'{day}-{classes}-{equip_no}')
            if names:
                status = names.pop('status', None)
                key_dic = {}
                for name, section_list in names.items():
                    for section in section_list:
                        key = f"{name}_{day}_{classes}_{section}"
                        work_time = work_times.get(f'{day}-{classes}-{equip_no}').get(name + '_' + section, [])
                        if len(work_time) < 2:
                            continue
                        st, et = work_time[:2]
                        if f'{equip_no}-{day}-{st}-{et}' in qty_data:
                            num = qty_data[f'{equip_no}-{day}-{st}-{et}']
                        else:
                            c_num = report_basic.objects.using(equip_no).filter(starttime__gte=work_time[0], savetime__lte=work_time[1],
                                                                                grouptime=filter_classes).aggregate(num=Count('id'))['num']
                            num = manual_count + (c_num if c_num else 0)  # 是否需要去除为0的机台再取平均
                            qty_data[f'{equip_no}-{day}-{st}-{et}'] = num
                        # 车数计算：当天产量 / 12小时 * 实际工作时间 -> 修改为根据考勤时间计算
                        if f"{name}_{day}_{classes}" not in key_dic:
                            key_dic[f"{name}_{day}_{classes}"] = key
                        else:
                            key = key_dic[f"{name}_{day}_{classes}"]
                        if user_result.get(key):
                            user_result[key][equip_no] = user_result[key].get(equip_no, 0) + num
                        else:
                            user_result[key] = {equip_no: num}
                        if status == '调岗':
                            user_result[key]['status'] = status
        result.append(dic)

    def get(self, factory_date, u_name, classes, day=0):
        year = int(factory_date.split('-')[0])
        month = int(factory_date.split('-')[1])
        equip_list = Equip.objects.filter(category__equip_type__global_name='称量设备').values_list('equip_no', flat=True)
        # 获取人员包数
        filter_kwargs = {}
        if all([u_name, day, classes]):
            filter_kwargs = {'user__username': u_name, 'factory_date__day': day, 'classes': classes}
        result = []
        result1 = {}
        users = {}
        work_times = {}
        user_result = {}
        user_package = {}
        price_obj = SetThePrice.objects.first()
        if not price_obj:
            return '请先去添加细料/硫磺单价'
        # 查询称量分类下当前月上班的所有员工
        user_list = EmployeeAttendanceRecords.objects.filter(
            Q(factory_date__year=year, factory_date__month=month, equip__in=equip_list) &
            Q(end_date__isnull=False, begin_date__isnull=False) & ~Q(is_use='废弃'), ~Q(clock_type='密炼'), **filter_kwargs) \
            .values('user__username', 'factory_date__day', 'group', 'classes', 'section', 'equip', 'calculate_begin_date', 'calculate_end_date', 'status',
                    'factory_date')
        # 人工录入产量
        manual_set = ManualWeightOutput.objects.filter(s_factory_date__startswith=factory_date).values('equip_no', 's_factory_date', 'classes').annotate(
            count=Sum('package_count')).values('equip_no', 's_factory_date', 'classes', 'count')
        manual_data = {f"{i['equip_no']}_{i['s_factory_date']}_{i['classes']}": i['count'] for i in manual_set}
        if filter_kwargs:  # 获取包数
            data = user_list.order_by('equip')
            user_total = {}
            for i in data:
                section, equip_no, st, et, classes, s_factory_date = i.get('section'), i.get('equip'), i.get('calculate_begin_date'), \
                    i.get('calculate_end_date'), i.get('classes'), i.get('factory_date')
                plan_model, report_basic = [JZPlan, JZReportBasic] if equip_no in JZ_EQUIP_NO else [Plan, ReportBasic]
                if equip_no in JZ_EQUIP_NO:
                    classes = '早' if classes == '早班' else ('晚' if classes == '夜班' else '中')
                num = report_basic.objects.using(equip_no).filter(starttime__gte=st, savetime__lte=et, grouptime=classes).aggregate(num=Count('id'))['num']
                manual_count = manual_data.get(f'{equip_no}_{s_factory_date}_{classes}', 0)
                t_num = manual_count + num
                if not t_num:
                    continue
                key = f"{equip_no}-{section}"
                unit = price_obj.xl if equip_no.startswith('F') else price_obj.lh
                equip_data = user_package.get(key)
                if equip_data:
                    equip_data['num'] += t_num
                else:
                    user_package[key] = {'section': section, 'num': t_num, 'equip_no': equip_no, 'unit': unit}
                user_total[equip_no] = user_total.get(equip_no, 0) + t_num
            return {'detail': user_package.values(), 'user_total': user_total}
        # 岗位系数
        section_dic = {}
        section_info = PerformanceJobLadder.objects.filter(delete_flag=False, type='生产配料').values('type', 'name', 'coefficient', 'post_standard',
                                                                                                      'post_coefficient')
        for item in section_info:
            section_dic[f"{item['name']}_{item['type']}"] = [item['coefficient'], item['post_standard'], item['post_coefficient']]
        # 员工类别
        independent = {}
        independent_lst = IndependentPostTemplate.objects.filter(date_time=factory_date).values('name', 'status', 'work_type')
        for item in independent_lst:
            independent[item['name']] = {'status': item['status'], 'work_type': item['work_type']}
        if not independent:
            return f'请添加{factory_date}员工类别'
        # 员工类别系数
        employee_type = GlobalCode.objects.filter(global_type__type_name='员工类别', global_type__use_flag=True, use_flag=True).values('global_no',
                                                                                                                                       'global_name')
        employee_type_dic = {dic['global_no']: dic['global_name'] for dic in employee_type}
        # 员工独立上岗系数
        coefficient = GlobalCode.objects.filter(global_type__type_name='是否独立上岗系数', global_type__use_flag=True, use_flag=True).values('global_no',
                                                                                                                                             'global_name')
        coefficient_dic = {dic['global_no']: dic['global_name'] for dic in coefficient}
        if not coefficient or not employee_type_dic:
            return f'请在公共变量中添加员工独立上岗系数或员工类别系数'

        for item in user_list:
            key = f"{item['factory_date__day']}-{item['classes']}-{item['equip']}"
            if users.get(key):
                work_times[key][item['user__username'] + '_' + item['section']] = [item['calculate_begin_date'], item['calculate_end_date']]
                users[key][item['user__username']] = [item['section']] + (
                    [] if not users[key].get(item['user__username']) else users[key][item['user__username']])
            else:
                work_times[key] = {item['user__username'] + '_' + item['section']: [item['calculate_begin_date'], item['calculate_end_date']]}
                users[key] = {item['user__username']: [item['section']]}
                if item['status'] == '调岗':
                    users[key]['status'] = '调岗'
        # 机台产量统计
        qty_data, t_num = {}, 4
        pool = ThreadPool(t_num)
        for equip_no in equip_list:
            pool.apply_async(self.concat_user_package, args=(equip_no, result, factory_date, users, work_times, user_result, qty_data, manual_data))
        pool.close()
        pool.join()
        sort_res = sorted(result, key=lambda x: x['equip_no'])
        for key, value in user_result.items():
            """
            key: test_1_早班_主控
            value: {'F03': 109, 'F02': 100,}
            """
            name, day, classes, section = key.split('_')
            # trans_flag = user_list.filter(status='调岗', user__username=name, classes=classes, factory_date=(factory_date + '-' + '%02d' % int(day)))
            trans_flag = value.pop('status', None)
            equip = list(value.keys())[0]
            type = '生产配料'
            if trans_flag:
                equip, count_ = equip, sum(value.values())
            else:
                if section_dic[f"{section}_{type}"][1] == 1:  # 最大值
                    equip, count_ = sorted(value.items(), key=lambda kv: (kv[1], kv[0]))[-1]
                else:  # 平均值  是否需要去除为0的机台再取平均
                    equip, count_ = equip, sum(value.values()) / len(value)
            # 细料/硫磺单价'
            unit_price = price_obj.xl if equip in ['F01', 'F02', 'F03'] else price_obj.lh
            # 员工类别系数
            a, w_coefficient = float(coefficient_dic.get('是', 1)), 1
            if independent.get(name):
                if independent.get(name).get('status') != 1:
                    a = float(coefficient_dic.get('否'))
                work_type = independent.get(name).get('work_type')
                w_coefficient = float(employee_type_dic.get(work_type)) if work_type else w_coefficient
            coefficient = section_dic[f"{section}_{type}"][0] / 100
            post_coefficient = section_dic[f"{section}_{type}"][2] / 100
            price = round(count_ * coefficient * post_coefficient * unit_price * a * w_coefficient, 2)
            xl = price if equip in ['F01', 'F02', 'F03'] else 0
            lh = price if equip in ['S01', 'S02'] else 0

            if result1.get(name):
                result1[name][f"{day}{classes}"] = price
                result1[name][f"{day}{classes}_count"] = count_
                result1[name]['xl'] = round(result1[name].get('xl', 0) + xl, 2)
                result1[name]['lh'] = round(result1[name].get('lh', 0) + lh, 2)
            else:
                result1[name] = {'name': name, f"{day}{classes}": price, f"{day}{classes}_count": count_, 'xl': round(xl, 2), 'lh': round(lh, 2)}
        return {'results': sort_res, 'users': result1.values(), 'user_result': user_result}


res = SummaryOfWeighingOutput().get('2023-07-01', '闵登军', '早班', 1)
print(res)
