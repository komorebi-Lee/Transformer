#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练问题诊断脚本
用于收集系统信息和错误日志，帮助诊断训练时黑屏的原因
"""

import os
import sys
import platform
import subprocess
import json
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_system_info():
    """获取系统基本信息"""
    info = {
        "timestamp": datetime.now().isoformat(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": sys.version,
        "python_executable": sys.executable
    }
    return info

def get_memory_info():
    """获取内存信息"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        return {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "percent": memory.percent
        }
    except ImportError:
        return {"error": "psutil not available"}

def get_gpu_info():
    """获取GPU信息"""
    gpu_info = []
    
    # 尝试获取NVIDIA GPU信息
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu', 
                               '--format=csv,noheader'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for i, line in enumerate(lines):
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 5:
                    gpu_info.append({
                        "index": i,
                        "name": parts[0],
                        "memory_total": parts[1],
                        "memory_used": parts[2],
                        "memory_free": parts[3],
                        "temperature": parts[4]
                    })
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        gpu_info.append({"nvidia_smi_error": str(e)})
    
    # 尝试通过torch获取GPU信息
    try:
        import torch
        if torch.cuda.is_available():
            gpu_info.append({
                "torch_cuda_available": True,
                "torch_cuda_device_count": torch.cuda.device_count(),
                "torch_cuda_current_device": torch.cuda.current_device(),
                "torch_cuda_device_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else None
            })
        else:
            gpu_info.append({"torch_cuda_available": False})
    except ImportError:
        gpu_info.append({"torch_error": "PyTorch not available"})
    
    return gpu_info

def get_windows_event_logs():
    """获取Windows事件日志中的错误信息"""
    errors = []
    try:
        # 获取最近24小时内的系统错误日志
        result = subprocess.run(
            ['powershell', '-Command', 
             'Get-EventLog -LogName System -EntryType Error -After (Get-Date).AddHours(-24) | Select-Object -First 10 | Format-Table TimeGenerated, Source, Message -Wrap'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            errors.append({"system_errors": result.stdout})
        
        # 获取应用程序错误日志
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-EventLog -LogName Application -EntryType Error -After (Get-Date).AddHours(-24) | Select-Object -First 10 | Format-Table TimeGenerated, Source, Message -Wrap'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            errors.append({"application_errors": result.stdout})
            
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        errors.append({"error": str(e)})
    
    return errors

def get_disk_space():
    """获取磁盘空间信息"""
    try:
        import psutil
        disk_info = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent": round(usage.percent, 2)
                })
            except PermissionError:
                continue
        return disk_info
    except ImportError:
        return [{"error": "psutil not available"}]

def check_training_logs():
    """检查训练相关的日志文件"""
    log_files = []
    log_paths = [
        "training.log",
        "app.log",
        "error.log",
        "logs/training.log",
        "logs/app.log"
    ]
    
    for log_path in log_paths:
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # 读取最后100行
                    lines = f.readlines()
                    last_lines = lines[-100:] if len(lines) > 100 else lines
                    log_files.append({
                        "file": log_path,
                        "last_lines": ''.join(last_lines)
                    })
            except Exception as e:
                log_files.append({"file": log_path, "error": str(e)})
    
    return log_files

def check_python_packages():
    """检查关键Python包版本"""
    packages = {}
    package_names = [
        'torch', 'tensorflow', 'numpy', 'pandas', 
        'sentence-transformers', 'transformers', 'psutil'
    ]
    
    for package in package_names:
        try:
            if package == 'torch':
                import torch
                packages[package] = torch.__version__
            elif package == 'tensorflow':
                import tensorflow as tf
                packages[package] = tf.__version__
            elif package == 'numpy':
                import numpy as np
                packages[package] = np.__version__
            elif package == 'pandas':
                import pandas as pd
                packages[package] = pd.__version__
            elif package == 'sentence-transformers':
                import sentence_transformers
                packages[package] = sentence_transformers.__version__
            elif package == 'transformers':
                import transformers
                packages[package] = transformers.__version__
            elif package == 'psutil':
                import psutil
                packages[package] = psutil.__version__
        except ImportError:
            packages[package] = "not installed"
        except Exception as e:
            packages[package] = f"error: {str(e)}"
    
    return packages

def generate_report():
    """生成诊断报告"""
    report = {
        "system_info": get_system_info(),
        "memory_info": get_memory_info(),
        "gpu_info": get_gpu_info(),
        "disk_space": get_disk_space(),
        "python_packages": check_python_packages(),
        "training_logs": check_training_logs(),
        "windows_event_logs": get_windows_event_logs() if platform.system() == "Windows" else "Not Windows system"
    }
    
    return report

def save_report(report, filename=None):
    """保存诊断报告到文件"""
    if filename is None:
        filename = f"diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info(f"诊断报告已保存到: {filename}")
    return filename

def print_summary(report):
    """打印诊断摘要"""
    print("\n" + "="*60)
    print("训练问题诊断摘要")
    print("="*60)
    
    # 系统信息
    print(f"\n系统: {report['system_info']['platform']}")
    print(f"Python: {report['system_info']['python_version'][:50]}...")
    
    # 内存信息
    if 'error' not in report['memory_info']:
        mem = report['memory_info']
        print(f"\n内存:")
        print(f"  总内存: {mem['total_gb']} GB")
        print(f"  已使用: {mem['used_gb']} GB ({mem['percent']}%)")
        print(f"  可用: {mem['available_gb']} GB")
        
        # 内存警告
        if mem['percent'] > 90:
            print("  ⚠️ 警告: 内存使用率过高！")
        elif mem['available_gb'] < 2:
            print("  ⚠️ 警告: 可用内存不足2GB！")
    
    # GPU信息
    print(f"\nGPU信息:")
    for gpu in report['gpu_info']:
        if 'name' in gpu:
            print(f"  {gpu['name']}")
            print(f"    显存: {gpu['memory_used']} / {gpu['memory_total']}")
            print(f"    温度: {gpu['temperature']}")
        elif 'torch_cuda_available' in gpu:
            if gpu['torch_cuda_available']:
                print(f"  PyTorch CUDA可用: {gpu.get('torch_cuda_device_name', 'Unknown')}")
            else:
                print("  PyTorch CUDA不可用")
    
    # 磁盘空间
    print(f"\n磁盘空间:")
    for disk in report['disk_space']:
        if 'error' not in disk:
            print(f"  {disk['mountpoint']}: {disk['free_gb']} GB 可用 / {disk['total_gb']} GB 总计 ({disk['percent']}% 已用)")
            if disk['free_gb'] < 10:
                print(f"    ⚠️ 警告: {disk['mountpoint']} 可用空间不足10GB！")
    
    # Python包
    print(f"\n关键Python包版本:")
    for package, version in report['python_packages'].items():
        status = "✓" if version not in ["not installed", "error"] else "✗"
        print(f"  {status} {package}: {version}")
    
    # 日志文件
    if report['training_logs']:
        print(f"\n找到的日志文件:")
        for log in report['training_logs']:
            print(f"  - {log['file']}")
    
    print("\n" + "="*60)
    print("常见黑屏原因分析:")
    print("="*60)
    
    reasons = []
    
    # 检查内存
    if 'error' not in report['memory_info']:
        if report['memory_info']['percent'] > 90:
            reasons.append("1. 内存使用率过高 (>90%)，可能导致系统崩溃")
        if report['memory_info']['available_gb'] < 4:
            reasons.append("2. 可用内存不足 (<4GB)，训练大型模型时容易耗尽内存")
    
    # 检查GPU
    for gpu in report['gpu_info']:
        if 'name' in gpu:
            try:
                temp = int(gpu['temperature'].replace('C', '').strip())
                if temp > 80:
                    reasons.append(f"3. GPU温度过高 ({temp}°C)，可能导致系统自动关机保护")
            except:
                pass
    
    # 检查磁盘
    for disk in report['disk_space']:
        if 'error' not in disk and disk['free_gb'] < 5:
            reasons.append(f"4. 磁盘空间不足 ({disk['mountpoint']} 仅剩 {disk['free_gb']} GB)")
    
    if not reasons:
        print("根据当前系统状态，未发现明显的资源问题。")
        print("建议查看Windows事件日志以获取更多信息。")
    else:
        for reason in reasons:
            print(reason)
    
    print("\n建议解决方案:")
    print("1. 关闭其他占用内存的程序")
    print("2. 减小训练批次大小 (batch_size)")
    print("3. 使用更小的模型或减少训练数据量")
    print("4. 确保系统散热良好")
    print("5. 清理磁盘空间")
    print("6. 考虑使用云服务进行训练")
    print("="*60 + "\n")

def main():
    """主函数"""
    logger.info("开始收集系统诊断信息...")
    
    try:
        report = generate_report()
        filename = save_report(report)
        print_summary(report)
        
        print(f"\n详细诊断报告已保存到: {filename}")
        print("请将这个文件发送给技术支持以获得进一步帮助。")
        
    except Exception as e:
        logger.error(f"生成诊断报告时出错: {e}")
        print(f"错误: {e}")

if __name__ == "__main__":
    main()
