"""
配置管理模块 - 使用 Pydantic Settings 管理环境变量

支持双配置源：
1. 用户配置（优先级高）：从用户目录的 config.json 加载
2. 环境变量（回退）：从 .env 文件或系统环境变量加载
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Dict, Any
import os


def _load_user_config_to_env() -> None:
    """
    从用户配置文件加载配置并设置到环境变量
    
    这是一个独立的函数，负责将用户配置转换为环境变量，
    这样 Settings 类就不需要直接依赖 config_manager
    """
    try:
        from ..config_manager import load_config
        user_config = load_config()
        
        if not user_config or 'llm' not in user_config:
            return
        
        llm_config = user_config['llm']
        
        # 提取配置值
        api_key = llm_config.get('api_key', '')
        model = llm_config.get('model')
        temperature = llm_config.get('temperature')
        base_url = llm_config.get('base_url')
        
        # 设置环境变量（优先级高于 .env 文件）
        if api_key:
            os.environ.setdefault('LLM_OPENAI_API_KEY', api_key)
            os.environ.setdefault('OPENAI_API_KEY', api_key)
        
        if model:
            os.environ.setdefault('LLM_MODEL', model)
        
        if temperature is not None:
            os.environ.setdefault('LLM_TEMPERATURE', str(temperature))
        
        if base_url:
            os.environ.setdefault('LLM_OPENAI_BASE_URL', base_url)
            os.environ.setdefault('OPENAI_BASE_URL', base_url)
    except Exception:
        # 如果加载失败，静默忽略，使用默认配置
        pass


class LLMSettings(BaseSettings):
    """LLM 相关配置"""
    
    # OpenAI API 配置
    openai_api_key: str = ""
    openai_base_url: Optional[str] = None  # 可选的自定义 base_url
    
    # 模型配置（统一使用一个模型）
    model: str = "gpt-4"
    
    # 温度参数
    temperature: float = 0.2
    
    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class DockerSettings(BaseSettings):
    """Docker 沙箱配置"""
    
    # 默认镜像
    default_image: str = "python:3.10-slim"
    
    # 资源限制
    default_mem_limit: str = "512m"
    default_cpu_quota: int = 50000
    
    # 超时设置
    default_timeout: int = 30
    
    model_config = SettingsConfigDict(
        env_prefix="DOCKER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class WorkflowSettings(BaseSettings):
    """工作流配置"""
    
    # 重试配置
    max_retries: int = 3
    
    model_config = SettingsConfigDict(
        env_prefix="WORKFLOW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# 在模块加载时，先从用户配置加载到环境变量
_load_user_config_to_env()


class Settings(BaseSettings):
    """
    全局配置类
    
    整合所有子配置,提供统一的配置访问接口
    配置优先级：用户配置 > 环境变量 > .env 文件 > 默认值
    """
    
    llm: LLMSettings = LLMSettings()
    docker: DockerSettings = DockerSettings()
    workflow: WorkflowSettings = WorkflowSettings()
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    def get_llm_client(self):
        """
        获取配置好的 LLM 客户端
        
        Returns:
            ChatOpenAI 实例
        """
        from langchain_openai import ChatOpenAI
        
        model_name = self.llm.model
        temperature = self.llm.temperature
        
        kwargs = {
            "model": model_name,
            "temperature": temperature,
            "extra_body": {"thinking": {"type": "disabled"}} if "deepseek" in model_name else None
        }
        
        # 如果设置了 API Key,优先使用配置中的值
        if self.llm.openai_api_key:
            kwargs["api_key"] = self.llm.openai_api_key
        # 否则让 LangChain 从环境变量 OPENAI_API_KEY 读取
        
        # 如果设置了自定义 base_url
        if self.llm.openai_base_url:
            kwargs["base_url"] = self.llm.openai_base_url
        
        return ChatOpenAI(**kwargs)


# 全局配置实例 (单例模式)
settings = Settings()


def get_settings() -> Settings:
    """
    获取配置实例
    
    Returns:
        Settings 实例
    """
    return settings
