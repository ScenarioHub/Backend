from django.urls import path
from .views import scenario_detail

urlpatterns = [
    path('scenario-detail/<int:id>/', scenario_detail),
]
