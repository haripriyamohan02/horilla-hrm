from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.utils.translation import gettext as _
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404
import json
from training.models import TrainingSchedule
from .serializers import TrainingScheduleSerializer
from django.http import JsonResponse


class TrainingDashboardView(TemplateView):
    template_name = "training/dashboard.html"


class TrainingScheduleView(TemplateView):
    template_name = "training/schedule.html"


class TrainingHistoryView(TemplateView):
    template_name = "training/history.html"


@api_view(["POST"])
@csrf_exempt
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


@api_view(["GET"])
def get_all_training_schedules(request):
    """
    Retrieve all training schedules from the database
    """
    try:
        schedules: QuerySet[TrainingSchedule] = TrainingSchedule.objects.all().order_by(
            "training_date", "start_time"
        )
        serializer = TrainingScheduleSerializer(schedules, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
def delete_training_schedule(request, schedule_id):
    if request.method in ["DELETE", "POST"]:
        try:
            schedule = get_object_or_404(TrainingSchedule, id=schedule_id)
            course_name = schedule.course_name
            schedule.delete()
            return JsonResponse(
                {
                    "message": f"Training schedule '{course_name}' has been deleted successfully"
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return JsonResponse(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)
