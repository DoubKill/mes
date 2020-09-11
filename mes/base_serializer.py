from collections import OrderedDict

from rest_framework import serializers
from rest_framework.fields import SkipField
from rest_framework.relations import PKOnlyObject

from django.utils.translation import ugettext as _

from system.models import User


def _common_to_representation(self, instance):
    """
    私有方法用于封装公用的to_representation方法
    :param self:
    :param instance:
    :return:
    """
    ret = OrderedDict()
    fields = self._readable_fields

    for field in fields:
        try:
            attribute = field.get_attribute(instance)
        except SkipField:
            continue

        # We skip `to_representation` for `None` values so that fields do
        # not have to explicitly deal with that case.
        #
        # For related fields with `use_pk_only_optimization` we need to
        # resolve the pk value.
        check_for_none = attribute.pk if isinstance(attribute, PKOnlyObject) else attribute
        if check_for_none is None:
            ret[field.field_name] = None
        else:
            temp_field = field.to_representation(attribute)
            if isinstance(temp_field, str):
                ret[field.field_name] = _(temp_field)
            else:
                ret[field.field_name] = temp_field
    return ret


class BaseHyperlinkSerializer(serializers.HyperlinkedModelSerializer):
    """封装字段值国际化功能后的超链接序列化器，需要用HyperlinkedModelSerializer请直接继承该类"""
    id = serializers.IntegerField(read_only=True)
    def to_representation(self, instance):
        """复用公共私有方法,扩展并继承原本to_representation方法"""
        return _common_to_representation(self, instance)


class BaseModelSerializer(serializers.ModelSerializer):
    """封装字段值国际化功能后的模型类序列化器，需要用ModelSerializer请直接继承该类"""
    created_username = serializers.CharField(source='created_user.username', read_only=True, default='')

    def to_representation(self, instance):
        """复用公共私有方法,扩展并继承原本to_representation方法"""
        return _common_to_representation(self, instance)

    def create(self, validated_data):
        """
        可供所有继承该序列化器的子类自动补充created_user
        :param validated_data:
        :return:
        """
        if self.Meta.model.__name__ in ["Permission", "Group"]:
            return super().create(validated_data)
        validated_data.update(created_user=self.context["request"].user)
        instance = super().create(validated_data)
        return instance

    def update(self, instance, validated_data):
        """
        可供所有继承该序列化器的子类自动补充updated_user
        :param instance:
        :param validated_data:
        :return:
        """
        if self.Meta.model.__name__ in ["Permission", "Group"]:
            return super().update(instance ,validated_data)
        validated_data.update(last_updated_user=self.context["request"].user)
        return super().update(instance ,validated_data)