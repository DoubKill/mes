from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission


class IsSuperUser(BasePermission):
    """
    Allows access only to superuser users.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)


class ProductBatchingPermissions(BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        if obj.used_type == 1:  # 当前状态是编辑
            return '配方审核' in request.user.groups.values_list('name', flat=True)
        elif obj.used_type == 2:  # 当前状态是校验通过
            return '配方应用' in request.user.groups.values_list('name', flat=True)
        elif obj.used_type == 3:  # 当前状态是应用
            return '配方废弃' in request.user.groups.values_list('name', flat=True)


class PermissonsDispatch(object):

    def __init__(self, user):
        self.user = user

    @property
    def get_user_group_permissions(self):
        """
        返回用户组的的权限名称列表
        """
        return [_.split(".")[1] for _ in self.user.get_group_permissions()] if self.user else []

    @property
    def get_user_module_permissions(self):
        """
        返回带模块名的用户所有权限集合
        :return:
        """
        return self.user.get_all_permissions()

    @property
    def get_user_permissions(self):
        """
        返回用户组的的权限名称列表
        :return:
        """
        return self.user.user_permissions.values_list("codename", flat=True) if self.user else []

    @property
    def get_all_permissions(self):
        """
        返回用户组+用户的的权限名称列表
        :return:
        """
        return [_.split(".")[1] for _ in self.user.get_all_permissions()] if self.user else []

    def __call__(self, dispatch="all"):
        """
        根据dispatch的值返回具体的权限列表
        :param user_id:
        :param dispatch: "user", "group", "all"
        :return:
        """
        if dispatch == "user":
            return self.get_user_permissions
        elif dispatch == "group":
            return self.get_user_group_permissions
        elif dispatch == "module":
            return self.get_user_module_permissions
        else:
            return self.get_all_permissions


def PermissionClass(permission_required=None):
    class _PermissionClass(BasePermission):
        """
        http权限控制,作为permission_classes参数
        参数模式：
        permission_required=
        {'view': '__all__', 'change': 'constract_update', 'add': 'constract_add', 'delete': 'constract_delete'}
        """

        def get_permission_required(self):
            if permission_required is None:
                raise ImproperlyConfigured(
                    '{0} 缺少一个 permission_required 参数. 设置 {0}.permission_required, 或者重写 '
                    '{0}.get_permission_required().'.format(self.__class__.__name__)
                )
            if not isinstance(permission_required, dict):
                raise ValidationError(
                    '{0} 的 permission_required 参数必须为字符串或者字典. '.format(self.__class__.__name__)
                )
            if set(permission_required) - {'view', 'change', 'delete', 'add'}:
                raise ValidationError(
                    "{0} 的 permission_required 为字典时, key只能在. "
                    "['view', 'change', 'delete', 'add'] 中选择".format(self.__class__.__name__)
                )
            permission_dict = dict()
            # permission_dict['OPTION'] = permission_required['view'] \
            #     if isinstance(permission_required['view'], list) else [permission_required['view']]
            if 'view' in permission_required:
                permission_dict['GET'] = permission_required['view'] \
                    if isinstance(permission_required['view'], list) else [permission_required['view']]
            if 'change' in permission_required:
                permission_dict['PATCH'] = permission_required['change'] \
                    if isinstance(permission_required['change'], list) else [permission_required['change']]
                permission_dict['PUT'] = permission_required['change'] \
                    if isinstance(permission_required['change'], list) else [permission_required['change']]
            if 'delete' in permission_required:
                permission_dict['DELETE'] = permission_required['delete'] \
                    if isinstance(permission_required['delete'], list) else [permission_required['delete']]
            if 'add' in permission_required:
                permission_dict['POST'] = permission_required['add'] \
                    if isinstance(permission_required['add'], list) else [permission_required['add']]
            return permission_dict

        def has_permission(self, request, view):
            """
            判断是否有权限
            """
            permission_dict = self.get_permission_required()
            if '__all__' in permission_dict.get(request.method, ""):
                return True
            if request.user.is_superuser:
                return True
            permission = request.user.raw_permissions
            # 判断是否有权限
            if not set(permission_dict.get(request.method, "")) & set(permission):
                return False
            return True

    return _PermissionClass
