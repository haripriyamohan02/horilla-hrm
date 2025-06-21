from django.views.generic import TemplateView


class TrainingDashboardView(TemplateView):
    template_name = "training/dashboard.html"


class TrainingScheduleView(TemplateView):
    template_name = "training/schedule.html"


class TrainingHistoryView(TemplateView):
    template_name = "training/history.html"
