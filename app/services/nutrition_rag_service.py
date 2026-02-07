"""
营养知识库 RAG 服务

基于 ChromaDB 向量数据库和 BGE-M3 嵌入模型，构建《中国食物成分表》知识库，
为营养分析提供 RAG（检索增强生成）能力，减少 LLM 幻觉，提升营养数据准确性。

Phase 38 实现
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 知识库集合名称
NUTRITION_COLLECTION = "nutrition_knowledge"
# 知识库数据目录
KNOWLEDGE_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "nutrition_knowledge",
)
# 默认数据文件
DEFAULT_DATA_FILE = os.path.join(KNOWLEDGE_DATA_DIR, "chinese_food_composition.json")


class NutritionRAGService:
    """
    营养知识库 RAG 服务

    功能：
    - 加载《中国食物成分表》数据并灌入向量数据库
    - 根据菜品名称检索相关营养知识
    - 将检索结果格式化为 LLM 上下文
    - 支持知识库的增量更新和重建
    """

    def __init__(
        self,
        vector_service=None,
        embedding_service=None,
    ):
        """
        初始化营养 RAG 服务

        Args:
            vector_service: 向量数据库服务实例，None 则使用全局单例
            embedding_service: 嵌入服务实例，None 则使用全局单例
        """
        self._vector_service = vector_service
        self._embedding_service = embedding_service
        self._initialized = False
        logger.info("NutritionRAGService 初始化")

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
    # 知识库构建
    # ================================================================

    def load_knowledge_data(self, data_file: Optional[str] = None) -> List[Dict]:
        """
        加载营养知识数据文件

        Args:
            data_file: JSON 数据文件路径，None 则使用默认路径

        Returns:
            食物数据列表
        """
        file_path = data_file or DEFAULT_DATA_FILE
        if not os.path.exists(file_path):
            logger.warning(f"知识库数据文件不存在: {file_path}")
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"加载营养知识数据: {len(data)} 条记录，来源: {file_path}")
            return data
        except Exception as e:
            logger.error(f"加载营养知识数据失败: {e}")
            return []

    def _food_to_text(self, food: Dict) -> str:
        """
        将食物数据转换为用于向量化的文本

        构建包含食物名称、别名、分类、营养数据和备注的结构化文本，
        便于嵌入模型理解和检索。

        Args:
            food: 食物数据字典

        Returns:
            结构化文本字符串
        """
        name = food.get("food_name", "")
        aliases = food.get("aliases", [])
        category = food.get("category", "")
        per_100g = food.get("per_100g", {})
        serving = food.get("common_serving", "")
        notes = food.get("cooking_notes", "")

        # 构建检索友好的文本
        parts = [f"食物名称：{name}"]
        if aliases:
            parts.append(f"别名：{'、'.join(aliases)}")
        if category:
            parts.append(f"分类：{category}")

        # 营养数据
        if per_100g:
            nutrition_parts = []
            if "calories" in per_100g:
                nutrition_parts.append(f"热量{per_100g['calories']}千卡")
            if "protein" in per_100g:
                nutrition_parts.append(f"蛋白质{per_100g['protein']}g")
            if "fat" in per_100g:
                nutrition_parts.append(f"脂肪{per_100g['fat']}g")
            if "carbs" in per_100g:
                nutrition_parts.append(f"碳水化合物{per_100g['carbs']}g")
            if "fiber" in per_100g:
                nutrition_parts.append(f"膳食纤维{per_100g['fiber']}g")
            if "sodium" in per_100g:
                nutrition_parts.append(f"钠{per_100g['sodium']}mg")
            if "calcium" in per_100g:
                nutrition_parts.append(f"钙{per_100g['calcium']}mg")
            if "iron" in per_100g:
                nutrition_parts.append(f"铁{per_100g['iron']}mg")
            parts.append(f"每100g营养成分：{'，'.join(nutrition_parts)}")

        if serving:
            parts.append(f"常见份量：{serving}")
        if notes:
            parts.append(f"备注：{notes}")

        return "。".join(parts)

    def _food_to_metadata(self, food: Dict) -> Dict[str, Any]:
        """
        提取食物数据的元数据（用于向量数据库存储）

        Args:
            food: 食物数据字典

        Returns:
            扁平化的元数据字典（ChromaDB 仅支持基础类型值）
        """
        per_100g = food.get("per_100g", {})
        return {
            "food_name": food.get("food_name", ""),
            "category": food.get("category", ""),
            "calories": per_100g.get("calories", 0.0),
            "protein": per_100g.get("protein", 0.0),
            "fat": per_100g.get("fat", 0.0),
            "carbs": per_100g.get("carbs", 0.0),
            "fiber": per_100g.get("fiber", 0.0),
            "sodium": per_100g.get("sodium", 0.0),
            "common_serving": food.get("common_serving", ""),
            "cooking_notes": food.get("cooking_notes", ""),
        }

    def build_knowledge_base(self, data_file: Optional[str] = None, force_rebuild: bool = False) -> int:
        """
        构建营养知识库（将数据灌入向量数据库）

        Args:
            data_file: 数据文件路径，None 则使用默认
            force_rebuild: 是否强制重建（删除已有集合后重建）

        Returns:
            成功插入的记录数
        """
        vs = self._get_vector_service()
        es = self._get_embedding_service()

        # 检查集合是否已存在
        if vs.has_collection(NUTRITION_COLLECTION):
            stats = vs.get_collection_stats(NUTRITION_COLLECTION)
            existing_count = stats.get("row_count", 0)
            if existing_count > 0 and not force_rebuild:
                logger.info(
                    f"营养知识库已存在，包含 {existing_count} 条记录，跳过构建（使用 force_rebuild=True 强制重建）"
                )
                self._initialized = True
                return existing_count

            if force_rebuild:
                logger.info("强制重建营养知识库，删除已有集合")
                vs.drop_collection(NUTRITION_COLLECTION)

        # 加载数据
        foods = self.load_knowledge_data(data_file)
        if not foods:
            logger.warning("无营养知识数据可加载")
            return 0

        # 创建集合
        vs.create_collection(
            collection_name=NUTRITION_COLLECTION,
            dimension=es.dimension,
            metric_type="cosine",
            description="中国食物成分表营养知识库",
        )

        # 将食物数据转换为文本
        texts = [self._food_to_text(food) for food in foods]
        metadatas = [self._food_to_metadata(food) for food in foods]

        # 批量向量化
        logger.info(f"正在向量化 {len(texts)} 条营养知识...")
        vectors = es.embed_texts(texts, is_query=False)

        # 批量插入向量数据库
        ids = vs.insert(
            collection_name=NUTRITION_COLLECTION,
            vectors=vectors,
            texts=texts,
            metadatas=metadatas,
        )

        self._initialized = True
        logger.info(f"营养知识库构建完成，插入 {len(ids)} 条记录")
        return len(ids)

    def ensure_initialized(self, data_file: Optional[str] = None) -> bool:
        """
        确保知识库已初始化（幂等操作）

        如果知识库尚未初始化，则自动构建。

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
            logger.error(f"营养知识库初始化失败: {e}")
            return False

    # ================================================================
    # RAG 检索
    # ================================================================

    def search_nutrition(
        self,
        query: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        根据查询文本检索相关营养知识

        Args:
            query: 查询文本（通常是菜品名称）
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
            logger.warning("营养知识库未初始化，返回空结果")
            return []

        try:
            # 将查询文本向量化（使用查询前缀提升检索效果）
            query_vector = es.embed_text(query, is_query=True)

            # 向量检索
            results = vs.search(
                collection_name=NUTRITION_COLLECTION,
                query_vector=query_vector,
                top_k=top_k,
            )

            logger.info(f"营养知识检索完成: query='{query}', 返回 {len(results)} 条结果")
            return results

        except Exception as e:
            logger.error(f"营养知识检索失败: {e}")
            return []

    def get_nutrition_context(
        self,
        food_name: str,
        top_k: int = 3,
        max_distance: float = 1.5,
    ) -> str:
        """
        获取格式化的营养知识上下文（供 LLM Prompt 使用）

        检索与菜品名称最相关的营养知识条目，格式化为 LLM 可理解的上下文文本。

        Args:
            food_name: 菜品名称
            top_k: 最多返回的参考条目数
            max_distance: 最大距离阈值（cosine距离，越小越相似；超过阈值的结果被过滤）

        Returns:
            格式化的上下文文本，如果没有相关知识则返回空字符串
        """
        results = self.search_nutrition(food_name, top_k=top_k)

        if not results:
            return ""

        # 过滤距离过大的结果（相关性低的不纳入上下文）
        relevant = [r for r in results if r.get("distance", float("inf")) <= max_distance]

        if not relevant:
            return ""

        # 格式化上下文
        context_parts = ["以下是《中国食物成分表》中的相关参考数据："]
        for i, r in enumerate(relevant, 1):
            meta = r.get("metadata", {})
            food = meta.get("food_name", "")
            cal = meta.get("calories", 0)
            pro = meta.get("protein", 0)
            fat = meta.get("fat", 0)
            carbs = meta.get("carbs", 0)
            fiber = meta.get("fiber", 0)
            sodium = meta.get("sodium", 0)
            serving = meta.get("common_serving", "")
            notes = meta.get("cooking_notes", "")

            entry = (
                f"\n参考{i}：{food}"
                f"\n  每100g：热量{cal}千卡，蛋白质{pro}g，脂肪{fat}g，碳水{carbs}g"
                f"，膳食纤维{fiber}g，钠{sodium}mg"
            )
            if serving:
                entry += f"\n  常见份量：{serving}"
            if notes:
                entry += f"\n  备注：{notes}"
            context_parts.append(entry)

        context_parts.append(
            "\n请参考以上数据给出准确的营养分析。如果查询的菜品与参考数据不完全匹配，"
            "请根据参考数据进行合理估算，但不要编造不存在的数据。"
        )

        return "\n".join(context_parts)

    # ================================================================
    # 知识库管理
    # ================================================================

    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        vs = self._get_vector_service()
        if not vs.has_collection(NUTRITION_COLLECTION):
            return {"exists": False, "row_count": 0, "initialized": self._initialized}

        stats = vs.get_collection_stats(NUTRITION_COLLECTION)
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

    def add_food_knowledge(self, food_data: Dict) -> Optional[str]:
        """
        向知识库增量添加单条食物数据

        Args:
            food_data: 食物数据字典，格式同 chinese_food_composition.json 中的条目

        Returns:
            插入记录的 ID，失败返回 None
        """
        vs = self._get_vector_service()
        es = self._get_embedding_service()

        if not self.ensure_initialized():
            logger.warning("知识库未初始化，无法添加数据")
            return None

        try:
            text = self._food_to_text(food_data)
            metadata = self._food_to_metadata(food_data)
            vector = es.embed_text(text, is_query=False)

            record_id = vs.insert_single(
                collection_name=NUTRITION_COLLECTION,
                vector=vector,
                text=text,
                metadata=metadata,
            )
            logger.info(f"成功添加食物知识: {food_data.get('food_name', 'unknown')}")
            return record_id

        except Exception as e:
            logger.error(f"添加食物知识失败: {e}")
            return None


# ============================================================
# 模块级单例
# ============================================================
_default_instance: Optional[NutritionRAGService] = None


def get_nutrition_rag_service() -> NutritionRAGService:
    """
    获取全局营养 RAG 服务单例

    首次调用时创建实例；后续调用返回同一实例。
    知识库在首次检索时自动初始化（懒加载）。
    """
    global _default_instance
    if _default_instance is None:
        _default_instance = NutritionRAGService()
    return _default_instance
