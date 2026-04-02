#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全的训练示例
展示如何在训练时使用内存监控，避免系统崩溃
"""

import logging
import sys
from monitor_training import start_monitoring, stop_monitoring, get_memory_status

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def safe_training_wrapper(training_function, *args, **kwargs):
    """
    安全的训练包装器
    在训练前后自动启动和停止内存监控
    
    Args:
        training_function: 训练函数
        *args, **kwargs: 传递给训练函数的参数
    
    Returns:
        训练函数的结果
    """
    # 检查初始内存状态
    initial_memory = get_memory_status()
    if initial_memory:
        logger.info(f"Initial memory status: {initial_memory['percent']}% used, "
                   f"{initial_memory['available_gb']}GB available")
        
        # 如果初始内存使用过高，警告用户
        if initial_memory['percent'] > 80:
            logger.warning("⚠️ Initial memory usage is high! Consider closing other applications.")
        
        if initial_memory['available_gb'] < 4:
            logger.warning("⚠️ Less than 4GB memory available! Training may cause system crash.")
    
    # 启动内存监控
    logger.info("Starting memory monitoring...")
    if not start_monitoring(memory_threshold=85, check_interval=5):
        logger.error("Failed to start memory monitoring!")
    
    try:
        # 执行训练
        logger.info("Starting training...")
        result = training_function(*args, **kwargs)
        logger.info("Training completed successfully!")
        return result
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise
        
    finally:
        # 停止内存监控
        logger.info("Stopping memory monitoring...")
        stop_monitoring()

def example_training_function(epochs=3, batch_size=4):
    """
    示例训练函数
    展示如何在训练过程中检查内存状态
    """
    from semantic_matcher import SemanticMatcher
    from coding_library_manager import CodingLibraryManager
    
    logger.info(f"Training with epochs={epochs}, batch_size={batch_size}")
    
    # 初始化组件
    matcher = SemanticMatcher()
    library_manager = CodingLibraryManager(semantic_matcher=matcher)
    
    # 获取二阶编码
    second_level_codes = library_manager.get_all_second_level_codes()
    logger.info(f"Loaded {len(second_level_codes)} second-level codes")
    
    # 模拟训练过程
    for epoch in range(epochs):
        logger.info(f"Epoch {epoch + 1}/{epochs}")
        
        # 每轮训练前检查内存
        memory_status = get_memory_status()
        if memory_status:
            if memory_status['percent'] > 90:
                logger.error(f"🚨 Memory usage too high ({memory_status['percent']}%)! Stopping training.")
                break
            elif memory_status['available_gb'] < 1:
                logger.error(f"🚨 Less than 1GB memory available! Stopping training.")
                break
        
        # 这里放置实际的训练代码
        # ...
        
        logger.info(f"Epoch {epoch + 1} completed")
    
    return {"status": "success", "epochs_completed": epochs}

def main():
    """主函数"""
    print("Safe Training Example")
    print("=" * 50)
    
    # 显示使用说明
    print("\nThis example shows how to use memory monitoring during training.")
    print("\nKey points:")
    print("1. Always check initial memory status before training")
    print("2. Use safe_training_wrapper to automatically monitor memory")
    print("3. Check memory status during training loops")
    print("4. Stop training if memory usage exceeds safe thresholds")
    
    print("\n" + "=" * 50)
    
    # 询问用户是否要运行示例训练
    response = input("\nDo you want to run the example training? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        try:
            # 使用安全的训练包装器
            result = safe_training_wrapper(
                example_training_function,
                epochs=2,
                batch_size=4
            )
            print(f"\nTraining result: {result}")
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            sys.exit(1)
    else:
        print("\nTo use in your code:")
        print("  from monitor_training import start_monitoring, stop_monitoring")
        print("  from safe_training_example import safe_training_wrapper")
        print("  ")
        print("  # Option 1: Use the wrapper")
        print("  result = safe_training_wrapper(your_training_function, arg1, arg2)")
        print("  ")
        print("  # Option 2: Manual monitoring")
        print("  start_monitoring(memory_threshold=85)")
        print("  try:")
        print("      your_training_function()")
        print("  finally:")
        print("      stop_monitoring()")

if __name__ == "__main__":
    main()
