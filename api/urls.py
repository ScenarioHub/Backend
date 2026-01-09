from django.urls import path
from .views import register, login, post_list, scenario_detail, upload_post

urlpatterns = [
    path('auth/register/', register),
    path('auth/login/', login),
    path('posts/', post_list),
    path('scenario-detail/<int:id>/', scenario_detail),
    path('upload/post/', upload_post),
]
