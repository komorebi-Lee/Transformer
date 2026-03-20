"""
有待优化再使用，尤其是包含地址的优化
标准答案JSON转换为训练数据格式

功能：
1. 从标准答案JSON文件中提取目标变量
2. 转换为模型训练所需的格式
3. 支持多句联合训练方式

输入格式（标准答案JSON）：
{
  "structured_codes": {
    "三级分类": {
      "二级分类": [
        {
          "name": "抽象重点",
          "parent": "B01 二级分类",
          "sentence_details": [
            {"text": "关联句子1"},
            {"text": "关联句子2"}
          ]
        }
      ]
    }
  }
}

输出格式（训练数据）：
{
  "input_sentences": ["句子1", "句子2"],
  "target_abstract": "抽象重点",
  "target_second_category": "二级分类",
  "target_third_category": "三级分类"
}
"""


import json
import os
from typing import Dict, List, Any
from datetime import datetime


def extract_training_data(standard_answer_path: str) -> List[Dict[str, Any]]:
    """
    从标准答案JSON中提取训练数据
    
    数据提取逻辑：
    - 如果 sentence_details 中有 text 字段（关联句子），则使用 text
    - 如果没有 text 字段（无关联句子），则使用 original_content
    
    Args:
        standard_answer_path: 标准答案JSON文件路径
        
    Returns:
        训练数据列表
    """
    with open(standard_answer_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    training_data = []
    structured_codes = data.get('structured_codes', {})
    
    for third_category, second_level_data in structured_codes.items():
        for second_category, first_level_codes in second_level_data.items():
            for code_item in first_level_codes:
                if not isinstance(code_item, dict):
                    continue
                
                name = code_item.get('name', '').strip()
                if not name:
                    continue
                
                sentence_details = code_item.get('sentence_details', [])
                
                input_sentences = []
                for detail in sentence_details:
                    text = detail.get('text', '').strip()
                    if text:
                        input_sentences.append(text)
                    else:
                        original_content = detail.get('original_content', '').strip()
                        if original_content:
                            input_sentences.append(original_content)
                
                if not input_sentences:
                    continue
                
                parent = code_item.get('parent', '')
                if parent:
                    second_category_clean = parent.split(' ', 1)[-1] if ' ' in parent else parent
                else:
                    second_category_clean = second_category
                
                training_sample = {
                    "input_sentences": input_sentences,
                    "target_abstract": name,
                    "target_second_category": second_category_clean,
                    "target_third_category": third_category
                }
                
                training_data.append(training_sample)
    
    return training_data


def save_training_data(training_data: List[Dict[str, Any]], output_path: str):
    """
    保存训练数据到JSON文件
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)
    print(f"训练数据已保存到: {output_path}")
    print(f"总样本数: {len(training_data)}")


def get_statistics(training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    获取训练数据统计信息
    """
    third_categories = set()
    second_categories = set()
    abstracts = set()
    sentence_counts = []
    
    for sample in training_data:
        third_categories.add(sample['target_third_category'])
        second_categories.add(sample['target_second_category'])
        abstracts.add(sample['target_abstract'])
        sentence_counts.append(len(sample['input_sentences']))
    
    return {
        "total_samples": len(training_data),
        "unique_third_categories": len(third_categories),
        "unique_second_categories": len(second_categories),
        "unique_abstracts": len(abstracts),
        "avg_sentences_per_sample": sum(sentence_counts) / len(sentence_counts) if sentence_counts else 0,
        "min_sentences": min(sentence_counts) if sentence_counts else 0,
        "max_sentences": max(sentence_counts) if sentence_counts else 0,
        "third_categories": list(third_categories),
        "second_categories": list(second_categories)
    }


def main():
    standard_answer_path = r"d:\zthree2\standard_answers\v24_20260319_203847.json"
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"d:\\zthree2\\training_data\\training_data_{timestamp}.json"
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print("=" * 60)
    print("标准答案转换为训练数据")
    print("=" * 60)
    
    print("\n正在提取训练数据...")
    training_data = extract_training_data(standard_answer_path)
    
    print("\n正在保存训练数据...")
    save_training_data(training_data, output_path)
    
    print("\n正在生成统计信息...")
    stats = get_statistics(training_data)
    
    print("\n" + "=" * 60)
    print("训练数据统计")
    print("=" * 60)
    print(f"总样本数: {stats['total_samples']}")
    print(f"三级分类数: {stats['unique_third_categories']}")
    print(f"二级分类数: {stats['unique_second_categories']}")
    print(f"唯一抽象重点数: {stats['unique_abstracts']}")
    print(f"平均每样本句子数: {stats['avg_sentences_per_sample']:.2f}")
    print(f"最少句子数: {stats['min_sentences']}")
    print(f"最多句子数: {stats['max_sentences']}")
    
    print("\n三级分类列表:")
    for cat in stats['third_categories']:
        print(f"  - {cat}")
    
    print("\n二级分类列表:")
    for cat in stats['second_categories']:
        print(f"  - {cat}")
    
    print("\n" + "=" * 60)
    print("示例数据（前3条）")
    print("=" * 60)
    for i, sample in enumerate(training_data[:3]):
        print(f"\n样本 {i+1}:")
        print(f"  输入句子数: {len(sample['input_sentences'])}")
        print(f"  输入句子: {sample['input_sentences'][:2]}..." if len(sample['input_sentences']) > 2 else f"  输入句子: {sample['input_sentences']}")
        print(f"  目标抽象: {sample['target_abstract']}")
        print(f"  二级分类: {sample['target_second_category']}")
        print(f"  三级分类: {sample['target_third_category']}")


if __name__ == "__main__":
    main()
