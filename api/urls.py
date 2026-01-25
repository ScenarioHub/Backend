from django.urls import path
from .views import register, login, post_list, scenario_detail, upload_post, xosc_download, stream_video

urlpatterns = [
    # 인증 관련
    path('auth/register/', register),
    path('auth/login/', login),
    # 시나리오 관련
    path('scenarios/explore', post_list, name='scenarios_explore_list'),
    path('scenarios/<int:id>/details/', scenario_detail, name='scenarios_details_list'),
    path('scenarios/<int:id>/download/', xosc_download.download_file, name='scenarios_download_list'),
    path('scenarios/<int:id>/video/', stream_video, name='scenarios_video_list'),
    # 업로드
    path('upload/post/', upload_post),
]