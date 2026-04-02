#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动修复PyTorch CUDA问题
"""

import subprocess
import sys
import os

print("=" * 60)
print("PyTorch CUDA 修复工具")
print("=" * 60)

def run_command(command, description):
    """运行命令并显示结果"""
    print(f"\n{description}...")
    print(f"命令: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            print("[OK] 成功")
            if result.stdout:
                print(result.stdout[:500])  # 只显示前500字符
            return True
        else:
            print("[ERROR] 失败")
            print("错误:", result.stderr[:500])
            return False
    except subprocess.TimeoutExpired:
        print("[ERROR] 超时")
        return False
    except Exception as e:
        print(f"[ERROR] 异常: {e}")
        return False

def check_cuda_driver():
    """检查NVIDIA驱动"""
    print("\n检查NVIDIA驱动...")
    try:
        result = subprocess.run(
            ['nvidia-smi'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("[OK] NVIDIA驱动已安装")
            # 显示GPU信息
            lines = result.stdout.split('\n')
            for line in lines[:10]:
                if 'NVIDIA' in line or 'MiB' in line:
                    print(" ", line)
            return True
        else:
            print("[ERROR] NVIDIA驱动未安装或有问题")
            return False
    except FileNotFoundError:
        print("[ERROR] nvidia-smi未找到，请安装NVIDIA驱动")
        print("  下载地址: https://www.nvidia.com/Download/index.aspx")
        return False
    except Exception as e:
        print(f"[ERROR] 检查驱动时出错: {e}")
        return False

def main():
    # 检查当前PyTorch状态
    print("\n步骤1: 检查当前PyTorch状态")
    try:
        import torch
        current_version = torch.__version__
        print(f"当前PyTorch版本: {current_version}")
        
        if '+cpu' in current_version:
            print("检测到CPU版本，需要更换为GPU版本")
        elif torch.cuda.is_available():
            print("[OK] CUDA已经可用，无需修复")
            print(f"  CUDA版本: {torch.version.cuda}")
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
            return
        else:
            print("PyTorch版本异常，建议重新安装")
    except ImportError:
        print("PyTorch未安装")
    
    # 检查NVIDIA驱动
    print("\n步骤2: 检查NVIDIA驱动")
    if not check_cuda_driver():
        print("\n请先安装NVIDIA驱动后再运行此脚本")
        print("1. 访问 https://www.nvidia.com/Download/index.aspx")
        print("2. 选择您的显卡型号（GeForce RTX 4060 Laptop）")
        print("3. 下载并安装驱动")
        return
    
    # 询问用户是否继续
    print("\n" + "=" * 60)
    response = input("是否继续安装GPU版PyTorch? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("取消安装")
        return
    
    # 卸载CPU版本
    print("\n步骤3: 卸载CPU版PyTorch")
    if not run_command(
        "pip uninstall torch torchvision torchaudio -y",
        "卸载当前PyTorch"
    ):
        print("卸载失败，但继续尝试安装...")
    
    # 安装GPU版本
    print("\n步骤4: 安装GPU版PyTorch")
    print("选择合适的CUDA版本:")
    print("1. CUDA 12.1 (推荐，支持RTX 4060)")
    print("2. CUDA 11.8 (兼容性更好)")
    print("3. 取消安装")
    
    choice = input("请选择 (1/2/3): ")
    
    if choice == '1':
        install_cmd = "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121"
    elif choice == '2':
        install_cmd = "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118"
    else:
        print("取消安装")
        return
    
    if run_command(install_cmd, "安装GPU版PyTorch"):
        print("\n步骤5: 验证安装")
        try:
            import torch
            if torch.cuda.is_available():
                print("[OK] CUDA现在可用!")
                print(f"  PyTorch版本: {torch.__version__}")
                print(f"  CUDA版本: {torch.version.cuda}")
                print(f"  GPU: {torch.cuda.get_device_name(0)}")
                print("\n修复完成! 请重新运行您的训练脚本。")
            else:
                print("[ERROR] CUDA仍然不可用")
                print("可能原因:")
                print("1. 安装过程中出现错误")
                print("2. 需要重启电脑")
                print("3. CUDA驱动版本不匹配")
        except ImportError:
            print("[ERROR] PyTorch安装失败")
    else:
        print("\n[ERROR] 安装失败")
        print("建议:")
        print("1. 检查网络连接")
        print("2. 尝试手动安装:")
        print(f"   {install_cmd}")
        print("3. 查看PyTorch官网: https://pytorch.org/get-started/locally/")

if __name__ == "__main__":
    main()
