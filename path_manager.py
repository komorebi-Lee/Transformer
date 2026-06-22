import os
import sys
from contextlib import contextmanager
from typing import Iterator, Optional, TextIO


class PathManager:
    """统一管理项目路径与常用目录。

    设计目标：
    - 开发环境：默认以当前工作目录作为 BASE_DIR（便于测试隔离）。
    - 打包环境（PyInstaller 等）：以可执行文件所在目录作为 BASE_DIR。

    注意：该模块不得引入 torch/transformers 等重依赖，避免启动阶段崩溃。
    """

    _BASE_DIR: Optional[str] = None
    _IS_FROZEN: bool = False

    @classmethod
    def is_frozen(cls) -> bool:
        if getattr(sys, "frozen", False):
            cls._IS_FROZEN = True
            return True
        cls._IS_FROZEN = False
        return False

    @classmethod
    def get_base_dir(cls) -> str:
        if cls._BASE_DIR:
            return cls._BASE_DIR

        if cls.is_frozen():
            # onedir: _MEIPASS = _internal/（持久目录）
            # 模型、数据、缓存均在 _internal/ 内，__file__ 和 PathManager 路径均正确
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
        else:
            # 单元测试会 chdir 到临时目录并期望 base_dir 随之变化
            base_dir = os.path.abspath(os.getcwd())

        base_dir = os.path.normpath(base_dir)

        # 极端情况下 cwd/可执行文件目录不存在时兜底到本文件目录
        if not os.path.exists(base_dir):
            base_dir = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))

        cls._BASE_DIR = base_dir
        return base_dir

    @classmethod
    def get_writable_base_dir(cls) -> str:
        """用户数据持久存储基路径。

        开发模式：与 get_base_dir() 相同（当前工作目录）。
        打包模式：exe 所在目录（onefile 下与 _MEIPASS 不同，_MEIPASS 是临时目录）。

        用途：保存、导出、备份、标准答案等用户生成的需要持久化的数据。
        不应用于：模型、配置、FAISS 索引等打包资源（这些走 get_base_dir()）。
        """
        if cls.is_frozen():
            return os.path.normpath(os.path.dirname(os.path.abspath(sys.executable)))
        else:
            return cls.get_base_dir()

    @classmethod
    def join(cls, *paths: str) -> str:
        """拼接路径。

        - 若 paths[0] 为绝对路径：直接在其基础上拼接剩余部分
        - 否则：以 BASE_DIR 为前缀
        """
        base_dir = cls.get_base_dir()
        if not paths:
            return base_dir

        first = paths[0]
        if os.path.isabs(first):
            joined = os.path.join(first, *paths[1:])
        else:
            joined = os.path.join(base_dir, *paths)
        return os.path.normpath(joined)

    @classmethod
    def join_writable(cls, *paths: str) -> str:
        """拼接路径（用户数据基路径）。

        与 join() 相同，但使用 get_writable_base_dir() 作为前缀。
        用于用户生成的需要持久化的数据（保存、导出、备份等）。
        """
        base_dir = cls.get_writable_base_dir()
        if not paths:
            return base_dir

        first = paths[0]
        if os.path.isabs(first):
            joined = os.path.join(first, *paths[1:])
        else:
            joined = os.path.join(base_dir, *paths)
        return os.path.normpath(joined)

    @classmethod
    def get_absolute_path(cls, path: str) -> str:
        if os.path.isabs(path):
            return os.path.normpath(path)
        return cls.join(path)

    @classmethod
    def ensure_dir(cls, path: str) -> str:
        abs_path = cls.get_absolute_path(path)
        os.makedirs(abs_path, exist_ok=True)
        return abs_path

    @classmethod
    def exists(cls, path: str) -> bool:
        return os.path.exists(cls.get_absolute_path(path))

    @classmethod
    def is_file(cls, path: str) -> bool:
        return os.path.isfile(cls.get_absolute_path(path))

    @classmethod
    def is_dir(cls, path: str) -> bool:
        return os.path.isdir(cls.get_absolute_path(path))

    @classmethod
    def get_file_path(cls, filename: str, subdir: Optional[str] = None) -> str:
        if subdir:
            return cls.join(subdir, filename)
        return cls.join(filename)

    @classmethod
    def get_dir_path(cls, dirname: str) -> str:
        return cls.join(dirname)

    @classmethod
    def get_projects_dir(cls) -> str:
        return cls.join_writable("projects")

    @classmethod
    def get_data_dir(cls) -> str:
        return cls.join("data")

    @classmethod
    def get_local_models_dir(cls) -> str:
        return cls.join("local_models")

    @classmethod
    def get_trained_models_dir(cls) -> str:
        return cls.join("trained_models")

    @classmethod
    def get_standard_answers_dir(cls) -> str:
        return cls.join_writable("standard_answers")

    @classmethod
    def get_output_dir(cls) -> str:
        return cls.join_writable("output")

    @classmethod
    def get_cache_dir(cls) -> str:
        return cls.join("cache")

    @classmethod
    def get_logs_dir(cls) -> str:
        return cls.join_writable("logs")

    @classmethod
    def get_backup_dir(cls, base_dir: Optional[str] = None) -> str:
        if base_dir is None:
            base = cls.get_writable_base_dir()
            return os.path.normpath(os.path.join(base, "backups"))
        return os.path.join(base_dir, "backups")

    @classmethod
    def get_modifications_dir(cls, base_dir: Optional[str] = None) -> str:
        if base_dir is None:
            base = cls.get_writable_base_dir()
            return os.path.normpath(os.path.join(base, "modifications"))
        return os.path.join(base_dir, "modifications")

    @classmethod
    def get_manual_coding_save_dir(cls) -> str:
        return cls.join_writable("手动编码保存编码")

    @classmethod
    def get_manual_coding_tree_save_dir(cls) -> str:
        return cls.join_writable("手动编码编码树保存")

    @classmethod
    def get_auto_coding_save_dir(cls) -> str:
        return cls.join_writable("自动编码保存编码")

    @classmethod
    def get_last_position_file(cls) -> str:
        return cls.join_writable("last_coding_position.json")

    @classmethod
    def get_version_history_file(cls) -> str:
        return cls.join_writable("version_history.json")

    @classmethod
    def normalize_path(cls, path: str) -> str:
        if os.path.isabs(path):
            return os.path.normpath(path)
        return os.path.normpath(os.path.join(cls.get_base_dir(), path))

    @classmethod
    def get_relative_path(cls, path: str) -> str:
        abs_path = cls.get_absolute_path(path) if not os.path.isabs(path) else os.path.normpath(path)
        base_dir = cls.get_base_dir()
        try:
            common = os.path.commonpath([os.path.normpath(base_dir), os.path.normpath(abs_path)])
            if os.path.normpath(common) == os.path.normpath(base_dir):
                rel = os.path.relpath(abs_path, base_dir)
                return os.path.normpath(rel)
        except Exception:
            pass
        return os.path.normpath(abs_path)

    @classmethod
    @contextmanager
    def safe_open(
        cls,
        path: str,
        mode: str = "r",
        encoding: Optional[str] = None,
        **kwargs,
    ) -> Iterator[TextIO]:
        abs_path = cls.get_absolute_path(path) if not os.path.isabs(path) else os.path.normpath(path)

        # 需要写入时确保父目录存在
        write_like = any(ch in mode for ch in ("w", "a", "x", "+"))
        if write_like:
            parent = os.path.dirname(abs_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

        f = open(abs_path, mode=mode, encoding=encoding, **kwargs)
        try:
            yield f
        finally:
            f.close()

    @classmethod
    def init_all_directories(cls) -> None:
        dirs = [
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
        for d in dirs:
            cls.ensure_dir(d)


# 便捷函数（保持对外 API 简洁）

def get_base_dir() -> str:
    return PathManager.get_base_dir()


def join_path(*paths: str) -> str:
    return PathManager.join(*paths)


def get_abs_path(path: str) -> str:
    return PathManager.get_absolute_path(path)


def ensure_dir(path: str) -> str:
    return PathManager.ensure_dir(path)


def file_exists(path: str) -> bool:
    return PathManager.exists(path)
