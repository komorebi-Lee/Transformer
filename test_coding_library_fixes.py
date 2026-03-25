#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试编码库系统修复
"""

import json
import os
import shutil
from coding_library_manager import CodingLibraryManager


def test_duplicate_second_level_code():
    """测试二阶编码重复添加验证"""
    print("\n=== 测试二阶编码重复添加验证 ===")
    
    # 创建临时编码库文件
    temp_lib_path = "temp_coding_library.json"
    if os.path.exists(temp_lib_path):
        os.remove(temp_lib_path)
    
    # 初始化编码库管理器
    manager = CodingLibraryManager(temp_lib_path)
    
    # 创建测试数据
    test_data = {
        "version": "1.0",
        "created_at": "2024-01-01",
        "description": "测试编码库",
        "encoding_library": {
            "third_level_codes": [
                {
                    "id": 1,
                    "name": "测试三阶编码1",
                    "description": "测试三阶编码1描述",
                    "second_level_codes": [
                        {
                            "id": "TEST001",
                            "name": "测试二阶编码1",
                            "description": "测试二阶编码1描述"
                        }
                    ]
                }
            ]
        }
    }
    
    # 写入测试数据
    with open(temp_lib_path, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    # 重新加载编码库
    manager.load_library()
    
    # 测试1: 尝试添加相同ID的二阶编码
    print("测试1: 尝试添加相同ID的二阶编码")
    result = manager.add_second_level_code(1, "TEST001", "测试二阶编码2", "测试二阶编码2描述")
    print(f"结果: {'失败 (正确)' if not result else '成功 (错误)'}")
    
    # 测试2: 尝试添加相同名称的二阶编码
    print("测试2: 尝试添加相同名称的二阶编码")
    result = manager.add_second_level_code(1, "TEST002", "测试二阶编码1", "测试二阶编码1描述")
    print(f"结果: {'失败 (正确)' if not result else '成功 (错误)'}")
    
    # 测试3: 正常添加新的二阶编码
    print("测试3: 正常添加新的二阶编码")
    result = manager.add_second_level_code(1, "TEST002", "测试二阶编码2", "测试二阶编码2描述")
    print(f"结果: {'成功 (正确)' if result else '失败 (错误)'}")
    
    # 清理临时文件
    if os.path.exists(temp_lib_path):
        os.remove(temp_lib_path)
    
    print("二阶编码重复添加验证测试完成！")


def test_delete_second_level_code():
    """测试二阶编码删除功能"""
    print("\n=== 测试二阶编码删除功能 ===")
    
    # 创建临时编码库文件
    temp_lib_path = "temp_coding_library.json"
    if os.path.exists(temp_lib_path):
        os.remove(temp_lib_path)
    
    # 初始化编码库管理器
    manager = CodingLibraryManager(temp_lib_path)
    
    # 创建测试数据
    test_data = {
        "version": "1.0",
        "created_at": "2024-01-01",
        "description": "测试编码库",
        "encoding_library": {
            "third_level_codes": [
                {
                    "id": 1,
                    "name": "测试三阶编码1",
                    "description": "测试三阶编码1描述",
                    "second_level_codes": [
                        {
                            "id": "TEST001",
                            "name": "测试二阶编码1",
                            "description": "测试二阶编码1描述"
                        },
                        {
                            "id": "TEST002",
                            "name": "测试二阶编码2",
                            "description": "测试二阶编码2描述"
                        }
                    ]
                }
            ]
        }
    }
    
    # 写入测试数据
    with open(temp_lib_path, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    # 重新加载编码库
    manager.load_library()
    
    # 测试1: 尝试删除不存在的二阶编码
    print("测试1: 尝试删除不存在的二阶编码")
    result = manager.delete_second_level_code("TEST999")
    print(f"结果: {'失败 (正确)' if not result else '成功 (错误)'}")
    
    # 测试2: 正常删除二阶编码
    print("测试2: 正常删除二阶编码")
    result = manager.delete_second_level_code("TEST001")
    print(f"结果: {'成功 (正确)' if result else '失败 (错误)'}")
    
    # 验证删除是否成功
    second_level_codes = manager.get_all_second_level_codes()
    deleted_code_exists = any(code.get('id') == "TEST001" for code in second_level_codes)
    print(f"验证删除结果: {'已删除 (正确)' if not deleted_code_exists else '未删除 (错误)'}")
    
    # 清理临时文件
    if os.path.exists(temp_lib_path):
        os.remove(temp_lib_path)
    
    print("二阶编码删除功能测试完成！")


def test_duplicate_third_level_code():
    """测试三阶编码重复添加验证"""
    print("\n=== 测试三阶编码重复添加验证 ===")
    
    # 创建临时编码库文件
    temp_lib_path = "temp_coding_library.json"
    if os.path.exists(temp_lib_path):
        os.remove(temp_lib_path)
    
    # 初始化编码库管理器
    manager = CodingLibraryManager(temp_lib_path)
    
    # 创建测试数据
    test_data = {
        "version": "1.0",
        "created_at": "2024-01-01",
        "description": "测试编码库",
        "encoding_library": {
            "third_level_codes": [
                {
                    "id": 1,
                    "name": "测试三阶编码1",
                    "description": "测试三阶编码1描述",
                    "second_level_codes": []
                }
            ]
        }
    }
    
    # 写入测试数据
    with open(temp_lib_path, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    # 重新加载编码库
    manager.load_library()
    
    # 测试1: 尝试添加相同ID的三阶编码
    print("测试1: 尝试添加相同ID的三阶编码")
    result = manager.add_third_level_code(1, "测试三阶编码2", "测试三阶编码2描述")
    print(f"结果: {'失败 (正确)' if not result else '成功 (错误)'}")
    
    # 测试2: 尝试添加相同名称的三阶编码
    print("测试2: 尝试添加相同名称的三阶编码")
    result = manager.add_third_level_code(2, "测试三阶编码1", "测试三阶编码1描述")
    print(f"结果: {'失败 (正确)' if not result else '成功 (错误)'}")
    
    # 测试3: 正常添加新的三阶编码
    print("测试3: 正常添加新的三阶编码")
    result = manager.add_third_level_code(2, "测试三阶编码2", "测试三阶编码2描述")
    print(f"结果: {'成功 (正确)' if result else '失败 (错误)'}")
    
    # 清理临时文件
    if os.path.exists(temp_lib_path):
        os.remove(temp_lib_path)
    
    print("三阶编码重复添加验证测试完成！")


def test_delete_third_level_code():
    """测试三阶编码删除功能"""
    print("\n=== 测试三阶编码删除功能 ===")
    
    # 创建临时编码库文件
    temp_lib_path = "temp_coding_library.json"
    if os.path.exists(temp_lib_path):
        os.remove(temp_lib_path)
    
    # 初始化编码库管理器
    manager = CodingLibraryManager(temp_lib_path)
    
    # 创建测试数据
    test_data = {
        "version": "1.0",
        "created_at": "2024-01-01",
        "description": "测试编码库",
        "encoding_library": {
            "third_level_codes": [
                {
                    "id": 1,
                    "name": "测试三阶编码1",
                    "description": "测试三阶编码1描述",
                    "second_level_codes": [
                        {
                            "id": "TEST001",
                            "name": "测试二阶编码1",
                            "description": "测试二阶编码1描述"
                        }
                    ]
                },
                {
                    "id": 2,
                    "name": "测试三阶编码2",
                    "description": "测试三阶编码2描述",
                    "second_level_codes": []
                }
            ]
        }
    }
    
    # 写入测试数据
    with open(temp_lib_path, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    # 重新加载编码库
    manager.load_library()
    
    # 测试1: 尝试删除不存在的三阶编码
    print("测试1: 尝试删除不存在的三阶编码")
    result = manager.delete_third_level_code(999)
    print(f"结果: {'失败 (正确)' if not result else '成功 (错误)'}")
    
    # 测试2: 正常删除三阶编码（包含关联的二阶编码）
    print("测试2: 正常删除三阶编码（包含关联的二阶编码）")
    result = manager.delete_third_level_code(1)
    print(f"结果: {'成功 (正确)' if result else '失败 (错误)'}")
    
    # 验证删除是否成功
    third_level_codes = manager.get_all_third_level_codes()
    deleted_code_exists = any(code.get('id') == 1 for code in third_level_codes)
    print(f"验证三阶编码删除结果: {'已删除 (正确)' if not deleted_code_exists else '未删除 (错误)'}")
    
    # 验证关联的二阶编码是否也被删除
    second_level_codes = manager.get_all_second_level_codes()
    related_second_level_exists = any(code.get('third_level') == "测试三阶编码1" for code in second_level_codes)
    print(f"验证关联二阶编码删除结果: {'已删除 (正确)' if not related_second_level_exists else '未删除 (错误)'}")
    
    # 清理临时文件
    if os.path.exists(temp_lib_path):
        os.remove(temp_lib_path)
    
    print("三阶编码删除功能测试完成！")


def test_integration():
    """集成测试"""
    print("\n=== 集成测试 ===")
    
    # 创建临时编码库文件
    temp_lib_path = "temp_coding_library.json"
    if os.path.exists(temp_lib_path):
        os.remove(temp_lib_path)
    
    # 初始化编码库管理器
    manager = CodingLibraryManager(temp_lib_path)
    
    # 测试完整流程
    print("测试完整流程: 添加三阶编码 -> 添加二阶编码 -> 删除二阶编码 -> 删除三阶编码")
    
    # 添加三阶编码
    result = manager.add_third_level_code(1, "集成测试三阶编码", "集成测试三阶编码描述")
    print(f"添加三阶编码: {'成功' if result else '失败'}")
    
    # 添加二阶编码
    result = manager.add_second_level_code(1, "INT001", "集成测试二阶编码", "集成测试二阶编码描述")
    print(f"添加二阶编码: {'成功' if result else '失败'}")
    
    # 尝试重复添加二阶编码
    result = manager.add_second_level_code(1, "INT001", "集成测试二阶编码", "集成测试二阶编码描述")
    print(f"重复添加二阶编码: {'失败 (正确)' if not result else '成功 (错误)'}")
    
    # 删除二阶编码
    result = manager.delete_second_level_code("INT001")
    print(f"删除二阶编码: {'成功' if result else '失败'}")
    
    # 删除三阶编码
    result = manager.delete_third_level_code(1)
    print(f"删除三阶编码: {'成功' if result else '失败'}")
    
    # 清理临时文件
    if os.path.exists(temp_lib_path):
        os.remove(temp_lib_path)
    
    print("集成测试完成！")


if __name__ == "__main__":
    print("开始测试编码库系统修复...")
    
    test_duplicate_second_level_code()
    test_delete_second_level_code()
    test_duplicate_third_level_code()
    test_delete_third_level_code()
    test_integration()
    
    print("\n所有测试完成！")
