# MaxKB（flyrain-kb）↔ 飞虹 Code（fhcode）底层引擎对接说明

> 架构层次：**fhcode 为底层执行引擎**（沙箱 / RBAC / 审计 / 加密 / 任务编排），**MaxKB（flyrain-kb）与 WeKnora 为上层应用**。
> 上层智能体通过本对接把「真实工程级编程任务」转发给 fhcode 沙箱执行。

## 一、对接能力

在 flyrain-kb 后端 Agent 引擎中新增内置工具 **「飞虹Code编程引擎」**（工具名 `fhcode_engine`）：

- 启用后，智能体可调用底层 fhcode 完成：编写 / 修改 / 重构多文件代码、运行测试与构建、执行命令、排查修复 bug、操作工作区文件。
- 与内置「代码执行（code_interpreter）」的分工：
  - `code_interpreter`：临时数学计算、数据分析、matplotlib 画图（无文件、无网络、受限）。
  - `fhcode_engine`：真实项目代码、文件操作、命令执行、工程级问题（隔离沙箱，完整能力）。
- 智能体通过 ReAct 模式自行选择工具；工具仅在 Agent 勾选「飞虹Code编程引擎」且后台已配置 `FHCODE_TOKEN` 时注册。

## 二、改动清单

| 文件 | 改动 |
| --- | --- |
| `backend/apps/application/fhcode_client.py` | **新建**。fhcode REST API 客户端：提交任务 / 轮询 / 停止 / 健康检查，含 Bearer Token 与写请求 HMAC-SHA256 签名 |
| `backend/apps/application/models.py` | `Agent` 新增 `enable_fhcode` 布尔字段 |
| `backend/apps/application/migrations/0012_agent_enable_fhcode.py` | **新建**。数据库迁移（AddField） |
| `backend/apps/application/agent_engine.py` | 注册 `fhcode_engine` 工具、新增执行分支、系统提示词规则、异常处理 |
| `backend/apps/application/agent_views.py` | `AgentSerializer` 暴露 `enable_fhcode`（同时补齐 `enable_code_interpreter`） |
| `frontend/src/views/AgentManage.vue` | 智能体编辑表单新增「飞虹Code编程引擎」开关（含默认值 / 编辑回填） |
| `frontend/src/views/AgentTemplate.vue` | 模板卡片与详情新增「飞虹Code引擎」标签 |
| `frontend/src/api/agent.ts` | `Agent` 类型补 `enable_code_interpreter?` / `enable_fhcode?` |
| `backend/.env`、`backend/.env.example` | 新增 fhcode 对接配置段 |

## 三、配置项（backend/.env）

```dotenv
# ---------- 飞虹 Code 底层引擎对接 ----------
FHCODE_BASE_URL=http://127.0.0.1:8080      # fhcode 服务地址
FHCODE_TOKEN=<与 fhcode 侧 FH_WEB_TOKEN 一致>
FHCODE_SIGN_SECRET=<与 fhcode 侧 FH_SIGN_SECRET 一致>   # 写请求签名密钥
FHCODE_TIMEOUT=300                          # 单次任务最大等待秒数
FHCODE_AGENT_TYPE=write-code                # 默认智能体类型（可选）
```

- `FHCODE_TOKEN`：fhcode 控制台主令牌（fhcode `.env` 的 `FH_WEB_TOKEN`）。
- `FHCODE_SIGN_SECRET`：fhcode 对所有写请求（POST/PUT/PATCH/DELETE）强制 HMAC 签名
  （`x-fh-ts` / `x-fh-nonce` / `x-fh-sig`，±5 分钟时间窗 + nonce 防重放）。
  客户端按 `HMAC-SHA256(secret, "{ts}|{nonce}|{bodyRaw}")` 计算，secret 与 fhcode 侧 `FH_SIGN_SECRET` 一致。
- 未配置 `FHCODE_TOKEN` 时，`fhcode_engine` 工具不会注册（`is_configured()` 守卫），不影响其它能力。
- `FHCODE_AGENT_TYPE` 可选值：`write-code` / `fix-code` / `exec-command` / `code-review` / `general`。

## 四、部署步骤

1. 确认 fhcode 服务已启动并可访问（默认 `http://127.0.0.1:8080`，`GET /api/health` 返回 200）。
2. 配置 `backend/.env`（见上，token 与签名密钥须与 fhcode 侧一致）。
3. 执行数据库迁移：
   ```bash
   cd backend
   python manage.py migrate application
   ```
4. 重启 flyrain-kb 后端服务。
5. 前端构建（部署时）：
   ```bash
   cd frontend
   npm install
   npm run build
   ```
6. 在「智能体管理 → 编辑」中打开「飞虹Code编程引擎」开关，保存即可。

## 五、已验证项（2026-09-18）

- 全部 Python 文件 `py_compile` 语法通过；model / migration / engine / serializer 静态一致性校验通过。
- 端到端联调（对本机运行中的 fhcode v8.4.3）：
  - `GET /api/health` 200；
  - `GET /api/tasks` 带 Bearer 200；
  - `POST /api/tasks` 带 HMAC 签名 **201 创建成功**（任务进入 `queued → running`）；
  - `GET /api/tasks/:id` 轮询状态机正常，正确读取终态 `done/failed` 与 `error` 字段；
  - `POST /api/tasks/:id/stop` 签名通过（对已结束任务返回 409「任务不存在或已结束」，业务正确）。
- 鉴权边界：无 token 访问受保护接口返回 401；写请求缺签名头返回 401。
- `backend/.env` 已被 `.gitignore` 排除，密钥不会进入版本库。

## 六、待办与注意事项

- **fhcode 模型 Provider 需先修复**：联调中测试任务最终 `failed`，原因为 fhcode 配置的 siliconflow 模型令牌无效
  （`HTTP 401 Token is invalid`）。这是 fhcode 侧的模型配置问题，与本对接无关；请在 fhcode 控制台配置有效的模型 API Key 后再做真实编程任务联调。
- 生产部署中若 fhcode 与 flyrain-kb 分机部署，`FHCODE_BASE_URL` 改为内网地址，并建议在防火墙 / nginx 层限制只允许 flyrain-kb 服务器访问 fhcode 端口。
- 生产环境建议为 fhcode 配置独立的最小权限令牌，结合 fhcode 的 RBAC（viewer/developer/operator/admin）与 `permissions`（denyShell / denyPaths / maxCostUsd）限制上层工具的操作范围。
- 前端当前未安装依赖，`npm run build` 需在部署环境执行；改动均为与现有「代码执行」开关同构的增量。
