from django.urls import path
from .views import *

urlpatterns = [
    # 인증 관련
    path('auth/register/', register),
    path('auth/login/', login),
    path('auth/refresh/', refresh_token),
    path('auth/logout/', logout),
    # 시나리오 관련
    path('scenarios/explore', post_list, name='scenarios_explore_list'),
    path('scenarios/<int:id>/details/', scenario_detail, name='scenarios_details_list'),
    path('scenarios/<int:id>/download/', download_file, name='scenarios_download_list'),
    path('scenarios/<int:id>/video/', stream_video, name='scenarios_video_list'),
    path('scenarios/<int:id>/like/', toggle_like, name='scenarios_like'),
    path('scenarios/<int:id>/delete/', delete_post, name='scenarios_delete'),
    path('scenarios/myscenario', my_scenario, name='myscenario_list'),
    path('scenarios/stats/', get_scenario_stats, name='scenarios_stats'),
    # 업로드 관련
    path('upload/post/', upload_post, name='upload_post'),
    path('upload/data', get_scenario_data, name='data_from_generate'),
    path('upload/from_generation/', upload_from_generation, name='upload_from_generation'),
    # 지도 관련
    path('maps/list', get_map_list),
    path('maps/preview', get_map_preview),
    # 시나리오 생성 (비동기)
    path('generator/generate/', start_generate_scenario),
    path('generator/<str:jobId>/state/', get_generating_state),
]