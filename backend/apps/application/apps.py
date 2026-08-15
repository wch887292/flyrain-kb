from django.apps import AppConfig


class ApplicationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.application'
    label = 'application'
    verbose_name = 'AI 应用'
