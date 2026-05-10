"""
配置管理模块 - 使用 Pydantic Settings 管理环境变量
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class LLMSettings(BaseSettings):
    """LLM 相关配置"""
    
    # OpenAI API 配置
    openai_api_key: str = ""
    openai_base_url: Optional[str] = None  # 可选的自定义 base_url
    
    # 模型配置
    parser_model: str = "gpt-4"
    generator_model: str = "gpt-4"
    
    # 温度参数
    parser_temperature: float = 0.1
    generator_temperature: float = 0.2
    
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


class Settings(BaseSettings):
    """
    全局配置类
    
    整合所有子配置,提供统一的配置访问接口
    """
    
    llm: LLMSettings = LLMSettings()
    docker: DockerSettings = DockerSettings()
    workflow: WorkflowSettings = WorkflowSettings()
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    def get_llm_client(self, model_type: str = "parser"):
        """
        获取配置好的 LLM 客户端
        
        Args:
            model_type: 模型类型 ("parser" 或 "generator")
            
        Returns:
            ChatOpenAI 实例
        """
        from langchain_openai import ChatOpenAI
        
        if model_type == "parser":
            model_name = self.llm.parser_model
            temperature = self.llm.parser_temperature
        else:
            model_name = self.llm.generator_model
            temperature = self.llm.generator_temperature
        
        kwargs = {
            "model": model_name,
            "temperature": temperature,
            "extra_body": {"thinking": {"type": "disabled"}}
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
