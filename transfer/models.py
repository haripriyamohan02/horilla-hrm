from django.db import models
from base.models import Department

class Posting(models.Model):
    job_title = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    location = models.CharField(max_length=100)
    date_posted = models.DateField(auto_now_add=True)
    vacancy = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.job_title} ({self.department}) - {self.location}" 