"""
配置管理模块

提供跨平台的用户配置管理功能，支持从用户目录加载和保存配置。
配置文件存储在平台标准的用户数据目录下。
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
import platformdirs


# 应用名称
APP_NAME = "oj-engine"
APP_AUTHOR = "oj-engine"
CONFIG_FILENAME = "config.json"


def get_config_dir() -> Path:
    """
    获取配置目录路径
    
    Returns:
        配置目录的 Path 对象
    """
    # 使用 platformdirs 获取平台标准的用户配置目录
    config_dir = platformdirs.user_config_dir(APP_NAME, APP_AUTHOR)
    return Path(config_dir)


def get_config_path() -> Path:
    """
    获取配置文件完整路径
    
    Returns:
        配置文件的 Path 对象
    """
    return get_config_dir() / CONFIG_FILENAME


def load_config() -> Optional[Dict[str, Any]]:
    """
    加载用户配置
    
    Returns:
        配置字典，如果配置文件不存在则返回 None
    """
    config_path = get_config_path()
    
    if not config_path.exists():
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8-sig') as f:
            config = json.load(f)
        return config
    except (json.JSONDecodeError, IOError) as e:
        print(f"警告: 无法加载配置文件 {config_path}: {e}")
        return None


def save_config(config: Dict[str, Any]) -> bool:
    """
    保存用户配置
    
    Args:
        config: 配置字典
        
    Returns:
        是否保存成功
    """
    config_dir = get_config_dir()
    config_path = get_config_path()
    
    try:
        # 创建配置目录（如果不存在）
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # 写入配置文件
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # 设置文件权限（仅当前用户可读写）
        # Windows 上 chmod 可能不起作用，但不会报错
        try:
            os.chmod(config_path, 0o600)
        except Exception:
            pass  # Windows 可能不支持
        
        return True
    
    except Exception as e:
        print(f"错误: 无法保存配置文件: {e}")
        return False


def is_configured() -> bool:
    """
    检查是否已配置
    
    Returns:
        如果存在有效配置则返回 True
    """
    config = load_config()
    
    if not config:
        return False
    
    # 检查必要字段
    if 'llm' not in config:
        return False
    
    llm_config = config['llm']
    if 'api_key' not in llm_config or 'provider' not in llm_config:
        return False
    
    return True


def validate_api_key(api_key: str, provider: str) -> bool:
    """
    验证 API Key 格式
    
    Args:
        api_key: API Key 字符串
        provider: 提供商名称（openai/anthropic/custom）
        
    Returns:
        如果格式基本正确则返回 True
    """
    if not api_key or len(api_key.strip()) < 10:
        return False
    
    # OpenAI API Key 通常以 sk- 开头
    if provider == 'openai' and not api_key.startswith('sk-'):
        return False
    
    # Anthropic API Key 通常以 sk-ant- 开头
    if provider == 'anthropic' and not api_key.startswith('sk-ant-'):
        return False
    
    return True


def mask_api_key(api_key: str) -> str:
    """
    隐藏 API Key，只显示最后4位
    
    Args:
        api_key: 完整的 API Key
        
    Returns:
        隐藏后的 API Key 字符串
    """
    if not api_key or len(api_key) < 8:
        return "********"
    
    return '*' * 8 + api_key[-4:]


def get_default_config() -> Dict[str, Any]:
    """
    获取默认配置模板
    
    Returns:
        默认配置字典
    """
    return {
        "version": "1.0",
        "llm": {
            "provider": "openai",
            "api_key": "",
            "model": "gpt-3.5-turbo",
            "base_url": None
        },
        "sandbox": {
            "image": "python:3.10-slim",
            "mem_limit": "512m",
            "cpu_quota": 50000
        },
        "output": {
            "default_dir": "outputs"
        }
    }
