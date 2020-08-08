# coding: utf-8
"""项目初始化脚本"""
import datetime
import os
import random
import string

import django

import xlrd

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from basics.models import GlobalCode, GlobalCodeType, WorkSchedule, ClassesDetail, EquipCategoryAttribute, PlanSchedule, \
    Equip, WorkSchedulePlan
from recipe.models import Material, ProductInfo, ProductRecipe, ProductBatching, ProductBatchingDetail
from system.models import GroupExtension, User, Section

last_names = ['赵', '钱', '孙', '李', '周', '吴', '郑', '王', '冯', '陈', '褚', '卫', '蒋', '沈', '韩', '杨', '朱', '秦', '尤', '许',
              '何', '吕', '施', '张', '孔', '曹', '严', '华', '金', '魏', '陶', '姜', '戚', '谢', '邹', '喻', '柏', '水', '窦', '章',
              '云', '苏', '潘', '葛', '奚', '范', '彭', '郎', '鲁', '韦', '昌', '马', '苗', '凤', '花', '方', '俞', '任', '袁', '柳',
              '酆', '鲍', '史', '唐', '费', '廉', '岑', '薛', '雷', '贺', '倪', '汤', '滕', '殷', '罗', '毕', '郝', '邬', '安', '常',
              '乐', '于', '时', '傅', '皮', '卞', '齐', '康', '伍', '余', '元', '卜', '顾', '孟', '平', '黄', '和', '穆', '萧', '尹',
              '姚', '邵', '堪', '汪', '祁', '毛', '禹', '狄', '米', '贝', '明', '臧', '计', '伏', '成', '戴', '谈', '宋', '茅', '庞',
              '熊', '纪', '舒', '屈', '项', '祝', '董', '梁']

first_names = ['的', '一', '是', '了', '我', '不', '人', '在', '他', '有', '这', '个', '上', '们', '来', '到', '时', '大', '地', '为',
               '子', '中', '你', '说', '生', '国', '年', '着', '就', '那', '和', '要', '她', '出', '也', '得', '里', '后', '自', '以',
               '会', '家', '可', '下', '而', '过', '天', '去', '能', '对', '小', '多', '然', '于', '心', '学', '么', '之', '都', '好',
               '看', '起', '发', '当', '没', '成', '只', '如', '事', '把', '还', '用', '第', '样', '道', '想', '作', '种', '开', '美',
               '总', '从', '无', '情', '己', '面', '最', '女', '但', '现', '前', '些', '所', '同', '日', '手', '又', '行', '意', '动',
               '方', '期', '它', '头', '经', '长', '儿', '回', '位', '分', '爱', '老', '因', '很', '给', '名', '法', '间', '斯', '知',
               '世', '什', '两', '次', '使', '身', '者', '被', '高', '已', '亲', '其', '进', '此', '话', '常', '与', '活', '正', '感',
               '见', '明', '问', '力', '理', '尔', '点', '文', '几', '定', '本', '公', '特', '做', '外', '孩', '相', '西', '果', '走',
               '将', '月', '十', '实', '向', '声', '车', '全', '信', '重', '三', '机', '工', '物', '气', '每', '并', '别', '真', '打',
               '太', '新', '比', '才', '便', '夫', '再', '书', '部', '水', '像', '眼', '等', '体', '却', '加', '电', '主', '界', '门',
               '利', '海', '受', '听', '表', '德', '少', '克', '代', '员', '许', '稜', '先', '口', '由', '死', '安', '写', '性', '马',
               '光', '白', '或', '住', '难', '望', '教', '命', '花', '结', '乐', '色', '更', '拉', '东', '神', '记', '处', '让', '母',
               '父', '应', '直', '字', '场', '平', '报', '友', '关', '放', '至', '张', '认', '接', '告', '入', '笑', '内', '英', '军',
               '候', '民', '岁', '往', '何', '度', '山', '觉', '路', '带', '万', '男', '边', '风', '解', '叫', '任', '金', '快', '原',
               '吃', '妈', '变', '通', '师', '立', '象', '数', '四', '失', '满', '战', '远', '格', '士', '音', '轻', '目', '条', '呢',
               '病', '始', '达', '深', '完', '今', '提', '求', '清', '王', '化', '空', '业', '思', '切', '怎', '非', '找', '片', '罗',
               '钱', '紶', '吗', '语', '元', '喜', '曾', '离', '飞', '科', '言', '干', '流', '欢', '约', '各', '即', '指', '合', '反',
               '题', '必', '该', '论', '交', '终', '林', '请', '医', '晚', '制', '球', '决', '窢', '传', '画', '保', '读', '运', '及',
               '则', '房', '早', '院', '量', '苦', '火', '布', '品', '近', '坐', '产', '答', '星', '精', '视', '五', '连', '司', '巴',
               '奇', '管', '类', '未', '朋', '且', '婚', '台', '夜', '青', '北', '队', '久', '乎', '越', '观', '落', '尽', '形', '影',
               '红', '爸', '百', '令', '周', '吧', '识', '步', '希', '亚', '术', '留', '市', '半', '热', '送', '兴', '造', '谈', '容',
               '极', '随', '演', '收', '首', '根', '讲', '整', '式', '取', '照', '办', '强', '石', '古', '华', '諣', '拿', '计', '您',
               '装', '似', '足', '双', '妻', '尼', '转', '诉', '米', '称', '丽', '客', '南', '领', '节', '衣', '站', '黑', '刻', '统',
               '断', '福', '城', '故', '历', '惊', '脸', '选', '包', '紧', '争', '另', '建', '维', '绝', '树', '系', '伤', '示', '愿',
               '持', '千', '史', '谁', '准', '联', '妇', '纪', '基', '买', '志', '静', '阿', '诗', '独', '复', '痛', '消', '社', '算',
               '义', '竟', '确', '酒', '需', '单', '治', '卡', '幸', '兰', '念', '举', '仅', '钟', '怕', '共', '毛', '句', '息', '功',
               '官', '待', '究', '跟', '穿', '室', '易', '游', '程', '号', '居', '考', '突', '皮', '哪', '费', '倒', '价', '图', '具',
               '刚', '脑', '永', '歌', '响', '商', '礼', '细', '专', '黄', '块', '脚', '味', '灵', '改', '据', '般', '破', '引', '食',
               '仍', '存', '众', '注', '笔', '甚', '某', '沉', '血', '备', '习', '校', '默', '务', '土', '微', '娘', '须', '试', '怀',
               '料', '调', '广', '蜖', '苏', '显', '赛', '查', '密', '议', '底', '列', '富', '梦', '错', '座', '参', '八', '除', '跑',
               '亮', '假', '印', '设', '线', '温', '虽', '掉', '京', '初', '养', '香', '停', '际', '致', '阳', '纸', '李', '纳', '验',
               '助', '激', '够', '严', '证', '帝', '饭', '忘', '趣', '支', '春', '集', '丈', '木', '研', '班', '普', '导', '顿', '睡',
               '展', '跳', '获', '艺', '六', '波', '察', '群', '皇', '段', '急', '庭', '创', '区', '奥', '器', '谢', '弟', '店', '否',
               '害', '草', '排', '背', '止', '组', '州', '朝', '封', '睛', '板', '角', '况', '曲', '馆', '育', '忙', '质', '河', '续',
               '哥', '呼', '若', '推', '境', '遇', '雨', '标', '姐', '充', '围', '案', '伦', '护', '冷', '警', '贝', '著', '雪', '索',
               '剧', '啊', '船', '险', '烟', '依', '斗', '值', '帮', '汉', '慢', '佛', '肯', '闻', '唱', '沙', '局', '伯', '族', '低',
               '玩', '资', '屋', '击', '速', '顾', '泪', '洲', '团', '圣', '旁', '堂', '兵', '七', '露', '园', '牛', '哭', '旅', '街',
               '劳', '型', '烈', '姑', '陈', '莫', '鱼', '异', '抱', '宝', '权', '鲁', '简', '态', '级', '票', '怪', '寻', '杀', '律',
               '胜', '份', '汽', '右', '洋', '范', '床', '舞', '秘', '午', '登', '楼', '贵', '吸', '责', '例', '追', '较', '职', '属',
               '渐', '左', '录', '丝', '牙', '党', '继', '托', '赶', '章', '智', '冲', '叶', '胡', '吉', '卖', '坚', '喝', '肉', '遗',
               '救', '修', '松', '临', '藏', '担', '戏', '善', '卫', '药', '悲', '敢', '靠', '伊', '村', '戴', '词', '森', '耳', '差',
               '短', '祖', '云', '规', '窗', '散', '迷', '油', '旧', '适', '乡', '架', '恩', '投', '弹', '铁', '博', '雷', '府', '压',
               '超', '负', '勒', '杂', '醒', '洗', '采', '毫', '嘴', '毕', '九', '冰', '既', '状', '乱', '景', '席', '珍', '童', '顶',
               '派', '素', '脱', '农', '疑', '练', '野', '按', '犯', '拍', '征', '坏', '骨', '余', '承', '置', '臓', '彩', '灯', '巨',
               '琴', '免', '环', '姆', '暗', '换', '技', '翻', '束', '增', '忍', '餐', '洛', '塞', '缺', '忆', '判', '欧', '层', '付',
               '阵', '玛', '批', '岛', '项', '狗', '休', '懂', '武', '革', '良', '恶', '恋', '委', '拥', '娜', '妙', '探', '呀', '营',
               '退', '摇', '弄', '桌', '熟', '诺', '宣', '银', '势', '奖', '宫', '忽', '套', '康', '供', '优', '课', '鸟', '喊', '降',
               '夏', '困', '刘', '罪', '亡', '鞋', '健', '模', '败', '伴', '守', '挥', '鲜', '财', '孤', '枪', '禁', '恐', '伙', '杰',
               '迹', '妹', '藸', '遍', '盖', '副', '坦', '牌', '江', '顺', '秋', '萨', '菜', '划', '授', '归', '浪', '听', '凡', '预',
               '奶', '雄', '升', '碃', '编', '典', '袋', '莱', '含', '盛', '济', '蒙', '棋', '端', '腿', '招', '释', '介', '烧', '误',
               '乾', '坤']


def add_global_codes():
    names = ['胶料状态', '产地', '包装单位', '原材料类别', '胶料段次', '班组', '班次', '设备类型', '工序', '炼胶机类型', '设备层次']
    for i, name in enumerate(names):
        instance, _ = GlobalCodeType.objects.get_or_create(type_no=str(i+1), type_name=name, used_flag=1)
        items = []
        if i == 1:
            items = ['安吉', '下沙', '杭州', '泰国']
        elif i == 2:
            items = ['袋', '包', '盒']
        elif i == 3:
            items = ['天然胶', '合成胶', '炭黑', '白色填料', '防老剂', '再生胶', '增塑剂', '粘合剂', '活化剂', '树脂', '硫化机',
                     '其他化工类', 'CMB', '待处料', 'FM', 'HMB', 'NF', 'RE', 'RFM', 'RMB', '1MB', '2MB', '3MB', '胎圈钢丝',
                     '纤维帘丝', '钢丝类', '帘布', '钢丝帘线']
        elif i == 4:
            items = ['MB1', 'MB2', 'FM']
        elif i == 5:
            items = ["a班", "b班", "c班"]
        elif i == 6:
            items = ["早班", "中班", "晚班"]
        elif i == 7:
            items = ["密炼设备", "快检设备", "传送设备"]
        elif i == 8:
            items = ["一段", "二段", "三段"]
        elif i == 9:
            items = ['400', '500', '600']
        elif i == 10:
            items = ['1', '2', '3']
        for item in items:
            GlobalCode.objects.get_or_create(global_no=str(i+1), global_name=item, global_type=instance)


def add_materials():
    """原材料信息"""
    wb = xlrd.open_workbook('原材料信息.xlsx')
    sheet = wb.sheets()[0]
    for i in range(1, sheet.nrows):
        x = sheet.row_values(i)
        data = dict()
        data['material_no'] = x[2]
        data['material_name'] = x[4]
        data['material_type'] = GlobalCode.objects.filter(global_name=x[3]).first()
        data['density'] = 1
        data['used_flag'] = 1
        try:
            Material.objects.create(**data)
        except Exception:
            pass


def add_groups():
    """角色信息"""
    wb = xlrd.open_workbook('用户组.xlsx')
    sheet = wb.sheets()[0]
    for i in range(1, sheet.nrows):
        x = sheet.row_values(i)
        try:
            name, _ = GroupExtension.objects.get_or_create(name=x[3], group_code=x[2], use_flag=1)
        except Exception:
            pass


def random_name(size=1, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def first_name(size=2, ln=None, fn=None):
    _lst = []
    for i in range(size):
        _item = random_name(1, fn)
        if ln:
            while _item in ln:
                _item = random_name(1, fn)
            _lst.append(_item)
        else:
            _lst.append(_item)
    return "".join(_lst)


def last_name(size=1, names=None):
    return random_name(size, names)


def full_name(lns, fns):
    _last = last_name(1, lns)
    return "{}{}".format(_last, first_name(random.randint(1, 2), _last, fns))


def getRandomName():
    return full_name(last_names, first_names)


def add_sections():
    for name in ['快检', '质检', '安全', '密炼', '管理', '后勤', '设备']:
        Section.objects.create(
            section_id=str(random.randint(1000, 9999)),
            name=name
        )


def add_users():
    section_ids = list(Section.objects.values_list('id', flat=True))
    group_ids = list(GroupExtension.objects.values_list('id', flat=True))
    for i in range(500):
        name = getRandomName()
        user = User.objects.create(
                username=name,
                password='123456',
                num=i,
                is_leave=False,
                section_id=random.choice(section_ids),
            )
        user.groups.add(random.choice(group_ids))


def randomtimes(start, end, n, frmt="%Y-%m-%d"):
    stime = datetime.datetime.strptime(start, frmt)

    etime = datetime.datetime.strptime(end, frmt)
    return [random.random() * (etime - stime) + stime for _ in range(n)]


def add_schedules():
    for name in ['密炼', '快检', '设备', '机械']:
        schedule = WorkSchedule.objects.create(
            schedule_no=str(random.randint(100, 999)),
            schedule_name=name
        )
        times = ['2020-06-01 00:00:01', '2020-06-01 08:00:00',
                 '2020-06-01 16:00:00', '2020-06-01 23:00:59']
        for i in range(3):
            ClassesDetail.objects.create(
                work_schedule=schedule,
                classes_id=random.choice(GlobalCode.objects.filter(global_type__type_name='班次'
                                                                   ).values_list('id', flat=True)),
                start_time=times[i],
                end_time=times[i+1]
            )


def add_equip_attribute():
    equip_type_ids = list(GlobalCode.objects.filter(global_type__type_name='设备类型').values_list('id', flat=True))
    process_ids = list(GlobalCode.objects.filter(global_type__type_name='工序').values_list('id', flat=True))

    for i in range(10):
        EquipCategoryAttribute.objects.create(
            equip_type_id=random.choice(equip_type_ids),
            category_no=random.randint(1000, 9000),
            category_name='设备属性{}'.format(i),
            volume=random.choice([400, 500, 600, 700, 800]),
            process_id=random.choice(process_ids)
        )


def add_equips():
    equip_level_ids = list(GlobalCode.objects.filter(global_type__type_name='设备层次').values_list('id', flat=True))
    attr_ids = list(EquipCategoryAttribute.objects.values_list('id', flat=True))
    for i in range(100):
        Equip.objects.create(
            category_id=random.choice(attr_ids),
            equip_no=random.randint(1000, 9999),
            equip_name='设备{}'.format(i),
            used_flag=True,
            count_flag=True,
            equip_level_id=random.choice(equip_level_ids)
        )


def add_plan_schedule():
    ids = list(WorkSchedule.objects.values_list('id', flat=True))
    times = ['2020-01-01', '2020-01-02', '2020-01-03',
             '2020-01-04', '2020-01-05', '2020-01-06',
             '2020-01-07']
    group_ids = list(GlobalCode.objects.filter(global_type__type_name='班组').values_list('id', flat=True))

    detail_ids = list(ClassesDetail.objects.values_list('id', flat=True))
    for i, time in enumerate(times):
        instance = PlanSchedule.objects.create(
            day_time=time,
            week_time=PlanSchedule.TYPE_CHOICE_WEEK[i][0],
            work_schedule_id=random.choice(ids)
        )
        for j in range(3):
            group_id = random.choice(group_ids)
            WorkSchedulePlan.objects.create(
                classes_detail_id=random.choice(detail_ids),
                group_id=group_id,
                group_name=GroupExtension.objects.get(id=group_id).name,
                rest_flag=False,
                plan_schedule=instance
            )


def add_product():
    products = ('J260','A019','A403','B166','B568','B635','C101','C110','C120','C140','C150','C155','C160', 'C180','C190','C195','EUC121')
    factory_ids = list(GlobalCode.objects.filter(global_type__type_name='产地').values_list('id', flat=True))
    stages = GlobalCode.objects.filter(global_type__type_name='胶料段次')
    materials = list(Material.objects.values_list('id', flat=True))
    for i in products:
        product = ProductInfo.objects.create(
            product_no=i,
            product_name=i,
            versions='01',
            factory_id=random.choice(factory_ids),
            used_type=1,
            recipe_weight=0
        )
        i = 1
        weight = 0
        for stage in stages:
            for k in range(random.randint(1, 4)):
                recipe = ProductRecipe.objects.create(
                    product_recipe_no=product.product_no + stage.global_name,
                    num=i,
                    product_info=product,
                    material_id=random.choice(materials),
                    stage=stage,
                    ratio=random.randint(10, 100)
                )
                weight += recipe.ratio
                i += 1
        product.recipe_weight = weight
        product.save()


def add_batch():
    dev_ids = list(GlobalCode.objects.filter(global_type__type_name='设备类型').values_list('id', flat=True))
    time_choice = ('00:02:12', '00:01:42', '00:03:44')
    for product in ProductInfo.objects.all():
        for stage in product.productrecipe_set.all().values('stage__global_name', 'stage'):
            instance = ProductBatching.objects.create(
                product_info=product,
                stage_product_batch_no=product.product_no + stage['stage__global_name'] + product.versions,
                stage_id=stage['stage'],
                dev_type_id=random.choice(dev_ids),
                batching_weight=random.randint(200, 500),
                manual_material_weight=random.randint(100, 300),
                volume=0,
                batching_time_interval=random.choice(time_choice),
                rm_flag=0,
                batching_proportion=0,
                production_time_interval=random.choice(time_choice)
                )
            mat_ids = ProductRecipe.objects.filter(product_info=product,
                                                   stage_id=stage['stage']).values_list('material', flat=True)
            i = 0
            for mat in mat_ids:
                ProductBatchingDetail.objects.create(
                    product_batching=instance,
                    num=i,
                    material_id=mat
                )


if __name__ == '__main__':
    add_global_codes()
    add_materials()
    add_groups()
    add_sections()
    add_users()
    add_schedules()
    add_equip_attribute()
    add_equips()
    add_plan_schedule()
    add_product()
    add_batch()