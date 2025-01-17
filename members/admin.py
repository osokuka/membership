from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Candidate, Lodge, Vote, Document

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'get_full_name', 'position', 'primary_lodge', 'is_dignitary', 'is_senior_member')
    list_filter = ('position', 'is_dignitary', 'is_senior_member', 'primary_lodge')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    # Add custom fields to fieldsets
    fieldsets = UserAdmin.fieldsets + (
        ('Lodge Information', {
            'fields': ('position', 'is_dignitary', 'is_senior_member', 'is_lodge_member', 'primary_lodge')
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'address', 'city')
        }),
    )

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'current_stage', 'application_date', 'city', 'interview_date')
    list_filter = ('current_stage', 'city', 'is_kosovo_citizen')
    search_fields = ('full_name', 'email', 'phone_number')
    readonly_fields = ('timestamp', 'application_date', 'last_updated')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('full_name', 'email', 'phone_number', 'address', 'city', 'is_kosovo_citizen')
        }),
        ('Social Media', {
            'fields': ('social_profile_url', 'social_profile_url2')
        }),
        ('Application Status', {
            'fields': ('current_stage', 'application_date', 'last_updated')
        }),
        ('Interview Information', {
            'fields': ('interview_date', 'interview_passed')
        }),
    )

@admin.register(Lodge)
class LodgeAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_members_count')
    search_fields = ('name',)
    filter_horizontal = ('members',)
    
    def get_members_count(self, obj):
        return obj.members.count()
    get_members_count.short_description = 'Number of Members'

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'voter', 'lodge', 'vote', 'vote_level', 'stage', 'timestamp')
    list_filter = ('vote', 'vote_level', 'stage', 'lodge')
    search_fields = ('candidate__full_name', 'voter__username', 'comments')
    readonly_fields = ('timestamp',)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('name', 'candidate', 'uploaded_at', 'verified')
    list_filter = ('verified', 'uploaded_at')
    search_fields = ('name', 'candidate__full_name')
    readonly_fields = ('uploaded_at',)
