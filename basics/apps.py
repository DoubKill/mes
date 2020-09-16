from django.apps import AppConfig


class BasicsConfig(AppConfig):
    name = 'basics'

    def ready(self):
        import basics.signals