import os
import sys
import logging
from typing import Optional, Union
from pathlib import Path


class PathManager:
    """
    统一的路径管理器，解决单文件打包场景下的文件路径处理问题
    
    功能特性：
    1. 支持单文件打包模式（PyInstaller、cx_Freeze 等）
    2. 跨平台路径规范化（Windows、macOS、Linux）
    3. 统一的路径拼接和访问接口
    4. 自动处理资源文件路径
    5. 提供路径验证和错误处理
    """

    # 基础路径 - 支持单文件打包
    # 使用 sys.argv[0] 可以正确处理打包后的可执行文件路径
    _BASE_DIR = None
    _IS_FROZEN = False

    @classmethod
    def get_base_dir(cls) -> str:
        """
        获取应用程序基础目录
        
        在开发环境中，返回脚本所在目录
        在打包后的单文件中，返回可执行文件所在目录
        
        Returns:
            str: 规范化后的基础目录路径
        """
        if cls._BASE_DIR is None:
            # 检查是否在打包环境中运行
            if getattr(sys, 'frozen', False):
                # 打包后的单文件模式
                cls._IS_FROZEN = True
                # 使用可执行文件所在目录作为基础目录
                # sys.executable 是可执行文件的完整路径
                cls._BASE_DIR = os.path.dirname(os.path.realpath(sys.executable))
            else:
                # 开发环境：使用脚本所在目录
                cls._BASE_DIR = os.path.dirname(os.path.realpath(sys.argv[0]))
            
            # 规范化路径，确保跨平台兼容性
            cls._BASE_DIR = os.path.normpath(cls._BASE_DIR)
            logging.info(f"基础路径已设置: {cls._BASE_DIR} (打包模式: {cls._IS_FROZEN})")
        
        return cls._BASE_DIR

    @classmethod
    def get_meipass_dir(cls) -> str:
        """
        获取 PyInstaller 单文件模式下的临时目录
        
        在 PyInstaller 单文件模式下，所有文件会解压到临时目录
        这个目录可以通过 sys._MEIPASS 访问
        
        Returns:
            str: 临时目录路径，如果不是打包模式则返回 None
        """
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            return os.path.normpath(sys._MEIPASS)
        return None

    @classmethod
    def is_frozen(cls) -> bool:
        """检查是否在打包环境中运行"""
        return cls._IS_FROZEN

    @classmethod
    def join(cls, *paths: Union[str, Path]) -> str:
        """
        拼接路径，使用基础目录作为起点
        
        Args:
            *paths: 要拼接的路径部分
            
        Returns:
            str: 规范化后的完整路径
        """
        base = cls.get_base_dir()
        result = os.path.join(base, *paths)
        return os.path.normpath(result)

    @classmethod
    def get_absolute_path(cls, relative_path: Union[str, Path]) -> str:
        """
        获取相对于基础目录的绝对路径
        
        Args:
            relative_path: 相对路径
            
        Returns:
            str: 规范化后的绝对路径
        """
        if isinstance(relative_path, Path):
            relative_path = str(relative_path)
        
        # 如果已经是绝对路径，直接返回
        if os.path.isabs(relative_path):
            return os.path.normpath(relative_path)
        
        return cls.join(relative_path)

    @classmethod
    def ensure_dir(cls, path: Union[str, Path]) -> str:
        """
        确保目录存在，不存在则创建
        
        Args:
            path: 目录路径
            
        Returns:
            str: 规范化后的目录路径
        """
        if isinstance(path, Path):
            path = str(path)
        
        # 获取绝对路径
        abs_path = cls.get_absolute_path(path)
        
        # 创建目录（如果不存在）
        os.makedirs(abs_path, exist_ok=True)
        logging.debug(f"确保目录存在: {abs_path}")
        
        return abs_path

    @classmethod
    def exists(cls, path: Union[str, Path]) -> bool:
        """
        检查路径是否存在
        
        Args:
            path: 要检查的路径
            
        Returns:
            bool: 路径是否存在
        """
        abs_path = cls.get_absolute_path(path)
        return os.path.exists(abs_path)

    @classmethod
    def is_file(cls, path: Union[str, Path]) -> bool:
        """检查路径是否为文件"""
        abs_path = cls.get_absolute_path(path)
        return os.path.isfile(abs_path)

    @classmethod
    def is_dir(cls, path: Union[str, Path]) -> bool:
        """检查路径是否为目录"""
        abs_path = cls.get_absolute_path(path)
        return os.path.isdir(abs_path)

    @classmethod
    def get_file_path(cls, filename: str, subdirectory: Optional[str] = None) -> str:
        """
        获取文件的完整路径
        
        Args:
            filename: 文件名
            subdirectory: 子目录（可选）
            
        Returns:
            str: 规范化后的文件路径
        """
        if subdirectory:
            return cls.join(subdirectory, filename)
        return cls.join(filename)

    @classmethod
    def get_dir_path(cls, dirname: str) -> str:
        """
        获取目录的完整路径
        
        Args:
            dirname: 目录名
            
        Returns:
            str: 规范化后的目录路径
        """
        return cls.join(dirname)

    @classmethod
    def get_projects_dir(cls) -> str:
        """获取项目目录路径"""
        return cls.get_dir_path("projects")

    @classmethod
    def get_data_dir(cls) -> str:
        """获取数据目录路径"""
        return cls.get_dir_path("data")

    @classmethod
    def get_local_models_dir(cls) -> str:
        """
        获取本地模型目录路径
        
        在打包后的单文件模式下，从临时目录中查找
        在开发环境中，从基础目录中查找
        
        Returns:
            str: 本地模型目录路径
        """
        # 在打包模式下，使用临时目录
        meipass_dir = cls.get_meipass_dir()
        if meipass_dir:
            local_models_path = os.path.join(meipass_dir, "local_models")
            logging.info(f"在打包模式下使用临时目录中的模型: {local_models_path}")
            return os.path.normpath(local_models_path)
        
        # 开发环境：使用基础目录
        return cls.get_dir_path("local_models")

    @classmethod
    def get_trained_models_dir(cls) -> str:
        """获取训练模型目录路径"""
        return cls.get_dir_path("trained_models")

    @classmethod
    def get_standard_answers_dir(cls) -> str:
        """获取标准答案目录路径"""
        return cls.get_dir_path("standard_answers")

    @classmethod
    def get_output_dir(cls) -> str:
        """获取输出目录路径"""
        return cls.get_dir_path("output")

    @classmethod
    def get_cache_dir(cls) -> str:
        """获取缓存目录路径"""
        return cls.get_dir_path("cache")

    @classmethod
    def get_logs_dir(cls) -> str:
        """获取日志目录路径"""
        return cls.get_dir_path("logs")

    @classmethod
    def get_backup_dir(cls, base_dir: str = None) -> str:
        """
        获取备份目录路径
        
        Args:
            base_dir: 基础目录，如果为 None 则使用标准答案目录
            
        Returns:
            str: 备份目录路径
        """
        if base_dir:
            return os.path.join(base_dir, "backups")
        return cls.join("standard_answers", "backups")

    @classmethod
    def get_modifications_dir(cls, base_dir: str = None) -> str:
        """
        获取修改记录目录路径
        
        Args:
            base_dir: 基础目录，如果为 None 则使用标准答案目录
            
        Returns:
            str: 修改记录目录路径
        """
        if base_dir:
            return os.path.join(base_dir, "modifications")
        return cls.join("standard_answers", "modifications")

    @classmethod
    def get_manual_coding_save_dir(cls) -> str:
        """获取手动编码保存目录路径"""
        return cls.join("projects", "手动编码保存编码")

    @classmethod
    def get_manual_coding_tree_save_dir(cls) -> str:
        """获取手动编码树保存目录路径"""
        return cls.join("projects", "手动编码编码树保存")

    @classmethod
    def get_last_position_file(cls) -> str:
        """获取最后编码位置文件路径"""
        return cls.join("projects", "last_coding_position.json")

    @classmethod
    def get_version_history_file(cls) -> str:
        """获取版本历史文件路径"""
        return cls.join("standard_answers", "version_history.json")

    @classmethod
    def normalize_path(cls, path: Union[str, Path]) -> str:
        """
        规范化路径，处理不同操作系统的路径格式差异
        
        Args:
            path: 要规范化的路径
            
        Returns:
            str: 规范化后的路径
        """
        if isinstance(path, Path):
            path = str(path)
        
        # 转换为绝对路径
        if not os.path.isabs(path):
            path = cls.get_absolute_path(path)
        
        # 规范化路径（处理 /、\、.. 等）
        return os.path.normpath(path)

    @classmethod
    def get_relative_path(cls, abs_path: Union[str, Path]) -> str:
        """
        获取相对于基础目录的相对路径
        
        Args:
            abs_path: 绝对路径
            
        Returns:
            str: 相对路径
        """
        if isinstance(abs_path, Path):
            abs_path = str(abs_path)
        
        abs_path = os.path.normpath(abs_path)
        base = cls.get_base_dir()
        
        try:
            rel_path = os.path.relpath(abs_path, base)
            # 如果相对路径以 .. 开头，说明不在基础目录下，返回绝对路径
            if rel_path.startswith('..'):
                return abs_path
            return rel_path
        except ValueError:
            # 跨驱动器（Windows）等情况，返回绝对路径
            return abs_path

    @classmethod
    def safe_open(cls, filename: str, mode: str = 'r', encoding: str = 'utf-8', **kwargs):
        """
        安全地打开文件，自动处理路径
        
        Args:
            filename: 文件名或路径
            mode: 打开模式
            encoding: 文件编码
            **kwargs: 其他传递给 open() 的参数
            
        Returns:
            文件对象
        """
        abs_path = cls.get_absolute_path(filename)
        return open(abs_path, mode=mode, encoding=encoding, **kwargs)

    @classmethod
    def init_all_directories(cls):
        """
        初始化所有必要的目录
        
        在应用启动时调用，确保所有需要的目录都存在
        """
        directories = [
            cls.get_projects_dir(),
            cls.get_data_dir(),
            cls.get_local_models_dir(),
            cls.get_trained_models_dir(),
            cls.get_standard_answers_dir(),
            cls.get_output_dir(),
            cls.get_cache_dir(),
            cls.get_logs_dir(),
            cls.get_backup_dir(),
            cls.get_modifications_dir(),
            cls.get_manual_coding_save_dir(),
            cls.get_manual_coding_tree_save_dir(),
        ]
        
        for directory in directories:
            cls.ensure_dir(directory)
            logging.info(f"目录已确保存在: {directory}")


# 便捷函数，提供更简洁的接口
def get_base_dir() -> str:
    """获取基础目录"""
    return PathManager.get_base_dir()


def join_path(*paths: Union[str, Path]) -> str:
    """拼接路径"""
    return PathManager.join(*paths)


def get_abs_path(path: Union[str, Path]) -> str:
    """获取绝对路径"""
    return PathManager.get_absolute_path(path)


def ensure_dir(path: Union[str, Path]) -> str:
    """确保目录存在"""
    return PathManager.ensure_dir(path)


def file_exists(path: Union[str, Path]) -> bool:
    """检查文件是否存在"""
    return PathManager.exists(path)


# 模块初始化时设置基础路径
PathManager.get_base_dir()
