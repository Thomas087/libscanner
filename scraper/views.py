from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from .models import GovernmentDocument

def document_list(request):
    """
    View to display a paginated list of government documents.
    Filters for ICPE documents only and allows filtering by department.
    """
    # Get all ICPE documents, ordered by date_updated (already set in model Meta)
    documents = GovernmentDocument.objects.filter(is_icpe=True)
    
    # Get filter parameters
    department = request.GET.get('department', '')
    search = request.GET.get('search', '')
    
    # Apply filters
    if department:
        documents = documents.filter(prefecture_name__icontains=department)
    
    if search:
        documents = documents.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(documents, 20)  # 20 documents per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique departments for filter dropdown
    departments = GovernmentDocument.objects.filter(
        is_icpe=True,
        prefecture_name__isnull=False
    ).values_list('prefecture_name', flat=True).distinct().order_by('prefecture_name')
    
    context = {
        'page_obj': page_obj,
        'documents': page_obj,
        'departments': departments,
        'current_department': department,
        'current_search': search,
    }
    
    return render(request, 'scraper/document_list.html', context)
