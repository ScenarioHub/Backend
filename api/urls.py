from django.urls import path
from .views import *

urlpatterns = [
    # 인증 관련
    path('auth/register/', register),
    path('auth/login/', login),
    path('auth/refresh/', refresh_token),
    path('auth/logout/', logout),
    # 개인화 관련
    path('user/myscenario', my_scenario),
    # 시나리오 관련
    path('scenarios/maps/list', get_map_list),
    path('scenarios/maps/preview', get_map_preview),
    path('scenarios/<int:scenarioId>/video/', stream_video),
    path('scenarios/<int:scenarioId>/download/', download_file),
    # 생성 페이지
    # path('generator/generate/', start_generating_scenario),
    # 데모용 생성
    path('generator/generate/', start_generation),
    path('generator/<str:jobId>/state/', get_generating_state),
    path('generator/<str:jobId>/contents/', get_generated_data),
    path('generator/<str:jobId>/upload/', upload_from_generation),
    # 공유 페이지
    path('board/stats/', get_service_stats),
    path('board/explore', post_list),
    path('board/upload/', upload_post),
    path('board/<int:postId>/details/', post_detail),
    path('board/<int:postId>/video/', stream_video_board),
    path('board/<int:postId>/delete/', delete_post),
    path('board/<int:postId>/like/', toggle_like),
    path('board/<int:postId>/download/', download_file_board),
]
