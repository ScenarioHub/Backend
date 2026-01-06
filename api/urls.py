from django.urls import path
from api.views import RegisterView, CustomLoginView, PostListView

urlpatterns = [
    #path('scenario-detail/<int:id>/', scenario_detail),
    path('auth/register/', RegisterView.as_view()),
    path('auth/login/', CustomLoginView.as_view()),
]
