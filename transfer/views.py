from django.views.generic import TemplateView

class DashboardView(TemplateView):
    template_name = "transfer/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transfers'] = [
            {'employee': 'John Doe', 'email': 'john.doe@company.com', 'type': 'DEPARTMENT', 'from': 'IT Department', 'to': 'HR Department', 'request_date': '2024-01-15', 'effective_date': '2024-02-01', 'status': 'PENDING'},
            {'employee': 'Jane Smith', 'email': 'jane.smith@company.com', 'type': 'POSITION', 'from': 'Software Developer', 'to': 'Senior Developer', 'request_date': '2024-01-10', 'effective_date': '2024-01-25', 'status': 'APPROVED'},
            {'employee': 'Mike Johnson', 'email': 'mike.johnson@company.com', 'type': 'LOCATION', 'from': 'New York Office', 'to': 'San Francisco', 'request_date': '2024-02-01', 'effective_date': '2024-02-15', 'status': 'REJECTED'},
        ]
        return context

class TransferRequestsView(TemplateView):
    template_name = "transfer/transfer_requests.html"

class PostingsView(TemplateView):
    template_name = "transfer/postings.html" 