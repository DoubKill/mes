from django.contrib.auth.models import AbstractUser, Group
from django.db import models


class User(AbstractUser):
    """用户拓展信息"""
    num = models.CharField(max_length=20, help_text='工号', verbose_name='工号', unique=True)
    is_leave = models.BooleanField(help_text='是否离职', verbose_name='是否离职', default=False)
    section = models.ForeignKey("Section", blank=True, null=True, help_text='部门', verbose_name='部门',
                                on_delete=models.DO_NOTHING)
    created_date = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    last_updated_date = models.DateTimeField(verbose_name='修改时间', auto_now=True)
    delete_date = models.DateTimeField(blank=True, null=True,
                                       help_text='删除日期', verbose_name='删除日期')
    delete_flag = models.BooleanField(help_text='是否删除', verbose_name='是否删除', default=False)
    created_user = models.ForeignKey('self', blank=True, null=True, related_name='c_%(app_label)s_%(class)s_related',
                                     help_text='创建人', verbose_name='创建人', on_delete=models.DO_NOTHING,
                                     related_query_name='c_%(app_label)s_%(class)ss')
    last_updated_user = models.ForeignKey('self', blank=True, null=True,
                                          related_name='u_%(app_label)s_%(class)s_related',
                                          help_text='更新人', verbose_name='更新人', on_delete=models.DO_NOTHING,
                                          related_query_name='u_%(app_label)s_%(class)ss')
    delete_user = models.ForeignKey('self', blank=True, null=True, related_name='d_%(app_label)s_%(class)s_related',
                                    help_text='删除人', verbose_name='删除人', on_delete=models.DO_NOTHING,
                                    related_query_name='d_%(app_label)s_%(class)ss')

    def __str__(self):
        return "{}".format(self.username)

    class Meta:
        db_table = "user"
        verbose_name_plural = verbose_name = '用户'
        permissions = ()


class AbstractEntity(models.Model):
    created_date = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    last_updated_date = models.DateTimeField(verbose_name='修改时间', auto_now=True)
    delete_date = models.DateTimeField(blank=True, null=True,
                                       help_text='删除日期', verbose_name='删除日期')
    delete_flag = models.BooleanField(help_text='是否删除', verbose_name='是否删除', default=False)
    created_user = models.ForeignKey(User, blank=True, null=True, related_name='c_%(app_label)s_%(class)s_related',
                                     help_text='创建人', verbose_name='创建人', on_delete=models.DO_NOTHING,
                                     related_query_name='c_%(app_label)s_%(class)ss')
    last_updated_user = models.ForeignKey(User, blank=True, null=True, related_name='u_%(app_label)s_%(class)s_related',
                                          help_text='更新人', verbose_name='更新人', on_delete=models.DO_NOTHING,
                                          related_query_name='u_%(app_label)s_%(class)ss')
    delete_user = models.ForeignKey(User, blank=True, null=True, related_name='d_%(app_label)s_%(class)s_related',
                                    help_text='删除人', verbose_name='删除人', on_delete=models.DO_NOTHING,
                                    related_query_name='d_%(app_label)s_%(class)ss')

    class Meta(object):
        abstract = True


class Section(AbstractEntity):
    """部门表"""
    section_id = models.CharField(max_length=40, help_text='部门ID', verbose_name='部门ID')
    name = models.CharField(max_length=30, help_text='部门名称', verbose_name='部门名称')
    description = models.CharField(max_length=256, blank=True, null=True,
                                   help_text='说明', verbose_name='说明')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'section'
        verbose_name_plural = verbose_name = '部门'


class GroupExtension(Group):
    """组织拓展信息表"""
    group_code = models.CharField(max_length=50, help_text='角色代码', verbose_name='角色代码', unique=True)
    use_flag = models.BooleanField(help_text='是否使用', verbose_name='是否使用')
    created_date = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    last_updated_date = models.DateTimeField(verbose_name='修改时间', auto_now=True)
    delete_date = models.DateTimeField(blank=True, null=True,
                                       help_text='删除日期', verbose_name='删除日期')
    delete_flag = models.BooleanField(help_text='是否删除', verbose_name='是否删除', default=False)
    created_user = models.ForeignKey(User, blank=True, null=True, related_name='c_%(app_label)s_%(class)s_related',
                                     help_text='创建人', verbose_name='创建人', on_delete=models.DO_NOTHING,
                                     related_query_name='c_%(app_label)s_%(class)ss')
    last_updated_user = models.ForeignKey(User, blank=True, null=True, related_name='u_%(app_label)s_%(class)s_related',
                                          help_text='更新人', verbose_name='更新人', on_delete=models.DO_NOTHING,
                                          related_query_name='u_%(app_label)s_%(class)ss')
    delete_user = models.ForeignKey(User, blank=True, null=True, related_name='d_%(app_label)s_%(class)s_related',
                                    help_text='删除人', verbose_name='删除人', on_delete=models.DO_NOTHING,
                                    related_query_name='d_%(app_label)s_%(class)ss')

    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'group_extension'
        verbose_name_plural = verbose_name = '组织拓展信息'


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
                                on_delete=models.DO_NOTHING, related_name="error_code_set")

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