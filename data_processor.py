import os
import json
import re
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple, Set, Optional
import pandas as pd
from docx import Document
import copy
from collections import defaultdict

logger = logging.getLogger(__name__)

# 尝试导入可选依赖
try:
    import win32com.client as win32

    WIN32COM_AVAILABLE = True
except ImportError:
    WIN32COM_AVAILABLE = False

try:
    import pypandoc

    PYPANDOC_AVAILABLE = True
except ImportError:
    PYPANDOC_AVAILABLE = False


class TextNumberingManager:
    """高效的文本句子编号管理器"""

    def __init__(self):
        # 使用多个缓存提高效率
        self._sentence_cache = {}  # 缓存已编号的句子 {sentence: number}
        self._file_sentences = defaultdict(list)  # 文件到句子列表的映射
        self._number_sentence = {}  # 编号到句子的反向映射
        self._next_number = 1  # 下一个可用的编号

        # 预编译正则表达式，提高效率
        self._sentence_split_pattern = re.compile(r'[。！？!?]')

    def reset(self):
        """重置编号管理器"""
        self._sentence_cache.clear()
        self._file_sentences.clear()
        self._number_sentence.clear()
        self._next_number = 1

    def number_text(self, text: str, filename: str = "") -> Tuple[str, Dict[int, str]]:
        """
        为文本中的句子编号

        返回: (编号后的文本, 编号到句子的映射)
        """
        if not text:
            return "", {}

        # 快速分割句子
        sentences = self._fast_split_sentences(text)
        if not sentences:
            return text, {}

        numbered_text_parts = []
        number_mapping = {}

        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue

            # 分配新编号，使用全局下一个编号，确保编号连续
            number = self._next_number
            self._next_number += 1

            # 更新缓存 - 现在每个句子都获得新编号，但仍然记录缓存以便后续识别重复
            if sentence not in self._sentence_cache:
                self._sentence_cache[sentence] = number
            self._number_sentence[number] = sentence

            if filename and filename != "default":  # 只有在filename非空时才记录
                self._file_sentences[filename].append((number, sentence))

            # 构建映射
            number_mapping[number] = sentence

            # 添加编号标记（在句子后添加编号）
            if i < len(sentences) - 1:
                # 不是最后一个句子
                numbered_text_parts.append(f"{sentence} [{number}]")
            else:
                # 最后一个句子
                numbered_text_parts.append(f"{sentence} [{number}]")

        numbered_text = "\n".join(numbered_text_parts)
        return numbered_text, number_mapping

    def _fast_split_sentences(self, text: str) -> List[str]:
        """快速分割句子 - 优化版本"""
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text.strip())

        # 使用预编译的正则表达式分割
        parts = self._sentence_split_pattern.split(text)

        # 过滤空字符串和短句子
        sentences = []
        for part in parts:
            clean_part = part.strip()
            if clean_part and len(clean_part) >= 3:  # 过滤太短的"句子"
                sentences.append(clean_part)

        return sentences

    def get_sentence_by_number(self, number: int) -> str:
        """根据编号获取句子"""
        return self._number_sentence.get(number, "")

    def get_number_by_sentence(self, sentence: str) -> int:
        """根据句子获取编号"""
        return self._sentence_cache.get(sentence, 0)

    def get_file_sentences(self, filename: str) -> List[Tuple[int, str]]:
        """获取文件中所有已编号的句子"""
        return self._file_sentences.get(filename, [])

    def get_all_numbered_sentences(self) -> Dict[int, str]:
        """获取所有已编号的句子"""
        return dict(self._number_sentence)

    def batch_number_texts(self, texts: Dict[str, str]) -> Dict[str, Tuple[str, Dict[int, str]]]:
        """批量处理多个文本，提高效率"""
        results = {}

        for filename, text in texts.items():
            try:
                numbered_text, mapping = self.number_text(text, filename)
                results[filename] = (numbered_text, mapping)
            except Exception as e:
                logger.error(f"为文件 {filename} 编号失败: {e}")
                results[filename] = (text, {})

        return results


class DataProcessor:
    """数据处理器 - 支持多文件处理和Word文档"""

    def __init__(self):
        self.sentence_counter = 0
        self.file_sentence_mapping = {}

        # 初始化模块级别的变量
        try:
            import win32com.client as win32
            self.WIN32COM_AVAILABLE = True
        except ImportError:
            self.WIN32COM_AVAILABLE = False

        try:
            import pypandoc
            self.PYPANDOC_AVAILABLE = True
        except ImportError:
            self.PYPANDOC_AVAILABLE = False

        # 添加句子编号管理器
        self.numbering_manager = TextNumberingManager()
        self._all_numbered_texts = {}  # 缓存所有编号后的文本

    # ========== 文件读取相关方法 ==========

    def read_doc_file(self, file_path: str) -> str:
        """读取.doc文件，使用多种备选方法"""
        # 方法1: 尝试使用win32com（仅Windows）
        if WIN32COM_AVAILABLE:
            try:
                return self._read_doc_with_win32com(file_path)
            except Exception as e:
                logger.warning(f"win32com读取失败，尝试其他方法: {e}")

        # 方法2: 尝试使用pypandoc
        if PYPANDOC_AVAILABLE:
            try:
                return self._read_doc_with_pypandoc(file_path)
            except Exception as e:
                logger.warning(f"pypandoc读取失败，尝试其他方法: {e}")

        # 方法3: 尝试使用pypandoc或win32com作为降级方案
        try:
            if PYPANDOC_AVAILABLE:
                return self._read_doc_with_antiword(file_path)  # 使用更新后的函数
            elif WIN32COM_AVAILABLE:
                return self._read_doc_with_win32com(file_path)
        except Exception as e:
            logger.warning(f"降级方法读取失败: {e}")

        # 如果所有方法都失败，抛出异常
        raise Exception("无法读取.doc文件，请安装win32com或pypandoc")

    def _read_doc_with_win32com(self, file_path: str) -> str:
        """使用win32com读取.doc文件"""
        if not WIN32COM_AVAILABLE:
            raise Exception("win32com不可用")
        
        import win32com.client as win32
        word_app = None
        doc = None
        try:
            word_app = win32.Dispatch('Word.Application')
            word_app.Visible = False  # 不显示Word界面
            word_app.DisplayAlerts = 0  # 不显示警告

            # 打开文档
            doc = word_app.Documents.Open(os.path.abspath(file_path))

            # 提取文本内容
            content = doc.Content.Text

            logger.info(f"成功使用win32com读取Word文档(.doc): {file_path}")
            return content.strip()
        except Exception as e:
            logger.error(f"win32com读取文档失败: {e}")
            raise
        finally:
            # 确保资源被正确释放
            if doc is not None:
                try:
                    doc.Close()
                except:
                    pass
            if word_app is not None:
                try:
                    word_app.Quit()
                except:
                    pass

    def _read_doc_with_pypandoc(self, file_path: str) -> str:
        """使用pypandoc读取.doc文件"""
        if not PYPANDOC_AVAILABLE:
            raise Exception("pypandoc不可用")
        
        import pypandoc
        # 将.doc文件转换为文本
        content = pypandoc.convert_file(file_path, 'plain')
        logger.info(f"成功使用pypandoc读取Word文档(.doc): {file_path}")
        return content.strip()

    def _read_doc_with_antiword(self, file_path: str) -> str:
        """使用pypandoc作为备用方案读取.doc文件"""
        if not PYPANDOC_AVAILABLE:
            raise Exception("pypandoc不可用")
        
        import pypandoc
        import zipfile
        import tempfile
        import os
        from docx import Document
        
        # 创建一个临时的docx文件，将doc内容转换
        temp_docx_path = None
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
                temp_docx_path = temp_file.name
            
            # 尝试使用pypandoc转换.doc到.docx
            pypandoc.convert_file(file_path, 'docx', outputfile=temp_docx_path)
            
            # 读取转换后的.docx文件
            doc = Document(temp_docx_path)
            content = ""
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    content += paragraph.text + "\n"
            
            logger.info(f"成功使用pypandoc转换并读取.doc文件: {file_path}")
            return content.strip()
        except Exception as e:
            logger.warning(f"pypandoc转换.doc失败: {e}")
            # 如果转换失败，尝试其他方法
            if temp_docx_path and os.path.exists(temp_docx_path):
                try:
                    os.unlink(temp_docx_path)
                except:
                    pass
            raise e

    def read_text_file(self, file_path: str) -> str:
        """读取文本文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"成功读取文本文件: {file_path}")
            return content
        except Exception as e:
            logger.error(f"读取文本文件失败 {file_path}: {e}")
            raise

    def read_word_file(self, file_path: str) -> str:
        """读取Word文档，支持.doc和.docx格式"""
        try:
            # 根据文件扩展名选择适当的读取方法
            if file_path.lower().endswith('.docx'):
                # 使用python-docx读取.docx文件
                doc = Document(file_path)
                content = ""
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        content += paragraph.text + "\n"
                logger.info(f"成功读取Word文档: {file_path}")
                return content.strip()
            elif file_path.lower().endswith('.doc'):
                # 使用专门的.doc文件读取方法
                return self.read_doc_file(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {file_path}")
        except Exception as e:
            logger.error(f"读取Word文档失败 {file_path}: {e}")
            # 对于.doc文件，不应该降级到文本读取，因为它们是二进制格式
            if file_path.lower().endswith('.doc'):
                raise Exception(f"无法读取.doc文件 {file_path}: {str(e)}")
            else:
                # 其他情况可以尝试文本读取
                return self.read_text_file(file_path)

    def read_file(self, file_path: str) -> str:
        """读取文件（自动判断类型）"""
        file_lower = file_path.lower()
        if file_lower.endswith('.docx') or file_lower.endswith('.doc'):
            return self.read_word_file(file_path)
        else:
            return self.read_text_file(file_path)

    # ========== 主要处理方法 ==========

    def process_multiple_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """处理多个文件，返回统一的文本和文件映射 - 增强版（带句子编号）"""
        # 先读取所有文件内容
        file_contents = {}
        for file_path in file_paths:
            try:
                content = self.read_file(file_path)
                filename = os.path.basename(file_path)
                file_contents[filename] = content
                logger.info(f"成功读取文件: {filename}")
            except Exception as e:
                logger.error(f"读取文件失败 {file_path}: {e}")
                continue

        if not file_contents:
            logger.error("没有成功读取任何文件")
            return {
                'combined_text': "",
                'file_sentence_mapping': {},
                'total_files': 0,
                'total_sentences': 0,
                'numbering_manager': self.numbering_manager
            }

        # 为所有文件内容批量编号
        numbered_results = self.numbering_manager.batch_number_texts(file_contents)

        all_texts = []
        file_sentence_mapping = {}

        for filename, (numbered_text, number_mapping) in numbered_results.items():
            original_content = file_contents[filename]

            # 智能识别段落（区分采访人和受访人）
            paragraphs = self.identify_interview_paragraphs(original_content, filename)

            # 提取受访人有意义的句子（带编号信息）
            respondent_sentences = self.extract_respondent_sentences_with_numbers(
                paragraphs, filename, number_mapping
            )

            # 建立文件到句子的映射
            file_sentence_mapping[filename] = {
                'file_path': next((fp for fp in file_paths if os.path.basename(fp) == filename), ''),
                'sentences': respondent_sentences,
                'original_content': original_content,
                'numbered_content': numbered_text,  # 添加编号后的文本
                'paragraphs': paragraphs,
                'number_mapping': number_mapping  # 添加编号映射
            }

            # 合并文本（用于编码生成）
            all_texts.append(original_content)

            # 缓存编号后的文本
            self._all_numbered_texts[filename] = numbered_text

            logger.info(f"处理文件 {filename}: 识别 {len(paragraphs)} 个段落，提取 {len(respondent_sentences)} 个受访人句子")

        # 合并所有文本
        combined_text = "\n\n".join(all_texts)

        return {
            'combined_text': combined_text,
            'file_sentence_mapping': file_sentence_mapping,
            'total_files': len(file_paths),
            'total_sentences': sum(len(data['sentences']) for data in file_sentence_mapping.values()),
            'numbering_manager': self.numbering_manager  # 返回编号管理器
        }

    # ========== 句子编号相关方法 ==========

    def extract_respondent_sentences_with_numbers(self, paragraphs: List[Dict[str, Any]],
                                                  filename: str,
                                                  number_mapping: Dict[int, str]) -> List[Dict[str, Any]]:
        """从受访人段落中提取有意义的句子（带编号信息）"""
        respondent_sentences = []

        for paragraph in paragraphs:
            if paragraph['speaker'] == 'respondent':
                content = paragraph['content']
                sentences = self.split_into_sentences(content)

                for sentence in sentences:
                    if self.is_meaningful_sentence(sentence):
                        # 查找这个句子的编号
                        sentence_number = 0
                        clean_sentence = sentence.strip()

                        # 在编号映射中查找
                        for num, sent in number_mapping.items():
                            if sent.strip() == clean_sentence:
                                sentence_number = num
                                break

                        respondent_sentences.append({
                            'content': sentence,
                            'original_content': sentence,
                            'numbered_content': f"({sentence_number}) {sentence}" if sentence_number else sentence,
                            'sentence_number': sentence_number,
                            'paragraph_content': content[:100] + '...' if len(content) > 100 else content,
                            'filename': filename,
                            'speaker': 'respondent',
                            'start_position': 0,
                            'end_position': len(sentence)
                        })

        return respondent_sentences

    def export_numbered_sentences_to_file(self, file_path: str) -> bool:
        """导出所有编号句子到文件"""
        try:
            # 获取所有编号句子
            all_sentences = self.numbering_manager.get_all_numbered_sentences()

            # 构建文件关联信息
            sentence_files = defaultdict(list)
            for filename in self._all_numbered_texts.keys():
                file_sentences = self.numbering_manager.get_file_sentences(filename)
                for number, _ in file_sentences:
                    sentence_files[number].append(filename)

            # 准备表格数据
            table_data = []
            for number, sentence in sorted(all_sentences.items()):
                table_data.append({
                    '句子编号': number,
                    '句子内容': sentence,
                    '出现文件': '; '.join(sentence_files.get(number, []))
                })

            # 创建DataFrame
            df = pd.DataFrame(table_data)

            # 根据文件扩展名选择导出格式
            if file_path.endswith('.xlsx'):
                df.to_excel(file_path, index=False, engine='openpyxl')
            elif file_path.endswith('.csv'):
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            else:
                # 默认导出为Excel
                file_path = file_path.replace('.json', '.xlsx')
                df.to_excel(file_path, index=False, engine='openpyxl')

            logger.info(f"已导出 {len(table_data)} 个编号句子到 {file_path}")
            return True

        except Exception as e:
            logger.error(f"导出编号句子失败: {e}")
            return False

    # ========== 文本处理核心方法 ==========

    def identify_interview_paragraphs(self, content: str, filename: str) -> List[Dict[str, Any]]:
        """智能识别采访段落，区分采访人和受访人"""
        paragraphs = []
        lines = content.split('\n')

        current_paragraph = []
        current_speaker = None
        paragraph_start_line = 0

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                if current_paragraph and current_speaker:
                    # 保存当前段落
                    paragraph_text = '\n'.join(current_paragraph)
                    paragraphs.append({
                        'speaker': current_speaker,
                        'content': paragraph_text,
                        'start_line': paragraph_start_line,
                        'end_line': i,
                        'filename': filename
                    })
                    current_paragraph = []
                    current_speaker = None
                continue

            # 检测说话人
            speaker = self.detect_speaker(line)

            if speaker and current_speaker != speaker:
                # 保存上一个段落
                if current_paragraph and current_speaker:
                    paragraph_text = '\n'.join(current_paragraph)
                    paragraphs.append({
                        'speaker': current_speaker,
                        'content': paragraph_text,
                        'start_line': paragraph_start_line,
                        'end_line': i,
                        'filename': filename
                    })

                # 开始新段落
                current_paragraph = [line]
                current_speaker = speaker
                paragraph_start_line = i
            else:
                current_paragraph.append(line)

        # 添加最后一个段落
        if current_paragraph and current_speaker:
            paragraph_text = '\n'.join(current_paragraph)
            paragraphs.append({
                'speaker': current_speaker,
                'content': paragraph_text,
                'start_line': paragraph_start_line,
                'end_line': len(lines),
                'filename': filename
            })

        return paragraphs

    def detect_speaker(self, line: str) -> Optional[str]:
        """检测说话人"""
        # 采访人模式
        interviewer_patterns = [
            r'^[问Qq][：:]', r'^提问[：:]', r'^采访[：:]', r'^访谈[：:]',
            r'^主持人[：:]', r'^记者[：:]', r'^访员[：:]', r'^请问',
            r'^您觉得', r'^您认为', r'^你们', r'^公司', r'^团队'
        ]

        # 受访人模式
        respondent_patterns = [
            r'^[答Aa][：:]', r'^回答[：:]', r'^受访[：:]', r'^被访[：:]',
            r'^嘉宾[：:]', r'^专家[：:]', r'^我们', r'^我的', r'^我觉得',
            r'^我认为', r'^我们的', r'^负责', r'^管理', r'^开发'
        ]

        # 检查采访人模式
        for pattern in interviewer_patterns:
            if re.search(pattern, line):
                return "interviewer"

        # 检查受访人模式
        for pattern in respondent_patterns:
            if re.search(pattern, line):
                return "respondent"

        # 基于内容判断
        if self.is_interviewer_line(line):
            return "interviewer"
        elif self.is_respondent_line(line):
            return "respondent"

        return None

    def is_interviewer_line(self, line: str) -> bool:
        """判断是否是采访人说的话"""
        interviewer_indicators = [
            '请问', '想问', '了解', '采访', '提问', '访谈', '什么', '为什么', '如何', '怎样',
            '吗？', '呢？', '负责什么', '负责哪块', '收益如何', '感觉如何', '如何改进',
            '有什么困难', '什么挑战', '未来计划', '目标是什么'
        ]

        # 包含疑问词的短句很可能是采访人
        if any(indicator in line for indicator in interviewer_indicators):
            return True

        # 以问号结尾的短句
        if line.endswith(('？', '?')) and len(line) < 50:
            return True

        return False

    def is_respondent_line(self, line: str) -> bool:
        """判断是否是受访人说的话"""
        # 排除明显的采访人特征
        if self.is_interviewer_line(line):
            return False

        respondent_indicators = [
            '我们', '我的', '我觉得', '我认为', '我们的', '团队', '工作', '项目',
            '负责', '管理', '开发', '设计', '测试', '经验', '感受', '收获',
            '成果', '效果', '改进', '优化', '提升', '解决', '处理', '应对'
        ]

        # 包含工作内容或个人感受的较长的句子
        content_indicators = any(indicator in line for indicator in respondent_indicators)

        # 长度判断：受访人的回答通常较长
        if len(line) > 25 and content_indicators:
            return True

        return len(line) > 35  # 较长的内容很可能是受访人

    def extract_respondent_sentences(self, paragraphs: List[Dict[str, Any]], filename: str) -> List[Dict[str, Any]]:
        """从受访人段落中提取有意义的句子"""
        respondent_sentences = []

        for paragraph in paragraphs:
            if paragraph['speaker'] == 'respondent':
                content = paragraph['content']
                sentences = self.split_into_sentences(content)

                for sentence in sentences:
                    if self.is_meaningful_sentence(sentence):
                        respondent_sentences.append({
                            'content': sentence,
                            'original_content': sentence,  # 明确保存原始内容
                            'paragraph_content': content[:100] + '...' if len(content) > 100 else content,
                            'filename': filename,
                            'speaker': 'respondent',
                            'start_position': 0,
                            'end_position': len(sentence)
                        })

        return respondent_sentences

    def split_into_sentences(self, text: str) -> List[str]:
        """将文本分割成句子"""
        # 使用中文句号、问号、感叹号分割
        sentences = re.split(r'[。！？!?]', text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) >= 5]

    def is_meaningful_sentence(self, sentence: str) -> bool:
        """判断句子是否有意义"""
        # 过滤无意义短句
        meaningless_patterns = [
            r'^为什么[？?]?$', r'^我不知道[。.]?$', r'^什么意思[？?]?$',
            r'^然后呢[？?]?$', r'^还有吗[？?]?$', r'^嗯+$', r'^啊+$',
            r'^对+$', r'^是+$', r'^好+$', r'^行+$'
        ]

        for pattern in meaningless_patterns:
            if re.match(pattern, sentence.strip()):
                return False

        # 检查句子长度和内容
        if len(sentence.strip()) < 8:
            return False

        # 检查是否包含实质性内容
        meaningful_keywords = [
            '因为', '所以', '但是', '然而', '因此', '于是', '然后',
            '工作', '团队', '管理', '发展', '创新', '问题', '解决',
            '感觉', '认为', '觉得', '应该', '需要', '重要', '负责',
            '方法', '技术', '项目', '质量', '检测', '领导', '变革',
            '主要', '关键', '重点', '核心', '特别', '尤其', '总之',
            '目标', '成果', '效果', '影响', '原因', '结果', '过程'
        ]

        return any(keyword in sentence for keyword in meaningful_keywords) or len(sentence) >= 15

    # ========== 文本清理方法 ==========

    def clean_text(self, text: str) -> str:
        """清洗文本 - 增强版，过滤录音转录信息"""
        if not text:
            return ""

        # 按行处理
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 过滤说话人标记（如：说话人1 00:51, Speaker1 12:30等）
            if self.is_speaker_time_mark(line):
                continue

            # 过滤纯时间标记 (00:01, 12:30:45)
            if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', line):
                continue

            # 过滤提问人标记（如：采访者：，提问者：，Interviewer: 等）
            if self.is_interviewer_mark(line):
                continue

            # 清理多余的标点符号
            line = re.sub(r'[，,；;]{2,}', '，', line)  # 多个逗号/分号合并为一个
            line = re.sub(r'[。！？!?]{2,}', '。', line)  # 多个句号合并为一个

            cleaned_lines.append(line)

        # 重新组合文本
        cleaned_text = '\n'.join(cleaned_lines)

        # 进一步清理整个文本
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  # 合并多个空格
        cleaned_text = re.sub(r'([。！？!?])\s*', r'\1\n', cleaned_text)  # 在句子结束符后换行

        return cleaned_text.strip()

    def is_speaker_time_mark(self, line: str) -> bool:
        """判断是否是说话人时间标记"""
        # 匹配模式：说话人 + 时间
        patterns = [
            r'^[a-zA-Z\u4e00-\u9fa5]+\s*\d+\s*\d+:\d+',  # 说话人1 00:51
            r'^[a-zA-Z\u4e00-\u9fa5]+\d*\s*\d+:\d+',  # Speaker1 12:30
            r'^[a-zA-Z\u4e00-\u9fa5]+\s*\d+:\d+',  # 采访者 01:23
            r'^[a-zA-Z]+\s*\d+:\d+',  # Interviewer 12:30
            r'^[\u4e00-\u9fa5]+\s*\d+:\d+',  # 受访者 02:15
        ]

        for pattern in patterns:
            if re.match(pattern, line):
                return True
        return False

    def is_interviewer_mark(self, line: str) -> bool:
        """判断是否是采访人标记"""
        # 匹配采访人标记
        interviewer_marks = [
            r'^[a-zA-Z\u4e00-\u9fa5]+[：:]',  # 任何中文或英文后跟冒号
        ]

        # 但排除可能是受访人内容的情况
        respondent_indicators = ['我们', '我的', '我觉得', '我认为', '我们的', '负责', '管理', '开发']

        for pattern in interviewer_marks:
            if re.match(pattern, line):
                # 检查是否包含受访人特征，如果是则保留
                content_after_colon = re.sub(r'^[a-zA-Z\u4e00-\u9fa5]+[：:]', '', line).strip()
                if any(indicator in content_after_colon for indicator in respondent_indicators):
                    return False
                return True
        return False

    # ========== 增强的说话人检测方法 ==========

    def detect_speaker_enhanced(self, line: str) -> Optional[str]:
        """增强的说话人检测 - 过滤录音转录信息"""
        # 首先过滤掉明显的时间标记等
        if self.is_speaker_time_mark(line):
            return None

        # 采访人模式 - 增强
        interviewer_patterns = [
            r'^[问Qq][：:]', r'^提问[：:]', r'^采访[：:]', r'^访谈[：:]',
            r'^主持人[：:]', r'^记者[：:]', r'^访员[：:]', r'^请问',
            r'^您觉得', r'^您认为', r'^你们', r'^公司', r'^团队',
            r'^Interviewer[：:]', r'^Host[：:]', r'^Reporter[：:]'
        ]

        # 受访人模式 - 增强
        respondent_patterns = [
            r'^[答Aa][：:]', r'^回答[：:]', r'^受访[：:]', r'^被访[：:]',
            r'^嘉宾[：:]', r'^专家[：:]', r'^我们', r'^我的', r'^我觉得',
            r'^我认为', r'^我们的', r'^负责', r'^管理', r'^开发',
            r'^Interviewee[：:]', r'^Guest[：:]', r'^Expert[：:]'
        ]

        # 检查采访人模式
        for pattern in interviewer_patterns:
            if re.search(pattern, line):
                return "interviewer"

        # 检查受访人模式
        for pattern in respondent_patterns:
            if re.search(pattern, line):
                return "respondent"

        # 基于内容判断
        if self.is_interviewer_line_enhanced(line):
            return "interviewer"
        elif self.is_respondent_line_enhanced(line):
            return "respondent"

        return None

    def is_interviewer_line_enhanced(self, line: str) -> bool:
        """判断是否是采访人说的话 - 增强版"""
        # 过滤掉短的时间标记等
        if len(line) < 10 and (re.match(r'^\d+:\d+', line) or re.match(r'^[a-zA-Z\u4e00-\u9fa5]+\d*$', line)):
            return False

        interviewer_indicators = [
            '请问', '想问', '了解', '采访', '提问', '访谈', '什么', '为什么', '如何', '怎样',
            '吗？', '呢？', '负责什么', '负责哪块', '收益如何', '感觉如何', '如何改进',
            '有什么困难', '什么挑战', '未来计划', '目标是什么', '能不能', '是否可以'
        ]

        # 包含疑问词的短句很可能是采访人
        if any(indicator in line for indicator in interviewer_indicators):
            return True

        # 以问号结尾的短句
        if line.endswith(('？', '?')) and len(line) < 50:
            return True

        return False

    def is_respondent_line_enhanced(self, line: str) -> bool:
        """判断是否是受访人说的话 - 增强版"""
        # 排除明显的采访人特征
        if self.is_interviewer_line_enhanced(line):
            return False

        # 过滤掉短的时间标记等
        if len(line) < 10 and (re.match(r'^\d+:\d+', line) or re.match(r'^[a-zA-Z\u4e00-\u9fa5]+\d*$', line)):
            return False

        respondent_indicators = [
            '我们', '我的', '我觉得', '我认为', '我们的', '团队', '工作', '项目',
            '负责', '管理', '开发', '设计', '测试', '经验', '感受', '收获',
            '成果', '效果', '改进', '优化', '提升', '解决', '处理', '应对'
        ]

        # 包含工作内容或个人感受的较长的句子
        content_indicators = any(indicator in line for indicator in respondent_indicators)

        # 长度判断：受访人的回答通常较长
        if len(line) > 25 and content_indicators:
            return True

        return len(line) > 35  # 较长的内容很可能是受访人

    # ========== 编码数据处理方法 ==========

    def merge_coding_data(self, standard_answers: Dict[str, Any], current_codes: Dict[str, Any]) -> Dict[str, Any]:
        """合并标准答案和当前编码数据"""
        try:
            # 深拷贝标准答案，避免修改原数据
            merged = copy.deepcopy(standard_answers)

            logger.info(f"开始合并编码数据: 标准答案有{len(standard_answers)}个三阶编码")

            for third_cat, second_cats in current_codes.items():
                # 清理三阶编码名称（移除编号前缀）
                clean_third_cat = self.clean_category_name(third_cat)

                if clean_third_cat not in merged:
                    merged[clean_third_cat] = {}
                    logger.info(f"新增三阶编码: {clean_third_cat}")

                for second_cat, first_contents in second_cats.items():
                    # 清理二阶编码名称（移除编号前缀）
                    clean_second_cat = self.clean_category_name(second_cat)

                    if clean_second_cat not in merged[clean_third_cat]:
                        merged[clean_third_cat][clean_second_cat] = []
                        logger.info(f"新增二阶编码: {clean_third_cat} -> {clean_second_cat}")

                    # 处理一阶编码内容
                    existing_first_contents = set(merged[clean_third_cat][clean_second_cat])

                    for content_data in first_contents:
                        if isinstance(content_data, dict):
                            # 提取一阶编码内容（清理编号前缀）
                            if "numbered_content" in content_data:
                                first_content = self.clean_first_level_content(content_data["numbered_content"])
                            elif "content" in content_data:
                                first_content = self.clean_first_level_content(content_data["content"])
                            else:
                                first_content = str(content_data)
                        else:
                            first_content = self.clean_first_level_content(str(content_data))

                        # 只有在新内容时才添加
                        if first_content and first_content not in existing_first_contents:
                            merged[clean_third_cat][clean_second_cat].append(first_content)
                            existing_first_contents.add(first_content)
                            logger.debug(f"新增一阶编码: {clean_third_cat} -> {clean_second_cat} -> {first_content[:30]}...")

            # 统计合并结果
            total_third = len(merged)
            total_second = sum(len(categories) for categories in merged.values())
            total_first = sum(
                len(first_contents)
                for categories in merged.values()
                for first_contents in categories.values()
            )

            logger.info(f"合并完成: {total_third}三阶, {total_second}二阶, {total_first}一阶")
            return merged

        except Exception as e:
            logger.error(f"合并编码数据失败: {e}")
            return standard_answers

    def clean_category_name(self, category_name: str) -> str:
        """清理类别名称，移除编号前缀"""
        cleaned = re.sub(r'^[A-Z]\d*\s*', '', category_name.strip())
        return cleaned

    def clean_first_level_content(self, content: str) -> str:
        """清理一阶编码内容，移除编号前缀"""
        cleaned = re.sub(r'^[A-Z]\d+\s*', '', content.strip())
        return cleaned

    # ========== 导出方法 ==========

    def export_structured_codes_to_table(self, file_path: str, structured_codes: Dict[str, Any]) -> bool:
        """导出编码结构为表格格式"""
        try:
            table_data = []

            for third_category, second_categories in structured_codes.items():
                for second_category, first_contents in second_categories.items():
                    for content_data in first_contents:
                        # 提取一阶编码内容
                        if isinstance(content_data, dict):
                            first_level_content = content_data.get('content', '')
                            # 如果是简化后的内容，去掉编号前缀
                            first_level_content = re.sub(r'^[A-Z]\d+\s*', '', first_level_content).strip()
                        else:
                            first_level_content = str(content_data)

                        # 清理类别名称
                        clean_third = self.clean_category_name(third_category)
                        clean_second = self.clean_category_name(second_category)

                        # 添加到表格数据
                        table_data.append({
                            "三阶编码": clean_third,
                            "二阶编码": clean_second,
                            "一阶编码": first_level_content
                        })

            # 创建DataFrame
            df = pd.DataFrame(table_data)

            # 根据文件扩展名选择导出格式
            if file_path.endswith('.xlsx'):
                df.to_excel(file_path, index=False, engine='openpyxl')
            elif file_path.endswith('.csv'):
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            else:
                # 默认导出为Excel
                file_path = file_path.replace('.json', '.xlsx')
                df.to_excel(file_path, index=False, engine='openpyxl')

            logger.info(f"表格格式编码已导出: {len(table_data)} 行数据")
            return True

        except Exception as e:
            logger.error(f"导出表格格式失败: {e}")
            return False

    def export_for_training_format(self, file_path: str, structured_codes: Dict[str, Any]) -> bool:
        """导出为训练数据格式"""
        try:
            # 构建与标准答案相同的结构
            training_format = {}

            for third_category, second_categories in structured_codes.items():
                clean_third = self.clean_category_name(third_category)
                training_format[clean_third] = {}

                for second_category, first_contents in second_categories.items():
                    clean_second = self.clean_category_name(second_category)

                    # 提取所有一阶编码内容
                    first_level_contents = []
                    for content_data in first_contents:
                        if isinstance(content_data, dict):
                            content = content_data.get('content', '')
                            # 去掉编号前缀，只保留内容
                            content = re.sub(r'^[A-Z]\d+\s*', '', content).strip()
                            first_level_contents.append(content)
                        else:
                            first_level_contents.append(str(content_data))

                    training_format[clean_third][clean_second] = first_level_contents

            # 导出为JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(training_format, f, ensure_ascii=False, indent=2)

            logger.info(f"训练格式编码已导出: {file_path}")
            return True

        except Exception as e:
            logger.error(f"导出训练格式失败: {e}")
            return False

    def get_timestamp(self) -> str:
        """获取时间戳"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 测试代码
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 创建处理器
    processor = DataProcessor()

    print("数据处理器已初始化")
    print("=" * 50)

    # 测试句子编号功能
    test_text = "我们团队采用民主式管理方式。强调团队合作和沟通。定期召开项目会议。"

    print("测试文本:")
    print(test_text)
    print("=" * 50)

    # 使用编号管理器
    numbered_text, mapping = processor.numbering_manager.number_text(test_text, "测试文件")

    print("编号后的文本:")
    print(numbered_text)
    print("=" * 50)

    print("编号映射:")
    for number, sentence in mapping.items():
        print(f"  {number}: {sentence}")

    # 测试查找功能
    print("=" * 50)
    print("查找测试:")
    print(f"编号1的句子: {processor.numbering_manager.get_sentence_by_number(1)}")
    print(f"句子'我们团队采用民主式管理方式'的编号: {processor.numbering_manager.get_number_by_sentence('我们团队采用民主式管理方式')}")
