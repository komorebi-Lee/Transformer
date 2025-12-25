import sys
import os
import logging
from PyQt5.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QFont
import traceback

# 配置日志 - 修复level参数
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("grounded_coding.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class FixedAppLauncher:
    """修复的应用程序启动器"""

    def __init__(self):
        self.app = None
        self.splash = None
        self.main_window = None

    def show_splash(self):
        """显示启动画面"""
        try:
            # 创建简单的启动画面
            self.splash = QSplashScreen()
            self.splash.showMessage("正在启动扎根理论编码分析系统...\n初始化界面...",
                                    Qt.AlignBottom | Qt.AlignCenter, Qt.black)
            self.splash.show()

            # 强制刷新
            if self.app:
                self.app.processEvents()
        except Exception as e:
            logger.error(f"显示启动画面失败: {e}")

    def initialize_environment(self):
        """初始化环境"""
        try:
            # 动态导入，避免在导入时就出错
            from config import Config

            # 初始化目录
            Config.init_directories()

            # 检查必要的目录
            required_dirs = ['local_models', 'trained_models', 'standard_answers', 'data']
            for dir_name in required_dirs:
                dir_path = os.path.join(Config.BASE_DIR, dir_name)
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path, exist_ok=True)
                    logger.info(f"创建目录: {dir_path}")

            # 检查模型是否存在（但不强制要求）
            bert_path = os.path.join(Config.LOCAL_MODELS_DIR, Config.DEFAULT_MODEL_NAME)
            if not os.path.exists(bert_path):
                logger.warning("BERT模型不存在，将使用降级模式")
                return True, "BERT模型不存在，将使用降级模式"

            logger.info("环境初始化成功")
            return True, "环境初始化成功"

        except Exception as e:
            logger.error(f"环境初始化失败: {e}")
            return False, f"环境初始化失败: {str(e)}"

    def launch(self):
        """启动应用程序"""
        try:
            # 先创建QApplication
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("扎根理论编码分析系统")
            self.app.setApplicationVersion("3.0")
            self.app.setFont(QFont("Microsoft YaHei", 9))

            # 显示启动画面
            self.show_splash()

            # 延迟初始化主窗口
            QTimer.singleShot(100, self.initialize_and_show_main_window)

            # 运行应用
            result = self.app.exec_()
            logger.info("应用程序正常退出")
            return result

        except Exception as e:
            logger.error(f"启动失败: {e}")
            self.show_error_message(f"程序启动失败:\n{str(e)}")
            return 1

    def initialize_and_show_main_window(self):
        """初始化和显示主窗口"""
        try:
            # 初始化环境
            success, message = self.initialize_environment()

            if not success:
                logger.warning(message)
                # 即使环境初始化有问题也继续启动，但显示警告
                self.show_warning_message(message)

            # 导入主窗口 - 在QApplication创建后导入
            from main_window import MainWindow
            from PyQt5.QtCore import QSettings

            # 创建主窗口
            settings = QSettings("GroundedTheory", "CodingSystem")

            # 使用try-except捕获主窗口创建过程中的错误
            try:
                self.main_window = MainWindow(settings)

                # 关闭启动画面，显示主窗口
                if self.splash:
                    self.splash.finish(self.main_window)

                self.main_window.show()
                self.main_window.raise_()  # 确保窗口在前台
                self.main_window.activateWindow()  # 激活窗口

                # 显示初始化状态
                if success:
                    self.main_window.statusBar().showMessage("程序启动完成 - 模型初始化中...")
                    # 异步初始化模型
                    QTimer.singleShot(500, self.main_window.initialize_models_async)
                else:
                    self.main_window.statusBar().showMessage(f"程序启动完成 - {message}")

                logger.info("扎根理论编码分析系统启动成功，主窗口已显示")

            except Exception as e:
                logger.error(f"创建主窗口失败: {e}")
                raise

        except Exception as e:
            logger.error(f"启动主窗口失败: {e}")
            error_msg = f"启动主窗口失败:\n{str(e)}\n\n详细错误信息:\n{traceback.format_exc()}"
            self.show_error_message(error_msg)
            if self.splash:
                self.splash.close()
            self.app.quit()

    def show_error_message(self, message):
        """显示错误消息"""
        if self.app:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("启动错误")
            msg_box.setText(message)
            msg_box.exec_()
        else:
            print(f"错误: {message}")

    def show_warning_message(self, message):
        """显示警告消息"""
        if self.app:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("启动警告")
            msg_box.setText(message)
            msg_box.exec_()
        else:
            print(f"警告: {message}")


if __name__ == '__main__':
    launcher = FixedAppLauncher()
    sys.exit(launcher.launch())