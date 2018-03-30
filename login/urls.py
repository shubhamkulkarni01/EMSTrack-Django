from django.conf.urls import url
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import views as auth_views
from login import views

app_name = 'login'
urlpatterns = [

    # login/logout
    url(r'^login/$',
        views.LoginView.as_view(),
        name='login'),
    url(r'^logout/$',
        views.LogoutView.as_view(),
        name='logout'),

    # signup
    url(r'^signup/$',
        views.SignupView.as_view(),
        name='signup'),
    
    # password change
    url(r'^password_change/$',
        auth_views.PasswordChangeView.as_view(),
        name='password_change'),
    url(r'^password_change/done/$',
        auth_views.PasswordChangeDoneView.as_view(),
        name='password_change_done'),
    
    # password reset
    url(r'^password_reset/$',
        auth_views.PasswordResetView.as_view(),
        name='password_reset'),
    url(r'^password_reset/done/$',
        auth_views.PasswordResetDoneView.as_view(),
        name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.PasswordResetConfirmView.as_view(),
        name='password_reset_confirm'),
    url(r'^reset/done/$',
        auth_views.PasswordResetCompleteView.as_view(),
        name='password_reset_complete'),

    # User Admin
    
    url(r'^user/$',
        staff_member_required(views.UserAdminListView.as_view()),
        name='user_list'),

    url(r'^user/create/$',
        staff_member_required(views.UserAdminCreateView.as_view()),
        name='user_create'),

    url(r'^user/detail/(?P<pk>[0-9]+)$',
        staff_member_required(views.UserAdminDetailView.as_view()),
        name='user_detail'),

    url(r'^user/update/(?P<pk>[0-9]+)$',
        staff_member_required(views.UserAdminUpdateView.as_view()),
        name='user_update'),

    # Group Admin

    url(r'^group/$',
        staff_member_required(views.GroupAdminListView.as_view()),
        name='group_list'),

    url(r'^group/create/$',
        staff_member_required(views.GroupAdminCreateView.as_view()),
        name='group_create'),

    url(r'^group/detail/(?P<pk>[0-9]+)$',
        staff_member_required(views.GroupAdminDetailView.as_view()),
        name='group_detail'),

    url(r'^group/update/(?P<pk>[0-9]+)$',
        staff_member_required(views.GroupAdminUpdateView.as_view()),
        name='group_update'),

    # client admin
    url(r'^client/$',
        staff_member_required(views.ClientListView.as_view()),
        name='client_list'),

    # restart

    url(r'^restart/$',
        views.RestartView.as_view(),
        name='restart'),

    # mqtt login
    
    url(r'^mqtt/login/$',
        views.MQTTLoginView.as_view(),
        name='mqtt_login'),
    url(r'^mqtt/superuser/$',
        views.MQTTSuperuserView.as_view(),
        name='mqtt_superuser'),
    url(r'^mqtt/acl/$',
        views.MQTTAclView.as_view(),
        name='mqtt_acl'),
    
]
