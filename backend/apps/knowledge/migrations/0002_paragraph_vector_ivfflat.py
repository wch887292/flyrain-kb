from django.db import migrations

# 为向量字段建立 ivfflat 索引，加速余弦相似度检索。
# search.py 使用 pgvector 的 CosineDistance（底层 <=> 运算符），
# 与 vector_cosine_ops 索引自动匹配，可被查询计划命中。
# lists 经验值：预期行数 / 1000（范围 1~1000）。数据量增长后可 REINDEX 调整。
SQL = """
CREATE INDEX IF NOT EXISTS knowledge_paragraph_vector_ivfflat_idx
ON knowledge_paragraph
USING ivfflat (vector vector_cosine_ops)
WITH (lists = 100);
"""

REVERSE_SQL = "DROP INDEX IF EXISTS knowledge_paragraph_vector_ivfflat_idx;"


class Migration(migrations.Migration):
    # ivfflat 建索引不应包裹在事务中
    atomic = False

    dependencies = [
        ('knowledge', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL),
    ]
