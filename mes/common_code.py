from django.contrib.auth.models import AnonymousUser
from rest_framework import status, mixins
from rest_framework.response import Response
from rest_framework.reverse import reverse

from mes.permissions import PermissonsDispatch
from system.models import User


class CommonDeleteMixin(object):
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete_flag = True
        instance.delete_user = request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SyncCreateMixin(mixins.CreateModelMixin):
    # 创建时需记录同步数据的接口请继承该创建插件
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        setattr(response, "model_name", self.queryset.model.__name__)
        return response


class SyncUpdateMixin(mixins.UpdateModelMixin):
    # 更新时需记录同步数据的接口请继承该更新插件
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        setattr(response, "model_name", self.queryset.model.__name__)
        return response

def return_permission_params(model_name):
    """
    :param model_name: 模型类名.lower()
    :return: permission_required需求参数
    """
    return {
        'view': f'view_{model_name}',
        'add': f'add_{model_name}',
        'delete': f'delete_{model_name}',
        'change': f'change_{model_name}'
    }


def menu(request, menu, temp, format):
    """
    生成菜单树
    :param request: http_request
    :param menu: 当前项目的菜单结构，后期动态菜单可维护到数据库
    :param temp: 继承于原函数的中间返回体
    :param format: reverse需要参数
    :return:
    """

    username = request.data.get("username")
    user = User.objects.filter(username=username).first()
    permissions = PermissonsDispatch(user)(dispatch="module")
    data = {}
    for _ in permissions:
        module, permission = _.split(".")
        m = None
        if permission.startswith("view"):
            m = permission.split("_")[1]
        module_list = menu.get(module, {})
        if m in module_list:
            if isinstance(data.get(module), dict):
                data[module].update({m: reverse(f'{m}-list', request=request, format=format)})
            else:
                data[module] = {m: reverse(f'{m}-list', request=request, format=format)}

    temp.data.update({"menu": data})
    return temp


def get_user(request):
    """
    Return the user model instance associated with the given request session.
    If no user is retrieved, return an instance of `AnonymousUser`.
    """
    user = None
    try:
        user_id = _get_user_session_key(request)
        backend_path = request.session[BACKEND_SESSION_KEY]
    except KeyError:
        pass
    else:
        if backend_path in settings.AUTHENTICATION_BACKENDS:
            backend = load_backend(backend_path)
            user = backend.get_user(user_id)
            # Verify the session
            if hasattr(user, 'get_session_auth_hash'):
                session_hash = request.session.get(HASH_SESSION_KEY)
                session_hash_verified = session_hash and constant_time_compare(
                    session_hash,
                    user.get_session_auth_hash()
                )
                if not session_hash_verified:
                    request.session.flush()
                    user = None

    return user or AnonymousUser()