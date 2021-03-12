import os
import django

from pyecharts.render import templates



os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()
from basics.models import Equip
from equipment.models import EquipMaintenanceOrder
from django.db.models import Sum, F, Count

from jinja2 import Environment, FileSystemLoader
from pyecharts.globals import CurrentConfig
from django.conf import settings

CurrentConfig.GLOBAL_ENV = Environment(loader=FileSystemLoader("{}/templates".format(settings.BASE_DIR)))


from django.template import loader

from mes.settings import BASE_DIR



from pyecharts.charts import Bar, Page, Pie, Grid
from pyecharts import options as opts
import os
if __name__ == '__main__':
    # pyecharts=1.8.1
    # 安装 python -m pip install pyecharts
    page = Page(layout=Page.DraggablePageLayout)

    # bar1 = Bar()
    # bar1.add_xaxis(["衬衫", "毛衣", "领带", "裤子", "风衣", "高跟鞋", "袜子"])
    # bar1.add_yaxis("商家A", [114, 55, 27, 101, 125, 27, 105])
    # bar1.add_yaxis("商家B", [57, 134, 137, 129, 145, 60, 49])
    # bar1.add_yaxis("商家C", [57, 134, 137, 129, 145, 60, 49])
    # bar1.set_global_opts(title_opts=opts.TitleOpts(title="某商场销售情况2"))
    # 将柱状图bar和bar1添加到page页面中，这样就可以将两个图标绘制成一个html中了
    # pie = Pie()
    equip_list = list(Equip.objects.filter(category__process__global_name="密炼").values_list("equip_no", flat=True))
    # 统计各个机台各个部位的故障比例
    equip_part_dict = {_: [[],[]] for _ in equip_list}
    temp_set = EquipMaintenanceOrder.objects.filter().values("equip_part__equip__equip_no", "equip_part__name").annotate(counts=Count('id'))
    for temp in temp_set:
        equip_part_dict[temp.get("equip_part__equip__equip_no")]
    # data = [(x, equip_list.index(x))  for x in equip_list]
    # pie.add('天气类型', equip_list)
    # page.add(pie)
    # page.render("test.html")
    # os.system("test.html")
    bar = Bar(init_opts=opts.InitOpts(width='1200px', height='300px'))
    bar.add_xaxis(equip_list)
    bar.add_yaxis("运行时间", [114, 55, 27, 101, 125, 27, 105])
    bar.add_yaxis("故障时间", [57, 134, 137, 129, 145, 60, 49])
    # bar.add_yaxis("商家C", [57, 134, 137, 129, 145, 60, 49])
    bar.set_global_opts(title_opts=opts.TitleOpts(title="安吉工厂运行状况"))
    data_list = [x for x in range(2,5)]
    data1 = [list(z) for z in zip(equip_list, data_list)]
    pie1 = Pie(init_opts=opts.InitOpts(width='1200px', height='300px'))
    pie1.add(series_name='123', data_pair=data1, center=[400,150])
    equip_listE = ['缺失值率', '自身异常值率', '验证异常值率']
    data_listE = [22, 10.00, 12.15]
    data2 = [list(z) for z in zip(equip_listE, data_listE)]
    pie1.add(series_name='出生日期', data_pair=data2, center=[800, 150])
    pie1.set_global_opts(title_opts=opts.TitleOpts(title="机台维修时间占比", subtitle='单位：%'),
                         legend_opts=opts.LegendOpts())
    pie1.set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {d}"))
    # pie2 = Pie(init_opts=opts.InitOpts(width='400px', height='200px'))
    # pie2.add(series_name='出生日期异常值', data_pair=[list(z) for z in zip(equip_listE, data_listE)])  # 饼图圆心位置
    # pie2.set_global_opts(title_opts=opts.TitleOpts(title="出生日期异常值情况", subtitle='单位：1/100', pos_right='0'),  # 标题位置
    #                         legend_opts=opts.LegendOpts())  # 图例位置
    # pie2.set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {d}"))

    page.add(bar, pie1)
    page.render("test.html", **{"abc": "lee"})
    os.system("test.html")
