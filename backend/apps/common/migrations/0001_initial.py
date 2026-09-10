from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """common app 初始迁移：创建 AuditLog 审计日志模型。"""

    initial = True

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('login', '登录'), ('logout', '登出'), ('create', '创建'), ('update', '更新'), ('delete', '删除'), ('upload', '上传'), ('reparse', '重新解析'), ('chat', '对话'), ('other', '其他')], default='other', max_length=20, verbose_name='操作类型')),
                ('resource_type', models.CharField(blank=True, default='', max_length=50, verbose_name='资源类型')),
                ('resource_id', models.IntegerField(blank=True, null=True, verbose_name='资源ID')),
                ('detail', models.TextField(blank=True, default='', verbose_name='操作详情')),
                ('ip', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP地址')),
                ('path', models.CharField(blank=True, default='', max_length=255, verbose_name='请求路径')),
                ('method', models.CharField(blank=True, default='', max_length=10, verbose_name='请求方法')),
                ('status_code', models.IntegerField(blank=True, null=True, verbose_name='响应状态码')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='操作时间')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to='users.user', verbose_name='操作用户')),
            ],
            options={
                'verbose_name': '审计日志',
                'verbose_name_plural': '审计日志',
                'ordering': ['-create_time'],
            },
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['user', '-create_time'], name='common_audit_user_id_7c2c_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['action', '-create_time'], name='common_audit_action_3e2f_idx'),
        ),
    ]
