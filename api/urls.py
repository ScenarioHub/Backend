from django.urls import path
from .views import scenario_detail, upload_post

urlpatterns = [
    path('scenario-detail/<int:id>/', scenario_detail),
    path('upload/post/', upload_post),
]
