import logging
from typing import Dict, List, Any, Tuple
import re
import jieba.posseg as pseg

logger = logging.getLogger(__name__)


class GroundedTheoryCoder:
    """扎根理论编码器 - 改进版，支持新的编号系统和导航标记"""

    def _has_information_cue(self, text: str) -> bool:
        t = str(text or '').strip()
        if not t:
            return False
        return bool(re.search(
            r'(引入|建立|调整|获得|降低|提高|推动|解决|分析|反馈|合作|转变|优化|对接|支持|审批|流程|'
            r'受影响|受限|不足|短板|导向|循环|机会|需求|资源|服务|监督|指引|开发|探索|'
            r'协调|整合|压力|风险|价值|增长|转型|评价|约束|冲突|规范|机制|平台|系统|品牌|团队|客户|治理|场景|'
            r'检测|医学|化学|分子|检验|报告|科室|批评|惩罚|框架|组织|集体|行为|方向|能力|'
            r'采用|具备|创新|成果|实施|管理|运营|维护|保障|推进|开展|'
            r'技术|业务|领域|行业|市场|模式|策略|方法|路径|方案|项目)',
            t,
        ))

    def _contains_colloquial_residue(self, text: str) -> bool:
        t = str(text or '').strip()
        return bool(
            re.search(r'(怎么说呢|就是说|我觉得|相当于|要看|分场合|这个东西|这个事情|这个问题|就是那种|就这种|类似这种)', t)
            or re.search(r'[吧呢啊嘛呀哦哈哎诶噢呃]', t)
            or re.search(r'^(然后|就是|所以|但是|不过|其实|那个|这个|后来|当时)', t)
            or re.search(r'(什么的|之类的|那种感觉|这种感觉|这样子|那样子)$', t)
        )

    def _is_question_like(self, text: str) -> bool:
        t = str(text or '').strip()
        if not t:
            return False
        if any(word in t for word in self.question_words):
            return True
        return ('？' in t) or ('?' in t)

    def _has_valid_pos_pattern(self, text: str) -> bool:
        t = str(text or '').strip()
        if not t:
            return False
        try:
            tokens = [(word.strip(), flag) for word, flag in pseg.cut(t) if str(word).strip()]
        except Exception:
            return True
        if not tokens:
            return False
        words = [word for word, _ in tokens]
        flags = [flag for _, flag in tokens]
        if any(word in self.modal_particles for word in words):
            return False
        if any(word in self.pronouns for word in words):
            return False
        noun_like = any(flag.startswith(('n', 's', 'nt', 'nz')) for flag in flags)
        verb_like = any(flag.startswith('v') for flag in flags)
        adj_like = any(flag.startswith('a') for flag in flags)
        has_info = self._has_information_cue(t)
        # Accept if the text has content markers: nouns, verbs, adjectives,
        # or info-bearing cues. Only reject truly content-free strings.
        if not (noun_like or verb_like or has_info):
            return False
        if not (noun_like or verb_like or adj_like or has_info):
            return False
        return True

    def _check_first_level_quality(self, text: str) -> tuple:
        """Check code quality and return (pass: bool, reason: str)."""
        t = re.sub(r'^[A-Z]\d+\s*', '', str(text or '').strip())
        if not t or len(t) < 2:
            return False, "too_short"
        if self._is_question_like(t):
            return False, "question_like"
        if self._contains_colloquial_residue(t):
            return False, "colloquial_residue"
        # Multi-char pronoun check
        if any(p in t for p in self.pronouns if len(p) >= 2):
            return False, "multi_char_pronoun"
        # Single-char pronoun token check
        scp = {p for p in self.pronouns if len(p) == 1}
        if scp:
            try:
                tokens = [w.strip() for w, _ in pseg.cut(t) if w.strip()]
                if any(w in scp for w in tokens):
                    return False, "single_char_pronoun_token"
            except Exception:
                if any(p in t for p in scp):
                    return False, "single_char_pronoun_substring"
        if any(particle in t for particle in self.modal_particles):
            return False, "modal_particle"
        if re.search(r'^(因为|所以|但是|不过|然后|如果|就是|其实|那个|这个|后来|当时)$', t):
            return False, "bare_conjunction"
        if re.search(r'^(因为|所以|但是|不过|然后|如果|就是|其实|那个|这个|后来|当时)', t) and not self._has_information_cue(t):
            return False, "conjunction_no_info"
        if re.search(r'(这个|那个|这块|这一块|那种|这种|这样|那样)$', t):
            return False, "trailing_demonstrative"
        if re.search(r'(什么的|之类的)$', t):
            return False, "trailing_vague"
        if not self._has_valid_pos_pattern(t):
            return False, "no_valid_pos_pattern"
        return True, "ok"

    def _is_good_first_level_content(self, text: str) -> bool:
        ok, _ = self._check_first_level_quality(text)
        return ok

    def __init__(self):
        self.used_second_categories = set()
        self.used_first_contents = set()
        self.code_counter = {
            'third': 0,
            'second': {},
            'first': {}
        }
        self.modal_particles = {
            '啊', '呀', '呢', '吧', '嘛', '哦', '哈', '啦', '哇', '呗', '咯', '诶', '欸', '嗯'
        }
        self.pronouns = {
            '你', '我', '他', '她', '它', '你们', '我们', '他们', '她们', '它们'
        }
        self.question_words = {
            '吗', '么', '呢', '什么', '为什么', '怎么', '如何', '哪', '哪里', '哪儿', '是否'
        }

    def build_coding_structure(self, raw_codes: Dict[str, Any]) -> Dict[str, Any]:
        """构建三级编码结构并自动编号，去除重复编码"""
        try:
            # 重置计数器
            self.code_counter = {
                'third': 0,
                'second': {},
                'first': {}
            }
            self.used_second_categories.clear()
            self.used_first_contents.clear()

            structured_codes = {}

            first_level_codes = raw_codes.get("一阶编码") or raw_codes.get("first_level_codes", {})
            second_level_codes = raw_codes.get("二阶编码") or raw_codes.get("second_level_codes", {})
            third_level_codes = raw_codes.get("三阶编码") or raw_codes.get("third_level_codes", {})

            logger.info(
                f"开始构建编码结构: 一阶{len(first_level_codes)}, 二阶{len(second_level_codes)}, 三阶{len(third_level_codes)}")

            # 构建完整映射
            for third_category, second_categories in third_level_codes.items():
                structured_codes[third_category] = {}

                for second_category in second_categories:
                    if second_category in second_level_codes:
                        first_level_keys = second_level_codes[second_category]

                        first_level_contents = []
                        for key in first_level_keys:
                            if key in first_level_codes:
                                contents = first_level_codes[key]
                                if isinstance(contents, list) and len(contents) >= 5:
                                    content_str = contents[0]

                                    # 主程序最终展示前的一阶编码内容总闸
                                    _qc_result, _qc_reason = self._check_first_level_quality(content_str)
                                    if not _qc_result:
                                        logger.info("过滤低质量L1编码 [%s]: %s", _qc_reason, content_str)
                                        continue

                                    # 检查一阶编码是否有关联句子编号，无关联编号则跳过
                                    sentence_details = contents[4] if len(contents) >= 5 else []
                                    has_associated_number = False
                                    if isinstance(sentence_details, list) and sentence_details:
                                        for sd in sentence_details:
                                            if isinstance(sd, dict):
                                                tn = sd.get('text_number', '') or sd.get('sentence_id', '')
                                                if tn and str(tn).strip().isdigit():
                                                    has_associated_number = True
                                                    break
                                    if not has_associated_number:
                                        logger.info(f"过滤无关联编号的一阶编码: {content_str[:50]}...")
                                        continue

                                    # 检查一阶编码是否重复
                                    if content_str not in self.used_first_contents:
                                        self.used_first_contents.add(content_str)

                                        # Extract text_number from sentence details
                                        tn = None
                                        sd_list = contents[4] if len(contents) > 4 else []
                                        if isinstance(sd_list, list) and sd_list:
                                            first_sd = sd_list[0]
                                            if isinstance(first_sd, dict):
                                                tn = first_sd.get('text_number') or first_sd.get('sentence_id')

                                        first_level_contents.append({
                                            "content": content_str,
                                            "original_sentence": contents[1],
                                            "original_key": key,
                                            "file_count": contents[2],
                                            "sentence_count": contents[3],
                                            "sentence_details": contents[4],
                                            "text_number": tn,
                                        })

                        if first_level_contents:
                            # 检查二阶编码是否重复
                            clean_second = self.clean_category_name(second_category)
                            if clean_second not in self.used_second_categories:
                                self.used_second_categories.add(clean_second)
                                structured_codes[third_category][clean_second] = first_level_contents

            # 为编码结构自动编号
            numbered_structured_codes = self.add_coding_numbers_new_format(structured_codes)

            logger.info(f"构建了扎根理论编码结构: {len(numbered_structured_codes)}个三阶编码")
            return numbered_structured_codes

        except Exception as e:
            logger.error(f"构建编码结构失败: {e}")
            return {"错误": {"构建失败": [{"content": f"构建失败: {str(e)}", "original_sentence": "", "original_key": "error"}]}}

    def add_coding_numbers_new_format(self, structured_codes: Dict[str, Any]) -> Dict[str, Any]:
        """为编码结构添加新的自动编号格式：A开头一阶，B开头二阶，C开头三阶"""
        numbered_codes = {}

        # 一阶编码编号：A01, A02, A03... (A开头表示一阶，全局递增)
        first_index = 0

        # 三阶编码编号：C01, C02, C03... (C开头表示三阶)
        third_index = 0
        for third_category, second_categories in structured_codes.items():
            third_letter = 'C'  # 三阶编码使用C开头
            third_number = third_index + 1
            third_code = f"{third_letter}{third_number:02d}"  # C01, C02, C03...

            # 清理三阶编码名称
            clean_third = self.clean_category_name(third_category)
            numbered_third_category = f"{third_code} {clean_third}"
            numbered_codes[numbered_third_category] = {}

            # 二阶编码编号：B01, B02, B03... (B开头表示二阶)
            second_categories_list = list(second_categories.items())
            for j, (second_category, first_contents) in enumerate(second_categories_list):
                second_letter = 'B'  # 二阶编码使用B开头
                second_number = j + 1
                second_code = f"{second_letter}{second_number:02d}"  # B01, B02, B03...
                numbered_second_category = f"{second_code} {self.clean_category_name(second_category)}"
                numbered_codes[numbered_third_category][numbered_second_category] = []

                # 一阶编码编号：A01, A02, A03... (A开头表示一阶，全局递增)
                for first_content in first_contents:
                    first_letter = 'A'  # 一阶编码使用A开头
                    first_number = first_index + 1
                    code_id = f"{first_letter}{first_number:02d}"  # A01, A02, A03...
                    first_index += 1  # 全局递增

                    if isinstance(first_content, dict) and 'content' in first_content:
                        # 获取原始内容（不简化）
                        original_content = first_content['content']

                        # 构建带编号的一阶编码内容 - 显示完整编号
                        numbered_first_content = f"{code_id} {original_content}"

                        # 更新原始句子，添加编号标记
                        updated_sentence_details = self.add_code_id_to_sentences(
                            first_content.get('sentence_details', []),
                            code_id
                        )

                        numbered_codes[numbered_third_category][numbered_second_category].append({
                            "numbered_content": numbered_first_content,  # 带编号的完整内容
                            "content": original_content,  # 原始内容
                            "original_sentence": first_content.get('original_sentence', ''),
                            "original_key": first_content.get('original_key', ''),
                            "code_id": code_id,
                            "file_count": first_content.get('file_count', 1),
                            "sentence_count": first_content.get('sentence_count', 1),
                            "sentence_details": updated_sentence_details,
                            "text_number": first_content.get('text_number')
                        })

            third_index += 1

        logger.info(f"自动编号完成: 共{third_index}个三阶编码")
        return numbered_codes

    def add_coding_numbers(self, structured_codes: Dict[str, Any]) -> Dict[str, Any]:
        """为编码结构添加自动编号（兼容旧版本）"""
        return self.add_coding_numbers_new_format(structured_codes)

    def add_code_id_to_sentences(self, sentence_details: List[Dict[str, Any]], code_id: str) -> List[Dict[str, Any]]:
        """为句子详情添加编码ID（不修改content，不添加marked_content）"""
        updated_details = []

        for sentence in sentence_details:
            if isinstance(sentence, dict):
                updated_sentence = sentence.copy()
                # 只添加 code_id 字段，不修改 content，不添加 marked_content
                updated_sentence['code_id'] = code_id
                updated_details.append(updated_sentence)
            else:
                updated_details.append(sentence)

        return updated_details

    def clean_category_name(self, category_name: str) -> str:
        """清理类别名称，移除编号前缀"""
        # 移除所有可能的编号格式：A, A1, A11等
        cleaned = re.sub(r'^[A-Z]\d*\s*', '', category_name.strip())
        return cleaned

    def simplify_content_intelligent(self, content: str) -> str:
        """智能内容简化方法 - 保留核心信息"""
        if not content:
            return ""

        # 移除编号前缀（如果有）
        content = re.sub(r'^[A-Z]\d+\s*', '', content.strip())

        # 如果内容本身已经很简洁，直接返回
        if len(content) <= 25:
            return content

        # 移除口语词但保持内容完整
        oral_words = ['我觉得', '我认为', '我感觉', '我想', '就是说', '然后',
                      '就是', '就是說', '嗯', '啊', '对不对']

        cleaned = content
        for word in oral_words:
            cleaned = cleaned.replace(word, '')

        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # 智能截断
        if len(cleaned) > 30:
            # 在30个字符附近找合适的截断点
            for i in range(25, min(35, len(cleaned))):
                if cleaned[i] in '，。；;！!?？':
                    return cleaned[:i].strip()
            return cleaned[:30].strip() + "..."

        return cleaned

    def generate_navigation_text(self, structured_codes: Dict[str, Any], original_text: str) -> str:
        """生成带导航标记的文本"""
        try:
            navigation_text = original_text

            # 收集所有编码位置信息
            code_positions = []

            for third_cat, second_cats in structured_codes.items():
                for second_cat, first_contents in second_cats.items():
                    for content_data in first_contents:
                        if isinstance(content_data, dict):
                            code_id = content_data.get('code_id', '')
                            sentence_details = content_data.get('sentence_details', [])

                            for sentence in sentence_details:
                                if isinstance(sentence, dict):
                                    original_content = sentence.get('original_content', '')  # 原始内容（无标记）
                                    marked_content = sentence.get('content', '')  # 带标记的内容

                                    if original_content and code_id:
                                        # 在原始文本中查找并替换为带标记的内容
                                        if original_content in navigation_text:
                                            navigation_text = navigation_text.replace(
                                                original_content,
                                                marked_content
                                            )

            return navigation_text

        except Exception as e:
            logger.error(f"生成导航文本失败: {e}")
            return original_text