from django.db import models


class TrainingSchedule(models.Model):
    CATEGORY_CHOICES = [
        ("Safety", "Safety"),
        ("Leadership", "Leadership"),
        ("Technical", "Technical"),
        ("Compliance", "Compliance"),
        ("Soft Skills", "Soft Skills"),
        ("Management", "Management"),
    ]
    STATUS_CHOICES = [
        ("Scheduled", "Scheduled"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
    ]
    course_name = models.CharField(max_length=255)
    course_category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    instructor = models.CharField(max_length=255)
    max_capacity = models.PositiveIntegerField()
    training_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration = models.DecimalField(max_digits=4, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Scheduled"
    )

    def __str__(self):
        return f"{self.course_name} ({self.training_date})"
