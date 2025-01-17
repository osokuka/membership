from .models import Lodge

def lodges_processor(request):
    """Make lodges available to all templates"""
    return {
        'all_lodges': Lodge.objects.all()
    } 