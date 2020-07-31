from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_jwt.views import obtain_jwt_token, refresh_jwt_token

from system.views import UserViewSet, UserGroupsViewSet, GroupExtensionViewSet, SectionViewSet, PermissionViewSet, \
    GroupAddUserViewSet

# app_name = 'system'
router = DefaultRouter()
# router.register(r'group', GroupViewSet)
router.register(r"personnels_groups", UserGroupsViewSet)

router.register(r'personnels', UserViewSet)

router.register(r'group_extension', GroupExtensionViewSet)

router.register(r'section', SectionViewSet)
# router.register(r'function_block', FunctionBlockViewSet)

# router.register(r'function_permission', FunctionPermissionViewSet)
# router.register(r'function', FunctionViewSet)
# router.register(r'menu', MenuViewSet)
router.register(r"permission", PermissionViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('group_add_user/<pk>/', GroupAddUserViewSet.as_view()),

    path('api-token-auth/', obtain_jwt_token),
    path('api-token-refresh/', refresh_jwt_token),
]
