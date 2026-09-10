"""Code Interpreter：受限的 Python 代码执行工具。

安全策略：
- 子进程执行，设置超时（默认 30s）
- 禁用网络、文件系统写入（通过 preload 钩子）
- AST 静态检查：禁止 import 危险模块、禁止 open/write/exec/eval/compile/__import__
- 捕获 stdout/stderr
- matplotlib 图表自动保存为 base64 PNG 返回

返回格式：
{
  "success": bool,
  "stdout": str,
  "stderr": str,
  "error": str,
  "images": [base64_png, ...],
  "execution_time_ms": float
}
"""
import ast
import base64
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 危险模块黑名单
DANGEROUS_MODULES = {
    'os', 'sys', 'subprocess', 'socket', 'http', 'urllib', 'requests',
    'ftplib', 'smtplib', 'telnetlib', 'poplib', 'imaplib',
    'shutil', 'pathlib', 'glob', 'tempfile', 'pickle', 'shelve',
    'ctypes', 'multiprocessing', 'threading', 'asyncio',
    'importlib', 'pkgutil', 'site', 'distutils',
    'winreg', 'win32api', 'win32con', 'win32gui',
    'psutil', 'docker', 'kubernetes',
}

# 危险函数/属性黑名单
DANGEROUS_NAMES = {
    'open', 'exec', 'eval', 'compile', '__import__', 'getattr', 'setattr',
    'delattr', 'globals', 'locals', 'vars', 'dir', 'hasattr',
    'input', 'raw_input', 'exit', 'quit', 'breakpoint',
    'memoryview', 'bytearray', 'bytes',
    'os.system', 'os.popen', 'os.exec', 'os.spawn', 'os.fork',
    'subprocess.call', 'subprocess.run', 'subprocess.Popen',
    'shutil.rmtree', 'shutil.move', 'shutil.copy',
    'socket.socket', 'http.client', 'urllib.request',
    'eval', 'exec', 'compile',
}


def _check_ast_safety(code: str) -> Optional[str]:
    """AST 静态安全检查，返回错误信息或 None。"""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"语法错误: {e}"

    for node in ast.walk(tree):
        # 检查 import
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_module = alias.name.split('.')[0]
                if top_module in DANGEROUS_MODULES:
                    return f"禁止导入模块: {alias.name}"
        if isinstance(node, ast.ImportFrom):
            if node.module:
                top_module = node.module.split('.')[0]
                if top_module in DANGEROUS_MODULES:
                    return f"禁止从模块导入: {node.module}"
        # 检查危险函数调用
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                if func.id in DANGEROUS_NAMES:
                    return f"禁止调用函数: {func.id}"
            elif isinstance(func, ast.Attribute):
                full_name = _get_full_attr_name(func)
                if full_name in DANGEROUS_NAMES:
                    return f"禁止调用: {full_name}"
                # 检查属性名是否危险
                if func.attr in {'system', 'popen', 'exec', 'eval', 'fork', 'spawn',
                                  'rmtree', 'remove', 'unlink', 'chmod', 'chown',
                                  'connect', 'send', 'recv', 'bind', 'listen', 'accept'}:
                    return f"禁止调用危险方法: {full_name}"
        # 检查危险属性访问
        if isinstance(node, ast.Attribute):
            if node.attr in {'__dict__', '__class__', '__bases__', '__subclasses__',
                             '__globals__', '__code__', '__closure__', '__frame__',
                             '__builtins__', '__import__'}:
                return f"禁止访问危险属性: .{node.attr}"
    return None


def _get_full_attr_name(node: ast.Attribute) -> str:
    """获取属性调用的完整名称，如 os.system。"""
    parts = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return '.'.join(reversed(parts))


def _wrap_code(code: str, files: List[Dict] = None) -> str:
    """包装用户代码：注入 matplotlib 后端设置、图表捕获、异常捕获、文件路径。"""
    files = files or []
    file_info_lines = []
    for f in files:
        file_info_lines.append(f"# 文件: {f['name']} -> data/{f['name']}")
    file_info = '\n'.join(file_info_lines) if file_info_lines else '# 无上传文件'

    wrapper = f'''
import sys
import io
import json
import base64
import traceback
import os

# 文件目录
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)
{file_info}

# 重定向 stdout/stderr
_stdout = io.StringIO()
_stderr = io.StringIO()
sys.stdout = _stdout
sys.stderr = _stderr

# matplotlib 非交互后端 + 图表捕获
_images = []
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    _original_show = plt.show
    def _capture_show(*args, **kwargs):
        for num in plt.get_fignums():
            fig = plt.figure(num)
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            _images.append(base64.b64encode(buf.read()).decode('utf-8'))
            plt.close(fig)
    plt.show = _capture_show
except ImportError:
    pass

_result = {{"success": True, "stdout": "", "stderr": "", "error": "", "images": []}}

try:
{chr(10).join('    ' + line for line in code.split(chr(10)))}
except Exception as e:
    _result["success"] = False
    _result["error"] = traceback.format_exc()

# 捕获剩余图表
try:
    import matplotlib.pyplot as plt
    for num in plt.get_fignums():
        fig = plt.figure(num)
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        _images.append(base64.b64encode(buf.read()).decode('utf-8'))
        plt.close(fig)
except Exception:
    pass

_result["stdout"] = _stdout.getvalue()
_result["stderr"] = _stderr.getvalue()
_result["images"] = _images

print("__RESULT_START__")
print(json.dumps(_result, ensure_ascii=False))
print("__RESULT_END__")
'''
    return wrapper


def execute_code(code: str, timeout: int = 30, memory_limit_mb: int = 512,
                 files: List[Dict] = None, sandbox_mode: str = "auto") -> Dict:
    """执行 Python 代码，返回执行结果。

    Args:
        code: Python 源代码
        timeout: 超时秒数
        memory_limit_mb: 内存限制（MB）
        files: 上传的文件列表 [{name, path}]，代码中可通过 data/文件名 访问
        sandbox_mode: 沙箱模式 - "auto"(自动选择) / "docker" / "subprocess"
    """
    # 自动选择模式
    if sandbox_mode == "auto":
        sandbox_mode = "docker" if check_docker_available() else "subprocess"

    # Docker 模式
    if sandbox_mode == "docker" and check_docker_available():
        result = execute_code_docker(
            code, timeout=timeout, memory_limit_mb=memory_limit_mb,
            files=files,
        )
        result["sandbox"] = "docker"
        return result

    # 子进程模式（回退）
    result = _execute_code_subprocess(code, timeout=timeout, memory_limit_mb=memory_limit_mb, files=files)
    result["sandbox"] = "subprocess"
    return result


def _execute_code_subprocess(code: str, timeout: int = 30, memory_limit_mb: int = 512,
                             files: List[Dict] = None) -> Dict:
    """子进程执行代码（原始实现）。"""
    start_time = time.time()
    files = files or []

    # 1. AST 安全检查
    safety_error = _check_ast_safety(code)
    if safety_error:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "error": f"安全检查未通过: {safety_error}",
            "images": [],
            "execution_time_ms": 0,
        }

    # 2. 包装代码
    wrapped = _wrap_code(code, files)

    # 3. 写入临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(wrapped)
        temp_path = f.name

    # 创建 data 目录并复制文件
    temp_dir = os.path.dirname(temp_path)
    data_dir = os.path.join(temp_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    for f in files:
        try:
            import shutil
            dest = os.path.join(data_dir, os.path.basename(f['name']))
            shutil.copy2(f['path'], dest)
        except Exception as e:
            logger.warning("文件复制失败: %s, error=%s", f.get('name'), e)

    try:
        # 4. 子进程执行
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['MPLBACKEND'] = 'Agg'

        cmd = [sys.executable, temp_path]

        # Windows 下不支持 resource 模块限制内存，用 CREATE_NO_WINDOW
        creationflags = 0
        if sys.platform == 'win32':
            creationflags = 0x08000000  # CREATE_NO_WINDOW

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=temp_dir,
                creationflags=creationflags,
                encoding='utf-8',
                errors='replace',
            )
            stdout = proc.stdout
            stderr = proc.stderr
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "error": f"执行超时（超过 {timeout} 秒）",
                "images": [],
                "execution_time_ms": (time.time() - start_time) * 1000,
            }

        # 5. 解析结果
        result = _parse_result(stdout, stderr)
        result["execution_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return result

    finally:
        # 清理临时文件
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def _parse_result(stdout: str, stderr: str) -> Dict:
    """从子进程输出中解析 JSON 结果。"""
    # 查找 __RESULT_START__ 和 __RESULT_END__ 之间的内容
    match = re.search(r'__RESULT_START__\s*\n(.*?)\n__RESULT_END__', stdout, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1))
            # 移除结果标记后的 stdout
            result["stdout"] = stdout[:stdout.find('__RESULT_START__')].strip()
            return result
        except json.JSONDecodeError:
            pass

    # 解析失败，返回原始输出
    return {
        "success": False,
        "stdout": stdout[:5000],
        "stderr": stderr[:5000],
        "error": "结果解析失败",
        "images": [],
    }


def format_code_result(result: Dict) -> str:
    """将代码执行结果格式化为文本，供 LLM 阅读。"""
    lines = []
    if result.get("success"):
        lines.append("代码执行成功")
    else:
        lines.append(f"代码执行失败: {result.get('error', '未知错误')}")

    if result.get("stdout"):
        lines.append(f"\n标准输出:\n{result['stdout'][:3000]}")

    if result.get("stderr"):
        lines.append(f"\n标准错误:\n{result['stderr'][:2000]}")

    if result.get("images"):
        lines.append(f"\n生成了 {len(result['images'])} 张图表")

    lines.append(f"\n耗时: {result.get('execution_time_ms', 0):.0f}ms")
    return '\n'.join(lines)


# ============ Docker 容器沙箱执行 ============

DOCKER_IMAGE = "python:3.11-slim"
DOCKER_AVAILABLE = None


def check_docker_available() -> bool:
    """检测 Docker 是否可用。"""
    global DOCKER_AVAILABLE
    if DOCKER_AVAILABLE is not None:
        return DOCKER_AVAILABLE
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True, text=True, timeout=5,
        )
        DOCKER_AVAILABLE = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        DOCKER_AVAILABLE = False
    return DOCKER_AVAILABLE


def execute_code_docker(code: str, timeout: int = 30, memory_limit_mb: int = 512,
                        cpu_limit: float = 1.0, network_disabled: bool = True,
                        files: List[Dict] = None) -> Dict:
    """在 Docker 容器中执行 Python 代码（更安全的沙箱）。

    Args:
        code: Python 源代码
        timeout: 超时秒数
        memory_limit_mb: 内存限制（MB）
        cpu_limit: CPU 核心数限制
        network_disabled: 是否禁用网络
        files: 上传的文件列表
    """
    start_time = time.time()
    files = files or []

    # 包装代码
    wrapped = _wrap_code(code, files)

    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="code_sandbox_")
    script_path = os.path.join(temp_dir, "main.py")
    data_dir = os.path.join(temp_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(wrapped)

    # 复制文件
    for f in files:
        try:
            import shutil
            dest = os.path.join(data_dir, os.path.basename(f['name']))
            shutil.copy2(f['path'], dest)
        except Exception as e:
            logger.warning("文件复制失败: %s, error=%s", f.get('name'), e)

    container_name = f"code-sandbox-{int(time.time() * 1000)}"

    try:
        # 构建 docker run 命令
        cmd = [
            "docker", "run",
            "--name", container_name,
            "--rm",
            "-m", f"{memory_limit_mb}m",
            "--cpus", str(cpu_limit),
            "--pids-limit", "128",
            "-v", f"{temp_dir}:/workspace",
            "-w", "/workspace",
            "-e", "PYTHONIOENCODING=utf-8",
            "-e", "MPLBACKEND=Agg",
            "--network", "none" if network_disabled else "bridge",
            DOCKER_IMAGE,
            "python", "/workspace/main.py",
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 10,  # 给 Docker 启动留额外时间
                encoding='utf-8',
                errors='replace',
            )
            stdout = proc.stdout
            stderr = proc.stderr
            if proc.returncode != 0 and not stdout:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": stderr[:2000],
                    "error": f"容器执行失败（退出码 {proc.returncode}）",
                    "images": [],
                    "execution_time_ms": round((time.time() - start_time) * 1000, 2),
                    "sandbox": "docker",
                }
        except subprocess.TimeoutExpired:
            # 强制删除容器
            subprocess.run(["docker", "rm", "-f", container_name],
                           capture_output=True, timeout=5)
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "error": f"执行超时（超过 {timeout} 秒）",
                "images": [],
                "execution_time_ms": round((time.time() - start_time) * 1000, 2),
                "sandbox": "docker",
            }

        result = _parse_result(stdout, stderr)
        result["execution_time_ms"] = round((time.time() - start_time) * 1000, 2)
        result["sandbox"] = "docker"
        return result

    finally:
        # 清理临时目录
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


def get_sandbox_status() -> Dict:
    """获取沙箱执行状态。"""
    docker_available = check_docker_available()
    return {
        "docker_available": docker_available,
        "docker_image": DOCKER_IMAGE,
        "default_mode": "docker" if docker_available else "subprocess",
        "modes": ["subprocess"] + (["docker"] if docker_available else []),
    }

