from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import GovernmentDocument, NegativeKeyword, ScrapingTask, ScrapingTaskResult
from .constants import ANIMAL_KEYWORDS
from .tasks import scrape_animal_keywords_enhanced_task


@admin.register(GovernmentDocument)
class GovernmentDocumentAdmin(admin.ModelAdmin):
    """Admin interface for GovernmentDocument model."""
    
    list_display = [
        'title_short', 
        'prefecture_name',
        'region_name',
        'date_updated', 
        'is_recent_display',
        'is_animal_farming_project_display',
        'animal_type_display',
        'animal_number_display',
        'link_display', 
        'created_at'
    ]
    
    list_filter = [
        'is_animal_farming_project',
        'animal_type',
        'prefecture_name',
        'region_name',
        'date_updated',
        'created_at',
        'updated_at',
    ]
    
    search_fields = [
        'title',
        'description',
        'link',
        'animal_type',
        'prefecture_name',
        'region_name',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'link_display',
        'is_recent_display',
        'full_page_text',
        'summary_display',
    ]
    
    fieldsets = (
        ('Document Information', {
            'fields': ('title', 'description', 'link_display')
        }),
        ('Content', {
            'fields': ('summary_display', 'summary', 'full_page_text'),
            'classes': ('collapse',)
        }),
        ('Prefecture Information', {
            'fields': ('prefecture_name', 'prefecture_code', 'region_name')
        }),
        ('Dates', {
            'fields': ('date_updated', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_recent_display',),
            'classes': ('collapse',)
        }),
        ('Animal Project Information', {
            'fields': ('is_animal_farming_project', 'animal_type', 'animal_number'),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 25
    ordering = ['-date_updated']
    
    def title_short(self, obj):
        """Display truncated title for list view."""
        if len(obj.title) > 60:
            return f"{obj.title[:60]}..."
        return obj.title
    title_short.short_description = "Title"
    title_short.admin_order_field = "title"
    
    def link_display(self, obj):
        """Display link as clickable URL."""
        if obj.link:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
                obj.link,
                "View Document"
            )
        return "No link"
    link_display.short_description = "Link"
    
    def is_recent_display(self, obj):
        """Display if document is recent with color coding."""
        is_recent = obj.is_recent()
        if is_recent:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Recent</span>'
            )
        else:
            return format_html(
                '<span style="color: orange;">Older</span>'
            )
    is_recent_display.short_description = "Recent"
    is_recent_display.admin_order_field = "date_updated"
    
    
    def is_animal_farming_project_display(self, obj):
        """Display animal farming project status with color coding."""
        if obj.is_animal_farming_project:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">🐄 Animal Farming Project</span>'
            )
        else:
            return format_html(
                '<span style="color: #6c757d;">General</span>'
            )
    is_animal_farming_project_display.short_description = "Animal Farming Project"
    is_animal_farming_project_display.admin_order_field = "is_animal_farming_project"
    
    def animal_type_display(self, obj):
        """Display animal type with formatting."""
        if obj.animal_type:
            return format_html(
                '<span style="color: #007bff; font-weight: bold;">{}</span>',
                obj.animal_type
            )
        else:
            return format_html(
                '<span style="color: #6c757d;">N/A</span>'
            )
    animal_type_display.short_description = "Animal Type"
    animal_type_display.admin_order_field = "animal_type"
    
    def animal_number_display(self, obj):
        """Display animal number with formatting."""
        if obj.animal_number is not None:
            try:
                # Try to convert to int, handling both numeric and string values
                number = int(float(str(obj.animal_number)))
                return format_html(
                    '<span style="color: #17a2b8; font-weight: bold;">{:,}</span>',
                    number
                )
            except (ValueError, TypeError):
                # If conversion fails, show the raw value or N/A
                return format_html(
                    '<span style="color: #6c757d;">{}</span>',
                    str(obj.animal_number) if obj.animal_number else 'N/A'
                )
        else:
            return format_html(
                '<span style="color: #6c757d;">N/A</span>'
            )
    animal_number_display.short_description = "Animal Count"
    animal_number_display.admin_order_field = "animal_number"
    
    def summary_display(self, obj):
        """Display formatted summary of the document."""
        if obj.summary:
            # Truncate summary if it's too long for better display
            summary_text = obj.summary
            if len(summary_text) > 500:
                summary_text = summary_text[:500] + "..."
            
            return format_html(
                '<div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #007bff; margin: 10px 0;">'
                '<h4 style="margin-top: 0; color: #007bff; font-size: 16px;">📄 Document Summary</h4>'
                '<p style="margin-bottom: 0; line-height: 1.5; color: #333;">{}</p>'
                '</div>',
                summary_text
            )
        else:
            return format_html(
                '<div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107; margin: 10px 0;">'
                '<p style="margin: 0; color: #856404; font-style: italic;">⚠️ No summary available for this document</p>'
                '</div>'
            )
    summary_display.short_description = "Document Summary"
    
    def get_queryset(self, request):
        """Optimize queryset for admin."""
        return super().get_queryset(request).select_related()
    
    def has_add_permission(self, request):
        """Allow adding documents manually."""
        return True
    
    def has_change_permission(self, request, obj=None):
        """Allow editing documents."""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Allow deleting documents."""
        return True


@admin.register(NegativeKeyword)
class NegativeKeywordAdmin(admin.ModelAdmin):
    """Admin interface for NegativeKeyword model."""
    
    list_display = [
        'keyword',
        'created_at',
        'updated_at'
    ]
    
    list_filter = [
        'created_at',
        'updated_at',
    ]
    
    search_fields = [
        'keyword',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Keyword Information', {
            'fields': ('keyword',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 25
    ordering = ['keyword']
    
    def get_urls(self):
        """Add custom URLs for cleanup action."""
        urls = super().get_urls()
        custom_urls = [
            path('cleanup-documents/', self.admin_site.admin_view(self.cleanup_documents_view), name='scraper_negativekeyword_cleanup'),
        ]
        return custom_urls + urls
    
    def cleanup_documents_view(self, request):
        """View to clean up documents containing negative keywords."""
        try:
            from .analysis import remove_documents_with_negative_keywords
            
            # Get the number of documents before cleanup
            from .models import GovernmentDocument
            total_docs_before = GovernmentDocument.objects.count()
            
            # Run the cleanup (removes ALL documents with negative keywords, regardless of age)
            removed_count = remove_documents_with_negative_keywords()
            
            # Get the number of documents after cleanup
            total_docs_after = GovernmentDocument.objects.count()
            
            if removed_count > 0:
                messages.success(request, f'Successfully removed {removed_count} documents containing negative keywords.')
                messages.info(request, f'Database now contains {total_docs_after} documents (was {total_docs_before}).')
                messages.warning(request, 'All documents containing negative keywords have been removed, regardless of their age.')
            else:
                messages.info(request, 'No documents containing negative keywords were found.')
            
            return redirect('admin:scraper_negativekeyword_changelist')
            
        except Exception as e:
            messages.error(request, f'Failed to cleanup documents: {str(e)}')
            return redirect('admin:scraper_negativekeyword_changelist')
    
    def changelist_view(self, request, extra_context=None):
        """Override changelist to add custom context for the cleanup button."""
        extra_context = extra_context or {}
        extra_context['show_cleanup_button'] = True
        return super().changelist_view(request, extra_context=extra_context)
    
    def get_queryset(self, request):
        """Optimize queryset for admin."""
        return super().get_queryset(request)
    
    def has_add_permission(self, request):
        """Allow adding negative keywords manually."""
        return True
    
    def has_change_permission(self, request, obj=None):
        """Allow editing negative keywords."""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Allow deleting negative keywords."""
        return True


class ScrapingTaskResultInline(admin.TabularInline):
    """Inline admin for ScrapingTaskResult."""
    model = ScrapingTaskResult
    extra = 0
    readonly_fields = ['prefecture_name', 'region_name', 'keyword', 'items_found', 'created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ScrapingTask)
class ScrapingTaskAdmin(admin.ModelAdmin):
    """Admin interface for ScrapingTask model."""
    
    list_display = [
        'task_id_short',
        'name',
        'status_display',
        'days_limit_display',
        'progress_display',
        'current_operation_display',
        'total_items_found',
        'created_at',
        'duration_display',
        'action_buttons'
    ]
    
    list_filter = [
        'status',
        'name',
        'created_at',
        'started_at',
        'completed_at',
    ]
    
    search_fields = [
        'task_id',
        'name',
        'current_prefecture',
        'current_keyword',
        'region_filter',
        'prefecture_filter',
    ]
    
    readonly_fields = [
        'task_id',
        'created_at',
        'started_at',
        'completed_at',
        'last_updated',
        'progress_percentage',
        'duration_display',
        'status_display',
        'current_operation_display',
        'results_summary_display',
        'error_message',
        'traceback',
    ]
    
    fieldsets = (
        ('Task Information', {
            'fields': ('task_id', 'name', 'status_display', 'created_at', 'started_at', 'completed_at', 'last_updated')
        }),
        ('Parameters', {
            'fields': ('keywords', 'region_filter', 'prefecture_filter', 'output_file', 'output_format', 'days_limit')
        }),
        ('Progress', {
            'fields': ('current_operation_display', 'progress_percentage', 'current_prefecture', 'current_keyword')
        }),
        ('Results', {
            'fields': ('total_items_found', 'results_summary_display'),
            'classes': ('collapse',)
        }),
        ('Error Information', {
            'fields': ('error_message', 'traceback'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ScrapingTaskResultInline]
    
    actions = ['start_animal_keywords_task', 'force_stop_selected_tasks']

    # Don't show actions dropdown if no items are selected
    def changelist_view(self, request, extra_context=None):
        """Override changelist to hide the action dropdown since we have custom buttons."""
        extra_context = extra_context or {}
        # We keep actions for the form submission but can customize the display
        return super().changelist_view(request, extra_context=extra_context)
    
    list_per_page = 25
    ordering = ['-created_at']
    
    def get_urls(self):
        """Add custom URLs for task actions."""
        urls = super().get_urls()
        custom_urls = [
            path('start-animal-keywords/', self.admin_site.admin_view(self.start_animal_keywords_view), name='scraper_scrapingtask_start_animal'),
            path('stop-task/<int:task_id>/', self.admin_site.admin_view(self.stop_task), name='scraper_scrapingtask_stop'),
            path('task-progress/<int:task_id>/', self.admin_site.admin_view(self.task_progress), name='scraper_scrapingtask_progress'),
        ]
        return custom_urls + urls

    def start_animal_keywords_view(self, request):
        """View to start the default animal keywords task."""
        try:
            # Check if there are any running tasks
            running_tasks = ScrapingTask.objects.filter(status__in=['PENDING', 'PROGRESS'])
            if running_tasks.exists():
                messages.warning(request, f'There are {running_tasks.count()} task(s) already running. Please wait for them to complete or stop them first.')
                return redirect('admin:scraper_scrapingtask_changelist')

            # Get days_limit from request parameters (default to 30)
            try:
                days_limit = int(request.GET.get('days_limit', 30))
                # Validate range
                if days_limit < 1:
                    days_limit = 1
                elif days_limit > 365:
                    days_limit = 365
            except (ValueError, TypeError):
                days_limit = 30

            keywords = list(ANIMAL_KEYWORDS)

            # Create task record
            task = ScrapingTask.objects.create(
                keywords=keywords,
                output_format='pretty',
                days_limit=days_limit
            )

            # Start Celery task
            celery_task = scrape_animal_keywords_enhanced_task.delay(
                task_id=task.id,
                keywords=keywords,
                output_format='pretty',
                days_limit=days_limit
            )

            # Update task record with Celery task ID
            task.task_id = celery_task.id
            task.started_at = timezone.now()
            task.save()

            messages.success(request, f'Animal keywords scraping task started! Task ID: {task.id}')
            messages.info(request, f'Keywords: {", ".join(keywords)}')
            messages.info(request, f'Time range: {days_limit} days')
            messages.info(request, 'You can monitor the progress in the task list below.')
            return redirect('admin:scraper_scrapingtask_changelist')

        except Exception as e:
            messages.error(request, f'Failed to start animal keywords task: {str(e)}')
            return redirect('admin:scraper_scrapingtask_changelist')
    
    def stop_task(self, request, task_id):
        """Force stop a running task completely."""
        try:
            task = ScrapingTask.objects.get(id=task_id)
            
            # Use the enhanced force_stop method
            success = task.force_stop()
            
            if success:
                messages.success(request, f'Task {task_id} has been force-stopped completely.')
                messages.info(request, 'The task and any associated worker processes have been terminated.')
            else:
                messages.warning(request, f'Task {task_id} has been marked as stopped, but some processes may still be running.')
                messages.info(request, 'You may need to restart Celery workers if they become unresponsive.')
            
            return redirect('admin:scraper_scrapingtask_changelist')
            
        except ScrapingTask.DoesNotExist:
            messages.error(request, f'Task {task_id} not found.')
            return redirect('admin:scraper_scrapingtask_changelist')
        except Exception as e:
            messages.error(request, f'Failed to force-stop task: {str(e)}')
            return redirect('admin:scraper_scrapingtask_changelist')
    
    def task_progress(self, request, task_id):
        """Get task progress as JSON."""
        try:
            task = ScrapingTask.objects.get(id=task_id)
            return JsonResponse({
                'status': task.status,
                'progress_percentage': task.progress_percentage,
                'current_operation': task.current_operation,
                'total_operations': task.total_operations,
                'current_prefecture': task.current_prefecture,
                'current_keyword': task.current_keyword,
                'total_items_found': task.total_items_found,
            })
        except ScrapingTask.DoesNotExist:
            return JsonResponse({'error': 'Task not found'}, status=404)
    
    def task_id_short(self, obj):
        """Display shortened task ID."""
        if len(obj.task_id) > 20:
            return f"{obj.task_id[:20]}..."
        return obj.task_id
    task_id_short.short_description = "Task ID"
    task_id_short.admin_order_field = "task_id"
    
    def days_limit_display(self, obj):
        """Display days limit with formatting."""
        return format_html(
            '<span style="color: #17a2b8;">{} days</span>',
            obj.days_limit
        )
    days_limit_display.short_description = "Time Range"
    days_limit_display.admin_order_field = "days_limit"
    
    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            'PENDING': 'orange',
            'PROGRESS': 'blue',
            'SUCCESS': 'green',
            'FAILURE': 'red',
            'REVOKED': 'gray',
            'RETRY': 'purple',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Status"
    status_display.admin_order_field = "status"
    
    def progress_display(self, obj):
        """Display progress bar."""
        if obj.total_operations == 0:
            return "N/A"
        
        percentage = obj.progress_percentage
        color = "green" if percentage >= 80 else "blue" if percentage >= 50 else "orange"
        
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; text-align: center; color: white; font-size: 12px; line-height: 20px;">{}%</div>'
            '</div>',
            percentage,
            color,
            f"{percentage:.1f}"
        )
    progress_display.short_description = "Progress"
    
    def current_operation_display(self, obj):
        """Display current operation."""
        if obj.total_operations == 0:
            return "N/A"
        return f"{obj.current_operation}/{obj.total_operations}"
    current_operation_display.short_description = "Operations"
    
    def duration_display(self, obj):
        """Display task duration."""
        duration = obj.duration
        if duration:
            total_seconds = int(duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        return "N/A"
    duration_display.short_description = "Duration"
    
    def results_summary_display(self, obj):
        """Display results summary."""
        if obj.results_summary:
            summary = obj.results_summary
            return format_html(
                '<strong>Total Items:</strong> {}<br>'
                '<strong>Prefectures:</strong> {}<br>'
                '<strong>Keywords:</strong> {}<br>'
                '<strong>Operations:</strong> {}',
                summary.get('total_items', 0),
                summary.get('total_prefectures', 0),
                summary.get('total_keywords', 0),
                summary.get('total_operations', 0)
            )
        return "No results yet"
    results_summary_display.short_description = "Results Summary"
    
    def action_buttons(self, obj):
        """Display action buttons."""
        buttons = []
        
        if obj.status == 'PROGRESS':
            stop_url = reverse('admin:scraper_scrapingtask_stop', args=[obj.id])
            buttons.append(
                format_html(
                    '<a href="{}" class="button force-btn" style="background-color: #dc3545; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; font-weight: 600; border: 1px solid #dc3545; transition: all 0.2s ease; display: inline-block;" onclick="return confirm(\'Are you sure you want to FORCE STOP this task? This will terminate the worker process.\')">Stop</a>',
                    stop_url
                )
            )
        
        return format_html(' '.join(buttons)) if buttons else "No actions"
    action_buttons.short_description = "Actions"

    def start_animal_keywords_task(self, request, queryset):
        """Admin action to start the default animal keywords task."""
        try:
            # Check if there are any running tasks
            running_tasks = ScrapingTask.objects.filter(status__in=['PENDING', 'PROGRESS'])
            if running_tasks.exists():
                messages.warning(request, f'There are {running_tasks.count()} task(s) already running. Please wait for them to complete or stop them first.')
                return redirect('admin:scraper_scrapingtask_changelist')
            
            # Default values
            days_limit = 30  # Default for admin action
            
            keywords = list(ANIMAL_KEYWORDS)

            # Create task record
            task = ScrapingTask.objects.create(
                keywords=keywords,
                output_format='pretty',
                days_limit=days_limit
            )

            # Start Celery task
            celery_task = scrape_animal_keywords_enhanced_task.delay(
                task_id=task.id,
                keywords=keywords,
                output_format='pretty',
                days_limit=days_limit
            )
            
            # Update task record with Celery task ID
            task.task_id = celery_task.id
            task.started_at = timezone.now()
            task.save()
            
            messages.success(request, f'Animal keywords scraping task started! Task ID: {task.id}')
            messages.info(request, f'Keywords: {", ".join(keywords)}')
            messages.info(request, f'Time range: {days_limit} days')
            messages.info(request, 'You can monitor the progress in the task list below.')
            return redirect('admin:scraper_scrapingtask_changelist')
            
        except Exception as e:
            messages.error(request, f'Failed to start animal keywords task: {str(e)}')
            return redirect('admin:scraper_scrapingtask_changelist')
    start_animal_keywords_task.short_description = "Scrape Animal Keywords"
    
    def force_stop_selected_tasks(self, request, queryset):
        """Admin action to force stop selected tasks."""
        stopped_count = 0
        failed_count = 0
        
        for task in queryset:
            if task.status in ['PENDING', 'PROGRESS']:
                try:
                    success = task.force_stop()
                    if success:
                        stopped_count += 1
                    else:
                        failed_count += 1
                except Exception:
                    failed_count += 1
            else:
                # Task is not running, skip it
                continue
        
        if stopped_count > 0:
            messages.success(request, f'Successfully force-stopped {stopped_count} task(s).')
        if failed_count > 0:
            messages.warning(request, f'Failed to force-stop {failed_count} task(s).')
        if stopped_count == 0 and failed_count == 0:
            messages.info(request, 'No running tasks were selected.')
    
    force_stop_selected_tasks.short_description = "🛑 Force Stop Selected Tasks"
    
    def has_add_permission(self, request):
        """Disable adding tasks manually - use 'Scrape Animal Keywords' button instead."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Allow editing tasks."""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Allow deleting tasks."""
        return True


@admin.register(ScrapingTaskResult)
class ScrapingTaskResultAdmin(admin.ModelAdmin):
    """Admin interface for ScrapingTaskResult model."""
    
    list_display = [
        'task_name',
        'prefecture_name',
        'region_name',
        'keyword',
        'items_found',
        'created_at'
    ]
    
    list_filter = [
        'task__name',
        'prefecture_name',
        'region_name',
        'keyword',
        'created_at',
    ]
    
    search_fields = [
        'task__name',
        'prefecture_name',
        'region_name',
        'keyword',
    ]
    
    readonly_fields = [
        'task',
        'prefecture_name',
        'region_name',
        'keyword',
        'items_found',
        'created_at'
    ]
    
    fieldsets = (
        ('Result Information', {
            'fields': ('task', 'prefecture_name', 'region_name', 'keyword', 'items_found')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 25
    ordering = ['-items_found', 'prefecture_name', 'keyword']
    
    def task_name(self, obj):
        """Display task name."""
        return obj.task.name
    task_name.short_description = "Task"
    task_name.admin_order_field = "task__name"
    
    def has_add_permission(self, request):
        """Prevent manual addition of results."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing results."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deleting results."""
        return True
