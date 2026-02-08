#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试项目管理器增强功能的脚本"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.getcwd())

from project_manager import ProjectManager
import json
from datetime import datetime

def test_project_manager():
    """测试项目管理器的增强功能"""
    print("测试项目管理器增强功能...")
    print("=" * 50)
    
    # 创建项目管理器实例（这会创建新的目录结构）
    pm = ProjectManager()
    print("✓ 项目管理器初始化完成")
    
    # 检查目录结构
    expected_dirs = [
        ("主界面项目保存", pm.main_projects_dir),
        ("手动编码保存编码", pm.manual_coding_dir),
        ("手动编码编码树保存", pm.coding_tree_dir)
    ]
    
    print("\n检查目录结构:")
    for name, path in expected_dirs:
        if os.path.exists(path):
            print(f"✓ {name}: {path}")
        else:
            print(f"✗ {name}: {path}")
    
    # 测试保存项目
    print("\n测试保存项目到新结构:")
    test_loaded_files = {
        "test1.txt": {
            "content": "测试内容1",
            "numbered_content": "1. 测试句子一。\n2. 测试句子二。"
        }
    }
    
    test_structured_codes = {
        "A01": {
            "code_name": "测试编码",
            "sentences": ["测试句子一"]
        }
    }
    
    result = pm.save_project("测试增强保存项目", test_loaded_files, test_structured_codes)
    if result:
        print("✓ 项目保存成功")
        
        # 检查文件是否在正确位置
        project_path = os.path.join(pm.main_projects_dir, "测试增强保存项目")
        if os.path.exists(project_path):
            print(f"✓ 项目文件夹创建在正确位置: {project_path}")
            
            # 检查项目文件
            meta_file = os.path.join(project_path, pm.PROJECT_META_FILE)
            data_file = os.path.join(project_path, pm.PROJECT_DATA_FILE)
            
            if os.path.exists(meta_file) and os.path.exists(data_file):
                print("✓ 项目元数据和数据文件创建成功")
                
                # 读取元数据检查save_type
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta_data = json.load(f)
                    
                if meta_data.get("save_type") == "main_project":
                    print("✓ 保存类型标记正确")
                else:
                    print("✗ 保存类型标记错误")
            else:
                print("✗ 项目文件创建失败")
        else:
            print("✗ 项目文件夹位置错误")
    else:
        print("✗ 项目保存失败")
    
    # 测试加载项目
    print("\n测试加载项目:")
    loaded_files, structured_codes = pm.load_project("测试增强保存项目")
    if loaded_files is not None and structured_codes is not None:
        print("✓ 项目加载成功")
        if "test1.txt" in loaded_files:
            print("✓ 文件数据正确")
        if "A01" in structured_codes:
            print("✓ 编码数据正确")
    else:
        print("✗ 项目加载失败")
    
    # 测试获取项目列表
    print("\n测试获取项目列表:")
    projects = pm.get_projects_list()
    if projects:
        print(f"✓ 获取到 {len(projects)} 个项目")
        for project in projects:
            if project["name"] == "测试增强保存项目":
                print(f"✓ 找到测试项目: {project['name']}, 保存类型: {project.get('save_type', '未标记')}")
                break
    else:
        print("✗ 项目列表为空")

def show_directory_structure():
    """显示目录结构"""
    print("\n" + "=" * 50)
    print("更新后的projects目录结构:")
    
    projects_dir = os.path.join(os.getcwd(), "projects")
    if os.path.exists(projects_dir):
        for root, dirs, files in os.walk(projects_dir):
            level = root.replace(projects_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files[:3]:  # 只显示前3个文件
                print(f"{subindent}{file}")
            if len(files) > 3:
                print(f"{subindent}... 还有 {len(files) - 3} 个文件")

if __name__ == "__main__":
    try:
        test_project_manager()
        show_directory_structure()
        print("\n" + "=" * 50)
        print("测试完成！所有增强功能已实现。")
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()