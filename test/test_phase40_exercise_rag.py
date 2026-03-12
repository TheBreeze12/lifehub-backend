"""
Phase 40 测试：运动消耗库 RAG 检索增强

测试内容：
1. 运动消耗知识库数据文件完整性和 schema 验证
2. ExerciseRAGService - 数据加载、构建、检索
3. METsService - RAG 增强后的 METs 查询（原有功能回归 + 新增小众运动）
4. 边缘情况 - 空查询、不匹配运动、重复构建等
5. 热量计算准确性 - RAG 增强前后对比

注意：测试使用临时目录存储 ChromaDB 数据，测试结束后自动清理。
嵌入模型测试使用 mock（单元测试）。
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ================================================================
# 运动消耗知识库数据文件完整性测试
# ================================================================


class TestExerciseDataFile(unittest.TestCase):
    """测试运动消耗知识库数据文件完整性"""

    def test_data_file_exists(self):
        """测试数据文件存在"""
        data_file = os.path.join(
            PROJECT_ROOT, "data", "exercise_knowledge", "exercise_mets_data.json"
        )
        self.assertTrue(
            os.path.exists(data_file),
            f"运动消耗知识库数据文件不存在: {data_file}",
        )

    def test_data_file_valid_json(self):
        """测试数据文件是有效的 JSON"""
        data_file = os.path.join(
            PROJECT_ROOT, "data", "exercise_knowledge", "exercise_mets_data.json"
        )
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0, "数据文件不能为空")

    def test_data_has_100_plus_exercises(self):
        """测试数据文件包含100+种运动"""
        data_file = os.path.join(
            PROJECT_ROOT, "data", "exercise_knowledge", "exercise_mets_data.json"
        )
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertGreaterEqual(
            len(data), 100, f"运动类型不足100种，当前: {len(data)}"
        )

    def test_data_file_schema(self):
        """测试每条数据的 schema 正确"""
        data_file = os.path.join(
            PROJECT_ROOT, "data", "exercise_knowledge", "exercise_mets_data.json"
        )
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        required_fields = [
            "exercise_name", "aliases", "category", "mets",
            "intensity", "description",
        ]

        for i, item in enumerate(data):
            for field in required_fields:
                self.assertIn(
                    field, item,
                    f"第 {i} 条数据缺少字段: {field}, 运动: {item.get('exercise_name', '?')}",
                )
            # exercise_name 应为非空字符串
            self.assertIsInstance(item["exercise_name"], str)
            self.assertGreater(len(item["exercise_name"]), 0)
            # aliases 应为列表
            self.assertIsInstance(item["aliases"], list)
            # mets 应为正数
            self.assertIsInstance(item["mets"], (int, float))
            self.assertGreater(item["mets"], 0, f"METs值必须为正: {item['exercise_name']}")
            # intensity 应为有效值
            self.assertIn(
                item["intensity"],
                ["light", "moderate", "vigorous"],
                f"强度值无效: {item['exercise_name']}: {item['intensity']}",
            )

    def test_data_no_duplicate_names(self):
        """测试运动名称没有重复"""
        data_file = os.path.join(
            PROJECT_ROOT, "data", "exercise_knowledge", "exercise_mets_data.json"
        )
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        names = [item["exercise_name"] for item in data]
        duplicates = [n for n in names if names.count(n) > 1]
        self.assertEqual(
            len(set(duplicates)), 0,
            f"存在重复运动名称: {set(duplicates)}",
        )

    def test_data_covers_major_categories(self):
        """测试数据覆盖主要运动分类"""
        data_file = os.path.join(
            PROJECT_ROOT, "data", "exercise_knowledge", "exercise_mets_data.json"
        )
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        categories = set(item["category"] for item in data)
        expected_categories = {"步行类", "跑步类", "骑行类", "水上运动", "球类运动", "力量训练"}
        for cat in expected_categories:
            self.assertIn(
                cat, categories,
                f"缺少主要运动分类: {cat}，已有分类: {categories}",
            )

    def test_data_mets_values_reasonable(self):
        """测试METs值在合理范围内 (1.0 - 20.0)"""
        data_file = os.path.join(
            PROJECT_ROOT, "data", "exercise_knowledge", "exercise_mets_data.json"
        )
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            self.assertGreaterEqual(
                item["mets"], 1.0,
                f"METs值过低: {item['exercise_name']}: {item['mets']}",
            )
            self.assertLessEqual(
                item["mets"], 20.0,
                f"METs值过高: {item['exercise_name']}: {item['mets']}",
            )


# ================================================================
# ExerciseRAGService 单元测试（mock 嵌入模型）
# ================================================================


def _make_mock_vector(dim=1024):
    """生成随机 mock 向量"""
    v = np.random.randn(dim).astype(np.float32)
    v = v / np.linalg.norm(v)
    return v.tolist()


class TestExerciseRAGServiceUnit(unittest.TestCase):
    """ExerciseRAGService 单元测试（使用 mock）"""

    def setUp(self):
        """每个测试前准备临时 ChromaDB 和 mock 嵌入"""
        self.temp_dir = tempfile.mkdtemp(prefix="test_exercise_rag_")

        from app.services.vector_service import VectorService
        self.vector_service = VectorService(db_path=self.temp_dir)

        # mock 嵌入服务
        self.embedding_service = MagicMock()
        self.embedding_service.dimension = 1024
        self.embedding_service.embed_texts.side_effect = lambda texts, **kwargs: [
            _make_mock_vector() for _ in texts
        ]
        self.embedding_service.embed_text.side_effect = lambda text, **kwargs: _make_mock_vector()

        from app.services.exercise_rag_service import ExerciseRAGService
        self.service = ExerciseRAGService(
            vector_service=self.vector_service,
            embedding_service=self.embedding_service,
        )

    def tearDown(self):
        """每个测试后清理"""
        self.vector_service.close()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_exercise_data(self):
        """测试加载运动数据"""
        data = self.service.load_exercise_data()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0, "应该能加载到运动数据")

    def test_load_exercise_data_missing_file(self):
        """测试加载不存在的数据文件"""
        data = self.service.load_exercise_data("/nonexistent/path.json")
        self.assertEqual(data, [], "不存在的文件应返回空列表")

    def test_build_knowledge_base(self):
        """测试构建运动知识库"""
        count = self.service.build_knowledge_base()
        self.assertGreater(count, 0, "知识库构建应返回正数")
        self.assertTrue(self.service._initialized)

    def test_build_knowledge_base_idempotent(self):
        """测试重复构建（幂等性）"""
        count1 = self.service.build_knowledge_base()
        count2 = self.service.build_knowledge_base()
        # 第二次应返回已有数量（跳过构建）
        self.assertEqual(count1, count2)

    def test_build_knowledge_base_force_rebuild(self):
        """测试强制重建"""
        count1 = self.service.build_knowledge_base()
        count2 = self.service.build_knowledge_base(force_rebuild=True)
        self.assertGreater(count2, 0)

    def test_ensure_initialized(self):
        """测试确保初始化"""
        result = self.service.ensure_initialized()
        self.assertTrue(result)
        self.assertTrue(self.service._initialized)

    def test_search_exercise(self):
        """测试检索运动"""
        self.service.build_knowledge_base()
        results = self.service.search_exercise("跑步")
        self.assertIsInstance(results, list)
        # mock 下返回结果
        self.assertGreater(len(results), 0, "应该有检索结果")

    def test_search_exercise_empty_query(self):
        """测试空查询"""
        results = self.service.search_exercise("")
        self.assertEqual(results, [])
        results = self.service.search_exercise("   ")
        self.assertEqual(results, [])

    def test_get_exercise_mets_from_rag(self):
        """测试从RAG获取METs值"""
        self.service.build_knowledge_base()
        result = self.service.get_exercise_mets_from_rag("拳击")
        self.assertIsInstance(result, dict)
        # 应该包含必要字段
        for field in ["found", "exercise_name", "mets", "intensity", "category"]:
            self.assertIn(field, result, f"结果缺少字段: {field}")

    def test_get_exercise_mets_from_rag_empty(self):
        """测试空查询返回未找到"""
        result = self.service.get_exercise_mets_from_rag("")
        self.assertFalse(result["found"])

    def test_exercise_to_text_format(self):
        """测试运动数据转文本格式"""
        exercise = {
            "exercise_name": "跑步",
            "aliases": ["running", "中速跑"],
            "category": "跑步类",
            "mets": 8.0,
            "intensity": "vigorous",
            "description": "中等速度跑步（约8km/h）",
            "suitable_for": ["减脂", "耐力训练"],
        }
        text = self.service._exercise_to_text(exercise)
        self.assertIn("跑步", text)
        self.assertIn("8.0", text)
        self.assertIn("跑步类", text)

    def test_exercise_to_metadata_format(self):
        """测试运动数据转元数据格式"""
        exercise = {
            "exercise_name": "跑步",
            "aliases": ["running"],
            "category": "跑步类",
            "mets": 8.0,
            "intensity": "vigorous",
            "description": "中等速度跑步",
            "suitable_for": ["减脂"],
        }
        metadata = self.service._exercise_to_metadata(exercise)
        self.assertEqual(metadata["exercise_name"], "跑步")
        self.assertEqual(metadata["mets"], 8.0)
        self.assertEqual(metadata["intensity"], "vigorous")
        self.assertEqual(metadata["category"], "跑步类")

    def test_get_knowledge_base_stats(self):
        """测试获取知识库统计信息"""
        self.service.build_knowledge_base()
        stats = self.service.get_knowledge_base_stats()
        self.assertTrue(stats.get("exists", False))
        self.assertGreater(stats.get("row_count", 0), 0)

    def test_rebuild_knowledge_base(self):
        """测试重建知识库"""
        self.service.build_knowledge_base()
        count = self.service.rebuild_knowledge_base()
        self.assertGreater(count, 0)


# ================================================================
# METsService RAG 增强集成测试（mock 嵌入模型）
# ================================================================


class TestMETsServiceRAGIntegration(unittest.TestCase):
    """METsService RAG增强后的集成测试"""

    def setUp(self):
        """准备 METsService 实例和 mock RAG"""
        self.temp_dir = tempfile.mkdtemp(prefix="test_mets_rag_")

        from app.services.vector_service import VectorService
        self.vector_service = VectorService(db_path=self.temp_dir)

        self.embedding_service = MagicMock()
        self.embedding_service.dimension = 1024
        self.embedding_service.embed_texts.side_effect = lambda texts, **kwargs: [
            _make_mock_vector() for _ in texts
        ]
        self.embedding_service.embed_text.side_effect = lambda text, **kwargs: _make_mock_vector()

        from app.services.exercise_rag_service import ExerciseRAGService
        self.exercise_rag = ExerciseRAGService(
            vector_service=self.vector_service,
            embedding_service=self.embedding_service,
        )
        self.exercise_rag.build_knowledge_base()

        from app.services.mets_service import METsService
        self.mets_service = METsService(exercise_rag_service=self.exercise_rag)

    def tearDown(self):
        self.vector_service.close()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ---- 回归测试：确保原有功能不受影响 ----

    def test_existing_walking_mets(self):
        """回归：步行的METs值不变"""
        mets = self.mets_service.get_mets_value("walking")
        self.assertEqual(mets, 3.5)

    def test_existing_running_mets(self):
        """回归：跑步的METs值不变"""
        mets = self.mets_service.get_mets_value("running")
        self.assertEqual(mets, 8.0)

    def test_existing_chinese_mapping(self):
        """回归：中文映射仍然有效"""
        mets = self.mets_service.get_mets_value("慢跑")
        self.assertEqual(mets, 7.0)

    def test_existing_cycling_mets(self):
        """回归：骑行的METs值不变"""
        mets = self.mets_service.get_mets_value("cycling")
        self.assertEqual(mets, 6.0)

    def test_existing_swimming_mets(self):
        """回归：游泳的METs值不变"""
        mets = self.mets_service.get_mets_value("swimming")
        self.assertEqual(mets, 7.0)

    def test_existing_yoga_mets(self):
        """回归：瑜伽的METs值不变"""
        mets = self.mets_service.get_mets_value("yoga")
        self.assertEqual(mets, 2.5)

    def test_existing_calories_calculation(self):
        """回归：热量计算公式不变"""
        # 70kg * 8.0 METs * 0.5h = 280.0 kcal
        calories = self.mets_service.calculate_calories("running", 70.0, 30)
        self.assertEqual(calories, 280.0)

    def test_existing_duration_calculation(self):
        """回归：时长反推不变"""
        duration = self.mets_service.calculate_duration_for_target("running", 70.0, 280.0)
        self.assertEqual(duration, 30)

    def test_existing_normalize_empty(self):
        """回归：空类型返回walking"""
        normalized = self.mets_service._normalize_exercise_type("")
        self.assertEqual(normalized, "walking")

    def test_existing_get_all_exercise_types(self):
        """回归：get_all_exercise_types 仍然返回静态表"""
        types = self.mets_service.get_all_exercise_types()
        self.assertIn("walking", types)
        self.assertIn("running", types)

    # ---- 新增功能测试：RAG 增强 ----

    def test_rag_fallback_for_known_types(self):
        """已知运动类型应直接从静态表获取，不走RAG"""
        mets = self.mets_service.get_mets_value("running")
        self.assertEqual(mets, 8.0)

    def test_rag_lookup_returns_float(self):
        """RAG查找未知运动应返回浮点数"""
        mets = self.mets_service.get_mets_value("蝶泳训练")
        self.assertIsInstance(mets, float)
        self.assertGreater(mets, 0)

    def test_get_exercise_info_with_rag(self):
        """get_exercise_info 对未知运动应尝试RAG"""
        info = self.mets_service.get_exercise_info("攀岩")
        self.assertIn("mets", info)
        self.assertGreater(info["mets"], 0)

    def test_calculate_calories_with_rag_type(self):
        """使用RAG查找到的运动类型计算热量"""
        calories = self.mets_service.calculate_calories("综合格斗", 70.0, 60)
        self.assertIsInstance(calories, float)
        self.assertGreater(calories, 0)

    def test_calculate_calories_invalid_duration(self):
        """无效时长返回0"""
        self.assertEqual(self.mets_service.calculate_calories("running", 70, 0), 0.0)
        self.assertEqual(self.mets_service.calculate_calories("running", 70, -10), 0.0)

    def test_calculate_calories_no_weight(self):
        """未提供体重时使用默认值"""
        calories = self.mets_service.calculate_calories("running", None, 30)
        expected = 8.0 * 70.0 * 0.5  # DEFAULT_WEIGHT_KG = 70
        self.assertEqual(calories, expected)

    def test_calculate_for_trip_item_with_rag(self):
        """trip_item 计算应支持RAG增强"""
        item = {"placeType": "拳击馆", "duration": 60}
        calories = self.mets_service.calculate_for_trip_item(item, 70.0)
        self.assertIsInstance(calories, float)
        self.assertGreater(calories, 0)

    def test_get_all_exercise_types_expanded(self):
        """扩展后的运动类型应包含RAG数据"""
        types = self.mets_service.get_all_exercise_types_expanded()
        self.assertIsInstance(types, list)
        # 应该包含静态表 + RAG知识库
        self.assertGreater(len(types), 30)

    # ---- 边缘情况 ----

    def test_completely_unknown_exercise(self):
        """完全未知的运动类型应返回默认METs"""
        mets = self.mets_service.get_mets_value("量子纠缠运动")
        # 如果RAG也找不到，应返回默认值
        self.assertIsInstance(mets, float)
        self.assertGreater(mets, 0)

    def test_partial_match_chinese(self):
        """中文部分匹配仍有效"""
        mets = self.mets_service.get_mets_value("快速骑车")
        self.assertIsInstance(mets, float)
        self.assertGreater(mets, 0)

    def test_english_input(self):
        """英文输入处理"""
        mets = self.mets_service.get_mets_value("basketball")
        self.assertEqual(mets, 6.5)

    def test_mixed_case_input(self):
        """大小写混合输入"""
        mets = self.mets_service.get_mets_value("Basketball")
        self.assertEqual(mets, 6.5)

    def test_whitespace_input(self):
        """带空格输入"""
        mets = self.mets_service.get_mets_value("  running  ")
        self.assertEqual(mets, 8.0)

    def test_none_weight_calculation(self):
        """体重为None时使用默认"""
        calories = self.mets_service.calculate_calories("running", None, 60)
        expected = 8.0 * 70.0 * 1.0
        self.assertEqual(calories, expected)

    def test_zero_weight_calculation(self):
        """体重为0时使用默认"""
        calories = self.mets_service.calculate_calories("running", 0, 60)
        expected = 8.0 * 70.0 * 1.0
        self.assertEqual(calories, expected)

    def test_negative_target_calories(self):
        """目标热量为负数返回0"""
        duration = self.mets_service.calculate_duration_for_target("running", 70, -100)
        self.assertEqual(duration, 0)

    def test_recalculate_trip_items_calories(self):
        """批量重新计算trip items"""
        items = [
            {"placeType": "walking", "duration": 30},
            {"placeType": "running", "duration": 20},
        ]
        result = self.mets_service.recalculate_trip_items_calories(items, 70.0)
        self.assertEqual(len(result), 2)
        self.assertGreater(result[0]["cost"], 0)
        self.assertGreater(result[1]["cost"], 0)

    def test_infer_exercise_from_notes(self):
        """从notes推断运动类型"""
        self.assertEqual(
            self.mets_service._infer_exercise_from_notes("去公园慢跑30分钟"),
            "running",
        )
        self.assertIsNone(self.mets_service._infer_exercise_from_notes(""))
        self.assertIsNone(self.mets_service._infer_exercise_from_notes(None))


# ================================================================
# METsService 无 RAG 模式测试（向后兼容）
# ================================================================


class TestMETsServiceWithoutRAG(unittest.TestCase):
    """测试 METsService 在没有 RAG 服务时仍正常工作"""

    def setUp(self):
        from app.services.mets_service import METsService
        self.service = METsService()  # 不传入 exercise_rag_service

    def test_known_type_works(self):
        """已知类型正常返回"""
        self.assertEqual(self.service.get_mets_value("running"), 8.0)

    def test_unknown_type_returns_default(self):
        """未知类型返回默认值"""
        mets = self.service.get_mets_value("完全不存在的运动")
        self.assertEqual(mets, self.service.DEFAULT_METS)

    def test_chinese_mapping_works(self):
        """中文映射正常"""
        self.assertEqual(self.service.get_mets_value("篮球"), 6.5)

    def test_calculate_calories_works(self):
        """热量计算正常"""
        calories = self.service.calculate_calories("running", 70.0, 30)
        self.assertEqual(calories, 280.0)

    def test_get_exercise_info_unknown(self):
        """未知运动info返回默认结构"""
        info = self.service.get_exercise_info("不存在的运动")
        self.assertEqual(info["mets"], self.service.DEFAULT_METS)
        self.assertEqual(info["intensity"], "moderate")


# ================================================================
# ExerciseRAGService 数据转换测试
# ================================================================


class TestExerciseRAGServiceDataConversion(unittest.TestCase):
    """测试数据转换方法的正确性"""

    def setUp(self):
        from app.services.exercise_rag_service import ExerciseRAGService
        self.service = ExerciseRAGService(
            vector_service=MagicMock(),
            embedding_service=MagicMock(),
        )

    def test_exercise_to_text_basic(self):
        """基本文本转换"""
        exercise = {
            "exercise_name": "跑步",
            "aliases": ["running"],
            "category": "跑步类",
            "mets": 8.0,
            "intensity": "vigorous",
            "description": "中等速度跑步",
        }
        text = self.service._exercise_to_text(exercise)
        self.assertIn("跑步", text)
        self.assertIn("running", text)
        self.assertIn("8.0", text)

    def test_exercise_to_text_with_suitable_for(self):
        """包含适合人群的文本转换"""
        exercise = {
            "exercise_name": "瑜伽",
            "aliases": ["yoga"],
            "category": "柔韧与平衡",
            "mets": 2.5,
            "intensity": "light",
            "description": "一般瑜伽练习",
            "suitable_for": ["柔韧性", "放松减压"],
        }
        text = self.service._exercise_to_text(exercise)
        self.assertIn("瑜伽", text)
        self.assertIn("柔韧性", text)

    def test_exercise_to_text_empty_aliases(self):
        """空别名的文本转换"""
        exercise = {
            "exercise_name": "测试运动",
            "aliases": [],
            "category": "测试",
            "mets": 3.0,
            "intensity": "light",
            "description": "测试",
        }
        text = self.service._exercise_to_text(exercise)
        self.assertIn("测试运动", text)

    def test_exercise_to_metadata_all_fields(self):
        """元数据包含所有必要字段"""
        exercise = {
            "exercise_name": "跑步",
            "aliases": ["running"],
            "category": "跑步类",
            "mets": 8.0,
            "intensity": "vigorous",
            "description": "中等速度跑步",
            "suitable_for": ["减脂"],
        }
        meta = self.service._exercise_to_metadata(exercise)
        self.assertEqual(meta["exercise_name"], "跑步")
        self.assertEqual(meta["mets"], 8.0)
        self.assertEqual(meta["intensity"], "vigorous")
        self.assertEqual(meta["category"], "跑步类")
        self.assertIn("description", meta)

    def test_exercise_to_metadata_chromadb_safe(self):
        """元数据值应为 ChromaDB 安全类型"""
        exercise = {
            "exercise_name": "跑步",
            "aliases": ["running", "中速跑"],
            "category": "跑步类",
            "mets": 8.0,
            "intensity": "vigorous",
            "description": "中等速度跑步",
            "suitable_for": ["减脂", "耐力训练"],
        }
        meta = self.service._exercise_to_metadata(exercise)
        for k, v in meta.items():
            self.assertIsInstance(
                v, (str, int, float, bool),
                f"元数据字段 {k} 的值类型不安全: {type(v)}",
            )


# ================================================================
# get_mets_service 单例测试
# ================================================================


class TestGetMetsServiceSingleton(unittest.TestCase):
    """测试 get_mets_service 单例行为"""

    def test_singleton_returns_same_instance(self):
        """连续调用应返回同一实例"""
        import app.services.mets_service as mod
        # 重置单例
        mod._mets_service_instance = None
        s1 = mod.get_mets_service()
        s2 = mod.get_mets_service()
        self.assertIs(s1, s2)
        # 清理
        mod._mets_service_instance = None


# ================================================================
# get_exercise_rag_service 单例测试
# ================================================================


class TestGetExerciseRAGServiceSingleton(unittest.TestCase):
    """测试 get_exercise_rag_service 单例行为"""

    def test_singleton_returns_same_instance(self):
        """连续调用应返回同一实例"""
        import app.services.exercise_rag_service as mod
        old = mod._default_instance
        mod._default_instance = None
        s1 = mod.get_exercise_rag_service()
        s2 = mod.get_exercise_rag_service()
        self.assertIs(s1, s2)
        # 清理
        mod._default_instance = old


# ================================================================
# 入口
# ================================================================


if __name__ == "__main__":
    unittest.main(verbosity=2)
