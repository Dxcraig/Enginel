from django.apps import AppConfig


class DesignsConfig(AppConfig):
    name = 'designs'
    
    def ready(self):
        """Import signals when Django starts."""
        import designs.signals  # noqa
