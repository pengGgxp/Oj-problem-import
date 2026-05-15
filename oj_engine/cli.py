"""
oj problem import CLI - 命令行工具

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
    """oj problem import - AI OJ 题目生成工具
    
    使用 AI 自动生成 OJ 题目的完整测试数据包，包括标答代码、
    数据生成器和多组测试数据。
    """
    pass


@main.command()
@click.option('--file', '-f', 'file_path', type=click.Path(exists=True), 
              help='题目描述文件路径（UTF-8 编码）')
@click.option('--description', '-d', type=str, 
              help='题目描述文本（直接传入）')
@click.option('--max-iterations', '-m', default=20, type=click.IntRange(1),
              help='Agent 最大迭代轮次（默认: 20，会自动换算为 LangGraph 图步数上限）')
@click.option('--output-dir', '-o', default='outputs', type=str,
              help='输出目录（默认: outputs）')
@click.option('--solution-file', '-s', type=click.Path(exists=True),
              help='官方题解/标程文件路径（可选，支持多语言）')
@click.option('--solution-language', '-l', type=str,
              help='官方题解语言（可选，如 python/cpp/c/java/javascript/go/rust）')
def generate(file_path, description, max_iterations, output_dir, solution_file, solution_language):
    """生成 OJ 题目测试数据包
    
    根据题目描述自动生成：
    - 标答代码 (solution.<ext>)
    - 数据生成器 (generator.py)
    - 10组测试数据 (tests/ 目录)
    
    示例:
        # 从文件读取题目描述
        oj-problem-import generate -f problem.txt
        
        # 直接传入题目描述
        oj-problem-import generate -d "A+B Problem..."

        # 使用官方 C++ 题解生成输出
        oj-problem-import generate -f problem.txt -s solution.cpp -l cpp
        
        # 自定义参数
        oj-problem-import generate -f problem.txt -m 30 -o ./results
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
        click.echo("使用 'oj-problem-import generate --help' 查看帮助", err=True)
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

    official_solution = ""
    if solution_file:
        try:
            with open(solution_file, 'r', encoding='utf-8') as f:
                official_solution = f.read()
            click.echo(f"✓ 已从文件读取官方题解: {solution_file}")
        except Exception as e:
            click.echo(f"错误: 无法读取官方题解文件 {solution_file}: {e}", err=True)
            sys.exit(1)
    
    # 显示配置信息
    click.echo("\n" + "=" * 80)
    click.echo("oj problem import - 题目生成")
    click.echo("=" * 80)
    click.echo(f"\n配置:")
    graph_limit = ProblemGenerationAgent.get_graph_recursion_limit(max_iterations)
    click.echo(f"  - Agent 最大迭代轮次: {max_iterations}")
    click.echo(f"  - LangGraph 图步数上限: {graph_limit}")
    click.echo(f"  - 输出目录: {output_dir}")
    if official_solution:
        click.echo(f"  - 官方题解: {solution_file}")
        click.echo(f"  - 题解语言: {solution_language or '自动判断'}")
    click.echo(f"\n题目预览:")
    preview = problem_description[:200].strip()
    click.echo(f"  {preview}...")
    click.echo("-" * 80)
    
    # 执行 Agent
    try:
        click.echo("\n开始生成题目...\n")
        
        with ProblemGenerationAgent(max_iterations=max_iterations) as agent:
            result = agent.generate_problem(
                problem_description,
                official_solution=official_solution,
                solution_language=solution_language or "",
            )
        
        # 显示结果
        click.echo("\n" + "=" * 80)
        click.echo("生成完成！")
        click.echo("=" * 80)
        
        # 检查是否有输出
        if "output" in result:
            output_preview = result["output"][:500]
            click.echo(f"\nAI 可见思考与总结（前500字符）:")
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
        if str(e).startswith("Agent 执行达到图步数上限"):
            sys.exit(1)

        import traceback
        traceback.print_exc()
        sys.exit(1)


@main.command()
def configure():
    """重新配置 oj problem import"""
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
        click.echo("未配置，请运行 'oj-problem-import configure'")


@main.command()
@click.argument('inputs', nargs=-1, required=True)
@click.option('--max-workers', '-w', default=4, type=int,
              help='最大并行工作进程数（默认: 4）')
@click.option('--max-iterations', '-m', default=20, type=click.IntRange(1),
              help='每个任务的 Agent 最大迭代轮次（默认: 20，会自动换算为 LangGraph 图步数上限）')
@click.option('--max-retries', '-r', default=2, type=int,
              help='每个任务的最大重试次数（默认: 2）')
@click.option('--output-dir', '-o', default='outputs', type=str,
              help='输出目录（默认: outputs）')
@click.option('--show-logs', is_flag=True,
              help='按任务分组显示完整执行日志（默认只显示失败任务日志尾部）')
@click.option('--log-lines', default=40, type=click.IntRange(0),
              help='失败任务默认显示的日志尾部行数，0 表示不显示（默认: 40）')
def batch(inputs, max_workers, max_iterations, max_retries, output_dir, show_logs, log_lines):
    """批量生成多个 OJ 题目
    
    支持单个文件、多个文件或目录。
    
    示例:
        # 单个文件
        oj-problem-import batch problem1.txt
        
        # 多个文件
        oj-problem-import batch problem1.txt problem2.txt problem3.txt
        
        # 目录（自动扫描所有 .txt/.md 文件）
        oj-problem-import batch ./problems/
        
        # 自定义参数
        oj-problem-import batch ./problems/ -w 8 -r 3
    """
    from .file_scanner import FileScanner
    from .task_scheduler import TaskScheduler
    from .task_models import TaskItem, TaskStatus
    import uuid
    
    # 检查配置
    if not is_configured():
        click.echo("\n⚠ 检测到未配置，启动配置向导...\n")
        success = run_config_wizard()
        if not success:
            click.echo("\n✗ 配置失败，无法继续执行", err=True)
            sys.exit(1)
        click.echo("\n配置完成！继续执行任务...\n")
    
    # 扫描所有输入
    all_files = []
    input_to_files = {}  # 记录每个输入路径对应的文件列表
    
    for input_path in inputs:
        try:
            files = FileScanner.scan_input(input_path)
            all_files.extend(files)
            input_to_files[input_path] = files
            click.echo(f"[OK] 扫描到 {len(files)} 个文件: {input_path}")
        except Exception as e:
            click.echo(f"[FAIL] 扫描失败 {input_path}: {e}", err=True)
    
    if not all_files:
        click.echo("错误: 未找到任何题目文件", err=True)
        sys.exit(1)
    
    click.echo(f"\n共发现 {len(all_files)} 个题目文件")
    
    # 创建任务列表，计算 base_path
    tasks = []
    for input_path_str in inputs:
        input_path = Path(input_path_str).resolve()  # 使用绝对路径
        files = input_to_files.get(input_path_str, [])
        
        for file_path in files:
            file_path_resolved = file_path.resolve()  # 也使用绝对路径
            
            # 计算 base_path：文件相对于输入路径的父目录
            if input_path.is_file():
                # 单个文件，base_path 为空
                base_path = ""
            elif input_path.is_dir():
                # 目录模式，计算相对路径
                try:
                    rel_path = file_path_resolved.relative_to(input_path)
                    # 取父目录作为 base_path
                    if rel_path.parent != Path('.'):
                        base_path = str(rel_path.parent)
                    else:
                        base_path = ""
                except ValueError:
                    # 如果无法计算相对路径，使用空字符串
                    base_path = ""
            else:
                base_path = ""
            
            tasks.append(
                TaskItem(
                    task_id=str(uuid.uuid4())[:8],
                    file_path=file_path,
                    problem_title=file_path.stem,
                    base_path=base_path
                )
            )
    
    # 执行任务
    try:
        scheduler = TaskScheduler(
            max_workers=max_workers,
            max_retries=max_retries,
            max_iterations=max_iterations,
            show_logs=show_logs,
            log_lines=log_lines,
        )
        
        results = scheduler.run_batch(tasks)
        
        # 显示详细报告
        scheduler.print_detailed_report()
        
        # 获取摘要
        summary = scheduler.get_summary()
        
        # 如果有失败任务，退出码为 1
        if summary['failed'] > 0:
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"\n✗ 调度器错误: {str(e)}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
