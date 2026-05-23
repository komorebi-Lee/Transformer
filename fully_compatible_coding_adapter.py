"""
完全兼容的编码流水线适配器
保持原有的所有功能：编号、关联、高亮、定位等
"""

import os
import logging
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger(__name__)


class FullyCompatibleCodingAdapter:
    """
    完全兼容的适配器
    
    功能：
    1. 使用优化流水线生成一阶编码（准确率更高）
    2. 保持原有的数据结构和所有关联功能
    3. 支持编号、双击弹窗、高亮定位等所有功能
    """
    
    def __init__(self, optimized_pipeline):
        """
        Args:
            optimized_pipeline: OptimizedCodingPipeline 实例
        """
        self.pipeline = optimized_pipeline
        logger.info("FullyCompatibleCodingAdapter 已初始化")
    
    def generate_grounded_theory_codes_multi_files(
        self,
        processed_data: Dict[str, Any],
        model_manager,
        progress_callback: Optional[Callable] = None,
        use_trained_model: bool = False,
        coding_thresholds: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        生成扎根理论三级编码（完全兼容原有格式）
        
        核心改进：
        1. 使用优化流水线生成更准确的编码
        2. 完全保持原有的数据结构和格式
        3. 使用原有的编码键格式（FL_0001, FL_0002, ...）
        4. 保持二阶和三阶编码结构
        
        Args:
            processed_data: 处理后的数据
            model_manager: 模型管理器
            progress_callback: 进度回调
            use_trained_model: 是否使用训练模型
            coding_thresholds: 编码阈值
        
        Returns:
            {
                "一阶编码": {
                    "FL_0001": [abstracted, [source_detail], file_count, sentence_count, [source_detail]],
                    ...
                },
                "二阶编码": {"其他各类话题": ["FL_0001", ...]},
                "三阶编码": {"其他重要维度": ["其他各类话题"]},
                "file_sentence_mapping": {...}
            }
        """
        try:
            # 提取已经处理好的句子
            file_sentence_mapping = processed_data.get('file_sentence_mapping', {})
            
            if not file_sentence_mapping:
                logger.warning("file_sentence_mapping 为空")
                return self._empty_result()
            
            logger.info(f"开始处理 {len(file_sentence_mapping)} 个文件")
            
            # 直接使用已提取的句子生成编码
            first_level_codes = {}
            code_counter = 1
            
            for i, (filename, data) in enumerate(file_sentence_mapping.items()):
                logger.info(f"[{i+1}/{len(file_sentence_mapping)}] 处理文件: {filename}")
                
                # 更新进度
                if progress_callback:
                    progress = 30 + int((i / len(file_sentence_mapping)) * 40)
                    progress_callback(progress)
                
                try:
                    # 获取已提取的句子
                    sentences = data.get('sentences', [])
                    
                    if not sentences:
                        logger.warning(f"  文件 {filename} 没有提取到句子")
                        continue
                    
                    # 为每个句子生成编码
                    for sent in sentences:
                        text = sent.get('content', '') or sent.get('original_content', '')
                        
                        if not text:
                            continue
                        
                        # 使用优化流水线的编码生成逻辑
                        code = self._generate_code_for_single_text(text)
                        
                        if code:
                            # 使用原有的编码键格式
                            code_key = f"FL_{code_counter:04d}"
                            
                            # 完全兼容原有格式
                            first_level_codes[code_key] = [
                                code,        # 0: abstracted (一阶编码内容)
                                [sent],      # 1: source_sentences (原始句子列表)
                                1,           # 2: file_count (文件数)
                                1,           # 3: sentence_count (句子数)
                                [sent]       # 4: sentence_details (句子详情)
                            ]
                            
                            code_counter += 1
                    
                    logger.info(f"  完成: {code_counter - 1} 条编码")
                
                except Exception as e:
                    logger.error(f"  处理文件失败 {filename}: {e}")
                    continue
            
            total_codes = len(first_level_codes)
            logger.info(f"多文件处理完成: 总计 {total_codes} 条一阶编码")
            
            # 返回完全兼容的格式（包含二阶和三阶编码）
            return {
                "一阶编码": first_level_codes,
                "二阶编码": {
                    "其他各类话题": list(first_level_codes.keys())  # 所有编码归入默认分类
                },
                "三阶编码": {
                    "其他重要维度": ["其他各类话题"]  # 默认三阶分类
                },
                "file_sentence_mapping": file_sentence_mapping  # 保持原有的映射
            }
        
        except Exception as e:
            logger.error(f"生成编码失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._empty_result()
    
    def _generate_code_for_single_text(self, text: str) -> Optional[str]:
        """
        为单个文本生成编码（不重新提取）
        
        使用 InterviewCodingPipeline 的编码生成逻辑
        
        Args:
            text: 单个句子文本
        
        Returns:
            一阶编码或None
        """
        try:
            from interview_coding_pipeline import InterviewCodingPipeline
            
            # 创建流水线（使用缓存避免重复创建）
            if not hasattr(self, '_coding_pipeline'):
                self._coding_pipeline = InterviewCodingPipeline(self.pipeline.model_manager)
            
            # 构造单句文本（带说话人标签）
            text_with_label = f"受访者: {text}"
            
            # 生成编码
            results = self._coding_pipeline.process_single_text(
                text_with_label,
                extract_interviewee=False,  # 已经是受访者语句了
                return_full_trace=True
            )
            
            # 取第一条结果
            if results:
                return results[0].get('selected_candidate')
            
            return None
        
        except Exception as e:
            logger.error(f"生成编码失败: {e}")
            return None
    
    def _empty_result(self) -> Dict[str, Any]:
        """返回空结果"""
        return {
            "一阶编码": {},
            "二阶编码": {},
            "三阶编码": {},
            "file_sentence_mapping": {}
        }


# ============================================================
# 使用示例
# ============================================================

if __name__ == '__main__':
    from optimized_coding_pipeline import OptimizedCodingPipeline
    from model_manager import EnhancedModelManager
    from data_processor import DataProcessor
    
    # 初始化
    model_manager = EnhancedModelManager()
    data_processor = DataProcessor()
    
    # 创建优化流水线
    optimized_pipeline = OptimizedCodingPipeline(
        model_manager=model_manager,
        use_qa_classifier=True
    )
    
    # 创建完全兼容的适配器
    coding_generator = FullyCompatibleCodingAdapter(optimized_pipeline)
    
    # 处理文件
    test_files = [
        r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人11.docx'
    ]
    
    processed_data = data_processor.process_multiple_files(test_files)
    
    # 生成编码（完全兼容原有格式）
    raw_codes = coding_generator.generate_grounded_theory_codes_multi_files(
        processed_data,
        model_manager
    )
    
    print(f"一阶编码: {len(raw_codes['一阶编码'])} 条")
    print(f"二阶编码: {len(raw_codes['二阶编码'])} 条")
    print(f"三阶编码: {len(raw_codes['三阶编码'])} 条")
    
    # 检查格式
    if raw_codes['一阶编码']:
        first_key = list(raw_codes['一阶编码'].keys())[0]
        first_value = raw_codes['一阶编码'][first_key]
        print(f"\n第一条编码格式:")
        print(f"  [0] abstracted: {first_value[0][:40]}")
        print(f"  [1] source_sentences: {len(first_value[1])} 条")
        print(f"  [2] file_count: {first_value[2]}")
        print(f"  [3] sentence_count: {first_value[3]}")
        print(f"  [4] sentence_details: {len(first_value[4])} 条")
        
        # 检查 source_detail 结构
        if first_value[4]:
            detail = first_value[4][0]
            print(f"\n  source_detail 结构:")
            print(f"    file: {detail.get('file')}")
            print(f"    sentence: {detail.get('sentence', '')[:50]}...")
            print(f"    sentence_number: {detail.get('sentence_number')}")
