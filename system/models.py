from django.contrib.auth.models import AbstractUser, Group
from django.db import models


class Section(models.Model):
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


class User(AbstractUser):
    """用户拓展信息"""
    num = models.CharField(max_length=20, help_text='工号', verbose_name='工号')
    is_leave = models.BooleanField(help_text='是否离职', verbose_name='是否离职', default=False)
    section = models.ForeignKey(Section, blank=True, null=True, help_text='部门', verbose_name='部门',
                                on_delete=models.DO_NOTHING)
    delete_flag = models.BooleanField(help_text='是否删除', verbose_name='是否删除', default=False)
    created_user = models.ForeignKey("self", blank=True, null=True, related_name='user',
                                     on_delete=models.DO_NOTHING, help_text='创建人', verbose_name='创建人')


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


class FunctionBlock(AbstractEntity):
    """功能区分表"""
    function_block_id = models.CharField(max_length=50, help_text='功能区分代码', verbose_name='功能区分代码')
    name = models.CharField(max_length=30, help_text='功能区分名称', verbose_name='功能区分名称')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'function_block'
        verbose_name_plural = verbose_name = '功能区分'


class FunctionPermission(AbstractEntity):
    """功能权限表"""
    function_permission_id = models.CharField(max_length=50, help_text='功能权限代码', verbose_name='功能权限代码')
    name = models.CharField(max_length=30, help_text='功能权限名称', verbose_name='功能权限名称')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'function_permission'
        verbose_name_plural = verbose_name = '功能权限'


class Function(AbstractEntity):
    """功能表"""
    function_id = models.CharField(max_length=50, help_text='功能代码', verbose_name='功能代码')
    name = models.CharField(max_length=30, help_text='功能名称', verbose_name='功能名称')
    function_url = models.CharField(max_length=200, help_text='功能路径', verbose_name='功能路径')
    function_block = models.ForeignKey(FunctionBlock, blank=True, null=True, help_text='功能区分', verbose_name='功能区分', on_delete=models.DO_NOTHING)
    used_flag = models.BooleanField(help_text='是否使用', verbose_name='是否使用')
    function_permission = models.ManyToManyField(FunctionPermission, help_text='功能权限', verbose_name='功能权限')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'function'
        verbose_name_plural = verbose_name = '功能'


class Menu(AbstractEntity):
    """菜单表"""
    menu_id = models.CharField(max_length=50, help_text='菜单ID', verbose_name='菜单ID')

    name = models.CharField(max_length=30, help_text='菜单名称', verbose_name='菜单名称')
    parent = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True,
                               help_text='上层菜单', verbose_name='上层菜单')
    used_flag = models.BooleanField(help_text='是否使用', verbose_name='是否使用')
    function = models.OneToOneField(Function, blank=True, null=True, help_text='功能', verbose_name='功能', on_delete=models.DO_NOTHING)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'menu'
        verbose_name_plural = verbose_name = '菜单'


class GroupExtension(Group):
    """组织拓展信息表"""
    group_code = models.CharField(max_length=50, help_text='角色代码', verbose_name='角色代码')
    use_flag = models.BooleanField(help_text='是否使用', verbose_name='是否使用')
    # menu = models.ManyToManyField(Menu, blank=True, null=True, help_text='菜单', verbose_name='菜单')
    # function = models.ManyToManyField(Function, blank=True, null=True, help_text='功能', verbose_name='功能')

    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'group_extension'
        verbose_name_plural = verbose_name = '组织拓展信息'

