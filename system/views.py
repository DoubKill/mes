from datetime import datetime

import xlrd
from django.contrib.auth.models import Permission
from django.utils.decorators import method_decorator
from rest_framework import mixins, status
from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet, GenericViewSet
from rest_framework_jwt.views import ObtainJSONWebToken

from mes.common_code import menu, CommonDeleteMixin
from mes.derorators import api_recorder
from mes.paginations import SinglePageNumberPagination

from plan.models import ProductClassesPlan
from recipe.models import ProductBatching
from system.models import GroupExtension, User, Section, ChildSystemInfo, SystemConfig
from system.serializers import GroupExtensionSerializer, GroupExtensionUpdateSerializer, UserSerializer, \
    UserUpdateSerializer, SectionSerializer, PermissionSerializer, GroupUserUpdateSerializer
from django_filters.rest_framework import DjangoFilterBackend
from system.filters import UserFilter, GroupExtensionFilter


@method_decorator([api_recorder], name="dispatch")
class PermissionViewSet(ReadOnlyModelViewSet):
    """
    list:
        权限列表
    create:
        创建权限
    update:
        修改权限
    destroy:
        删除权限
    """
    queryset = Permission.objects.filter()
    serializer_class = PermissionSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = SinglePageNumberPagination
    # filter_backends = (DjangoFilterBackend,)


@method_decorator([api_recorder], name="dispatch")
class UserViewSet(ModelViewSet):
    """
    list:
        用户列表
    create:
        创建用户
    update:
        修改用户
    destroy:
        账号停用和启用
    """
    queryset = User.objects.filter(delete_flag=False).prefetch_related('user_permissions', 'groups')
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = UserFilter

    def destroy(self, request, *args, **kwargs):
        # 账号停用和启用
        instance = self.get_object()
        if instance.is_active:
            instance.is_active = 0
        else:
            instance.is_active = 1
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_serializer_class(self):
        if self.action == 'list':
            return UserSerializer
        if self.action == 'create':
            return UserSerializer
        if self.action == 'update':
            return UserUpdateSerializer
        if self.action == 'retrieve':
            return UserSerializer
        if self.action == 'partial_update':
            return UserUpdateSerializer


@method_decorator([api_recorder], name="dispatch")
class UserGroupsViewSet(mixins.ListModelMixin,
                        GenericViewSet):
    queryset = User.objects.filter(delete_flag=False).prefetch_related('user_permissions', 'groups')

    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    pagination_class = SinglePageNumberPagination
    filter_class = UserFilter


@method_decorator([api_recorder], name="dispatch")
class GroupExtensionViewSet(CommonDeleteMixin, ModelViewSet):  # 本来是删除，现在改为是启用就改为禁用 是禁用就改为启用
    """
    list:
        角色列表,xxx?all=1查询所有
    create:
        创建角色
    update:
        修改角色
    destroy:
        删除角色
    """
    queryset = GroupExtension.objects.filter(delete_flag=False).prefetch_related('user_set', 'permissions')
    serializer_class = GroupExtensionSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = GroupExtensionFilter

    def get_permissions(self):
        if self.request.query_params.get('all'):
            return ()
        else:
            return (IsAuthenticated(),)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'name')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return GroupExtensionSerializer
        if self.action == 'create':
            return GroupExtensionSerializer
        elif self.action == 'update':
            return GroupExtensionUpdateSerializer
        if self.action == 'partial_update':
            return GroupExtensionUpdateSerializer


@method_decorator([api_recorder], name="dispatch")
class GroupAddUserViewSet(UpdateAPIView):
    """控制角色中用户具体为哪些的视图"""
    queryset = GroupExtension.objects.filter(delete_flag=False).prefetch_related('user_set', 'permissions')
    serializer_class = GroupUserUpdateSerializer


@method_decorator([api_recorder], name="dispatch")
class SectionViewSet(ModelViewSet):
    """
    list:
        角色列表
    create:
        创建角色
    update:
        修改角色
    destroy:
        删除角色
    """
    queryset = Section.objects.filter(delete_flag=False)
    serializer_class = SectionSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)


class MesLogin(ObtainJSONWebToken):
    menu = {
        "basics": [
            "globalcodetype",
            "globalcode",
            "workschedule",
            "equip"
        ],
        "system": {
            "user",
        },
        "auth": {
        }

    }

    def post(self, request, *args, **kwargs):
        temp = super().post(request, *args, **kwargs)
        format = kwargs.get("format")
        if temp.status_code != 200:
            return temp
        return menu(request, self.menu, temp, format)


class LoginView(ObtainJSONWebToken):
    """
    post
        获取权限列表
    """

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = serializer.object.get('user') or request.user
            token = serializer.object.get('token')
            # 获取该用户所有权限
            permissions = list(user.get_all_permissions())
            # 除去前端不涉及模块
            permission_list = []
            for p in permissions:
                if p.split(".")[0] not in ["contenttypes", "sessions", "work_station", "admin"]:
                    permission_list.append(p)
            # 生成菜单管理树
            permissions_set = set([_.split(".")[0] for _ in permission_list])
            permissions_tree = {__: {} for __ in permissions_set}
            for x in permission_list:
                first_key = x.split(".")[0]
                second_key = x.split(".")[-1].split("_")[-1]
                op_value = x.split(".")[-1].split("_")[0]
                op_list = permissions_tree.get(first_key, {}).get(second_key)
                if op_list:
                    permissions_tree[first_key][second_key].append(op_value)
                else:
                    permissions_tree[first_key][second_key] = [op_value]
            if permissions_tree.get("auth"):
                auth = permissions_tree.pop("auth")
                # 合并auth与system
                if permissions_tree.get("system"):
                    permissions_tree["system"].update(**auth)
                else:
                    permissions_tree["system"] = auth

            # 先这么写 待会给李威看,
            # 并没有删除 只是给其他的模块新增
            # 把plan里的productdayplan复制一份放在production里
            if permissions_tree['plan'] and permissions_tree['plan'].get('productdayplan') and permissions_tree[
                'production']:
                permissions_tree['production']['productdayplan'] = permissions_tree['plan'].get('productdayplan')

            # 把recipe里的material复制一份放在production里
            if permissions_tree['recipe'] and permissions_tree['recipe'].get('material') and permissions_tree[
                'production']:
                permissions_tree['production']['material'] = permissions_tree['recipe'].get('material')

            # 把system里的groupextension和user复制一份放在basics里
            if permissions_tree['system'] and permissions_tree['system'].get('groupextension') and permissions_tree[
                'system'].get('user') and permissions_tree['basics']:
                permissions_tree['basics']['groupextension'] = permissions_tree['system'].get('groupextension')
                permissions_tree['basics']['user'] = permissions_tree['system'].get('user')

            return Response({"results": permissions_tree,
                             "username": user.username,
                             "token": token})
        # 返回异常信息
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Synchronization(APIView):
    def get(self, request, *args, **kwargs):
        mes_dict = {}
        mes_dict['plan'] = {}
        mes_dict['recipe'] = {}
        # mes_dict = {'ProductClassesPlan': [], 'ProductBatching': []}
        # 获取断网时间
        params = request.query_params
        lost_time1 = params.get("lost_time")
        lost_time = datetime.strptime(lost_time1, '%Y-%m-%d %X')
        print(lost_time, type(lost_time))
        mes_dict["lost_time"] = lost_time
        if lost_time:
            # 胶料日班次计划
            pcp_set = ProductClassesPlan.objects.filter(last_updated_date__gte=lost_time)
            if pcp_set:
                mes_dict['plan']['ProductClassesPlan'] = {}
                for pcp_obj in pcp_set:
                    pcp_dict = pcp_obj.__dict__
                    pcp_dict.pop("_state")
                    mes_dict['plan']['ProductClassesPlan'][pcp_obj.plan_classes_uid] = pcp_dict
            pbc_set = ProductBatching.objects.filter(last_updated_date__gte=lost_time)
            if pbc_set:
                mes_dict['recipe']['ProductBatching'] = {}
                for pbc_obj in pbc_set:
                    pbc_dict = pbc_obj.__dict__
                    pbc_dict.pop("_state")
                    mes_dict['recipe']['ProductBatching'][pbc_obj.stage_product_batch_no] = pbc_dict

        return Response({'MES系统': mes_dict}, status=200)
