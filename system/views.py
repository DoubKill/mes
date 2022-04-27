from datetime import datetime

from django.db.models import F
from django.db.transaction import atomic
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import UpdateAPIView, CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.views import ObtainJSONWebToken

from equipment.utils import DinDinAPI
from mes.common_code import zdy_jwt_payload_handler
from mes.conf import WMS_URL, TH_URL
from mes.derorators import api_recorder
from mes.paginations import SinglePageNumberPagination
from plan.models import ProductClassesPlan, MaterialDemanded, ProductDayPlan
from production.models import PlanStatus
from quality.utils import get_cur_sheet, get_sheet_data
from recipe.models import Material
from system.filters import UserFilter, GroupExtensionFilter, SectionFilter
from system.models import GroupExtension, User, Section, Permissions, DingDingInfo
from system.serializers import GroupExtensionSerializer, GroupExtensionUpdateSerializer, UserSerializer, \
    UserUpdateSerializer, SectionSerializer, GroupUserUpdateSerializer, PlanReceiveSerializer, \
    MaterialReceiveSerializer, UserImportSerializer, UserLoginSerializer


jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER


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
    queryset = User.objects.filter(delete_flag=False,
                                   is_superuser=False).order_by('num').prefetch_related('group_extensions')
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = UserFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if self.request.query_params.get('all'):
            data = queryset.values('id', 'username', 'num', 'is_active')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)

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
        if self.action in ['list', 'create', 'retrieve']:
            return UserSerializer
        else:
            return UserUpdateSerializer

    @action(methods=['post'], detail=False, permission_classes=[IsAuthenticated, ], url_path='import_xlsx',
            url_name='import_xlsx')
    def import_xlx(self, request):
        excel_file = request.FILES.get('file', None)
        if not excel_file:
            raise ValidationError('文件不可为空！')
        cur_sheet = get_cur_sheet(excel_file)
        if cur_sheet.ncols != 7:
            raise ValidationError('导入文件数据错误！')
        data = get_sheet_data(cur_sheet, start_row=1)
        user_list = []
        for item in data:
            user_data = {
                "username": item[0],
                "password": item[1],
                "num": str(item[2]).split('.')[0] if item[2] else item[2],
                "phone_number": str(item[3]).split('.')[0] if item[3] else item[3],
                "id_card_num": str(item[4]).split('.')[0] if item[4] else item[4],
                "section": item[5],
                "group_extensions": item[6]
            }
            user_list.append(user_data)
        s = UserImportSerializer(data=user_list, many=True, context={'request': self.request})
        if not s.is_valid():
            for i in s.errors:
                if i:
                    raise ValidationError(list(i.values())[0])
        validated_data = s.validated_data
        username_list = [item['username'] for item in validated_data]
        num_list = [item['num'] for item in validated_data]
        if len(username_list) != len(set(username_list)):
            raise ValidationError('导入数据中存在相同的用户名，请修改后重试！')
        if len(num_list) != len(set(num_list)):
            raise ValidationError('导入数据中存在相同的员工工号，请修改后重试！')
        s.save()
        return Response('ok')


@method_decorator([api_recorder], name="dispatch")
class UserGroupsViewSet(mixins.ListModelMixin,
                        GenericViewSet):
    queryset = User.objects.filter(delete_flag=False, is_superuser=False).prefetch_related('user_permissions', 'groups')
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    pagination_class = SinglePageNumberPagination
    filter_class = UserFilter


@method_decorator([api_recorder], name="dispatch")
class GroupExtensionViewSet(ModelViewSet):
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
            data = queryset.filter(use_flag=True).values('id', 'name')
            return Response({'results': data})
        else:
            return super().list(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return GroupExtensionUpdateSerializer
        else:
            return GroupExtensionSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.use_flag:
            instance.use_flag = 0
            instance.group_users.clear()
        else:
            instance.use_flag = 1
        instance.last_updated_user = request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator([api_recorder], name="dispatch")
class GroupAddUserViewSet(UpdateAPIView):
    """控制角色中用户具体为哪些的视图"""
    queryset = GroupExtension.objects.filter(delete_flag=False).prefetch_related('group_users', 'permissions')
    serializer_class = GroupUserUpdateSerializer


@method_decorator([api_recorder], name="dispatch")
class SectionViewSet(ModelViewSet):
    """
    list:
        部门列表
    create:
        创建部门
    update:
        修改部门
    destroy:
        删除部门
    """
    queryset = Section.objects.order_by('id')
    serializer_class = SectionSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = SectionFilter

    def list(self, request, *args, **kwargs):
        if self.request.query_params.get("all"):
            data = self.get_queryset().filter(parent_section__isnull=False).values('id', 'name')
            return Response({'results': data})
        if self.request.query_params.get('section_users'):
            section = self.queryset.filter(section_users=self.request.user).first()
            return Response({'section': section.name if section else None})
        if self.request.query_params.get('section_name'):
            # 根据部门获取部门负责人
            name = self.request.query_params.get('section_name')
            section = self.queryset.filter(name=name).first()
            in_charge_user = None
            if section:
                in_charge_user = section.in_charge_user.username if section.in_charge_user else None
            return Response({'in_charge_user': in_charge_user})
        data = []
        index_tree = {}
        for section in Section.objects.order_by('id'):
            in_charge_username = section.in_charge_user.username if section.in_charge_user else ''
            if section.id not in index_tree:
                index_tree[section.id] = dict({"id": section.id,
                                               'section_id': section.section_id,
                                               'in_charge_user_id': section.in_charge_user_id,
                                               'in_charge_username': in_charge_username,
                                               "label": section.name, 'repair_areas': section.repair_areas,
                                               'children': []})

            if not section.parent_section_id:  # 根节点
                data.append(index_tree[section.id])  # 浅拷贝
                continue

            if section.parent_section_id in index_tree:  # 子节点
                if "children" not in index_tree[section.parent_section_id]:
                    index_tree[section.parent_section_id]["children"] = []

                index_tree[section.parent_section_id]["children"].append(index_tree[section.id])
            else:  # 没有节点则加入
                index_tree[section.parent_section_id] = dict(
                    {"id": section.parent_section_id,
                     'section_id': section.section_id,
                     'in_charge_user_id': section.in_charge_user_id,
                     'in_charge_username': in_charge_username,
                     "label": section.parent_section.name,
                     "children": [], 'repair_areas': section.repair_areas})
                index_tree[section.parent_section_id]["children"].append(index_tree[section.id])
        return Response({'results': data})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.section_users.count() > 0:
            raise ValidationError('操作无效，该部门下存在用户！')
        if instance.children_sections.count() > 0:
            raise ValidationError('操作无效，该部门下存在子部门！')
        return super().destroy(request, *args, **kwargs)

    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated], url_path='tree',
            url_name='tree')
    def tree(self, request):
        data = []
        index_tree = {}
        for section in Section.objects.all():
            in_charge_username = section.in_charge_user.username if section.in_charge_user else ''
            if section.id not in index_tree:
                index_tree[section.id] = dict(
                    {"section_id": section.id, 'in_charge_username': in_charge_username, "label": section.name,
                     'children': list(User.objects.filter(section=section, is_active=1).values(user_id=F('id'),
                                                                                               label=F('username'),
                                                                                               type=F('workshop')))})

            if not section.parent_section_id:  # 根节点
                data.append(index_tree[section.id])  # 浅拷贝
                continue

            if section.parent_section_id in index_tree:  # 子节点
                if "children" not in index_tree[section.parent_section_id]:
                    index_tree[section.parent_section_id]["children"] = list(User.objects.filter(section=section.parent_section,
                                                                                                 is_active=1).values(user_id=F('id'),
                                                                                                                     label=F('username'),
                                                                                                                     type=F('workshop')))

                index_tree[section.parent_section_id]["children"].append(index_tree[section.id])
            else:  # 没有节点则加入
                index_tree[section.parent_section_id] = dict(
                    {"section_id": section.parent_section_id, 'in_charge_username': in_charge_username,
                     "label": section.parent_section.name, "children": list(User.objects.filter(section=section.parent_section,
                                                                                                is_active=1).values(user_id=F('id'),
                                                                                                                    label=F('username'),
                                                                                                                    type=F('workshop')))})
                index_tree[section.parent_section_id]["children"].append(index_tree[section.id])
        return Response({'results': data})


@method_decorator([api_recorder], name="dispatch")
class LoginView(ObtainJSONWebToken):
    """
    post
        登录并返回用户所有权限
    """
    serializer_class = UserLoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = serializer.object.get('user') or request.user
            token = serializer.object.get('token')
            return Response({"permissions": user.permissions_list,
                             'section': user.section.name if user.section else None,
                             'id_card_num': user.id_card_num,
                             "username": user.username,
                             'id': user.id,
                             "token": token,
                             'wms_url': WMS_URL,
                             'th_url': TH_URL})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator([api_recorder], name="dispatch")
class Synchronization(APIView):
    @atomic()
    def post(self, request, *args, **kwargs):
        # 获取断网时间
        params = request.data
        lost_time1 = params.get("lost_time")
        lost_time = datetime.strptime(lost_time1, '%Y-%m-%d %X')
        pcp_set = ProductClassesPlan.objects.filter(last_updated_date__gte=lost_time)
        ProductDayPlan.objects.filter(last_updated_date__gte=lost_time).update(delete_flag=True)
        for pcp_obj in pcp_set:
            PlanStatus.objects.filter(plan_classes_uid=pcp_obj.plan_classes_uid).update(delete_flag=True)
            MaterialDemanded.objects.filter(product_classes_plan=pcp_obj).update(delete_flag=True)
            pcp_obj.delete_flag = True
            pcp_obj.save()
        return Response('删除断网之后的计划成功', status=200)


@method_decorator([api_recorder], name="dispatch")
class GroupPermissions(APIView):
    """获取权限表格数据"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        group_id = self.request.query_params.get('group_id')
        if group_id:
            try:
                group = GroupExtension.objects.get(id=group_id)
            except Exception:
                raise ValidationError('参数错误')
            group_permissions = list(group.permissions.values_list('id', flat=True))
            ret = []
            parent_permissions = Permissions.objects.filter(parent__isnull=True)
            for perm in parent_permissions:
                children_list = perm.children_list
                for child in children_list:
                    if child['id'] in group_permissions:
                        child['has_permission'] = True
                    else:
                        child['has_permission'] = False
                ret.append({'name': perm.name, 'permissions': children_list})
        else:
            ret = []
            parent_permissions = Permissions.objects.filter(parent__isnull=True)
            for perm in parent_permissions:
                ret.append({'name': perm.name, 'permissions': perm.children_list})
        return Response(data={'result': ret})


@method_decorator([api_recorder], name="dispatch")
class PlanReceive(CreateAPIView):
    """接受上辅机计划数据接口"""
    # permission_classes = ()
    # authentication_classes = ()
    # permission_classes = (IsAuthenticated,)
    serializer_class = PlanReceiveSerializer
    queryset = ProductClassesPlan.objects.all()

    @atomic()
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


@method_decorator([api_recorder], name="dispatch")
class MaterialReceive(CreateAPIView):
    """接受上辅机原材料数据接口"""
    # permission_classes = ()
    # authentication_classes = ()
    # permission_classes = (IsAuthenticated,)
    serializer_class = MaterialReceiveSerializer
    queryset = Material.objects.all()

    @atomic()
    def post(self, request, *args, **kwargs):
        m_obj = Material.objects.filter(material_no=request.data['material_no']).first()
        if not m_obj:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response('mes拥有当前原材料', status=status.HTTP_201_CREATED)


def index(request):
    request.META["CSRF_COOKIE_USED"] = True
    return render(request, 'index.html')


@method_decorator([api_recorder], name="dispatch")
class ResetPassword(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = self.request.user
        new_password = self.request.data.get('new_password')
        old_password = self.request.data.get('old_password')
        if not all([new_password, old_password]):
            raise ValidationError('参数缺失！')
        if not user.check_password(old_password):
            raise ValidationError('原密码错误！')
        user.set_password(new_password)
        user.save()
        return Response('修改成功')


@method_decorator([api_recorder], name="dispatch")
class DelUser(APIView):
    permission_classes = (IsAuthenticated,)

    def delete(self, request, pk):
        try:
            instance = User.objects.get(pk=pk)
        except Exception:
            raise ValidationError('object does not exits!')
        u_name = instance.username + '(DELETED{})'.format(str(instance.id))
        instance.delete_flag = True
        instance.is_active = 0
        instance.username = u_name
        instance.save()
        return Response('ok')


@method_decorator([api_recorder], name="dispatch")
class IdentityCard(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = self.request.user
        id_card = self.request.data.get('id_card')
        jy = id_card[len(id_card) - 1:len(id_card)]  # 截取校验位
        if len(id_card) == 18:  # 判断输入的身份证号是否为18位
            if not id_card[0:17].isdigit():
                raise ValidationError('输入的身份证号有误！')
            x = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
            s = 0
            for i in range(1, len(id_card)):
                e = id_card[i - 1:i]
                s = s + int(e) * x[i - 1]
            b = s % 11
            y = ("1", "O", "X", "9", "8", "7", "6", "5", "4", "3", "2")
            c = y[b]
            if jy == c:  # 判断校验位是否相同
                user.id_card_num = id_card
                user.save()
            else:
                raise ValidationError('输入的身份证号有误！')
        else:
            raise ValidationError('输入的长度有误！')
        return Response('ok')


@method_decorator([api_recorder], name="dispatch")
class DingDingLoginView(APIView):
    """钉钉登录"""

    def post(self, request):
        auth_code = self.request.data.get('auth_code')
        if not auth_code:
            raise ValidationError('参数缺失！')
        try:
            d = DinDinAPI()
            dd_user_data = d.auth(auth_code)
        except Exception as err:
            raise ValidationError(str(err))
        dd_user_id = dd_user_data.get('userid')
        try:
            user = User.objects.get(dingding__dd_user_id=dd_user_id)
        except User.DoesNotExist:
            raise ValidationError("该钉钉账号未绑定MES用户！")
        if not user.is_active:
            raise ValidationError('该账号已被停用！')
        payload = zdy_jwt_payload_handler(user)
        token = jwt_encode_handler(payload)
        return Response({"permissions": user.permissions_list,
                         'section': user.section.name if user.section else None,
                         'id_card_num': user.id_card_num,
                         "username": user.username,
                         "userNo": user.num,
                         'id': user.id,
                         "token": token,
                         'wms_url': WMS_URL,
                         'th_url': TH_URL})


@method_decorator([api_recorder], name="dispatch")
class DingDingBind(APIView):
    """钉钉账号与MES绑定"""

    def post(self, request):
        username = self.request.data.get('username')
        password = self.request.data.get('password')
        auth_code = self.request.data.get('auth_code')
        if not all([username, password, auth_code]):
            raise ValidationError('参数缺失！')
        try:
            user = User.objects.get(username=username)
        except Exception:
            raise ValidationError('改用户不存在！')
        if not user.check_password(password):
            raise ValidationError('密码错误，请修改后重试！')
        if not user.is_active:
            raise ValidationError('该账号已被停用！')
        try:
            d = DinDinAPI()
            dd_user_data = d.auth(auth_code)
        except Exception as err:
            raise ValidationError(str(err))
        if DingDingInfo.objects.filter(dd_user_id=dd_user_data.get('userid')).exists():
            raise ValidationError('改钉钉已绑定其他MES账号！')
        if DingDingInfo.objects.filter(user__username=username).exists():
            raise ValidationError('MES账号已绑定其他钉钉账号！')
        dd_data = {
            "user": user,
            "dd_user_id": dd_user_data.get('userid'),
            "associated_unionid": dd_user_data.get('associated_unionid'),
            "unionid": dd_user_data.get('unionid'),
        }
        DingDingInfo.objects.create(**dd_data)
        payload = zdy_jwt_payload_handler(user)
        token = jwt_encode_handler(payload)
        return Response({"permissions": user.permissions_list,
                         'section': user.section.name if user.section else None,
                         'id_card_num': user.id_card_num,
                         "username": user.username,
                         "userNo": user.num,
                         'id': user.id,
                         "token": token,
                         'wms_url': WMS_URL,
                         'th_url': TH_URL})


@method_decorator([api_recorder], name="dispatch")
class QRLoginView(APIView):
    """钉钉扫码登录"""

    def post(self, request):
        code = self.request.data.get("code")
        d = DinDinAPI()
        union_id = d.get_union_id(code)
        dd_user_id = d.get_user_id_through_union_id(union_id)
        try:
            user = User.objects.get(dingding__dd_user_id=dd_user_id)
        except User.DoesNotExist:
            raise ValidationError("该钉钉账号未绑定MES用户！")
        if not user.is_active:
            raise ValidationError('该账号已被停用！')
        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)
        return Response({"permissions": user.permissions_list,
                         'section': user.section.name if user.section else None,
                         'id_card_num': user.id_card_num,
                         "username": user.username,
                         "userNo": user.num,
                         'id': user.id,
                         "token": token,
                         'wms_url': WMS_URL,
                         'th_url': TH_URL})