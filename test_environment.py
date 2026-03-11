#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境测试脚本 - 用于验证是否可以读取grounded_theory_latest.pkl
"""

import sys
import os
from datetime import datetime

def check_environment():
    """检查Python环境是否满足要求"""
    print("🔍 环境检查")
    print("=" * 40)
    
    # Python版本
    print(f"Python版本: {sys.version.split()[0]}")
    
    # 检查必需模块
    modules = {
        'pickle': '内置模块',
        'numpy': None,
        'sklearn': None, 
        'joblib': None
    }
    
    for module_name in modules:
        try:
            if module_name == 'sklearn':
                module = __import__(module_name)
                modules[module_name] = getattr(module, '__version__', '未知版本')
            elif module_name == 'pickle':
                modules[module_name] = '内置模块 ✅'
            else:
                module = __import__(module_name)
                modules[module_name] = getattr(module, '__version__', '已安装')
        except ImportError:
            modules[module_name] = '❌ 未安装'
        except Exception as e:
            modules[module_name] = f'❌ 错误: {str(e)[:30]}...'
    
    # 显示结果
    print("\n模块状态:")
    for name, version in modules.items():
        status = "✅" if "❌" not in str(version) else "❌"
        print(f"  {name:<10}: {version} {status}")
    
    return all("❌" not in str(v) for v in modules.values())

def check_file():
    """检查模型文件"""
    print("\n📁 文件检查")
    print("=" * 40)
    
    file_path = "trained_models/grounded_theory_latest.pkl"
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    # 文件基本信息
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
    
    print(f"✅ 文件存在: {file_path}")
    print(f"   大小: {size_mb:.2f} MB")
    print(f"   修改时间: {mtime}")
    
    # 检查文件头
    try:
        with open(file_path, 'rb') as f:
            header = f.read(10)
        print(f"   文件头: {header}")
        print("✅ 文件可读取")
        return True
    except Exception as e:
        print(f"❌ 文件读取错误: {e}")
        return False

def simple_load_test():
    """简单加载测试"""
    print("\n🧪 加载测试")
    print("=" * 40)
    
    try:
        import pickle
        import warnings
        warnings.filterwarnings('ignore')
        
        file_path = "trained_models/grounded_theory_latest.pkl"
        
        print("正在尝试加载模型...")
        with open(file_path, 'rb') as f:
            model = pickle.load(f)
        
        print("✅ 模型加载成功!")
        print(f"   数据类型: {type(model)}")
        
        if isinstance(model, dict):
            print(f"   包含 {len(model)} 个键: {list(model.keys())}")
        
        return True, model
        
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        print(f"   错误类型: {type(e).__name__}")
        return False, None

def provide_next_steps(env_ok, file_ok, load_ok):
    """提供下一步建议"""
    print("\n📋 建议")
    print("=" * 40)
    
    if env_ok and file_ok and load_ok:
        print("🎉 一切正常! 你可以:")
        print("   1. 使用提供的代码脚本读取模型")
        print("   2. 开始分析模型数据")
        print("   3. 进行预测或其他机器学习任务")
        return
    
    if not file_ok:
        print("📁 文件问题:")
        print("   1. 确认文件路径正确")
        print("   2. 检查文件是否被移动或删除")
        print("   3. 重新训练并保存模型")
        return
    
    if not env_ok:
        print("🔧 环境问题:")
        print("   1. 运行: pip install --upgrade numpy scikit-learn joblib")
        print("   2. 或创建新的conda环境")
        print("   3. 使用Docker环境")
        return
    
    if not load_ok:
        print("⚡ 加载问题:")
        print("   1. 版本兼容性问题 - 升级sklearn到1.7+")
        print("   2. numpy._core问题 - 重新安装numpy") 
        print("   3. 在原始训练环境中读取")

def main():
    """主函数"""
    print("grounded_theory_latest.pkl 环境测试")
    print("=" * 60)
    print("这个脚本帮你诊断为什么无法读取模型文件")
    
    # 环境检查
    env_ok = check_environment()
    
    # 文件检查
    file_ok = check_file()
    
    # 加载测试
    load_ok, model = simple_load_test()
    
    # 总结和建议
    provide_next_steps(env_ok, file_ok, load_ok)
    
    print("\n" + "=" * 60)
    if env_ok and file_ok and load_ok:
        print("✅ 诊断完成 - 环境就绪!")
        return model
    else:
        print("❌ 诊断完成 - 发现问题，请按建议修复")
        return None

if __name__ == "__main__":
    result = main()
    
    if result:
        print("\n🚀 模型已加载，存储在变量 'result' 中")
    else:
        print("\n🛠️  请按照建议修复问题后重新运行")