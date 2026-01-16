from django.urls import path
from .views import register, login, post_list, scenario_detail, upload_post, download_file, stream_video

urlpatterns = [
    path('auth/register/', register),
    path('auth/login/', login),
    path('scenarios/explore/', post_list),
    path('scenario-detail/<int:id>/', scenario_detail),
    path('upload/post/', upload_post),
    path('scenarios/<int:id>/download/', download_file, name='scenario_download'),
    path('scenarios/<int:id>/video/', stream_video, name='scenario-video'),
]
