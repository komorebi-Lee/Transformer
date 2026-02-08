import os
import json
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import shutil
import re

logger = logging.getLogger(__name__)


class StandardAnswerManager:
    """标准答案管理器 - 增强版，支持增量保存"""

    def __init__(self):
        self.standard_answers_dir = "standard_answers"
        self.backup_dir = os.path.join(self.standard_answers_dir, "backups")
        self.modifications_dir = os.path.join(self.standard_answers_dir, "modifications")
        os.makedirs(self.standard_answers_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.modifications_dir, exist_ok=True)

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
            file_path = os.path.join(self.standard_answers_dir, f"{version_id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
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
            file_path = os.path.join(self.standard_answers_dir, f"{version_id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(standard_answer, f, ensure_ascii=False, indent=2)

            # 保存修改详情（单独文件）
            modification_file = os.path.join(self.modifications_dir, f"modifications_{version_id}.json")
            with open(modification_file, 'w', encoding='utf-8') as f:
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

        # 转换为标准格式进行比较
        original_standard = self._convert_to_standard_format(original)
        modified_standard = self._convert_to_standard_format(modified)

        # 分析新增的三阶编码
        for third_cat in modified_standard:
            if third_cat not in original_standard:
                modifications["added"][third_cat] = modified_standard[third_cat]
                modifications["summary"]["added_codes"] += self._count_codes_in_category(modified_standard[third_cat])

        # 分析删除的三阶编码
        for third_cat in original_standard:
            if third_cat not in modified_standard:
                modifications["deleted"][third_cat] = original_standard[third_cat]
                modifications["summary"]["deleted_codes"] += self._count_codes_in_category(original_standard[third_cat])

        # 分析修改的三阶编码
        for third_cat in modified_standard:
            if third_cat in original_standard:
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

        # 检查是否有变化
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

        # 分析新增的二阶编码
        for second_cat in modified_second:
            if second_cat not in original_second:
                modifications["added"][second_cat] = modified_second[second_cat]
                modifications["summary"]["added_codes"] += len(modified_second[second_cat])

        # 分析删除的二阶编码
        for second_cat in original_second:
            if second_cat not in modified_second:
                modifications["deleted"][second_cat] = original_second[second_cat]
                modifications["summary"]["deleted_codes"] += len(original_second[second_cat])

        # 分析修改的二阶编码
        for second_cat in modified_second:
            if second_cat in original_second:
                # 分析一阶编码的变化
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

        # 检查是否有变化
        total_changes = (modifications["summary"]["added_codes"] +
                         modifications["summary"]["modified_codes"] +
                         modifications["summary"]["deleted_codes"])
        modifications["has_changes"] = total_changes > 0

        return modifications

    def _analyze_first_level_modifications(self, original_first: List[str],
                                           modified_first: List[str],
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

        # 转换为集合进行比较
        original_set = set(original_first)
        modified_set = set(modified_first)

        # 分析新增的一阶编码
        added_codes = modified_set - original_set
        if added_codes:
            modifications["added"] = list(added_codes)
            modifications["summary"]["added_codes"] = len(added_codes)

        # 分析删除的一阶编码
        deleted_codes = original_set - modified_set
        if deleted_codes:
            modifications["deleted"] = list(deleted_codes)
            modifications["summary"]["deleted_codes"] = len(deleted_codes)

        # 检查是否有变化
        total_changes = len(added_codes) + len(deleted_codes)
        modifications["has_changes"] = total_changes > 0

        return modifications

    def _merge_modifications(self, original: Dict[str, Any], modifications: Dict[str, Any]) -> Dict[str, Any]:
        """合并修改到原始标准答案"""
        merged = original.copy()

        # 处理新增的三阶编码
        for third_cat, second_cats in modifications["added"].items():
            merged[third_cat] = second_cats

        # 处理删除的三阶编码
        for third_cat in modifications["deleted"]:
            if third_cat in merged:
                del merged[third_cat]

        # 处理修改的三阶编码
        for third_cat, third_modifications in modifications["modified"].items():
            if third_cat in merged:
                # 处理新增的二阶编码
                for second_cat, first_codes in third_modifications["added"].items():
                    merged[third_cat][second_cat] = first_codes

                # 处理删除的二阶编码
                for second_cat in third_modifications["deleted"]:
                    if second_cat in merged[third_cat]:
                        del merged[third_cat][second_cat]

                # 处理修改的二阶编码
                for second_cat, second_modifications in third_modifications["modified"].items():
                    if second_cat in merged[third_cat]:
                        # 处理新增的一阶编码
                        for first_code in second_modifications["added"]:
                            if first_code not in merged[third_cat][second_cat]:
                                merged[third_cat][second_cat].append(first_code)

                        # 处理删除的一阶编码
                        for first_code in second_modifications["deleted"]:
                            if first_code in merged[third_cat][second_cat]:
                                merged[third_cat][second_cat].remove(first_code)

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
                file_path = os.path.join(self.modifications_dir, file)
                with open(file_path, 'r', encoding='utf-8') as f:
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
                    if isinstance(content, dict):
                        clean_content = self._clean_first_level_content(content.get('content', ''))
                    else:
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
        """提取训练数据"""
        training_data = []
        for third_cat, second_cats in structured_codes.items():
            for second_cat, first_contents in second_cats.items():
                for content in first_contents:
                    if isinstance(content, dict):
                        text_content = content.get('content', '')
                    else:
                        text_content = str(content)

                    if text_content.strip():
                        training_data.append({
                            "text": text_content.strip(),
                            "third_category": third_cat,
                            "second_category": second_cat,
                            "full_category": f"{third_cat} > {second_cat}"
                        })
        return training_data

    def _create_backup(self, version_id: str, data: Dict[str, Any]):
        """创建备份"""
        backup_file = os.path.join(self.backup_dir, f"{version_id}.json")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_version_history(self):
        """保存版本历史"""
        history_file = os.path.join(self.standard_answers_dir, "version_history.json")
        with open(history_file, 'w', encoding='utf-8') as f:
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
        history_file = os.path.join(self.standard_answers_dir, "version_history.json")
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                self.version_history = json.load(f)

    def load_answers(self, filename: str) -> bool:
        """加载指定标准答案"""
        try:
            # 检查是否需要添加 .json 扩展名
            if not filename.endswith('.json'):
                filename_json = filename + '.json'
                file_path_json = os.path.join(self.standard_answers_dir, filename_json)
                if os.path.exists(file_path_json):
                    filename = filename_json
            
            file_path = os.path.join(self.standard_answers_dir, filename)
            
            # 打印路径信息用于调试
            print(f"StandardAnswerManager 检查文件路径: {file_path}")
            print(f"文件是否存在: {os.path.exists(file_path)}")
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                logger.error(f"标准答案文件不存在: {file_path}")
                return False
            
            # 检查文件大小
            if os.path.getsize(file_path) == 0:
                logger.error(f"标准答案文件为空: {file_path}")
                return False
            
            # 尝试打开和解析文件
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
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