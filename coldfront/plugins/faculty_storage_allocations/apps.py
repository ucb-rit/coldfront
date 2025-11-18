from django.apps import AppConfig


class FacultyStorageAllocationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'coldfront.plugins.faculty_storage_allocations'

    def ready(self):
        """Import signal handlers when the app is ready."""
        import coldfront.plugins.faculty_storage_allocations.signals
