import logging
import sys

from .base import *  # noqa

DEBUG = False

# 生产环境安全校验：SECRET_KEY 仍为默认值时直接禁止启动
_default_secret = "change-me-secret"
if SECRET_KEY == _default_secret:  # noqa: F405 (from base import *)
    raise RuntimeError(
        "【安全错误】生产环境 SECRET_KEY 仍为默认值 'change-me-secret'，"
        "会话签名可被伪造，禁止启动。\n"
        "请在 backend/.env 中设置 SECRET_KEY=<随机字符串>，"
        "可用以下命令生成：python -c \"import secrets; print(secrets.token_urlsafe(50))\""
    )

# 生产环境安全配置
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")  # noqa: F405
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# 生产环境日志：输出到控制台，Docker 可通过 docker logs 收集
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
