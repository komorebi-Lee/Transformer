#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PKL文件内容输出器 - 尝试多种方法显示文件内容
"""

import pickle
import pickletools
import os
import sys
import io
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

def analyze_with_pickletools(file_path):
    """使用pickletools分析文件结构"""
    print("🔍 使用pickletools分析文件结构")
    print("=" * 50)
    
    try:
        with open(file_path, 'rb') as f:
            print("Pickle操作码序列:")
            print("-" * 30)
            
            # 捕获pickletools输出
            old_stdout = sys.stdout
            output = io.StringIO()
            sys.stdout = output
            
            try:
                pickletools.dis(f)
            finally:
                sys.stdout = old_stdout
            
            # 显示前50行
            lines = output.getvalue().split('\n')
            for i, line in enumerate(lines[:50]):
                print(f"{i+1:3d}: {line}")
            
            if len(lines) > 50:
                print(f"... (还有 {len(lines)-50} 行，已省略)")
                
        return True
        
    except Exception as e:
        print(f"❌ pickletools分析失败: {e}")
        return False

def extract_strings_from_file(file_path):
    """从文件中提取可读字符串"""
    print("\n📄 提取文件中的可读字符串")
    print("=" * 50)
    
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # 提取ASCII字符串
        strings = []
        current_string = ""
        
        for byte in data:
            if 32 <= byte <= 126:  # 可打印ASCII字符
                current_string += chr(byte)
            else:
                if len(current_string) >= 3:  # 只保留长度>=3的字符串
                    strings.append(current_string)
                current_string = ""
        
        # 添加最后一个字符串
        if len(current_string) >= 3:
            strings.append(current_string)
        
        print(f"找到 {len(strings)} 个字符串:")
        print("-" * 30)
        
        # 显示前50个字符串
        for i, s in enumerate(strings[:50]):
            if len(s) > 80:
                print(f"{i+1:3d}: {s[:77]}...")
            else:
                print(f"{i+1:3d}: {s}")
        
        if len(strings) > 50:
            print(f"... (还有 {len(strings)-50} 个字符串)")
            
        return strings
        
    except Exception as e:
        print(f"❌ 字符串提取失败: {e}")
        return []

def try_partial_pickle_load(file_path):
    """尝试部分加载pickle文件"""
    print("\n🔄 尝试部分加载pickle文件")
    print("=" * 50)
    
    try:
        with open(file_path, 'rb') as f:
            # 读取文件头
            header = f.read(100)
            print(f"文件头 (100字节): {header}")
            
            # 重置文件指针
            f.seek(0)
            
            # 尝试使用不同的加载方式
            methods = [
                ("标准pickle", lambda: pickle.load(f)),
                ("unsafe pickle", lambda: pickle.load(f, encoding='bytes')),
                ("latin1 pickle", lambda: pickle.load(f, encoding='latin1')),
            ]
            
            for method_name, load_func in methods:
                f.seek(0)  # 重置文件指针
                try:
                    print(f"\n尝试 {method_name}:")
                    result = load_func()
                    print(f"✅ {method_name} 成功!")
                    return analyze_loaded_data(result)
                except Exception as e:
                    print(f"❌ {method_name} 失败: {str(e)[:100]}...")
                    continue
    
    except Exception as e:
        print(f"❌ 文件读取失败: {e}")
    
    return None

def analyze_loaded_data(data):
    """分析已加载的数据"""
    print("\n📊 数据内容分析")
    print("=" * 50)
    
    print(f"数据类型: {type(data)}")
    
    if isinstance(data, dict):
        print(f"字典，包含 {len(data)} 个键:")
        for i, (key, value) in enumerate(data.items()):
            print(f"\n[{i+1}] 键: {key}")
            print(f"    类型: {type(value)}")
            
            # 显示值的详细信息
            if isinstance(value, str):
                if len(value) > 200:
                    print(f"    内容: {value[:200]}...")
                else:
                    print(f"    内容: {value}")
            elif isinstance(value, (int, float, bool)):
                print(f"    值: {value}")
            elif isinstance(value, (list, tuple)):
                print(f"    长度: {len(value)}")
                if len(value) > 0:
                    print(f"    第一个元素: {type(value[0])} = {str(value[0])[:50]}...")
            elif hasattr(value, '__dict__'):
                print(f"    对象属性: {list(value.__dict__.keys())[:10]}")
            elif hasattr(value, 'get_params'):
                print(f"    机器学习模型")
                try:
                    params = value.get_params()
                    important_params = {k: v for k, v in list(params.items())[:5]}
                    print(f"    主要参数: {important_params}")
                except:
                    pass
                    
            if hasattr(value, 'classes_'):
                try:
                    print(f"    类别: {list(value.classes_)[:10]}")
                except:
                    pass
    
    elif isinstance(data, (list, tuple)):
        print(f"{type(data).__name__}，包含 {len(data)} 个元素:")
        for i, item in enumerate(data[:10]):
            print(f"  [{i}] {type(item)}: {str(item)[:100]}...")
        if len(data) > 10:
            print(f"  ... (还有 {len(data)-10} 个元素)")
    
    else:
        print(f"单一对象: {type(data)}")
        if hasattr(data, '__dict__'):
            print(f"属性: {list(data.__dict__.keys())}")
        print(f"字符串表示: {str(data)[:500]}...")
    
    return data

def create_content_dump(data, strings, output_file="pkl_content_dump.txt"):
    """将所有内容导出到文件"""
    print(f"\n💾 导出内容到文件: {output_file}")
    print("=" * 50)
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("PKL文件内容导出\n")
            f.write("=" * 60 + "\n")
            f.write(f"导出时间: {datetime.now()}\n\n")
            
            if data is not None:
                f.write("1. 数据结构内容:\n")
                f.write("-" * 30 + "\n")
                f.write(f"数据类型: {type(data)}\n")
                f.write(f"字符串表示:\n{str(data)}\n\n")
                
            if strings:
                f.write("2. 提取的字符串:\n")
                f.write("-" * 30 + "\n")
                for i, s in enumerate(strings):
                    f.write(f"{i+1:4d}: {s}\n")
                f.write("\n")
            
            f.write("3. 详细信息:\n")
            f.write("-" * 30 + "\n")
            if data is not None:
                try:
                    import pprint
                    f.write("数据的详细表示:\n")
                    pprint.pprint(data, stream=f, depth=5, width=100)
                except:
                    f.write(f"无法使用pprint，原始表示:\n{data}")
        
        file_size = os.path.getsize(output_file) / 1024
        print(f"✅ 内容已导出到 {output_file} ({file_size:.1f} KB)")
        
    except Exception as e:
        print(f"❌ 导出失败: {e}")

def main():
    """主函数"""
    file_path = "trained_models/grounded_theory_latest.pkl"
    
    print("PKL文件内容输出器")
    print("=" * 60)
    print(f"目标文件: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return
    
    file_size = os.path.getsize(file_path) / (1024*1024)
    print(f"文件大小: {file_size:.2f} MB")
    print()
    
    # 方法1: 使用pickletools分析
    analyze_with_pickletools(file_path)
    
    # 方法2: 提取字符串
    strings = extract_strings_from_file(file_path)
    
    # 方法3: 尝试部分加载
    data = try_partial_pickle_load(file_path)
    
    # 导出所有内容到文件
    create_content_dump(data, strings)
    
    print("\n" + "=" * 60)
    print("内容输出完成!")
    print("详细内容已保存到 pkl_content_dump.txt")

if __name__ == "__main__":
    main()