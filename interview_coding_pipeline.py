"""
批量访谈文本一阶编码流水线

流程：
1. 读取访谈文本（docx/txt）
2. 提取受访者语句（过滤访谈员问句）
3. 对每条受访者语句生成一阶编码
4. 输出结果（CSV/JSON）
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from speaker_role_extractor import SpeakerRoleExtractor
from enhanced_coding_generator import EnhancedCodingGenerator
from model_manager import EnhancedModelManager
import config

logger = logging.getLogger(__name__)


class InterviewCodingPipeline:
    """访谈文本一阶编码流水线"""
    
    def __init__(self, model_manager: Optional[EnhancedModelManager] = None):
        """
        初始化流水线
        
        Args:
            model_manager: 模型管理器（可选，如果不提供会自动创建）
        """
        self.speaker_extractor = SpeakerRoleExtractor()
        self.coding_generator = EnhancedCodingGenerator()
        self.model_manager = model_manager or EnhancedModelManager()
        
        # 配置一阶编码参数
        config.Config.FIRST_LEVEL_RECALL_ENHANCED = True
        config.Config.FIRST_LEVEL_USE_LABEL_RECALL_CANDIDATES = False
        config.Config.FIRST_LEVEL_PROTOTYPE_FILES = []
    
    def process_single_text(
        self,
        text: str,
        extract_interviewee: bool = True,
        return_full_trace: bool = True
    ) -> List[Dict[str, any]]:
        """
        处理单个文本，返回完整的一阶编码 trace
        
        Args:
            text: 原始访谈文本
            extract_interviewee: 是否提取受访者语句（False则对全文编码）
            return_full_trace: 是否返回完整trace（候选、打分、rerank等）
            
        Returns:
            编码结果列表，每条包含：
            {
                'original_text': 原始文本,
                'normalized_sentence': 归一化后的句子,
                'selected_candidate': 最终选中的一阶编码,
                'best_rule_candidate': 规则最佳候选,
                'used_rerank': 是否使用了rerank,
                'candidates': 候选列表（含打分、rerank分数等）,
                'speaker_confidence': 说话人识别置信度（如果extract_interviewee=True）,
                'speaker_label': 说话人标签
            }
        """
        results = []
        
        # 步骤1: 提取受访者语句
        if extract_interviewee:
            interviewee_segments = self.speaker_extractor.extract_interviewee_sentences(
                text,
                return_metadata=True
            )
        else:
            # 不提取，直接分句
            interviewee_segments = [
                {'text': text, 'speaker_label': None, 'confidence': 1.0, 'method': 'direct'}
            ]
        
        # 步骤2: 对每条受访者语句生成一阶编码 trace
        for seg in interviewee_segments:
            sent_text = seg['text']
            if not sent_text or len(sent_text) < 10:
                continue
            
            # 生成完整的一阶编码 trace
            trace = self.coding_generator.build_first_level_candidate_trace(
                sent_text,
                model_manager=self.model_manager,
                top_n=10 if return_full_trace else 5
            )
            
            # 构建结果
            result = {
                'original_text': sent_text,
                'normalized_sentence': trace.get('normalized_sentence', ''),
                'selected_candidate': trace.get('selected_candidate', ''),
                'best_rule_candidate': trace.get('best_rule_candidate', ''),
                'used_rerank': trace.get('used_rerank', False),
                'prototype_enabled': trace.get('prototype_enabled', False),
            }
            
            if extract_interviewee:
                result['speaker_confidence'] = seg['confidence']
                result['speaker_label'] = seg.get('speaker_label')
                result['speaker_method'] = seg.get('method')
            
            if return_full_trace:
                # 返回完整候选列表
                result['candidates'] = trace.get('candidates', [])
                result['prototype_hits'] = trace.get('prototype_hits', [])
            else:
                # 只返回 top 5 候选的简化信息
                candidates = trace.get('candidates', [])[:5]
                result['top_candidates'] = [
                    {
                        'text': c.get('text'),
                        'rerank_score': c.get('rerank_score'),
                        'rule_score': c.get('rule_score'),
                        'selected': c.get('selected', False)
                    }
                    for c in candidates
                ]
            
            results.append(result)
        
        return results
    
    def process_batch(
        self,
        texts: List[str],
        extract_interviewee: bool = True,
        return_full_trace: bool = True,
        show_progress: bool = True
    ) -> List[List[Dict[str, any]]]:
        """
        批量处理文本，返回完整 trace
        
        Args:
            texts: 文本列表
            extract_interviewee: 是否提取受访者语句
            return_full_trace: 是否返回完整trace
            show_progress: 是否显示进度
            
        Returns:
            每个文本的编码 trace 列表
        """
        all_results = []
        total = len(texts)
        
        for i, text in enumerate(texts):
            if show_progress and (i + 1) % 10 == 0:
                print(f"已处理 {i + 1}/{total} 个文本")
            
            try:
                results = self.process_single_text(
                    text,
                    extract_interviewee=extract_interviewee,
                    return_full_trace=return_full_trace
                )
                all_results.append(results)
            except Exception as e:
                logger.error(f"处理第 {i+1} 个文本失败: {e}")
                all_results.append([])
        
        return all_results
    
    def process_docx_file(
        self,
        file_path: str,
        extract_interviewee: bool = True,
        return_full_trace: bool = True
    ) -> List[Dict[str, any]]:
        """
        处理单个 docx 文件，返回完整 trace
        
        Args:
            file_path: docx 文件路径
            extract_interviewee: 是否提取受访者语句
            return_full_trace: 是否返回完整trace
            
        Returns:
            编码 trace 列表
        """
        try:
            from enhanced_docx_reader import EnhancedDocxReader
            reader = EnhancedDocxReader()
            full_text = reader.read_docx(file_path)
            logger.info(f"使用增强读取器读取文件: {file_path}")
        except Exception as e:
            logger.warning(f"增强读取器失败，使用标准读取器: {e}")
            # 降级到标准读取器
            try:
                from docx import Document
            except ImportError:
                raise ImportError("需要安装 python-docx: pip install python-docx")
            
            # 读取文档
            doc = Document(file_path)
            
            # 合并段落为完整文本
            paragraphs = []
            for para in doc.paragraphs:
                text = para.text.strip()
                if text and len(text) > 10:
                    # 跳过元数据行
                    if any(x in text for x in ['访谈', '时间', '地点', '受访者', '访谈员']):
                        continue
                    paragraphs.append(text)
            
            full_text = '\n'.join(paragraphs)
        
        # 处理文本，返回完整 trace
        results = self.process_single_text(
            full_text,
            extract_interviewee=extract_interviewee,
            return_full_trace=return_full_trace
        )
        
        # 添加文件名
        for r in results:
            r['source_file'] = Path(file_path).name
        
        return results
    
    def process_docx_folder(
        self,
        folder_path: str,
        output_csv: Optional[str] = None,
        output_json: Optional[str] = None,
        extract_interviewee: bool = True,
        return_full_trace: bool = True,
        max_files: Optional[int] = None
    ) -> pd.DataFrame:
        """
        批量处理文件夹中的 docx 文件，返回完整 trace
        
        Args:
            folder_path: 文件夹路径
            output_csv: 输出 CSV 文件路径（简化版，可选）
            output_json: 输出 JSON 文件路径（完整 trace，可选）
            extract_interviewee: 是否提取受访者语句
            return_full_trace: 是否返回完整trace
            max_files: 最多处理文件数（可选，用于测试）
            
        Returns:
            结果 DataFrame（简化版）
        """
        folder = Path(folder_path)
        docx_files = list(folder.glob('*.docx'))
        
        if max_files:
            docx_files = docx_files[:max_files]
        
        print(f"找到 {len(docx_files)} 个 docx 文件")
        
        all_results = []
        all_traces = []  # 保存完整 trace
        start_time = time.time()
        
        for i, docx_file in enumerate(docx_files):
            print(f"\n处理文件 {i+1}/{len(docx_files)}: {docx_file.name}")
            
            try:
                results = self.process_docx_file(
                    str(docx_file),
                    extract_interviewee=extract_interviewee,
                    return_full_trace=return_full_trace
                )
                
                # 保存完整 trace
                all_traces.extend(results)
                
                # 构建简化版结果（用于 CSV）
                for r in results:
                    simplified = {
                        'source_file': r.get('source_file'),
                        'original_text': r.get('original_text'),
                        'selected_candidate': r.get('selected_candidate'),
                        'speaker_label': r.get('speaker_label'),
                        'speaker_confidence': r.get('speaker_confidence'),
                        'used_rerank': r.get('used_rerank'),
                    }
                    all_results.append(simplified)
                
                print(f"  提取 {len(results)} 条受访者语句并完成编码")
            except Exception as e:
                logger.error(f"处理文件 {docx_file.name} 失败: {e}")
        
        elapsed = time.time() - start_time
        print(f"\n总耗时: {elapsed:.1f}秒")
        print(f"共处理 {len(all_results)} 条语句")
        print(f"平均每条: {elapsed/len(all_results):.2f}秒" if all_results else "")
        
        # 转换为 DataFrame（简化版）
        df = pd.DataFrame(all_results)
        
        # 保存简化版到 CSV
        if output_csv:
            df.to_csv(output_csv, index=False, encoding='utf-8-sig')
            print(f"\n简化结果已保存到: {output_csv}")
        
        # 保存完整 trace 到 JSON
        if output_json:
            import json
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(all_traces, f, ensure_ascii=False, indent=2)
            print(f"完整 trace 已保存到: {output_json}")
        
        return df


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='批量访谈文本一阶编码（返回完整trace）')
    parser.add_argument('input', help='输入文件夹路径')
    parser.add_argument('--output-csv', '-c', help='输出简化版 CSV 文件路径', default='coding_results.csv')
    parser.add_argument('--output-json', '-j', help='输出完整 trace JSON 文件路径', default='coding_traces.json')
    parser.add_argument('--max-files', '-n', type=int, help='最多处理文件数（用于测试）')
    parser.add_argument('--no-extract', action='store_true', help='不提取受访者语句，对全文编码')
    parser.add_argument('--no-trace', action='store_true', help='不返回完整trace，只返回最终编码')
    
    args = parser.parse_args()
    
    # 创建流水线
    pipeline = InterviewCodingPipeline()
    
    # 处理文件夹
    df = pipeline.process_docx_folder(
        args.input,
        output_csv=args.output_csv,
        output_json=args.output_json if not args.no_trace else None,
        extract_interviewee=not args.no_extract,
        return_full_trace=not args.no_trace,
        max_files=args.max_files
    )
    
    # 打印统计
    print("\n=== 编码质量统计 ===")
    print(f"总样本数: {len(df)}")
    
    if 'selected_candidate' in df.columns:
        empty = df['selected_candidate'].isna().sum() + (df['selected_candidate'] == '').sum()
        print(f"空编码: {empty} ({empty/len(df)*100:.1f}%)")
        
        avg_len = df['selected_candidate'].str.len().mean()
        print(f"平均编码长度: {avg_len:.1f}字")
    
    if 'speaker_confidence' in df.columns:
        avg_conf = df['speaker_confidence'].mean()
        print(f"平均说话人识别置信度: {avg_conf:.2f}")
    
    if 'used_rerank' in df.columns:
        rerank_count = df['used_rerank'].sum()
        print(f"使用 rerank: {rerank_count} ({rerank_count/len(df)*100:.1f}%)")


if __name__ == '__main__':
    # 如果没有命令行参数，运行测试
    if len(sys.argv) == 1:
        print("测试模式：处理示例文件夹，返回完整 trace")
        print("=" * 60)
        
        # 测试路径
        test_folder = r"C:\Users\33288\Downloads\新文本\润色后文件"
        
        if not os.path.exists(test_folder):
            print(f"测试文件夹不存在: {test_folder}")
            print("\n使用方法:")
            print("  python interview_coding_pipeline.py <输入文件夹> --output-csv <输出CSV> --output-json <输出JSON>")
            sys.exit(1)
        
        # 创建流水线
        pipeline = InterviewCodingPipeline()
        
        # 只处理前3个文件作为测试
        df = pipeline.process_docx_folder(
            test_folder,
            output_csv='test_coding_results.csv',
            output_json='test_coding_traces.json',
            extract_interviewee=True,
            return_full_trace=True,
            max_files=3
        )
        
        # 显示前5条结果的完整 trace
        print("\n=== 前5条编码 trace 示例 ===")
        
        # 读取完整 trace
        import json
        with open('test_coding_traces.json', 'r', encoding='utf-8') as f:
            traces = json.load(f)
        
        for i, trace in enumerate(traces[:5]):
            print(f"\n[{i+1}] 文件: {trace.get('source_file', 'unknown')}")
            print(f"原文: {trace['original_text'][:80]}...")
            print(f"归一化: {trace.get('normalized_sentence', '')[:60]}...")
            print(f"最终编码: {trace['selected_candidate']}")
            print(f"规则最佳: {trace.get('best_rule_candidate', '')}")
            print(f"使用 rerank: {trace.get('used_rerank', False)}")
            
            if 'speaker_label' in trace:
                print(f"说话人: {trace['speaker_label']} (置信度: {trace.get('speaker_confidence', 0):.2f})")
            
            # 显示 top 3 候选
            candidates = trace.get('candidates', [])[:3]
            if candidates:
                print(f"Top 3 候选:")
                for j, cand in enumerate(candidates):
                    print(f"  {j+1}. {cand.get('text', '')} "
                          f"(rerank: {cand.get('rerank_score', 'N/A')}, "
                          f"rule: {cand.get('rule_score', 0):.2f}, "
                          f"selected: {cand.get('selected', False)})")
    else:
        main()
