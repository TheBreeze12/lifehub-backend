"""
向量数据库服务（ChromaDB 实现）

使用 ChromaDB（嵌入式模式）管理向量集合，提供向量 CRUD 操作。
支持集合创建、向量插入、相似度检索、向量删除等功能。

ChromaDB 嵌入式模式无需外部服务，数据持久化在本地目录中，
跨平台兼容（Windows / macOS / Linux），适合开发与测试。

对外接口与 Milvus 版本一致，后续可按需切换后端。

Phase 37 实现
"""

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 默认持久化目录
DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "chroma_db",
)

# 默认向量维度（与 BGE-M3 一致）
DEFAULT_DIMENSION = 1024

# 默认相似度度量类型（ChromaDB 支持 cosine / l2 / ip）
DEFAULT_METRIC_TYPE = "cosine"


class VectorService:
    """
    向量数据库服务（ChromaDB 后端）

    功能：
    - 集合管理（创建、删除、列出）
    - 向量插入（单条 / 批量）
    - 相似度检索（Top-K）
    - 向量删除（按 ID）
    - 集合统计信息

    使用 ChromaDB 嵌入式持久化模式，数据存储在本地目录中。
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化向量数据库服务

        Args:
            db_path: ChromaDB 持久化目录路径，None 则使用默认路径
        """
        self._db_path = db_path or DEFAULT_DB_PATH
        self._client = None
        # 记录每个集合的维度配置
        self._collection_dims: Dict[str, int] = {}
        logger.info(f"VectorService 初始化，数据库路径: {self._db_path}")

    def _ensure_client(self):
        """
        确保 ChromaDB 客户端已连接（懒加载）
        """
        if self._client is not None:
            return

        try:
            import chromadb

            # 确保数据目录存在
            if not os.path.exists(self._db_path):
                os.makedirs(self._db_path, exist_ok=True)
                logger.info(f"创建数据目录: {self._db_path}")

            self._client = chromadb.PersistentClient(path=self._db_path)
            logger.info(f"ChromaDB 客户端连接成功: {self._db_path}")
        except Exception as e:
            logger.error(f"ChromaDB 客户端连接失败: {e}")
            raise RuntimeError(f"无法连接 ChromaDB 数据库: {e}") from e

    # ================================================================
    # 集合管理
    # ================================================================

    def create_collection(
        self,
        collection_name: str,
        dimension: int = DEFAULT_DIMENSION,
        metric_type: str = DEFAULT_METRIC_TYPE,
        description: str = "",
    ) -> bool:
        """
        创建向量集合

        如果集合已存在则获取已有集合，返回 True。

        Args:
            collection_name: 集合名称
            dimension: 向量维度（记录用，ChromaDB 不强制校验维度）
            metric_type: 相似度度量类型（cosine / l2 / ip）
            description: 集合描述

        Returns:
            是否成功
        """
        self._ensure_client()

        try:
            # ChromaDB 的 get_or_create_collection 自带幂等性
            chroma_metric = metric_type.lower()
            if chroma_metric not in ("cosine", "l2", "ip"):
                chroma_metric = "cosine"

            self._client.get_or_create_collection(
                name=collection_name,
                metadata={
                    "hnsw:space": chroma_metric,
                    "dimension": dimension,
                    "description": description or f"LifeHub RAG 集合: {collection_name}",
                },
            )
            self._collection_dims[collection_name] = dimension
            logger.info(f"集合创建/获取成功: {collection_name}, 维度: {dimension}, 度量: {chroma_metric}")
            return True

        except Exception as e:
            logger.error(f"创建集合失败 [{collection_name}]: {e}")
            raise RuntimeError(f"创建集合失败: {e}") from e

    def drop_collection(self, collection_name: str) -> bool:
        """
        删除向量集合

        Args:
            collection_name: 集合名称

        Returns:
            是否成功
        """
        self._ensure_client()

        try:
            if not self.has_collection(collection_name):
                logger.warning(f"集合不存在，无需删除: {collection_name}")
                return True

            self._client.delete_collection(collection_name)
            self._collection_dims.pop(collection_name, None)
            logger.info(f"集合已删除: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"删除集合失败 [{collection_name}]: {e}")
            raise RuntimeError(f"删除集合失败: {e}") from e

    def has_collection(self, collection_name: str) -> bool:
        """
        检查集合是否存在

        Args:
            collection_name: 集合名称

        Returns:
            集合是否存在
        """
        self._ensure_client()
        try:
            existing = [c.name for c in self._client.list_collections()]
            return collection_name in existing
        except Exception:
            return False

    def list_collections(self) -> List[str]:
        """
        列出所有集合名称

        Returns:
            集合名称列表
        """
        self._ensure_client()
        try:
            return [c.name for c in self._client.list_collections()]
        except Exception:
            return []

    # ================================================================
    # 向量插入
    # ================================================================

    def insert(
        self,
        collection_name: str,
        vectors: List[List[float]],
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        """
        批量插入向量数据

        Args:
            collection_name: 集合名称
            vectors: 向量列表
            texts: 对应的原始文本列表
            metadatas: 对应的元数据列表（可选）

        Returns:
            插入记录的 ID 列表（字符串 UUID）
        """
        self._ensure_client()

        if len(vectors) != len(texts):
            raise ValueError(f"向量数量({len(vectors)})与文本数量({len(texts)})不一致")

        if metadatas is not None and len(metadatas) != len(vectors):
            raise ValueError(f"元数据数量({len(metadatas)})与向量数量({len(vectors)})不一致")

        try:
            collection = self._client.get_collection(collection_name)

            # 生成唯一 ID
            ids = [str(uuid.uuid4()) for _ in range(len(vectors))]

            # ChromaDB 要求 metadata 值为 str/int/float/bool，不支持嵌套 dict
            # 将复杂 metadata 序列化为 JSON 字符串存储
            import json
            safe_metadatas = []
            if metadatas is None:
                safe_metadatas = [{"_raw": "{}"} for _ in range(len(vectors))]
            else:
                for meta in metadatas:
                    safe_meta = {}
                    for k, v in meta.items():
                        if isinstance(v, (str, int, float, bool)):
                            safe_meta[k] = v
                        else:
                            safe_meta[k] = json.dumps(v, ensure_ascii=False)
                    if not safe_meta:
                        safe_meta["_raw"] = "{}"
                    safe_metadatas.append(safe_meta)

            collection.add(
                ids=ids,
                embeddings=vectors,
                documents=texts,
                metadatas=safe_metadatas,
            )

            logger.info(f"向量插入成功: {collection_name}, 数量: {len(ids)}")
            return ids

        except Exception as e:
            if "向量数量" in str(e) or "元数据数量" in str(e):
                raise
            logger.error(f"向量插入失败 [{collection_name}]: {e}")
            raise RuntimeError(f"向量插入失败: {e}") from e

    def insert_single(
        self,
        collection_name: str,
        vector: List[float],
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        插入单条向量数据

        Args:
            collection_name: 集合名称
            vector: 向量
            text: 原始文本
            metadata: 元数据（可选）

        Returns:
            插入记录的 ID
        """
        ids = self.insert(
            collection_name=collection_name,
            vectors=[vector],
            texts=[text],
            metadatas=[metadata or {}],
        )
        return ids[0] if ids else ""

    # ================================================================
    # 相似度检索
    # ================================================================

    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        filter_expr: Optional[Dict] = None,
        output_fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        向量相似度检索

        Args:
            collection_name: 集合名称
            query_vector: 查询向量
            top_k: 返回最相似的 K 条结果
            filter_expr: 过滤条件（ChromaDB where 字典格式）
            output_fields: 需要返回的字段列表（兼容参数，ChromaDB 默认返回全部）

        Returns:
            检索结果列表，每条包含 id、distance、text、metadata 等字段
        """
        self._ensure_client()

        try:
            collection = self._client.get_collection(collection_name)

            kwargs = {
                "query_embeddings": [query_vector],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"],
            }
            if filter_expr and isinstance(filter_expr, dict):
                kwargs["where"] = filter_expr

            results = collection.query(**kwargs)

            parsed = []
            if results and results.get("ids"):
                ids_list = results["ids"][0]
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                dists = results.get("distances", [[]])[0]

                for i, doc_id in enumerate(ids_list):
                    item = {
                        "id": doc_id,
                        "distance": dists[i] if i < len(dists) else None,
                        "text": docs[i] if i < len(docs) else "",
                        "metadata": metas[i] if i < len(metas) else {},
                    }
                    # 清理 metadata 中的 _raw 占位符
                    if item["metadata"] and "_raw" in item["metadata"]:
                        if item["metadata"]["_raw"] == "{}":
                            item["metadata"] = {}
                    parsed.append(item)

            logger.debug(f"检索完成: {collection_name}, 返回 {len(parsed)} 条结果")
            return parsed

        except Exception as e:
            logger.error(f"向量检索失败 [{collection_name}]: {e}")
            raise RuntimeError(f"向量检索失败: {e}") from e

    # ================================================================
    # 向量删除
    # ================================================================

    def delete_by_ids(self, collection_name: str, ids: List[str]) -> bool:
        """
        按 ID 删除向量

        Args:
            collection_name: 集合名称
            ids: 要删除的记录 ID 列表

        Returns:
            是否成功
        """
        self._ensure_client()

        try:
            collection = self._client.get_collection(collection_name)
            collection.delete(ids=ids)
            logger.info(f"向量删除成功: {collection_name}, 数量: {len(ids)}")
            return True
        except Exception as e:
            logger.error(f"向量删除失败 [{collection_name}]: {e}")
            raise RuntimeError(f"向量删除失败: {e}") from e

    def delete_by_filter(self, collection_name: str, filter_expr: Dict) -> bool:
        """
        按过滤条件删除向量

        Args:
            collection_name: 集合名称
            filter_expr: ChromaDB where 字典格式的过滤条件

        Returns:
            是否成功
        """
        self._ensure_client()

        try:
            collection = self._client.get_collection(collection_name)
            collection.delete(where=filter_expr)
            logger.info(f"按条件删除成功: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"按条件删除失败 [{collection_name}]: {e}")
            raise RuntimeError(f"按条件删除失败: {e}") from e

    # ================================================================
    # 统计与工具
    # ================================================================

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        获取集合统计信息

        Args:
            collection_name: 集合名称

        Returns:
            包含 row_count 等统计信息的字典
        """
        self._ensure_client()

        try:
            if not self.has_collection(collection_name):
                return {"exists": False, "row_count": 0}

            collection = self._client.get_collection(collection_name)
            count = collection.count()
            return {
                "exists": True,
                "row_count": count,
            }
        except Exception as e:
            logger.error(f"获取集合统计失败 [{collection_name}]: {e}")
            return {"exists": True, "row_count": -1, "error": str(e)}

    def get_service_info(self) -> Dict[str, Any]:
        """返回服务元信息"""
        return {
            "db_path": self._db_path,
            "connected": self._client is not None,
            "backend": "chromadb",
            "collections": self.list_collections() if self._client else [],
        }

    def close(self):
        """关闭客户端连接"""
        if self._client is not None:
            try:
                logger.info("ChromaDB 客户端已关闭")
            except Exception as e:
                logger.warning(f"关闭 ChromaDB 客户端时出错: {e}")
            finally:
                self._client = None
                self._collection_dims.clear()


# ============================================================
# 模块级单例
# ============================================================
_default_instance: Optional[VectorService] = None


def get_vector_service(db_path: Optional[str] = None) -> VectorService:
    """
    获取全局向量数据库服务单例

    首次调用时创建实例；后续调用返回同一实例。
    客户端在首次操作时才建立连接（懒加载）。
    """
    global _default_instance
    if _default_instance is None:
        _default_instance = VectorService(db_path=db_path)
    return _default_instance
