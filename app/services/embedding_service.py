"""
BGE-M3 嵌入模型服务

使用 sentence-transformers 加载 BAAI/bge-m3 模型，将文本转换为向量表示。
BGE-M3 支持中英文双语，适用于营养知识库、菜谱知识图谱等 RAG 场景。

向量维度：1024（BGE-M3 默认输出维度）

Phase 37 实现
"""

import logging
from typing import List, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)

# BGE-M3 模型名称
DEFAULT_MODEL_NAME = "BAAI/bge-m3"
# BGE-M3 输出向量维度
EMBEDDING_DIM = 1024


class EmbeddingService:
    """
    文本嵌入服务（基于 BGE-M3）

    功能：
    - 单条文本向量化
    - 批量文本向量化
    - 支持查询前缀优化（BGE 系列推荐对查询添加 instruction 前缀）

    线程安全：模型加载后只做推理，可安全并发读取。
    """

    # BGE 系列推荐的查询前缀，用于区分"检索查询"和"文档段落"
    QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, device: Optional[str] = None):
        """
        初始化嵌入服务

        Args:
            model_name: HuggingFace 模型名称或本地路径
            device: 推理设备（'cpu' / 'cuda' / 'mps'），None 时自动选择
        """
        self._model_name = model_name
        self._device = device
        self._model = None
        self._dim = EMBEDDING_DIM
        logger.info(f"EmbeddingService 初始化，模型: {model_name}, 设备: {device or '自动'}")

    @property
    def dimension(self) -> int:
        """返回嵌入向量维度"""
        return self._dim

    def _load_model(self):
        """
        懒加载模型（首次调用时加载，避免启动时阻塞）
        """
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"正在加载嵌入模型: {self._model_name} ...")
            self._model = SentenceTransformer(
                self._model_name,
                device=self._device,
            )
            # 更新实际维度
            self._dim = self._model.get_sentence_embedding_dimension()
            logger.info(f"嵌入模型加载完成，维度: {self._dim}")
        except Exception as e:
            logger.error(f"嵌入模型加载失败: {e}")
            raise RuntimeError(f"无法加载嵌入模型 {self._model_name}: {e}") from e

    def embed_texts(
        self,
        texts: List[str],
        is_query: bool = False,
        batch_size: int = 32,
        normalize: bool = True,
    ) -> List[List[float]]:
        """
        将文本列表转换为向量列表

        Args:
            texts: 待向量化的文本列表
            is_query: 是否为检索查询（True 时添加查询前缀以提升检索质量）
            batch_size: 批量推理大小
            normalize: 是否对向量做 L2 归一化（推荐 True，便于余弦相似度计算）

        Returns:
            向量列表，每个向量为 float 列表，长度为 self.dimension
        """
        if not texts:
            return []

        self._load_model()

        # BGE 系列对查询文本添加前缀可提升检索效果
        if is_query:
            texts = [f"{self.QUERY_INSTRUCTION}{t}" for t in texts]

        try:
            embeddings = self._model.encode(
                texts,
                batch_size=batch_size,
                normalize_embeddings=normalize,
                show_progress_bar=False,
            )
            # 转为 Python 原生列表（便于 JSON 序列化和 Milvus 写入）
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"文本向量化失败: {e}")
            raise RuntimeError(f"文本向量化失败: {e}") from e

    def embed_text(self, text: str, is_query: bool = False, normalize: bool = True) -> List[float]:
        """
        将单条文本转换为向量（embed_texts 的便捷方法）

        Args:
            text: 待向量化的文本
            is_query: 是否为检索查询
            normalize: 是否归一化

        Returns:
            浮点数列表，长度为 self.dimension
        """
        results = self.embed_texts([text], is_query=is_query, normalize=normalize)
        return results[0]

    def compute_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """
        计算两个向量的余弦相似度

        Args:
            vec_a: 向量 A
            vec_b: 向量 B

        Returns:
            余弦相似度值，范围 [-1, 1]
        """
        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def is_model_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self._model is not None

    def get_model_info(self) -> dict:
        """返回模型元信息"""
        return {
            "model_name": self._model_name,
            "dimension": self._dim,
            "device": self._device or "auto",
            "loaded": self.is_model_loaded(),
        }


# ============================================================
# 模块级单例（供其他服务直接 import 使用）
# ============================================================
_default_instance: Optional[EmbeddingService] = None


def get_embedding_service(
    model_name: str = DEFAULT_MODEL_NAME,
    device: Optional[str] = None,
) -> EmbeddingService:
    """
    获取全局嵌入服务单例

    首次调用时创建实例；后续调用返回同一实例。
    注意：模型本身在首次 embed 调用时才加载。
    """
    global _default_instance
    if _default_instance is None:
        _default_instance = EmbeddingService(model_name=model_name, device=device)
    return _default_instance
