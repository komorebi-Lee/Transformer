"""
验证关联编号与一阶编码原始文本的匹配（基于编码树）
如果不匹配，删除该编码
"""

from typing import Dict, Any
import logging
import re

logger = logging.getLogger(__name__)

def validate_and_filter_codes_by_tree(
    coding_tree,
    structured_codes: Dict[str, Any],
    number_mapping: Dict[int, str]
) -> Dict[str, Any]:
    """
    基于编码树的关联编号验证一阶编码
    
    Args:
        coding_tree: 编码树控件
        structured_codes: 编码结构
        number_mapping: TextNumbering 编号映射 {编号: 原始文本}
    
    Returns:
        过滤后的编码结构
    """
    if not number_mapping:
        logger.warning("number_mapping 为空，跳过验证")
        return structured_codes
    
    # 收集需要删除的编码ID
    codes_to_remove = set()
    
    # 遍历编码树，获取关联编号
    root = coding_tree.invisibleRootItem()
    _collect_invalid_codes(root, number_mapping, codes_to_remove)
    
    if not codes_to_remove:
        logger.info("所有编码都匹配，无需删除")
        return structured_codes
    
    logger.info(f"需要删除 {len(codes_to_remove)} 个不匹配的编码")
    
    # 从 structured_codes 中删除这些编码
    total_count = 0
    removed_count = 0
    
    for third_cat, second_cats in list(structured_codes.items()):
        for second_cat, first_contents in list(second_cats.items()):
            filtered_first_contents = []
            
            for first_content in first_contents:
                total_count += 1
                code_id = first_content.get('code_id', '')
                
                if code_id in codes_to_remove:
                    logger.warning(f'删除不匹配的编码: {code_id}')
                    removed_count += 1
                else:
                    filtered_first_contents.append(first_content)
            
            second_cats[second_cat] = filtered_first_contents
            
            if not filtered_first_contents:
                del second_cats[second_cat]
        
        if not second_cats:
            del structured_codes[third_cat]
    
    logger.info(f'验证完成: 总数={total_count}, 删除={removed_count}, 保留={total_count - removed_count}')
    logger.info(f'删除率: {removed_count/total_count*100:.1f}%')
    
    return structured_codes

def _collect_invalid_codes(item, number_mapping, codes_to_remove):
    """递归遍历编码树，收集不匹配的编码ID"""
    from PyQt5.QtCore import Qt
    
    # 检查当前项
    item_data = item.data(0, Qt.UserRole)
    if item_data and item_data.get('level') == 1:  # 一阶编码
        # 获取编码ID
        code_id = item_data.get('code_id', '')
        
        # 获取关联编号（第5列）
        associated_number = item.text(5)
        
        # 获取原始文本，优先使用与关联编号一致的稳定主键详情
        sentence_details = item_data.get('sentence_details', [])
        if sentence_details:
            matched_detail = None
            normalized_numbers = {n.strip().strip('[]') for n in associated_number.split(',') if n.strip()}
            for detail in sentence_details:
                if not isinstance(detail, dict):
                    continue
                stable_id = detail.get('text_number') or detail.get('sentence_id')
                if stable_id is not None and str(stable_id).strip().strip('[]') in normalized_numbers:
                    matched_detail = detail
                    break

            if matched_detail is None:
                matched_detail = sentence_details[0]

            original_text = matched_detail.get('original_content', '') or matched_detail.get('content', '')
            
            # 验证匹配
            if not _validate_match_by_number(original_text, associated_number, number_mapping):
                codes_to_remove.add(code_id)
                logger.debug(f'标记删除: {code_id}, 关联编号={associated_number}')
    
    # 递归处理子项
    for i in range(item.childCount()):
        child = item.child(i)
        _collect_invalid_codes(child, number_mapping, codes_to_remove)

def _validate_match_by_number(original_text: str, associated_number: str, number_mapping: Dict[int, str]) -> bool:
    """
    验证原始文本与关联编号对应的文本是否匹配
    
    Args:
        original_text: 一阶编码的原始文本
        associated_number: 编码树第5列的关联编号（可能是逗号分隔的多个编号）
        number_mapping: 编号映射
    
    Returns:
        是否匹配
    """
    if not original_text or not associated_number:
        # 缺少必要信息，保留
        return True
    
    # 解析关联编号（可能是 "3174" 或 "3174, 3175"）
    numbers = [n.strip() for n in associated_number.split(',') if n.strip()]
    
    if not numbers:
        return True
    
    # 使用第一个编号进行验证
    first_number = numbers[0]
    
    # 转换为整数
    try:
        text_number = int(first_number)
    except (ValueError, TypeError):
        logger.debug(f'无法转换编号为整数: {first_number}')
        return True
    
    # 检查编号是否存在于映射中
    if text_number not in number_mapping:
        logger.debug(f'编号 {text_number} 不在 number_mapping 中，保留编码')
        return True  # 修改：编号不在映射中时保留，而不是删除
    
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
    logger.debug(f'不匹配: 编号={text_number}, original={original_text[:50]}..., mapped={mapped_text[:50]}..., similarity={similarity:.2f}')
    return False

def _normalize_text(text: str) -> str:
    """标准化文本：去除空格、换行、标点"""
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
