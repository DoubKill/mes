from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """用户拓展信息"""
    num = models.CharField(max_length=20, help_text='工号', verbose_name='工号', unique=True)
    is_leave = models.BooleanField(help_text='是否离职', verbose_name='是否离职', default=False)
    section = models.ForeignKey("Section", blank=True, null=True, help_text='部门', verbose_name='部门',
                                on_delete=models.SET_NULL, related_name="section_users")
    created_date = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    last_updated_date = models.DateTimeField(verbose_name='修改时间', auto_now=True)
    delete_date = models.DateTimeField(blank=True, null=True,
                                       help_text='删除日期', verbose_name='删除日期')
    delete_flag = models.BooleanField(help_text='是否删除', verbose_name='是否删除', default=False)
    created_user = models.ForeignKey('self', blank=True, null=True, related_name='c_%(app_label)s_%(class)s_related',
                                     help_text='创建人', verbose_name='创建人', on_delete=models.CASCADE,
                                     related_query_name='c_%(app_label)s_%(class)ss')
    last_updated_user = models.ForeignKey('self', blank=True, null=True,
                                          related_name='u_%(app_label)s_%(class)s_related',
                                          help_text='更新人', verbose_name='更新人', on_delete=models.CASCADE,
                                          related_query_name='u_%(app_label)s_%(class)ss')
    delete_user = models.ForeignKey('self', blank=True, null=True, related_name='d_%(app_label)s_%(class)s_related',
                                    help_text='删除人', verbose_name='删除人', on_delete=models.CASCADE,
                                    related_query_name='d_%(app_label)s_%(class)ss')
    group_extensions = models.ManyToManyField('GroupExtension', help_text='角色', related_name='group_users',)
    phone_number = models.CharField(max_length=11, help_text='手机号', verbose_name='手机号', blank=True, null=True)
    workshop = models.CharField(max_length=32, help_text='车间', verbose_name='车间', blank=True, null=True)
    technology = models.CharField(max_length=32, help_text='技术资格', verbose_name='技术资格', blank=True, null=True)
    repair_group = models.CharField(max_length=32, help_text='维修班组', verbose_name='维修班组', blank=True, null=True)
    id_card_num = models.CharField(max_length=18, help_text='身份证号码', blank=True, null=True)

    def __str__(self):
        return "{}".format(self.username)

    class Meta:
        db_table = "user"
        verbose_name_plural = verbose_name = '用户'


class AbstractEntity(models.Model):
    created_date = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    last_updated_date = models.DateTimeField(verbose_name='修改时间', auto_now=True)
    delete_date = models.DateTimeField(blank=True, null=True,
                                       help_text='删除日期', verbose_name='删除日期')
    delete_flag = models.BooleanField(help_text='是否删除', verbose_name='是否删除', default=False)
    created_user = models.ForeignKey(User, blank=True, null=True, related_name='c_%(app_label)s_%(class)s_related',
                                     help_text='创建人', verbose_name='创建人', on_delete=models.CASCADE,
                                     related_query_name='c_%(app_label)s_%(class)ss')
    last_updated_user = models.ForeignKey(User, blank=True, null=True, related_name='u_%(app_label)s_%(class)s_related',
                                          help_text='更新人', verbose_name='更新人', on_delete=models.CASCADE,
                                          related_query_name='u_%(app_label)s_%(class)ss')
    delete_user = models.ForeignKey(User, blank=True, null=True, related_name='d_%(app_label)s_%(class)s_related',
                                    help_text='删除人', verbose_name='删除人', on_delete=models.CASCADE,
                                    related_query_name='d_%(app_label)s_%(class)ss')

    class Meta(object):
        abstract = True


class Section(AbstractEntity):
    """部门表"""
    section_id = models.CharField(max_length=40, help_text='部门ID', verbose_name='部门ID')
    name = models.CharField(max_length=30, help_text='部门名称', verbose_name='部门名称')
    description = models.CharField(max_length=256, blank=True, null=True,
                                   help_text='说明', verbose_name='说明')
    parent_section = models.ForeignKey('self', help_text='父节点部门', on_delete=models.CASCADE,
                                       related_name='children_sections', blank=True, null=True)
    in_charge_user = models.ForeignKey(User, help_text='负责人', blank=True, null=True, on_delete=models.CASCADE,
                                       related_name='in_charge_sections')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'section'
        verbose_name_plural = verbose_name = '部门'


class Permissions(models.Model):
    code = models.CharField(max_length=64, help_text='权限代码', unique=True)
    name = models.CharField(max_length=64, help_text='权限名称')
    parent = models.ForeignKey('self', help_text='父节点', related_name='children_permissions',
                               blank=True, null=True, on_delete=models.CASCADE)

    @property
    def children_list(self):
        return list(self.children_permissions.values('id', 'code', 'name'))

    class Meta:
        db_table = 'permissions'
        verbose_name_plural = verbose_name = '权限'


class GroupExtension(AbstractEntity):
    """角色"""
    group_code = models.CharField(max_length=50, help_text='角色代码', verbose_name='角色代码', unique=True)
    name = models.CharField('角色名称', max_length=150, unique=True)
    use_flag = models.BooleanField(help_text='是否使用', verbose_name='是否使用', default=True)
    permissions = models.ManyToManyField(Permissions, help_text='角色权限', blank=True)

    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'group_extensions'
        verbose_name_plural = verbose_name = '角色'


class ChildSystemInfo(AbstractEntity):
    link_address = models.CharField(max_length=64, help_text='连接地址', verbose_name='连接地址')
    system_type = models.CharField(max_length=64, help_text='系统类型', verbose_name='系统地址')
    system_name = models.CharField(max_length=64, help_text='系统名称', verbose_name='系统名称')
    status = models.CharField(max_length=64, help_text='子系统状态', verbose_name='子系统状态', default="联网")
    status_lock = models.BooleanField(help_text="状态锁/true的时候status不可修改", verbose_name="状态锁", default=False)

    def __str__(self):
        return f"{self.system_type}|{self.system_name}|{self.link_address}"

    class Meta:
        db_table = 'child_system_info'
        verbose_name_plural = verbose_name = '子系统信息'


class SystemConfig(AbstractEntity):
    category = models.CharField(max_length=64, help_text='种类', verbose_name='种类')
    config_name = models.CharField(max_length=64, help_text='配置名称', verbose_name='配置名称')
    config_value = models.CharField(max_length=64, help_text='配置值', verbose_name='配置值')
    description = models.CharField(max_length=64, help_text='描述', verbose_name='描述', default="")

    def __str__(self):
        return f"{self.category}|{self.config_name}|{self.config_value}"

    class Meta:
        db_table = 'system_config'
        verbose_name_plural = verbose_name = '系统配置表'


class AsyncUpdateContent(AbstractEntity):
    """异步更新表"""
    content = models.CharField(max_length=64, help_text='内容', verbose_name='内容')
    recv_flag = models.BooleanField(default=False, help_text='已经接受标志', verbose_name='已经接受标志')
    src_table_name = models.CharField(max_length=64, help_text='表名', verbose_name='表名')
    dst_address = models.CharField(max_length=64, help_text='目标地址', verbose_name='目标地址')
    method = models.CharField(max_length=64, help_text='http方法', verbose_name='http方法')

    def __str__(self):
        return f"{self.src_table_name}"

    class Meta:
        db_table = 'async_update_content'
        verbose_name_plural = verbose_name = '异步更新表'


class AsyncUpdateContentHistory(AbstractEntity):
    """异步更新历史表"""
    content = models.CharField(max_length=64, help_text='内容', verbose_name='内容')
    recv_flag = models.BooleanField(default=False, help_text='已经接受标志', verbose_name='已经接受标志')
    src_table_name = models.CharField(max_length=64, help_text='表名', verbose_name='表名')
    dst_address = models.CharField(max_length=64, help_text='目标地址', verbose_name='目标地址')
    method = models.CharField(max_length=64, help_text='http方法', verbose_name='http方法')

    def __str__(self):
        return f"{self.src_table_name}|history"

    class Meta:
        db_table = 'async_update_content_history'
        verbose_name_plural = verbose_name = '异步更新历史表'


class ErrorCode(AbstractEntity):
    """错误编码表"""
    name = models.CharField(max_length=64, help_text='错误名称', verbose_name='错误名称')
    description = models.CharField(max_length=256, help_text='描述', verbose_name='描述')
    error_type = models.ForeignKey("ErrorType", help_text='错误类型', verbose_name='错误类型',
                                   on_delete=models.CASCADE, related_name="error_code_set")

    def __str__(self):
        return f"{self.name}"

    class Meta:
        db_table = 'error_code'
        verbose_name_plural = verbose_name = '错误编码'


class ErrorType(AbstractEntity):
    """错误类型表"""
    name = models.CharField(max_length=64, help_text='错误名称', verbose_name='错误名称')
    description = models.CharField(max_length=256, help_text='描述', verbose_name='描述')
    category = models.CharField(max_length=64, help_text='错误名称', verbose_name='错误名称')

    def __str__(self):
        return f"{self.name}"

    class Meta:
        db_table = 'error_type'
        verbose_name_plural = verbose_name = '错误类型'


class DataSynchronization(models.Model):
    """记录已经同步过去的数据"""
    TYPE_CHOICE = (
        (1, '公共代码类型'),
        (2, '公共代码'),
        (3, '倒班管理'),
        (4, '倒班条目'),
        (5, '设备种类属性'),
        (6, '设备'),
        (7, '排班管理'),
        (8, '排班详情'),
        (9, '原材料'),
        (10, '胶料信息')
    )
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    type = models.PositiveSmallIntegerField(help_text='模型类型', verbose_name='模型类型', choices=TYPE_CHOICE)
    obj_id = models.IntegerField(help_text='对应数据库id', verbose_name='对应数据库id')

    class Meta:
        db_table = 'data_sync'
        verbose_name_plural = verbose_name = '自动同步数据'
