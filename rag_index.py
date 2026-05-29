import hashlib
import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import jieba
import numpy as np

logger = logging.getLogger(__name__)

INDEX_VERSION = "rag-index-v1"


def file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    for token in jieba.lcut(text or ""):
        token = token.strip().lower()
        if len(token) >= 2:
            tokens.append(token)
    return tokens


class RagIndexBuilder:
    def __init__(
        self,
        library_path: str,
        index_dir: str,
        embedding_fn: Optional[Callable[[str], np.ndarray]] = None,
    ):
        self.library_path = library_path
        self.index_dir = Path(index_dir)
        self.embedding_fn = embedding_fn

    def build_documents(self) -> List[Dict[str, Any]]:
        with open(self.library_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        documents: List[Dict[str, Any]] = []
        third_levels = data.get("encoding_library", {}).get("third_level_codes", [])
        for third in third_levels:
            third_id = third.get("id")
            third_name = str(third.get("name", "")).strip()
            third_description = str(third.get("description", "")).strip()
            second_codes = third.get("second_level_codes", []) or []
            sibling_names = [str(code.get("name", "")).strip() for code in second_codes if code.get("name")]

            third_text = self._compose_text(
                level_label="三阶编码",
                code_id=third_id,
                name=third_name,
                description=third_description,
                parent_name="",
                parent_description="",
                siblings=sibling_names,
            )
            documents.append(
                {
                    "doc_id": f"third:{third_id}",
                    "level": "third",
                    "code_id": third_id,
                    "name": third_name,
                    "description": third_description,
                    "third_level_id": third_id,
                    "third_level": third_name,
                    "tokens": tokenize(third_text),
                    "text": third_text,
                }
            )

            for second in second_codes:
                second_id = second.get("id")
                second_name = str(second.get("name", "")).strip()
                second_description = str(second.get("description", "")).strip()
                second_text = self._compose_text(
                    level_label="二阶编码",
                    code_id=second_id,
                    name=second_name,
                    description=second_description,
                    parent_name=third_name,
                    parent_description=third_description,
                    siblings=[name for name in sibling_names if name != second_name],
                )
                documents.append(
                    {
                        "doc_id": f"second:{second_id}",
                        "level": "second",
                        "code_id": second_id,
                        "name": second_name,
                        "description": second_description,
                        "third_level_id": second.get("third_level_id", third_id),
                        "third_level": second.get("third_level", third_name),
                        "tokens": tokenize(second_text),
                        "text": second_text,
                    }
                )
        return documents

    def build_token_index(self, documents: List[Dict[str, Any]]) -> Dict[str, List[int]]:
        index: Dict[str, List[int]] = defaultdict(list)
        for i, document in enumerate(documents):
            for token in set(document.get("tokens", [])):
                index[token].append(i)
        return {token: sorted(postings) for token, postings in index.items()}

    def build_embeddings(self, documents: List[Dict[str, Any]]) -> np.ndarray:
        if not documents:
            return np.zeros((0, 1), dtype="float32")

        vectors = [self._safe_embedding(document.get("text", "")) for document in documents]
        dim = max((vector.shape[0] for vector in vectors), default=1)
        normalized = []
        for vector in vectors:
            if vector.shape[0] != dim:
                padded = np.zeros(dim, dtype="float32")
                padded[: vector.shape[0]] = vector
                vector = padded
            normalized.append(vector)
        return np.stack(normalized).astype("float32")

    def write(self) -> Dict[str, Any]:
        self.index_dir.mkdir(parents=True, exist_ok=True)

        documents = self.build_documents()
        token_index = self.build_token_index(documents)
        embeddings = self.build_embeddings(documents)

        (self.index_dir / "code_documents.json").write_text(
            json.dumps(documents, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (self.index_dir / "token_index.json").write_text(
            json.dumps(token_index, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        np.savez_compressed(self.index_dir / "vector_embeddings.npz", embeddings=embeddings)

        meta = {
            "index_version": INDEX_VERSION,
            "library_path": str(Path(self.library_path).resolve()),
            "library_hash": file_sha256(self.library_path),
            "document_count": len(documents),
            "built_at": datetime.now().isoformat(),
            "invalidated": False,
        }
        (self.index_dir / "index_meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return meta

    def _safe_embedding(self, text: str) -> np.ndarray:
        if not self.embedding_fn:
            # token 哈希向量，保证无模型情况下依然可工作
            return self._hashed_embedding(text)
        try:
            vector = self.embedding_fn(text)
            if vector is None:
                return self._hashed_embedding(text)
            vector = np.asarray(vector, dtype="float32").reshape(-1)
            if vector.size == 0:
                return self._hashed_embedding(text)
            return vector
        except Exception:
            return self._hashed_embedding(text)

    def _hashed_embedding(self, text: str, dim: int = 128) -> np.ndarray:
        vector = np.zeros(dim, dtype="float32")
        for token in tokenize(text):
            vector[hash(token) % dim] += 1.0
        norm = float(np.linalg.norm(vector))
        if norm > 0:
            vector /= norm
        return vector

    def _compose_text(
        self,
        level_label: str,
        code_id: Any,
        name: str,
        description: str,
        parent_name: str,
        parent_description: str,
        siblings: List[str],
    ) -> str:
        # 以编码名称为核心信号，用同类编码名称提供区分度。
        meaningful_desc = description
        generic_prefix = f"描述{name}"
        if not description or description.startswith(generic_prefix):
            meaningful_desc = self._generate_rich_description(name, level_label, parent_name)

        parts = [name]

        # 仅当描述比名称更长且不重复时加入
        if meaningful_desc and len(meaningful_desc) > len(name) + 3:
            desc_clean = meaningful_desc.strip()
            if desc_clean.startswith(name):
                rest = desc_clean[len(name):].strip("。，、. \t")
                if rest:
                    parts.append(f"{name}：{rest}")
            else:
                parts.append(desc_clean)

        if parent_name:
            parts.append(f"{name}属于{parent_name}")

        # 同类编码名称提供关键的区分信号
        if siblings:
            related = "、".join(siblings[:6])
            parts.append(f"相关概念：{related}")

        return "\n".join(parts)

    @staticmethod
    def _generate_rich_description(name: str, level_label: str, parent_name: str) -> str:
        """基于编码名称生成较丰富的描述文本"""
        # 领域关键词 -> 描述模板
        keyword_templates = [
            ('技术', f'{name}涉及技术研发、技术创新和技术应用方面的讨论'),
            ('创新', f'{name}涉及创新方法、创新机制和创新成果方面的讨论'),
            ('管理', f'{name}涉及组织管理、人员管理和流程管理方面的讨论'),
            ('市场', f'{name}涉及市场策略、营销推广和客户销售方面的讨论'),
            ('资源', f'{name}涉及资源配置、资源获取和资源整合方面的讨论'),
            ('服务', f'{name}涉及服务流程、服务质量和客户服务体验方面的讨论'),
            ('质量', f'{name}涉及质量标准、质量控制和质量管理方面的讨论'),
            ('团队', f'{name}涉及团队协作、团队建设和团队管理方面的讨论'),
            ('战略', f'{name}涉及战略规划、战略执行和战略调整方面的讨论'),
            ('文化', f'{name}涉及组织文化、价值观念和文化建设方面的讨论'),
            ('制度', f'{name}涉及制度建设、制度执行和制度完善方面的讨论'),
            ('风险', f'{name}涉及风险识别、风险评估和风险应对方面的讨论'),
            ('合作', f'{name}涉及合作关系、合作模式和合作效果方面的讨论'),
            ('知识', f'{name}涉及知识管理、知识共享和知识传承方面的讨论'),
            ('学习', f'{name}涉及学习过程、学习机制和知识获取方面的讨论'),
            ('权力', f'{name}涉及权力分配、权力运行和权力制衡方面的讨论'),
            ('关系', f'{name}涉及关系网络、关系维护和关系协调方面的讨论'),
            ('传承', f'{name}涉及技艺传承、文化传承和代际传承方面的讨论'),
            ('手工', f'{name}涉及手工技艺、手工制作和手工艺方面的讨论'),
            ('设计', f'{name}涉及设计理念、设计方法和设计创新方面的讨论'),
            ('品牌', f'{name}涉及品牌建设、品牌传播和品牌价值方面的讨论'),
            ('渠道', f'{name}涉及渠道建设、渠道管理和渠道拓展方面的讨论'),
            ('供应链', f'{name}涉及供应链管理、供应链优化和供应链协同方面的讨论'),
            ('生产', f'{name}涉及生产工艺、生产流程和生产效率方面的讨论'),
            ('产品', f'{name}涉及产品开发、产品设计和产品质量方面的讨论'),
            ('治理', f'{name}涉及组织治理、治理结构和治理机制方面的讨论'),
            ('组织', f'{name}涉及组织结构、组织变革和组织管理方面的讨论'),
            ('绩效', f'{name}涉及绩效评估、绩效管理和绩效改进方面的讨论'),
            ('激励', f'{name}涉及激励制度、激励方式和激励效果方面的讨论'),
            ('领导', f'{name}涉及领导方式、领导行为和领导决策方面的讨论'),
            ('决策', f'{name}涉及决策过程、决策机制和决策执行方面的讨论'),
            ('能力', f'{name}涉及能力建设、能力评估和能力提升方面的讨论'),
            ('价值', f'{name}涉及价值创造、价值评估和价值实现方面的讨论'),
            ('模式', f'{name}涉及模式创新、模式选择和模式转型方面的讨论'),
            ('环境', f'{name}涉及环境分析、环境适应和环境变化方面的讨论'),
            ('竞争', f'{name}涉及竞争策略、竞争优势和竞争态势方面的讨论'),
            ('客户', f'{name}涉及客户需求、客户关系和客户服务方面的讨论'),
            ('人才', f'{name}涉及人才培养、人才引进和人才管理方面的讨论'),
            ('资金', f'{name}涉及资金管理、资金筹措和资金运作方面的讨论'),
            ('信息', f'{name}涉及信息管理、信息共享和信息处理方面的讨论'),
            ('流程', f'{name}涉及流程设计、流程优化和流程管理方面的讨论'),
            ('结构', f'{name}涉及结构设计、结构优化和结构调整方面的讨论'),
            ('机制', f'{name}涉及机制设计、机制运行和机制完善方面的讨论'),
            ('体系', f'{name}涉及体系建设、体系完善和体系管理方面的讨论'),
        ]

        for keyword, template in keyword_templates:
            if keyword in name:
                return template

        # 默认: 基于名称和父级描述
        if parent_name:
            return f'{name}是属于{parent_name}领域的一个编码概念，涉及{name}方面的讨论和分析'
        return f'{name}是一个编码概念，涉及{name}方面的讨论和分析内容'


class RagIndexManager:
    def __init__(
        self,
        library_path: str,
        index_dir: str,
        embedding_fn: Optional[Callable[[str], np.ndarray]] = None,
    ):
        self.library_path = library_path
        self.index_dir = Path(index_dir)
        self.embedding_fn = embedding_fn

    def is_fresh(self) -> bool:
        if not self._artifacts_are_valid():
            return False
        try:
            meta = json.loads((self.index_dir / "index_meta.json").read_text(encoding="utf-8"))
        except Exception:
            return False
        if not isinstance(meta, dict):
            return False
        if meta.get("index_version") != INDEX_VERSION:
            return False
        if meta.get("invalidated") is not False:
            return False
        if str(Path(self.library_path).resolve()) != str(meta.get("library_path")):
            return False
        if meta.get("library_hash") != file_sha256(self.library_path):
            return False
        return True

    def _artifacts_are_valid(self) -> bool:
        required = [
            self.index_dir / "code_documents.json",
            self.index_dir / "token_index.json",
            self.index_dir / "vector_embeddings.npz",
            self.index_dir / "index_meta.json",
        ]
        return all(path.exists() for path in required)

    def invalidate(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        meta_path = self.index_dir / "index_meta.json"
        meta: Dict[str, Any] = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
        meta.update({"invalidated": True, "invalidated_at": datetime.now().isoformat()})
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def rebuild(self) -> Dict[str, Any]:
        return RagIndexBuilder(self.library_path, str(self.index_dir), self.embedding_fn).write()

    def ensure_fresh(self) -> bool:
        if self.is_fresh():
            return True
        try:
            self.rebuild()
        except Exception as exc:
            logger.warning("RAG index rebuild failed: %s", exc)
            return False
        return self.is_fresh()
