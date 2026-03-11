import pickle
import os
import numpy as np
from datetime import datetime


def create_simple_usage_script(model_data):  # 修改1：参数名改为model_data（与实际变量一致）
    """生成简单的模型使用脚本"""
    print("\n💡 使用示例:")
    print("---------------")
    print("# 访问模型数据")
    print("model_data['classifier']  # 获取 classifier")
    print("")
    print("# 使用分类器")
    print("classifier = model_data['classifier']")
    print("# predictions = classifier.predict(X)  # X为特征矩阵")
    print("# probabilities = classifier.predict_proba(X)")
    print("")
    print("📋 导出数据到文件:")
    print("# 保存为新的pickle文件")
    print("with open('exported_model.pkl', 'wb') as f:")
    print("    pickle.dump(model_data, f)")

    # 修改2：打印正确的变量名model_data，而非未定义的model
    print(f"\n模型类型: {type(model_data)}")


def main():
    print("强制模型读取器 - 忽略版本警告")
    print("=" * 50)

    # 目标文件路径
    model_path = "trained_models/grounded_theory_latest.pkl"
    print(f"目标文件: {model_path}")

    # 获取文件信息
    file_size = os.path.getsize(model_path) / (1024 * 1024)
    file_mtime = datetime.fromtimestamp(os.path.getmtime(model_path))
    print(f"📄 大小: {file_size:.2f} MB")
    print(f"🕐 修改: {file_mtime}")

    print("\n🔄 正在读取模型...")
    # 尝试读取模型
    model_data = None
    try:
        print("  尝试 标准pickle...")
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        print("  ✅ 标准pickle 成功!")
    except Exception as e:
        print(f"  ❌ 标准pickle 失败: {e}")
        raise

    if model_data is None:
        raise Exception("无法读取模型文件")

    print("\n✅ 模型读取成功! (使用 标准pickle)")
    print(f"🔍 数据类型: {type(model_data)}")

    # 模型结构分析（省略原有分析代码，保持不变）
    print("\n📊 模型结构分析:")
    print("-------------------------")
    # ... 此处保留你原有模型分析代码 ...

    # 修改3：调用函数时传入正确的变量名model_data
    create_simple_usage_script(model_data)

    return model_data


if __name__ == "__main__":
    model_result = main()