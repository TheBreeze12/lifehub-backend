"""
Phase 38 测试：营养知识库 RAG 构建与检索

测试内容：
1. NutritionRAGService - 知识库数据加载、构建、检索、上下文生成
2. AI Service 集成 - RAG 上下文注入 Prompt 构建
3. 端到端流程 - 数据加载 → 向量化 → 存储 → 检索 → 上下文格式化
4. 边缘情况 - 空查询、不存在的食物、重复构建、增量添加等

注意：测试使用临时目录存储 ChromaDB 数据，测试结束后自动清理。
嵌入模型测试使用真实 BGE-M3 模型（需要首次下载）。
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestNutritionDataFile(unittest.TestCase):
    """测试营养知识数据文件完整性"""

    def test_data_file_exists(self):
        """测试数据文件存在"""
        from app.services.nutrition_rag_service import DEFAULT_DATA_FILE
        self.assertTrue(
            os.path.exists(DEFAULT_DATA_FILE),
            f"营养知识数据文件不存在: {DEFAULT_DATA_FILE}",
        )

    def test_data_file_valid_json(self):
        """测试数据文件是有效的 JSON"""
        from app.services.nutrition_rag_service import DEFAULT_DATA_FILE
        with open(DEFAULT_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0, "数据文件不能为空")

    def test_data_file_schema(self):
        """测试每条数据的 schema 正确"""
        from app.services.nutrition_rag_service import DEFAULT_DATA_FILE
        with open(DEFAULT_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        required_fields = ["food_name", "per_100g"]
        nutrition_fields = ["calories", "protein", "fat", "carbs"]

        for i, item in enumerate(data):
            for field in required_fields:
                self.assertIn(
                    field, item, f"第 {i} 条数据缺少字段: {field}, 食物: {item.get('food_name', '?')}"
                )
            per_100g = item["per_100g"]
            for nf in nutrition_fields:
                self.assertIn(
                    nf, per_100g,
                    f"第 {i} 条数据 per_100g 缺少字段: {nf}, 食物: {item['food_name']}",
                )
                self.assertIsInstance(
                    per_100g[nf], (int, float),
                    f"第 {i} 条数据 per_100g.{nf} 不是数值类型, 食物: {item['food_name']}",
                )

    def test_data_has_diverse_categories(self):
        """测试数据覆盖多个食物分类"""
        from app.services.nutrition_rag_service import DEFAULT_DATA_FILE
        with open(DEFAULT_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        categories = set(item.get("category", "") for item in data)
        # 应至少覆盖主要分类
        self.assertGreaterEqual(len(categories), 5, f"食物分类过少: {categories}")

    def test_data_has_aliases(self):
        """测试大部分食物有别名"""
        from app.services.nutrition_rag_service import DEFAULT_DATA_FILE
        with open(DEFAULT_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        with_aliases = sum(1 for item in data if item.get("aliases"))
        ratio = with_aliases / len(data)
        self.assertGreater(ratio, 0.8, f"有别名的食物比例过低: {ratio:.1%}")

    def test_data_calorie_range_reasonable(self):
        """测试热量数据在合理范围内"""
        from app.services.nutrition_rag_service import DEFAULT_DATA_FILE
        with open(DEFAULT_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            cal = item["per_100g"]["calories"]
            self.assertGreaterEqual(
                cal, 0, f"{item['food_name']} 热量不能为负: {cal}"
            )
            self.assertLessEqual(
                cal, 900, f"{item['food_name']} 热量异常高（>900kcal/100g）: {cal}"
            )

    def test_data_macronutrient_sum_reasonable(self):
        """测试三大宏量营养素总量不超过 100g"""
        from app.services.nutrition_rag_service import DEFAULT_DATA_FILE
        with open(DEFAULT_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            p = item["per_100g"]["protein"]
            f_ = item["per_100g"]["fat"]
            c = item["per_100g"]["carbs"]
            total = p + f_ + c
            self.assertLessEqual(
                total, 105,  # 允许少许误差
                f"{item['food_name']} 宏量营养素总量超 100g: P={p}+F={f_}+C={c}={total}",
            )


class TestNutritionRAGServiceUnit(unittest.TestCase):
    """NutritionRAGService 单元测试（不加载模型）"""

    def test_import(self):
        """测试模块可以正常导入"""
        from app.services.nutrition_rag_service import (
            NutritionRAGService,
            get_nutrition_rag_service,
            NUTRITION_COLLECTION,
        )
        self.assertIsNotNone(NutritionRAGService)
        self.assertEqual(NUTRITION_COLLECTION, "nutrition_knowledge")

    def test_init(self):
        """测试初始化"""
        from app.services.nutrition_rag_service import NutritionRAGService
        svc = NutritionRAGService()
        self.assertFalse(svc._initialized)

    def test_load_knowledge_data_default(self):
        """测试加载默认数据文件"""
        from app.services.nutrition_rag_service import NutritionRAGService
        svc = NutritionRAGService()
        data = svc.load_knowledge_data()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_load_knowledge_data_nonexistent_file(self):
        """测试加载不存在的数据文件"""
        from app.services.nutrition_rag_service import NutritionRAGService
        svc = NutritionRAGService()
        data = svc.load_knowledge_data("/nonexistent/path/data.json")
        self.assertEqual(data, [])

    def test_load_knowledge_data_custom_file(self):
        """测试加载自定义数据文件"""
        from app.services.nutrition_rag_service import NutritionRAGService
        svc = NutritionRAGService()

        # 创建临时数据文件
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        try:
            json.dump(
                [{"food_name": "测试食物", "per_100g": {"calories": 100, "protein": 10, "fat": 5, "carbs": 15}}],
                tmp,
                ensure_ascii=False,
            )
            tmp.close()
            data = svc.load_knowledge_data(tmp.name)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["food_name"], "测试食物")
        finally:
            os.unlink(tmp.name)

    def test_food_to_text(self):
        """测试食物数据转文本"""
        from app.services.nutrition_rag_service import NutritionRAGService
        svc = NutritionRAGService()

        food = {
            "food_name": "番茄炒蛋",
            "aliases": ["西红柿炒蛋"],
            "category": "家常菜",
            "per_100g": {
                "calories": 86.0,
                "protein": 5.2,
                "fat": 5.8,
                "carbs": 3.8,
                "fiber": 0.5,
                "sodium": 280.0,
            },
            "common_serving": "一份约250g",
            "cooking_notes": "鸡蛋为蛋类过敏原",
        }
        text = svc._food_to_text(food)

        # 验证包含关键信息
        self.assertIn("番茄炒蛋", text)
        self.assertIn("西红柿炒蛋", text)
        self.assertIn("家常菜", text)
        self.assertIn("86.0", text)
        self.assertIn("5.2", text)
        self.assertIn("一份约250g", text)
        self.assertIn("蛋类过敏原", text)

    def test_food_to_text_minimal(self):
        """测试最小化食物数据转文本"""
        from app.services.nutrition_rag_service import NutritionRAGService
        svc = NutritionRAGService()

        food = {"food_name": "未知食物"}
        text = svc._food_to_text(food)
        self.assertIn("未知食物", text)

    def test_food_to_metadata(self):
        """测试食物数据转元数据"""
        from app.services.nutrition_rag_service import NutritionRAGService
        svc = NutritionRAGService()

        food = {
            "food_name": "鸡胸肉",
            "category": "肉类",
            "per_100g": {"calories": 133, "protein": 31.4, "fat": 1.2, "carbs": 0},
            "common_serving": "一块约150g",
            "cooking_notes": "高蛋白低脂",
        }
        meta = svc._food_to_metadata(food)

        self.assertEqual(meta["food_name"], "鸡胸肉")
        self.assertEqual(meta["category"], "肉类")
        self.assertEqual(meta["calories"], 133)
        self.assertEqual(meta["protein"], 31.4)
        self.assertEqual(meta["common_serving"], "一块约150g")

    def test_food_to_metadata_missing_fields(self):
        """测试缺少字段时元数据的默认值"""
        from app.services.nutrition_rag_service import NutritionRAGService
        svc = NutritionRAGService()

        food = {"food_name": "测试"}
        meta = svc._food_to_metadata(food)
        self.assertEqual(meta["food_name"], "测试")
        self.assertEqual(meta["calories"], 0.0)
        self.assertEqual(meta["protein"], 0.0)

    def test_singleton_pattern(self):
        """测试单例模式"""
        from app.services import nutrition_rag_service as mod
        mod._default_instance = None
        svc1 = mod.get_nutrition_rag_service()
        svc2 = mod.get_nutrition_rag_service()
        self.assertIs(svc1, svc2)
        mod._default_instance = None


class TestNutritionRAGServiceWithVectorDB(unittest.TestCase):
    """NutritionRAGService 集成测试（使用临时 ChromaDB）"""

    @classmethod
    def setUpClass(cls):
        """创建临时目录和服务实例"""
        cls.temp_dir = tempfile.mkdtemp(prefix="lifehub_test_rag_")
        cls.db_path = os.path.join(cls.temp_dir, "chroma_test")

        # 创建向量服务（使用临时路径）
        from app.services.vector_service import VectorService
        cls.vector_service = VectorService(db_path=cls.db_path)

    @classmethod
    def tearDownClass(cls):
        """清理临时目录"""
        try:
            if cls.vector_service:
                cls.vector_service.close()
            shutil.rmtree(cls.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def _create_service_with_mock_embedding(self):
        """创建使用 mock 嵌入的 RAG 服务（避免加载真实模型）"""
        from app.services.nutrition_rag_service import NutritionRAGService

        mock_es = MagicMock()
        mock_es.dimension = 64  # 使用较小维度加速测试
        # embed_texts 返回固定维度的随机向量
        import numpy as np

        def fake_embed_texts(texts, is_query=False, **kwargs):
            np.random.seed(hash(str(texts)) % (2**31))
            return np.random.randn(len(texts), 64).tolist()

        def fake_embed_text(text, is_query=False, **kwargs):
            np.random.seed(hash(text) % (2**31))
            return np.random.randn(64).tolist()

        mock_es.embed_texts = fake_embed_texts
        mock_es.embed_text = fake_embed_text

        svc = NutritionRAGService(
            vector_service=self.vector_service,
            embedding_service=mock_es,
        )
        return svc

    def test_build_knowledge_base(self):
        """测试构建知识库"""
        svc = self._create_service_with_mock_embedding()
        count = svc.build_knowledge_base(force_rebuild=True)
        self.assertGreater(count, 0, "应成功插入至少1条记录")

        # 验证集合已创建
        from app.services.nutrition_rag_service import NUTRITION_COLLECTION
        self.assertTrue(self.vector_service.has_collection(NUTRITION_COLLECTION))

        # 验证统计信息
        stats = svc.get_knowledge_base_stats()
        self.assertTrue(stats["exists"])
        self.assertEqual(stats["row_count"], count)

    def test_build_knowledge_base_idempotent(self):
        """测试重复构建知识库（幂等性）"""
        svc = self._create_service_with_mock_embedding()
        count1 = svc.build_knowledge_base(force_rebuild=True)
        # 第二次不 force，应跳过
        count2 = svc.build_knowledge_base(force_rebuild=False)
        self.assertEqual(count1, count2, "幂等构建应返回相同数量")

    def test_build_knowledge_base_force_rebuild(self):
        """测试强制重建知识库"""
        svc = self._create_service_with_mock_embedding()
        count1 = svc.build_knowledge_base(force_rebuild=True)
        count2 = svc.rebuild_knowledge_base()
        self.assertEqual(count1, count2)

    def test_search_nutrition(self):
        """测试营养知识检索"""
        svc = self._create_service_with_mock_embedding()
        svc.build_knowledge_base(force_rebuild=True)

        results = svc.search_nutrition("番茄炒蛋", top_k=3)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0, "检索应返回至少1条结果")

        # 验证结果结构
        for r in results:
            self.assertIn("id", r)
            self.assertIn("distance", r)
            self.assertIn("text", r)
            self.assertIn("metadata", r)

    def test_search_nutrition_empty_query(self):
        """测试空查询"""
        svc = self._create_service_with_mock_embedding()
        results = svc.search_nutrition("")
        self.assertEqual(results, [])

        results = svc.search_nutrition("   ")
        self.assertEqual(results, [])

    def test_get_nutrition_context(self):
        """测试获取格式化的营养上下文"""
        svc = self._create_service_with_mock_embedding()
        svc.build_knowledge_base(force_rebuild=True)

        context = svc.get_nutrition_context("鸡胸肉", top_k=3)
        self.assertIsInstance(context, str)

        # 上下文可能为空（mock 嵌入导致距离较大），但如果不为空则应包含关键结构
        if context:
            self.assertIn("中国食物成分表", context)
            self.assertIn("参考", context)

    def test_get_nutrition_context_empty_query(self):
        """测试空查询的上下文"""
        svc = self._create_service_with_mock_embedding()
        context = svc.get_nutrition_context("")
        self.assertEqual(context, "")

    def test_add_food_knowledge(self):
        """测试增量添加食物知识"""
        svc = self._create_service_with_mock_embedding()
        svc.build_knowledge_base(force_rebuild=True)

        stats_before = svc.get_knowledge_base_stats()
        count_before = stats_before["row_count"]

        new_food = {
            "food_name": "测试新食物XYZ",
            "aliases": ["测试别名"],
            "category": "测试类",
            "per_100g": {
                "calories": 999,
                "protein": 50,
                "fat": 30,
                "carbs": 20,
                "fiber": 5,
                "sodium": 100,
            },
            "common_serving": "一份100g",
            "cooking_notes": "仅用于测试",
        }
        record_id = svc.add_food_knowledge(new_food)
        self.assertIsNotNone(record_id)
        self.assertIsInstance(record_id, str)

        stats_after = svc.get_knowledge_base_stats()
        self.assertEqual(stats_after["row_count"], count_before + 1)

    def test_ensure_initialized(self):
        """测试确保初始化"""
        svc = self._create_service_with_mock_embedding()
        svc._initialized = False

        # 先清理集合
        from app.services.nutrition_rag_service import NUTRITION_COLLECTION
        if self.vector_service.has_collection(NUTRITION_COLLECTION):
            self.vector_service.drop_collection(NUTRITION_COLLECTION)

        result = svc.ensure_initialized()
        self.assertTrue(result)
        self.assertTrue(svc._initialized)

    def test_build_with_empty_data(self):
        """测试使用空数据文件构建知识库"""
        svc = self._create_service_with_mock_embedding()

        # 创建空数据文件
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        try:
            json.dump([], tmp, ensure_ascii=False)
            tmp.close()
            count = svc.build_knowledge_base(data_file=tmp.name, force_rebuild=True)
            self.assertEqual(count, 0)
        finally:
            os.unlink(tmp.name)

    def test_search_nonexistent_food(self):
        """测试检索不存在的食物"""
        svc = self._create_service_with_mock_embedding()
        svc.build_knowledge_base(force_rebuild=True)

        # 查询一个非常不常见的食物
        results = svc.search_nutrition("外星生物料理ZZZZZ")
        # 即使食物不存在，向量检索仍会返回最近的结果
        self.assertIsInstance(results, list)

    def test_get_nutrition_context_max_distance_filter(self):
        """测试距离阈值过滤"""
        svc = self._create_service_with_mock_embedding()
        svc.build_knowledge_base(force_rebuild=True)

        # 使用极小的 max_distance 应过滤掉所有结果
        context = svc.get_nutrition_context("番茄炒蛋", max_distance=0.0001)
        # mock 嵌入的距离通常不会这么小
        self.assertEqual(context, "")

    def test_get_knowledge_base_stats_no_collection(self):
        """测试集合不存在时的统计"""
        from app.services.nutrition_rag_service import NutritionRAGService
        svc = NutritionRAGService(
            vector_service=self.vector_service,
            embedding_service=MagicMock(),
        )
        # 确保集合不存在
        from app.services.nutrition_rag_service import NUTRITION_COLLECTION
        if self.vector_service.has_collection(NUTRITION_COLLECTION):
            self.vector_service.drop_collection(NUTRITION_COLLECTION)

        stats = svc.get_knowledge_base_stats()
        self.assertFalse(stats["exists"])
        self.assertEqual(stats["row_count"], 0)


class TestAIServiceRAGIntegration(unittest.TestCase):
    """测试 AI Service 中 RAG 集成的 Prompt 构建"""

    def test_build_nutrition_prompt_without_rag(self):
        """测试无 RAG 上下文时的 Prompt 构建"""
        # 使用 mock 避免初始化真实 AI 服务
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"}):
            with patch("dashscope.api_key", "test-key"):
                from app.services.ai_service import AIService
                svc = AIService.__new__(AIService)
                svc.ark_client = None
                svc.geocoder = None

                prompt = svc._build_nutrition_prompt("番茄炒蛋", rag_context="")
                self.assertIn("番茄炒蛋", prompt)
                self.assertIn("八大类过敏原", prompt)
                self.assertNotIn("中国食物成分表", prompt)

    def test_build_nutrition_prompt_with_rag(self):
        """测试有 RAG 上下文时的 Prompt 构建"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"}):
            with patch("dashscope.api_key", "test-key"):
                from app.services.ai_service import AIService
                svc = AIService.__new__(AIService)
                svc.ark_client = None
                svc.geocoder = None

                rag_ctx = (
                    "以下是《中国食物成分表》中的相关参考数据：\n"
                    "参考1：番茄炒蛋\n  每100g：热量86千卡，蛋白质5.2g，脂肪5.8g"
                )
                prompt = svc._build_nutrition_prompt("番茄炒蛋", rag_context=rag_ctx)

                self.assertIn("番茄炒蛋", prompt)
                self.assertIn("中国食物成分表", prompt)
                self.assertIn("86千卡", prompt)
                self.assertIn("优先参考", prompt)
                self.assertIn("营养数值应与参考数据接近", prompt)

    def test_build_nutrition_prompt_rag_context_position(self):
        """测试 RAG 上下文在 Prompt 中的位置正确"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"}):
            with patch("dashscope.api_key", "test-key"):
                from app.services.ai_service import AIService
                svc = AIService.__new__(AIService)
                svc.ark_client = None
                svc.geocoder = None

                rag_ctx = "参考数据：测试RAG标记"
                prompt = svc._build_nutrition_prompt("测试菜品", rag_context=rag_ctx)

                # RAG 上下文应在 Prompt 开头部分（菜品名称之后、要求之前）
                rag_pos = prompt.find("测试RAG标记")
                req_pos = prompt.find("要求：")
                self.assertGreater(rag_pos, -1, "RAG 上下文应出现在 Prompt 中")
                self.assertLess(rag_pos, req_pos, "RAG 上下文应在要求列表之前")


class TestNutritionRAGServiceWithRealEmbedding(unittest.TestCase):
    """
    使用真实 BGE-M3 嵌入模型的集成测试

    这些测试需要下载模型（首次运行可能较慢），
    验证真实嵌入下的检索质量。
    """

    @classmethod
    def setUpClass(cls):
        """创建临时目录和真实服务实例"""
        cls.temp_dir = tempfile.mkdtemp(prefix="lifehub_test_real_rag_")
        cls.db_path = os.path.join(cls.temp_dir, "chroma_real")

        from app.services.vector_service import VectorService
        cls.vector_service = VectorService(db_path=cls.db_path)

        # 尝试加载真实嵌入模型
        cls.embedding_available = False
        try:
            from app.services.embedding_service import EmbeddingService
            cls.embedding_service = EmbeddingService(device="cpu")
            # 触发模型加载
            cls.embedding_service.embed_text("测试")
            cls.embedding_available = True
        except Exception as e:
            print(f"警告: 嵌入模型加载失败，跳过真实嵌入测试: {e}")
            cls.embedding_service = None

    @classmethod
    def tearDownClass(cls):
        """清理"""
        try:
            if cls.vector_service:
                cls.vector_service.close()
            shutil.rmtree(cls.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def setUp(self):
        if not self.embedding_available:
            self.skipTest("嵌入模型不可用，跳过真实嵌入测试")

    def _create_real_service(self):
        """创建使用真实嵌入的 RAG 服务"""
        from app.services.nutrition_rag_service import NutritionRAGService
        return NutritionRAGService(
            vector_service=self.vector_service,
            embedding_service=self.embedding_service,
        )

    def test_real_build_and_search(self):
        """测试真实嵌入下的构建和检索"""
        svc = self._create_real_service()
        count = svc.build_knowledge_base(force_rebuild=True)
        self.assertGreater(count, 0)

        results = svc.search_nutrition("番茄炒蛋", top_k=3)
        self.assertGreater(len(results), 0)

        # 验证最相关的结果应该包含番茄炒蛋或相关食物
        top_result = results[0]
        self.assertIn("metadata", top_result)
        # 最相似的结果应该距离较小
        self.assertLess(top_result["distance"], 1.0, "最相似结果距离应小于1.0")

    def test_real_search_exact_match(self):
        """测试精确匹配查询"""
        svc = self._create_real_service()
        svc.build_knowledge_base(force_rebuild=True)

        # 查询 "鸡胸肉" 应该返回鸡胸肉相关数据
        results = svc.search_nutrition("鸡胸肉", top_k=3)
        self.assertGreater(len(results), 0)

        # 第一条结果的 food_name 应该是鸡胸肉
        top_food = results[0]["metadata"].get("food_name", "")
        self.assertIn("鸡胸", top_food, f"查询'鸡胸肉'的第一结果应匹配，实际: {top_food}")

    def test_real_search_alias_match(self):
        """测试别名匹配查询"""
        svc = self._create_real_service()
        svc.build_knowledge_base(force_rebuild=True)

        # "西红柿炒蛋" 是 "番茄炒蛋" 的别名
        results = svc.search_nutrition("西红柿炒蛋", top_k=3)
        self.assertGreater(len(results), 0)

        # 应该能检索到番茄炒蛋
        food_names = [r["metadata"].get("food_name", "") for r in results]
        found_match = any("番茄" in fn or "西红柿" in fn for fn in food_names)
        self.assertTrue(found_match, f"别名查询应匹配到番茄炒蛋，实际: {food_names}")

    def test_real_search_similar_food(self):
        """测试相似食物检索"""
        svc = self._create_real_service()
        svc.build_knowledge_base(force_rebuild=True)

        # 查询 "烤三文鱼" 应该返回三文鱼相关数据
        results = svc.search_nutrition("烤三文鱼", top_k=3)
        self.assertGreater(len(results), 0)

        food_names = [r["metadata"].get("food_name", "") for r in results]
        found_fish = any("三文鱼" in fn or "鱼" in fn for fn in food_names)
        self.assertTrue(found_fish, f"相似查询应检索到鱼类，实际: {food_names}")

    def test_real_nutrition_context_format(self):
        """测试真实嵌入下的上下文格式"""
        svc = self._create_real_service()
        svc.build_knowledge_base(force_rebuild=True)

        context = svc.get_nutrition_context("宫保鸡丁", top_k=3)
        self.assertIsInstance(context, str)

        if context:
            self.assertIn("中国食物成分表", context)
            self.assertIn("参考", context)
            self.assertIn("每100g", context)
            self.assertIn("千卡", context)

    def test_real_search_category_relevance(self):
        """测试检索结果的分类相关性"""
        svc = self._create_real_service()
        svc.build_knowledge_base(force_rebuild=True)

        # 查询 "牛奶" 应优先返回乳制品类
        results = svc.search_nutrition("牛奶", top_k=3)
        self.assertGreater(len(results), 0)

        top_category = results[0]["metadata"].get("category", "")
        self.assertIn("乳制品", top_category, f"查询'牛奶'应返回乳制品，实际: {top_category}")


class TestNutritionRAGEdgeCases(unittest.TestCase):
    """边缘情况测试"""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="lifehub_test_edge_")
        cls.db_path = os.path.join(cls.temp_dir, "chroma_edge")
        from app.services.vector_service import VectorService
        cls.vector_service = VectorService(db_path=cls.db_path)

    @classmethod
    def tearDownClass(cls):
        try:
            if cls.vector_service:
                cls.vector_service.close()
            shutil.rmtree(cls.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def _create_mock_service(self):
        from app.services.nutrition_rag_service import NutritionRAGService
        import numpy as np

        mock_es = MagicMock()
        mock_es.dimension = 64

        def fake_embed_texts(texts, **kwargs):
            return [np.random.randn(64).tolist() for _ in texts]

        def fake_embed_text(text, **kwargs):
            return np.random.randn(64).tolist()

        mock_es.embed_texts = fake_embed_texts
        mock_es.embed_text = fake_embed_text

        return NutritionRAGService(
            vector_service=self.vector_service,
            embedding_service=mock_es,
        )

    def test_unicode_food_names(self):
        """测试 Unicode 食物名称"""
        svc = self._create_mock_service()
        svc.build_knowledge_base(force_rebuild=True)

        # 测试包含特殊字符的查询
        results = svc.search_nutrition("鱼香肉丝（微辣）", top_k=3)
        self.assertIsInstance(results, list)

    def test_very_long_query(self):
        """测试超长查询"""
        svc = self._create_mock_service()
        svc.build_knowledge_base(force_rebuild=True)

        long_query = "番茄炒蛋" * 100
        results = svc.search_nutrition(long_query, top_k=3)
        self.assertIsInstance(results, list)

    def test_special_characters_query(self):
        """测试特殊字符查询"""
        svc = self._create_mock_service()
        svc.build_knowledge_base(force_rebuild=True)

        for query in ["123", "!@#$%", "   空格   ", "abc"]:
            results = svc.search_nutrition(query, top_k=3)
            self.assertIsInstance(results, list)

    def test_top_k_boundary(self):
        """测试 top_k 边界值"""
        svc = self._create_mock_service()
        svc.build_knowledge_base(force_rebuild=True)

        # top_k=1
        results = svc.search_nutrition("米饭", top_k=1)
        self.assertLessEqual(len(results), 1)

        # top_k=100（大于数据量）
        results = svc.search_nutrition("米饭", top_k=100)
        self.assertIsInstance(results, list)

    def test_concurrent_search(self):
        """测试并发检索"""
        import threading

        svc = self._create_mock_service()
        svc.build_knowledge_base(force_rebuild=True)

        results_container = {}
        errors = []

        def search_task(food, idx):
            try:
                results_container[idx] = svc.search_nutrition(food, top_k=2)
            except Exception as e:
                errors.append((idx, str(e)))

        foods = ["番茄炒蛋", "鸡胸肉", "牛奶", "米饭", "红烧肉"]
        threads = [
            threading.Thread(target=search_task, args=(f, i))
            for i, f in enumerate(foods)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        self.assertEqual(len(errors), 0, f"并发检索出错: {errors}")
        self.assertEqual(len(results_container), len(foods))

    def test_invalid_data_file_format(self):
        """测试无效的数据文件格式"""
        svc = self._create_mock_service()

        # 创建无效 JSON 文件
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        try:
            tmp.write("this is not valid json {{{")
            tmp.close()
            data = svc.load_knowledge_data(tmp.name)
            self.assertEqual(data, [])
        finally:
            os.unlink(tmp.name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
