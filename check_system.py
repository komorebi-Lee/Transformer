#!/usr/bin/env python3
"""
系统完整性检查脚本
检查所有潜在问题并给出修复建议
"""

import os
import sys
import importlib
import logging
import traceback


def check_logging_config():
    """检查日志配置"""
    print("🔍 检查日志配置...")
    try:
        # 测试正确的配置
        logging.basicConfig(
            level=logging.INFO,  # 正确的常量
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger("test_logger")
        logger.info("日志配置测试成功")
        print("✅ 日志配置正确")
        return True
    except Exception as e:
        print(f"❌ 日志配置错误: {e}")
        return False


def check_pyqt5():
    """检查PyQt5"""
    print("🔍 检查PyQt5...")
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt, QTimer
        from PyQt5.QtGui import QFont
        print("✅ PyQt5导入成功")
        return True
    except ImportError as e:
        print(f"❌ PyQt5导入失败: {e}")
        print("💡 解决方案: pip install PyQt5")
        return False


def check_ml_dependencies():
    """检查机器学习依赖"""
    print("🔍 检查机器学习依赖...")
    dependencies = [
        ("transformers", "AutoTokenizer"),
        ("torch",),
        ("numpy",),
        ("sklearn", "RandomForestClassifier"),
    ]

    all_ok = True
    for dep in dependencies:
        try:
            if len(dep) == 1:
                importlib.import_module(dep[0])
                print(f"✅ {dep[0]} 导入成功")
            else:
                module = importlib.import_module(dep[0])
                getattr(module, dep[1])
                print(f"✅ {dep[0]}.{dep[1]} 导入成功")
        except ImportError as e:
            print(f"❌ {dep[0]} 导入失败: {e}")
            all_ok = False

    return all_ok


def check_custom_modules():
    """检查自定义模块"""
    print("🔍 检查自定义模块...")
    modules = [
        "config",
        "model_manager",
        "data_processor",
        "enhanced_coding_generator",
        "grounded_theory_coder",
        "training_manager",
        "standard_answer_manager",
        "text_navigator",
        "word_exporter",
        "manual_coding_dialog"
    ]

    missing_modules = []
    for module in modules:
        try:
            importlib.import_module(module)
            print(f"✅ {module} 导入成功")
        except ImportError as e:
            print(f"❌ {module} 导入失败: {e}")
            missing_modules.append(module)

    if missing_modules:
        print(f"💡 缺失模块: {', '.join(missing_modules)}")
        return False
    return True


def check_model_files():
    """检查模型文件"""
    print("🔍 检查模型文件...")
    model_dirs = [
        "local_models/bert-base-chinese",
    ]

    required_files = [
        "config.json",
        "pytorch_model.bin",
        "tokenizer_config.json",
        "vocab.txt"
    ]

    all_ok = True
    for model_dir in model_dirs:
        if not os.path.exists(model_dir):
            print(f"❌ 模型目录不存在: {model_dir}")
            all_ok = False
            continue

        missing_files = []
        for file in required_files:
            file_path = os.path.join(model_dir, file)
            if not os.path.exists(file_path):
                missing_files.append(file)

        if missing_files:
            print(f"❌ {model_dir} 缺少文件: {', '.join(missing_files)}")
            all_ok = False
        else:
            print(f"✅ {model_dir} 文件完整")

    return all_ok


def test_main_window():
    """测试主窗口创建"""
    print("🔍 测试主窗口创建...")
    try:
        # 创建一个简单的QApplication用于测试
        from PyQt5.QtWidgets import QApplication
        app = QApplication([])

        # 测试导入主窗口
        from main_window import MainWindow
        from PyQt5.QtCore import QSettings

        settings = QSettings("GroundedTheory", "CodingSystem")
        window = MainWindow(settings)

        print("✅ 主窗口创建成功")
        return True
    except Exception as e:
        print(f"❌ 主窗口创建失败: {e}")
        print("详细错误信息:")
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("扎根理论编码分析系统 - 完整性检查")
    print("=" * 60)

    tests = [
        ("日志配置", check_logging_config),
        ("PyQt5", check_pyqt5),
        ("机器学习依赖", check_ml_dependencies),
        ("自定义模块", check_custom_modules),
        ("模型文件", check_model_files),
        ("主窗口", test_main_window),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 正在执行: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 60)
    print("检查结果汇总:")
    print("=" * 60)

    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\n总测试: {len(results)} | 通过: {passed} | 失败: {len(results) - passed}")

    if passed == len(results):
        print("\n🎉 所有检查通过！系统可以正常运行。")
        print("运行: python app_launcher.py")
        return 0
    else:
        print("\n⚠️  部分检查失败，请根据上面的提示修复问题。")
        print("建议先修复严重问题（PyQt5、日志配置等）")
        return 1


if __name__ == "__main__":
    sys.exit(main())