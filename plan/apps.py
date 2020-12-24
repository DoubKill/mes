from django.apps import AppConfig


class PlanConfig(AppConfig):
    name = 'plan'

    def ready(self):
        from . import signals