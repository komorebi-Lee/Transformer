#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查PyTorch和CUDA状态
"""

import sys

print("=" * 60)
print("PyTorch CUDA 检查")
print("=" * 60)

try:
    import torch
    print("[OK] PyTorch已安装")
    print("  版本:", torch.__version__)
    
    # 检查CUDA是否可用
    if torch.cuda.is_available():
        print("[OK] CUDA可用")
        print("  CUDA版本:", torch.version.cuda)
        print("  GPU数量:", torch.cuda.device_count())
        print("  当前GPU:", torch.cuda.current_device())
        print("  GPU名称:", torch.cuda.get_device_name(0))
    else:
        print("[ERROR] CUDA不可用")
        print("  原因: PyTorch是CPU版本")
        
        # 检查版本号中的标识
        if '+cpu' in torch.__version__:
            print("  确认: 安装的是CPU版本 (+cpu标识)")
        
        print("\n解决方案:")
        print("1. 卸载当前PyTorch:")
        print("   pip uninstall torch torchvision torchaudio")
        print("\n2. 安装GPU版本:")
        print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
        
except ImportError:
    print("[ERROR] PyTorch未安装")
    print("  请安装PyTorch:")
    print("  pip install torch torchvision torchaudio")
    sys.exit(1)

print("=" * 60)
