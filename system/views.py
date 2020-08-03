import xlrd
from django.contrib.auth.models import Permission
from django.utils.decorators import method_decorator
from rest_framework import mixins
from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet, GenericViewSet
from rest_framework_jwt.views import ObtainJSONWebToken

from mes.common_code import menu
from mes.derorators import api_recorder
from mes.paginations import SinglePageNumberPagination
from system.models import GroupExtension, User, Section
from system.serializers import GroupExtensionSerializer, GroupExtensionUpdateSerializer, UserSerializer, \
    UserUpdateSerializer, SectionSerializer, PermissionSerializer, GroupUserUpdateSerializer
from basics.views import CommonDeleteMixin
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
    permission_classes = (IsAuthenticatedOrReadOnly,)
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
        删除用户
    """
    queryset = User.objects.all()

    serializer_class = UserSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = UserFilter

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
            return UserSerializer


class UserGroupsViewSet(mixins.ListModelMixin,
                           GenericViewSet):
    queryset = User.objects.all()

    serializer_class = UserSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    pagination_class = SinglePageNumberPagination
    filter_class = UserFilter



@method_decorator([api_recorder], name="dispatch")
class GroupExtensionViewSet(ModelViewSet):
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
    queryset = GroupExtension.objects.filter()
    serializer_class = GroupExtensionSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = GroupExtensionFilter

    def get_serializer_class(self):
        if self.action == 'list':
            return GroupExtensionSerializer
        if self.action == 'create':
            return GroupExtensionSerializer
        if self.action == 'update':
            return GroupExtensionUpdateSerializer
        if self.action == 'retrieve':
            return GroupExtensionSerializer
        if self.action == 'partial_update':
            return GroupExtensionSerializer


@method_decorator([api_recorder], name="dispatch")
class GroupAddUserViewSet(UpdateAPIView):
    """控制角色中用户具体为哪些的视图"""
    queryset = GroupExtension.objects.all()
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
    queryset = Section.objects.filter()
    serializer_class = SectionSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)


# @method_decorator([api_recorder], name="dispatch")
# class FunctionBlockViewSet(ModelViewSet):
#     """
#     list:
#         角色列表
#     create:
#         创建角色
#     update:
#         修改角色
#     destroy:
#         删除角色
#     """
#     queryset = FunctionBlock.objects.filter()
#     serializer_class = FunctionBlockSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly,)
#     filter_backends = (DjangoFilterBackend,)


# @method_decorator([api_recorder], name="dispatch")
# class FunctionPermissionViewSet(ModelViewSet):
#     """
#     list:
#         角色列表
#     create:
#         创建角色
#     update:
#         修改角色
#     destroy:
#         删除角色
#     """
#     queryset = FunctionPermission.objects.filter()
#     serializer_class = FunctionPermissionSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly,)
#     filter_backends = (DjangoFilterBackend,)


# @method_decorator([api_recorder], name="dispatch")
# class FunctionViewSet(ModelViewSet):
#     """
#     list:
#         角色列表
#     create:
#         创建角色
#     update:
#         修改角色
#     destroy:
#         删除角色
#     """
#     queryset = Function.objects.filter()
#     serializer_class = FunctionSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly,)
#     filter_backends = (DjangoFilterBackend,)


# @method_decorator([api_recorder], name="dispatch")
# class MenuViewSet(ModelViewSet):
#     """
#     list:
#         角色列表
#     create:
#         创建角色
#     update:
#         修改角色
#     destroy:
#         删除角色
#     """
#     queryset = Menu.objects.filter()
#     serializer_class = MenuSerializer
#     permission_classes = (IsAuthenticatedOrReadOnly,)
#     filter_backends = (DjangoFilterBackend,)


class MesLogin(ObtainJSONWebToken):
    menu = {
        "basics": [
            "globalcodetype",
            "globalcode",
            "workschedule",
            "equip",
            # "sysbaseequiplevel",
            "classesdetail",
            # "workscheduleplan"
        ],
        "system": {
            "user",
            "section",
        },
        "auth": {
            # "group",
            "permission",
        }

    }

    def post(self, request, *args, **kwargs):
        temp = super().post(request, *args, **kwargs)
        format = kwargs.get("format")
        if temp.status_code != 200:
            return temp
        return menu(request, self.menu, temp, format)


class ImportExcel(APIView):

    def post(self, request, *args, **kwargs):
        excel_file = request.FILES.get('excel_file', '')
        if excel_file.name.endswith(".xlsx"):
            data = xlrd.open_workbook(filename=None, file_contents=excel_file.read())  # xlsx文件
        elif excel_file.endswith(".xls"):
            data = xlrd.open_workbook(filename=None, file_contents=excel_file.read(), formatting_info=True)  # xls
        else:
            raise TypeError
        all_list_1 = self.get_sheets_mg(data)
        for x in all_list_1:
            print(x)
        return Response({"msg": "ok"})

    def get_sheets_mg(self, data, num=0):  # data:Excel数据对象，num要读取的表
        table = data.sheets()[num]  # 打开第一张表
        nrows = table.nrows  # 获取表的行数
        ncole = table.ncols  # 获取列数
        all_list = []
        for i in range(nrows):  # 循环逐行打印
            one_list = []
            for j in range(ncole):
                cell_value = table.row_values(i)[j]
                if (cell_value is None or cell_value == ''):
                    cell_value = (self.get_merged_cells_value(table, i, j))
                one_list.append(cell_value)
            all_list.append(one_list)
        del (all_list[0])  # 删除标题   如果Excel文件中第一行是标题可删除掉，如果没有就不需要这行代码
        return all_list

    def get_merged_cells_value(self, sheet, row_index, col_index):
        """
        先判断给定的单元格，是否属于合并单元格；
        如果是合并单元格，就返回合并单元格的内容
        :return:
        """
        merged = self.get_merged_cells(sheet)
        # print(merged,"==hebing==")
        for (rlow, rhigh, clow, chigh) in merged:
            if (row_index >= rlow and row_index < rhigh):
                if (col_index >= clow and col_index < chigh):
                    cell_value = sheet.cell_value(rlow, clow)
                    # print('该单元格[%d,%d]属于合并单元格，值为[%s]' % (row_index, col_index, cell_value))
                    return cell_value
                    break
        return None

    def get_merged_cells(self, sheet):
        """
        获取所有的合并单元格，格式如下：
        [(4, 5, 2, 4), (5, 6, 2, 4), (1, 4, 3, 4)]
        (4, 5, 2, 4) 的含义为：行 从下标4开始，到下标5（不包含）  列 从下标2开始，到下标4（不包含），为合并单元格
        :param sheet:
        :return:
        """
        return sheet.merged_cells
