from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_jwt.views import obtain_jwt_token, refresh_jwt_token

from system.views import UserViewSet, UserGroupsViewSet, GroupExtensionViewSet, SectionViewSet, \
    GroupAddUserViewSet, LoginView, Synchronization, GroupPermissions, PlanReceive, MaterialReceive, ResetPassword, \
    DelUser

# app_name = 'system'
router = DefaultRouter()

router.register(r"personnels_groups", UserGroupsViewSet)

router.register(r'personnels', UserViewSet)

router.register(r'group_extension', GroupExtensionViewSet)

router.register(r'section', SectionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('group_add_user/<pk>/', GroupAddUserViewSet.as_view()),
    path('login/', LoginView.as_view()),
    path('api-token-auth/', obtain_jwt_token),
    path('api-token-refresh/', refresh_jwt_token),
    path('synchronization/', Synchronization.as_view()),  # 删除断网后计划数据
    path('group-permissions/', GroupPermissions.as_view()),
    path('plan-receive/', PlanReceive.as_view()),  # 接受上辅机同步来计划的数据
    path('material-receive/', MaterialReceive.as_view()),  # 接受上辅机同步来原材料的数据
    path('reset-password/', ResetPassword.as_view()),
    path('del-user/<pk>/', DelUser.as_view()),
]
