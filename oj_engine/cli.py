"""
OJ Engine CLI - 命令行工具

提供便捷的命令行接口来生成 OJ 题目测试数据包。
"""
import sys
import click
from pathlib import Path
from oj_engine.agent import ProblemGenerationAgent
from oj_engine.config_manager import is_configured, load_config, mask_api_key, get_config_path
from oj_engine.config_wizard import run_config_wizard


@click.group()
def main():
    """OJ Engine - AI OJ 题目生成工具
    
    使用 AI 自动生成 OJ 题目的完整测试数据包，包括标答代码、
    数据生成器和多组测试数据。
    """
    pass


@main.command()
@click.option('--file', '-f', 'file_path', type=click.Path(exists=True), 
              help='题目描述文件路径（UTF-8 编码）')
@click.option('--description', '-d', type=str, 
              help='题目描述文本（直接传入）')
@click.option('--max-iterations', '-m', default=20, type=int,
              help='Agent 最大迭代次数（默认: 20）')
@click.option('--output-dir', '-o', default='outputs', type=str,
              help='输出目录（默认: outputs）')
def generate(file_path, description, max_iterations, output_dir):
    """生成 OJ 题目测试数据包
    
    根据题目描述自动生成：
    - 标答代码 (solution.py)
    - 数据生成器 (generator.py)
    - 10组测试数据 (tests/ 目录)
    
    示例:
        # 从文件读取题目描述
        oj-engine generate -f problem.txt
        
        # 直接传入题目描述
        oj-engine generate -d "A+B Problem..."
        
        # 自定义参数
        oj-engine generate -f problem.txt -m 30 -o ./results
    """
    # 检查配置
    if not is_configured():
        click.echo("\n⚠ 检测到未配置，启动配置向导...\n")
        success = run_config_wizard()
        if not success:
            click.echo("\n✗ 配置失败，无法继续执行", err=True)
            sys.exit(1)
        click.echo("\n配置完成！继续执行任务...\n")
    
    # 验证参数
    if not file_path and not description:
        click.echo("错误: 必须提供 --file 或 --description 参数", err=True)
        click.echo("使用 'oj-engine generate --help' 查看帮助", err=True)
        sys.exit(1)
    
    # 读取题目描述
    if file_path:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                problem_description = f.read()
            click.echo(f"✓ 已从文件读取题目描述: {file_path}")
        except Exception as e:
            click.echo(f"错误: 无法读取文件 {file_path}: {e}", err=True)
            sys.exit(1)
    else:
        problem_description = description
    
    # 验证题目描述不为空
    if not problem_description or not problem_description.strip():
        click.echo("错误: 题目描述不能为空", err=True)
        sys.exit(1)
    
    # 显示配置信息
    click.echo("\n" + "=" * 80)
    click.echo("OJ Engine - 题目生成")
    click.echo("=" * 80)
    click.echo(f"\n配置:")
    click.echo(f"  - 最大迭代次数: {max_iterations}")
    click.echo(f"  - 输出目录: {output_dir}")
    click.echo(f"\n题目预览:")
    preview = problem_description[:200].strip()
    click.echo(f"  {preview}...")
    click.echo("-" * 80)
    
    # 执行 Agent
    try:
        click.echo("\n开始生成题目...\n")
        
        with ProblemGenerationAgent(max_iterations=max_iterations) as agent:
            result = agent.generate_problem(problem_description)
        
        # 显示结果
        click.echo("\n" + "=" * 80)
        click.echo("生成完成！")
        click.echo("=" * 80)
        
        # 检查是否有输出
        if "output" in result:
            output_preview = result["output"][:500]
            click.echo(f"\n输出预览（前500字符）:")
            click.echo(output_preview)
            click.echo("...")
        
        # 显示产物保存路径
        outputs_dir = Path(output_dir)
        if outputs_dir.exists():
            click.echo(f"\n✓ 产物已保存到: {outputs_dir.absolute()}")
            
            # 列出最新的输出
            output_dirs = sorted(outputs_dir.iterdir(), 
                               key=lambda x: x.stat().st_mtime, 
                               reverse=True)
            if output_dirs:
                latest = output_dirs[0]
                click.echo(f"\n最新输出:")
                click.echo(f"  {latest.name}")
                click.echo(f"\n文件列表:")
                for item in sorted(latest.rglob("*")):
                    if item.is_file():
                        rel_path = item.relative_to(latest)
                        click.echo(f"    {rel_path}")
        else:
            click.echo(f"\n⚠ 未找到输出目录: {outputs_dir}")
        
        click.echo("\n" + "=" * 80)
        
    except Exception as e:
        click.echo(f"\n✗ 错误: {str(e)}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@main.command()
def configure():
    """重新配置 OJ Engine"""
    click.echo("启动配置向导...")
    success = run_config_wizard()
    if not success:
        sys.exit(1)


@main.command()
def show_config():
    """显示当前配置（隐藏敏感信息）"""
    config = load_config()
    if config:
        click.echo("当前配置:")
        click.echo(f"  LLM 提供商: {config['llm']['provider']}")
        click.echo(f"  模型: {config['llm']['model']}")
        click.echo(f"  API Key: {mask_api_key(config['llm']['api_key'])}")
        if config['llm'].get('base_url'):
            click.echo(f"  Base URL: {config['llm']['base_url']}")
        click.echo(f"  配置文件: {get_config_path()}")
    else:
        click.echo("未配置，请运行 'oj-engine configure'")


if __name__ == "__main__":
    main()
