from django.views.generic import TemplateView

class TransferRequestsView(TemplateView):
    template_name = "transfer/transfer_requests.html"

class PostingsView(TemplateView):
    template_name = "transfer/postings.html" 