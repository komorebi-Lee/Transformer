import json
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from standard_answer_manager import StandardAnswerManager
from coding_library_manager import CodingLibraryManager
from semantic_matcher import SemanticMatcher

logger = logging.getLogger(__name__)

# 尝试导入psutil库用于内存监控
psutil = None
try:
    import psutil
    logger.info("psutil 库加载成功")
except ImportError as e:
    logger.warning(f"psutil 库加载失败: {e}")
    logger.warning("内存监控功能将不可用")


class EnhancedManualCoding:
    """人工编码增强功能"""

    def __init__(self):
        """
        初始化人工编码增强功能
        """
        self.standard_answer_manager = StandardAnswerManager()
        self.coding_library_manager = CodingLibraryManager()
        self.semantic_matcher = SemanticMatcher()
        self.processed_codes = set()  # 用于跟踪已处理的编码，避免重复添加

    def process_standard_answer(self, standard_answer: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理标准答案，提取并更新编码库

        Args:
            standard_answer: 标准答案数据

        Returns:
            处理结果，包含新增和更新的编码信息
        """
        try:
            logger.info("开始处理标准答案，提取编码元素")
            # 记录处理前内存使用
            self._log_memory_usage("处理前")

            # 清空已处理编码集合，确保每次训练都是从干净的状态开始
            self.processed_codes.clear()

            # 优先从training_data获取编码信息
            training_data = standard_answer.get("training_data", [])
            structured_codes = {}
            
            if training_data:
                logger.info("从training_data提取编码信息")
                # 构建结构化编码数据（分批处理）
                batch_size = 1000  # 每批处理的数据量
                for i in range(0, len(training_data), batch_size):
                    batch_data = training_data[i:i + batch_size]
                    for item in batch_data:
                        if isinstance(item, dict):
                            third_level = item.get("target_third_category")
                            second_level = item.get("target_second_category")
                            if third_level and second_level:
                                # 清除三阶编码编号（如B0X）
                                cleaned_third_level = self._clean_code_name(third_level)
                                # 清除二阶编码编号（如C0X）
                                cleaned_second_level = self._clean_code_name(second_level)
                                if cleaned_third_level and cleaned_second_level:
                                    if cleaned_third_level not in structured_codes:
                                        structured_codes[cleaned_third_level] = {}
                                    if cleaned_second_level not in structured_codes[cleaned_third_level]:
                                        structured_codes[cleaned_third_level][cleaned_second_level] = []
                                    # 添加一阶编码内容
                                    target_abstract = item.get("target_abstract", "")
                                    if target_abstract:
                                        structured_codes[cleaned_third_level][cleaned_second_level].append(target_abstract)
                    logger.info(f"处理第 {i//batch_size + 1} 批训练数据完成")
                    # 记录内存使用情况
                    self._log_memory_usage(f"处理第 {i//batch_size + 1} 批训练数据后")
            else:
                # 回退到structured_codes
                structured_codes = standard_answer.get("structured_codes", {})
                if not structured_codes:
                    logger.warning("标准答案中没有结构化编码")
                    return {"success": False, "message": "没有结构化编码可处理"}
                # 清理结构化编码中的编号
                cleaned_structured_codes = {}
                for third_level, second_levels in structured_codes.items():
                    cleaned_third_level = self._clean_code_name(third_level)
                    if cleaned_third_level:
                        cleaned_structured_codes[cleaned_third_level] = {}
                        for second_level, first_levels in second_levels.items():
                            cleaned_second_level = self._clean_code_name(second_level)
                            if cleaned_second_level:
                                cleaned_structured_codes[cleaned_third_level][cleaned_second_level] = first_levels
                structured_codes = cleaned_structured_codes

            # 提取并处理所有二阶和三阶编码
            processing_result = {
                "added_second_level_codes": [],
                "updated_second_level_codes": [],
                "added_third_level_codes": [],
                "updated_third_level_codes": [],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # 处理三阶编码（分批处理）
            third_level_items = list(structured_codes.items())
            batch_size = 100  # 每批处理的三阶编码数量
            for i in range(0, len(third_level_items), batch_size):
                batch_items = third_level_items[i:i + batch_size]
                for third_level_name, second_level_codes in batch_items:
                    # 检查是否已经处理过这个三阶编码
                    third_level_key = f"third:{third_level_name}"
                    if third_level_key not in self.processed_codes:
                        # 处理三阶编码
                        third_level_result = self._process_third_level_code(third_level_name, second_level_codes)
                        if third_level_result["created"]:
                            processing_result["added_third_level_codes"].append(third_level_name)
                        elif third_level_result["updated"]:
                            processing_result["updated_third_level_codes"].append(third_level_name)
                        # 标记为已处理
                        self.processed_codes.add(third_level_key)

                    # 处理二阶编码
                    for second_level_name, first_level_codes in second_level_codes.items():
                        # 检查是否已经处理过这个二阶编码
                        second_level_key = f"second:{third_level_name}:{second_level_name}"
                        if second_level_key not in self.processed_codes:
                            second_level_result = self._process_second_level_code(
                                second_level_name, first_level_codes, third_level_name
                            )
                            if second_level_result["created"]:
                                processing_result["added_second_level_codes"].append(second_level_name)
                            elif second_level_result["updated"]:
                                processing_result["updated_second_level_codes"].append(second_level_name)
                            # 标记为已处理
                            self.processed_codes.add(second_level_key)
                logger.info(f"处理第 {i//batch_size + 1} 批编码数据完成")
                # 记录内存使用情况
                self._log_memory_usage(f"处理第 {i//batch_size + 1} 批编码数据后")

            # 记录处理完成后内存使用
            self._log_memory_usage("处理完成后")
            logger.info(f"编码处理完成: 新增三阶编码 {len(processing_result['added_third_level_codes'])} 个, "
                        f"更新三阶编码 {len(processing_result['updated_third_level_codes'])} 个, "
                        f"新增二阶编码 {len(processing_result['added_second_level_codes'])} 个, "
                        f"更新二阶编码 {len(processing_result['updated_second_level_codes'])} 个")

            return {
                "success": True,
                "result": processing_result,
                "message": "编码处理完成"
            }

        except Exception as e:
            logger.error(f"处理标准答案失败: {e}")
            return {"success": False, "message": f"处理失败: {str(e)}"}

    def _process_third_level_code(self, third_level_name: str, second_level_codes: Dict[str, Any]) -> Dict[str, bool]:
        """
        处理三阶编码

        Args:
            third_level_name: 三阶编码名称
            second_level_codes: 二阶编码字典

        Returns:
            处理结果，包含是否创建或更新
        """
        try:
            # 检查编码库中是否已存在该三阶编码
            existing_third_level = None
            for code in self.coding_library_manager.get_all_third_level_codes():
                if code.get("name") == third_level_name:
                    existing_third_level = code
                    break

            if existing_third_level:
                # 更新三阶编码的向量表示
                self._update_third_level_vector(existing_third_level, second_level_codes)
                logger.info(f"更新三阶编码: {third_level_name}")
                return {"created": False, "updated": True}
            else:
                # 创建新的三阶编码
                new_third_level_id = self._generate_third_level_id()
                description = self._generate_third_level_description(second_level_codes)
                success = self.coding_library_manager.add_third_level_code(
                    new_third_level_id, third_level_name, description
                )
                if success:
                    # 为新三阶编码设置向量表示
                    self._update_third_level_vector(
                        {"name": third_level_name, "description": description},
                        second_level_codes
                    )
                    logger.info(f"新增三阶编码: {third_level_name}")
                    return {"created": True, "updated": False}
                else:
                    logger.error(f"创建三阶编码失败: {third_level_name}")
                    return {"created": False, "updated": False}

        except Exception as e:
            logger.error(f"处理三阶编码失败 {third_level_name}: {e}")
            return {"created": False, "updated": False}

    def _process_second_level_code(self, second_level_name: str, first_level_codes: List[Any], third_level_name: str) -> Dict[str, bool]:
        """
        处理二阶编码

        Args:
            second_level_name: 二阶编码名称
            first_level_codes: 一阶编码列表
            third_level_name: 所属三阶编码名称

        Returns:
            处理结果，包含是否创建或更新
        """
        try:
            # 检查编码库中是否已存在该二阶编码
            existing_second_level = None
            for code in self.coding_library_manager.get_all_second_level_codes():
                if code.get("name") == second_level_name:
                    existing_second_level = code
                    break

            if existing_second_level:
                # 更新二阶编码的向量表示
                self._update_second_level_vector(existing_second_level, first_level_codes)
                logger.info(f"更新二阶编码: {second_level_name}")
                return {"created": False, "updated": True}
            else:
                # 创建新的二阶编码
                third_level_id = self._get_third_level_id(third_level_name)
                if third_level_id is None:
                    logger.error(f"找不到三阶编码ID: {third_level_name}")
                    return {"created": False, "updated": False}

                new_second_level_id = self._generate_second_level_id(third_level_id)
                description = self._generate_second_level_description(first_level_codes)
                success = self.coding_library_manager.add_second_level_code(
                    third_level_id, new_second_level_id, second_level_name, description
                )
                if success:
                    # 为新二阶编码设置向量表示
                    self._update_second_level_vector(
                        {"name": second_level_name, "description": description},
                        first_level_codes
                    )
                    logger.info(f"新增二阶编码: {second_level_name}")
                    return {"created": True, "updated": False}
                else:
                    logger.error(f"创建二阶编码失败: {second_level_name}")
                    return {"created": False, "updated": False}

        except Exception as e:
            logger.error(f"处理二阶编码失败 {second_level_name}: {e}")
            return {"created": False, "updated": False}

    def _update_second_level_vector(self, second_level_code: Dict[str, Any], first_level_codes: List[Any]):
        """
        更新二阶编码的向量表示（增量更新）

        Args:
            second_level_code: 二阶编码信息
            first_level_codes: 一阶编码列表
        """
        try:
            # 提取一阶编码文本
            first_level_texts = []
            for code in first_level_codes:
                if isinstance(code, dict):
                    text = code.get("content", code.get("name", ""))
                else:
                    text = str(code)
                if text.strip():
                    first_level_texts.append(text)

            if first_level_texts:
                # 计算一阶编码的平均嵌入
                embeddings = []
                for text in first_level_texts:
                    embedding = self.semantic_matcher.get_embedding(text)
                    if embedding is not None:
                        embeddings.append(embedding)

                if embeddings:
                    # 计算新向量
                    new_embedding = sum(embeddings) / len(embeddings)
                    
                    # 检查是否存在历史向量
                    combined_text = f"{second_level_code.get('name', '')} {second_level_code.get('description', '')}"
                    if combined_text in self.semantic_matcher.embeddings_cache:
                        # 增量更新：结合历史向量和新向量
                        historical_embedding = self.semantic_matcher.embeddings_cache[combined_text]
                        # 使用加权平均，给新向量更高权重
                        updated_embedding = (historical_embedding * 0.7) + (new_embedding * 0.3)
                        self.semantic_matcher.embeddings_cache[combined_text] = updated_embedding
                        logger.debug(f"增量更新二阶编码向量: {second_level_code.get('name')}")
                    else:
                        # 新编码，直接使用新向量
                        self.semantic_matcher.embeddings_cache[combined_text] = new_embedding
                        logger.debug(f"新增二阶编码向量: {second_level_code.get('name')}")
                else:
                    logger.warning(f"无法计算二阶编码 {second_level_code.get('name')} 的向量表示")

        except Exception as e:
            logger.error(f"更新二阶编码向量失败: {e}")

    def _update_third_level_vector(self, third_level_code: Dict[str, Any], second_level_codes: Dict[str, Any]):
        """
        更新三阶编码的向量表示（增量更新）

        Args:
            third_level_code: 三阶编码信息
            second_level_codes: 二阶编码字典
        """
        try:
            # 提取二阶编码文本
            second_level_texts = []
            for second_level_name in second_level_codes.keys():
                second_level_texts.append(second_level_name)

            if second_level_texts:
                # 计算二阶编码的平均嵌入
                embeddings = []
                for text in second_level_texts:
                    embedding = self.semantic_matcher.get_embedding(text)
                    if embedding is not None:
                        embeddings.append(embedding)

                if embeddings:
                    # 计算新向量
                    new_embedding = sum(embeddings) / len(embeddings)
                    
                    # 检查是否存在历史向量
                    combined_text = f"{third_level_code.get('name', '')} {third_level_code.get('description', '')}"
                    if combined_text in self.semantic_matcher.embeddings_cache:
                        # 增量更新：结合历史向量和新向量
                        historical_embedding = self.semantic_matcher.embeddings_cache[combined_text]
                        # 使用加权平均，给新向量更高权重
                        updated_embedding = (historical_embedding * 0.7) + (new_embedding * 0.3)
                        self.semantic_matcher.embeddings_cache[combined_text] = updated_embedding
                        logger.debug(f"增量更新三阶编码向量: {third_level_code.get('name')}")
                    else:
                        # 新编码，直接使用新向量
                        self.semantic_matcher.embeddings_cache[combined_text] = new_embedding
                        logger.debug(f"新增三阶编码向量: {third_level_code.get('name')}")
                else:
                    logger.warning(f"无法计算三阶编码 {third_level_code.get('name')} 的向量表示")

        except Exception as e:
            logger.error(f"更新三阶编码向量失败: {e}")

    def _generate_third_level_id(self) -> int:
        """
        生成新的三阶编码ID

        Returns:
            新的三阶编码ID
        """
        existing_ids = [code.get("id") for code in self.coding_library_manager.get_all_third_level_codes()]
        if existing_ids:
            return max(existing_ids) + 1
        return 1

    def _generate_second_level_id(self, third_level_id: int) -> str:
        """
        生成新的二阶编码ID，格式为X.X

        Args:
            third_level_id: 所属三阶编码ID

        Returns:
            新的二阶编码ID，格式为X.X
        """
        # 获取当前三阶编码下的所有二阶编码
        second_level_codes = []
        for code in self.coding_library_manager.get_all_second_level_codes():
            if code.get('third_level_id') == third_level_id:
                second_level_codes.append(code)
        
        # 计算最大的二阶编码序号
        max_seq = 0
        for code in second_level_codes:
            code_id = code.get('id')
            if code_id and '.' in code_id:
                try:
                    seq = int(code_id.split('.')[1])
                    if seq > max_seq:
                        max_seq = seq
                except (ValueError, IndexError):
                    pass
        
        # 生成新的二阶编码ID
        new_seq = max_seq + 1
        return f"{third_level_id}.{new_seq}"

    def _get_third_level_id(self, third_level_name: str) -> Optional[int]:
        """
        根据三阶编码名称获取ID

        Args:
            third_level_name: 三阶编码名称

        Returns:
            三阶编码ID
        """
        for code in self.coding_library_manager.get_all_third_level_codes():
            if code.get("name") == third_level_name:
                return code.get("id")
        return None

    def _generate_second_level_description(self, first_level_codes: List[Any]) -> str:
        """
        根据一阶编码生成二阶编码描述

        Args:
            first_level_codes: 一阶编码列表

        Returns:
            二阶编码描述
        """
        try:
            # 提取一阶编码的关键词
            keywords = []
            for code in first_level_codes:
                if isinstance(code, dict):
                    text = code.get("content", code.get("name", ""))
                else:
                    text = str(code)
                if text.strip():
                    # 简单提取关键词（这里可以使用更复杂的NLP方法）
                    words = text.split()
                    keywords.extend([word for word in words if len(word) > 1])

            # 去重并限制长度
            unique_keywords = list(set(keywords))[:10]
            if unique_keywords:
                return "包含：" + "、".join(unique_keywords)
            else:
                return "暂无详细描述"

        except Exception as e:
            logger.error(f"生成二阶编码描述失败: {e}")
            return "暂无详细描述"

    def _generate_third_level_description(self, second_level_codes: Dict[str, Any]) -> str:
        """
        根据二阶编码生成三阶编码描述

        Args:
            second_level_codes: 二阶编码字典

        Returns:
            三阶编码描述
        """
        try:
            second_level_names = list(second_level_codes.keys())
            if second_level_names:
                return "包含：" + "、".join(second_level_names[:5])
            else:
                return "暂无详细描述"

        except Exception as e:
            logger.error(f"生成三阶编码描述失败: {e}")
            return "暂无详细描述"

    def _clean_code_name(self, code_name: str) -> str:
        """
        清除编码名称中的编号（如B0X，C0X）

        Args:
            code_name: 编码名称

        Returns:
            清除编号后的编码名称
        """
        import re
        try:
            # 匹配并移除编码前的编号，如 B01、C02 等
            cleaned_name = re.sub(r'^[A-Z]\d+\s*', '', code_name)
            # 移除可能的空格和特殊字符
            cleaned_name = cleaned_name.strip()
            return cleaned_name
        except Exception as e:
            logger.error(f"清理编码名称失败: {e}")
            return code_name

    def _get_memory_usage(self) -> Dict[str, float]:
        """
        获取当前内存使用情况

        Returns:
            内存使用情况字典
        """
        if psutil:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            return {
                'rss': memory_info.rss / 1024 / 1024,  # MB
                'vms': memory_info.vms / 1024 / 1024,  # MB
                'percent': process.memory_percent()
            }
        return {}

    def _log_memory_usage(self, message: str):
        """
        记录内存使用情况

        Args:
            message: 日志消息
        """
        memory_usage = self._get_memory_usage()
        if memory_usage:
            logger.info(f"{message} - 内存使用: RSS={memory_usage['rss']:.2f}MB, 百分比={memory_usage['percent']:.2f}%")

    def integrate_with_model_training(self, training_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        与模型训练流程集成

        Args:
            training_data: 训练数据

        Returns:
            集成结果，包含编码处理结果
        """
        try:
            logger.info("开始与模型训练流程集成")

            # 处理训练数据中的编码信息
            processing_result = self.process_standard_answer(training_data)
            if processing_result["success"]:
                logger.info("编码处理成功，继续模型训练")
            else:
                logger.warning(f"编码处理失败: {processing_result['message']}")

            logger.info("与模型训练流程集成完成")
            return {
                "success": True, 
                "message": "集成成功",
                "processing_result": processing_result.get("result", {})
            }

        except Exception as e:
            logger.error(f"与模型训练流程集成失败: {e}")
            return {"success": False, "message": f"集成失败: {str(e)}"}
