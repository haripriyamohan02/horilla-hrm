from django.urls import path
from .views import TransferRequestsView, PostingsView, DashboardView

urlpatterns = [
    path('transfer/dashboard/', DashboardView.as_view(), name='transfer-dashboard'),
    path('transfer-requests/', TransferRequestsView.as_view(), name='transfer-requests'),
    path('postings/', PostingsView.as_view(), name='postings'),
] 