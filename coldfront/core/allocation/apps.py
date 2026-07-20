from django.apps import AppConfig


class AllocationConfig(AppConfig):
    name = "coldfront.core.allocation"

    def ready(self):
        import coldfront.core.allocation.signals  # noqa: F401
        import coldfront.core.allocation.signals_.renewal_signals  # noqa: F401
