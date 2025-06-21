from django.urls import path

from training.views import (
    TrainingDashboardView,
    TrainingHistoryView,
    TrainingScheduleView,
)

urlpatterns = [
    path("dashboard/", TrainingDashboardView.as_view(), name="training-dashboard"),
    path("schedule/", TrainingScheduleView.as_view(), name="training-schedule"),
    path("history/", TrainingHistoryView.as_view(), name="training-history"),
]
