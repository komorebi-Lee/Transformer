#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练监控脚本
用于实时监控训练过程中的内存使用情况
"""

import time
import sys
import os
import threading
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('training_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available, memory monitoring will be limited")

class TrainingMonitor:
    def __init__(self, memory_threshold=90, check_interval=5):
        """
        初始化训练监控器
        
        Args:
            memory_threshold: 内存使用率阈值（百分比），超过此值将发出警告
            check_interval: 检查间隔（秒）
        """
        self.memory_threshold = memory_threshold
        self.check_interval = check_interval
        self.monitoring = False
        self.monitor_thread = None
        self.peak_memory = 0
        self.start_time = None
        
    def get_memory_info(self):
        """获取内存信息"""
        if not PSUTIL_AVAILABLE:
            return None
        
        memory = psutil.virtual_memory()
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info()
        
        return {
            'total_gb': round(memory.total / (1024**3), 2),
            'available_gb': round(memory.available / (1024**3), 2),
            'used_gb': round(memory.used / (1024**3), 2),
            'percent': memory.percent,
            'process_rss_mb': round(process_memory.rss / (1024**2), 2),
            'process_vms_mb': round(process_memory.vms / (1024**2), 2)
        }
    
    def monitor(self):
        """监控循环"""
        while self.monitoring:
            memory_info = self.get_memory_info()
            if memory_info:
                # 更新峰值内存
                if memory_info['percent'] > self.peak_memory:
                    self.peak_memory = memory_info['percent']
                
                # 记录内存使用情况
                logger.info(f"Memory: {memory_info['percent']}% used, "
                          f"{memory_info['available_gb']}GB available, "
                          f"Process RSS: {memory_info['process_rss_mb']}MB")
                
                # 检查内存阈值
                if memory_info['percent'] > self.memory_threshold:
                    logger.warning(f"⚠️ HIGH MEMORY USAGE: {memory_info['percent']}% "
                                 f"(threshold: {self.memory_threshold}%)")
                    
                    # 如果内存使用超过95%，建议停止训练
                    if memory_info['percent'] > 95:
                        logger.error("🚨 CRITICAL: Memory usage exceeds 95%! "
                                   "Consider stopping training to prevent system crash.")
                
                # 检查可用内存是否过低
                if memory_info['available_gb'] < 1:
                    logger.error("🚨 CRITICAL: Less than 1GB memory available! "
                               "System may crash soon.")
            
            time.sleep(self.check_interval)
    
    def start(self):
        """开始监控"""
        if not PSUTIL_AVAILABLE:
            logger.error("Cannot start monitoring: psutil not available")
            return False
        
        self.monitoring = True
        self.start_time = datetime.now()
        self.monitor_thread = threading.Thread(target=self.monitor, daemon=True)
        self.monitor_thread.start()
        logger.info(f"Training monitor started (threshold: {self.memory_threshold}%, "
                   f"interval: {self.check_interval}s)")
        return True
    
    def stop(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        
        if self.start_time:
            duration = datetime.now() - self.start_time
            logger.info(f"Training monitor stopped. Duration: {duration}, "
                       f"Peak memory usage: {self.peak_memory}%")
    
    def get_summary(self):
        """获取监控摘要"""
        if not self.start_time:
            return "Monitor not started"
        
        duration = datetime.now() - self.start_time
        memory_info = self.get_memory_info()
        
        summary = f"""
Training Monitor Summary:
========================
Duration: {duration}
Peak Memory Usage: {self.peak_memory}%
Current Memory Usage: {memory_info['percent'] if memory_info else 'N/A'}%
"""
        return summary

# 全局监控器实例
_global_monitor = None

def start_monitoring(memory_threshold=90, check_interval=5):
    """
    启动训练监控
    
    Args:
        memory_threshold: 内存使用率阈值（百分比）
        check_interval: 检查间隔（秒）
    """
    global _global_monitor
    _global_monitor = TrainingMonitor(memory_threshold, check_interval)
    return _global_monitor.start()

def stop_monitoring():
    """停止训练监控"""
    global _global_monitor
    if _global_monitor:
        _global_monitor.stop()
        summary = _global_monitor.get_summary()
        print(summary)

def get_memory_status():
    """获取当前内存状态"""
    if not PSUTIL_AVAILABLE:
        return None
    
    monitor = TrainingMonitor()
    return monitor.get_memory_info()

if __name__ == "__main__":
    # 测试监控功能
    print("Training Monitor Test")
    print("====================")
    
    # 显示当前内存状态
    status = get_memory_status()
    if status:
        print(f"Current Memory Status:")
        print(f"  Total: {status['total_gb']} GB")
        print(f"  Used: {status['used_gb']} GB ({status['percent']}%)")
        print(f"  Available: {status['available_gb']} GB")
        print(f"  Process RSS: {status['process_rss_mb']} MB")
    else:
        print("Memory status not available")
    
    print("\nTo use in your training script:")
    print("  from monitor_training import start_monitoring, stop_monitoring")
    print("  start_monitoring(memory_threshold=85)")
    print("  # ... your training code ...")
    print("  stop_monitoring()")
