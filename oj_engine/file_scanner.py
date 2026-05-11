"""
File Scanner - 文件扫描器

负责识别和扫描题目文件，支持单个文件、多个文件或目录模式。
"""
from pathlib import Path
from typing import List, Union


class FileScanner:
    """扫描和识别题目文件"""
    
    # 支持的题目文件扩展名
    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.markdown'}
    
    @staticmethod
    def scan_input(input_path: Union[str, Path]) -> List[Path]:
        """
        扫描输入路径，返回题目文件列表
        
        Args:
            input_path: 可以是单个文件、多个文件（用逗号分隔）或目录
            
        Returns:
            题目文件路径列表
            
        Raises:
            FileNotFoundError: 路径不存在
        """
        if isinstance(input_path, str):
            # 检查是否是多个文件（逗号分隔）
            if ',' in input_path:
                files = [Path(p.strip()) for p in input_path.split(',')]
                valid_files = []
                for f in files:
                    if f.exists() and f.is_file():
                        valid_files.append(f)
                    else:
                        print(f"  ⚠ 跳过无效文件: {f}")
                return valid_files
            
            input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Path not found: {input_path}")
        
        if input_path.is_file():
            # 单个文件
            return [input_path]
        elif input_path.is_dir():
            # 扫描目录下所有支持的文件
            files = sorted([
                f for f in input_path.rglob('*') 
                if f.is_file() and f.suffix.lower() in FileScanner.SUPPORTED_EXTENSIONS
            ])
            
            if not files:
                print(f"  ⚠ 目录中未找到题目文件: {input_path}")
                print(f"     支持的格式: {', '.join(FileScanner.SUPPORTED_EXTENSIONS)}")
            
            return files
        else:
            raise FileNotFoundError(f"Invalid path: {input_path}")
    
    @staticmethod
    def validate_file(file_path: Path) -> bool:
        """
        验证文件是否为有效的题目文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            True 如果文件有效
        """
        if not file_path.exists():
            return False
        
        if not file_path.is_file():
            return False
        
        if file_path.suffix.lower() not in FileScanner.SUPPORTED_EXTENSIONS:
            return False
        
        # 检查文件是否非空
        if file_path.stat().st_size == 0:
            return False
        
        return True
    
    @staticmethod
    def scan_multiple_inputs(input_paths: List[Union[str, Path]]) -> List[Path]:
        """
        扫描多个输入路径，合并结果
        
        Args:
            input_paths: 输入路径列表
            
        Returns:
            所有找到的题目文件列表（去重）
        """
        all_files = []
        seen_paths = set()
        
        for input_path in input_paths:
            try:
                files = FileScanner.scan_input(input_path)
                for f in files:
                    # 去重
                    abs_path = f.resolve()
                    if abs_path not in seen_paths:
                        seen_paths.add(abs_path)
                        all_files.append(f)
            except Exception as e:
                print(f"  ✗ 扫描失败 {input_path}: {e}")
        
        return all_files
