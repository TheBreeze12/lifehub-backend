"""
运动消耗知识库 RAG 服务

基于 ChromaDB 向量数据库和 BGE-M3 嵌入模型，构建运动代谢当量（METs）知识库，
通过 RAG 检索增强运动消耗数据查询，将运动类型覆盖从 20+ 扩展到 100+。

数据来源：《Compendium of Physical Activities》和《中国成人身体活动能量消耗参考手册》

Phase 40 实现
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 知识库集合名称
EXERCISE_COLLECTION = "exercise_knowledge"

# 知识库数据目录
EXERCISE_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "exercise_knowledge",
)

# 默认数据文件
DEFAULT_EXERCISE_DATA_FILE = os.path.join(EXERCISE_DATA_DIR, "exercise_mets_data.json")


class ExerciseRAGService:
    """
    运动消耗知识库 RAG 服务

    功能：
    - 加载运动代谢当量数据并灌入向量数据库
    - 根据运动名称/描述检索相关运动的 METs 值
    - 支持知识库的增量更新和重建
    - 为 METsService 提供 RAG 增强查询接口
    """

    def __init__(
        self,
        vector_service=None,
        embedding_service=None,
    ):
        """
        初始化运动消耗 RAG 服务

        Args:
            vector_service: 向量数据库服务实例，None 则使用全局单例
            embedding_service: 嵌入服务实例，None 则使用全局单例
        """
        self._vector_service = vector_service
        self._embedding_service = embedding_service
        self._initialized = False
        logger.info("ExerciseRAGService 初始化")

    def _get_vector_service(self):
        """获取向量数据库服务（懒加载）"""
        if self._vector_service is None:
            from app.services.vector_service import get_vector_service
            self._vector_service = get_vector_service()
        return self._vector_service

    def _get_embedding_service(self):
        """获取嵌入服务（懒加载）"""
        if self._embedding_service is None:
            from app.services.embedding_service import get_embedding_service
            self._embedding_service = get_embedding_service()
        return self._embedding_service

    # ================================================================
    # 知识库数据处理
    # ================================================================

    def load_exercise_data(self, data_file: Optional[str] = None) -> List[Dict]:
        """
        加载运动消耗知识库数据文件

        Args:
            data_file: JSON 数据文件路径，None 则使用默认路径

        Returns:
            运动数据列表
        """
        file_path = data_file or DEFAULT_EXERCISE_DATA_FILE
        if not os.path.exists(file_path):
            logger.warning(f"运动消耗知识库数据文件不存在: {file_path}")
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"加载运动消耗数据: {len(data)} 条记录，来源: {file_path}")
            return data
        except Exception as e:
            logger.error(f"加载运动消耗数据失败: {e}")
            return []

    def _exercise_to_text(self, exercise: Dict) -> str:
        """
        将运动数据转换为用于向量化的文本

        构建包含运动名称、别名、分类、METs值、强度、描述的结构化文本，
        便于嵌入模型理解和检索。

        Args:
            exercise: 运动数据字典

        Returns:
            结构化文本字符串
        """
        name = exercise.get("exercise_name", "")
        aliases = exercise.get("aliases", [])
        category = exercise.get("category", "")
        mets = exercise.get("mets", 0)
        intensity = exercise.get("intensity", "")
        description = exercise.get("description", "")
        suitable_for = exercise.get("suitable_for", [])

        # 强度中文映射
        intensity_cn = {"light": "低强度", "moderate": "中等强度", "vigorous": "高强度"}.get(
            intensity, intensity
        )

        parts = [f"运动名称：{name}"]
        if aliases:
            parts.append(f"别名：{'、'.join(aliases)}")
        if category:
            parts.append(f"分类：{category}")
        parts.append(f"METs值：{mets}")
        parts.append(f"强度：{intensity_cn}")
        if description:
            parts.append(f"描述：{description}")
        if suitable_for:
            parts.append(f"适合：{'、'.join(suitable_for)}")

        return "。".join(parts)

    def _exercise_to_metadata(self, exercise: Dict) -> Dict[str, Any]:
        """
        提取运动数据的元数据（用于向量数据库存储）

        Args:
            exercise: 运动数据字典

        Returns:
            扁平化的元数据字典（ChromaDB 仅支持基础类型值）
        """
        return {
            "exercise_name": exercise.get("exercise_name", ""),
            "aliases": json.dumps(exercise.get("aliases", []), ensure_ascii=False),
            "category": exercise.get("category", ""),
            "mets": float(exercise.get("mets", 0)),
            "intensity": exercise.get("intensity", ""),
            "description": exercise.get("description", ""),
            "suitable_for": json.dumps(exercise.get("suitable_for", []), ensure_ascii=False),
        }

    # ================================================================
    # 知识库构建
    # ================================================================

    def build_knowledge_base(self, data_file: Optional[str] = None, force_rebuild: bool = False) -> int:
        """
        构建运动消耗知识库（将数据灌入向量数据库）

        Args:
            data_file: 数据文件路径，None 则使用默认
            force_rebuild: 是否强制重建（删除已有集合后重建）

        Returns:
            成功插入的记录数
        """
        vs = self._get_vector_service()
        es = self._get_embedding_service()

        # 检查集合是否已存在
        if vs.has_collection(EXERCISE_COLLECTION):
            stats = vs.get_collection_stats(EXERCISE_COLLECTION)
            existing_count = stats.get("row_count", 0)
            if existing_count > 0 and not force_rebuild:
                logger.info(
                    f"运动消耗知识库已存在，包含 {existing_count} 条记录，跳过构建"
                    f"（使用 force_rebuild=True 强制重建）"
                )
                self._initialized = True
                return existing_count

            if force_rebuild:
                logger.info("强制重建运动消耗知识库，删除已有集合")
                vs.drop_collection(EXERCISE_COLLECTION)

        # 加载数据
        exercises = self.load_exercise_data(data_file)
        if not exercises:
            logger.warning("无运动消耗数据可加载")
            return 0

        # 创建集合
        vs.create_collection(
            collection_name=EXERCISE_COLLECTION,
            dimension=es.dimension,
            metric_type="cosine",
            description="运动代谢当量（METs）知识库",
        )

        # 将运动数据转换为文本
        texts = [self._exercise_to_text(ex) for ex in exercises]
        metadatas = [self._exercise_to_metadata(ex) for ex in exercises]

        # 批量向量化
        logger.info(f"正在向量化 {len(texts)} 条运动消耗数据...")
        vectors = es.embed_texts(texts, is_query=False)

        # 批量插入向量数据库
        ids = vs.insert(
            collection_name=EXERCISE_COLLECTION,
            vectors=vectors,
            texts=texts,
            metadatas=metadatas,
        )

        self._initialized = True
        logger.info(f"运动消耗知识库构建完成，插入 {len(ids)} 条记录")
        return len(ids)

    def ensure_initialized(self, data_file: Optional[str] = None) -> bool:
        """
        确保知识库已初始化（幂等操作）

        Args:
            data_file: 数据文件路径

        Returns:
            是否初始化成功
        """
        if self._initialized:
            return True

        try:
            count = self.build_knowledge_base(data_file=data_file)
            return count > 0
        except Exception as e:
            logger.error(f"运动消耗知识库初始化失败: {e}")
            return False

    # ================================================================
    # RAG 检索
    # ================================================================

    def search_exercise(
        self,
        query: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        根据查询文本检索相关运动数据

        Args:
            query: 查询文本（通常是运动名称或描述）
            top_k: 返回最相似的 K 条结果

        Returns:
            检索结果列表，每条包含 text、metadata、distance 等字段
        """
        if not query or not query.strip():
            return []

        vs = self._get_vector_service()
        es = self._get_embedding_service()

        # 确保知识库已初始化
        if not self.ensure_initialized():
            logger.warning("运动消耗知识库未初始化，返回空结果")
            return []

        try:
            # 将查询文本向量化（使用查询前缀提升检索效果）
            query_vector = es.embed_text(query, is_query=True)

            # 向量检索
            results = vs.search(
                collection_name=EXERCISE_COLLECTION,
                query_vector=query_vector,
                top_k=top_k,
            )

            logger.info(f"运动消耗检索完成: query='{query}', 返回 {len(results)} 条结果")
            return results

        except Exception as e:
            logger.error(f"运动消耗检索失败: {e}")
            return []

    def get_exercise_mets_from_rag(
        self,
        exercise_query: str,
        max_distance: float = 1.5,
    ) -> Dict[str, Any]:
        """
        通过 RAG 检索获取运动的 METs 值

        检索最匹配的运动条目，返回其 METs 值和详细信息。

        Args:
            exercise_query: 运动名称或描述
            max_distance: 最大距离阈值（cosine距离，超过则认为不匹配）

        Returns:
            包含 found、exercise_name、mets、intensity、category 等字段的字典
        """
        if not exercise_query or not exercise_query.strip():
            return self._empty_result()

        results = self.search_exercise(exercise_query, top_k=1)

        if not results:
            return self._empty_result()

        top = results[0]
        distance = top.get("distance", float("inf"))

        if distance > max_distance:
            logger.debug(f"RAG检索距离过大: query='{exercise_query}', distance={distance:.3f}")
            return self._empty_result()

        meta = top.get("metadata", {})

        return {
            "found": True,
            "exercise_name": meta.get("exercise_name", ""),
            "mets": float(meta.get("mets", 0)),
            "intensity": meta.get("intensity", ""),
            "category": meta.get("category", ""),
            "description": meta.get("description", ""),
            "distance": distance,
            "source": "rag",
        }

    def get_all_exercise_names(self) -> List[str]:
        """
        获取知识库中所有运动名称

        Returns:
            运动名称列表
        """
        data = self.load_exercise_data()
        return [ex.get("exercise_name", "") for ex in data if ex.get("exercise_name")]

    # ================================================================
    # 知识库管理
    # ================================================================

    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        vs = self._get_vector_service()
        if not vs.has_collection(EXERCISE_COLLECTION):
            return {"exists": False, "row_count": 0, "initialized": self._initialized}

        stats = vs.get_collection_stats(EXERCISE_COLLECTION)
        stats["initialized"] = self._initialized
        return stats

    def rebuild_knowledge_base(self, data_file: Optional[str] = None) -> int:
        """
        强制重建知识库

        Args:
            data_file: 数据文件路径

        Returns:
            插入的记录数
        """
        self._initialized = False
        return self.build_knowledge_base(data_file=data_file, force_rebuild=True)

    # ================================================================
    # 工具方法
    # ================================================================

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        """返回空的检索结果"""
        return {
            "found": False,
            "exercise_name": "",
            "mets": 0.0,
            "intensity": "",
            "category": "",
            "description": "",
            "distance": float("inf"),
            "source": "",
        }


# ============================================================
# 模块级单例
# ============================================================
_default_instance: Optional[ExerciseRAGService] = None


def get_exercise_rag_service() -> ExerciseRAGService:
    """
    获取全局运动消耗 RAG 服务单例

    首次调用时创建实例；后续调用返回同一实例。
    知识库在首次检索时自动初始化（懒加载）。
    """
    global _default_instance
    if _default_instance is None:
        _default_instance = ExerciseRAGService()
    return _default_instance
