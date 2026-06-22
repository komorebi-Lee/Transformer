"""
说话人角色识别与受访者语句提取模块

用于从访谈文本中自动识别并提取受访者的语句，过滤访谈员的问句。
支持多种文本格式：明确标注、说话人编号、无标注混合文本。
可选：使用轻量级 QA 分类模型辅助识别。
"""

import re
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# 尝试导入 QA 分类器
try:
    from qa_classifier import QAClassifier
    QA_CLASSIFIER_AVAILABLE = True
except ImportError:
    QA_CLASSIFIER_AVAILABLE = False
    logger.info("qa_classifier 不可用，将使用纯规则模式")


class SpeakerRoleExtractor:
    """说话人角色识别器"""
    
    def __init__(self, use_qa_classifier: bool = False, qa_model_path: str = None):
        """
        初始化

        Args:
            use_qa_classifier: 是否使用 QA 分类器辅助识别
            qa_model_path: QA 分类器模型路径（None=规则模式）
        """
        self.use_qa_classifier = use_qa_classifier
        self.qa_model_path = qa_model_path
        self._qa_classifier = None
        self._qa_tried_load = False

        # 采样式说话人画像参数
        self.profile_sample_blocks = 3   # 每个说话人最多采样块数
        self.profile_block_size = 10     # 交互窗口大小（连续轮次数）
        self.interviewer_threshold = 0.5 # 多数块超此分→采访者

        # 访谈员关键词（问句特征）- 扩充版
        self.interviewer_patterns = [
            # 明确标记
            r'^[问Qq][：:]',
            r'^[Aa][：:]',
            r'^提问[：:]',
            r'^采访[：:]',
            r'^访谈[：:]',
            r'^主持人[：:]',
            r'^记者[：:]',
            r'^访员[：:]',
            r'^Interviewer[：:]',
            r'^Host[：:]',
            r'^Reporter[：:]',
            
            # 疑问词开头
            r'^请问',
            r'^想问',
            r'^了解',
            r'^您觉得',
            r'^您认为',
            r'^你的',
            r'^您是',
            r'^您了解',
            r'^那您',
            r'^从您',
            r'^你们',
            r'^公司',
            r'^团队',
            
            # 疑问句特征
            r'[？?]$',
            r'吗[？?]?$',
            r'呢[？?]?$',
            r'如何',
            r'怎么',
            r'怎样',
            r'为什么',
            r'什么',
            r'哪',
            r'能不能',
            r'是否可以',
            
            # 访谈常见问法
            r'负责什么',
            r'负责哪块',
            r'收益如何',
            r'感觉如何',
            r'如何改进',
            r'有什么困难',
            r'什么挑战',
            r'未来计划',
            r'目标是什么',

            # 采访者结束语/客套话 — 称呼对方的感谢/道歉必为采访者
            r'感谢您',
            r'谢谢您',
            r'感谢你的',
            r'谢谢你的',
            r'麻烦您',
            r'辛苦您',
            r'打扰您',
            r'抱歉打扰',
            r'不好意思',
        ]
        
        # 受访者关键词（陈述特征）- 扩充版
        self.interviewee_patterns = [
            # 明确标记
            r'^[答Aa][：:]',
            r'^[Bb][：:]',
            r'^回答[：:]',
            r'^受访[：:]',
            r'^被访[：:]',
            r'^嘉宾[：:]',
            r'^专家[：:]',
            r'^Interviewee[：:]',
            r'^Guest[：:]',
            r'^Expert[：:]',
            
            # 第一人称开头
            r'^(是的|对|嗯|哦|好的|没错|确实)',
            r'我(觉得|认为|感觉|看|想|做|是|在|有|会|能)',
            r'我们(这|在|有|做|能|会|觉得|的|来)',
            r'我的',
            
            # 工作内容相关
            r'(很多|有些|一些|大部分)人',
            r'(肯定|应该|可能|也许|大概)',
            r'团队',
            r'工作',
            r'项目',
            r'负责',
            r'管理',
            r'开发',
            r'设计',
            r'测试',
            r'经验',
            r'感受',
            r'收获',
            r'成果',
            r'效果',
            r'改进',
            r'优化',
            r'提升',
            r'解决',
            r'处理',
            r'应对',
        ]
    
    def extract_interviewee_sentences(
        self,
        text: str,
        return_metadata: bool = False
    ) -> List[str] | List[Dict[str, any]]:
        """
        从文本中提取受访者语句
        
        Args:
            text: 原始访谈文本
            return_metadata: 是否返回元数据（说话人标签、置信度等）
            
        Returns:
            受访者语句列表，或包含元数据的字典列表
        """
        # 文本预处理
        text = self._preprocess_text(text)

        # 分句并识别说话人
        segments = self._segment_by_speaker(text)

        # 采样式说话人画像：文件级角色判定
        profiles = self._build_speaker_profiles(segments)

        # 识别非采访者语句（排除采访者，保留受访者+同伴+顾客等所有其他人）
        interviewee_segments = []
        for i, seg in enumerate(segments):
            role, confidence = self._identify_role(seg, profiles, segments, i)
            if role != 'interviewer':
                # 清理说话人标签
                clean_text = self._remove_speaker_label(seg['text'])
                if return_metadata:
                    interviewee_segments.append({
                        'text': clean_text,
                        'speaker_label': seg.get('speaker_label'),
                        'confidence': confidence,
                        'method': seg.get('method', 'rule'),
                    })
                else:
                    interviewee_segments.append(clean_text)
        
        return interviewee_segments

    def extract_all_segments(self, text: str, clean: bool = True) -> List[Dict[str, any]]:
        """返回所有说话人分段（含采访者+受访者），保留角色标签用于边界保留。

        Args:
            text: 原始文本
            clean: True 时剥离说话人标签，False 时保留标签在 text 中

        Returns:
            [{'text': ..., 'speaker_label': ..., 'role': ..., 'confidence': ..., 'method': ...}, ...]
        """
        text = self._preprocess_text(text)
        segments = self._segment_by_speaker(text)
        profiles = self._build_speaker_profiles(segments)

        result = []
        for i, seg in enumerate(segments):
            role, confidence = self._identify_role(seg, profiles, segments, i)
            seg_text = seg['text']
            speaker_label = seg.get('speaker_label', '')
            if not clean and speaker_label:
                # 剥离原始标签（无冒号），再拼回标准格式的标签
                seg_text = speaker_label + '：' + self._remove_speaker_label(seg_text)
            else:
                seg_text = self._remove_speaker_label(seg_text)
            result.append({
                'text': seg_text,
                'speaker_label': speaker_label,
                'role': role,
                'confidence': confidence,
                'method': seg.get('method', 'rule'),
            })
        return result

    def _remove_speaker_label(self, text: str) -> str:
        """移除文本开头的说话人标签"""
        text = re.sub(
            r'^(?:受访者|采访者|访谈员|说话人\s*\d+|里弄管家\s*\d+|游客\s*\d+'
            r'|老师\s*\d*|主持人|记者)\s*[:：]?\s*', '', text)
        text = re.sub(r'^[AaBb][：:]\s*', '', text)
        text = re.sub(r'^[问答Qq][：:]\s*', '', text)
        return text.strip()
    
    def _preprocess_text(self, text: str) -> str:
        """文本预处理 - 增强版，处理时间戳和标注残留"""
        # 统一冒号
        text = text.replace('：', ':')
        
        # 清理时间戳 (00:32 格式)
        text = re.sub(r'\d{2}:\d{2}', '', text)
        
        # 清理标注残留（"问题"、"回答"、"标签对好"等）
        text = re.sub(r'^(问题|回答|标签对好)\s*', '', text, flags=re.MULTILINE)
        
        # 统一换行
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 清理多余空白
        text = re.sub(r'\n\s*\n', '\n', text)
        text = re.sub(r'  +', ' ', text)
        
        return text.strip()

    def _segment_by_ab_labels(self, text: str) -> Optional[List[Dict[str, str]]]:
        """
        按 A:/B: 行级标签分段，无标签续行继承上一说话人。
        A=采访者，B=受访者（本项目仅编码受访者）。
        """
        lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        ab_interviewer_re = re.compile(r'^[Aa][：:]\s*')
        ab_interviewee_re = re.compile(r'^[Bb][：:]\s*')

        has_ab = any(
            ab_interviewer_re.match(line.strip()) or ab_interviewee_re.match(line.strip())
            for line in lines if line.strip()
        )
        if not has_ab:
            return None

        segments = []
        current_speaker_label = None
        current_text = []

        def _flush():
            nonlocal current_speaker_label, current_text
            if current_speaker_label and current_text:
                segments.append({
                    'text': '\n'.join(current_text),
                    'speaker_label': current_speaker_label,
                    'method': 'ab_explicit',
                })
            current_text = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if ab_interviewer_re.match(line):
                _flush()
                current_speaker_label = '采访者'
                current_text = [line]
            elif ab_interviewee_re.match(line):
                _flush()
                current_speaker_label = '受访者'
                current_text = [line]
            elif current_speaker_label:
                current_text.append(line)

        _flush()
        return segments if segments else None

    def _segment_by_speaker(self, text: str) -> List[Dict[str, str]]:
        """
        按说话人分句 - 增强版，处理问答杂糅
        
        Returns:
            [{'text': '...', 'speaker_label': '受访者', 'method': 'explicit'}, ...]
        """
        # 策略0: A:/B: 行级标签（访谈稿最常见，续行继承说话人）
        ab_segments = self._segment_by_ab_labels(text)
        if ab_segments:
            return ab_segments

        segments = []
        
        # 策略1: 明确标注（受访者:、采访者:、说话人X:、里弄管家X:等）
        explicit_pattern = r'(受访者|采访者|访谈员|说话人\s*\d+|里弄管家\s*\d+|游客\s*\d+|老师\s*\d*|主持人|记者)\s*[:：]\s*'
        parts = re.split(f'({explicit_pattern})', text)
        
        if len(parts) > 1:
            # 有明确标注
            current_speaker = None
            current_text = []
            
            for i, part in enumerate(parts):
                if not part.strip():
                    continue
                
                # 检查是否是说话人标签
                if re.match(explicit_pattern, part):
                    # 保存上一个说话人的内容
                    if current_speaker and current_text:
                        segments.append({
                            'text': ''.join(current_text).strip(),
                            'speaker_label': current_speaker,
                            'method': 'explicit'
                        })
                    current_speaker = part.strip().rstrip(':：')
                    current_text = []
                elif not re.match(explicit_pattern, part.strip()):
                    # 只添加非标签内容
                    current_text.append(part)
            
            # 保存最后一个说话人的内容
            if current_speaker and current_text:
                segments.append({
                    'text': ''.join(current_text).strip(),
                    'speaker_label': current_speaker,
                    'method': 'explicit'
                })
        else:
            # 无明确标注，使用智能分段
            segments = self._smart_segment_qa_mixed(text)
        
        return segments
    
    def _smart_segment_qa_mixed(self, text: str) -> List[Dict[str, str]]:
        """
        智能分段问答杂糅文本
        
        策略：
        1. 按问号分割：['文本1', '？', '文本2', '？', '文本3']
        2. 遍历parts，遇到问号前的文本+问号 = 问句
        3. 问号后、下一个问号前的文本 = 回答
        """
        segments = []
        
        # 按问号分割，保留问号
        parts = re.split(r'([？?])', text)
        
        i = 0
        while i < len(parts):
            part = parts[i].strip()
            
            # 跳过空内容
            if not part:
                i += 1
                continue
            
            # 如果是问号，跳过（会在处理问句时一起处理）
            if part in ['？', '?']:
                i += 1
                continue
            
            # 检查下一个是否是问号
            next_is_question = (i + 1 < len(parts) and parts[i + 1] in ['？', '?'])
            
            if next_is_question:
                # 这是问句：文本 + 问号
                question = part + parts[i + 1]
                segments.append({
                    'text': question,
                    'speaker_label': None,
                    'method': 'qa_pattern',
                    'inferred_role': 'interviewer'
                })
                i += 2  # 跳过文本和问号
            else:
                # 非问句片段：不默认归为受访者（可能是采访者续行或杂糅文本）
                if len(part) >= 5:
                    segments.append({
                        'text': part,
                        'speaker_label': None,
                        'method': 'qa_pattern',
                    })
                i += 1
        
        return segments

    def _build_speaker_profiles(self, segments: List[Dict[str, str]]) -> Dict[str, str]:
        """
        采样式说话人画像：随机抽取3个交互窗口（每个窗口10个连续轮次），
        窗口内按说话人聚合文本打分，多数投票确定文件级角色。

        Returns:
            {speaker_label: 'interviewer' | 'non-interviewer'}
        """
        import random

        n = len(segments)
        window_size = self.profile_block_size  # 每个窗口包含的连续轮次数
        n_sample = min(self.profile_sample_blocks, max(1, n - window_size + 1))

        if n_sample == 0 or n == 0:
            return {}

        # 1. 收集所有需要判定的说话人
        speaker_labels = set()
        for seg in segments:
            method = seg.get('method', '')
            if method == 'ab_explicit':
                continue  # A:/B: 标签已确定角色
            if seg.get('inferred_role') is not None:
                continue  # QA pattern 已有推断角色
            sp = seg.get('speaker_label')
            if sp:
                speaker_labels.add(sp)

        if not speaker_labels:
            return {}

        # 2. 随机抽取3个交互窗口
        max_start = max(0, n - window_size)
        starts = random.sample(range(max_start + 1), min(n_sample, max_start + 1))

        # 3. 每个窗口内，按说话人聚合文本，独立打分
        speaker_votes = {sp: {'total': 0, 'interviewer_votes': 0} for sp in speaker_labels}

        for start in starts:
            window_segs = segments[start:start + window_size]
            # 窗口内按说话人分组
            window_texts = {}
            for seg in window_segs:
                sp = seg.get('speaker_label')
                if not sp:
                    continue
                if sp not in window_texts:
                    window_texts[sp] = []
                window_texts[sp].append(seg['text'])

            # 逐说话人打分
            for sp in speaker_labels:
                texts = window_texts.get(sp, [])
                if not texts:
                    continue
                block_text = '\n'.join(texts)
                iv_score = self._calc_interviewer_score(block_text)
                ie_score = self._calc_interviewee_score(block_text)
                speaker_votes[sp]['total'] += 1
                if iv_score > self.interviewer_threshold and iv_score > ie_score:
                    speaker_votes[sp]['interviewer_votes'] += 1

        # 4. 多数投票
        profiles = {}
        for sp, votes in speaker_votes.items():
            if votes['total'] > 0 and votes['interviewer_votes'] > votes['total'] / 2:
                profiles[sp] = 'interviewer'
            else:
                profiles[sp] = 'non-interviewer'

        # 5. 结尾确认：最后5句中谁说了结束语，谁就是采访者（覆盖投票结果）
        closing_re = re.compile(
            r'(谢谢|感谢|非常感谢|太感谢|多谢).{0,15}'
            r'(配合|接受|参与|支持|访谈|采访|您|你|各位|大家)'
            r'|(耽误|打扰|麻烦|辛苦|劳烦).{0,5}(您|你)'
            r'|(访谈|采访|咱们).{0,10}(到此|到这里|就到这|先到这|结束|就到这儿)'
        )
        tail_segs = segments[-5:] if len(segments) >= 5 else segments
        for seg in tail_segs:
            if closing_re.search(seg.get('text', '')):
                closer = seg.get('speaker_label')
                if closer and closer in profiles:
                    profiles[closer] = 'interviewer'
                break  # 找到一句就够

        return profiles

    def _context_enhance_role(self, segment: Dict[str, str],
                              all_segments: List[Dict[str, str]],
                              seg_index: int) -> Tuple[str, float]:
        """
        上下文增强：取当前segment前后各1条拼接重新打分

        Returns:
            (role, confidence)
        """
        parts = []

        # 前一条（同 speaker_label）
        if seg_index > 0:
            prev_seg = all_segments[seg_index - 1]
            if prev_seg.get('speaker_label') == segment.get('speaker_label'):
                parts.append(prev_seg['text'])

        # 当前
        parts.append(segment['text'])

        # 后一条（同 speaker_label）
        if seg_index < len(all_segments) - 1:
            next_seg = all_segments[seg_index + 1]
            if next_seg.get('speaker_label') == segment.get('speaker_label'):
                parts.append(next_seg['text'])

        context_text = '\n'.join(parts)
        iv_score = self._calc_interviewer_score(context_text)
        ie_score = self._calc_interviewee_score(context_text)

        if iv_score > ie_score:
            return 'interviewer', iv_score
        else:
            return 'interviewee', ie_score

    def _split_sentences(self, text: str) -> List[str]:
        """分句（保留语义完整性）- 增强版，处理问答杂糅"""
        sentences = []
        
        # 策略1: 按问号分割（问答杂糅的关键标志）
        # "那您觉得...？那倒没有..." → ["那您觉得...？", "那倒没有..."]
        parts = re.split(r'([？?])', text)
        
        current = []
        for i, part in enumerate(parts):
            if not part.strip():
                continue
            
            current.append(part)
            
            # 遇到问号，结束当前句子
            if part in ['？', '?']:
                sent = ''.join(current).strip()
                if sent and len(sent) >= 5:
                    sentences.append(sent)
                current = []
        
        # 处理剩余部分（没有问号的陈述句）
        if current:
            remaining = ''.join(current).strip()
            if remaining:
                # 按句号、感叹号分割
                sub_parts = re.split(r'([。！\n])', remaining)
                sub_current = []
                for part in sub_parts:
                    if not part.strip():
                        continue
                    sub_current.append(part)
                    if part in ['。', '！', '\n']:
                        sent = ''.join(sub_current).strip()
                        if sent and len(sent) >= 5:
                            sentences.append(sent)
                        sub_current = []
                
                # 最后一句
                if sub_current:
                    sent = ''.join(sub_current).strip()
                    if sent and len(sent) >= 5:
                        sentences.append(sent)
        
        return sentences
    
    def _ensure_qa_classifier(self):
        """懒加载 QA 分类器"""
        if self._qa_tried_load:
            return
        self._qa_tried_load = True
        if not self.use_qa_classifier or not QA_CLASSIFIER_AVAILABLE:
            return
        try:
            self._qa_classifier = QAClassifier(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            if self.qa_model_path:
                self._qa_classifier.load_model(self.qa_model_path)
            else:
                self._qa_classifier.loaded = True  # 规则模式，跳过模型加载
                self._qa_classifier.model = None
            logger.info("QA 分类器已启用（规则+模型混合模式）")
        except Exception as e:
            logger.warning("QA 分类器初始化失败，回退到纯规则: %s", e)
            self._qa_classifier = None

    def _identify_role(self, segment: Dict[str, str],
                       profiles: Dict[str, str] = None,
                       all_segments: List[Dict[str, str]] = None,
                       seg_index: int = -1) -> Tuple[str, float]:
        """
        识别说话人角色 - 增强版，支持规则+QA模型混合判断

        Returns:
            (role, confidence)
            role: 'interviewer' | 'interviewee' | 'unknown'
            confidence: 0.0 ~ 1.0
        """
        text = segment['text']
        speaker_label = segment.get('speaker_label')
        method = segment.get('method')
        inferred_role = segment.get('inferred_role')  # 新增：问答模式推断的角色
        
        # 策略0: 问答模式推断（最高优先级）
        if inferred_role == 'interviewer':
            return 'interviewer', 0.95
        elif inferred_role == 'interviewee':
            return 'interviewee', 0.90
        
        # 策略1: 明确标注（含 A:/B: 分段）
        if method in ('explicit', 'ab_explicit') and speaker_label:
            if '受访' in speaker_label:
                return 'interviewee', 1.0
            elif '采访' in speaker_label or '访谈' in speaker_label:
                return 'interviewer', 1.0
            elif speaker_label.startswith('说话人'):
                # 说话人编号不可靠（不同文件中1和2可能角色互换），
                # 不根据编号假设角色，统一交给下面的内容特征打分判断
                pass

        # 策略2: 基于内容特征（仅强信号直接决策，弱信号交给画像）
        interviewer_score = self._calc_interviewer_score(text)
        interviewee_score = self._calc_interviewee_score(text)

        if interviewer_score > 0.7:
            return 'interviewer', interviewer_score
        if interviewee_score > 0.7:
            return 'interviewee', interviewee_score

        # 策略2.5: 内容不确定时，查采样式说话人画像映射表兜底
        if profiles and speaker_label and method != 'ab_explicit':
            profile_key = speaker_label if speaker_label else '__NONE__'
            if profile_key in profiles:
                role = profiles[profile_key]
                if role == 'interviewer':
                    return 'interviewer', 0.85
                else:
                    return 'interviewee', 0.85

        # ── 规则不确定 → QA 分类器 fallback ──
        self._ensure_qa_classifier()
        if self._qa_classifier is not None:
            try:
                qa_result = self._qa_classifier.classify(text)
                qa_label = qa_result.get('label', 'other')
                qa_conf = qa_result.get('confidence', 0.5)
                if qa_label == 'answer' and qa_conf >= 0.6:
                    return 'interviewee', qa_conf
                elif qa_label == 'question' and qa_conf >= 0.6:
                    return 'interviewer', qa_conf
                # qa_label == 'other' → 规则和模型都无法确定，交给启发式兜底
            except Exception:
                pass  # QA 失败，继续走启发式兜底

        # 策略4: 上下文增强（profiles 不确定时的 fallback）
        if all_segments is not None and seg_index >= 0:
            return self._context_enhance_role(segment, all_segments, seg_index)

        # 无法可靠判断时：
        # - 短文本+问句特征 → 采访者（避免误编码采访者)
        # - 短文本无特征 → unknown（真不确定）
        # - 长文本(≥50字) → 受访者（访谈中受访者说大部分内容，尤其润色后文件无标签）
        if len(text) < 30 and text.endswith(('？', '?', '吗', '呢')):
            return 'interviewer', 0.6
        if len(text) >= 50:
            _iv_score = self._calc_interviewer_score(text)
            if _iv_score > 0.5:
                return 'interviewer', _iv_score
            return 'interviewee', 0.55
        return 'unknown', 0.3
    
    def _calc_interviewer_score(self, text: str) -> float:
        """计算访谈员特征得分"""
        score = 0.0
        count = 0
        
        for pattern in self.interviewer_patterns:
            if re.search(pattern, text):
                count += 1
        
        # 归一化（每匹配2个模式得1分）
        if count > 0:
            score = min(1.0, count / 2.0)
        
        # 问号加权
        if text.endswith(('？', '?')):
            score += 0.3
        
        # 短句问句加权
        if len(text) < 50 and any(q in text for q in ['什么', '如何', '怎么', '为什么', '哪']):
            score += 0.2
        
        # 过滤掉明显的时间标记
        if re.match(r'^\d+:\d+', text) or re.match(r'^[a-zA-Z\u4e00-\u9fa5]+\d*\s*\d+:\d+', text):
            score = 0.0
        
        return min(1.0, score)
    
    def _calc_interviewee_score(self, text: str) -> float:
        """计算受访者特征得分"""
        score = 0.0
        count = 0
        
        for pattern in self.interviewee_patterns:
            if re.search(pattern, text):
                count += 1
        
        # 归一化（每匹配2个模式得1分）
        if count > 0:
            score = min(1.0, count / 2.0)
        
        # 长句加权（受访者通常回答较长）
        if len(text) > 50:
            score += 0.2
        elif len(text) > 100:
            score += 0.3
        
        # 包含工作内容关键词加权
        work_keywords = ['团队', '工作', '项目', '负责', '管理', '开发', '设计', '经验', '成果']
        if any(kw in text for kw in work_keywords):
            score += 0.15
        
        # 过滤掉明显的时间标记
        if re.match(r'^\d+:\d+', text) or re.match(r'^[a-zA-Z\u4e00-\u9fa5]+\d*\s*\d+:\d+', text):
            score = 0.0
        
        # 过滤掉短的无意义回答
        if len(text) < 10 and text in ['是的', '对', '嗯', '好的', '没错', '确实']:
            score = 0.3  # 降低得分但不完全过滤

        # 以问号结尾 → 大概率是提问，不是受访者陈述
        if text.rstrip().endswith(('？', '?')):
            score *= 0.6

        return min(1.0, score)
    
    def _is_statement(self, text: str) -> bool:
        """判断是否为陈述句（非问句）"""
        # 不以问号结尾，且不含疑问词
        if text.endswith(('？', '?', '吗', '呢')):
            return False
        
        question_words = ['什么', '怎么', '如何', '为什么', '哪', '请问']
        for word in question_words:
            if word in text:
                return False
        
        return True


def batch_extract_interviewee_sentences(
    texts: List[str],
    return_metadata: bool = False
) -> List[List[str]] | List[List[Dict[str, any]]]:
    """
    批量提取受访者语句
    
    Args:
        texts: 文本列表
        return_metadata: 是否返回元数据
        
    Returns:
        每个文本的受访者语句列表
    """
    extractor = SpeakerRoleExtractor()
    results = []
    
    for text in texts:
        try:
            interviewee_sents = extractor.extract_interviewee_sentences(
                text,
                return_metadata=return_metadata
            )
            results.append(interviewee_sents)
        except Exception as e:
            logger.error(f"提取受访者语句失败: {e}")
            results.append([])
    
    return results


# 测试代码
if __name__ == '__main__':
    # 测试用例1: 明确标注
    test_text1 = """
    采访者: 但传承应该还是有一些困难吧？您现在看到的困难主要是什么？
    受访者: 很多人来学习，都要自己负担生活费。这个是正常的。一般最少都要学一年。
    采访者: 时间比较长。
    受访者: 对，一年是最少的。真正想学到什么都会，肯定要三年。
    """
    
    # 测试用例2: 说话人编号
    test_text2 = """
    说话人1：请问您是晚上在这里经营摊位吗？
    说话人2：是的。
    说话人1：您觉得在陶溪川采用哪种经营模式，更容易被大众接受呢？
    说话人2：肯定是创新品类更受年轻人喜爱。
    """
    
    # 测试用例3: 无标注混合
    test_text3 = """
    做陶瓷肯定来景德镇了，别的地方不好做。因为景德镇这边的一个整个生产的一个产业链是很完整的。
    那您觉得景漂这个称呼对您意味着是什么呢？
    那倒没有可能也就只是一个标签吧。
    """
    
    # 测试用例4: 问答杂糅（简化版，更有代表性）
    test_text4 = """
    那您觉得景漂这个称呼对您意味着是什么呢？
    那倒没有可能也就只是一个标签吧。
    那您刚来的时候遇到的最大困难是什么呢？
    没钱哦。当时真的很困难。
    那如何解决这个困难呢？
    就是慢慢积累，一点一点做起来的。
    """
    
    extractor = SpeakerRoleExtractor()
    
    print("=" * 60)
    print("测试用例1: 明确标注")
    print("=" * 60)
    result1 = extractor.extract_interviewee_sentences(test_text1, return_metadata=True)
    for item in result1:
        print(f"[{item['speaker_label']}] 置信度:{item['confidence']:.2f}")
        print(f"  {item['text'][:100]}")
        print()
    
    print("=" * 60)
    print("测试用例2: 说话人编号")
    print("=" * 60)
    result2 = extractor.extract_interviewee_sentences(test_text2, return_metadata=True)
    for item in result2:
        print(f"[{item['speaker_label']}] 置信度:{item['confidence']:.2f}")
        print(f"  {item['text'][:100]}")
        print()
    
    print("=" * 60)
    print("测试用例3: 无标注混合")
    print("=" * 60)
    result3 = extractor.extract_interviewee_sentences(test_text3, return_metadata=True)
    for item in result3:
        print(f"[{item.get('speaker_label', 'unknown')}] 置信度:{item['confidence']:.2f}")
        print(f"  {item['text'][:100]}")
        print()
    
    print("=" * 60)
    print("测试用例4: 问答杂糅")
    print("=" * 60)
    result4 = extractor.extract_interviewee_sentences(test_text4, return_metadata=True)
    print(f"共提取 {len(result4)} 条受访者语句")
    for i, item in enumerate(result4):
        print(f"\n[{i+1}] 置信度:{item['confidence']:.2f}")
        print(f"  {item['text'][:80]}...")
    
    if len(result4) == 0:
        print("\n调试信息：")
        preprocessed = extractor._preprocess_text(test_text4)
        segments = extractor._segment_by_speaker(preprocessed)
        print(f"分段数: {len(segments)}")
        for i, seg in enumerate(segments[:5]):
            role = seg.get('inferred_role', 'none')
            print(f"{i+1}. {role}: {seg['text'][:50]}...")
