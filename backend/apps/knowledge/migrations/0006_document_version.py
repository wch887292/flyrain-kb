from django.db import migrations, models
import django.db.models.deletion
import django.conf


class Migration(migrations.Migration):
    """文档版本管理：DocumentVersion 模型 + Document.current_version 字段。"""

    dependencies = [
        ('knowledge', '0005_document_auth'),
        migrations.swappable_dependency(django.conf.settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='current_version',
            field=models.IntegerField(default=1, verbose_name='当前版本号'),
        ),
        migrations.CreateModel(
            name='DocumentVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.IntegerField(default=1, verbose_name='版本号')),
                ('file_path', models.CharField(max_length=500, verbose_name='文件存储路径')),
                ('char_count', models.IntegerField(default=0, verbose_name='字符数')),
                ('remark', models.CharField(blank=True, default='', max_length=500, verbose_name='版本备注')),
                ('is_current', models.BooleanField(default=False, verbose_name='是否当前版本')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='上传时间')),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='knowledge.document', verbose_name='文档')),
                ('uploader', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=django.conf.settings.AUTH_USER_MODEL, verbose_name='上传者')),
            ],
            options={
                'verbose_name': '文档版本',
                'verbose_name_plural': '文档版本',
                'ordering': ['-version'],
                'unique_together': {('document', 'version')},
            },
        ),
    ]
