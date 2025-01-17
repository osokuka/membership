from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, CreateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Candidate, Lodge, MemberDocument, BulkUpload, User
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .mixins import SecretaryOrDignitaryRequiredMixin
from django.contrib import messages
import pandas as pd
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
import json
from django.core.exceptions import PermissionDenied

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('home')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_lodges'] = Lodge.objects.all()  # Add lodges to context for nav menu
        return context

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'members/home.html'
    login_url = 'login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_lodges'] = Lodge.objects.all()  # Add lodges to context for nav menu
        return context

class ApplicantsListView(LoginRequiredMixin, ListView):
    model = Candidate
    template_name = 'members/applicants.html'
    context_object_name = 'applicants'
    login_url = 'login'
    paginate_by = 10  # Default page size
    
    def get_paginate_by(self, queryset):
        # Get page size from request, default to 10
        return self.request.GET.get('page_size', self.paginate_by)
    
    def get_queryset(self):
        return Candidate.objects.all().order_by('-application_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stages'] = Candidate.STAGE_CHOICES
        context['all_lodges'] = Lodge.objects.all()
        context['page_sizes'] = [10, 20, 50, 100]
        context['current_page_size'] = int(self.request.GET.get('page_size', self.paginate_by))
        return context

class CandidateDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'members/candidate_detail.html'
    login_url = 'login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['candidate'] = get_object_or_404(Candidate, id=self.kwargs['candidate_id'])
        context['all_lodges'] = Lodge.objects.all()
        context['stages'] = Candidate.STAGE_CHOICES
        return context
    
    def post(self, request, *args, **kwargs):
        if not (request.user.is_secretary or request.user.is_senior_member):
            raise PermissionDenied
        
        candidate = get_object_or_404(Candidate, id=self.kwargs['candidate_id'])
        
        # Update candidate information
        candidate.full_name = request.POST.get('full_name', candidate.full_name)
        candidate.email = request.POST.get('email', candidate.email)
        candidate.phone_number = request.POST.get('phone_number', candidate.phone_number)
        candidate.city = request.POST.get('city', candidate.city)
        candidate.address = request.POST.get('address', candidate.address)
        candidate.social_profile_url = request.POST.get('social_profile_url', candidate.social_profile_url)
        candidate.current_stage = request.POST.get('current_stage', candidate.current_stage)
        candidate.is_kosovo_citizen = request.POST.get('is_kosovo_citizen') == 'on'
        
        try:
            candidate.save()
            messages.success(request, 'Candidate profile updated successfully.')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
        
        return redirect('candidate_detail', candidate_id=candidate.id)

class LodgeDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'members/lodge_detail.html'
    login_url = 'login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lodge'] = get_object_or_404(Lodge, id=self.kwargs['lodge_id'])
        context['all_lodges'] = Lodge.objects.all()  # Add lodges to context for nav menu
        return context

class ControlPanelView(SecretaryOrDignitaryRequiredMixin, TemplateView):
    template_name = 'members/control_panel.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_lodges'] = Lodge.objects.all()
        context['recent_documents'] = MemberDocument.objects.select_related('member', 'uploaded_by').order_by('-uploaded_at')[:10]
        context['recent_uploads'] = BulkUpload.objects.select_related('uploaded_by').order_by('-uploaded_at')[:5]
        return context

class MemberDocumentUploadView(SecretaryOrDignitaryRequiredMixin, CreateView):
    model = MemberDocument
    template_name = 'members/document_upload.html'
    fields = ['member', 'document_type', 'file', 'title', 'description']
    success_url = reverse_lazy('control_panel')
    
    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Document uploaded successfully.')
        return response

class BulkCandidateUploadView(SecretaryOrDignitaryRequiredMixin, CreateView):
    model = BulkUpload
    template_name = 'members/bulk_upload.html'
    fields = ['file']
    success_url = reverse_lazy('control_panel')
    
    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        
        try:
            # Read Excel file with all string columns to preserve leading zeros in phone numbers
            df = pd.read_excel(form.instance.file.path, dtype=str)
            
            # Trim column names and remove extra spaces
            df.columns = df.columns.str.strip()
            
            # Define required columns (using Albanian names)
            REQUIRED_COLUMNS = {
                'Emrin dhe Mbiemrin',
                'Email Address'
            }
            
            # Check for missing required columns (after trimming)
            missing_columns = REQUIRED_COLUMNS - set(df.columns)
            if missing_columns:
                raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
            
            # Process each row
            processed_count = 0
            skipped_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Clean and validate email
                    email = row['Email Address'].strip().lower() if pd.notna(row['Email Address']) else None
                    if not email:
                        errors.append(f"Row {index + 2}: Email is required")
                        continue
                    
                    # Check if candidate with this email already exists
                    if Candidate.objects.filter(email=email).exists():
                        skipped_count += 1
                        errors.append(f"Row {index + 2}: Candidate with email {email} already exists")
                        continue
                    
                    # Handle Kosovo citizenship
                    is_kosovo_citizen = True
                    if 'Jeni qytetar i Republikes së Kosoves?' in df.columns:
                        answer = str(row['Jeni qytetar i Republikes së Kosoves?']).strip().lower()
                        is_kosovo_citizen = answer in ['po', 'yes', 'true', '1']
                    
                    # Parse timestamp
                    application_date = None
                    if 'Timestamp' in df.columns:
                        try:
                            application_date = pd.to_datetime(row['Timestamp'])
                        except:
                            pass
                    
                    # Create new candidate
                    candidate_data = {
                        'email': email,
                        'full_name': row['Emrin dhe Mbiemrin'].strip() if pd.notna(row['Emrin dhe Mbiemrin']) else '',
                        'phone_number': str(row['Nr. e Telefonit']).strip() if 'Nr. e Telefonit' in df.columns and pd.notna(row['Nr. e Telefonit']) else '',
                        'address': row['Adresa'].strip() if 'Adresa' in df.columns and pd.notna(row['Adresa']) else '',
                        'city': row['Qyteti'].strip() if 'Qyteti' in df.columns and pd.notna(row['Qyteti']) else '',
                        'is_kosovo_citizen': is_kosovo_citizen,
                        'social_profile_url': row['Shto vegzën e profilit tuaj (LinkedIn, Facebook etj).'].strip() if 'Shto vegzën e profilit tuaj (LinkedIn, Facebook etj).' in df.columns and pd.notna(row['Shto vegzën e profilit tuaj (LinkedIn, Facebook etj).']) else '',
                        'current_stage': 'APPLIED'
                    }
                    
                    candidate = Candidate.objects.create(**candidate_data)
                    
                    # Update application date if available
                    if application_date:
                        candidate.application_date = application_date
                        candidate.save()
                    
                    processed_count += 1
                except Exception as e:
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            # Update upload status
            status_message = []
            if processed_count > 0:
                status_message.append(f"Successfully processed {processed_count} new candidates")
            if skipped_count > 0:
                status_message.append(f"Skipped {skipped_count} existing candidates")
            
            form.instance.processed_count = processed_count
            if errors:
                form.instance.status = 'COMPLETED_WITH_ERRORS'
                form.instance.error_log = '\n'.join(errors)
                messages.warning(self.request, f"{' | '.join(status_message)}. {len(errors)} errors found.")
            else:
                form.instance.status = 'COMPLETED'
                form.instance.error_log = 'All records processed successfully'
                messages.success(self.request, f"{' | '.join(status_message)}")
            
            form.instance.save()
                
        except Exception as e:
            form.instance.status = 'FAILED'
            form.instance.error_log = str(e)
            form.instance.save()
            messages.error(self.request, f'Failed to process file: {str(e)}')
        
        return response

@method_decorator(login_required, name='dispatch')
class MemberDocumentDeleteView(SecretaryOrDignitaryRequiredMixin, DeleteView):
    model = MemberDocument
    success_url = reverse_lazy('control_panel')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Document deleted successfully.')
        return super().delete(request, *args, **kwargs)
