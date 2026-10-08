from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.conf import settings

from apps.users.models import Tenant
from apps.knowledge.models import KnowledgeBase


class Application(models.Model):
    """AI 助手应用：绑定知识库 + Prompt 配置"""
    name = models.CharField(max_length=200, verbose_name="名称")
    desc = models.TextField(blank=True, default="", verbose_name="描述")
    kbs = models.ManyToManyField(KnowledgeBase, blank=True, related_name='apps',
                                 verbose_name="关联知识库")
    system_prompt = models.TextField(
        blank=True, default="你是一个基于企业知识库作答的助手，请只依据给定资料回答。",
        verbose_name="系统提示词")
    temperature = models.FloatField(default=0.7, verbose_name="温度")
    max_tokens = models.IntegerField(default=1024, verbose_name="最大Token")
    vector_weight = models.FloatField(
        default=0.7, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name="向量检索权重")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='apps',
                               verbose_name="租户")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "AI 应用"
        verbose_name_plural = "AI 应用"

    def __str__(self):
        return self.name


class Plugin(models.Model):
    """插件：可在工作流步骤或智能体中调用的外部工具（当前支持 HTTP 插件）"""
    PLUGIN_TYPE = (
        ('http', 'HTTP 请求'),
    )
    name = models.CharField(max_length=100, verbose_name="名称")
    type = models.CharField(max_length=20, choices=PLUGIN_TYPE, default='http', verbose_name="类型")
    description = models.TextField(blank=True, default="", verbose_name="描述")
    config = models.JSONField(default=dict, verbose_name="插件配置")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='plugins',
                               verbose_name="租户")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "插件"
        verbose_name_plural = "插件"
        ordering = ['-create_time']

    def __str__(self):
        return f'{self.name}({self.type})'


class MCPServer(models.Model):
    """MCP 服务器配置：通过 Model Context Protocol 连接外部工具"""
    TRANSPORT_CHOICES = (
        ('stdio', '标准输入输出'),
        ('http', 'HTTP/SSE'),
    )
    name = models.CharField(max_length=100, verbose_name="名称")
    transport = models.CharField(max_length=20, choices=TRANSPORT_CHOICES, default='http', verbose_name="传输方式")
    url = models.CharField(max_length=500, blank=True, default="", verbose_name="服务器地址")
    command = models.CharField(max_length=500, blank=True, default="", verbose_name="启动命令(stdio)")
    args = models.JSONField(default=list, verbose_name="启动参数")
    env = models.JSONField(default=dict, verbose_name="环境变量")
    headers = models.JSONField(default=dict, verbose_name="请求头")
    tools_cache = models.JSONField(default=list, verbose_name="工具列表缓存")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='mcp_servers',
                               verbose_name="租户")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "MCP 服务器"
        verbose_name_plural = "MCP 服务器"
        ordering = ['-create_time']

    def __str__(self):
        return self.name


class Agent(models.Model):
    """智能体：具备角色设定、知识库检索、工具调用、子智能体协作能力的 AI Agent"""
    name = models.CharField(max_length=200, verbose_name="名称")
    avatar = models.CharField(max_length=500, blank=True, default="", verbose_name="头像URL")
    description = models.TextField(blank=True, default="", verbose_name="描述")
    role = models.CharField(max_length=200, blank=True, default="", verbose_name="角色设定")
    system_prompt = models.TextField(
        blank=True,
        default="你是一个智能助手，可以使用提供的工具来回答用户问题。如果需要调用工具，请按照指定格式输出。",
        verbose_name="系统提示词")
    kbs = models.ManyToManyField(KnowledgeBase, blank=True, related_name='agents',
                                 verbose_name="关联知识库")
    tools = models.ManyToManyField(Plugin, blank=True, related_name='agents',
                                    verbose_name="可用工具")
    mcp_servers = models.ManyToManyField(MCPServer, blank=True, related_name='agents',
                                          verbose_name="MCP 服务器")
    sub_agents = models.ManyToManyField('self', blank=True, symmetrical=False,
                                         related_name='parent_agents', verbose_name="子智能体")
    temperature = models.FloatField(default=0.7, verbose_name="温度")
    max_tokens = models.IntegerField(default=2048, verbose_name="最大Token")
    max_iterations = models.IntegerField(default=5, verbose_name="最大推理轮次")
    opening_message = models.TextField(blank=True, default="你好！我是你的智能助手，有什么可以帮你的？",
                                        verbose_name="开场白")
    suggested_questions = models.JSONField(default=list, verbose_name="建议问题")
    enable_reasoning = models.BooleanField(default=True, verbose_name="展示思考过程")
    enable_code_interpreter = models.BooleanField(default=False, verbose_name="启用代码执行")
    enable_fhcode = models.BooleanField(default=False, verbose_name="启用飞虹Code编程引擎")
    enable_auto_optimize = models.BooleanField(default=False, verbose_name="启用自动优化")
    # 分享发布
    is_public = models.BooleanField(default=False, verbose_name="是否公开")
    share_code = models.CharField(max_length=32, blank=True, default="", verbose_name="分享码")
    share_config = models.JSONField(default=dict, verbose_name="分享配置")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='agents',
                               verbose_name="租户")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "智能体"
        verbose_name_plural = "智能体"
        ordering = ['-create_time']

    def __str__(self):
        return self.name


class AgentConversation(models.Model):
    """智能体会话"""
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='conversations',
                               verbose_name="智能体")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='agent_conversations', verbose_name="用户")
    session_id = models.CharField(max_length=64, unique=True, verbose_name="会话ID")
    title = models.CharField(max_length=200, blank=True, default="新对话", verbose_name="标题")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "智能体会话"
        verbose_name_plural = "智能体会话"
        ordering = ['-update_time']

    def __str__(self):
        return f'{self.agent.name} - {self.title}'


class AgentMessage(models.Model):
    """智能体消息"""
    ROLE_CHOICES = (
        ('user', '用户'),
        ('assistant', '助手'),
        ('tool', '工具'),
    )
    conversation = models.ForeignKey(AgentConversation, on_delete=models.CASCADE,
                                      related_name='messages', verbose_name="会话")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name="角色")
    content = models.TextField(verbose_name="内容")
    reasoning = models.TextField(blank=True, default="", verbose_name="思考过程")
    tool_calls = models.JSONField(default=list, verbose_name="工具调用记录")
    tool_name = models.CharField(max_length=100, blank=True, default="", verbose_name="工具名称")
    images = models.JSONField(default=list, verbose_name="生成的图片(base64)")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "智能体消息"
        verbose_name_plural = "智能体消息"
        ordering = ['create_time']

    def __str__(self):
        return f'{self.conversation.agent.name} - {self.role}'


class AgentFile(models.Model):
    """智能体对话中上传的文件，可供代码执行工具读取"""
    conversation = models.ForeignKey(AgentConversation, on_delete=models.CASCADE,
                                      related_name='files', verbose_name="会话")
    file_name = models.CharField(max_length=255, verbose_name="文件名")
    file_path = models.CharField(max_length=500, verbose_name="文件路径")
    file_size = models.BigIntegerField(default=0, verbose_name="文件大小(字节)")
    file_type = models.CharField(max_length=50, verbose_name="文件类型")
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                  null=True, blank=True, verbose_name="上传者")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")

    class Meta:
        verbose_name = "智能体文件"
        verbose_name_plural = "智能体文件"
        ordering = ['-create_time']

    def __str__(self):
        return self.file_name


class AgentEvaluation(models.Model):
    """智能体对话评价与优化建议"""
    SCORE_CHOICES = [(i, str(i)) for i in range(1, 6)]
    conversation = models.ForeignKey(AgentConversation, on_delete=models.CASCADE,
                                      related_name='evaluations', verbose_name="会话")
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='evaluations',
                               verbose_name="智能体")
    score = models.IntegerField(choices=SCORE_CHOICES, default=3, verbose_name="综合评分")
    relevance_score = models.IntegerField(default=3, verbose_name="相关性评分")
    accuracy_score = models.IntegerField(default=3, verbose_name="准确性评分")
    completeness_score = models.IntegerField(default=3, verbose_name="完整性评分")
    feedback = models.TextField(blank=True, default="", verbose_name="评价内容")
    suggestion = models.TextField(blank=True, default="", verbose_name="优化建议")
    suggested_prompt = models.TextField(blank=True, default="", verbose_name="建议的系统提示词")
    applied = models.BooleanField(default=False, verbose_name="是否已应用")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "智能体评价"
        verbose_name_plural = "智能体评价"
        ordering = ['-create_time']

    def __str__(self):
        return f'{self.agent.name} - {self.score}分'


class AgentVersion(models.Model):
    """智能体版本快照：发布时保存配置，支持回滚"""
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='versions',
                              verbose_name="智能体")
    version = models.CharField(max_length=20, verbose_name="版本号")
    name = models.CharField(max_length=200, blank=True, default="", verbose_name="版本名称")
    description = models.TextField(blank=True, default="", verbose_name="版本说明")
    # 配置快照
    config_snapshot = models.JSONField(default=dict, verbose_name="配置快照")
    is_current = models.BooleanField(default=False, verbose_name="是否当前版本")
    is_published = models.BooleanField(default=False, verbose_name="是否已发布")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True, verbose_name="创建者")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "智能体版本"
        verbose_name_plural = "智能体版本"
        ordering = ['-create_time']
        unique_together = ('agent', 'version')

    def __str__(self):
        return f'{self.agent.name} v{self.version}'


class Workflow(models.Model):
    """工作流：多步骤提示词链，按顺序执行，每步可引用上一步输出。"""
    STATUS = (
        ('draft', '草稿'),
        ('active', '启用'),
        ('archived', '归档'),
    )
    name = models.CharField(max_length=200, verbose_name="名称")
    desc = models.TextField(blank=True, default="", verbose_name="描述")
    status = models.CharField(max_length=20, choices=STATUS, default='draft', verbose_name="状态")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='workflows',
                               verbose_name="租户")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "工作流"
        verbose_name_plural = "工作流"
        ordering = ['-create_time']

    def __str__(self):
        return self.name


class WorkflowStep(models.Model):
    """工作流步骤"""
    STEP_TYPE = (
        ('llm', 'LLM 调用'),
        ('plugin', '插件调用'),
    )
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='steps',
                                  verbose_name="所属工作流")
    order = models.IntegerField(default=1, verbose_name="执行顺序")
    name = models.CharField(max_length=100, verbose_name="步骤名称")
    step_type = models.CharField(max_length=20, choices=STEP_TYPE, default='llm', verbose_name="步骤类型")
    plugin = models.ForeignKey(Plugin, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='steps', verbose_name="调用插件")
    prompt = models.TextField(blank=True, default="", verbose_name="提示词模板")
    temperature = models.FloatField(default=0.7, verbose_name="温度")
    max_tokens = models.IntegerField(default=1024, verbose_name="最大Token")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "工作流步骤"
        verbose_name_plural = "工作流步骤"
        ordering = ['order']

    def __str__(self):
        return f'{self.workflow.name} - 步骤{self.order}: {self.name}'


class WorkflowExecution(models.Model):
    """工作流执行记录"""
    STATUS = (
        ('running', '执行中'),
        ('success', '成功'),
        ('failed', '失败'),
    )
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='executions',
                                  verbose_name="工作流")
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True,
                             verbose_name="触发用户")
    input_text = models.TextField(verbose_name="输入内容")
    output_text = models.TextField(blank=True, default="", verbose_name="最终输出")
    step_outputs = models.JSONField(default=list, verbose_name="各步骤输出")
    status = models.CharField(max_length=20, choices=STATUS, default='running', verbose_name="状态")
    error_msg = models.TextField(blank=True, default="", verbose_name="错误信息")
    duration_ms = models.FloatField(default=0, verbose_name="耗时(毫秒)")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="执行时间")

    class Meta:
        verbose_name = "工作流执行记录"
        verbose_name_plural = "工作流执行记录"
        ordering = ['-create_time']

    def __str__(self):
        return f'{self.workflow.name} - {self.status}'
