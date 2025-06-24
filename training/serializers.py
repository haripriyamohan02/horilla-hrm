from rest_framework import serializers
from .models import TrainingSchedule


class TrainingScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingSchedule
        fields = "__all__"
