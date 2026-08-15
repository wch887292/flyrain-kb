from django.apps import AppConfig


class ModelProviderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.model_provider'
    label = 'model_provider'
    verbose_name = '模型供应商'
