from django.urls import path
from . import views

app_name = 'gui'
urlpatterns = [
    path('global/codes/manage/', views.GlobalCodesManageView.as_view(), name='global-codes-manage'),
    path('user/manage/', views.UserManageView.as_view(), name='user-manage'),
    path('group/manage/', views.GroupManageView.as_view(), name='group-manage')
]