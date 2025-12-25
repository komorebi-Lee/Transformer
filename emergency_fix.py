#!/usr/bin/env python3
"""
紧急修复脚本
修复常见的启动问题
"""

import os
import sys
import logging
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_sklearn_import():
    """修复sklearn导入问题"""
    print("🔧 修复sklearn导入问题...")
    try:
        # 检查sklearn安装
        result = subprocess.run([
            sys.executable, "-c",
            "import sklearn; print(f'sklearn版本: {sklearn.__version__}'); "
            "from sklearn.ensemble import RandomForestClassifier; print('RandomForestClassifier导入成功')"
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print("✅ sklearn导入正常")
            print(result.stdout)
            return True
        else:
            print("❌ sklearn导入有问题")
            print("错误输出:", result.stderr)

            # 尝试重新安装
            print("尝试重新安装scikit-learn...")
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "scikit-learn"], check=True)
            print("✅ scikit-learn重新安装完成")
            return True

    except Exception as e:
        print(f"❌ 修复sklearn失败: {e}")
        return False


def fix_model_files():
    """修复模型文件问题"""
    print("🔧 检查模型文件...")

    model_dirs = [
        "local_models/bert-base-chinese",
    ]

    for model_dir in model_dirs:
        if not os.path.exists(model_dir):
            print(f"❌ 模型目录不存在: {model_dir}")
            print("请运行: python download_models.py")
            return False
        else:
            print(f"✅ 模型目录存在: {model_dir}")

    return True


def create_fallback_config():
    """创建降级配置文件"""
    print("🔧 创建降级配置...")

    config_content = '''
import os

class Config:
    """应用程序配置 - 降级版本"""

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # 目录配置
    LOCAL_MODELS_DIR = os.path.join(BASE_DIR, "local_models")
    TRAINED_MODELS_DIR = os.path.join(BASE_DIR, "trained_models")
    STANDARD_ANSWERS_DIR = os.path.join(BASE_DIR, "standard_answers")
    DATA_DIR = os.path.join(BASE_DIR, "data")

    # 模型配置
    DEFAULT_MODEL_NAME = "bert-base-chinese"
    SENTENCE_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

    # 训练配置
    TRAINING_EPOCHS = 3
    BATCH_SIZE = 8
    LEARNING_RATE = 2e-5

    # 编码配置
    MAX_SENTENCE_LENGTH = 256
    SIMILARITY_THRESHOLD = 0.5
    MIN_SENTENCE_LENGTH = 5

    @classmethod
    def init_directories(cls):
        """初始化必要的目录"""
        directories = [
            cls.LOCAL_MODELS_DIR,
            cls.TRAINED_MODELS_DIR,
            cls.STANDARD_ANSWERS_DIR,
            cls.DATA_DIR
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"确保目录存在: {directory}")
'''

    with open("config_fallback.py", "w", encoding="utf-8") as f:
        f.write(config_content)

    print("✅ 降级配置文件已创建")


def main():
    print("=" * 60)
    print("扎根理论编码分析系统 - 紧急修复")
    print("=" * 60)

    fixes = [
        ("sklearn导入", fix_sklearn_import),
        ("模型文件", fix_model_files),
        ("降级配置", create_fallback_config),
    ]

    results = []
    for fix_name, fix_func in fixes:
        print(f"\n📋 执行修复: {fix_name}")
        try:
            result = fix_func()
            results.append((fix_name, result))
        except Exception as e:
            print(f"❌ {fix_name} 修复异常: {e}")
            results.append((fix_name, False))

    print("\n" + "=" * 60)
    print("修复结果汇总:")
    print("=" * 60)

    passed = 0
    for fix_name, result in results:
        status = "✅ 成功" if result else "❌ 失败"
        print(f"{fix_name}: {status}")
        if result:
            passed += 1

    print(f"\n总修复: {len(results)} | 成功: {passed} | 失败: {len(results) - passed}")

    if passed == len(results):
        print("\n🎉 所有修复成功！现在可以运行应用程序。")
        print("运行: python fixed_app_launcher.py")
        return 0
    else:
        print("\n⚠️ 部分修复失败，但应用程序仍可尝试运行")
        print("运行: python fixed_app_launcher.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())