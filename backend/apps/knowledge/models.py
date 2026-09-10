from django.db import models
from django.contrib.postgres.search import SearchVectorField
from pgvector.django import VectorField
from django.conf import settings

from apps.users.models import Tenant, User


class KnowledgeBase(models.Model):
    """知识库"""
    name = models.CharField(max_length=200, verbose_name="名称")
    desc = models.TextField(blank=True, default="", verbose_name="描述")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE,
                               related_name='kbs', verbose_name="租户")
    authorized_users = models.ManyToManyField(
        User, blank=True, related_name='authorized_kbs', verbose_name="授权用户")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "知识库"
        verbose_name_plural = "知识库"

    def __str__(self):
        return self.name

    def user_can_access(self, user) -> bool:
        if not user or not user.is_authenticated:
            return False
        if user.role == 'admin':
            return True
        if not self.authorized_users.exists():
            return True
        return self.authorized_users.filter(pk=user.pk).exists()


class Document(models.Model):
    """文档：上传的 pdf/docx 等"""
    STATUS = (
        ('pending', '待处理'),
        ('parsing', '解析中'),
        ('success', '成功'),
        ('fail', '失败'),
    )
    kb = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE, related_name="docs",
                          verbose_name="知识库")
    name = models.CharField(max_length=255, verbose_name="文件名")
    file_path = models.CharField(max_length=500, blank=True, verbose_name="存储路径")
    source_type = models.CharField(max_length=20, default="file", verbose_name="来源类型")
    status = models.CharField(max_length=20, choices=STATUS, default="pending", verbose_name="状态")
    error_msg = models.TextField(blank=True, default="", verbose_name="错误信息")
    char_count = models.IntegerField(default=0, verbose_name="字符数")
    has_images = models.BooleanField(default=False, verbose_name="含图片")
    has_tables = models.BooleanField(default=False, verbose_name="含表格")
    image_count = models.IntegerField(default=0, verbose_name="图片数")
    table_count = models.IntegerField(default=0, verbose_name="表格数")
    current_version = models.IntegerField(default=1, verbose_name="当前版本号")
    authorized_users = models.ManyToManyField(
        User, blank=True, related_name='authorized_docs', verbose_name="文档授权用户")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "文档"
        verbose_name_plural = "文档"

    def __str__(self):
        return self.name

    def user_can_access(self, user) -> bool:
        if not user or not user.is_authenticated:
            return False
        if user.role == 'admin':
            return True
        if self.authorized_users.exists():
            return self.authorized_users.filter(pk=user.pk).exists()
        return self.kb.user_can_access(user)


class DocumentVersion(models.Model):
    """文档版本历史：每次上传新版本时记录，支持回滚"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions',
                                  verbose_name="文档")
    version = models.IntegerField(default=1, verbose_name="版本号")
    file_path = models.CharField(max_length=500, verbose_name="文件存储路径")
    char_count = models.IntegerField(default=0, verbose_name="字符数")
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                  null=True, blank=True, verbose_name="上传者")
    remark = models.CharField(max_length=500, blank=True, default="", verbose_name="版本备注")
    is_current = models.BooleanField(default=False, verbose_name="是否当前版本")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")

    class Meta:
        verbose_name = "文档版本"
        verbose_name_plural = "文档版本"
        ordering = ['-version']
        unique_together = ('document', 'version')

    def __str__(self):
        return f'{self.document.name} v{self.version}'


class Paragraph(models.Model):
    """分段，对应每一块文本，存储向量"""
    BLOCK_TYPE = (
        ('text', '文本'),
        ('table', '表格'),
        ('image', '图片'),
    )
    doc = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="paragraphs",
                            verbose_name="文档")
    content = models.TextField(verbose_name="内容")
    vector = VectorField(dimensions=1024, null=True, blank=True, verbose_name="向量")
    search_vector = SearchVectorField(null=True, blank=True, verbose_name="全文检索向量")
    block_type = models.CharField(max_length=10, choices=BLOCK_TYPE, default='text',
                                   verbose_name="块类型")
    page_no = models.IntegerField(default=0, verbose_name="页码")
    index = models.IntegerField(default=0, verbose_name="段落序号")
    hit_count = models.IntegerField(default=0, verbose_name="命中次数")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "分段"
        verbose_name_plural = "分段"
        ordering = ['index']

    def __str__(self):
        return f'{self.doc.name}#{self.index}'
