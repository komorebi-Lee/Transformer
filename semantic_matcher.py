import torch
import numpy as np
import os
from typing import List, Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

SentenceTransformer = None
try:
    from sentence_transformers import SentenceTransformer
    logger.info("sentence-transformers 库加载成功")
except ImportError as e:
    logger.warning(f"sentence-transformers 库加载失败: {e}")
    logger.warning("语义匹配功能将不可用，但人工编码增强功能仍可正常工作")


class SemanticMatcher:
    """语义匹配器"""

    def __init__(self, model_name: str = None):
        """
        初始化语义匹配器

        Args:
            model_name: 模型名称或路径
        """
        import os
        from config import Config
        
        # 优先用微调后的 concept_anchor_v6（与 FAISS 锚点共享模型，512-dim）
        if model_name is None:
            _v6 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "trained_models", "concept_anchor_v6")
            if os.path.exists(_v6):
                model_name = _v6
            else:
                model_name = os.path.join(Config.LOCAL_MODELS_DIR, Config.SENTENCE_MODEL_NAME)

        # 使用本地模型路径
        if os.path.isabs(model_name) or model_name.startswith("trained_models"):
            self.model_name = model_name
        else:
            self.model_name = os.path.join(Config.LOCAL_MODELS_DIR, model_name)
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.embeddings_cache: Dict[str, np.ndarray] = {}
        self.code_weights: Dict[str, float] = {}
        self.cache_size_limit = 10000  # 缓存大小限制
        self.batch_size_limit = 1000   # 批处理大小限制

        if SentenceTransformer:
            self.load_model()
        else:
            logger.warning("sentence-transformers 库不可用，跳过模型加载")

    def load_model(self) -> bool:
        """
        加载sentence-transformer模型

        Returns:
            是否加载成功
        """
        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"正在加载sentence-transformer模型: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.model.to(self.device)
            logger.info(f"模型加载成功，使用设备: {self.device}")
            return True

        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            return False

    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        获取文本的嵌入向量

        Args:
            text: 文本内容

        Returns:
            嵌入向量
        """
        try:
            # 检查缓存
            if text in self.embeddings_cache:
                return self.embeddings_cache[text]

            # 检查模型是否可用
            if not self.model:
                logger.warning("模型不可用，无法计算嵌入")
                return None

            # 计算嵌入
            embedding = self.model.encode([text], show_progress_bar=False)[0]

            # 缓存结果
            self.embeddings_cache[text] = embedding
            # 管理缓存大小
            self._manage_cache()

            return embedding

        except Exception as e:
            logger.error(f"计算嵌入失败: {e}")
            return None

    def get_batch_embeddings(self, texts: List[str]) -> Optional[np.ndarray]:
        """
        批量获取文本的嵌入向量

        Args:
            texts: 文本列表

        Returns:
            嵌入向量数组
        """
        try:
            # 检查模型是否可用
            if not self.model:
                logger.warning("模型不可用，无法计算嵌入")
                return None

            # 检查缓存
            uncached_texts = []
            cached_embeddings = {}

            for text in texts:
                if text in self.embeddings_cache:
                    cached_embeddings[text] = self.embeddings_cache[text]
                else:
                    uncached_texts.append(text)

            # 计算未缓存的文本（分批处理）
            if uncached_texts:
                # 分批处理，避免内存溢出
                for i in range(0, len(uncached_texts), self.batch_size_limit):
                    batch_texts = uncached_texts[i:i + self.batch_size_limit]
                    new_embeddings = self.model.encode(batch_texts, show_progress_bar=False)
                    for text, embedding in zip(batch_texts, new_embeddings):
                        self.embeddings_cache[text] = embedding
                        cached_embeddings[text] = embedding
                    # 每批处理后管理缓存
                    self._manage_cache()

            # 按原始顺序返回嵌入
            embeddings = np.array([cached_embeddings[text] for text in texts])
            return embeddings

        except Exception as e:
            logger.error(f"批量计算嵌入失败: {e}")
            return None

    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray, code_id: str = None) -> float:
        """
        计算两个嵌入向量的余弦相似度

        Args:
            embedding1: 第一个嵌入向量
            embedding2: 第二个嵌入向量
            code_id: 二阶编码ID，用于应用权重

        Returns:
            相似度值（-1到1之间）
        """
        try:
            # 计算余弦相似度
            similarity = np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            )
            
            # 应用编码权重
            if code_id and code_id in self.code_weights:
                weight = self.code_weights[code_id]
                # 权重范围调整到0.8-1.2
                adjusted_similarity = similarity * (0.8 + 0.4 * weight)
                return float(adjusted_similarity)
            
            return float(similarity)

        except Exception as e:
            logger.error(f"计算相似度失败: {e}")
            return 0.0

    def match_first_level_to_second_level(
        self, 
        first_level_text: str, 
        second_level_codes: List[Dict[str, Any]],
        top_k: int = 3,
        threshold: float = 0.5
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        将一阶编码匹配到最相似的二阶编码

        Args:
            first_level_text: 一阶编码文本
            second_level_codes: 二阶编码列表
            top_k: 返回前k个最相似的编码
            threshold: 相似度阈值

        Returns:
            匹配结果列表，每个元素包含二阶编码和相似度
        """
        try:
            # 获取一阶编码的嵌入
            first_level_embedding = self.get_embedding(first_level_text)
            if first_level_embedding is None:
                logger.error("一阶编码嵌入计算失败")
                return []

            # 准备二阶编码文本
            second_level_texts = []
            for code in second_level_codes:
                # 组合编码名称和描述以获得更准确的语义
                text = f"{code.get('name', '')} {code.get('description', '')}"
                second_level_texts.append(text)

            # 批量获取二阶编码的嵌入
            second_level_embeddings = self.get_batch_embeddings(second_level_texts)
            if second_level_embeddings is None:
                logger.error("二阶编码嵌入计算失败")
                return []

            # 计算相似度
            similarities = []
            for i, embedding in enumerate(second_level_embeddings):
                code_id = second_level_codes[i].get('id')
                similarity = self.calculate_similarity(first_level_embedding, embedding, code_id)
                if similarity >= threshold:
                    similarities.append((second_level_codes[i], similarity))

            # 按相似度排序并返回前k个
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]

        except Exception as e:
            logger.error(f"匹配一阶编码到二阶编码失败: {e}")
            return []

    def match_second_level_to_third_level(
        self, 
        second_level_code: Dict[str, Any], 
        third_level_codes: List[Dict[str, Any]],
        threshold: float = 0.5
    ) -> Optional[Tuple[Dict[str, Any], float]]:
        """
        将二阶编码匹配到最相似的三阶编码

        Args:
            second_level_code: 二阶编码
            third_level_codes: 三阶编码列表
            threshold: 相似度阈值

        Returns:
            最相似的三阶编码和相似度
        """
        try:
            # 准备二阶编码文本
            second_level_text = f"{second_level_code.get('name', '')} {second_level_code.get('description', '')}"

            # 获取二阶编码的嵌入
            second_level_embedding = self.get_embedding(second_level_text)
            if second_level_embedding is None:
                logger.error("二阶编码嵌入计算失败")
                return None

            # 准备三阶编码文本
            third_level_texts = []
            for code in third_level_codes:
                text = f"{code.get('name', '')} {code.get('description', '')}"
                third_level_texts.append(text)

            # 批量获取三阶编码的嵌入
            third_level_embeddings = self.get_batch_embeddings(third_level_texts)
            if third_level_embeddings is None:
                logger.error("三阶编码嵌入计算失败")
                return None

            # 计算相似度并找到最相似的
            max_similarity = -1
            best_match = None

            for i, embedding in enumerate(third_level_embeddings):
                similarity = self.calculate_similarity(second_level_embedding, embedding)
                if similarity > max_similarity:
                    max_similarity = similarity
                    best_match = third_level_codes[i]

            if max_similarity >= threshold:
                return best_match, max_similarity
            else:
                logger.warning(f"二阶编码 {second_level_code.get('name')} 与所有三阶编码的相似度都低于阈值 {threshold}")
                return None

        except Exception as e:
            logger.error(f"匹配二阶编码到三阶编码失败: {e}")
            return None

    def update_code_embeddings(self, second_level_codes: List[Dict[str, Any]]):
        """
        更新编码库的嵌入向量

        Args:
            second_level_codes: 二阶编码列表
        """
        try:
            # 重新计算所有二阶编码的嵌入
            for code in second_level_codes:
                text = f"{code.get('name', '')} {code.get('description', '')}"
                # 清除旧缓存
                if text in self.embeddings_cache:
                    del self.embeddings_cache[text]
                # 计算新嵌入
                self.get_embedding(text)
            logger.info(f"编码库嵌入已更新，共 {len(second_level_codes)} 个编码")
        except Exception as e:
            logger.error(f"更新编码嵌入失败: {e}")

    def _manage_cache(self):
        """
        管理缓存大小，当超出限制时清理最旧的缓存
        """
        if len(self.embeddings_cache) >= self.cache_size_limit:
            # 计算需要清理的数量
            items_to_remove = len(self.embeddings_cache) - int(self.cache_size_limit * 0.8)
            # 移除最旧的缓存项（基于插入顺序）
            items = list(self.embeddings_cache.keys())[:items_to_remove]
            for item in items:
                del self.embeddings_cache[item]
            logger.info(f"缓存已清理，当前大小: {len(self.embeddings_cache)}")
