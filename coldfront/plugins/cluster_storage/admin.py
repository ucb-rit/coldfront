from django.contrib import admin

from coldfront.plugins.cluster_storage.models import FacultyStorageAllocationRequest
from coldfront.plugins.cluster_storage.models import FacultyStorageAllocationRequestStatusChoice


@admin.register(FacultyStorageAllocationRequestStatusChoice)
class FacultyStorageAllocationRequestStatusChoiceAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(FacultyStorageAllocationRequest)
class FacultyStorageAllocationRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'project',
        'pi',
        'requester',
        'status',
        'requested_amount_gb',
        'approved_amount_gb',
        'request_time',
        'completion_time',
    )
    list_filter = ('status', 'request_time', 'completion_time')
    search_fields = (
        'project__name',
        'pi__username',
        'pi__first_name',
        'pi__last_name',
        'requester__username',
        'requester__first_name',
        'requester__last_name',
    )
    readonly_fields = (
        'request_time',
        'approval_time',
        'completion_time',
        'created',
        'modified',
        'state',
    )
    fieldsets = (
        ('Request Information', {
            'fields': (
                'status',
                'project',
                'requester',
                'pi',
            )
        }),
        ('Storage Amounts', {
            'fields': (
                'requested_amount_gb',
                'approved_amount_gb',
            )
        }),
        ('Timestamps', {
            'fields': (
                'request_time',
                'approval_time',
                'completion_time',
                'created',
                'modified',
            )
        }),
        ('State (JSON)', {
            'fields': ('state',),
            'classes': ('collapse',),
        }),
    )
    date_hierarchy = 'request_time'
    ordering = ('-request_time',)
