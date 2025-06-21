from django.urls import path
from .views import TransferRequestsView, PostingsView

urlpatterns = [
    path('transfer-requests/', TransferRequestsView.as_view(), name='transfer-requests'),
    path('postings/', PostingsView.as_view(), name='postings'),
] 