import re
import csv
import jieba
import jieba.posseg as pseg
from collections import Counter, defaultdict
from typing import List, Dict, Set, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class HighQualitySampleLearner:
    """从高质量样本中学习语义模式和编码特征"""

    def __init__(self):
        self.valid_codes: Set[str] = set()
        self.code_to_source: Dict[str, str] = {}
        self.frequent_nouns: Counter = Counter()
        self.frequent_verbs: Counter = Counter()
        self.valid_patterns: List[re.Pattern] = []
        self.semantic_vectors: Dict[str, List[str]] = {}
        self.keyword_cooccurrence: defaultdict = defaultdict(Counter)

    def _read_csv_rows(self, file_path: str) -> Tuple[Optional[List[list]], Optional[str]]:
        """按常见编码依次尝试读取 CSV（项目样本多为 GBK/UTF-8）。"""
        for encoding in ('utf-8-sig', 'utf-8', 'gb18030', 'gbk'):
            try:
                with open(file_path, 'r', encoding=encoding, newline='') as f:
                    rows = list(csv.reader(f))
                return rows, encoding
            except UnicodeDecodeError:
                continue
        return None, None

    def load_samples(self, file_path: str) -> bool:
        """加载高质量样本CSV文件"""
        try:
            rows, encoding = self._read_csv_rows(file_path)
            if not rows:
                logger.error("加载样本失败: 无法用 utf-8/gbk 等编码解析文件")
                return False

            if len(rows) > 1:
                rows = rows[1:]  # 跳过表头
            for row in rows:
                if len(row) >= 2:
                    code = row[0].strip()
                    source = row[1].strip() if len(row) > 1 else ""
                    if code and len(code) >= 4:
                        self.valid_codes.add(code)
                        self.code_to_source[code] = source
                        self._analyze_code(code)
            logger.info(f"加载了 {len(self.valid_codes)} 个高质量样本 (encoding={encoding})")
            return True
        except Exception as e:
            logger.error(f"加载样本失败: {e}")
            return False

    def _analyze_code(self, code: str) -> None:
        """分析编码的词性特征"""
        try:
            tokens = pseg.cut(code)
            words = []
            for word, flag in tokens:
                words.append(word)
                if flag.startswith('n'):
                    self.frequent_nouns[word] += 1
                elif flag.startswith('v'):
                    self.frequent_verbs[word] += 1
            
            for i, word in enumerate(words):
                if i < len(words) - 1:
                    next_word = words[i + 1]
                    self.keyword_cooccurrence[word][next_word] += 1
                    self.keyword_cooccurrence[next_word][word] += 1
                    
            self.semantic_vectors[code] = words
        except Exception:
            pass

    def score_by_pattern_match(self, candidate: str) -> float:
        """根据高质量样本模式匹配度打分"""
        score = 0.0
        candidate_tokens = [word for word, _ in pseg.cut(candidate)]
        
        for token in candidate_tokens:
            if token in self.frequent_nouns:
                score += self.frequent_nouns[token] * 0.1
            if token in self.frequent_verbs:
                score += self.frequent_verbs[token] * 0.15
        
        for i, token in enumerate(candidate_tokens):
            if i < len(candidate_tokens) - 1:
                next_token = candidate_tokens[i + 1]
                if next_token in self.keyword_cooccurrence.get(token, {}):
                    score += self.keyword_cooccurrence[token][next_token] * 0.05
        
        matched_pattern = self._match_quality_pattern(candidate)
        if matched_pattern:
            score += 2.0
        
        return score

    def _match_quality_pattern(self, text: str) -> bool:
        """检查是否匹配高质量编码模式"""
        patterns = [
            r'^[动词][名词][名词]$',
            r'^[名词][动词][名词]$',
            r'^[动词][名词]$',
            r'^[名词][名词][名词]$',
            r'^[形容词][名词][名词]$',
        ]
        
        pos_tags = [flag for _, flag in pseg.cut(text)]
        pos_pattern = ''.join([
            '动词' if flag.startswith('v') else
            '名词' if flag.startswith('n') else
            '形容词' if flag.startswith('a') else
            '其他'
            for flag in pos_tags
        ])
        
        for pattern in patterns:
            if re.match(pattern.replace('[动词]', '动词').replace('[名词]', '名词').replace('[形容词]', '形容词'), pos_pattern):
                return True
        return False

    def is_high_quality_like(self, candidate: str) -> bool:
        """判断候选编码是否符合高质量编码特征"""
        clean = candidate.strip()
        if not clean or len(clean) < 4:
            return False
        
        tokens = list(pseg.cut(clean))
        if len(tokens) < 2:
            return False
        
        has_verb = any(flag.startswith('v') for _, flag in tokens)
        has_noun = any(flag.startswith('n') for _, flag in tokens)
        
        if not has_noun:
            return False
        
        pronouns = {'我', '我们', '你', '你们', '他', '他们'}
        modal_particles = {'吗', '嘛', '吧', '呢', '啊', '呀', '哦', '哈', '呗', '啦'}
        
        words = [word for word, _ in tokens]
        if any(word in pronouns for word in words):
            return False
        if any(word in modal_particles for word in words):
            return False
        
        weak_starters = {'我觉得', '其实', '然后', '所以', '但是', '不过', '当时', '那个时候', '就是'}
        if any(clean.startswith(ws) for ws in weak_starters):
            return False
        
        return True

    def suggest_improvement(self, low_quality_code: str) -> Optional[str]:
        """基于样本模式提出改进建议"""
        tokens = [word for word, _ in pseg.cut(low_quality_code)]
        suggestions = []
        
        for token in tokens:
            if token in self.frequent_verbs:
                related_nouns = [
                    noun for noun in self.frequent_nouns 
                    if noun in self.keyword_cooccurrence.get(token, {})
                ]
                if related_nouns:
                    suggestions.append(f"{token}{related_nouns[0]}")
        
        if suggestions:
            return suggestions[0]
        return None

    def get_top_keywords(self, n: int = 20) -> Tuple[List[str], List[str]]:
        """获取高频名词和动词"""
        top_nouns = [word for word, _ in self.frequent_nouns.most_common(n)]
        top_verbs = [word for word, _ in self.frequent_verbs.most_common(n)]
        return top_nouns, top_verbs