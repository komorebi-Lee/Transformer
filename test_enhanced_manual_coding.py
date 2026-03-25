#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试人工编码增强功能
"""

import json
import os
from enhanced_manual_coding import EnhancedManualCoding


def test_enhanced_manual_coding():
    """测试人工编码增强功能"""
    print("开始测试人工编码增强功能...")
    
    # 初始化人工编码增强功能
    enhanced_coding = EnhancedManualCoding()
    print("人工编码增强功能初始化成功")
    
    # 创建测试用的标准答案数据
    test_standard_answer = {
        "structured_codes": {
            "同质竞加剧": {
                "家电模具工艺趋同争同质模具产能过剩": [
                    "模具工艺趋同，导致同质化竞争加剧",
                    "产能过剩，价格战频发"
                ],
                "同行发起低价竞争争爆发恶性价格战": [
                    "竞争对手纷纷降价，引发价格战",
                    "利润空间被压缩"
                ]
            },
            "成长空被挤压": {
                "间 市场份额被侵占目标客户被侵夺": [
                    "市场份额不断下降",
                    "核心客户被竞争对手抢走"
                ],
                "销售额增长乏力速利润率逐渐下滑": [
                    "销售额增长缓慢",
                    "利润率持续下降"
                ]
            }
        }
    }
    
    print("测试数据创建成功")
    
    # 处理标准答案
    print("开始处理标准答案...")
    result = enhanced_coding.process_standard_answer(test_standard_answer)
    
    print(f"处理结果: {result}")
    
    if result["success"]:
        print("✅ 人工编码增强功能测试成功！")
        print(f"新增三阶编码: {result['result']['added_third_level_codes']}")
        print(f"更新三阶编码: {result['result']['updated_third_level_codes']}")
        print(f"新增二阶编码: {result['result']['added_second_level_codes']}")
        print(f"更新二阶编码: {result['result']['updated_second_level_codes']}")
    else:
        print(f"❌ 人工编码增强功能测试失败: {result['message']}")
    
    # 测试与模型训练流程集成
    print("\n测试与模型训练流程集成...")
    integration_result = enhanced_coding.integrate_with_model_training(test_standard_answer)
    
    print(f"集成结果: {integration_result}")
    
    if integration_result["success"]:
        print("✅ 与模型训练流程集成测试成功！")
    else:
        print(f"❌ 与模型训练流程集成测试失败: {integration_result['message']}")


if __name__ == "__main__":
    test_enhanced_manual_coding()
