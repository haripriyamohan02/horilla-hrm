from django.urls import path
from training import views
from training.views import (
    TrainingDashboardView,
    TrainingHistoryView,
    TrainingScheduleView,
)

urlpatterns = [
    path("dashboard/", TrainingDashboardView.as_view(), name="training-dashboard"),
    path("schedule/", TrainingScheduleView.as_view(), name="training-schedule"),
    path("history/", TrainingHistoryView.as_view(), name="training-history"),
    path(
        "api/create-schedule/",
        views.create_training_schedule,
        name="create_training_schedule",
    ),
    path(
        "api/get-all-schedules/",
        views.get_all_training_schedules,
        name="get_all_training_schedules",
    ),
]
