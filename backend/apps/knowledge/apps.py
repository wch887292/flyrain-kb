from django.apps import AppConfig


class KnowledgeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.knowledge'
    label = 'knowledge'
    verbose_name = '知识库'

    def ready(self):
        # 注册信号：Paragraph 保存时自动更新 search_vector
        import apps.knowledge.signals  # noqa: F401
