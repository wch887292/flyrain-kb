from django.db import migrations
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class Migration(migrations.Migration):
    """为 Paragraph 添加全文检索向量字段 + GIN 索引，替代 icontains 全表扫描。"""

    dependencies = [
        ('knowledge', '0002_paragraph_vector_ivfflat'),
    ]

    operations = [
        migrations.AddField(
            model_name='paragraph',
            name='search_vector',
            field=SearchVectorField(null=True, blank=True, verbose_name='全文检索向量'),
        ),
        # GIN 索引加速 tsvector 全文匹配（@@ 运算符 / SearchQuery）
        migrations.AddIndex(
            model_name='paragraph',
            index=GinIndex(fields=['search_vector'], name='knowledge_para_search_vec_gin'),
        ),
        # 对已有数据回填 search_vector（content 字段的英文+数字分词；中文需 pg_jieba 等扩展，
        # 未安装时 PostgreSQL 默认分词器对中文按单字切分，仍可命中但精度有限）
        migrations.RunSQL(
            sql="""
            UPDATE knowledge_paragraph
            SET search_vector = to_tsvector('simple', COALESCE(content, ''))
            WHERE search_vector IS NULL;
            """,
            reverse_sql="UPDATE knowledge_paragraph SET search_vector = NULL;",
        ),
    ]
