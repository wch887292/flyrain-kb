import logging
import warnings

from .base import *  # noqa

DEBUG = False

# 生产环境安全校验：SECRET_KEY 仍为默认值时发出强烈警告
_default_secret = "change-me-secret"
if SECRET_KEY == _default_secret:  # noqa: F405 (from base import *)
    warnings.warn(
        "⚠️  安全警告：SECRET_KEY 仍为默认值 'change-me-secret'，"
        "生产环境必须修改为随机字符串，否则会话签名可被伪造。"
        "请在 backend/.env 中设置 SECRET_KEY。",
        RuntimeWarning,
        stacklevel=2,
    )

# 生产环境日志：输出到控制台，Docker 可通过 docker logs 收集
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
