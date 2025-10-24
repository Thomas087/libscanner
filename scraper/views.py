from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from .models import GovernmentDocument

def document_list(request):
    """
    View to display a paginated list of government documents.
    Allows filtering by document type and department.
    """
    # Get all documents, ordered by date_updated (already set in model Meta)
    documents = GovernmentDocument.objects.all()
    
    # Get filter parameters
    department = request.GET.get('department', '')
    search = request.GET.get('search', '')
    
    # Document type filters - check if any filters are explicitly set
    intensive_param = request.GET.get('intensive')
    other_animal_param = request.GET.get('other_animal')
    other_docs_param = request.GET.get('other_docs')
    
    # If no filter parameters are provided, default to intensive farming only
    if not any([intensive_param, other_animal_param, other_docs_param]):
        show_intensive = True
        show_other_animal = False
        show_other_docs = False
    else:
        # Use the provided parameters, allowing all to be false
        show_intensive = intensive_param == 'true'
        show_other_animal = other_animal_param == 'true'
        show_other_docs = other_docs_param == 'true'
    
    # Apply document type filters
    type_filters = Q()
    if show_intensive:
        type_filters |= Q(is_intensive_farming=True)
    if show_other_animal:
        type_filters |= Q(is_animal_project=True, is_intensive_farming=False)
    if show_other_docs:
        type_filters |= Q(is_animal_project=False, is_intensive_farming=False)
    
    if type_filters:
        documents = documents.filter(type_filters)
    
    # Apply other filters
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
        prefecture_name__isnull=False
    ).values_list('prefecture_name', flat=True).distinct().order_by('prefecture_name')
    
    context = {
        'page_obj': page_obj,
        'documents': page_obj,
        'departments': departments,
        'current_department': department,
        'current_search': search,
        'show_intensive': show_intensive,
        'show_other_animal': show_other_animal,
        'show_other_docs': show_other_docs,
    }
    
    return render(request, 'scraper/document_list.html', context)
