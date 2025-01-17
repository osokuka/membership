from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    CustomLoginView, HomeView, ApplicantsListView, LodgeDetailView,
    ControlPanelView, MemberDocumentUploadView, BulkCandidateUploadView,
    MemberDocumentDeleteView, CandidateDetailView
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(
        template_name='registration/logged_out.html',
        next_page='login'
    ), name='logout'),
    path('applicants/', ApplicantsListView.as_view(), name='applicants'),
    path('applicant/<int:candidate_id>/', CandidateDetailView.as_view(), name='candidate_detail'),
    path('lodge/<int:lodge_id>/', LodgeDetailView.as_view(), name='lodge_detail'),
    
    # Control Panel URLs
    path('control-panel/', ControlPanelView.as_view(), name='control_panel'),
    path('control-panel/upload-document/', MemberDocumentUploadView.as_view(), name='upload_document'),
    path('control-panel/bulk-upload/', BulkCandidateUploadView.as_view(), name='bulk_upload'),
    path('control-panel/document/<int:pk>/delete/', MemberDocumentDeleteView.as_view(), name='delete_document'),
] 