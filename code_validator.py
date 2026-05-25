"""
验证关联编号与一阶编码原始文本的匹配
如果不匹配，删除该编码
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

def validate_and_filter_codes(
    structured_codes: Dict[str, Any],
    number_mapping: Dict[int, str]
) -> Dict[str, Any]:
    """
    验证关联编号对应的文本与一阶编码原始文本是否匹配
    如果不匹配，删除该编码
    
    Args:
        structured_codes: 编码结构
        number_mapping: TextNumbering 编号映射 {编号: 原始文本}
    
    Returns:
        过滤后的编码结构
    """
    if not number_mapping:
        logger.warning("number_mapping 为空，跳过验证")
        return structured_codes
    
    total_count = 0
    removed_count = 0
    
    # 遍历三阶编码
    for third_cat, second_cats in list(structured_codes.items()):
        # 遍历二阶编码
        for second_cat, first_contents in list(second_cats.items()):
            # 遍历一阶编码
            filtered_first_contents = []
            
            for first_content in first_contents:
                total_count += 1
                
                # 获取一阶编码的原始文本
                sentence_details = first_content.get('sentence_details', [])
                if not sentence_details:
                    # 没有句子详情，保留
                    filtered_first_contents.append(first_content)
                    continue
                
                # 获取第一个句子的内容和编号
                first_detail = sentence_details[0]
                original_text = first_detail.get('content', '')
                sentence_id = first_detail.get('sentence_id', '') or first_detail.get('code_id', '')
                
                if not original_text or not sentence_id:
                    # 缺少必要信息，保留
                    filtered_first_contents.append(first_content)
                    continue
                
                # 验证匹配
                if _validate_match(original_text, sentence_id, number_mapping):
                    # 匹配成功，保留
                    filtered_first_contents.append(first_content)
                else:
                    # 匹配失败，删除
                    code_id = first_content.get('code_id', 'Unknown')
                    logger.warning(f'删除不匹配的编码: {code_id}, sentence_id={sentence_id}')
                    removed_count += 1
            
            # 更新二阶编码的一阶编码列表
            second_cats[second_cat] = filtered_first_contents
            
            # 如果二阶编码下没有一阶编码了，删除二阶编码
            if not filtered_first_contents:
                del second_cats[second_cat]
        
        # 如果三阶编码下没有二阶编码了，删除三阶编码
        if not second_cats:
            del structured_codes[third_cat]
    
    logger.info(f'验证完成: 总数={total_count}, 删除={removed_count}, 保留={total_count - removed_count}')
    logger.info(f'删除率: {removed_count/total_count*100:.1f}%')
    
    return structured_codes

def _validate_match(original_text: str, sentence_id: str, number_mapping: Dict[int, str]) -> bool:
    """
    验证原始文本与编号映射是否匹配
    
    Args:
        original_text: 一阶编码的原始文本
        sentence_id: 句子编号
        number_mapping: 编号映射
    
    Returns:
        是否匹配
    """
    # 转换 sentence_id 为整数
    try:
        text_number = int(sentence_id)
    except (ValueError, TypeError):
        # 无法转换为整数，跳过验证
        return True
    
    # 检查编号是否存在于映射中
    if text_number not in number_mapping:
        logger.debug(f'编号 {text_number} 不在 number_mapping 中')
        return False
    
    # 获取映射中的文本
    mapped_text = number_mapping[text_number]
    
    # 标准化文本（去除空格、标点）
    original_clean = _normalize_text(original_text)
    mapped_clean = _normalize_text(mapped_text)
    
    # 1. 完全匹配
    if original_clean == mapped_clean:
        return True
    
    # 2. 包含关系（原始文本是映射文本的子串，或反之）
    if original_clean in mapped_clean or mapped_clean in original_clean:
        return True
    
    # 3. 前缀匹配（至少50个字符）
    min_len = min(len(original_clean), len(mapped_clean))
    if min_len >= 50:
        prefix_len = min(50, min_len)
        if original_clean[:prefix_len] == mapped_clean[:prefix_len]:
            return True
    
    # 4. 相似度匹配（至少80%相同）
    similarity = _calculate_similarity(original_clean, mapped_clean)
    if similarity >= 0.8:
        return True
    
    # 不匹配
    logger.debug(f'不匹配: original={original_text[:50]}..., mapped={mapped_text[:50]}..., similarity={similarity:.2f}')
    return False

def _normalize_text(text: str) -> str:
    """标准化文本：去除空格、换行、标点"""
    import re
    # 去除所有空白字符
    text = re.sub(r'\s+', '', text)
    # 去除标点符号
    text = re.sub(r'[。！？!?.,;；、]', '', text)
    return text

def _calculate_similarity(text1: str, text2: str) -> float:
    """计算两个文本的相似度（简单的字符匹配率）"""
    if not text1 or not text2:
        return 0.0
    
    # 使用较短的文本作为基准
    shorter = text1 if len(text1) <= len(text2) else text2
    longer = text2 if len(text1) <= len(text2) else text1
    
    # 计算匹配的字符数
    matches = sum(1 for c in shorter if c in longer)
    
    # 相似度 = 匹配字符数 / 较短文本长度
    return matches / len(shorter)
