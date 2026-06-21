import re
import logging
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)


class TextNumberingManager:
    """文本编号管理器 - 为文本中的句子添加编号"""

    def __init__(self):
        self.sentence_counter = 0
        self._speaker_extractor = None
        self._init_speaker_extractor()
        self.reset()

    def _init_speaker_extractor(self):
        """尝试加载 SpeakerRoleExtractor 用于无标签文本的内容分析"""
        try:
            from speaker_role_extractor import SpeakerRoleExtractor
            self._speaker_extractor = SpeakerRoleExtractor(use_qa_classifier=False)
            logger.info("TextNumberingManager 已加载 SpeakerRoleExtractor（内容分析）")
        except ImportError:
            self._speaker_extractor = None
            logger.warning("TextNumberingManager: SpeakerRoleExtractor 不可用，回退到纯标签匹配")

    def reset(self):
        """重置计数器"""
        self.sentence_counter = 0

    def number_text(self, text: str, filename: str = "") -> Tuple[str, Dict[int, str]]:
        """
        为文本中的句子添加编号

        Args:
            text: 输入文本
            filename: 文件名（用于日志记录）

        Returns:
            tuple: (编号后的文本, 编号映射字典)
        """
        if not text:
            return "", {}

        # 按说话人分块分割文本（优先），无说话人标签时回退到传统按句号分句
        chunks = self.split_by_speaker_chunks(text)

        numbered_text = ""
        number_mapping = {}

        for chunk in chunks:
            sentence = chunk['text']
            role = chunk.get('role', 'unknown')

            if not sentence.strip():  # 忽略空句子
                continue

            # 采访者语句：展示但不编号，不加入 number_mapping
            if role == 'interviewer':
                if numbered_text:
                    numbered_text += "\n"
                numbered_text += self._strip_all_speaker_prefixes(sentence)
                continue

            # 无标签文本：用 SpeakerRoleExtractor 做内容分析
            if role == 'unknown' and self._speaker_extractor is not None:
                content_role = self._detect_role_by_content(sentence)
                if content_role == 'interviewer':
                    if numbered_text:
                        numbered_text += "\n"
                    numbered_text += self._strip_all_speaker_prefixes(sentence)
                    continue

            # 受访者或未知角色：正常编号
            self.sentence_counter += 1
            clean_sentence = self._strip_all_speaker_prefixes(sentence)
            numbered_sentence = f"{clean_sentence} [{self.sentence_counter}]"

            if numbered_text:
                numbered_text += "\n"
            numbered_text += numbered_sentence

            # 记录编号与原文的映射关系
            number_mapping[self.sentence_counter] = clean_sentence.strip()

        logger.info(f"为文件 {filename} 中的 {len(chunks)} 个分块进行了编号（跳过 {sum(1 for c in chunks if c.get('role') == 'interviewer')} 个采访者块）")

        return numbered_text, number_mapping

    @staticmethod
    def _strip_speaker_prefix(sentence: str) -> str:
        """移除行首说话人标记（A:/B:/问:/答:/受访者：等），仅影响展示与映射，不改变原始文本缓存。"""
        if sentence is None:
            return ""
        s = str(sentence).strip()
        s = re.sub(
            r'^\s*(?:'
            r'[QqAaBb]|'
            r'问|答|回答|提问|'
            r'采访者|访谈者|提问者|主持人|记者|面试官|'
            r'受访者|被访者|受访人|受访对象|'
            r'Interviewer|Interviewee|Respondent|Host|Reporter|'
            r'Speaker\s*\d+|说话人\s*\d+'
            r')\s*[:\uFF1A]\s*',
            '',
            s
        )
        return s.strip()

    @staticmethod
    def _strip_all_speaker_prefixes(text: str) -> str:
        """移除文本中所有的说话人标记（不仅是行首，合并块中可能有多处）"""
        if text is None:
            return ""
        s = str(text)
        s = re.sub(
            r'(?:^|\n)\s*(?:'
            r'[QqAaBb]|'
            r'问|答|回答|提问|'
            r'采访者|访谈者|提问者|主持人|记者|面试官|'
            r'受访者|被访者|受访人|受访对象|'
            r'Interviewer|Interviewee|Respondent|Host|Reporter|'
            r'Speaker\s*\d+|说话人\s*\d+'
            r')\s*[:\uFF1A]\s*',
            '\n',
            s,
            flags=re.MULTILINE
        )
        return s.strip()

    def _detect_role_by_content(self, text: str) -> str:
        """对无标签文本做内容分析，判断是否为采访者语句

        使用 SpeakerRoleExtractor 的双向评分机制：
        - 问句特征强（疑问词、问号、短句等）→ 'interviewer'
        - 陈述特征强（第一人称、长句、工作关键词等）→ 'interviewee'
        - 无法判断 → 'unknown'

        Returns:
            'interviewer' | 'interviewee' | 'unknown'
        """
        if not self._speaker_extractor:
            return 'unknown'

        try:
            # 清理文本后分析
            clean_text = self._strip_all_speaker_prefixes(text).strip()
            if not clean_text or len(clean_text) < 4:
                return 'unknown'
            segment = {
                'text': clean_text,
                'speaker_label': None,
                'method': 'content_analysis',
                'inferred_role': None,
            }
            role, confidence = self._speaker_extractor._identify_role(segment)
            logger.debug(
                f"内容分析: role={role}, confidence={confidence:.2f}, "
                f"text={text[:50]}..."
            )
            return role
        except Exception as e:
            logger.warning(f"内容分析失败: {e}，回退到 unknown")
            return 'unknown'

    def _fallback_segment_by_question(self, text: str) -> List[Dict[str, str]]:
        """无说话人标签时的智能分段回退策略

        优先使用 SpeakerRoleExtractor._smart_segment_qa_mixed 按问号分段，
        问号前的文本标记为 interviewer，其余为 unknown（由下游内容分析决定）。
        若提取器不可用，整段文本作为一个 unknown chunk，不再按句号拆碎。

        Returns:
            [{'text': '...', 'role': 'interviewer'|'unknown'}, ...]
        """
        if not text or not text.strip():
            return []

        # 尝试用 SpeakerRoleExtractor 按问号分段（仅用于分块，不信任其角色推断）
        if self._speaker_extractor is not None:
            try:
                segments = self._speaker_extractor._smart_segment_qa_mixed(text)
                result = []
                for seg in segments:
                    # 不信任 inferred_role，统一标记为 unknown，由内容分析层判定
                    result.append({'text': seg['text'], 'role': 'unknown'})
                if result:
                    return result
            except Exception as e:
                logger.warning(f"智能分段失败: {e}，回退到整段文本")

        # 最终回退：整段文本作为一个块（不再按句号拆碎）
        return [{'text': text.strip(), 'role': 'unknown'}]

    def split_into_sentences(self, text: str) -> List[str]:
        """将文本按句子分割（传统按句号分句方法，保留兼容）"""
        # 使用中文句号、问号、感叹号和换行符分割句子
        # 保留分隔符
        sentences = re.split(r'([。！？!? \n\r])', text)

        result = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]  # 添加标点符号

            # 清理句子
            sentence = sentence.strip()
            if sentence:
                result.append(sentence)

        # 处理最后一部分（如果没有标点符号结尾）
        if len(sentences) % 2 == 1:
            last_part = sentences[-1].strip()
            if last_part:
                # 添加到最后一句
                if result:
                    result[-1] += last_part
                else:
                    result.append(last_part)

        return result

    def split_by_speaker_chunks(self, text: str) -> List[Dict[str, str]]:
        """按说话人分块分割文本（不按句号分句）
        
        规则：
        1. 以说话人标签为边界分割文本（每个说话人标签到下一个标签为一整块）
        2. 如果同一说话人标签连续出现（如 B:... B:...），则合并为一块
        3. 每个chunk携带角色标签（'interviewer' / 'respondent' / 'unknown'）
           interviewer的chunk在编号时会被跳过
        
        返回: [{'text': '文本内容', 'role': 'respondent'}, ...]
        
        说话人标签匹配：
        - 中文标签：问/答/提问/回答/采访者/受访者/访谈者/主持人/记者/嘉宾/专家 等 + ：或:
        - 字母标签：A:/a:/B:/b:/Q:/q: 等
        - 编号标签：说话人1:/说话人2: 等
        """
        if not text or not text.strip():
            return []

        # 统一的说话人标签正则（中英文、全半角冒号）
        speaker_prefix = (
            r'(?:'
            r'[ABQabq][：:]|'
            r'[问答][：:]|'
            r'提问[：:]|回答[：:]|采访[：:]|访谈[：:]|受访[：:]|被访[：:]|'
            r'采访者[：:]|受访者[：:]|访谈者[：:]|提问者[：:]|'
            r'主持人[：:]|记者[：:]|访员[：:]|嘉宾[：:]|专家[：:]|'
            r'面试官[：:]|被访者[：:]|受访人[：:]|受访对象[：:]|'
            r'说话人\s*\d+[：:]|Speaker\s*\d+[：:]|'
            r'Interviewer[：:]|Interviewee[：:]|Respondent[：:]|Host[：:]|Reporter[：:]|'
            r'[\u4e00-\u9fa5]+[：:](?=\s*\S)'
            r')'
        )

        # 按说话人标签位置分割（保留标签本身）
        parts = re.split(f'({speaker_prefix})', text)

        if len(parts) <= 1:
            # 没找到任何说话人标签，用问号智能分段（不再按句号拆碎）
            return self._fallback_segment_by_question(text)

        # 解析为 (标签, 内容) 对
        raw_chunks = []
        i = 0
        while i < len(parts):
            part = parts[i].strip()
            if not part:
                i += 1
                continue

            is_label = bool(re.match(f'^{speaker_prefix}$', part))
            if is_label:
                # 标签 + 下一个非标签内容
                label = part
                content = ''
                if i + 1 < len(parts):
                    content = parts[i + 1].strip()
                raw_chunks.append({
                    'label': label,
                    'content': content,
                })
                i += 2  # 跳过标签和内容
            else:
                # 纯内容（无标签开头），合并到上一个chunk或独立
                raw_chunks.append({
                    'label': '',
                    'content': part,
                })
                i += 1

        # 第二步：合并同一说话人的连续chunk
        if not raw_chunks:
            return self._fallback_segment_by_question(text)

        # 受访者角色集 和 采访者角色集
        respondent_role_set = {'受访者', '被访者', '受访人', '受访对象', '嘉宾', '专家', 'B', 'b', '答', '回答', 'Interviewee', 'Respondent'}
        interviewer_role_set = {'采访者', '访谈者', '提问者', '主持人', '记者', '访员', '面试官', 'A', 'a', 'Q', 'q', '问', '提问', '采访', '访谈', 'Interviewer', 'Host', 'Reporter'}

        def get_role_key(label: str) -> str:
            """获取角色分类键：respondent / interviewer / other"""
            name = re.sub(r'[：:]$', '', label).strip()
            if name in respondent_role_set:
                return 'respondent'
            if name in interviewer_role_set:
                return 'interviewer'
            return name  # 其他保持原名

        def get_role_label(name: str) -> str:
            """获取角色的标准化标签：interviewer / respondent / unknown"""
            if name in interviewer_role_set:
                return 'interviewer'
            if name in respondent_role_set:
                return 'respondent'
            return 'unknown'

        merged = []
        for chunk in raw_chunks:
            lbl = chunk['label']
            content = chunk['content']
            role_key = get_role_key(lbl) if lbl else ('empty_label' if not content else 'no_label')

            if not merged:
                merged.append(chunk)
                continue

            prev_chunk = merged[-1]
            prev_role = get_role_key(prev_chunk['label']) if prev_chunk['label'] else ('empty_label' if not prev_chunk['content'] else 'no_label')

            # 同一角色连续出现 → 合并
            if role_key == prev_role and role_key not in ('no_label', 'other'):
                prev_chunk['content'] = prev_chunk['content'] + '\n' + (lbl + ' ' if lbl else '') + content
            else:
                merged.append(chunk)

        # 第三步：组装为 dict 列表（携带角色标签）
        result = []
        for chunk in merged:
            lbl = chunk['label']
            content = chunk['content']
            role = get_role_label(lbl) if lbl else 'unknown'
            if lbl and content:
                result.append({'text': lbl + ' ' + content, 'role': role})
            elif content:
                result.append({'text': content, 'role': role})

        return result if result else self._fallback_segment_by_question(text)

    def _merge_consecutive_speaker_chunks(self, chunks: List[str]) -> List[str]:
        """合并同一说话人的连续chunk（基于chunk开头提取说话人）"""
        if not chunks:
            return chunks

        # 受访者角色集 和 采访者角色集
        respondent_set = {'受访者', '被访者', '受访人', '受访对象', '嘉宾', '专家', 'B', 'b', '答', '回答', 'Interviewee', 'Respondent'}
        interviewer_set = {'采访者', '访谈者', '提问者', '主持人', '记者', '访员', '面试官', 'A', 'a', 'Q', 'q', '问', '提问', '采访', '访谈', 'Interviewer', 'Host', 'Reporter'}

        def get_speaker_role(chunk_text: str):
            """从chunk文本中提取说话人角色"""
            patterns = [
                (r'^([ABQabq])[：:]', lambda m: 'interviewer' if m.group(1) in ('A', 'a', 'Q', 'q') else 'respondent'),
                (r'^([问答])[：:]', lambda m: 'interviewer'),
                (r'^(提问|采访|访谈)[：:]', lambda m: 'interviewer'),
                (r'^(回答|受访|被访)[：:]', lambda m: 'respondent'),
                (r'^(采访者|访谈者|提问者|主持人|记者|访员|面试官)[：:]', lambda m: 'interviewer'),
                (r'^(受访者|被访者|受访人|受访对象|嘉宾|专家)[：:]', lambda m: 'respondent'),
                (r'^(说话人\s*\d+)[：:]', lambda m: m.group(1)),
                (r'^(Interviewer|Host|Reporter)[：:]', lambda m: 'interviewer'),
                (r'^(Interviewee|Respondent)[：:]', lambda m: 'respondent'),
            ]
            for pattern, role_func in patterns:
                m = re.match(pattern, chunk_text)
                if m:
                    return role_func(m)
            return chunk_text[:5]

        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_role = get_speaker_role(result[-1])
            curr_role = get_speaker_role(chunks[i])

            is_same = False
            if prev_role == curr_role:
                is_same = True
            elif prev_role in respondent_set and curr_role in respondent_set:
                is_same = True
            elif prev_role in interviewer_set and curr_role in interviewer_set:
                is_same = True

            if is_same:
                result[-1] = result[-1] + '\n' + chunks[i]
            else:
                result.append(chunks[i])

        return result

    def _extract_speaker_from_chunk(self, chunk: str) -> str:
        """从chunk中提取说话人标识"""
        # 尝试匹配各种说话人标签
        patterns = [
            r'^([ABQabq])[：:]',           # A:/B:/Q: 等
            r'^([问答])[：:]',              # 问:/答:
            r'^(提问|回答|采访|访谈|受访|被访)[：:]',
            r'^(采访者|受访者|访谈者|提问者|主持人|记者|访员|嘉宾|专家|面试官|被访者|受访人|受访对象)[：:]',
            r'^(说话人\s*\d+|Speaker\s*\d+)[：:]',
            r'^(Interviewer|Interviewee|Respondent|Host|Reporter)[：:]',
            r'^([\u4e00-\u9fa5]+)[：:]',     # 任意中文+冒号
        ]
        for pattern in patterns:
            m = re.match(pattern, chunk)
            if m:
                return m.group(1)
        return chunk[:5]  # 取前5个字符作为标识

    def _merge_consecutive_speaker_chunks(self, chunks: List[str]) -> List[str]:
        """合并同一说话人的连续chunk"""
        if not chunks:
            return chunks

        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_speaker = self._extract_speaker_from_chunk(result[-1])
            curr_speaker = self._extract_speaker_from_chunk(chunks[i])

            # 判断是否同一说话人
            is_same = False
            if prev_speaker == curr_speaker:
                is_same = True
            elif prev_speaker in ('受访者', '被访者', '受访人', '受访对象', '嘉宾', '专家', 'B', 'b', '答', '回答', 'Interviewee', 'Respondent') and \
                 curr_speaker in ('受访者', '被访者', '受访人', '受访对象', '嘉宾', '专家', 'B', 'b', '答', '回答', 'Interviewee', 'Respondent'):
                is_same = True
            elif prev_speaker in ('采访者', '访谈者', '提问者', '主持人', '记者', '访员', '面试官', 'A', 'a', 'Q', 'q', '问', '提问', '采访', '访谈', 'Interviewer', 'Host', 'Reporter') and \
                 curr_speaker in ('采访者', '访谈者', '提问者', '主持人', '记者', '访员', '面试官', 'A', 'a', 'Q', 'q', '问', '提问', '采访', '访谈', 'Interviewer', 'Host', 'Reporter'):
                is_same = True

            if is_same:
                # 同一说话人 → 合并
                result[-1] = result[-1] + '\n' + chunks[i]
            else:
                result.append(chunks[i])

        return result

    def get_current_number(self) -> int:
        """获取当前句子编号"""
        return self.sentence_counter

    def set_start_number(self, start_num: int):
        """设置起始编号"""
        self.sentence_counter = start_num - 1  # 因为每次都会+1