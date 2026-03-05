# 运行时钩子，用于修改 transformers 的版本检查逻辑和处理导入错误
import sys
import os
import importlib

# 检查是否在打包环境中运行
if getattr(sys, 'frozen', False):
    # 在打包环境中，修改 transformers 的版本检查逻辑
    print("Running in frozen environment, patching transformers dependency check...")
    
    # 先导入 transformers 相关模块
    try:
        import transformers.utils.versions
        
        # 保存原始的 require_version 函数
        original_require_version = transformers.utils.versions.require_version
        
        # 定义新的 require_version 函数，跳过版本检查
        def patched_require_version(requirement, hint=None):
            print(f"Skipping version check for: {requirement}")
            # 跳过版本检查
            return
        
        # 替换原始函数
        transformers.utils.versions.require_version = patched_require_version
        transformers.utils.versions.require_version_core = patched_require_version
        
        print("Successfully patched transformers dependency check")
    except Exception as e:
        print(f"Error patching transformers dependency check: {e}")
    
    # 处理 huggingface_hub 导入错误
    try:
        # 先导入 huggingface_hub
        import huggingface_hub
        
        # 检查是否缺少 split_torch_state_dict_into_shards 函数
        if not hasattr(huggingface_hub, 'split_torch_state_dict_into_shards'):
            # 添加一个空的函数来避免导入错误
            def mock_split_torch_state_dict_into_shards(*args, **kwargs):
                return None
            
            # 将函数添加到 huggingface_hub 模块
            huggingface_hub.split_torch_state_dict_into_shards = mock_split_torch_state_dict_into_shards
            print("Successfully added mock split_torch_state_dict_into_shards function")
    except Exception as e:
        print(f"Error patching huggingface_hub: {e}")
