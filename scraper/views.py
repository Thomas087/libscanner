from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from .models import GovernmentDocument

def document_list(request):
    """
    View to display a paginated list of government documents.
    Two tabs: "Élevage animal" (animal farming projects) and "Autres documents".
    """
    documents = GovernmentDocument.objects.all()

    department = request.GET.get('department', '')
    search = request.GET.get('search', '')
    tab_param = request.GET.get('tab', 'animal')

    # tab=animal → Élevage animal (is_animal_farming_project=True)
    # tab=other → Autres documents (is_animal_farming_project=False)
    show_animal_farming = tab_param != 'other'

    if show_animal_farming:
        documents = documents.filter(is_animal_farming_project=True)
    else:
        documents = documents.filter(is_animal_farming_project=False)

    if department:
        documents = documents.filter(prefecture_name__icontains=department)

    if search:
        documents = documents.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )

    paginator = Paginator(documents, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    departments = GovernmentDocument.objects.filter(
        prefecture_name__isnull=False
    ).values_list('prefecture_name', flat=True).distinct().order_by('prefecture_name')

    context = {
        'page_obj': page_obj,
        'documents': page_obj,
        'departments': departments,
        'current_department': department,
        'current_search': search,
        'show_animal_farming': show_animal_farming,
    }

    return render(request, 'scraper/document_list.html', context)
