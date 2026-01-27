from django.urls import path
from .views import register, login, post_list, scenario_detail, upload_post, download_file, stream_video, get_map_list, get_map_preview, my_scenario

urlpatterns = [
    path('auth/register/', register),
    path('auth/login/', login),
    path('upload/post/', upload_post),
    path('maps/list', get_map_list),
    path('maps/preview', get_map_preview),
    path('scenarios/explore', post_list),
    path('scenarios/<int:id>/details/', scenario_detail),
    path('scenarios/<int:id>/download/', download_file, name='scenario_download'),
    path('scenarios/<int:id>/video/', stream_video, name='scenario-video'),
    path('scenarios/myscenario', my_scenario, name='myscenario_list')
]