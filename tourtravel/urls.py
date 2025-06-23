from django.urls import path
from . import views

app_name = 'tourtravel'

urlpatterns = [
    path('dashboard/', views.TravelDashboardView.as_view(), name='dashboard'),
    path('requests/', views.TravelRequestView.as_view(), name='requests'),
    path('reimbursement/', views.TravelReimbursementView.as_view(), name='reimbursement'),
    path('lta/applications/', views.LTAApplicationsView.as_view(), name='lta-applications'),
    path('lta/approvals/', views.LTAApprovalsView.as_view(), name='lta-approvals'),
] 