"""
优化流水线适配器
将 OptimizedCodingPipeline 适配到主程序接口
"""

import os
import logging
from typing import List, Dict, Any
from optimized_coding_pipeline import OptimizedCodingPipeline

logger = logging.getLogger(__name__)


class CodingPipelineAdapter:
    """
    适配器：将 OptimizedCodingPipeline 适配到主程序接口
    
    主程序期望的接口：
        generate_grounded_theory_codes_multi_files(files) -> Dict[str, List[Dict]]
    
    优化流水线接口：
        process_file(file_path, adaptive=True) -> List[Dict]
    """
    
    def __init__(self, pipeline: OptimizedCodingPipeline):
        """
        初始化适配器
        
        Args:
            pipeline: OptimizedCodingPipeline 实例
        """
        self.pipeline = pipeline
        logger.info("CodingPipelineAdapter 已初始化")
    
    def generate_grounded_theory_codes_multi_files(
        self,
        files,  # 可以是文件路径列表或processed_data字典
        model_manager=None,  # 兼容主程序参数
        adaptive: bool = True,
        progress_callback=None,  # 兼容主程序参数
        use_trained_model: bool = False,  # 兼容主程序参数
        coding_thresholds: dict = None,  # 兼容主程序参数
        **kwargs
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        多文件编码生成（适配主程序接口）
        
        Args:
            files: 文件路径列表 或 processed_data字典
            model_manager: 模型管理器（兼容性参数）
            adaptive: 是否启用混合策略（默认True）
            progress_callback: 进度回调（兼容性参数）
            use_trained_model: 是否使用训练模型（兼容性参数）
            coding_thresholds: 编码阈值（兼容性参数）
            **kwargs: 其他参数（兼容性）
        
        Returns:
            {
                'file1.docx': [
                    {
                        'text': '受访者的原文',
                        'code': '一阶编码',
                        'confidence': 0.95,
                        'method': 'rule_explicit',
                        'speaker': 'speaker_respondent',
                        'candidates': [...],  # 候选编码列表
                        'scores': [...]       # 候选编码分数
                    },
                    ...
                ],
                ...
            }
        """
        results = {}
        
        # 判断输入类型
        if isinstance(files, dict):
            # processed_data格式：{'file_sentence_mapping': {...}, 'combined_text': ...}
            if 'file_sentence_mapping' in files:
                # 从file_sentence_mapping中提取文件路径
                file_list = []
                for filename, data in files['file_sentence_mapping'].items():
                    file_path = data.get('file_path', filename)
                    file_list.append(file_path)
                logger.info(f"检测到processed_data格式，提取文件路径: {len(file_list)}个文件")
            elif 'file_paths' in files:
                # 备用格式
                file_list = files['file_paths']
                logger.info(f"检测到file_paths格式: {len(file_list)}个文件")
            else:
                # 可能是旧格式的字典
                logger.warning(f"未识别的字典格式，尝试提取键作为文件路径")
                file_list = list(files.keys())
        elif isinstance(files, (list, tuple)):
            # 文件路径列表
            file_list = files
            logger.info(f"检测到文件路径列表: {len(file_list)}个文件")
        else:
            logger.error(f"不支持的输入类型: {type(files)}")
            return {}
        
        logger.info(f"开始处理 {len(file_list)} 个文件（混合策略: {adaptive}）")
        
        for i, file_path in enumerate(file_list):
            file_name = os.path.basename(file_path)
            logger.info(f"[{i+1}/{len(file_list)}] 处理文件: {file_name}")
            
            # 更新进度
            if progress_callback:
                progress = 30 + int((i / len(file_list)) * 40)
                progress_callback(progress)
            
            try:
                # 使用优化流水线处理
                file_results = self.pipeline.process_file(
                    file_path,
                    adaptive=adaptive  # 启用混合策略
                )
                
                # 转换为主程序期望的格式
                converted_results = []
                for r in file_results:
                    # 只返回有编码的结果
                    if r.get('selected_candidate'):
                        converted_results.append({
                            'text': r.get('text', ''),
                            'code': r.get('selected_candidate', ''),
                            'confidence': r.get('confidence', 0.0),
                            'method': r.get('method', 'unknown'),
                            'speaker': r.get('speaker', ''),
                            # 保留额外信息供调试和分析
                            'candidates': r.get('candidates', []),
                            'scores': r.get('scores', [])
                        })
                
                results[file_name] = converted_results
                
                logger.info(f"  完成: {len(converted_results)} 条编码")
                
            except Exception as e:
                logger.error(f"  处理文件失败 {file_name}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                results[file_name] = []
        
        total_codes = sum(len(codes) for codes in results.values())
        logger.info(f"多文件处理完成: 总计 {total_codes} 条编码")
        
        # 转换为主程序期望的格式
        legacy_format = self._convert_to_legacy_format(results)
        
        return legacy_format
    
    def _convert_to_legacy_format(self, results: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        将优化流水线格式转换为主程序期望的格式
        
        输入：
        {
            'file1.docx': [
                {'text': '...', 'code': '...', ...},
                ...
            ]
        }
        
        输出：
        {
            "一阶编码": {
                "code_1": [编码内容, 原文, file_count, sentence_count, sentence_details],
                ...
            },
            "二阶编码": {
                "自动生成编码": ["code_1", "code_2", ...]
            },
            "三阶编码": {
                "一阶编码": ["自动生成编码"]
            }
        }
        """
        first_level = {}
        code_counter = 1
        all_code_keys = []
        
        # 统计文件数
        file_count = len(results)
        
        for filename, codes in results.items():
            for code_data in codes:
                text = code_data.get('text', '')
                code = code_data.get('code', '')
                
                if code:  # 只处理有编码的
                    key = f"code_{code_counter}"
                    all_code_keys.append(key)
                    
                    # sentence_details 格式
                    sentence_details = [{
                        'file': filename,
                        'sentence': text,
                        'code_id': f'A{code_counter:02d}'
                    }]
                    
                    first_level[key] = [
                        code,              # 0: 编码内容
                        text,              # 1: 原文
                        file_count,        # 2: file_count
                        1,                 # 3: sentence_count (每个编码对应1个句子)
                        sentence_details   # 4: sentence_details
                    ]
                    code_counter += 1
        
        logger.info(f"格式转换完成: {len(first_level)} 条一阶编码")
        
        # 创建默认的二阶和三阶编码结构
        # 这样 build_coding_structure 才能正常工作
        second_level = {
            "自动生成编码": all_code_keys  # 所有一阶编码归到一个二阶类别
        }
        
        third_level = {
            "一阶编码": ["自动生成编码"]  # 二阶类别归到一个三阶类别
        }
        
        return {
            "一阶编码": first_level,
            "二阶编码": second_level,
            "三阶编码": third_level
        }
    
    def generate_grounded_theory_codes(
        self,
        file_path: str,
        adaptive: bool = True,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        单文件编码生成（适配主程序接口）
        
        Args:
            file_path: 文件路径
            adaptive: 是否启用混合策略（默认True）
            **kwargs: 其他参数（兼容性）
        
        Returns:
            [
                {
                    'text': '受访者的原文',
                    'code': '一阶编码',
                    'confidence': 0.95,
                    ...
                },
                ...
            ]
        """
        results = self.generate_grounded_theory_codes_multi_files(
            [file_path],
            adaptive=adaptive,
            **kwargs
        )
        
        file_name = os.path.basename(file_path)
        return results.get(file_name, [])
    
    def get_statistics(self, results: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        获取编码统计信息
        
        Args:
            results: generate_grounded_theory_codes_multi_files 的返回结果
        
        Returns:
            {
                'total_files': 文件数,
                'total_codes': 总编码数,
                'avg_confidence': 平均置信度,
                'method_distribution': 方法分布,
                'empty_codes': 空编码数
            }
        """
        total_files = len(results)
        total_codes = sum(len(codes) for codes in results.values())
        
        all_confidences = []
        method_counts = {}
        
        for codes in results.values():
            for code in codes:
                all_confidences.append(code.get('confidence', 0.0))
                method = code.get('method', 'unknown')
                method_counts[method] = method_counts.get(method, 0) + 1
        
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        
        return {
            'total_files': total_files,
            'total_codes': total_codes,
            'avg_confidence': avg_confidence,
            'method_distribution': method_counts,
            'files': {
                file_name: len(codes)
                for file_name, codes in results.items()
            }
        }


# 便捷函数
def create_optimized_adapter(
    model_manager=None,
    use_qa_classifier: bool = True
) -> CodingPipelineAdapter:
    """
    创建优化流水线适配器（便捷函数）
    
    Args:
        model_manager: 模型管理器
        use_qa_classifier: 是否启用QA分类器（混合策略）
    
    Returns:
        CodingPipelineAdapter 实例
    """
    pipeline = OptimizedCodingPipeline(
        model_manager=model_manager,
        use_qa_classifier=use_qa_classifier
    )
    
    return CodingPipelineAdapter(pipeline)


if __name__ == '__main__':
    # 测试适配器
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建适配器
    adapter = create_optimized_adapter(use_qa_classifier=True)
    
    # 测试文件
    test_files = [
        r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人11.docx'
    ]
    
    # 生成编码
    results = adapter.generate_grounded_theory_codes_multi_files(
        test_files,
        adaptive=True
    )
    
    # 显示结果
    for file_name, codes in results.items():
        print(f'\n文件: {file_name}')
        print(f'编码数: {len(codes)}')
        
        if codes:
            print('\n前3条示例:')
            for i, code in enumerate(codes[:3]):
                print(f'  [{i+1}] {code["method"]} | 置信度:{code["confidence"]:.2f}')
                print(f'      原文: {code["text"][:50]}...')
                print(f'      编码: {code["code"][:40]}')
    
    # 统计信息
    stats = adapter.get_statistics(results)
    print(f'\n统计信息:')
    print(f'  总文件: {stats["total_files"]}')
    print(f'  总编码: {stats["total_codes"]}')
    print(f'  平均置信度: {stats["avg_confidence"]:.2f}')
    print(f'  方法分布: {stats["method_distribution"]}')
