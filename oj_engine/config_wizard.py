"""
配置向导模块

提供交互式的配置向导，引导用户完成初始配置。
使用 questionary 库实现友好的命令行交互界面。
"""
import sys
import questionary
from .config_manager import (
    save_config,
    get_config_path,
    validate_api_key,
    get_default_config,
)


def run_config_wizard() -> bool:
    """
    运行配置向导
    
    Returns:
        如果配置成功则返回 True，否则返回 False
    """
    print("\n" + "=" * 60)
    print("欢迎使用 OJ Engine 配置向导")
    print("=" * 60)
    print("\n这将引导你完成初始配置\n")
    
    try:
        # 1. 选择 LLM 提供商
        provider_choice = questionary.select(
            "选择 AI 模型提供商:",
            choices=[
                questionary.Choice("OpenAI (GPT-4/GPT-3.5)", value="openai"),
                questionary.Choice("Anthropic (Claude)", value="anthropic"),
                questionary.Choice("自定义 OpenAI 兼容 API", value="custom"),
            ]
        ).ask()
        
        if provider_choice is None:
            print("\n✗ 配置已取消")
            return False
        
        # 2. 输入 API Key
        api_key = questionary.password(
            "请输入 API Key:"
        ).ask()
        
        if api_key is None:
            print("\n✗ 配置已取消")
            return False
        
        # 验证 API Key 格式
        if not validate_api_key(api_key, provider_choice):
            retry = questionary.confirm(
                "API Key 格式可能不正确，是否继续?",
                default=False
            ).ask()
            
            if not retry:
                print("\n✗ 配置已取消")
                return False
        
        # 3. 选择模型
        if provider_choice == "openai":
            model = questionary.select(
                "选择模型:",
                choices=[
                    "gpt-4",
                    "gpt-3.5-turbo",
                    "gpt-4-turbo",
                    "gpt-4o",
                ]
            ).ask()
        elif provider_choice == "anthropic":
            model = questionary.select(
                "选择模型:",
                choices=[
                    "claude-3-opus-20240229",
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307",
                ]
            ).ask()
        else:  # custom
            model = questionary.text(
                "请输入模型名称:",
                default="gpt-3.5-turbo"
            ).ask()
        
        if model is None:
            print("\n✗ 配置已取消")
            return False
        
        # 4. 配置 Base URL（可选）
        use_custom_base_url = questionary.confirm(
            "是否使用自定义 API Base URL?",
            default=False
        ).ask()
        
        if use_custom_base_url is None:
            print("\n✗ 配置已取消")
            return False
        
        base_url = None
        if use_custom_base_url:
            if provider_choice == "openai":
                default_url = "https://api.openai.com/v1"
            elif provider_choice == "anthropic":
                default_url = "https://api.anthropic.com/v1"
            else:
                default_url = "https://api.openai.com/v1"
            
            base_url = questionary.text(
                "请输入 API Base URL:",
                default=default_url
            ).ask()
            
            if base_url is None:
                print("\n✗ 配置已取消")
                return False
        
        # 5. 沙箱配置（可选，提供默认值）
        use_default_sandbox = questionary.confirm(
            "使用默认沙箱配置?",
            default=True
        ).ask()
        
        if use_default_sandbox is None:
            print("\n✗ 配置已取消")
            return False
        
        # 5. 构建配置
        config = get_default_config()
        config['llm'] = {
            "provider": provider_choice,
            "api_key": api_key,
            "model": model,
            "base_url": base_url
        }
        
        # 6. 显示配置摘要并确认
        print("\n" + "-" * 60)
        print("配置摘要:")
        print(f"  LLM 提供商: {provider_choice}")
        print(f"  模型: {model}")
        print(f"  API Key: {'*' * 8}{api_key[-4:]}")
        if base_url:
            print(f"  Base URL: {base_url}")
        else:
            print(f"  Base URL: 默认")
        print(f"  沙箱配置: {'默认' if use_default_sandbox else '自定义'}")
        print("-" * 60)
        
        confirm = questionary.confirm(
            "确认保存配置?",
            default=True
        ).ask()
        
        if confirm is None or not confirm:
            print("\n✗ 配置已取消")
            return False
        
        # 7. 保存配置
        if save_config(config):
            print("\n✓ 配置已保存!")
            print(f"  配置文件: {get_config_path()}")
            print("\n提示: 如需重新配置，请运行 'oj-engine configure'\n")
            return True
        else:
            print("\n✗ 配置保存失败")
            return False
    
    except KeyboardInterrupt:
        print("\n\n✗ 配置已取消")
        return False
    except Exception as e:
        print(f"\n✗ 配置过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False
