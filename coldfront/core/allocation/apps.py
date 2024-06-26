from django.apps import AppConfig


class AllocationConfig(AppConfig):
    name = 'coldfront.core.allocation'

    def ready(self):
        import coldfront.core.allocation.signals
        import coldfront.core.allocation.signals_.renewal_signals
