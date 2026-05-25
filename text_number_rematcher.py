"""
文本编号重新匹配器：使用一阶编码中的原始文本直接匹配
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def rematch_text_numbers_for_codes(
    structured_codes: Dict[str, Any],
    number_mapping: Dict[int, str]
) -> Dict[str, Any]:
    """
    使用一阶编码中的原始文本重新匹配 text_number
    
    Args:
        structured_codes: 编码结构
        number_mapping: TextNumbering 编号映射
    
    Returns:
        更新后的编码结构
    """
    if not number_mapping:
        logger.warning("number_mapping 为空，跳过重新匹配")
        return structured_codes
    
    matched_count = 0
    rematched_count = 0
    total_count = 0
    
    for third_cat, second_cats in structured_codes.items():
        for second_cat, first_contents in second_cats.items():
            for first_content in first_contents:
                sentence_details = first_content.get('sentence_details', [])
                
                for detail in sentence_details:
                    total_count += 1
                    
                    # 使用句子的原始文本
                    original_text = detail.get('content', '')
                    
                    if not original_text:
                        continue
                    
                    # 如果已经有 text_number，检查是否正确
                    existing_number = detail.get('text_number')
                    if existing_number:
                        matched_count += 1
                        # 验证是否正确
                        if existing_number in number_mapping:
                            mapped_text = number_mapping[existing_number]
                            if original_text not in mapped_text and mapped_text not in original_text:
                                # 编号不正确，重新匹配
                                text_number = _find_exact_match(original_text, number_mapping)
                                if text_number and text_number != existing_number:
                                    detail['text_number'] = text_number
                                    detail['numbered_sentence'] = f"{original_text} [{text_number}]"
                                    rematched_count += 1
                        continue
                    
                    # 没有 text_number，尝试匹配
                    text_number = _find_exact_match(original_text, number_mapping)
                    
                    if text_number:
                        detail['text_number'] = text_number
                        detail['numbered_sentence'] = f"{original_text} [{text_number}]"
                        matched_count += 1
    
    logger.info(f'重新匹配完成: {matched_count}/{total_count} ({matched_count/total_count*100:.1f}%)')
    if rematched_count > 0:
        logger.info(f'修正错误匹配: {rematched_count} 个')
    
    return structured_codes

def _find_exact_match(text: str, number_mapping: Dict[int, str]) -> Optional[int]:
    """
    精确匹配文本编号
    
    Args:
        text: 要匹配的文本
        number_mapping: 编号映射
    
    Returns:
        匹配的编号或None
    """
    if not text or not number_mapping:
        return None
    
    # 1. 完全精确匹配
    for num, mapped_text in number_mapping.items():
        if text == mapped_text:
            return num
    
    # 2. 去除末尾标点后匹配
    text_no_punct = text.rstrip('。！？!?.,;；')
    for num, mapped_text in number_mapping.items():
        mapped_no_punct = mapped_text.rstrip('。！？!?.,;；')
        if text_no_punct == mapped_no_punct:
            return num
    
    # 3. 去除所有空格和标点后匹配
    text_clean = text.replace(' ', '').replace('\n', '').replace('\t', '').rstrip('。！？!?.,;；')
    for num, mapped_text in number_mapping.items():
        mapped_clean = mapped_text.replace(' ', '').replace('\n', '').replace('\t', '').rstrip('。！？!?.,;；')
        if text_clean == mapped_clean:
            return num
    
    return None
