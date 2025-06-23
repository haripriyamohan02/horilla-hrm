from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy

class TravelDashboardView(TemplateView):
    template_name = "travel/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['applications'] = [
            {'employee': 'Alice Smith', 'destination': 'Delhi', 'date': '2024-06-10', 'status': 'Approved'},
            {'employee': 'John Doe', 'destination': 'Mumbai', 'date': '2024-06-15', 'status': 'Pending'},
            {'employee': 'Jane Lee', 'destination': 'Bangalore', 'date': '2024-06-18', 'status': 'Rejected'},
        ]
        return context

class TravelRequestView(LoginRequiredMixin, TemplateView):
    """Combined view for travel requests (both applying and approving)"""
    template_name = 'travel/requests.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Travel Requests')
        return context

    def post(self, request, *args, **kwargs):
        try:
            # Add your form processing logic here
            messages.success(request, _('Travel request created successfully'))
            return redirect('tourtravel:requests')
        except Exception as e:
            messages.error(request, str(e))
            return self.get(request, *args, **kwargs)

class TravelReimbursementView(TemplateView):
    template_name = "travel/reimbursement.html"

class LTARequestsView(TemplateView):
    template_name = 'travel/lta-requests.html'