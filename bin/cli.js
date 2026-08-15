#!/usr/bin/env node
/**
 * flyrain-kb CLI — 飞虹智知识库一键脚手架与部署工具
 *
 * 公司：晋江市飞虹智科技企业管理有限公司
 * 中心：飞扬企源研发中心
 * 负责人：吴赐虹
 */
'use strict'

const fs = require('fs')
const path = require('path')
const { spawnSync } = require('child_process')

const PKG_ROOT = path.resolve(__dirname, '..')
const PKG = JSON.parse(fs.readFileSync(path.join(PKG_ROOT, 'package.json'), 'utf8'))

// 模板目录：随包发布的项目源码
const TEMPLATE_DIRS = ['backend', 'frontend', 'deploy']
const TEMPLATE_FILES = ['README.md']

// 复制时永远跳过的路径片段（防止把构建产物带进新项目）
const SKIP = ['__pycache__', 'node_modules', '.venv', '.venv_check', 'dist', '.git']

const C = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  cyan: '\x1b[36m',
}

function log(msg = '') {
  process.stdout.write(msg + '\n')
}
function ok(msg) {
  log(`${C.green}✓${C.reset} ${msg}`)
}
function warn(msg) {
  log(`${C.yellow}!${C.reset} ${msg}`)
}
function die(msg, code = 1) {
  process.stderr.write(`${C.red}✗ ${msg}${C.reset}\n`)
  process.exit(code)
}

/** 新项目的 .gitignore（npm 发布会剔除 .gitignore，故在此生成） */
const GITIGNORE = `# 依赖与构建产物
__pycache__/
*.pyc
.venv/
node_modules/
dist/

# 环境与密钥
.env
*.local

# 媒体与日志
media/
*.log

# IDE
.idea/
.vscode/
.DS_Store
`

function copyTemplate(destDir) {
  const filter = (src) => !SKIP.some((s) => src.split(/[\\/]/).includes(s))

  for (const d of TEMPLATE_DIRS) {
    const from = path.join(PKG_ROOT, d)
    if (!fs.existsSync(from)) {
      die(`包内缺少模板目录 ${d}，安装可能不完整，请重新 npm i -g flyrain-kb`)
    }
    fs.cpSync(from, path.join(destDir, d), { recursive: true, filter })
  }
  for (const f of TEMPLATE_FILES) {
    const from = path.join(PKG_ROOT, f)
    if (fs.existsSync(from)) fs.copyFileSync(from, path.join(destDir, f))
  }
}

function cmdInit(args) {
  const force = args.includes('--force') || args.includes('-f')
  const target = args.find((a) => !a.startsWith('-')) || 'flyrain-kb'
  const destDir = path.resolve(process.cwd(), target)

  if (fs.existsSync(destDir)) {
    const entries = fs.readdirSync(destDir)
    if (entries.length > 0 && !force) {
      die(`目录已存在且非空：${destDir}\n  如需覆盖请加 --force`)
    }
  } else {
    fs.mkdirSync(destDir, { recursive: true })
  }

  log(`\n${C.bold}飞虹智知识库${C.reset} ${C.dim}v${PKG.version}${C.reset}  正在生成项目…\n`)

  copyTemplate(destDir)
  ok(`源码已生成：${destDir}`)

  // .gitignore（npm 不发布 .gitignore，需在此写出）
  fs.writeFileSync(path.join(destDir, '.gitignore'), GITIGNORE, 'utf8')
  ok('已生成 .gitignore')

  // 由 .env.example 生成 .env
  const envExample = path.join(destDir, 'backend', '.env.example')
  const envFile = path.join(destDir, 'backend', '.env')
  if (fs.existsSync(envExample) && !fs.existsSync(envFile)) {
    fs.copyFileSync(envExample, envFile)
    ok('已由 .env.example 生成 backend/.env')
    warn('请先填入真实的 DEFAULT_LLM_API_KEY / DEFAULT_LLM_BASE_URL / EMBEDDING_MODEL')
  }

  log(`\n${C.bold}下一步${C.reset}`)
  log(`  ${C.cyan}cd ${target}${C.reset}`)
  log(`  ${C.dim}# 1) 编辑 backend/.env 填入模型密钥${C.reset}`)
  log(`  ${C.cyan}flyrain-kb up${C.reset}          ${C.dim}# 或 cd deploy && docker compose up -d --build${C.reset}`)
  log(`  ${C.dim}# 2) 创建管理员${C.reset}`)
  log(`  ${C.cyan}flyrain-kb seed-admin${C.reset}`)
  log(`\n  前端 ${C.cyan}http://localhost:8080${C.reset}   后端 ${C.cyan}http://localhost:8000${C.reset}\n`)
}

/** 定位项目根：当前目录或参数指定目录下须存在 deploy/docker-compose.yml */
function resolveProject(args) {
  const target = args.find((a) => !a.startsWith('-')) || '.'
  const root = path.resolve(process.cwd(), target)
  const compose = path.join(root, 'deploy', 'docker-compose.yml')
  if (!fs.existsSync(compose)) {
    die(
      `未找到 deploy/docker-compose.yml（查找位置：${root}）\n` +
        `  请在项目根目录执行，或先运行 flyrain-kb init`
    )
  }
  return path.join(root, 'deploy')
}

function docker(cwd, dockerArgs) {
  const r = spawnSync('docker', dockerArgs, { cwd, stdio: 'inherit', shell: process.platform === 'win32' })
  if (r.error) {
    die(`无法执行 docker，请确认已安装并启动 Docker Desktop / Docker Engine\n  ${r.error.message}`)
  }
  process.exit(r.status === null ? 1 : r.status)
}

function cmdUp(args) {
  const cwd = resolveProject(args)
  log(`${C.dim}› docker compose up -d --build${C.reset}`)
  docker(cwd, ['compose', 'up', '-d', '--build'])
}

function cmdDown(args) {
  const cwd = resolveProject(args)
  log(`${C.dim}› docker compose down${C.reset}`)
  docker(cwd, ['compose', 'down'])
}

function cmdLogs(args) {
  const cwd = resolveProject(args)
  log(`${C.dim}› docker compose logs -f --tail=100${C.reset}`)
  docker(cwd, ['compose', 'logs', '-f', '--tail=100'])
}

function cmdSeedAdmin(args) {
  const cwd = resolveProject(args)
  const user = valueOf(args, '--username') || 'admin'
  const pass = valueOf(args, '--password') || 'admin123'
  log(`${C.dim}› docker compose exec backend python manage.py seed_admin${C.reset}`)
  docker(cwd, [
    'compose', 'exec', 'backend', 'python', 'manage.py', 'seed_admin',
    '--username', user, '--password', pass,
  ])
}

function valueOf(args, flag) {
  const i = args.indexOf(flag)
  return i >= 0 ? args[i + 1] : null
}

function help() {
  log(`
${C.bold}飞虹智知识库 flyrain-kb${C.reset} ${C.dim}v${PKG.version}${C.reset}
私有化部署的 RAG 知识库问答平台（Django 5 + Vue 3 + PostgreSQL/pgvector）

${C.bold}用法${C.reset}
  flyrain-kb <命令> [选项]

${C.bold}命令${C.reset}
  init [目录]            生成完整项目源码（默认目录 flyrain-kb）
                         --force  目标目录非空时强制覆盖
  up [目录]              docker compose up -d --build 启动全栈
  down [目录]            停止并移除容器
  logs [目录]            跟踪查看容器日志
  seed-admin [目录]      创建管理员账号
                         --username <名>  --password <密码>

${C.bold}选项${C.reset}
  -v, --version          显示版本
  -h, --help             显示帮助

${C.bold}快速开始${C.reset}
  ${C.cyan}npx flyrain-kb init my-kb${C.reset}
  ${C.cyan}cd my-kb${C.reset}   ${C.dim}# 编辑 backend/.env 填模型密钥${C.reset}
  ${C.cyan}flyrain-kb up${C.reset}

${C.dim}晋江市飞虹智科技企业管理有限公司 · 飞扬企源研发中心 · 负责人：吴赐虹${C.reset}
`)
}

function main() {
  const argv = process.argv.slice(2)
  const cmd = argv[0]
  const rest = argv.slice(1)

  if (!cmd || cmd === '-h' || cmd === '--help' || cmd === 'help') return help()
  if (cmd === '-v' || cmd === '--version') return log(PKG.version)

  switch (cmd) {
    case 'init':
      return cmdInit(rest)
    case 'up':
    case 'start':
      return cmdUp(rest)
    case 'down':
    case 'stop':
      return cmdDown(rest)
    case 'logs':
      return cmdLogs(rest)
    case 'seed-admin':
      return cmdSeedAdmin(rest)
    default:
      die(`未知命令：${cmd}\n  运行 flyrain-kb --help 查看可用命令`)
  }
}

main()
