"""User-facing error translation and guidance helpers."""

from __future__ import annotations

import re
from typing import Sequence


DOCKER_DESKTOP_URL = "https://www.docker.com/products/docker-desktop/"
DEFAULT_SUPPORTED_LANGUAGES = ("python", "cpp", "c", "java", "javascript", "go", "rust")


def _compact(text: object) -> str:
    return " ".join(str(text or "").replace("\r", " ").split())


def _is_docker_exception(exc: BaseException | None) -> bool:
    if exc is None:
        return False

    cls = exc.__class__
    module = getattr(cls, "__module__", "").lower()
    name = getattr(cls, "__name__", "")
    return "docker" in module or name in {
        "DockerException",
        "APIError",
        "ContainerError",
        "ImageNotFound",
        "NotFound",
        "BuildError",
    }


def _classify_docker_problem(message: str) -> str:
    text = _compact(message).lower()

    if any(keyword in text for keyword in (
        "permission denied",
        "access is denied",
        "got permission denied",
    )):
        return "permission"

    if any(keyword in text for keyword in (
        "cannot connect to the docker daemon",
        "is the docker daemon running",
        "error while fetching server api version",
        "connection refused",
        "dial tcp",
        "context deadline exceeded",
        "npipe",
        "docker_engine",
    )):
        return "not_running"

    if any(keyword in text for keyword in (
        "starting the docker daemon",
        "docker daemon is starting",
        "daemon is starting",
    )):
        return "starting"

    if "docker" in text and any(keyword in text for keyword in (
        "no such file or directory",
        "executable file not found",
        "not found",
    )):
        return "not_installed"

    return "unknown"


def docker_unavailable_message(reason: str = "unknown") -> str:
    lines = ["Docker 环境不可用。"]

    if reason == "not_installed":
        lines.append(f"请先安装 Docker Desktop: {DOCKER_DESKTOP_URL}")
    elif reason == "not_running":
        lines.append(f"请先安装并启动 Docker Desktop: {DOCKER_DESKTOP_URL}")
        lines.append("如果已经安装，请确认 Docker Daemon 正在运行。")
    elif reason == "permission":
        lines.append("当前账号没有访问 Docker 的权限。请重新登录后再试，或使用有权限的账号启动 Docker Desktop。")
    elif reason == "starting":
        lines.append("Docker 可能还在启动中，请稍等片刻后重试。")
    else:
        lines.append("请确认已安装 Docker Desktop，且服务处于运行状态。")

    lines.append("你也可以先在终端运行 `docker ps` 检查 Docker 是否可用。")
    return "\n".join(lines)


def _format_language_message(message: str, supported_languages: Sequence[str]) -> str:
    supported = ", ".join(supported_languages)

    match = re.search(r"Unsupported language '([^']+)'", message)
    if match:
        return f"不支持的语言: {match.group(1)}。支持的语言: {supported}"

    match = re.search(r"Cannot infer language from file '([^']+)'", message)
    if match:
        return f"无法从文件 {match.group(1)} 推断语言，请显式传入 language 参数。支持的语言: {supported}"

    return ""


def format_user_friendly_error(
    exc: BaseException | str | None,
    *,
    action: str = "操作",
    supported_languages: Sequence[str] = DEFAULT_SUPPORTED_LANGUAGES,
) -> str:
    """Translate raw exceptions into short, user-facing messages."""
    raw_message = str(exc or "").strip()
    message = _compact(raw_message)
    if not message:
        return f"{action}失败，请稍后重试。"

    if "Docker 环境不可用" in message:
        return raw_message or message

    if any(marker in message for marker in (
        "Docker 镜像",
        "请先安装 Docker Desktop",
        "请先启动 Docker Desktop",
        "docker ps",
    )):
        return raw_message or message

    if "SandboxSession not initialized" in message or "沙箱尚未初始化" in message:
        return "沙箱尚未初始化，请先启动沙箱后再执行。"

    if "Path escapes sandbox workspace" in message:
        return "路径超出了沙箱允许范围，请使用工作目录内的相对路径。"

    language_message = _format_language_message(message, supported_languages)
    if language_message:
        return language_message

    lowered = message.lower()
    if isinstance(exc, FileNotFoundError):
        if "docker" in lowered:
            return docker_unavailable_message("not_installed")
        return message or f"{action}失败，找不到指定文件或目录，请确认路径是否正确。"

    if isinstance(exc, PermissionError):
        return f"{action}失败，当前没有权限访问该资源，请检查权限后重试。"

    if _is_docker_exception(exc) or "docker" in lowered:
        if "image not found" in lowered or "pull access denied" in lowered:
            return "Docker 镜像不存在或无法下载。请确认网络可用后手动执行 `docker pull <镜像名>`，然后重试。"
        return docker_unavailable_message(_classify_docker_problem(message))

    if isinstance(exc, ValueError):
        return f"{action}失败，请检查输入后重试。"

    return f"{action}失败，请稍后重试。"


__all__ = [
    "DOCKER_DESKTOP_URL",
    "DEFAULT_SUPPORTED_LANGUAGES",
    "docker_unavailable_message",
    "format_user_friendly_error",
]
