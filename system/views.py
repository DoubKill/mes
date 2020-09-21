from datetime import datetime

from django.utils.decorators import method_decorator
from rest_framework import mixins, status
from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework_jwt.views import ObtainJSONWebToken

from mes.common_code import CommonDeleteMixin
from mes.derorators import api_recorder
from mes.paginations import SinglePageNumberPagination
from mes.common_code import UserFunctions

from plan.models import ProductClassesPlan
from recipe.models import ProductBatching
from system.models import GroupExtension, User, Section, Permissions
from system.serializers import GroupExtensionSerializer, GroupExtensionUpdateSerializer, UserSerializer, \
    UserUpdateSerializer, SectionSerializer, GroupUserUpdateSerializer
from django_filters.rest_framework import DjangoFilterBackend
from system.filters import UserFilter, GroupExtensionFilter


@method_decorator([api_recorder], name="dispatch")
class PermissionView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        ret = {}
        parent_permissions = Permissions.objects.filter(parent__isnull=True)
        for perm in parent_permissions:
            ret[perm.name] = perm.children_list
        return Response(data={'result': ret})


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
    queryset = User.objects.exclude(is_superuser=True).filter(delete_flag=False).prefetch_related('group_extensions')
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
    queryset = GroupExtension.objects.filter(
        delete_flag=False).prefetch_related('permissions').order_by('-created_date')
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
    queryset = GroupExtension.objects.filter(delete_flag=False).prefetch_related('group_users', 'permissions')
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


class LoginView(ObtainJSONWebToken):
    """
    post
        登录并返回用户所有权限
    """

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = serializer.object.get('user') or request.user
            token = serializer.object.get('token')
            return Response({"permissions": user.permissions_list,
                             "username": user.username,
                             "token": token})
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