# 飞虹智知识库 flyrain-kb

> 对标 MaxKB 的企业级 RAG 知识库问答平台（可私有化部署）
> 公司：晋江市飞虹智科技企业管理有限公司 · 中心：飞扬企源研发中心 · 负责人：吴赐虹

## 技术栈

- 后端：Python 3.11 + Django 5.2 + DRF + Celery + Redis + pgvector(PostgreSQL 15)
- 前端：Vue3 + Vite5 + TypeScript + Element-Plus
- 通信：REST API + SSE 流式对话
- 部署：Docker-Compose

## 目录结构

```
flyrain-kb/
├── backend/        # Django 后端（apps: users/knowledge/application/chat/model_provider/common）
├── frontend/       # Vue3 前端
└── deploy/         # docker-compose / nginx
```

## 快速开始（npm 一键脚手架）

已发布到 npm，无需克隆仓库：

```bash
# 生成完整项目（后端 + 前端 + docker-compose）
npx flyrain-kb init my-kb
cd my-kb

# 编辑 backend/.env 填入真实模型密钥（init 已自动从 .env.example 生成）
#   DEFAULT_LLM_API_KEY / DEFAULT_LLM_BASE_URL / DEFAULT_EMBEDDING_MODEL

# 拉起全栈（postgres / redis / backend / worker / frontend）
npx flyrain-kb up

# 创建管理员
npx flyrain-kb seed-admin --username admin --password admin123
```

也可全局安装后直接使用 `flyrain-kb` 命令：

```bash
npm i -g flyrain-kb
flyrain-kb --help
```

### CLI 命令

| 命令 | 说明 |
| --- | --- |
| `init [目录]` | 生成完整项目源码（默认目录 `flyrain-kb`），`--force` 覆盖非空目录 |
| `up [目录]` | `docker compose up -d --build` 启动全栈 |
| `down [目录]` | 停止并移除容器 |
| `logs [目录]` | 跟踪查看容器日志 |
| `seed-admin [目录]` | 创建管理员，`--username` / `--password` |
| `-v, --version` / `-h, --help` | 版本 / 帮助 |

> CLI 零运行时依赖，仅需 Node.js >= 18；`up` 系列命令需本机已安装并启动 Docker。

## 快速开始（已有源码，直接 Docker）

```bash
cd deploy
docker compose up -d --build
```

- 前端控制台：http://localhost:8080
- 后端 API：http://localhost:8000

## 本地开发

后端：

```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate
pip install .
cp .env.example .env   # 修改 DEFAULT_LLM_API_KEY
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
celery -A celery_app worker -l info
```

前端：

```bash
cd frontend
npm install
npm run dev
```

## 核心流程

1. 新建知识库 → 上传 PDF/DOCX/TXT/MD/XLSX
2. Celery 异步解析 + 分块 + 向量化入库
3. 创建 AI 应用，绑定知识库与 Prompt
4. 对话页提问，混合检索（向量+关键词）召回资料，LLM 经 SSE 流式作答

## 角色与权限（RBAC）

系统内置三类角色，按写操作最小权限控制：

| 角色 | 说明 | 可写资源 |
| --- | --- | --- |
| admin（管理员） | 最高权限 | 知识库 / 文档 / AI 应用 / 模型配置 / 用户 |
| editor（知识库维护） | 内容维护 | 知识库 / 文档 / AI 应用 |
| user（普通用户） | 只读使用者 | 仅查看与对话，无写权限 |

- 后端通过 `apps/common/rbac.py` 的 `RoleRequiredMixin` 在 `perform_create/update/destroy` 及 `upload` 动作中做角色校验，越权返回 `403`。
- 前端路由守卫（`router/index.ts`）按 `meta.roles` 限制 `/model`（仅 admin）、`/apps`（admin/editor）；布局菜单与菜单项、各页「新建/上传」按钮按当前角色显隐。
- 自注册（`/users/register/`）仅生成 `user` 角色，管理员使用种子命令创建：

```bash
python manage.py seed_admin --username admin --password admin123
```

### 用户管理页（admin 专属）

- 路由 `/users`（`meta.roles: ['admin']`），左侧菜单「用户管理」仅 admin 可见。
- 后端 `UserViewSet`（`apps/users/views.py`）仅 admin 可读写：`GET/POST /api/users/`、`GET/PUT/DELETE /api/users/<pk>/`。
- 支持：新建用户（含密码/角色/租户）、修改角色、删除用户。
- 安全护栏（后端强制）：
  - 不可删除当前登录账号；
  - 不可删除或降级**唯一一名管理员**（至少保留一名 admin）；
  - 角色选择限定 `admin / editor / user` 三档。
- 新建/改角色走 `AdminUserWriteSerializer`，密码仅写入不回显。

## 向量检索索引优化（IVFFlat）

`Paragraph.vector` 字段已建立 pgvector `ivfflat` 索引（`vector_cosine_ops`），与检索使用的余弦距离（`CosineDistance`，底层 `<=>` 运算符）自动匹配，大幅提升大规模向量的相似度查询性能。

- 迁移文件：`apps/knowledge/migrations/0002_paragraph_vector_ivfflat.py`
- `lists = 100` 为经验默认值，建议按「预期行数 / 1000」调整（范围 1~1000）；数据量显著增长后执行 `REINDEX INDEX knowledge_paragraph_vector_ivfflat_idx;`
- 检索前可在会话中设置探针数提升召回：`SET ivfflat_probes = 10;`（默认 probes=1）

## 分段命中高亮（KnowledgeDetail）

知识库详情页的「分段预览」对话框支持关键词高亮：

- 检索模式下：自动用检索词对命中分段做 `<mark>` 高亮；
- 任意分段预览下：顶部「高亮」输入框可手动输入关键词（空格分隔多个词）实时高亮；
- 实现要点：先对文档内容做 HTML 转义再包裹高亮标签（`highlight()` 函数），避免文档内容造成 XSS。

## 本地 Docker 联调

```bash
cd deploy
# 1) 配置真实模型 Key（必须，否则 embedding/对话会失败）
cp ../backend/.env.example ../backend/.env
#    编辑 .env 设置 DEFAULT_LLM_API_KEY / DEFAULT_LLM_BASE_URL / DEFAULT_EMBEDDING_MODEL
# 2) 构建并启动全部服务（postgres / redis / backend / worker / frontend）
docker compose up -d --build
# 3) 创建管理员账户
docker compose exec backend python manage.py seed_admin --username admin --password admin123
```

- 前端控制台：http://localhost:8080
- 后端 API：http://localhost:8000
- 首次用 seed 创建的管理员登录，再建知识库 → 上传文档（Celery Worker 异步解析+向量化）→ 配置模型 → 对话。

## 待完善

- 多模态解析（图片/表格深度理解）、工作流编排
- 模型微调与效果评测、命中率分析看板
