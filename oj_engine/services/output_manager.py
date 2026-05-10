"""
产物管理器 - 负责保存和加载生成的代码、测试数据等产物
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


class OutputManager:
    """
    产物管理器
    
    功能:
    - 保存生成的代码和测试数据
    - 按时间戳组织输出目录
    - 提供产物查看和加载功能
    """
    
    def __init__(self, output_dir: str = "outputs"):
        """
        初始化产物管理器
        
        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def save_result(self, state: Dict[str, Any], problem_title: str = "unnamed") -> Path:
        """
        保存工作流执行结果
        
        Args:
            state: 工作流最终状态
            problem_title: 题目标题(用于命名)
            
        Returns:
            保存的目录路径
        """
        # 创建带时间戳的输出目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = self._sanitize_filename(problem_title)
        output_path = self.output_dir / f"{timestamp}_{safe_title}"
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"\n[OutputManager] 保存产物到: {output_path}")
        
        # 1. 保存元数据
        metadata = {
            "timestamp": timestamp,
            "problem_title": problem_title,
            "status": state.get("status"),
            "retry_count": state.get("retry_count", 0),
            "created_at": datetime.now().isoformat()
        }
        
        if state.get("requirements"):
            req = state["requirements"]
            metadata["requirements"] = {
                "time_limit": req.time_limit,
                "memory_limit": req.memory_limit,
                "input_format": req.input_format,
                "output_format": req.output_format,
                "variable_ranges": req.variable_ranges,
                "constraints": req.constraints
            }
        
        if state.get("execution_result"):
            exec_result = state["execution_result"]
            metadata["execution"] = {
                "status": exec_result.status,
                "exit_code": exec_result.exit_code,
                "execution_time": exec_result.execution_time,
                "memory_usage": exec_result.memory_usage,
                "error_type": exec_result.error_type
            }
        
        metadata_file = output_path / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"  ✓ 保存元数据: metadata.json")
        
        # 2. 保存生成的代码
        if state.get("codes"):
            codes = state["codes"]
            code_dir = output_path / "codes"
            code_dir.mkdir(exist_ok=True)
            
            # 标答代码
            solution_ext = self._get_file_extension(codes.solution_language)
            solution_file = code_dir / f"solution{solution_ext}"
            with open(solution_file, 'w', encoding='utf-8') as f:
                f.write(codes.solution_code)
            print(f"  ✓ 保存标答: solution{solution_ext}")
            
            # 数据生成器
            generator_file = code_dir / "generator.py"
            with open(generator_file, 'w', encoding='utf-8') as f:
                f.write(codes.generator_code)
            print(f"  ✓ 保存生成器: generator.py")
            
            # SPJ (如果有)
            if codes.checker_code:
                checker_file = code_dir / "checker.cpp"
                with open(checker_file, 'w', encoding='utf-8') as f:
                    f.write(codes.checker_code)
                print(f"  ✓ 保存SPJ: checker.cpp")
        
        # 3. 保存测试数据
        if state.get("test_cases"):
            test_data_file = output_path / "test_cases.json"
            with open(test_data_file, 'w', encoding='utf-8') as f:
                json.dump(state["test_cases"], f, ensure_ascii=False, indent=2)
            print(f"  ✓ 保存测试数据: test_cases.json ({len(state['test_cases'])} 组)")
        
        # 4. 保存错误历史
        if state.get("error_history"):
            error_history_file = output_path / "error_history.json"
            with open(error_history_file, 'w', encoding='utf-8') as f:
                json.dump(state["error_history"], f, ensure_ascii=False, indent=2)
            print(f"  ✓ 保存错误历史: error_history.json")
        
        # 5. 保存 README
        readme_file = output_path / "README.md"
        self._generate_readme(readme_file, metadata, state)
        print(f"  ✓ 生成说明文档: README.md")
        
        print(f"\n[OutputManager] 产物保存完成!")
        print(f"  目录: {output_path.absolute()}")
        
        return output_path
    
    def load_result(self, output_path: Path) -> Dict[str, Any]:
        """
        加载之前保存的产物
        
        Args:
            output_path: 产物目录路径
            
        Returns:
            加载的状态数据
        """
        if not output_path.exists():
            raise FileNotFoundError(f"产物目录不存在: {output_path}")
        
        # 加载元数据
        metadata_file = output_path / "metadata.json"
        if not metadata_file.exists():
            raise FileNotFoundError(f"元数据文件不存在: {metadata_file}")
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # 加载代码
        codes = {}
        code_dir = output_path / "codes"
        if code_dir.exists():
            for file in code_dir.iterdir():
                if file.is_file():
                    with open(file, 'r', encoding='utf-8') as f:
                        codes[file.name] = f.read()
        
        # 加载测试数据
        test_cases = []
        test_data_file = output_path / "test_cases.json"
        if test_data_file.exists():
            with open(test_data_file, 'r', encoding='utf-8') as f:
                test_cases = json.load(f)
        
        return {
            "metadata": metadata,
            "codes": codes,
            "test_cases": test_cases
        }
    
    def list_outputs(self) -> list:
        """
        列出所有保存的产物
        
        Returns:
            产物目录列表
        """
        if not self.output_dir.exists():
            return []
        
        outputs = []
        for item in sorted(self.output_dir.iterdir()):
            if item.is_dir():
                metadata_file = item / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    outputs.append({
                        "path": item,
                        "title": metadata.get("problem_title", "unnamed"),
                        "timestamp": metadata.get("timestamp", ""),
                        "status": metadata.get("status", "unknown")
                    })
        
        return outputs
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名,移除非法字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            清理后的文件名
        """
        # 移除非法字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # 限制长度
        if len(filename) > 50:
            filename = filename[:50]
        
        return filename.strip()
    
    def _get_file_extension(self, language: str) -> str:
        """
        根据语言获取文件扩展名
        
        Args:
            language: 编程语言
            
        Returns:
            文件扩展名(包含点号)
        """
        extensions = {
            "python": ".py",
            "cpp": ".cpp",
            "c": ".c",
            "java": ".java",
            "javascript": ".js"
        }
        return extensions.get(language.lower(), ".txt")
    
    def _generate_readme(self, readme_file: Path, metadata: dict, state: Dict[str, Any]):
        """
        生成 README 说明文档
        
        Args:
            readme_file: README 文件路径
            metadata: 元数据
            state: 工作流状态
        """
        content = f"""# {metadata.get('problem_title', 'OJ Problem')}

## 基本信息

- **生成时间**: {metadata.get('created_at', 'N/A')}
- **状态**: {metadata.get('status', 'unknown')}
- **重试次数**: {metadata.get('retry_count', 0)}

## 题目要求

"""
        
        if metadata.get('requirements'):
            req = metadata['requirements']
            content += f"""- **时间限制**: {req.get('time_limit', 'N/A')}s
- **内存限制**: {req.get('memory_limit', 'N/A')}MB
- **输入格式**: {req.get('input_format', 'N/A')}
- **输出格式**: {req.get('output_format', 'N/A')}
"""
        
        content += """
## 文件说明

- `codes/solution.*` - 标答代码
- `codes/generator.py` - 数据生成器
- `codes/checker.cpp` - 特殊判题器(如果有)
- `test_cases.json` - 测试数据
- `metadata.json` - 元数据
- `error_history.json` - 错误历史(如果有)

## 使用方法

### 运行标答

```bash
cd codes
python solution.py < input.txt
```

### 生成测试数据

```bash
cd codes
python generator.py > input.txt
```

### 批量测试

```bash
# 使用提供的测试脚本
python ../run_tests.py
```

## 执行结果

"""
        
        if metadata.get('execution'):
            exec_info = metadata['execution']
            content += f"""- **执行状态**: {exec_info.get('status', 'N/A')}
- **退出码**: {exec_info.get('exit_code', 'N/A')}
- **内存使用**: {exec_info.get('memory_usage', 0):.2f}MB
"""
        
        content += "\n---\n\n*Generated by OJ Engine*\n"
        
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(content)
