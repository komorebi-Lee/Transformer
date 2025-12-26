import sys
import os
from cx_Freeze import setup, Executable

# 包含的文件和目录
include_files = [
    ("local_models/", "local_models"),
    ("trained_models/", "trained_models"),
    ("standard_answers/", "standard_answers"),
    ("data/", "data")
]

# 排除的模块
excludes = [
    "tkinter", "unittest", "email", "http", "urllib",
    "xmlrpc", "pydoc", "pdb", "multiprocessing", "test",
    "matplotlib", "scipy", "pytest", "notebook", "jupyter"
]

# 构建选项
build_exe_options = {
    "includes": [
        "PyQt5", "PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets",
        "sklearn", "sklearn.ensemble", "sklearn.cluster",
        "transformers", "torch", "sentence_transformers",
        "numpy", "pandas", "docx", "jieba", "re", "json", "logging"
    ],
    "excludes": excludes,
    "include_files": include_files,
    "optimize": 2,
    "packages": ["os", "sys", "collections", "datetime", "typing"],
    "include_msvcr": True,
    "build_exe": "build/grounded_theory_coder"
}

# 基础设置
base = None
if sys.platform == "win32":
    base = "Win32GUI"

# 应用程序信息
app_name = "扎根理论编码分析系统"
app_version = "3.0.0"
app_description = "基于人工智能的扎根理论三级编码分析工具"

setup(
    name=app_name,
    version=app_version,
    description=app_description,
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            "main.py",
            base=base,
            target_name="GroundedTheoryCoder.exe",
            icon="icon.ico"  # 可选：添加图标
        )
    ]
)