import os
import json
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import shutil
import re
import copy
from config import Config
from path_manager import PathManager

logger = logging.getLogger(__name__)


class StandardAnswerManager:
    """标准答案管理器 - 增强版，支持增量保存"""

    def __init__(self):
        self.standard_answers_dir = PathManager.get_standard_answers_dir()
        self.backup_dir = PathManager.get_backup_dir()
        self.modifications_dir = PathManager.get_modifications_dir()
        PathManager.ensure_dir(self.standard_answers_dir)
        PathManager.ensure_dir(self.backup_dir)
        PathManager.ensure_dir(self.modifications_dir)

        # 当前标准答案
        self.current_answers = {}
        self.version_history = []
        self.load_latest_answers()

    def create_from_structured_codes(self, structured_codes: Dict[str, Any], description: str = "") -> str:
        """从结构化编码创建标准答案"""
        try:
            # 生成版本号
            version = f"v{len(os.listdir(self.standard_answers_dir)) + 1}"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            version_id = f"{version}_{timestamp}"

            standard_answer = {
                "metadata": {
                    "version": version_id,
                    "description": description,
                    "created_time": self.get_timestamp(),
                    "source": "manual_coding",
                    "code_statistics": self._calculate_statistics(structured_codes),
                    "total_codes": self._count_total_codes(structured_codes)
                },
                "structured_codes": self._convert_to_standard_format(structured_codes),
                "training_data": self._extract_training_data(structured_codes),
                "export_formats": {
                    "json": True,
                    "excel": True,
                    "word": False
                }
            }

            # 保存文件
            file_path = PathManager.join(self.standard_answers_dir, f"{version_id}.json")
            with PathManager.safe_open(file_path, 'w', encoding='utf-8') as f:
                json.dump(standard_answer, f, ensure_ascii=False, indent=2)

            # 创建备份
            self._create_backup(version_id, standard_answer)

            # 更新当前答案和版本历史
            self.current_answers = standard_answer
            self.version_history.append({
                "version": version_id,
                "description": description,
                "timestamp": self.get_timestamp(),
                "file_path": file_path,
                "type": "full"
            })

            # 保存版本历史
            self._save_version_history()

            logger.info(f"标准答案已创建: {version_id}")
            return version_id

        except Exception as e:
            logger.error(f"创建标准答案失败: {e}")
            return None

    def save_modifications_only(self, modified_codes: Dict[str, Any], description: str = "") -> str:
        """只保存修改和新增的编码（增量保存）"""
        try:
            if not self.current_answers:
                return self.create_from_structured_codes(modified_codes, description)

            # 获取当前标准答案
            current_codes = self.current_answers.get("structured_codes", {})

            # 分析修改内容
            modifications = self._analyze_modifications(current_codes, modified_codes)

            if not modifications["has_changes"]:
                logger.info("没有检测到修改，跳过保存")
                return self.current_answers["metadata"]["version"]

            # 备份当前答案
            current_version = self.current_answers["metadata"]["version"]
            self._create_backup(f"pre_modification_{current_version}", self.current_answers)

            # 合并修改到当前标准答案
            merged_codes = self._merge_modifications(current_codes, modifications)

            # 创建新版本
            version = f"v{len(os.listdir(self.standard_answers_dir)) + 1}"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            version_id = f"{version}_{timestamp}"

            standard_answer = {
                "metadata": {
                    "version": version_id,
                    "description": description,
                    "created_time": self.get_timestamp(),
                    "source": "incremental_update",
                    "code_statistics": self._calculate_statistics(merged_codes),
                    "total_codes": self._count_total_codes(merged_codes),
                    "modification_summary": modifications["summary"]
                },
                "structured_codes": merged_codes,
                "training_data": self._extract_training_data(merged_codes),
                "modification_details": modifications,
                "export_formats": {
                    "json": True,
                    "excel": True,
                    "word": False
                }
            }

            # 保存完整文件
            file_path = PathManager.join(self.standard_answers_dir, f"{version_id}.json")
            with PathManager.safe_open(file_path, 'w', encoding='utf-8') as f:
                json.dump(standard_answer, f, ensure_ascii=False, indent=2)

            # 保存修改详情（单独文件）
            modification_file = PathManager.join(self.modifications_dir, f"modifications_{version_id}.json")
            with PathManager.safe_open(modification_file, 'w', encoding='utf-8') as f:
                json.dump(modifications, f, ensure_ascii=False, indent=2)

            # 更新当前答案和版本历史
            self.current_answers = standard_answer
            self.version_history.append({
                "version": version_id,
                "description": description,
                "timestamp": self.get_timestamp(),
                "file_path": file_path,
                "type": "incremental",
                "modification_summary": modifications["summary"]
            })

            # 保存版本历史
            self._save_version_history()

            logger.info(f"增量保存完成: {version_id}")
            logger.info(f"修改统计: {modifications['summary']}")
            return version_id

        except Exception as e:
            logger.error(f"增量保存失败: {e}")
            return None

    def _analyze_modifications(self, original: Dict[str, Any], modified: Dict[str, Any]) -> Dict[str, Any]:
        """分析修改内容"""
        modifications = {
            "added": {},
            "modified": {},
            "deleted": {},
            "summary": {
                "added_codes": 0,
                "modified_codes": 0,
                "deleted_codes": 0
            },
            "has_changes": False
        }

        try:
            original_standard = self._convert_to_standard_format(original)
            modified_standard = self._convert_to_standard_format(modified)
        except Exception as e:
            logger.error(f"转换标准格式失败: {e}")
            return modifications

        for third_cat in modified_standard:
            if third_cat not in original_standard:
                modifications["added"][third_cat] = copy.deepcopy(modified_standard[third_cat])
                modifications["summary"]["added_codes"] += self._count_codes_in_category(modified_standard[third_cat])

        for third_cat in original_standard:
            if third_cat not in modified_standard:
                modifications["deleted"][third_cat] = copy.deepcopy(original_standard[third_cat])
                modifications["summary"]["deleted_codes"] += self._count_codes_in_category(original_standard[third_cat])

        for third_cat in modified_standard:
            if third_cat in original_standard:
                try:
                    third_modifications = self._analyze_second_level_modifications(
                        original_standard[third_cat],
                        modified_standard[third_cat],
                        third_cat
                    )

                    if third_modifications["has_changes"]:
                        modifications["modified"][third_cat] = third_modifications
                        modifications["summary"]["added_codes"] += third_modifications["summary"]["added_codes"]
                        modifications["summary"]["modified_codes"] += third_modifications["summary"]["modified_codes"]
                        modifications["summary"]["deleted_codes"] += third_modifications["summary"]["deleted_codes"]
                except Exception as e:
                    logger.error(f"分析三阶编码修改失败 {third_cat}: {e}")

        total_changes = (modifications["summary"]["added_codes"] +
                         modifications["summary"]["modified_codes"] +
                         modifications["summary"]["deleted_codes"])
        modifications["has_changes"] = total_changes > 0

        return modifications

    def _analyze_second_level_modifications(self, original_second: Dict[str, Any],
                                            modified_second: Dict[str, Any],
                                            third_cat: str) -> Dict[str, Any]:
        """分析二阶编码的修改"""
        modifications = {
            "added": {},
            "modified": {},
            "deleted": {},
            "summary": {
                "added_codes": 0,
                "modified_codes": 0,
                "deleted_codes": 0
            },
            "has_changes": False
        }

        for second_cat in modified_second:
            if second_cat not in original_second:
                modifications["added"][second_cat] = copy.deepcopy(modified_second[second_cat])
                modifications["summary"]["added_codes"] += len(modified_second[second_cat])

        for second_cat in original_second:
            if second_cat not in modified_second:
                modifications["deleted"][second_cat] = copy.deepcopy(original_second[second_cat])
                modifications["summary"]["deleted_codes"] += len(original_second[second_cat])

        for second_cat in modified_second:
            if second_cat in original_second:
                first_modifications = self._analyze_first_level_modifications(
                    original_second[second_cat],
                    modified_second[second_cat],
                    f"{third_cat} > {second_cat}"
                )

                if first_modifications["has_changes"]:
                    modifications["modified"][second_cat] = first_modifications
                    modifications["summary"]["added_codes"] += first_modifications["summary"]["added_codes"]
                    modifications["summary"]["modified_codes"] += first_modifications["summary"]["modified_codes"]
                    modifications["summary"]["deleted_codes"] += first_modifications["summary"]["deleted_codes"]

        total_changes = (modifications["summary"]["added_codes"] +
                         modifications["summary"]["modified_codes"] +
                         modifications["summary"]["deleted_codes"])
        modifications["has_changes"] = total_changes > 0

        return modifications

    def _analyze_first_level_modifications(self, original_first: List[Any],
                                           modified_first: List[Any],
                                           category_path: str) -> Dict[str, Any]:
        """分析一阶编码的修改"""
        modifications = {
            "added": [],
            "modified": [],
            "deleted": [],
            "summary": {
                "added_codes": 0,
                "modified_codes": 0,
                "deleted_codes": 0
            },
            "has_changes": False
        }

        try:
            from collections import defaultdict

            def get_content_key(item):
                """用于比较的一阶编码键值

                优先使用 code_id + content 组合，保证像 A21/A22 这种
                内容相似但编号不同的编码可以被单独识别和统计。
                没有 code_id 的情况（手动新增的自由编码）退化为只用内容。
                """
                if isinstance(item, dict):
                    content = item.get('content', item.get('name', str(item)))
                    code_id = item.get('code_id')
                    if code_id:
                        return f"{code_id}||{content}"
                    return content
                return str(item)

            def get_content_dict(item):
                if isinstance(item, dict):
                    return copy.deepcopy(item)
                return {'content': str(item)}

            # 使用列表映射处理重复项
            original_map = defaultdict(list)
            for item in original_first:
                try:
                    key = get_content_key(item)
                    original_map[key].append(get_content_dict(item))
                except Exception as e:
                    logger.warning(f"处理原始一阶编码时出错: {e}")

            modified_map = defaultdict(list)
            for item in modified_first:
                try:
                    key = get_content_key(item)
                    modified_map[key].append(get_content_dict(item))
                except Exception as e:
                    logger.warning(f"处理修改后一阶编码时出错: {e}")

            all_keys = set(original_map.keys()) | set(modified_map.keys())

            for key in all_keys:
                orig_items = original_map[key]
                mod_items = modified_map[key]

                # 计算数量差异（用于新增/删除统计）
                diff = len(mod_items) - len(orig_items)

                if diff > 0:
                    # 新增了 diff 个项目
                    modifications["added"].extend(mod_items[-diff:])
                    modifications["summary"]["added_codes"] += diff
                elif diff < 0:
                    # 删除了 abs(diff) 个项目
                    count = abs(diff)
                    modifications["deleted"].extend(orig_items[:count])
                    modifications["summary"]["deleted_codes"] += count

            # 额外检测：同一 code_id 下内容是否发生变化，计入 "修改编码"
            try:
                def get_code_id(item):
                    if isinstance(item, dict):
                        return item.get("code_id")
                    return None

                def get_content_text(item):
                    if isinstance(item, dict):
                        return str(item.get("content", item.get("name", "")))
                    return str(item)

                original_by_id = {}
                for item in original_first:
                    cid = get_code_id(item)
                    if cid:
                        original_by_id[cid] = item

                modified_by_id = {}
                for item in modified_first:
                    cid = get_code_id(item)
                    if cid:
                        modified_by_id[cid] = item

                common_ids = set(original_by_id.keys()) & set(modified_by_id.keys())

                for cid in common_ids:
                    o_item = original_by_id[cid]
                    m_item = modified_by_id[cid]
                    if get_content_text(o_item) != get_content_text(m_item):
                        modifications["summary"]["modified_codes"] += 1
            except Exception as e:
                logger.warning(f"检测基于 code_id 的一阶编码修改失败 {category_path}: {e}")

            total_changes = (modifications["summary"]["added_codes"] +
                             modifications["summary"]["deleted_codes"] +
                             modifications["summary"]["modified_codes"])
            modifications["has_changes"] = total_changes > 0
            
            # 添加日志，方便调试删除检测问题
            if modifications["has_changes"]:
                 logger.debug(f"Detected changes in {category_path}: Added={modifications['summary']['added_codes']}, Deleted={modifications['summary']['deleted_codes']}")

        except Exception as e:
            logger.error(f"分析一阶编码修改失败 {category_path}: {e}")

        return modifications

    def _merge_modifications(self, original: Dict[str, Any], modifications: Dict[str, Any]) -> Dict[str, Any]:
        """合并修改到原始标准答案"""
        merged = copy.deepcopy(original)

        # 处理新增的三阶类别（整块新增）
        for third_cat, second_cats in modifications["added"].items():
            merged[third_cat] = copy.deepcopy(second_cats)

        # 处理被整体删除的三阶类别
        for third_cat in modifications["deleted"]:
            if third_cat in merged:
                del merged[third_cat]

        # 工具函数：用于一阶编码匹配，保证删除时更稳健
        def _first_level_key(item: Any) -> str:
            if isinstance(item, dict):
                content = item.get("content", item.get("name", str(item)))
                code_id = item.get("code_id")
                if code_id:
                    return f"{code_id}||{content}"
                return str(content)
            return str(item)

        # 处理在现有三阶类别下的二阶/一阶修改
        for third_cat, third_modifications in modifications["modified"].items():
            if third_cat in merged:
                # 新增完整的二阶类别
                for second_cat, first_codes in third_modifications["added"].items():
                    if second_cat not in merged[third_cat]:
                        merged[third_cat][second_cat] = copy.deepcopy(first_codes)
                    else:
                        # 同一二阶下新增的一阶编码，追加到原列表
                        merged[third_cat][second_cat].extend(copy.deepcopy(first_codes))

                # 删除整个二阶类别
                for second_cat in third_modifications["deleted"]:
                    if second_cat in merged[third_cat]:
                        del merged[third_cat][second_cat]

                for second_cat, second_modifications in third_modifications["modified"].items():
                    if second_cat in merged[third_cat]:
                        # 处理一阶新增：基于 key 去重后追加
                        existing_list = merged[third_cat][second_cat]
                        existing_keys = {_first_level_key(item) for item in existing_list}

                        for first_code in second_modifications["added"]:
                            key = _first_level_key(first_code)
                            if key not in existing_keys:
                                existing_list.append(copy.deepcopy(first_code))
                                existing_keys.add(key)

                        # 处理一阶删除：按 key 过滤列表，确保真正移除
                        if second_modifications["deleted"]:
                            deleted_keys = {_first_level_key(item) for item in second_modifications["deleted"]}
                            merged[third_cat][second_cat] = [
                                item for item in existing_list
                                if _first_level_key(item) not in deleted_keys
                            ]

        return merged

    def _count_codes_in_category(self, category: Dict[str, Any]) -> int:
        """计算类别中的编码数量"""
        count = 0
        for second_cat, first_codes in category.items():
            count += len(first_codes)
        return count

    def _count_total_codes(self, structured_codes: Dict[str, Any]) -> int:
        """计算总编码数量"""
        total = 0
        for third_cat, second_cats in structured_codes.items():
            for second_cat, first_codes in second_cats.items():
                total += len(first_codes)
        return total

    def get_modification_history(self) -> List[Dict[str, Any]]:
        """获取修改历史"""
        modification_files = [f for f in os.listdir(self.modifications_dir) if f.startswith('modifications_')]
        history = []

        for file in modification_files:
            try:
                file_path = PathManager.join(self.modifications_dir, file)
                with PathManager.safe_open(file_path, 'r', encoding='utf-8') as f:
                    modification_data = json.load(f)

                version = file.replace('modifications_', '').replace('.json', '')
                history.append({
                    "version": version,
                    "modification_date": os.path.getctime(file_path),
                    "summary": modification_data.get("summary", {}),
                    "file_path": file_path
                })
            except Exception as e:
                logger.error(f"加载修改历史文件失败 {file}: {e}")

        # 按时间排序
        history.sort(key=lambda x: x["modification_date"], reverse=True)
        return history

    # 保留原有的方法用于兼容性
    def merge_with_existing(self, new_structured_codes: Dict[str, Any], description: str = "") -> str:
        """合并新编码到现有标准答案 - 现在使用增量保存"""
        return self.save_modifications_only(new_structured_codes, description)

    def _convert_to_standard_format(self, structured_codes: Dict[str, Any]) -> Dict[str, Any]:
        """转换为标准格式"""
        standard_format = {}

        for third_cat, second_cats in structured_codes.items():
            clean_third = self._clean_category_name(third_cat)
            standard_format[clean_third] = {}

            for second_cat, first_contents in second_cats.items():
                clean_second = self._clean_category_name(second_cat)
                standard_format[clean_third][clean_second] = []

                for content in first_contents:
                    # 保留完整的一阶编码数据结构，包括sentence_details
                    if isinstance(content, dict):
                        # 确保content字段存在
                        if 'content' not in content and 'name' in content:
                            content['content'] = content['name']
                        # 保留完整的字典结构，包括sentence_details
                        standard_format[clean_third][clean_second].append(content)
                    else:
                        # 处理字符串内容
                        clean_content = self._clean_first_level_content(str(content))
                        if clean_content:
                            standard_format[clean_third][clean_second].append(clean_content)

        return standard_format

    def _clean_category_name(self, name: str) -> str:
        """清理类别名称"""
        return re.sub(r'^[A-Z]\d*\s*', '', name.strip())

    def _clean_first_level_content(self, content: str) -> str:
        """清理一阶编码内容"""
        return re.sub(r'^[A-Z]\d+\s*', '', content.strip())

    def _calculate_statistics(self, structured_codes: Dict[str, Any]) -> Dict[str, Any]:
        """计算统计信息"""
        third_count = len(structured_codes)
        second_count = sum(len(categories) for categories in structured_codes.values())
        first_count = sum(
            len(contents)
            for categories in structured_codes.values()
            for contents in categories.values()
        )

        return {
            "third_level_codes": third_count,
            "second_level_codes": second_count,
            "first_level_codes": first_count,
            "total_codes": first_count
        }

    def _extract_training_data(self, structured_codes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取训练数据，生成面向模型训练的结构化样本

        目标结构示例：
        {
            "input_sentences": {
                "original_content": "原语句",
                "related_statement": ["句子1", "句子2"]
            },
            "target_abstract": "抽象重点（一阶编码）",
            "target_second_category": "二级分类",
            "target_third_category": "三级分类"
        }
        """

        training_data: List[Dict[str, Any]] = []

        for third_cat, second_cats in structured_codes.items():
            for second_cat, first_contents in second_cats.items():
                for content in first_contents:
                    if not isinstance(content, dict):
                        # 兼容字符串等简单形式
                        abstract_text = str(content).strip()
                        if not abstract_text:
                            continue

                        training_data.append({
                            "input_sentences": {
                                "original_content": abstract_text,
                                "related_statement": []
                            },
                            "target_abstract": abstract_text,
                            "target_second_category": second_cat,
                            "target_third_category": third_cat
                        })
                        continue

                    # 一阶编码的抽象文本（目标摘要）
                    if "content" in content:
                        target_abstract = (content.get("content") or "").strip()
                    elif "name" in content:
                        target_abstract = (content.get("name") or "").strip()
                    else:
                        target_abstract = str(content).strip()

                    # 原始语句：优先使用 original_sentence 列表中的 original_content
                    original_content = ""
                    original_sentences = content.get("original_sentence", [])
                    if original_sentences and isinstance(original_sentences[0], dict):
                        original_content = (
                            original_sentences[0].get("original_content")
                            or original_sentences[0].get("content", "")
                        )

                    if not original_content:
                        # 回退到一阶编码的文本内容
                        original_content = target_abstract

                    original_content = (original_content or "").strip()

                    # 关联句子：来自 sentence_details 中的拖拽文本
                    related_statements: List[str] = []
                    sentence_details = content.get("sentence_details", [])
                    for sentence in sentence_details:
                        if not isinstance(sentence, dict):
                            continue

                        dragged_text = (
                            sentence.get("original_content", "")
                            or sentence.get("text", "")
                            or sentence.get("content", "")
                        )
                        dragged_text = (dragged_text or "").strip()
                        if not dragged_text:
                            continue

                        # 清理尾部的 [A01] / [1] 等编号标记
                        clean_dragged_text = re.sub(r"\s*\[[A-Z]\d+\]", "", dragged_text)
                        clean_dragged_text = re.sub(r"\s*\[\d+\]", "", clean_dragged_text)
                        clean_dragged_text = re.sub(r"^[A-Z]\d+\s+", "", clean_dragged_text).strip()

                        if clean_dragged_text:
                            related_statements.append(clean_dragged_text)

                    if not target_abstract and not original_content and not related_statements:
                        # 完全没有可用文本则跳过
                        continue

                    sample: Dict[str, Any] = {
                        "input_sentences": {
                            "original_content": original_content,
                            "related_statement": related_statements,
                        },
                        "target_abstract": target_abstract or original_content,
                        "target_second_category": second_cat,
                        "target_third_category": third_cat,
                    }

                    training_data.append(sample)

        return training_data

    def _create_backup(self, version_id: str, data: Dict[str, Any]):
        """创建备份"""
        backup_file = PathManager.join(self.backup_dir, f"{version_id}.json")
        with PathManager.safe_open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_version_history(self):
        """保存版本历史"""
        history_file = PathManager.join(self.standard_answers_dir, "version_history.json")
        with PathManager.safe_open(history_file, 'w', encoding='utf-8') as f:
            json.dump(self.version_history, f, ensure_ascii=False, indent=2)

    def load_latest_answers(self):
        """加载最新的标准答案"""
        try:
            answer_files = [f for f in os.listdir(self.standard_answers_dir) if
                            f.endswith('.json') and not f.startswith('.')]
            if answer_files:
                # 排除历史文件
                answer_files = [f for f in answer_files if f not in ['version_history.json', 'merge_history.json']]
                if answer_files:
                    answer_files.sort(reverse=True)

                    # 尝试加载最新的文件，如果失败则尝试下一个
                    for file_name in answer_files:
                        if self.load_answers(file_name):
                            logger.info(f"成功加载最新的标准答案: {file_name}")
                            break
                    else:
                        logger.warning("没有找到可加载的标准答案文件")

        except Exception as e:
            logger.error(f"加载最新标准答案失败: {e}")

        # 加载版本历史
        self._load_version_history()

    def _load_version_history(self):
        """加载版本历史"""
        history_file = PathManager.join(self.standard_answers_dir, "version_history.json")
        if PathManager.exists(history_file):
            with PathManager.safe_open(history_file, 'r', encoding='utf-8') as f:
                self.version_history = json.load(f)

    def load_answers(self, filename: str) -> bool:
        """加载指定标准答案"""
        try:
            # 检查是否需要添加 .json 扩展名
            if not filename.endswith('.json'):
                filename_json = filename + '.json'
                file_path_json = PathManager.join(self.standard_answers_dir, filename_json)
                if PathManager.exists(file_path_json):
                    filename = filename_json

            file_path = PathManager.join(self.standard_answers_dir, filename)

            # 打印路径信息用于调试
            print(f"StandardAnswerManager 检查文件路径: {file_path}")
            print(f"文件是否存在: {PathManager.exists(file_path)}")

            # 检查文件是否存在
            if not PathManager.exists(file_path):
                logger.error(f"标准答案文件不存在: {file_path}")
                return False

            # 检查文件大小
            if os.path.getsize(file_path) == 0:
                logger.error(f"标准答案文件为空: {file_path}")
                return False

            # 尝试打开和解析文件
            try:
                with PathManager.safe_open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 检查文件内容是否为空
                if not content.strip():
                    logger.error(f"标准答案文件内容为空: {file_path}")
                    return False

                # 解析JSON
                self.current_answers = json.loads(content)

                # 验证数据结构
                if not isinstance(self.current_answers, dict):
                    logger.error(f"标准答案文件格式错误: 不是有效的JSON对象")
                    return False

                # 验证必要的字段
                if "structured_codes" not in self.current_answers:
                    logger.warning(f"标准答案文件缺少 structured_codes 字段")
                    # 不返回False，因为可能是旧版本的文件

                logger.info(f"标准答案已加载: {filename}")
                return True

            except UnicodeDecodeError:
                logger.error(f"标准答案文件编码错误: 不是UTF-8编码")
                return False
            except json.JSONDecodeError as e:
                logger.error(f"标准答案文件JSON格式错误: {e}")
                return False
            except Exception as e:
                logger.error(f"加载标准答案文件失败: {e}")
                return False

        except Exception as e:
            logger.error(f"加载标准答案失败: {e}")
            return False

    def get_current_answers(self) -> Dict[str, Any]:
        """获取当前标准答案"""
        return self.current_answers

    def get_version_history(self) -> List[Dict[str, Any]]:
        """获取版本历史"""
        # 每次获取版本历史时都从文件重新加载，确保获取最新版本
        self._load_version_history()
        return self.version_history

    def get_training_sample_count(self) -> int:
        """获取训练样本数量"""
        if not self.current_answers:
            return 0

        count = 0
        structured_codes = self.current_answers.get("structured_codes", {})
        for third_cat, second_cats in structured_codes.items():
            for second_cat, first_contents in second_cats.items():
                count += len(first_contents)

        return count

    def export_for_training(self) -> Dict[str, Any]:
        """导出用于训练的数据"""
        if not self.current_answers:
            return {}

        # 返回当前标准答案中的训练相关数据
        training_data = {
            "structured_codes": self.current_answers.get("structured_codes", {}),
            "metadata": self.current_answers.get("metadata", {}),
            "training_data": self.current_answers.get("training_data", {})
        }

        return training_data

    def get_timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")