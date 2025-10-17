from django.apps import AppConfig


class ClusterStorageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'coldfront.plugins.cluster_storage'

    def ready(self):
        """Import signal handlers when the app is ready."""
        import coldfront.plugins.cluster_storage.signals
