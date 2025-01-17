from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """Custom user model for enhanced functionality"""
    POSITION_CHOICES = [
        ('FNMM', 'Grand Master'),
        ('ZFNMM', 'Deputy Grand Master'),
        ('FMB1', 'Senior Grand Warden'),
        ('FNMB2', 'Grand Junior Warden'),
        ('FNS', 'Grand Secretary'),
        ('FNT', 'Grand Treasurer'),
        ('FNO', 'Grand Orator'),
        ('MN', 'Worshipful Master'),
        ('MB1', 'Senior Warden'),
        ('MB2', 'Junior Warden'),
        ('SE', 'Secretary'),
        ('TR', 'Treasurer'),
        ('OR', 'Orator'),
        ('Antare', 'Regular Member'),
    ]
    
    # Lodge and Position Information
    position = models.CharField(
        max_length=20,
        choices=POSITION_CHOICES,
        default='MEMBER'
    )
    is_dignitary = models.BooleanField(
        default=False,
        help_text="Indicates if the user is one of the three dignitaries"
    )
    is_senior_member = models.BooleanField(
        default=False,
        help_text="Senior members have additional privileges"
    )
    is_lodge_member = models.BooleanField(default=False)
    primary_lodge = models.ForeignKey(
        'Lodge',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_members'
    )
    
    # Contact Information
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
    
    def __str__(self):
        return f"{self.get_full_name()} - {self.get_position_display()}"
    
    @property
    def is_leadership(self):
        """Check if user holds a leadership position"""
        return self.position in ['FNMM', 'ZFNMM', 'FMB1', 'FNMB2', 'FNS', 'FNT', 'FNO', 'MN', 'MB1', 'MB2', 'SE', 'TR', 'OR']

    @property
    def full_name(self):
        """Returns the person's full name."""
        return f"{self.first_name} {self.last_name}"

class Candidate(models.Model):
    """Model for membership candidates"""
    STAGE_CHOICES = [
        ('APPLIED', 'Application Submitted'),
        ('DOCUMENTS', 'Document Review'),
        ('INTERVIEW', 'Interview Stage'),
        ('LODGE_REVIEW', 'Lodge Review'),
        ('VOTING', 'Final Voting'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    ]
    
    # Basic Information
    timestamp = models.DateTimeField(auto_now_add=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    is_kosovo_citizen = models.BooleanField(default=True)
    social_profile_url = models.URLField(blank=True) #alow multiple social media links  
    social_profile_url2 = models.URLField(blank=True)
    
    # Application Status
    current_stage = models.CharField(
        max_length=50,
        choices=STAGE_CHOICES,
        default='APPLIED'
    )
    application_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    # Interview Details
    interview_date = models.DateTimeField(null=True, blank=True)
    interview_passed = models.BooleanField(null=True, blank=True)
    
    class Meta:
        ordering = ['-application_date']
        
    def __str__(self):
        return f"{self.full_name} - {self.get_current_stage_display()}"
    
    def check_vote_status(self, stage):
        """Check voting status for the candidate at a specific stage"""
        return Vote.get_final_decision(self, stage)

class Lodge(models.Model):
    """Model for different lodges"""
    name = models.CharField(max_length=100)
    members = models.ManyToManyField(User, related_name='lodges')
    
    def __str__(self):
        return self.name

class Vote(models.Model):
    """Model for tracking votes on candidates"""
    VOTE_CHOICES = [
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
        ('ABSTAIN', 'Abstain'),
    ]
    
    VOTE_LEVEL = [
        ('LODGE', 'Lodge Level'),
        ('GRAND_LODGE', 'Grand Lodge Level'),
    ]
    
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    voter = models.ForeignKey(User, on_delete=models.CASCADE)
    lodge = models.ForeignKey(Lodge, on_delete=models.CASCADE)
    vote = models.CharField(max_length=10, choices=VOTE_CHOICES)
    vote_level = models.CharField(
        max_length=20, 
        choices=VOTE_LEVEL,
        default='LODGE'
    )
    stage = models.CharField(max_length=20, choices=Candidate.STAGE_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['candidate', 'voter', 'stage', 'vote_level']
        
    def __str__(self):
        return f"{self.candidate.full_name} - {self.vote} by {self.voter.username} ({self.get_vote_level_display()})"

    @classmethod
    def check_unanimous(cls, candidate, stage, vote_level):
        """Check if voting is unanimous for a candidate at a specific stage and level"""
        total_votes = cls.objects.filter(
            candidate=candidate,
            stage=stage,
            vote_level=vote_level
        ).exclude(vote='ABSTAIN').count()
        
        approve_votes = cls.objects.filter(
            candidate=candidate,
            stage=stage,
            vote_level=vote_level,
            vote='APPROVE'
        ).count()
        
        # If there are any votes and all votes are approvals
        return total_votes > 0 and total_votes == approve_votes

    @classmethod
    def get_final_decision(cls, candidate, stage):
        """
        Get final decision considering both lodge and grand lodge votes.
        Grand Lodge decision supersedes Lodge decision.
        """
        # Check Grand Lodge votes first
        grand_lodge_unanimous = cls.check_unanimous(candidate, stage, 'GRAND_LODGE')
        if cls.objects.filter(
            candidate=candidate,
            stage=stage,
            vote_level='GRAND_LODGE'
        ).exists():
            return grand_lodge_unanimous
        
        # If no Grand Lodge votes, check Lodge votes
        return cls.check_unanimous(candidate, stage, 'LODGE')

class Document(models.Model):
    """Model for candidate documents"""
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to='candidate_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.name} - {self.candidate.full_name}"

class MemberDocument(models.Model):
    """Model for storing member documents"""
    DOCUMENT_TYPES = [
        ('ID', 'ID Card'),
        ('PASSPORT', 'Passport'),
        ('CERTIFICATE', 'Certificate'),
        ('OTHER', 'Other Document'),
    ]
    
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='member_documents/')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_documents')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.member.get_full_name()} - {self.get_document_type_display()}"

class BulkUpload(models.Model):
    """Model for tracking bulk candidate uploads"""
    file = models.FileField(upload_to='bulk_uploads/')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='PENDING')
    processed_count = models.IntegerField(default=0)
    error_log = models.TextField(blank=True)
    
    def __str__(self):
        return f"Bulk Upload by {self.uploaded_by} on {self.uploaded_at}"
