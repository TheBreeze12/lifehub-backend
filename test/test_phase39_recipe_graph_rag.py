"""
Phase 39 测试：菜谱知识图谱 RAG（过敏原推理增强）

测试内容：
1. 知识图谱数据文件完整性和 schema 验证
2. RecipeGraphService - 数据加载、构建、检索、过敏原推理
3. AllergenService - check_allergens_with_rag 增强检测
4. 隐性过敏原检测对比（RAG 前后准确率对比）
5. 边缘情况 - 空查询、不匹配菜品、重复构建、增量添加等

注意：测试使用临时目录存储 ChromaDB 数据，测试结束后自动清理。
嵌入模型测试使用 mock（单元测试）和真实 BGE-M3（集成测试，可选）。
"""

import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ================================================================
# 知识图谱数据文件完整性测试
# ================================================================


class TestRecipeDataFile(unittest.TestCase):
    """测试菜谱知识图谱数据文件完整性"""

    def test_data_file_exists(self):
        """测试数据文件存在"""
        from app.services.recipe_graph_service import DEFAULT_RECIPE_DATA_FILE
        self.assertTrue(
            os.path.exists(DEFAULT_RECIPE_DATA_FILE),
            f"菜谱知识图谱数据文件不存在: {DEFAULT_RECIPE_DATA_FILE}",
        )

    def test_data_file_valid_json(self):
        """测试数据文件是有效的 JSON"""
        from app.services.recipe_graph_service import DEFAULT_RECIPE_DATA_FILE
        with open(DEFAULT_RECIPE_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0, "数据文件不能为空")

    def test_data_file_schema(self):
        """测试每条数据的 schema 正确"""
        from app.services.recipe_graph_service import DEFAULT_RECIPE_DATA_FILE
        with open(DEFAULT_RECIPE_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        required_fields = ["dish_name", "ingredients", "allergens"]

        for i, item in enumerate(data):
            for field in required_fields:
                self.assertIn(
                    field, item,
                    f"第 {i} 条数据缺少字段: {field}, 菜品: {item.get('dish_name', '?')}",
                )
            # ingredients 应为非空列表
            self.assertIsInstance(
                item["ingredients"], list,
                f"第 {i} 条数据 ingredients 不是列表: {item['dish_name']}",
            )
            self.assertGreater(
                len(item["ingredients"]), 0,
                f"第 {i} 条数据 ingredients 不能为空: {item['dish_name']}",
            )
            # allergens 应为字典
            self.assertIsInstance(
                item["allergens"], dict,
                f"第 {i} 条数据 allergens 不是字典: {item['dish_name']}",
            )

    def test_data_allergen_codes_valid(self):
        """测试过敏原代码都是有效的八大类代码"""
        from app.services.recipe_graph_service import DEFAULT_RECIPE_DATA_FILE
        from app.services.allergen_service import ALLERGEN_CATEGORIES

        valid_codes = set(ALLERGEN_CATEGORIES.keys())

        with open(DEFAULT_RECIPE_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            for code in item.get("allergens", {}).keys():
                self.assertIn(
                    code, valid_codes,
                    f"菜品 '{item['dish_name']}' 含无效过敏原代码: {code}，"
                    f"有效代码: {valid_codes}",
                )

    def test_data_allergen_structure(self):
        """测试每个过敏原条目包含必要字段"""
        from app.services.recipe_graph_service import DEFAULT_RECIPE_DATA_FILE
        with open(DEFAULT_RECIPE_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            for code, info in item.get("allergens", {}).items():
                self.assertIsInstance(
                    info, dict,
                    f"菜品 '{item['dish_name']}' 过敏原 '{code}' 的值不是字典",
                )
                self.assertIn(
                    "direct", info,
                    f"菜品 '{item['dish_name']}' 过敏原 '{code}' 缺少 'direct' 字段",
                )
                self.assertIn(
                    "ingredient", info,
                    f"菜品 '{item['dish_name']}' 过敏原 '{code}' 缺少 'ingredient' 字段",
                )
                self.assertIsInstance(
                    info["direct"], bool,
                    f"菜品 '{item['dish_name']}' 过敏原 '{code}' 的 'direct' 字段不是布尔值",
                )

    def test_data_has_hidden_allergens(self):
        """测试数据中包含隐性过敏原（非直接）的菜品"""
        from app.services.recipe_graph_service import DEFAULT_RECIPE_DATA_FILE
        with open(DEFAULT_RECIPE_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        dishes_with_hidden = []
        for item in data:
            for code, info in item.get("allergens", {}).items():
                if isinstance(info, dict) and not info.get("direct", True):
                    dishes_with_hidden.append(item["dish_name"])
                    break

        self.assertGreater(
            len(dishes_with_hidden), 5,
            f"含隐性过敏原的菜品数量不足（至少5个），实际: {len(dishes_with_hidden)}",
        )

    def test_data_covers_all_allergen_types(self):
        """测试数据覆盖全部八大类过敏原"""
        from app.services.recipe_graph_service import DEFAULT_RECIPE_DATA_FILE
        from app.services.allergen_service import ALLERGEN_CATEGORIES

        with open(DEFAULT_RECIPE_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        covered_codes = set()
        for item in data:
            covered_codes.update(item.get("allergens", {}).keys())

        expected_codes = set(ALLERGEN_CATEGORIES.keys())
        missing = expected_codes - covered_codes
        self.assertEqual(
            missing, set(),
            f"数据未覆盖以下过敏原类型: {missing}",
        )

    def test_data_has_high_risk_dishes(self):
        """测试数据包含已知高隐性过敏原风险菜品"""
        from app.services.recipe_graph_service import DEFAULT_RECIPE_DATA_FILE
        with open(DEFAULT_RECIPE_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        dish_names = set()
        for item in data:
            dish_names.add(item["dish_name"])
            for alias in item.get("aliases", []):
                dish_names.add(alias)

        # 关键菜品：沙茶酱含花生是 Phase 39 验证要求
        high_risk = ["沙茶酱牛肉", "宫保鸡丁", "咖喱鸡"]
        for dish in high_risk:
            found = any(dish in name for name in dish_names)
            self.assertTrue(
                found,
                f"数据缺少高风险菜品: {dish}",
            )

    def test_data_satay_sauce_has_peanut(self):
        """验证关键场景：沙茶酱含花生（Phase 39 核心验证）"""
        from app.services.recipe_graph_service import DEFAULT_RECIPE_DATA_FILE
        with open(DEFAULT_RECIPE_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        satay_dish = None
        for item in data:
            if "沙茶" in item["dish_name"]:
                satay_dish = item
                break

        self.assertIsNotNone(satay_dish, "数据中应包含沙茶酱相关菜品")
        self.assertIn("peanut", satay_dish["allergens"], "沙茶酱菜品应标注花生过敏原")
        self.assertIn("shellfish", satay_dish["allergens"], "沙茶酱菜品应标注甲壳类过敏原")

    def test_data_no_duplicates(self):
        """测试数据中无重复菜品名称"""
        from app.services.recipe_graph_service import DEFAULT_RECIPE_DATA_FILE
        with open(DEFAULT_RECIPE_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        names = [item["dish_name"] for item in data]
        duplicates = [n for n in names if names.count(n) > 1]
        self.assertEqual(
            len(set(duplicates)), 0,
            f"数据中有重复菜品名称: {set(duplicates)}",
        )

    def test_data_has_hidden_allergen_notes(self):
        """测试大部分菜品有隐性过敏原说明"""
        from app.services.recipe_graph_service import DEFAULT_RECIPE_DATA_FILE
        with open(DEFAULT_RECIPE_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        with_notes = sum(1 for item in data if item.get("hidden_allergen_notes"))
        ratio = with_notes / len(data) if data else 0
        self.assertGreater(
            ratio, 0.8,
            f"有隐性过敏原说明的菜品比例过低: {ratio:.1%}",
        )


# ================================================================
# RecipeGraphService 单元测试（不加载模型）
# ================================================================


class TestRecipeGraphServiceUnit(unittest.TestCase):
    """RecipeGraphService 单元测试"""

    def test_import(self):
        """测试模块可以正常导入"""
        from app.services.recipe_graph_service import (
            RecipeGraphService,
            get_recipe_graph_service,
            RECIPE_GRAPH_COLLECTION,
        )
        self.assertIsNotNone(RecipeGraphService)
        self.assertEqual(RECIPE_GRAPH_COLLECTION, "recipe_knowledge_graph")

    def test_init(self):
        """测试初始化"""
        from app.services.recipe_graph_service import RecipeGraphService
        svc = RecipeGraphService()
        self.assertFalse(svc._initialized)

    def test_load_recipe_data_default(self):
        """测试加载默认数据文件"""
        from app.services.recipe_graph_service import RecipeGraphService
        svc = RecipeGraphService()
        data = svc.load_recipe_data()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_load_recipe_data_nonexistent_file(self):
        """测试加载不存在的数据文件"""
        from app.services.recipe_graph_service import RecipeGraphService
        svc = RecipeGraphService()
        data = svc.load_recipe_data("/nonexistent/path/data.json")
        self.assertEqual(data, [])

    def test_load_recipe_data_custom_file(self):
        """测试加载自定义数据文件"""
        from app.services.recipe_graph_service import RecipeGraphService
        svc = RecipeGraphService()

        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        try:
            json.dump(
                [{"dish_name": "测试菜", "ingredients": ["a"], "allergens": {"egg": {"direct": True, "ingredient": "鸡蛋", "note": "test"}}}],
                tmp, ensure_ascii=False,
            )
            tmp.close()
            data = svc.load_recipe_data(tmp.name)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["dish_name"], "测试菜")
        finally:
            os.unlink(tmp.name)

    def test_recipe_to_text(self):
        """测试菜谱数据转文本"""
        from app.services.recipe_graph_service import RecipeGraphService
        svc = RecipeGraphService()

        recipe = {
            "dish_name": "宫保鸡丁",
            "aliases": ["宫爆鸡丁"],
            "ingredients": ["鸡胸肉", "花生米", "辣椒"],
            "allergens": {
                "peanut": {"direct": True, "ingredient": "花生米", "note": "花生是核心配料"},
                "soy": {"direct": True, "ingredient": "酱油", "note": "含大豆"},
            },
            "hidden_allergen_notes": "花生是标志性配料",
        }
        text = svc._recipe_to_text(recipe)

        self.assertIn("宫保鸡丁", text)
        self.assertIn("宫爆鸡丁", text)
        self.assertIn("花生米", text)
        self.assertIn("花生是核心配料", text)
        self.assertIn("花生是标志性配料", text)
        self.assertIn("直接", text)

    def test_recipe_to_text_minimal(self):
        """测试最小化数据转文本"""
        from app.services.recipe_graph_service import RecipeGraphService
        svc = RecipeGraphService()

        recipe = {"dish_name": "未知菜品"}
        text = svc._recipe_to_text(recipe)
        self.assertIn("未知菜品", text)

    def test_recipe_to_metadata(self):
        """测试菜谱数据转元数据"""
        from app.services.recipe_graph_service import RecipeGraphService
        svc = RecipeGraphService()

        recipe = {
            "dish_name": "沙茶酱牛肉",
            "aliases": ["沙茶牛肉"],
            "ingredients": ["牛肉", "沙茶酱"],
            "allergens": {
                "peanut": {"direct": True, "ingredient": "沙茶酱(含花生)", "note": ""},
                "shellfish": {"direct": True, "ingredient": "沙茶酱(含虾酱)", "note": ""},
                "fish": {"direct": False, "ingredient": "沙茶酱(含鱼露)", "note": ""},
            },
            "hidden_allergen_notes": "沙茶酱含花生和虾酱",
        }
        meta = svc._recipe_to_metadata(recipe)

        self.assertEqual(meta["dish_name"], "沙茶酱牛肉")
        self.assertEqual(meta["allergen_count"], 3)

        allergen_codes = json.loads(meta["allergen_codes"])
        self.assertIn("peanut", allergen_codes)
        self.assertIn("shellfish", allergen_codes)
        self.assertIn("fish", allergen_codes)

        direct_codes = json.loads(meta["direct_allergen_codes"])
        self.assertIn("peanut", direct_codes)
        self.assertNotIn("fish", direct_codes)

        hidden_codes = json.loads(meta["hidden_allergen_codes"])
        self.assertIn("fish", hidden_codes)
        self.assertNotIn("peanut", hidden_codes)

    def test_recipe_to_metadata_empty(self):
        """测试空数据的元数据"""
        from app.services.recipe_graph_service import RecipeGraphService
        svc = RecipeGraphService()

        recipe = {"dish_name": "空菜品"}
        meta = svc._recipe_to_metadata(recipe)
        self.assertEqual(meta["dish_name"], "空菜品")
        self.assertEqual(meta["allergen_count"], 0)

    def test_singleton_pattern(self):
        """测试单例模式"""
        from app.services import recipe_graph_service as mod
        mod._default_instance = None
        svc1 = mod.get_recipe_graph_service()
        svc2 = mod.get_recipe_graph_service()
        self.assertIs(svc1, svc2)
        mod._default_instance = None

    def test_empty_allergen_context(self):
        """测试空过敏原上下文"""
        from app.services.recipe_graph_service import RecipeGraphService
        ctx = RecipeGraphService._empty_allergen_context()
        self.assertEqual(ctx["matched_recipes"], [])
        self.assertEqual(ctx["all_allergen_codes"], [])
        self.assertEqual(ctx["direct_allergens"], {})
        self.assertEqual(ctx["hidden_allergens"], {})
        self.assertEqual(ctx["reasoning_text"], "")

    def test_empty_allergen_detail(self):
        """测试空过敏原详情"""
        from app.services.recipe_graph_service import RecipeGraphService
        detail = RecipeGraphService._empty_allergen_detail()
        self.assertFalse(detail["matched"])
        self.assertEqual(detail["allergen_codes"], [])


# ================================================================
# RecipeGraphService 集成测试（使用临时 ChromaDB + mock 嵌入）
# ================================================================


class TestRecipeGraphServiceWithVectorDB(unittest.TestCase):
    """RecipeGraphService 集成测试（临时 ChromaDB + mock 嵌入）"""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="lifehub_test_recipe_rag_")
        cls.db_path = os.path.join(cls.temp_dir, "chroma_test")
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
        """创建使用 mock 嵌入的服务"""
        from app.services.recipe_graph_service import RecipeGraphService

        mock_es = MagicMock()
        mock_es.dimension = 64

        def fake_embed_texts(texts, is_query=False, **kwargs):
            vecs = []
            for t in texts:
                np.random.seed(hash(t) % (2**31))
                vecs.append(np.random.randn(64).tolist())
            return vecs

        def fake_embed_text(text, is_query=False, **kwargs):
            np.random.seed(hash(text) % (2**31))
            return np.random.randn(64).tolist()

        mock_es.embed_texts = fake_embed_texts
        mock_es.embed_text = fake_embed_text

        return RecipeGraphService(
            vector_service=self.vector_service,
            embedding_service=mock_es,
        )

    def test_build_knowledge_base(self):
        """测试构建知识图谱"""
        svc = self._create_mock_service()
        count = svc.build_knowledge_base(force_rebuild=True)
        self.assertGreater(count, 0, "应成功插入至少1条记录")

        from app.services.recipe_graph_service import RECIPE_GRAPH_COLLECTION
        self.assertTrue(self.vector_service.has_collection(RECIPE_GRAPH_COLLECTION))

        stats = svc.get_knowledge_base_stats()
        self.assertTrue(stats["exists"])
        self.assertEqual(stats["row_count"], count)

    def test_build_knowledge_base_idempotent(self):
        """测试幂等构建"""
        svc = self._create_mock_service()
        count1 = svc.build_knowledge_base(force_rebuild=True)
        count2 = svc.build_knowledge_base(force_rebuild=False)
        self.assertEqual(count1, count2)

    def test_build_knowledge_base_force_rebuild(self):
        """测试强制重建"""
        svc = self._create_mock_service()
        count1 = svc.build_knowledge_base(force_rebuild=True)
        count2 = svc.rebuild_knowledge_base()
        self.assertEqual(count1, count2)

    def test_search_recipe(self):
        """测试菜谱检索"""
        svc = self._create_mock_service()
        svc.build_knowledge_base(force_rebuild=True)

        results = svc.search_recipe("宫保鸡丁", top_k=3)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

        for r in results:
            self.assertIn("id", r)
            self.assertIn("distance", r)
            self.assertIn("text", r)
            self.assertIn("metadata", r)

    def test_search_recipe_empty_query(self):
        """测试空查询"""
        svc = self._create_mock_service()
        self.assertEqual(svc.search_recipe(""), [])
        self.assertEqual(svc.search_recipe("   "), [])

    def test_get_allergen_context(self):
        """测试过敏原上下文获取"""
        svc = self._create_mock_service()
        svc.build_knowledge_base(force_rebuild=True)

        context = svc.get_allergen_context("沙茶酱牛肉", top_k=3, max_distance=2.0)
        self.assertIsInstance(context, dict)
        self.assertIn("matched_recipes", context)
        self.assertIn("all_allergen_codes", context)
        self.assertIn("direct_allergens", context)
        self.assertIn("hidden_allergens", context)
        self.assertIn("reasoning_text", context)

    def test_get_allergen_context_empty(self):
        """测试无匹配时的过敏原上下文"""
        svc = self._create_mock_service()
        context = svc.get_allergen_context("")
        self.assertEqual(context["matched_recipes"], [])

    def test_get_hidden_allergens_for_dish(self):
        """测试获取隐性过敏原"""
        svc = self._create_mock_service()
        svc.build_knowledge_base(force_rebuild=True)

        hidden = svc.get_hidden_allergens_for_dish("沙茶酱牛肉", max_distance=2.0)
        self.assertIsInstance(hidden, list)

    def test_get_full_allergen_detail(self):
        """测试获取完整过敏原详情"""
        svc = self._create_mock_service()
        svc.build_knowledge_base(force_rebuild=True)

        detail = svc.get_full_allergen_detail("宫保鸡丁", max_distance=2.0)
        self.assertIsInstance(detail, dict)
        self.assertIn("matched", detail)
        self.assertIn("allergen_codes", detail)
        self.assertIn("ingredients", detail)

    def test_get_full_allergen_detail_no_match(self):
        """测试无匹配时的详情"""
        svc = self._create_mock_service()
        svc.build_knowledge_base(force_rebuild=True)

        detail = svc.get_full_allergen_detail("完全不存在的菜", max_distance=0.001)
        self.assertFalse(detail["matched"])

    def test_add_recipe_knowledge(self):
        """测试增量添加菜谱知识"""
        svc = self._create_mock_service()
        svc.build_knowledge_base(force_rebuild=True)

        stats_before = svc.get_knowledge_base_stats()
        count_before = stats_before["row_count"]

        new_recipe = {
            "dish_name": "测试新菜品XYZ",
            "aliases": ["测试别名"],
            "ingredients": ["测试配料A", "测试配料B"],
            "allergens": {
                "egg": {"direct": True, "ingredient": "鸡蛋", "note": "测试"},
            },
            "hidden_allergen_notes": "仅用于测试",
        }
        record_id = svc.add_recipe_knowledge(new_recipe)
        self.assertIsNotNone(record_id)
        self.assertIsInstance(record_id, str)

        stats_after = svc.get_knowledge_base_stats()
        self.assertEqual(stats_after["row_count"], count_before + 1)

    def test_ensure_initialized(self):
        """测试确保初始化"""
        svc = self._create_mock_service()
        svc._initialized = False

        from app.services.recipe_graph_service import RECIPE_GRAPH_COLLECTION
        if self.vector_service.has_collection(RECIPE_GRAPH_COLLECTION):
            self.vector_service.drop_collection(RECIPE_GRAPH_COLLECTION)

        result = svc.ensure_initialized()
        self.assertTrue(result)
        self.assertTrue(svc._initialized)

    def test_build_with_empty_data(self):
        """测试使用空数据文件构建"""
        svc = self._create_mock_service()

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

    def test_search_nonexistent_dish(self):
        """测试检索不存在的菜品"""
        svc = self._create_mock_service()
        svc.build_knowledge_base(force_rebuild=True)

        results = svc.search_recipe("外星生物料理ZZZZZ")
        self.assertIsInstance(results, list)

    def test_get_knowledge_base_stats_no_collection(self):
        """测试集合不存在时的统计"""
        from app.services.recipe_graph_service import RecipeGraphService, RECIPE_GRAPH_COLLECTION
        svc = RecipeGraphService(
            vector_service=self.vector_service,
            embedding_service=MagicMock(),
        )
        if self.vector_service.has_collection(RECIPE_GRAPH_COLLECTION):
            self.vector_service.drop_collection(RECIPE_GRAPH_COLLECTION)

        stats = svc.get_knowledge_base_stats()
        self.assertFalse(stats["exists"])
        self.assertEqual(stats["row_count"], 0)

    def test_invalid_data_file_format(self):
        """测试无效的数据文件格式"""
        svc = self._create_mock_service()

        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        try:
            tmp.write("this is not valid json {{{")
            tmp.close()
            data = svc.load_recipe_data(tmp.name)
            self.assertEqual(data, [])
        finally:
            os.unlink(tmp.name)


# ================================================================
# AllergenService - RAG 增强检测测试
# ================================================================


class TestAllergenServiceWithRAG(unittest.TestCase):
    """测试 AllergenService 的 RAG 增强检测"""

    def test_check_allergens_with_rag_method_exists(self):
        """测试 check_allergens_with_rag 方法存在"""
        from app.services.allergen_service import AllergenService
        svc = AllergenService()
        self.assertTrue(
            hasattr(svc, "check_allergens_with_rag"),
            "AllergenService 应有 check_allergens_with_rag 方法",
        )

    def test_check_allergens_with_rag_returns_valid_structure(self):
        """测试 RAG 增强检测返回有效结构"""
        from app.services.allergen_service import AllergenService

        svc = AllergenService()

        # Mock recipe_graph_service 返回空匹配（降级场景）
        with patch("app.services.recipe_graph_service.get_recipe_graph_service") as mock_rgs:
            mock_service = MagicMock()
            mock_service.get_full_allergen_detail.return_value = {
                "matched": False,
                "allergen_codes": [],
            }
            mock_rgs.return_value = mock_service

            result = svc.check_allergens_with_rag("番茄炒蛋")

            self.assertIn("food_name", result)
            self.assertIn("detected_allergens", result)
            self.assertIn("has_allergens", result)
            self.assertEqual(result["food_name"], "番茄炒蛋")

    def test_rag_enhances_detection_satay_sauce(self):
        """核心测试：沙茶酱牛肉应通过 RAG 检测到花生过敏原"""
        from app.services.allergen_service import AllergenService

        svc = AllergenService()

        # 纯关键词检测：沙茶酱牛肉不含花生关键词
        keyword_result = svc.check_allergens("沙茶酱牛肉")
        keyword_codes = {a["code"] for a in keyword_result["detected_allergens"]}
        # 沙茶酱牛肉中"牛"不直接匹配任何过敏原关键词
        # （"酱"也没有直接匹配）

        # 模拟 RAG 增强检测
        with patch(
            "app.services.recipe_graph_service.get_recipe_graph_service"
        ) as mock_rgs:
            mock_service = MagicMock()
            mock_service.get_full_allergen_detail.return_value = {
                "matched": True,
                "dish_name": "沙茶酱牛肉",
                "distance": 0.1,
                "ingredients": ["牛肉", "沙茶酱"],
                "allergen_codes": ["peanut", "shellfish", "fish", "soy"],
                "direct_allergen_codes": ["peanut", "shellfish"],
                "hidden_allergen_codes": ["fish"],
                "hidden_allergen_notes": "沙茶酱含花生和虾酱",
            }
            mock_rgs.return_value = mock_service

            rag_result = svc.check_allergens_with_rag("沙茶酱牛肉")

            rag_codes = {a["code"] for a in rag_result["detected_allergens"]}

            # RAG 应该检测出更多过敏原
            self.assertIn("peanut", rag_codes, "RAG 应检测到花生过敏原")
            self.assertIn("shellfish", rag_codes, "RAG 应检测到甲壳类过敏原")
            self.assertGreaterEqual(
                len(rag_codes), len(keyword_codes),
                "RAG 检测结果不应少于纯关键词",
            )

    def test_rag_detection_with_user_allergens_warning(self):
        """测试 RAG 增强检测配合用户过敏原告警"""
        from app.services.allergen_service import AllergenService

        svc = AllergenService()

        with patch(
            "app.services.recipe_graph_service.get_recipe_graph_service"
        ) as mock_rgs:
            mock_service = MagicMock()
            mock_service.get_full_allergen_detail.return_value = {
                "matched": True,
                "dish_name": "宫保鸡丁",
                "distance": 0.1,
                "ingredients": ["鸡胸肉", "花生米"],
                "allergen_codes": ["peanut", "soy"],
                "direct_allergen_codes": ["peanut", "soy"],
                "hidden_allergen_codes": [],
                "hidden_allergen_notes": "",
            }
            mock_rgs.return_value = mock_service

            result = svc.check_allergens_with_rag(
                "宫保鸡丁",
                user_allergens=["花生"],
            )

            self.assertTrue(result["has_warnings"], "应触发花生过敏告警")
            warning_allergens = [w["allergen"] for w in result["warnings"]]
            self.assertIn("花生", warning_allergens)

    def test_rag_graceful_degradation(self):
        """测试 RAG 服务异常时的优雅降级"""
        from app.services.allergen_service import AllergenService

        svc = AllergenService()

        with patch(
            "app.services.recipe_graph_service.get_recipe_graph_service"
        ) as mock_rgs:
            mock_rgs.side_effect = RuntimeError("知识图谱服务不可用")

            # 不应抛异常，而是降级为纯关键词检测
            result = svc.check_allergens_with_rag("番茄炒蛋")
            self.assertIsInstance(result, dict)
            self.assertIn("detected_allergens", result)

    def test_rag_adds_source_field(self):
        """测试 RAG 增强结果包含来源标识"""
        from app.services.allergen_service import AllergenService

        svc = AllergenService()

        with patch(
            "app.services.recipe_graph_service.get_recipe_graph_service"
        ) as mock_rgs:
            mock_service = MagicMock()
            mock_service.get_full_allergen_detail.return_value = {
                "matched": True,
                "dish_name": "沙茶酱牛肉",
                "distance": 0.1,
                "ingredients": ["牛肉", "沙茶酱"],
                "allergen_codes": ["peanut", "shellfish"],
                "direct_allergen_codes": ["peanut"],
                "hidden_allergen_codes": ["shellfish"],
                "hidden_allergen_notes": "沙茶酱含花生",
            }
            mock_rgs.return_value = mock_service

            result = svc.check_allergens_with_rag("沙茶酱牛肉")

            for allergen in result["detected_allergens"]:
                self.assertIn(
                    "source", allergen,
                    f"过敏原 {allergen['code']} 缺少 source 字段",
                )
                self.assertIn(
                    allergen["source"],
                    ["keyword", "rag", "keyword+rag"],
                    f"无效的 source 值: {allergen['source']}",
                )

    def test_rag_detection_methods_field(self):
        """测试结果包含 detection_methods 统计"""
        from app.services.allergen_service import AllergenService

        svc = AllergenService()

        with patch(
            "app.services.recipe_graph_service.get_recipe_graph_service"
        ) as mock_rgs:
            mock_service = MagicMock()
            mock_service.get_full_allergen_detail.return_value = {
                "matched": True,
                "dish_name": "宫保鸡丁",
                "distance": 0.1,
                "ingredients": ["鸡胸肉", "花生米"],
                "allergen_codes": ["peanut", "soy"],
                "direct_allergen_codes": ["peanut"],
                "hidden_allergen_codes": [],
                "hidden_allergen_notes": "",
            }
            mock_rgs.return_value = mock_service

            result = svc.check_allergens_with_rag("宫保鸡丁")

            self.assertIn("detection_methods", result)
            methods = result["detection_methods"]
            self.assertIn("keyword_count", methods)
            self.assertIn("rag_count", methods)
            self.assertIn("merged_count", methods)

    def test_merge_keyword_and_rag_deduplication(self):
        """测试合并时去重：关键词和 RAG 检测到相同过敏原"""
        from app.services.allergen_service import AllergenService

        svc = AllergenService()

        # 关键词检测 "宫保鸡丁" 能检测到花生（因为 "宫保" 在花生关键词中）
        keyword_result = svc.check_allergens("宫保鸡丁")

        merged = svc._merge_keyword_and_rag(
            food_name="宫保鸡丁",
            keyword_result=keyword_result,
            rag_allergen_codes=["peanut", "soy"],
            rag_reasoning="知识图谱检测",
            rag_ingredients=["鸡胸肉", "花生米"],
        )

        # 合并后不应有重复的过敏原代码
        codes = [a["code"] for a in merged["detected_allergens"]]
        self.assertEqual(len(codes), len(set(codes)), f"检测到重复: {codes}")

        # 同时被两种方法检测到的应标记 keyword+rag
        for allergen in merged["detected_allergens"]:
            if allergen["code"] == "peanut":
                self.assertEqual(
                    allergen["source"], "keyword+rag",
                    "花生应被关键词和RAG同时检测到",
                )

    def test_rag_reasoning_field(self):
        """测试 rag_reasoning 字段"""
        from app.services.allergen_service import AllergenService

        svc = AllergenService()

        with patch(
            "app.services.recipe_graph_service.get_recipe_graph_service"
        ) as mock_rgs:
            mock_service = MagicMock()
            mock_service.get_full_allergen_detail.return_value = {
                "matched": True,
                "dish_name": "沙茶酱牛肉",
                "distance": 0.1,
                "ingredients": ["牛肉", "沙茶酱"],
                "allergen_codes": ["peanut"],
                "direct_allergen_codes": ["peanut"],
                "hidden_allergen_codes": [],
                "hidden_allergen_notes": "沙茶酱含花生",
            }
            mock_rgs.return_value = mock_service

            result = svc.check_allergens_with_rag("沙茶酱牛肉")
            self.assertIn("rag_reasoning", result)
            self.assertIn("沙茶酱含花生", result["rag_reasoning"])


# ================================================================
# 隐性过敏原检测对比测试（RAG 前后准确率对比）
# ================================================================


class TestHiddenAllergenDetectionComparison(unittest.TestCase):
    """对比 RAG 前后过敏原检测能力

    重点验证 Phase 39 需求：含隐性过敏原菜品的检测准确率提升。
    """

    def setUp(self):
        from app.services.allergen_service import AllergenService
        self.svc = AllergenService()

    def test_satay_sauce_without_rag(self):
        """沙茶酱牛肉（无 RAG）：关键词无法检测到花生"""
        result = self.svc.check_allergens("沙茶酱牛肉")
        codes = {a["code"] for a in result["detected_allergens"]}
        # 纯关键词检测："沙茶酱牛肉"不包含"花生"关键词
        # 也不包含"虾"等关键词（"酱"不在甲壳类关键词中）
        self.assertNotIn(
            "peanut", codes,
            "纯关键词检测不应检测到沙茶酱中的花生（这是隐性过敏原）",
        )

    def test_gongbao_chicken_keyword_detection(self):
        """宫保鸡丁：关键词能检测到花生（"宫保"在花生关键词中）"""
        result = self.svc.check_allergens("宫保鸡丁")
        codes = {a["code"] for a in result["detected_allergens"]}
        self.assertIn("peanut", codes, "宫保鸡丁应能通过关键词'宫保'检测到花生")

    def test_hidden_allergen_dishes_comparison(self):
        """对比多道菜品的关键词检测覆盖率（说明 RAG 的必要性）"""
        # 这些菜品含隐性过敏原，关键词检测可能不全
        test_dishes = [
            {
                "name": "沙茶酱牛肉",
                "expected_hidden": ["peanut", "shellfish"],
                "note": "沙茶酱含花生和虾酱",
            },
            {
                "name": "咖喱鸡",
                "expected_hidden": ["milk", "wheat"],
                "note": "咖喱块含乳制品和面粉",
            },
            {
                "name": "蚝油生菜",
                "expected_hidden": ["shellfish"],
                "note": "蚝油含牡蛎提取物",
            },
            {
                "name": "XO酱炒菜",
                "expected_hidden": ["shellfish"],
                "note": "XO酱含干贝和虾米",
            },
        ]

        keyword_misses = 0
        total_hidden = 0

        for dish in test_dishes:
            result = self.svc.check_allergens(dish["name"])
            detected_codes = {a["code"] for a in result["detected_allergens"]}

            for hidden_code in dish["expected_hidden"]:
                total_hidden += 1
                if hidden_code not in detected_codes:
                    keyword_misses += 1

        # 关键词检测应漏掉一些隐性过敏原（证明 RAG 的必要性）
        self.assertGreater(
            keyword_misses, 0,
            "纯关键词检测应存在隐性过敏原漏检情况（否则 RAG 无必要性）",
        )

    def test_keyword_vs_rag_detection_count(self):
        """对比关键词与 RAG 增强后的检测数量"""
        from app.services.allergen_service import AllergenService

        svc = AllergenService()

        # 沙茶酱牛肉：关键词检测
        keyword_result = svc.check_allergens("沙茶酱牛肉")
        keyword_count = keyword_result["allergen_count"]

        # 沙茶酱牛肉：RAG 增强检测（mock）
        with patch(
            "app.services.recipe_graph_service.get_recipe_graph_service"
        ) as mock_rgs:
            mock_service = MagicMock()
            mock_service.get_full_allergen_detail.return_value = {
                "matched": True,
                "dish_name": "沙茶酱牛肉",
                "distance": 0.1,
                "ingredients": ["牛肉", "沙茶酱"],
                "allergen_codes": ["peanut", "shellfish", "fish", "soy"],
                "direct_allergen_codes": ["peanut", "shellfish"],
                "hidden_allergen_codes": ["fish"],
                "hidden_allergen_notes": "沙茶酱含花生和虾酱",
            }
            mock_rgs.return_value = mock_service

            rag_result = svc.check_allergens_with_rag("沙茶酱牛肉")
            rag_count = rag_result["allergen_count"]

        self.assertGreater(
            rag_count, keyword_count,
            f"RAG 增强后检测数量({rag_count})应多于纯关键词({keyword_count})",
        )


# ================================================================
# 边缘情况测试
# ================================================================


class TestRecipeGraphEdgeCases(unittest.TestCase):
    """边缘情况测试"""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="lifehub_test_recipe_edge_")
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
        from app.services.recipe_graph_service import RecipeGraphService

        mock_es = MagicMock()
        mock_es.dimension = 64

        def fake_embed_texts(texts, **kwargs):
            return [np.random.randn(64).tolist() for _ in texts]

        def fake_embed_text(text, **kwargs):
            return np.random.randn(64).tolist()

        mock_es.embed_texts = fake_embed_texts
        mock_es.embed_text = fake_embed_text

        return RecipeGraphService(
            vector_service=self.vector_service,
            embedding_service=mock_es,
        )

    def test_unicode_dish_names(self):
        """测试 Unicode 菜品名称"""
        svc = self._create_mock_service()
        svc.build_knowledge_base(force_rebuild=True)

        results = svc.search_recipe("鱼香肉丝（微辣）", top_k=3)
        self.assertIsInstance(results, list)

    def test_very_long_query(self):
        """测试超长查询"""
        svc = self._create_mock_service()
        svc.build_knowledge_base(force_rebuild=True)

        long_query = "宫保鸡丁" * 100
        results = svc.search_recipe(long_query, top_k=3)
        self.assertIsInstance(results, list)

    def test_special_characters_query(self):
        """测试特殊字符查询"""
        svc = self._create_mock_service()
        svc.build_knowledge_base(force_rebuild=True)

        for query in ["123", "!@#$%", "   空格   ", "abc"]:
            results = svc.search_recipe(query, top_k=3)
            self.assertIsInstance(results, list)

    def test_top_k_boundary(self):
        """测试 top_k 边界值"""
        svc = self._create_mock_service()
        svc.build_knowledge_base(force_rebuild=True)

        results = svc.search_recipe("宫保鸡丁", top_k=1)
        self.assertLessEqual(len(results), 1)

        results = svc.search_recipe("宫保鸡丁", top_k=100)
        self.assertIsInstance(results, list)

    def test_concurrent_search(self):
        """测试并发检索"""
        svc = self._create_mock_service()
        svc.build_knowledge_base(force_rebuild=True)

        results_container = {}
        errors = []

        def search_task(food, idx):
            try:
                results_container[idx] = svc.search_recipe(food, top_k=2)
            except Exception as e:
                errors.append((idx, str(e)))

        foods = ["宫保鸡丁", "沙茶酱牛肉", "番茄炒蛋", "咖喱鸡", "麻婆豆腐"]
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

    def test_allergen_context_max_distance_strict(self):
        """测试极小距离阈值过滤"""
        svc = self._create_mock_service()
        svc.build_knowledge_base(force_rebuild=True)

        context = svc.get_allergen_context("宫保鸡丁", max_distance=0.0001)
        self.assertEqual(context["matched_recipes"], [])

    def test_metadata_json_parsing_robustness(self):
        """测试元数据 JSON 解析的健壮性"""
        from app.services.recipe_graph_service import RecipeGraphService

        svc = RecipeGraphService()

        # 模拟损坏的元数据
        mock_result = {
            "metadata": {
                "dish_name": "测试",
                "allergen_codes": "invalid json",
                "direct_allergen_codes": "[]",
                "hidden_allergen_codes": "[]",
                "ingredients": "[]",
                "hidden_allergen_notes": "",
            },
            "distance": 0.5,
        }

        # 直接测试 get_allergen_context 的 JSON 解析逻辑
        # 构建 mock 使 search_recipe 返回上面的结果
        mock_vs = MagicMock()
        mock_es = MagicMock()
        mock_es.embed_text = MagicMock(return_value=[0.0] * 64)

        svc._vector_service = mock_vs
        svc._embedding_service = mock_es
        svc._initialized = True

        mock_vs.search.return_value = [mock_result]
        mock_vs.has_collection.return_value = True

        context = svc.get_allergen_context("测试", max_distance=1.0)
        # 不应抛出异常，应优雅处理
        self.assertIsInstance(context, dict)


# ================================================================
# 使用真实嵌入模型的集成测试（可选）
# ================================================================


class TestRecipeGraphWithRealEmbedding(unittest.TestCase):
    """使用真实 BGE-M3 嵌入模型的集成测试"""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="lifehub_test_real_recipe_")
        cls.db_path = os.path.join(cls.temp_dir, "chroma_real")

        from app.services.vector_service import VectorService
        cls.vector_service = VectorService(db_path=cls.db_path)

        cls.embedding_available = False
        try:
            from app.services.embedding_service import EmbeddingService
            cls.embedding_service = EmbeddingService(device="cpu")
            cls.embedding_service.embed_text("测试")
            cls.embedding_available = True
        except Exception as e:
            print(f"警告: 嵌入模型加载失败，跳过真实嵌入测试: {e}")
            cls.embedding_service = None

    @classmethod
    def tearDownClass(cls):
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
        from app.services.recipe_graph_service import RecipeGraphService
        return RecipeGraphService(
            vector_service=self.vector_service,
            embedding_service=self.embedding_service,
        )

    def test_real_build_and_search(self):
        """真实嵌入下的构建和检索"""
        svc = self._create_real_service()
        count = svc.build_knowledge_base(force_rebuild=True)
        self.assertGreater(count, 0)

        results = svc.search_recipe("宫保鸡丁", top_k=3)
        self.assertGreater(len(results), 0)

        top_result = results[0]
        self.assertLess(top_result["distance"], 1.0)

    def test_real_satay_sauce_detection(self):
        """真实嵌入下：沙茶酱牛肉应检索到沙茶相关条目"""
        svc = self._create_real_service()
        svc.build_knowledge_base(force_rebuild=True)

        results = svc.search_recipe("沙茶酱牛肉", top_k=3)
        self.assertGreater(len(results), 0)

        top_dish = results[0]["metadata"].get("dish_name", "")
        self.assertIn("沙茶", top_dish, f"查询'沙茶酱牛肉'应匹配沙茶相关菜品，实际: {top_dish}")

    def test_real_allergen_context_satay(self):
        """真实嵌入下：沙茶酱牛肉过敏原上下文应含花生"""
        svc = self._create_real_service()
        svc.build_knowledge_base(force_rebuild=True)

        context = svc.get_allergen_context("沙茶酱牛肉", max_distance=1.0)
        all_codes = context.get("all_allergen_codes", [])
        self.assertIn("peanut", all_codes, f"沙茶酱牛肉应检测到花生，实际: {all_codes}")

    def test_real_allergen_detail_gongbao(self):
        """真实嵌入下：宫保鸡丁详情应含花生"""
        svc = self._create_real_service()
        svc.build_knowledge_base(force_rebuild=True)

        detail = svc.get_full_allergen_detail("宫保鸡丁", max_distance=1.0)
        self.assertTrue(detail["matched"])
        self.assertIn("peanut", detail["allergen_codes"])

    def test_real_hidden_allergens(self):
        """真实嵌入下：获取沙茶酱牛肉的隐性过敏原"""
        svc = self._create_real_service()
        svc.build_knowledge_base(force_rebuild=True)

        hidden = svc.get_hidden_allergens_for_dish("沙茶酱牛肉", max_distance=1.0)
        hidden_codes = [h["code"] for h in hidden]
        # 鱼露是沙茶酱的隐性过敏原
        self.assertIn("fish", hidden_codes, f"沙茶酱应含隐性鱼类过敏原，实际: {hidden_codes}")

    def test_real_alias_search(self):
        """真实嵌入下：别名搜索"""
        svc = self._create_real_service()
        svc.build_knowledge_base(force_rebuild=True)

        results = svc.search_recipe("宫爆鸡丁", top_k=3)
        self.assertGreater(len(results), 0)

        food_names = [r["metadata"].get("dish_name", "") for r in results]
        found = any("宫保" in fn or "宫爆" in fn for fn in food_names)
        self.assertTrue(found, f"别名'宫爆鸡丁'应匹配到宫保鸡丁，实际: {food_names}")

    def test_real_no_fish_in_yuxiang(self):
        """真实嵌入下：鱼香肉丝应不含鱼类过敏原"""
        svc = self._create_real_service()
        svc.build_knowledge_base(force_rebuild=True)

        detail = svc.get_full_allergen_detail("鱼香肉丝", max_distance=1.0)
        if detail["matched"] and "鱼香" in detail["dish_name"]:
            self.assertNotIn(
                "fish", detail.get("direct_allergen_codes", []),
                "鱼香肉丝不含鱼类，不应有鱼类直接过敏原",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
