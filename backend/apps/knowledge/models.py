from django.db import models
from pgvector.django import VectorField

from apps.users.models import Tenant


class KnowledgeBase(models.Model):
    """知识库"""
    name = models.CharField(max_length=200, verbose_name="名称")
    desc = models.TextField(blank=True, default="", verbose_name="描述")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE,
                               related_name='kbs', verbose_name="租户")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "知识库"
        verbose_name_plural = "知识库"

    def __str__(self):
        return self.name


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
    source_type = models.CharField(max_length=20, default="file", verbose_name="来源类型")  # file / web
    status = models.CharField(max_length=20, choices=STATUS, default="pending", verbose_name="状态")
    error_msg = models.TextField(blank=True, default="", verbose_name="错误信息")
    char_count = models.IntegerField(default=0, verbose_name="字符数")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "文档"
        verbose_name_plural = "文档"

    def __str__(self):
        return self.name


class Paragraph(models.Model):
    """分段，对应每一块文本，存储向量"""
    doc = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="paragraphs",
                            verbose_name="文档")
    content = models.TextField(verbose_name="内容")
    vector = VectorField(dimensions=1024, null=True, blank=True, verbose_name="向量")
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
