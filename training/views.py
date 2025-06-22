from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext as _


class TrainingDashboardView(TemplateView):
    template_name = "training/dashboard.html"


class TrainingScheduleView(TemplateView):
    template_name = "training/schedule.html"


class TrainingHistoryView(TemplateView):
    template_name = "training/history.html"


class CreateTrainingScheduleView(TemplateView):
    template_name = "training/schedule.html"

    def post(self, request, *args, **kwargs):
        # Extract form data
        course_name = request.POST.get("course_name")
        course_category = request.POST.get("course_category")
        course_description = request.POST.get("course_description")
        training_date = request.POST.get("training_date")
        duration = request.POST.get("duration")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")
        location = request.POST.get("location")
        instructor = request.POST.get("instructor")
        max_capacity = request.POST.get("max_capacity")
        prerequisites = request.POST.get("prerequisites")
        materials = request.POST.get("materials")
        registration_deadline = request.POST.get("registration_deadline")
        cost = request.POST.get("cost")
        certification_provided = request.POST.get("certification_provided") == "1"
        mandatory_training = request.POST.get("mandatory_training") == "1"
        recurring_training = request.POST.get("recurring_training") == "1"

        # Here you would typically save to your database
        # For now, we'll just show a success message

        # Example validation
        if not all(
            [
                course_name,
                course_category,
                training_date,
                duration,
                start_time,
                end_time,
                location,
                instructor,
                max_capacity,
            ]
        ):
            messages.error(request, _("Please fill in all required fields."))
            return self.get(request, *args, **kwargs)

        # TODO: Save to database
        # training_schedule = TrainingSchedule.objects.create(
        #     course_name=course_name,
        #     course_category=course_category,
        #     course_description=course_description,
        #     training_date=training_date,
        #     duration=duration,
        #     start_time=start_time,
        #     end_time=end_time,
        #     location=location,
        #     instructor=instructor,
        #     max_capacity=max_capacity,
        #     prerequisites=prerequisites,
        #     materials=materials,
        #     registration_deadline=registration_deadline,
        #     cost=cost,
        #     certification_provided=certification_provided,
        #     mandatory_training=mandatory_training,
        #     recurring_training=recurring_training,
        # )

        messages.success(request, _("Training schedule created successfully!"))
        return HttpResponseRedirect(reverse("training-schedule"))
