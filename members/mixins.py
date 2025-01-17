from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class SecretaryOrDignitaryRequiredMixin(UserPassesTestMixin):
    """Verify that the current user is a secretary or senior dignitary"""
    
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
            
        # Check if user is a secretary (SE) or senior dignitary
        is_secretary = self.request.user.position == 'SE'
        is_dignitary = self.request.user.is_dignitary
        is_senior_member = self.request.user.is_senior_member
        
        return is_secretary or is_dignitary or is_senior_member
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("You don't have permission to access this page.")
        return super().handle_no_permission() 