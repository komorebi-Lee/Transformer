import os
import time
import importlib
import logging
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)

class HotReloader(QObject):
    """热部署类，用于监控文件变化并自动重新加载模块"""
    
    # 信号
    module_reloaded = pyqtSignal(str, str)  # 模块路径, 模块名称
    
    def __init__(self, watched_dirs=None, watched_extensions=None):
        super().__init__()
        
        # 要监控的目录
        self.watched_dirs = watched_dirs or ["."]
        # 要监控的文件扩展名
        self.watched_extensions = watched_extensions or [".py"]
        # 文件修改时间记录
        self.file_mtimes = {}
        # 定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_files)
        # 监控间隔（毫秒）
        self.interval = 2000
    
    def start(self):
        """开始监控"""
        # 初始化文件修改时间
        self._initialize_file_mtimes()
        # 启动定时器
        self.timer.start(self.interval)
        logger.info("热部署监控已启动")
    
    def stop(self):
        """停止监控"""
        self.timer.stop()
        logger.info("热部署监控已停止")
    
    def _initialize_file_mtimes(self):
        """初始化文件修改时间"""
        for directory in self.watched_dirs:
            for root, dirs, files in os.walk(directory):
                # 跳过隐藏目录
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    if any(file.endswith(ext) for ext in self.watched_extensions):
                        file_path = os.path.join(root, file)
                        try:
                            self.file_mtimes[file_path] = os.path.getmtime(file_path)
                        except Exception as e:
                            logger.warning(f"无法获取文件修改时间: {file_path}, 错误: {e}")
    
    def check_files(self):
        """检查文件变化"""
        for directory in self.watched_dirs:
            for root, dirs, files in os.walk(directory):
                # 跳过隐藏目录
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    if any(file.endswith(ext) for ext in self.watched_extensions):
                        file_path = os.path.join(root, file)
                        try:
                            current_mtime = os.path.getmtime(file_path)
                            
                            # 检查文件是否被修改
                            if file_path not in self.file_mtimes:
                                # 新文件
                                self.file_mtimes[file_path] = current_mtime
                                logger.info(f"发现新文件: {file_path}")
                            elif current_mtime > self.file_mtimes[file_path]:
                                # 文件被修改
                                self.file_mtimes[file_path] = current_mtime
                                self._reload_module(file_path)
                        except Exception as e:
                            logger.warning(f"检查文件时出错: {file_path}, 错误: {e}")
    
    def _reload_module(self, file_path):
        """重新加载模块"""
        try:
            # 转换文件路径为模块路径
            relative_path = os.path.relpath(file_path, os.getcwd())
            module_path = relative_path.replace(os.path.sep, '.').rsplit('.', 1)[0]
            
            # 检查模块是否已经导入
            if module_path in sys.modules:
                module = sys.modules[module_path]
                importlib.reload(module)
                logger.info(f"热重载模块: {module_path}")
                self.module_reloaded.emit(file_path, module_path)
            else:
                logger.info(f"文件已修改，但模块未导入: {file_path}")
        except Exception as e:
            logger.error(f"热重载模块失败: {file_path}, 错误: {e}")

# 全局热部署实例
hot_reloader = None

def init_hot_reload():
    """初始化热部署"""
    global hot_reloader
    if hot_reloader is None:
        # 监控当前目录及其子目录
        hot_reloader = HotReloader(watched_dirs=[os.getcwd()])
        hot_reloader.start()
    return hot_reloader

def stop_hot_reload():
    """停止热部署"""
    global hot_reloader
    if hot_reloader:
        hot_reloader.stop()
        hot_reloader = None

# 导入sys模块
import sys