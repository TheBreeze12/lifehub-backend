"""
菜谱知识图谱 RAG 服务

构建"菜品-配料-过敏原"知识图谱，通过向量检索增强隐性过敏原推理能力。
知识图谱数据包含菜品的完整配料列表、直接/隐性过敏原标注和推理说明。

Phase 39 实现
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 知识图谱集合名称
RECIPE_GRAPH_COLLECTION = "recipe_knowledge_graph"

# 知识图谱数据目录
RECIPE_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "recipe_knowledge",
)

# 默认数据文件
DEFAULT_RECIPE_DATA_FILE = os.path.join(RECIPE_DATA_DIR, "recipe_ingredient_allergen.json")


class RecipeGraphService:
    """
    菜谱知识图谱 RAG 服务

    功能：
    - 加载菜品-配料-过敏原知识图谱数据并灌入向量数据库
    - 根据菜品名称检索相关知识图谱条目
    - 提取隐性过敏原信息
    - 生成过敏原推理上下文（供 LLM 或 allergen_service 使用）
    - 支持知识库增量更新和重建
    """

    def __init__(
        self,
        vector_service=None,
        embedding_service=None,
    ):
        """
        初始化菜谱知识图谱服务

        Args:
            vector_service: 向量数据库服务实例，None 则使用全局单例
            embedding_service: 嵌入服务实例，None 则使用全局单例
        """
        self._vector_service = vector_service
        self._embedding_service = embedding_service
        self._initialized = False
        logger.info("RecipeGraphService 初始化")

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
    # 知识图谱数据处理
    # ================================================================

    def load_recipe_data(self, data_file: Optional[str] = None) -> List[Dict]:
        """
        加载菜谱知识图谱数据文件

        Args:
            data_file: JSON 数据文件路径，None 则使用默认路径

        Returns:
            菜谱数据列表
        """
        file_path = data_file or DEFAULT_RECIPE_DATA_FILE
        if not os.path.exists(file_path):
            logger.warning(f"菜谱知识图谱数据文件不存在: {file_path}")
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"加载菜谱知识图谱数据: {len(data)} 条记录，来源: {file_path}")
            return data
        except Exception as e:
            logger.error(f"加载菜谱知识图谱数据失败: {e}")
            return []

    def _recipe_to_text(self, recipe: Dict) -> str:
        """
        将菜谱数据转换为用于向量化的文本

        构建包含菜品名称、别名、配料、过敏原信息的结构化文本，
        便于嵌入模型理解和检索。

        Args:
            recipe: 菜谱数据字典

        Returns:
            结构化文本字符串
        """
        name = recipe.get("dish_name", "")
        aliases = recipe.get("aliases", [])
        ingredients = recipe.get("ingredients", [])
        allergens = recipe.get("allergens", {})
        hidden_notes = recipe.get("hidden_allergen_notes", "")

        parts = [f"菜品名称：{name}"]
        if aliases:
            parts.append(f"别名：{'、'.join(aliases)}")
        if ingredients:
            parts.append(f"配料：{'、'.join(ingredients)}")

        # 过敏原信息
        if allergens:
            allergen_parts = []
            for code, info in allergens.items():
                if isinstance(info, dict):
                    ingredient = info.get("ingredient", "")
                    note = info.get("note", "")
                    direct = info.get("direct", False)
                    allergen_type = "直接" if direct else "隐性"
                    allergen_parts.append(f"{code}({allergen_type}，来源：{ingredient}，{note})")
            if allergen_parts:
                parts.append(f"过敏原：{'；'.join(allergen_parts)}")

        if hidden_notes:
            parts.append(f"隐性过敏原说明：{hidden_notes}")

        return "。".join(parts)

    def _recipe_to_metadata(self, recipe: Dict) -> Dict[str, Any]:
        """
        提取菜谱数据的元数据（用于向量数据库存储）

        Args:
            recipe: 菜谱数据字典

        Returns:
            扁平化的元数据字典（ChromaDB 仅支持基础类型值）
        """
        allergens = recipe.get("allergens", {})

        # 提取过敏原代码列表
        allergen_codes = list(allergens.keys()) if allergens else []
        direct_allergen_codes = [
            code for code, info in allergens.items()
            if isinstance(info, dict) and info.get("direct", False)
        ]
        hidden_allergen_codes = [
            code for code, info in allergens.items()
            if isinstance(info, dict) and not info.get("direct", False)
        ]

        return {
            "dish_name": recipe.get("dish_name", ""),
            "aliases": json.dumps(recipe.get("aliases", []), ensure_ascii=False),
            "ingredients": json.dumps(recipe.get("ingredients", []), ensure_ascii=False),
            "allergen_codes": json.dumps(allergen_codes, ensure_ascii=False),
            "direct_allergen_codes": json.dumps(direct_allergen_codes, ensure_ascii=False),
            "hidden_allergen_codes": json.dumps(hidden_allergen_codes, ensure_ascii=False),
            "hidden_allergen_notes": recipe.get("hidden_allergen_notes", ""),
            "allergen_count": len(allergen_codes),
        }

    # ================================================================
    # 知识库构建
    # ================================================================

    def build_knowledge_base(self, data_file: Optional[str] = None, force_rebuild: bool = False) -> int:
        """
        构建菜谱知识图谱（将数据灌入向量数据库）

        Args:
            data_file: 数据文件路径，None 则使用默认
            force_rebuild: 是否强制重建（删除已有集合后重建）

        Returns:
            成功插入的记录数
        """
        vs = self._get_vector_service()
        es = self._get_embedding_service()

        # 检查集合是否已存在
        if vs.has_collection(RECIPE_GRAPH_COLLECTION):
            stats = vs.get_collection_stats(RECIPE_GRAPH_COLLECTION)
            existing_count = stats.get("row_count", 0)
            if existing_count > 0 and not force_rebuild:
                logger.info(
                    f"菜谱知识图谱已存在，包含 {existing_count} 条记录，跳过构建"
                    f"（使用 force_rebuild=True 强制重建）"
                )
                self._initialized = True
                return existing_count

            if force_rebuild:
                logger.info("强制重建菜谱知识图谱，删除已有集合")
                vs.drop_collection(RECIPE_GRAPH_COLLECTION)

        # 加载数据
        recipes = self.load_recipe_data(data_file)
        if not recipes:
            logger.warning("无菜谱知识图谱数据可加载")
            return 0

        # 创建集合
        vs.create_collection(
            collection_name=RECIPE_GRAPH_COLLECTION,
            dimension=es.dimension,
            metric_type="cosine",
            description="菜品-配料-过敏原知识图谱",
        )

        # 将菜谱数据转换为文本
        texts = [self._recipe_to_text(recipe) for recipe in recipes]
        metadatas = [self._recipe_to_metadata(recipe) for recipe in recipes]

        # 批量向量化
        logger.info(f"正在向量化 {len(texts)} 条菜谱知识图谱...")
        vectors = es.embed_texts(texts, is_query=False)

        # 批量插入向量数据库
        ids = vs.insert(
            collection_name=RECIPE_GRAPH_COLLECTION,
            vectors=vectors,
            texts=texts,
            metadatas=metadatas,
        )

        self._initialized = True
        logger.info(f"菜谱知识图谱构建完成，插入 {len(ids)} 条记录")
        return len(ids)

    def ensure_initialized(self, data_file: Optional[str] = None) -> bool:
        """
        确保知识图谱已初始化（幂等操作）

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
            logger.error(f"菜谱知识图谱初始化失败: {e}")
            return False

    # ================================================================
    # RAG 检索与过敏原推理
    # ================================================================

    def search_recipe(
        self,
        query: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        根据查询文本检索相关菜谱知识

        Args:
            query: 查询文本（通常是菜品名称）
            top_k: 返回最相似的 K 条结果

        Returns:
            检索结果列表
        """
        if not query or not query.strip():
            return []

        vs = self._get_vector_service()
        es = self._get_embedding_service()

        # 确保知识图谱已初始化
        if not self.ensure_initialized():
            logger.warning("菜谱知识图谱未初始化，返回空结果")
            return []

        try:
            # 将查询文本向量化
            query_vector = es.embed_text(query, is_query=True)

            # 向量检索
            results = vs.search(
                collection_name=RECIPE_GRAPH_COLLECTION,
                query_vector=query_vector,
                top_k=top_k,
            )

            logger.info(f"菜谱知识图谱检索完成: query='{query}', 返回 {len(results)} 条结果")
            return results

        except Exception as e:
            logger.error(f"菜谱知识图谱检索失败: {e}")
            return []

    def get_allergen_context(
        self,
        food_name: str,
        top_k: int = 3,
        max_distance: float = 1.2,
    ) -> Dict[str, Any]:
        """
        获取菜品的过敏原推理上下文

        检索与菜品最相关的知识图谱条目，提取过敏原信息。

        Args:
            food_name: 菜品名称
            top_k: 最多返回的参考条目数
            max_distance: 最大距离阈值（cosine距离，超过则过滤）

        Returns:
            过敏原上下文字典，包含：
            - matched_recipes: 匹配的菜谱列表
            - all_allergen_codes: 所有检测到的过敏原代码集合
            - direct_allergens: 直接过敏原详情
            - hidden_allergens: 隐性过敏原详情
            - reasoning_text: 推理说明文本
        """
        results = self.search_recipe(food_name, top_k=top_k)

        if not results:
            return self._empty_allergen_context()

        # 过滤距离过大的结果
        relevant = [r for r in results if r.get("distance", float("inf")) <= max_distance]

        if not relevant:
            return self._empty_allergen_context()

        # 解析过敏原信息
        matched_recipes = []
        all_allergen_codes = set()
        direct_allergens = {}
        hidden_allergens = {}
        reasoning_parts = []

        for r in relevant:
            meta = r.get("metadata", {})
            dish_name = meta.get("dish_name", "")
            distance = r.get("distance", float("inf"))

            # 解析 JSON 字符串字段
            try:
                allergen_codes = json.loads(meta.get("allergen_codes", "[]"))
            except (json.JSONDecodeError, TypeError):
                allergen_codes = []

            try:
                direct_codes = json.loads(meta.get("direct_allergen_codes", "[]"))
            except (json.JSONDecodeError, TypeError):
                direct_codes = []

            try:
                hidden_codes = json.loads(meta.get("hidden_allergen_codes", "[]"))
            except (json.JSONDecodeError, TypeError):
                hidden_codes = []

            try:
                ingredients = json.loads(meta.get("ingredients", "[]"))
            except (json.JSONDecodeError, TypeError):
                ingredients = []

            hidden_notes = meta.get("hidden_allergen_notes", "")

            matched_recipes.append({
                "dish_name": dish_name,
                "distance": distance,
                "allergen_codes": allergen_codes,
                "ingredients": ingredients,
            })

            # 合并过敏原信息
            all_allergen_codes.update(allergen_codes)

            for code in direct_codes:
                if code not in direct_allergens:
                    direct_allergens[code] = {
                        "source_dish": dish_name,
                        "confidence": "high",
                    }

            for code in hidden_codes:
                if code not in hidden_allergens:
                    hidden_allergens[code] = {
                        "source_dish": dish_name,
                        "confidence": "medium",
                    }

            if hidden_notes:
                reasoning_parts.append(f"参考菜品[{dish_name}]：{hidden_notes}")

        # 构建推理说明文本
        reasoning_text = ""
        if reasoning_parts:
            reasoning_text = "知识图谱过敏原推理：\n" + "\n".join(reasoning_parts)

        return {
            "matched_recipes": matched_recipes,
            "all_allergen_codes": list(all_allergen_codes),
            "direct_allergens": direct_allergens,
            "hidden_allergens": hidden_allergens,
            "reasoning_text": reasoning_text,
        }

    def get_hidden_allergens_for_dish(
        self,
        food_name: str,
        max_distance: float = 0.8,
    ) -> List[Dict[str, Any]]:
        """
        获取菜品的隐性过敏原列表

        仅返回隐性过敏原（非直接可见的），用于增强过敏原检测结果。

        Args:
            food_name: 菜品名称
            max_distance: 最大距离阈值（较严格，确保高相关性）

        Returns:
            隐性过敏原列表，每个元素包含 code、source_dish、note
        """
        context = self.get_allergen_context(food_name, top_k=2, max_distance=max_distance)

        hidden = []
        for code, info in context.get("hidden_allergens", {}).items():
            hidden.append({
                "code": code,
                "source_dish": info.get("source_dish", ""),
                "confidence": info.get("confidence", "medium"),
            })

        return hidden

    def get_full_allergen_detail(
        self,
        food_name: str,
        max_distance: float = 0.8,
    ) -> Dict[str, Any]:
        """
        获取菜品的完整过敏原详情（含配料信息）

        返回最匹配菜谱的完整过敏原信息，供 allergen_service 合并使用。

        Args:
            food_name: 菜品名称
            max_distance: 最大距离阈值

        Returns:
            完整过敏原详情字典
        """
        results = self.search_recipe(food_name, top_k=1)

        if not results:
            return self._empty_allergen_detail()

        top = results[0]
        distance = top.get("distance", float("inf"))
        if distance > max_distance:
            return self._empty_allergen_detail()

        meta = top.get("metadata", {})

        try:
            allergen_codes = json.loads(meta.get("allergen_codes", "[]"))
        except (json.JSONDecodeError, TypeError):
            allergen_codes = []

        try:
            direct_codes = json.loads(meta.get("direct_allergen_codes", "[]"))
        except (json.JSONDecodeError, TypeError):
            direct_codes = []

        try:
            hidden_codes = json.loads(meta.get("hidden_allergen_codes", "[]"))
        except (json.JSONDecodeError, TypeError):
            hidden_codes = []

        try:
            ingredients = json.loads(meta.get("ingredients", "[]"))
        except (json.JSONDecodeError, TypeError):
            ingredients = []

        return {
            "matched": True,
            "dish_name": meta.get("dish_name", ""),
            "distance": distance,
            "ingredients": ingredients,
            "allergen_codes": allergen_codes,
            "direct_allergen_codes": direct_codes,
            "hidden_allergen_codes": hidden_codes,
            "hidden_allergen_notes": meta.get("hidden_allergen_notes", ""),
        }

    # ================================================================
    # 知识库管理
    # ================================================================

    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """获取知识图谱统计信息"""
        vs = self._get_vector_service()
        if not vs.has_collection(RECIPE_GRAPH_COLLECTION):
            return {"exists": False, "row_count": 0, "initialized": self._initialized}

        stats = vs.get_collection_stats(RECIPE_GRAPH_COLLECTION)
        stats["initialized"] = self._initialized
        return stats

    def rebuild_knowledge_base(self, data_file: Optional[str] = None) -> int:
        """
        强制重建知识图谱

        Args:
            data_file: 数据文件路径

        Returns:
            插入的记录数
        """
        self._initialized = False
        return self.build_knowledge_base(data_file=data_file, force_rebuild=True)

    def add_recipe_knowledge(self, recipe_data: Dict) -> Optional[str]:
        """
        向知识图谱增量添加单条菜谱数据

        Args:
            recipe_data: 菜谱数据字典

        Returns:
            插入记录的 ID，失败返回 None
        """
        vs = self._get_vector_service()
        es = self._get_embedding_service()

        if not self.ensure_initialized():
            logger.warning("知识图谱未初始化，无法添加数据")
            return None

        try:
            text = self._recipe_to_text(recipe_data)
            metadata = self._recipe_to_metadata(recipe_data)
            vector = es.embed_text(text, is_query=False)

            record_id = vs.insert_single(
                collection_name=RECIPE_GRAPH_COLLECTION,
                vector=vector,
                text=text,
                metadata=metadata,
            )
            logger.info(f"成功添加菜谱知识: {recipe_data.get('dish_name', 'unknown')}")
            return record_id

        except Exception as e:
            logger.error(f"添加菜谱知识失败: {e}")
            return None

    # ================================================================
    # 工具方法
    # ================================================================

    @staticmethod
    def _empty_allergen_context() -> Dict[str, Any]:
        """返回空的过敏原上下文"""
        return {
            "matched_recipes": [],
            "all_allergen_codes": [],
            "direct_allergens": {},
            "hidden_allergens": {},
            "reasoning_text": "",
        }

    @staticmethod
    def _empty_allergen_detail() -> Dict[str, Any]:
        """返回空的过敏原详情"""
        return {
            "matched": False,
            "dish_name": "",
            "distance": float("inf"),
            "ingredients": [],
            "allergen_codes": [],
            "direct_allergen_codes": [],
            "hidden_allergen_codes": [],
            "hidden_allergen_notes": "",
        }


# ============================================================
# 模块级单例
# ============================================================
_default_instance: Optional[RecipeGraphService] = None


def get_recipe_graph_service() -> RecipeGraphService:
    """
    获取全局菜谱知识图谱服务单例

    首次调用时创建实例；后续调用返回同一实例。
    知识图谱在首次检索时自动初始化（懒加载）。
    """
    global _default_instance
    if _default_instance is None:
        _default_instance = RecipeGraphService()
    return _default_instance
