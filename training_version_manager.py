import csv
import json
import logging
import os
import shutil
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import Config

logger = logging.getLogger(__name__)


class TrainingVersionManager:
    """训练版本管理器"""

    VERSIONS_DIR_NAME = "versions"
    VERSION_METADATA_FILE = "version_metadata.json"
    VERSIONS_INDEX_FILE = "versions_index.json"

    def __init__(self, trained_models_dir: Optional[str] = None):
        """
        初始化训练版本管理器

        Args:
            trained_models_dir: 训练模型目录，如果为None则使用Config中的配置
        """
        self.trained_models_dir = trained_models_dir or Config.TRAINED_MODELS_DIR
        self.versions_dir = os.path.join(self.trained_models_dir, self.VERSIONS_DIR_NAME)
        self.versions_index_path = os.path.join(self.versions_dir, self.VERSIONS_INDEX_FILE)

        self._ensure_directories()
        self._load_versions_index()

        logger.info(f"TrainingVersionManager 初始化完成，版本目录: {self.versions_dir}")

    def _ensure_directories(self) -> None:
        """确保必要的目录存在"""
        os.makedirs(self.trained_models_dir, exist_ok=True)
        os.makedirs(self.versions_dir, exist_ok=True)

    def _load_versions_index(self) -> None:
        """加载版本索引"""
        self.versions_index: Dict[str, Dict[str, Any]] = {}
        if os.path.exists(self.versions_index_path):
            try:
                with open(self.versions_index_path, 'r', encoding='utf-8') as f:
                    self.versions_index = json.load(f)
                logger.info(f"已加载版本索引: {len(self.versions_index)} 个版本")
            except Exception as e:
                logger.warning(f"加载版本索引失败: {e}")
                self.versions_index = {}

    def _save_versions_index(self) -> bool:
        """保存版本索引"""
        try:
            with open(self.versions_index_path, 'w', encoding='utf-8') as f:
                json.dump(self.versions_index, f, ensure_ascii=False, indent=2)
            logger.debug("版本索引已保存")
            return True
        except Exception as e:
            logger.error(f"保存版本索引失败: {e}")
            return False

    def _generate_version_id(self) -> str:
        """
        生成唯一的版本ID

        Returns:
            版本ID字符串
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        return f"v_{timestamp}_{unique_id}"

    def _get_version_dir(self, version_id: str) -> str:
        """
        获取版本目录路径

        Args:
            version_id: 版本ID

        Returns:
            版本目录路径
        """
        return os.path.join(self.versions_dir, version_id)

    def _get_version_metadata_path(self, version_id: str) -> str:
        """
        获取版本元数据文件路径

        Args:
            version_id: 版本ID

        Returns:
            元数据文件路径
        """
        return os.path.join(self._get_version_dir(version_id), self.VERSION_METADATA_FILE)

    def create_version(self, model_dir: str, metadata: Dict[str, Any]) -> str:
        """
        创建新版本

        Args:
            model_dir: 模型目录路径
            metadata: 版本元数据，包含以下字段：
                - model_type: 模型类型（bert_finetune/classifier）
                - sample_count: 训练样本数
                - accuracy: 准确率
                - training_params: 训练参数
                - data_version: 数据版本
                - parent_version: 父版本ID（用于增量训练）

        Returns:
            新创建的版本ID
        """
        try:
            if not os.path.exists(model_dir):
                raise ValueError(f"模型目录不存在: {model_dir}")

            version_id = self._generate_version_id()
            version_dir = self._get_version_dir(version_id)
            os.makedirs(version_dir, exist_ok=True)

            model_copy_dir = os.path.join(version_dir, "model")
            shutil.copytree(model_dir, model_copy_dir, dirs_exist_ok=True)
            logger.info(f"模型文件已复制到: {model_copy_dir}")

            version_metadata = {
                "version_id": version_id,
                "created_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "model_type": metadata.get("model_type", "unknown"),
                "sample_count": metadata.get("sample_count", 0),
                "accuracy": metadata.get("accuracy", None),
                "training_params": metadata.get("training_params", {}),
                "data_version": metadata.get("data_version", ""),
                "parent_version": metadata.get("parent_version", None),
                "source_model_dir": model_dir,
                "model_path": model_copy_dir
            }

            metadata_path = self._get_version_metadata_path(version_id)
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(version_metadata, f, ensure_ascii=False, indent=2)
            logger.info(f"版本元数据已保存: {metadata_path}")

            self.versions_index[version_id] = {
                "version_id": version_id,
                "created_time": version_metadata["created_time"],
                "model_type": version_metadata["model_type"],
                "sample_count": version_metadata["sample_count"],
                "accuracy": version_metadata["accuracy"],
                "parent_version": version_metadata["parent_version"]
            }
            self._save_versions_index()

            logger.info(f"版本创建成功: {version_id}")
            return version_id

        except Exception as e:
            logger.error(f"创建版本失败: {e}")
            raise

    def get_version(self, version_id: str) -> Dict[str, Any]:
        """
        获取指定版本的详细信息

        Args:
            version_id: 版本ID

        Returns:
            版本元数据字典
        """
        try:
            if version_id not in self.versions_index:
                logger.warning(f"版本不存在: {version_id}")
                return {}

            metadata_path = self._get_version_metadata_path(version_id)
            if not os.path.exists(metadata_path):
                logger.warning(f"版本元数据文件不存在: {metadata_path}")
                return {}

            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            logger.debug(f"获取版本信息: {version_id}")
            return metadata

        except Exception as e:
            logger.error(f"获取版本信息失败: {e}")
            return {}

    def list_versions(self) -> List[Dict[str, Any]]:
        """
        列出所有版本

        Returns:
            版本列表，按创建时间降序排列
        """
        try:
            versions = []
            for version_id, index_info in self.versions_index.items():
                version_info = {
                    "version_id": version_id,
                    "created_time": index_info.get("created_time", ""),
                    "model_type": index_info.get("model_type", "unknown"),
                    "sample_count": index_info.get("sample_count", 0),
                    "accuracy": index_info.get("accuracy", None),
                    "parent_version": index_info.get("parent_version", None)
                }
                versions.append(version_info)

            versions.sort(key=lambda x: x.get("created_time", ""), reverse=True)

            logger.debug(f"列出所有版本: {len(versions)} 个")
            return versions

        except Exception as e:
            logger.error(f"列出版本失败: {e}")
            return []

    def rollback_to_version(self, version_id: str) -> bool:
        """
        回滚到指定版本

        Args:
            version_id: 目标版本ID

        Returns:
            回滚是否成功
        """
        try:
            if version_id not in self.versions_index:
                logger.error(f"版本不存在: {version_id}")
                return False

            version_metadata = self.get_version(version_id)
            if not version_metadata:
                logger.error(f"无法获取版本元数据: {version_id}")
                return False

            model_path = version_metadata.get("model_path", "")
            if not model_path or not os.path.exists(model_path):
                logger.error(f"版本模型路径不存在: {model_path}")
                return False

            current_model_dir = self.trained_models_dir

            backup_dir = os.path.join(
                self.trained_models_dir,
                f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            if os.path.exists(current_model_dir):
                for item in os.listdir(current_model_dir):
                    item_path = os.path.join(current_model_dir, item)
                    if item != self.VERSIONS_DIR_NAME:
                        if os.path.isdir(item_path):
                            os.makedirs(backup_dir, exist_ok=True)
                            shutil.move(item_path, os.path.join(backup_dir, item))
                        else:
                            os.makedirs(backup_dir, exist_ok=True)
                            shutil.move(item_path, os.path.join(backup_dir, item))
                logger.info(f"当前模型已备份到: {backup_dir}")

            for item in os.listdir(model_path):
                src_path = os.path.join(model_path, item)
                dst_path = os.path.join(current_model_dir, item)
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(src_path, dst_path)

            logger.info(f"已回滚到版本: {version_id}")
            return True

        except Exception as e:
            logger.error(f"回滚版本失败: {e}")
            return False

    def delete_version(self, version_id: str) -> bool:
        """
        删除指定版本

        Args:
            version_id: 要删除的版本ID

        Returns:
            删除是否成功
        """
        try:
            if version_id not in self.versions_index:
                logger.warning(f"版本不存在: {version_id}")
                return False

            for vid, info in self.versions_index.items():
                if info.get("parent_version") == version_id:
                    logger.warning(f"版本 {version_id} 有子版本 {vid}，无法删除")
                    return False

            version_dir = self._get_version_dir(version_id)
            if os.path.exists(version_dir):
                shutil.rmtree(version_dir)
                logger.info(f"版本目录已删除: {version_dir}")

            if version_id in self.versions_index:
                del self.versions_index[version_id]
                self._save_versions_index()

            logger.info(f"版本已删除: {version_id}")
            return True

        except Exception as e:
            logger.error(f"删除版本失败: {e}")
            return False

    def get_latest_version(self) -> Dict[str, Any]:
        """
        获取最新版本

        Returns:
            最新版本的元数据，如果没有版本则返回空字典
        """
        try:
            versions = self.list_versions()
            if not versions:
                logger.info("没有可用版本")
                return {}

            latest_version_id = versions[0]["version_id"]
            return self.get_version(latest_version_id)

        except Exception as e:
            logger.error(f"获取最新版本失败: {e}")
            return {}

    def generate_history_report(self) -> str:
        """
        生成训练历史报告

        Returns:
            格式化的历史报告字符串
        """
        try:
            versions = self.list_versions()
            if not versions:
                return "暂无训练版本记录"

            report_lines = []
            report_lines.append("=" * 60)
            report_lines.append("训练版本历史报告")
            report_lines.append("=" * 60)
            report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append(f"总版本数: {len(versions)}")
            report_lines.append("")

            for i, version in enumerate(versions, 1):
                report_lines.append("-" * 40)
                report_lines.append(f"版本 #{i}")
                report_lines.append(f"  版本ID: {version['version_id']}")
                report_lines.append(f"  创建时间: {version['created_time']}")
                report_lines.append(f"  模型类型: {version['model_type']}")
                report_lines.append(f"  训练样本数: {version['sample_count']}")

                accuracy = version.get('accuracy')
                if accuracy is not None:
                    report_lines.append(f"  准确率: {accuracy:.4f}")

                parent = version.get('parent_version')
                if parent:
                    report_lines.append(f"  父版本: {parent}")

                report_lines.append("")

            report_lines.append("=" * 60)

            initial_count = sum(1 for v in versions if not v.get('parent_version'))
            incremental_count = sum(1 for v in versions if v.get('parent_version'))
            total_samples = sum(v.get('sample_count', 0) for v in versions)

            report_lines.append("统计摘要:")
            report_lines.append(f"  初始训练次数: {initial_count}")
            report_lines.append(f"  增量训练次数: {incremental_count}")
            report_lines.append(f"  总训练样本数: {total_samples}")

            accuracies = [v.get('accuracy') for v in versions if v.get('accuracy') is not None]
            if accuracies:
                avg_accuracy = sum(accuracies) / len(accuracies)
                max_accuracy = max(accuracies)
                min_accuracy = min(accuracies)
                report_lines.append(f"  平均准确率: {avg_accuracy:.4f}")
                report_lines.append(f"  最高准确率: {max_accuracy:.4f}")
                report_lines.append(f"  最低准确率: {min_accuracy:.4f}")

            report_lines.append("=" * 60)

            report = "\n".join(report_lines)
            logger.info("历史报告已生成")
            return report

        except Exception as e:
            logger.error(f"生成历史报告失败: {e}")
            return f"生成报告失败: {str(e)}"

    def export_history_to_csv(self, output_file: str) -> bool:
        """
        导出训练历史到CSV文件

        Args:
            output_file: 输出CSV文件路径

        Returns:
            导出是否成功
        """
        try:
            versions = self.list_versions()
            if not versions:
                logger.warning("没有版本记录可导出")
                return False

            fieldnames = [
                "version_id",
                "created_time",
                "model_type",
                "sample_count",
                "accuracy",
                "parent_version"
            ]

            with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for version in versions:
                    row = {
                        "version_id": version.get("version_id", ""),
                        "created_time": version.get("created_time", ""),
                        "model_type": version.get("model_type", ""),
                        "sample_count": version.get("sample_count", 0),
                        "accuracy": version.get("accuracy", ""),
                        "parent_version": version.get("parent_version", "")
                    }
                    writer.writerow(row)

            logger.info(f"训练历史已导出到: {output_file}")
            return True

        except Exception as e:
            logger.error(f"导出历史到CSV失败: {e}")
            return False

    def get_version_chain(self, version_id: str) -> List[str]:
        """
        获取版本的完整链路（从根版本到指定版本）

        Args:
            version_id: 版本ID

        Returns:
            版本链路列表
        """
        try:
            chain = []
            current_id = version_id

            while current_id:
                version_metadata = self.get_version(current_id)
                if not version_metadata:
                    break

                chain.insert(0, current_id)
                current_id = version_metadata.get("parent_version")

            return chain

        except Exception as e:
            logger.error(f"获取版本链路失败: {e}")
            return []

    def get_children_versions(self, version_id: str) -> List[str]:
        """
        获取指定版本的所有子版本

        Args:
            version_id: 版本ID

        Returns:
            子版本ID列表
        """
        try:
            children = []
            for vid, info in self.versions_index.items():
                if info.get("parent_version") == version_id:
                    children.append(vid)

            return children

        except Exception as e:
            logger.error(f"获取子版本失败: {e}")
            return []

    def compare_versions(self, version_id1: str, version_id2: str) -> Dict[str, Any]:
        """
        比较两个版本

        Args:
            version_id1: 第一个版本ID
            version_id2: 第二个版本ID

        Returns:
            比较结果字典
        """
        try:
            v1 = self.get_version(version_id1)
            v2 = self.get_version(version_id2)

            if not v1 or not v2:
                return {"error": "一个或两个版本不存在"}

            comparison = {
                "version1": {
                    "version_id": version_id1,
                    "created_time": v1.get("created_time", ""),
                    "sample_count": v1.get("sample_count", 0),
                    "accuracy": v1.get("accuracy")
                },
                "version2": {
                    "version_id": version_id2,
                    "created_time": v2.get("created_time", ""),
                    "sample_count": v2.get("sample_count", 0),
                    "accuracy": v2.get("accuracy")
                },
                "differences": {}
            }

            if v1.get("sample_count") != v2.get("sample_count"):
                comparison["differences"]["sample_count"] = {
                    "version1": v1.get("sample_count", 0),
                    "version2": v2.get("sample_count", 0),
                    "delta": v2.get("sample_count", 0) - v1.get("sample_count", 0)
                }

            acc1 = v1.get("accuracy")
            acc2 = v2.get("accuracy")
            if acc1 is not None and acc2 is not None and acc1 != acc2:
                comparison["differences"]["accuracy"] = {
                    "version1": acc1,
                    "version2": acc2,
                    "delta": acc2 - acc1
                }

            return comparison

        except Exception as e:
            logger.error(f"比较版本失败: {e}")
            return {"error": str(e)}
