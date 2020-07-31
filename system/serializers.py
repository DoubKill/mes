"""
auther :liwei
create_date:
updater:
update_time:
"""
from django.contrib.auth.models import Permission
from django.db.transaction import atomic
from rest_framework import serializers
from django.contrib.auth.hashers import make_password

from mes.base_serializer import BaseModelSerializer
from mes.conf import COMMON_READ_ONLY_FIELDS
from system.models import GroupExtension, Group, User, Section


class GroupSerializer(BaseModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'
        # read_only_fields = COMMON_READ_ONLY_FIELDS


class PermissionSerializer(BaseModelSerializer):
    class Meta:
        model = Permission
        fields = ("id", "codename", "name",)


class UserUpdateSerializer(BaseModelSerializer):
    is_active = serializers.BooleanField(read_only=True)
    username = serializers.CharField(required=False)
    password = serializers.CharField(required=False)
    num = serializers.CharField(required=False)

    def to_representation(self, instance):
        instance = super().to_representation(instance)
        instance.pop('password')
        return instance

    def update(self, instance, validated_data):
        validated_data['password'] = make_password(validated_data['password']) if validated_data.get(
            'password') else instance.password
        return super(UserUpdateSerializer, self).update(instance, validated_data)

    class Meta:
        model = User
        fields = '__all__'
        # read_only_fields = COMMON_READ_ONLY_FIELDS


class UserSerializer(BaseModelSerializer):
    is_active = serializers.BooleanField(read_only=True)

    def to_representation(self, instance):
        instance = super().to_representation(instance)
        instance.pop('password')
        return instance

    def create(self, validated_data):
        password = validated_data.get('password')
        user = super().create(validated_data)
        user.set_password(password)
        user.save()
        return user

    class Meta:
        model = User
        fields = '__all__'
        # read_only_fields = COMMON_READ_ONLY_FIELDS


class GroupUserSerializer(BaseModelSerializer):
    id = serializers.IntegerField()
    username = serializers.CharField(required=False)
    password = serializers.CharField(required=False)
    num = serializers.CharField(required=False)

    def to_representation(self, instance):
        instance = super().to_representation(instance)
        instance.pop('password')
        return instance

    class Meta:
        model = User
        fields = '__all__'


class GroupExtensionSerializer(BaseModelSerializer):
    """角色组扩展序列化器"""

    class Meta:
        model = GroupExtension
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS

    def to_representation(self, instance):
        return super().to_representation(instance)


class GroupExtensionUpdateSerializer(BaseModelSerializer):
    """更新角色组用户序列化器"""
    user_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), write_only=True)

    def update(self, instance, validated_data):
        user_ids = validated_data['user_ids']

        instance.user_set.add(*user_ids)
        instance.save()
        return instance

    class Meta:
        model = GroupExtension
        fields = ('id', 'user_ids')
        # fields = '__all__'
        # read_only_fields = COMMON_READ_ONLY_FIELDS


class SectionSerializer(BaseModelSerializer):
    class Meta:
        model = Section
        fields = '__all__'
        read_only_fields = COMMON_READ_ONLY_FIELDS

# class FunctionBlockSerializer(BaseModelSerializer):
#
#     class Meta:
#         model = FunctionBlock
#         fields = '__all__'
#         read_only_fields = COMMON_READ_ONLY_FIELDS
#
#
# class FunctionPermissionSerializer(BaseModelSerializer):
#
#     class Meta:
#         model = FunctionPermission
#         fields = '__all__'
#         read_only_fields = COMMON_READ_ONLY_FIELDS
#
#
# class FunctionSerializer(BaseModelSerializer):
#
#     class Meta:
#         model = Function
#         fields = '__all__'
#         read_only_fields = COMMON_READ_ONLY_FIELDS
#
#
# class MenuSerializer(BaseModelSerializer):
#
#     class Meta:
#         model = Menu
#         fields = '__all__'
#         read_only_fields = COMMON_READ_ONLY_FIELDS
