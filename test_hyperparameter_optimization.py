#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超参数优化性能测试脚本
"""

import time
import logging
from hyperparameter_optimizer import HyperparameterOptimizer
from bert_dataset import create_dataset_from_standard_answers
from config import Config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockModelManager:
    """模拟模型管理器"""
    def is_trained_model_available(self):
        return False

def load_test_data():
    """
    加载测试数据
    """
    # 这里使用模拟数据，实际使用时应该加载真实的训练数据
    test_data = {
        'training_data': [
            {
                'text': '这是一个测试文本，用于超参数优化性能测试。',
                'full_category': '测试类别 > 子类别1'
            },
            {
                'text': '另一个测试文本，用于评估不同优化算法的性能。',
                'full_category': '测试类别 > 子类别2'
            },
            {
                'text': '第三个测试文本，比较不同算法的执行时间。',
                'full_category': '测试类别 > 子类别1'
            },
            {
                'text': '第四个测试文本，验证寻优质量。',
                'full_category': '测试类别 > 子类别2'
            },
            {
                'text': '第五个测试文本，确保系统稳定性。',
                'full_category': '测试类别 > 子类别1'
            }
        ]
    }
    return test_data

def test_optimization_algorithms():
    """
    测试不同优化算法的性能
    """
    logger.info("开始超参数优化性能测试")
    
    # 加载测试数据
    test_data = load_test_data()
    dataset = create_dataset_from_standard_answers(test_data)
    logger.info(f"加载测试数据完成，共 {len(dataset)} 个样本")
    
    # 初始化优化器
    model_manager = MockModelManager()
    optimizer = HyperparameterOptimizer(model_manager)
    
    # 测试算法列表
    algorithms = ['tpe', 'cmaes', 'random']
    results = []
    
    for algorithm in algorithms:
        logger.info(f"测试算法: {algorithm}")
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            # 运行贝叶斯优化
            result = optimizer.bayesian_optimization(
                dataset=dataset,
                n_trials=5,  # 减少试验次数以加快测试
                cv_folds=2,  # 减少交叉验证折数以加快测试
                algorithm=algorithm,
                n_jobs=-1  # 使用所有CPU核心
            )
            
            # 计算执行时间
            execution_time = time.time() - start_time
            
            # 记录结果
            results.append({
                'algorithm': algorithm,
                'execution_time': execution_time,
                'best_score': result['best_score'],
                'best_params': result['best_params']
            })
            
            logger.info(f"算法 {algorithm} 测试完成，执行时间: {execution_time:.2f}秒, 最优分数: {result['best_score']:.4f}")
            logger.info(f"最优参数: {result['best_params']}")
            
        except Exception as e:
            logger.error(f"测试算法 {algorithm} 失败: {e}")
            results.append({
                'algorithm': algorithm,
                'execution_time': -1,
                'best_score': -1,
                'best_params': {}
            })
    
    # 打印测试结果
    logger.info("\n性能测试结果汇总:")
    logger.info("-" * 80)
    logger.info(f"{'算法':<10} {'执行时间(秒)':<15} {'最优分数':<10} {'最优参数'}")
    logger.info("-" * 80)
    
    for result in results:
        algorithm = result['algorithm']
        execution_time = result['execution_time']
        best_score = result['best_score']
        best_params = result['best_params']
        
        if execution_time >= 0:
            logger.info(f"{algorithm:<10} {execution_time:<15.2f} {best_score:<10.4f} {best_params}")
        else:
            logger.info(f"{algorithm:<10} {'失败':<15} {'-':<10} {'-':<10}")
    
    logger.info("-" * 80)
    
    # 分析结果
    if results:
        # 找到最快的算法
        fastest_algorithm = min(results, key=lambda x: x['execution_time'] if x['execution_time'] >= 0 else float('inf'))
        # 找到分数最高的算法
        best_score_algorithm = max(results, key=lambda x: x['best_score'] if x['best_score'] >= 0 else -float('inf'))
        
        logger.info(f"\n最快算法: {fastest_algorithm['algorithm']}, 执行时间: {fastest_algorithm['execution_time']:.2f}秒")
        logger.info(f"分数最高算法: {best_score_algorithm['algorithm']}, 最优分数: {best_score_algorithm['best_score']:.4f}")
    
    logger.info("超参数优化性能测试完成")

if __name__ == "__main__":
    test_optimization_algorithms()
