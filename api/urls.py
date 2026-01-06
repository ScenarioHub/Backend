from django.urls import path
from .views import RegisterView, CustomLoginView, PostListView, scenario_detail, upload_post

urlpatterns = [
    path('auth/register/', RegisterView.as_view()),
    path('auth/login/', CustomLoginView.as_view()),
    path('posts/', PostListView.as_view()),
    path('scenario-detail/<int:id>/', scenario_detail),
    path('upload/post/', upload_post),
]
