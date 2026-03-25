import logging
import os
import random
import re
from typing import Dict, List, Any, Optional, Tuple

import torch
from torch.utils.data import Dataset
from transformers import BertTokenizer

logger = logging.getLogger(__name__)


class GroundedTheoryDataset(Dataset):
    """扎根理论BERT微调数据集"""

    def __init__(self, texts: List[str], labels: List[int], tokenizer, max_length: int = 512):
        """
        初始化数据集

        Args:
            texts: 文本列表
            labels: 标签列表
            tokenizer: BERT tokenizer
            max_length: 最大序列长度
        """
        if len(texts) != len(labels):
            raise ValueError(f"文本数量({len(texts)})与标签数量({len(labels)})不匹配")

        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

        logger.info(f"数据集初始化完成，共 {len(self.texts)} 个样本")

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        """
        获取单个样本

        Args:
            idx: 样本索引

        Returns:
            包含 input_ids, attention_mask, labels 的字典
        """
        if idx < 0 or idx >= len(self.texts):
            raise IndexError(f"索引 {idx} 超出范围 [0, {len(self.texts)})")

        text = self.texts[idx]
        label = self.labels[idx]

        try:
            encoding = self.tokenizer(
                text,
                max_length=self.max_length,
                padding='max_length',
                truncation=True,
                return_tensors='pt'
            )

            return {
                'input_ids': encoding['input_ids'].squeeze(0),
                'attention_mask': encoding['attention_mask'].squeeze(0),
                'labels': torch.tensor(label, dtype=torch.long)
            }
        except Exception as e:
            logger.error(f"处理样本 {idx} 时出错: {e}")
            raise


def get_label_mapping(standard_answer_manager) -> Tuple[Dict[str, int], Dict[int, str]]:
    """
    获取标签到ID和ID到标签的映射

    Args:
        standard_answer_manager: 标准答案管理器实例

    Returns:
        Tuple[label_to_id, id_to_label]: 标签映射元组
    """
    if standard_answer_manager is None:
        raise ValueError("standard_answer_manager 不能为 None")

    current_answers = standard_answer_manager.get_current_answers()
    if not current_answers:
        raise ValueError("没有可用的标准答案数据")

    structured_codes = current_answers.get("structured_codes", {})
    if not structured_codes:
        raise ValueError("标准答案中没有结构化编码数据")

    label_to_id = {}
    id_to_label = {}
    label_id = 0

    for third_cat, second_cats in structured_codes.items():
        for second_cat, first_codes in second_cats.items():
            full_category = f"{third_cat} > {second_cat}"
            if full_category not in label_to_id:
                label_to_id[full_category] = label_id
                id_to_label[label_id] = full_category
                label_id += 1

    logger.info(f"创建了 {len(label_to_id)} 个标签映射")
    return label_to_id, id_to_label


def get_label_mapping_from_dict(current_answers: Dict[str, Any]) -> Tuple[Dict[str, int], Dict[int, str]]:
    """
    从标准答案字典获取标签到ID和ID到标签的映射

    Args:
        current_answers: 标准答案字典

    Returns:
        Tuple[label_to_id, id_to_label]: 标签映射元组
    """
    if not current_answers:
        raise ValueError("没有可用的标准答案数据")

    structured_codes = current_answers.get("structured_codes", {})
    if not structured_codes:
        raise ValueError("标准答案中没有结构化编码数据")

    label_to_id = {}
    id_to_label = {}
    label_id = 0

    for third_cat, second_cats in structured_codes.items():
        for second_cat, first_codes in second_cats.items():
            full_category = f"{third_cat} > {second_cat}"
            if full_category not in label_to_id:
                label_to_id[full_category] = label_id
                id_to_label[label_id] = full_category
                label_id += 1

    logger.info(f"创建了 {len(label_to_id)} 个标签映射")
    return label_to_id, id_to_label


def create_dataset_from_standard_answers(
    standard_answer_manager,
    tokenizer=None,
    max_length: int = 512,
    use_augmentation: bool = False
) -> GroundedTheoryDataset:
    """
    从standard_answer_manager加载数据并创建数据集

    Args:
        standard_answer_manager: 标准答案管理器实例 或 标准答案字典
        tokenizer: BERT tokenizer，如果为None则自动加载
        max_length: 最大序列长度
        use_augmentation: 是否使用数据增强

    Returns:
        GroundedTheoryDataset 实例
    """
    if standard_answer_manager is None:
        raise ValueError("standard_answer_manager 不能为 None")

    if isinstance(standard_answer_manager, dict):
        current_answers = standard_answer_manager
        label_to_id, _ = get_label_mapping_from_dict(current_answers)
    else:
        current_answers = standard_answer_manager.get_current_answers()
        label_to_id, _ = get_label_mapping(standard_answer_manager)

    if not current_answers:
        raise ValueError("没有可用的标准答案数据")

    training_data = current_answers.get("training_data", [])
    if not training_data:
        structured_codes = current_answers.get("structured_codes", {})
        training_data = _extract_training_data_from_codes(structured_codes)

    if not training_data:
        raise ValueError("没有可用的训练数据")

    texts = []
    labels = []

    for item in training_data:
        if not isinstance(item, dict):
            continue

        # 兼容两种 training_data 结构：
        # 1) 旧结构：直接包含 text / third_category / second_category
        # 2) 新结构：input_sentences + target_abstract/second/third_category
        text = item.get("text", "")
        third_cat = item.get("third_category", "")
        second_cat = item.get("second_category", "")

        if not text and "input_sentences" in item:
            input_sentences = item.get("input_sentences", {}) or {}
            original_content = (input_sentences.get("original_content") or "").strip()
            related_list = input_sentences.get("related_statement") or []

            if isinstance(related_list, list):
                related_part = " ".join([str(s).strip() for s in related_list if str(s).strip()])
            else:
                related_part = str(related_list).strip()

            # 将原语句和关联句子拼接成一个输入序列
            if original_content and related_part:
                text = f"{original_content} {related_part}"
            else:
                text = original_content or related_part

        if not third_cat and "target_third_category" in item:
            third_cat = item.get("target_third_category", "")
        if not second_cat and "target_second_category" in item:
            second_cat = item.get("target_second_category", "")

        if text and third_cat and second_cat:
            full_category = f"{third_cat} > {second_cat}"
            if full_category in label_to_id:
                texts.append(text)
                labels.append(label_to_id[full_category])

                if use_augmentation:
                    augmented_text = augment_text(text)
                    if augmented_text != text:
                        texts.append(augmented_text)
                        labels.append(label_to_id[full_category])

    if not texts:
        raise ValueError("无法从标准答案中提取有效的训练数据")

    if tokenizer is None:
        try:
            from config import Config
            local_model_path = os.path.join(Config.LOCAL_MODELS_DIR, Config.DEFAULT_MODEL_NAME)
            if os.path.exists(local_model_path):
                tokenizer = BertTokenizer.from_pretrained(local_model_path)
                logger.info(f"从本地路径加载 tokenizer: {local_model_path}")
            else:
                tokenizer = BertTokenizer.from_pretrained(Config.DEFAULT_MODEL_NAME)
                logger.info(f"从 HuggingFace 加载 tokenizer: {Config.DEFAULT_MODEL_NAME}")
        except Exception as e:
            logger.warning(f"加载 tokenizer 失败: {e}")
            raise ValueError(f"无法加载 tokenizer，请确保本地模型存在或网络可用: {e}")

    logger.info(f"创建数据集，共 {len(texts)} 个样本")
    return GroundedTheoryDataset(texts, labels, tokenizer, max_length)


def _extract_training_data_from_codes(structured_codes: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从结构化编码中提取训练数据

    Args:
        structured_codes: 结构化编码字典

    Returns:
        训练数据列表
    """
    training_data = []

    for third_cat, second_cats in structured_codes.items():
        for second_cat, first_contents in second_cats.items():
            for content in first_contents:
                if isinstance(content, dict):
                    if 'content' in content:
                        text_content = content.get('content', '')
                    elif 'name' in content:
                        text_content = content.get('name', '')
                    else:
                        text_content = str(content)

                    if text_content and text_content.strip():
                        training_data.append({
                            "text": text_content.strip(),
                            "third_category": third_cat,
                            "second_category": second_cat,
                            "full_category": f"{third_cat} > {second_cat}",
                            "source": "first_level_code"
                        })

                        sentence_details = content.get('sentence_details', [])
                        for detail in sentence_details:
                            if isinstance(detail, dict):
                                sentence_text = detail.get('sentence', '')
                                if sentence_text and sentence_text.strip():
                                    training_data.append({
                                        "text": sentence_text.strip(),
                                        "third_category": third_cat,
                                        "second_category": second_cat,
                                        "full_category": f"{third_cat} > {second_cat}",
                                        "source": "dragged_sentence"
                                    })

    return training_data


def augment_text(text: str, augmentation_prob: float = 0.3) -> str:
    """
    简单的文本增强

    Args:
        text: 原始文本
        augmentation_prob: 增强概率

    Returns:
        增强后的文本
    """
    if not text or not text.strip():
        return text

    if random.random() > augmentation_prob:
        return text

    augmentation_methods = [
        _synonym_replacement,
        _random_deletion,
        _random_swap
    ]

    method = random.choice(augmentation_methods)
    try:
        augmented = method(text)
        return augmented if augmented else text
    except Exception as e:
        logger.debug(f"文本增强失败: {e}")
        return text


def _synonym_replacement(text: str, n: int = 1) -> str:
    """
    同义词替换

    Args:
        text: 原始文本
        n: 替换词数

    Returns:
        替换后的文本
    """
    synonym_map = {
        "很": ["非常", "特别", "相当"],
        "非常": ["很", "特别", "相当"],
        "好": ["不错", "良好", "优秀"],
        "不错": ["好", "良好", "优秀"],
        "但是": ["不过", "然而", "可是"],
        "因为": ["由于", "因", "缘于"],
        "所以": ["因此", "故", "于是"],
        "如果": ["假如", "倘若", "若是"],
        "但是": ["可是", "不过", "然而"],
        "重要": ["关键", "紧要", "要紧"],
        "问题": ["难题", "疑问", "困惑"],
        "方法": ["方式", "办法", "途径"],
        "结果": ["成果", "结局", "后果"],
        "过程": ["历程", "经过", "进程"],
    }

    words = list(text)
    replaced = 0

    for i, word in enumerate(words):
        if replaced >= n:
            break
        if word in synonym_map and random.random() < 0.3:
            words[i] = random.choice(synonym_map[word])
            replaced += 1

    return ''.join(words)


def _random_deletion(text: str, p: float = 0.1) -> str:
    """
    随机删除字符

    Args:
        text: 原始文本
        p: 删除概率

    Returns:
        删除后的文本
    """
    if len(text) <= 3:
        return text

    words = list(text)
    retained = []

    for word in words:
        if random.random() > p:
            retained.append(word)

    if not retained:
        return text

    return ''.join(retained)


def _random_swap(text: str, n: int = 1) -> str:
    """
    随机交换字符

    Args:
        text: 原始文本
        n: 交换次数

    Returns:
        交换后的文本
    """
    if len(text) <= 3:
        return text

    words = list(text)

    for _ in range(n):
        idx1 = random.randint(0, len(words) - 1)
        idx2 = random.randint(0, len(words) - 1)
        if idx1 != idx2:
            words[idx1], words[idx2] = words[idx2], words[idx1]

    return ''.join(words)


def create_dataloader(
    dataset: GroundedTheoryDataset,
    batch_size: int = 16,
    shuffle: bool = True,
    num_workers: int = 0
) -> torch.utils.data.DataLoader:
    """
    创建数据加载器

    Args:
        dataset: 数据集实例
        batch_size: 批次大小
        shuffle: 是否打乱
        num_workers: 工作进程数

    Returns:
        DataLoader 实例
    """
    return torch.utils.data.DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers
    )


def split_dataset(
    dataset: GroundedTheoryDataset,
    train_ratio: float = 0.8,
    random_seed: int = 42
) -> Tuple[GroundedTheoryDataset, GroundedTheoryDataset]:
    """
    分割数据集为训练集和验证集

    Args:
        dataset: 原始数据集
        train_ratio: 训练集比例
        random_seed: 随机种子

    Returns:
        Tuple[train_dataset, val_dataset]: 训练集和验证集
    """
    import numpy as np

    np.random.seed(random_seed)

    total_size = len(dataset)
    train_size = int(total_size * train_ratio)

    indices = list(range(total_size))
    np.random.shuffle(indices)

    train_indices = indices[:train_size]
    val_indices = indices[train_size:]

    train_texts = [dataset.texts[i] for i in train_indices]
    train_labels = [dataset.labels[i] for i in train_indices]

    val_texts = [dataset.texts[i] for i in val_indices]
    val_labels = [dataset.labels[i] for i in val_indices]

    train_dataset = GroundedTheoryDataset(
        train_texts, train_labels, dataset.tokenizer, dataset.max_length
    )
    val_dataset = GroundedTheoryDataset(
        val_texts, val_labels, dataset.tokenizer, dataset.max_length
    )

    logger.info(f"数据集分割完成: 训练集 {len(train_dataset)} 样本, 验证集 {len(val_dataset)} 样本")

    return train_dataset, val_dataset