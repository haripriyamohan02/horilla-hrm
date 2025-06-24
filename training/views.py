from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext as _
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
from .models import TrainingSchedule
from .serializers import TrainingScheduleSerializer


class TrainingDashboardView(TemplateView):
    template_name = "training/dashboard.html"


class TrainingScheduleView(TemplateView):
    template_name = "training/schedule.html"


class TrainingHistoryView(TemplateView):
    template_name = "training/history.html"


@api_view(["POST"])
@csrf_exempt  # Exempt CSRF for API endpoint
def create_training_schedule(request):
    try:
        # Handle JSON data
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.data

        serializer = TrainingScheduleSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )
    except json.JSONDecodeError:
        return Response(
            {"error": "Invalid JSON data"}, status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
