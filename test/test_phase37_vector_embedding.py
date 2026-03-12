"""
Phase 37 测试：向量数据库（ChromaDB）+ BGE-M3 嵌入模型集成

测试内容：
1. EmbeddingService - 文本向量化、批量向量化、相似度计算
2. VectorService (ChromaDB) - 集合管理、向量CRUD、相似度检索
3. 端到端集成 - 嵌入 + 存储 + 检索完整流程
4. 边缘情况 - 空输入、重复操作、不存在的集合等

注意：测试使用临时目录存储 ChromaDB 数据，测试结束后自动清理。
"""

import os
import sys
import tempfile
import unittest
import shutil

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestEmbeddingServiceUnit(unittest.TestCase):
    """EmbeddingService 单元测试（不依赖模型加载的部分）"""

    def test_import(self):
        """测试模块可以正常导入"""
        from app.services.embedding_service import EmbeddingService, get_embedding_service, EMBEDDING_DIM
        self.assertIsNotNone(EmbeddingService)
        self.assertEqual(EMBEDDING_DIM, 1024)

    def test_init(self):
        """测试初始化不会立即加载模型"""
        from app.services.embedding_service import EmbeddingService
        svc = EmbeddingService(model_name="BAAI/bge-m3")
        self.assertFalse(svc.is_model_loaded())
        self.assertEqual(svc.dimension, 1024)

    def test_get_model_info(self):
        """测试模型元信息"""
        from app.services.embedding_service import EmbeddingService
        svc = EmbeddingService(model_name="BAAI/bge-m3", device="cpu")
        info = svc.get_model_info()
        self.assertEqual(info["model_name"], "BAAI/bge-m3")
        self.assertEqual(info["device"], "cpu")
        self.assertFalse(info["loaded"])
        self.assertEqual(info["dimension"], 1024)

    def test_embed_empty_list(self):
        """测试空列表输入"""
        from app.services.embedding_service import EmbeddingService
        svc = EmbeddingService(model_name="BAAI/bge-m3")
        result = svc.embed_texts([])
        self.assertEqual(result, [])

    def test_compute_similarity_zero_vectors(self):
        """测试零向量的相似度计算"""
        from app.services.embedding_service import EmbeddingService
        svc = EmbeddingService()
        zero_vec = [0.0] * 10
        non_zero = [1.0] * 10
        sim = svc.compute_similarity(zero_vec, non_zero)
        self.assertEqual(sim, 0.0)

    def test_compute_similarity_identical(self):
        """测试相同向量的相似度为1"""
        from app.services.embedding_service import EmbeddingService
        svc = EmbeddingService()
        vec = [1.0, 2.0, 3.0, 4.0, 5.0]
        sim = svc.compute_similarity(vec, vec)
        self.assertAlmostEqual(sim, 1.0, places=5)

    def test_compute_similarity_orthogonal(self):
        """测试正交向量的相似度为0"""
        from app.services.embedding_service import EmbeddingService
        svc = EmbeddingService()
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [0.0, 1.0, 0.0]
        sim = svc.compute_similarity(vec_a, vec_b)
        self.assertAlmostEqual(sim, 0.0, places=5)

    def test_compute_similarity_opposite(self):
        """测试反向向量的相似度为-1"""
        from app.services.embedding_service import EmbeddingService
        svc = EmbeddingService()
        vec_a = [1.0, 2.0, 3.0]
        vec_b = [-1.0, -2.0, -3.0]
        sim = svc.compute_similarity(vec_a, vec_b)
        self.assertAlmostEqual(sim, -1.0, places=5)

    def test_singleton_pattern(self):
        """测试单例模式"""
        from app.services import embedding_service as mod
        mod._default_instance = None
        svc1 = mod.get_embedding_service()
        svc2 = mod.get_embedding_service()
        self.assertIs(svc1, svc2)
        mod._default_instance = None


class TestVectorServiceUnit(unittest.TestCase):
    """VectorService 单元测试（使用临时数据库）"""

    def setUp(self):
        self._temp_dir = tempfile.mkdtemp(prefix="lifehub_test_chroma_")
        self._db_path = os.path.join(self._temp_dir, "chroma_data")

    def tearDown(self):
        try:
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        except Exception:
            pass

    def _get_service(self):
        from app.services.vector_service import VectorService
        return VectorService(db_path=self._db_path)

    def test_import(self):
        """测试模块可以正常导入"""
        from app.services.vector_service import VectorService, get_vector_service, DEFAULT_DIMENSION
        self.assertIsNotNone(VectorService)
        self.assertEqual(DEFAULT_DIMENSION, 1024)

    def test_init(self):
        """测试初始化不会立即连接"""
        from app.services.vector_service import VectorService
        svc = VectorService(db_path=self._db_path)
        self.assertIsNone(svc._client)

    def test_create_collection(self):
        """测试创建集合"""
        svc = self._get_service()
        result = svc.create_collection("test_collection", dimension=128)
        self.assertTrue(result)
        self.assertTrue(svc.has_collection("test_collection"))
        svc.close()

    def test_create_collection_idempotent(self):
        """测试重复创建集合（幂等性）"""
        svc = self._get_service()
        svc.create_collection("test_collection", dimension=128)
        result = svc.create_collection("test_collection", dimension=128)
        self.assertTrue(result)
        svc.close()

    def test_drop_collection(self):
        """测试删除集合"""
        svc = self._get_service()
        svc.create_collection("to_drop", dimension=128)
        self.assertTrue(svc.has_collection("to_drop"))
        svc.drop_collection("to_drop")
        self.assertFalse(svc.has_collection("to_drop"))
        svc.close()

    def test_drop_nonexistent_collection(self):
        """测试删除不存在的集合"""
        svc = self._get_service()
        result = svc.drop_collection("nonexistent_collection_xyz")
        self.assertTrue(result)
        svc.close()

    def test_list_collections_empty(self):
        """测试空数据库的集合列表"""
        svc = self._get_service()
        collections = svc.list_collections()
        self.assertIsInstance(collections, list)
        svc.close()

    def test_list_collections_after_create(self):
        """测试创建集合后的列表"""
        svc = self._get_service()
        svc.create_collection("col_a", dimension=128)
        svc.create_collection("col_b", dimension=128)
        collections = svc.list_collections()
        self.assertIn("col_a", collections)
        self.assertIn("col_b", collections)
        svc.close()

    def test_insert_and_search(self):
        """测试向量插入与检索"""
        svc = self._get_service()
        dim = 128
        svc.create_collection("search_test", dimension=dim)

        vec1 = [1.0] * dim
        vec2 = [0.5] * dim
        vec3 = [-1.0] * dim

        ids = svc.insert(
            collection_name="search_test",
            vectors=[vec1, vec2, vec3],
            texts=["positive_full", "positive_half", "negative_full"],
            metadatas=[
                {"category": "pos"},
                {"category": "pos"},
                {"category": "neg"},
            ],
        )
        self.assertEqual(len(ids), 3)

        query = [1.0] * dim
        results = svc.search("search_test", query_vector=query, top_k=3)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].get("text"), "positive_full")
        svc.close()

    def test_insert_single(self):
        """测试单条插入"""
        svc = self._get_service()
        dim = 64
        svc.create_collection("single_test", dimension=dim)

        vec = [0.5] * dim
        record_id = svc.insert_single(
            collection_name="single_test",
            vector=vec,
            text="test_text",
            metadata={"source": "test"},
        )
        self.assertIsNotNone(record_id)

        results = svc.search("single_test", query_vector=vec, top_k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].get("text"), "test_text")
        svc.close()

    def test_insert_mismatch_raises(self):
        """测试向量和文本数量不匹配时抛异常"""
        svc = self._get_service()
        dim = 64
        svc.create_collection("mismatch_test", dimension=dim)
        with self.assertRaises(ValueError):
            svc.insert(
                collection_name="mismatch_test",
                vectors=[[0.1] * dim, [0.2] * dim],
                texts=["only one"],
            )
        svc.close()

    def test_insert_metadata_mismatch_raises(self):
        """测试元数据数量不匹配时抛异常"""
        svc = self._get_service()
        dim = 64
        svc.create_collection("meta_mismatch", dimension=dim)
        with self.assertRaises(ValueError):
            svc.insert(
                collection_name="meta_mismatch",
                vectors=[[0.1] * dim],
                texts=["text1"],
                metadatas=[{"a": 1}, {"b": 2}],
            )
        svc.close()

    def test_delete_by_ids(self):
        """测试按ID删除"""
        svc = self._get_service()
        dim = 64
        svc.create_collection("delete_test", dimension=dim)

        ids = svc.insert(
            collection_name="delete_test",
            vectors=[[0.1] * dim, [0.9] * dim],
            texts=["text_a", "text_b"],
        )
        self.assertEqual(len(ids), 2)

        svc.delete_by_ids("delete_test", [ids[0]])

        results = svc.search("delete_test", query_vector=[0.9] * dim, top_k=10)
        texts = [r.get("text") for r in results]
        self.assertNotIn("text_a", texts)
        svc.close()

    def test_get_collection_stats(self):
        """测试获取集合统计信息"""
        svc = self._get_service()
        dim = 64
        svc.create_collection("stats_test", dimension=dim)

        svc.insert(
            collection_name="stats_test",
            vectors=[[0.1] * dim, [0.2] * dim, [0.3] * dim],
            texts=["a", "b", "c"],
        )

        stats = svc.get_collection_stats("stats_test")
        self.assertTrue(stats["exists"])
        self.assertEqual(stats["row_count"], 3)
        svc.close()

    def test_get_stats_nonexistent(self):
        """测试获取不存在集合的统计"""
        svc = self._get_service()
        stats = svc.get_collection_stats("no_such_collection")
        self.assertFalse(stats["exists"])
        self.assertEqual(stats["row_count"], 0)
        svc.close()

    def test_get_service_info(self):
        """测试服务元信息"""
        svc = self._get_service()
        info = svc.get_service_info()
        self.assertEqual(info["db_path"], self._db_path)
        self.assertFalse(info["connected"])

        svc.list_collections()
        info = svc.get_service_info()
        self.assertTrue(info["connected"])
        svc.close()

    def test_close_and_reconnect(self):
        """测试关闭后可以重新连接"""
        svc = self._get_service()
        svc.create_collection("reconnect_test", dimension=64)
        svc.close()
        self.assertIsNone(svc._client)

        has = svc.has_collection("reconnect_test")
        self.assertTrue(has)
        svc.close()

    def test_singleton_pattern(self):
        """测试单例模式"""
        from app.services import vector_service as mod
        mod._default_instance = None
        svc1 = mod.get_vector_service(db_path=self._db_path)
        svc2 = mod.get_vector_service()
        self.assertIs(svc1, svc2)
        svc1.close()
        mod._default_instance = None

    def test_search_top_k_ordering(self):
        """测试检索结果按相似度排序（使用不同方向的向量）"""
        svc = self._get_service()
        dim = 64
        svc.create_collection("ordering_test", dimension=dim)

        import math
        # 构造方向不同的向量：target 方向、接近方向、远离方向
        target = [1.0 if j < dim // 2 else 0.0 for j in range(dim)]
        close_vec = [0.9 if j < dim // 2 else 0.1 for j in range(dim)]
        mid_vec = [0.5] * dim
        far_vec = [0.0 if j < dim // 2 else 1.0 for j in range(dim)]

        svc.insert(
            "ordering_test",
            vectors=[far_vec, mid_vec, close_vec],
            texts=["far", "mid", "close"],
        )

        results = svc.search("ordering_test", query_vector=target, top_k=3)
        self.assertEqual(len(results), 3)
        # 最接近 target 方向的应该排第一
        self.assertEqual(results[0].get("text"), "close")
        svc.close()

    def test_search_with_output_fields(self):
        """测试检索时指定输出字段"""
        svc = self._get_service()
        dim = 64
        svc.create_collection("fields_test", dimension=dim)

        svc.insert(
            "fields_test",
            vectors=[[0.5] * dim],
            texts=["hello"],
            metadatas=[{"source": "test", "score": 99}],
        )

        results = svc.search(
            "fields_test",
            query_vector=[0.5] * dim,
            top_k=1,
            output_fields=["text", "metadata"],
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].get("text"), "hello")
        meta = results[0].get("metadata", {})
        self.assertEqual(meta.get("source"), "test")
        self.assertEqual(meta.get("score"), 99)
        svc.close()

    def test_large_batch_insert(self):
        """测试较大批量插入（100条）"""
        svc = self._get_service()
        dim = 64
        svc.create_collection("batch_test", dimension=dim)

        import random
        random.seed(123)
        n = 100
        vecs = [[random.random() for _ in range(dim)] for _ in range(n)]
        texts = [f"doc_{i}" for i in range(n)]

        ids = svc.insert("batch_test", vectors=vecs, texts=texts)
        self.assertEqual(len(ids), n)

        stats = svc.get_collection_stats("batch_test")
        self.assertEqual(stats["row_count"], n)
        svc.close()


class TestEmbeddingModelIntegration(unittest.TestCase):
    """
    嵌入模型集成测试（需要下载模型，可能较慢）
    """

    @classmethod
    def setUpClass(cls):
        from app.services.embedding_service import EmbeddingService
        cls.svc = EmbeddingService(model_name="BAAI/bge-m3", device="cpu")
        try:
            cls.svc._load_model()
            cls.model_available = True
        except Exception as e:
            print(f"\nBGE-M3 model not available, skipping integration tests: {e}")
            cls.model_available = False

    def setUp(self):
        if not self.model_available:
            self.skipTest("BGE-M3 model not available")

    def test_embed_single_text(self):
        """测试单条文本向量化"""
        vec = self.svc.embed_text("番茄炒蛋的营养成分")
        self.assertIsInstance(vec, list)
        self.assertEqual(len(vec), self.svc.dimension)
        self.assertGreater(sum(abs(v) for v in vec), 0)

    def test_embed_batch(self):
        """测试批量文本向量化"""
        texts = ["番茄炒蛋", "宫保鸡丁", "红烧肉", "清蒸鱼"]
        vecs = self.svc.embed_texts(texts)
        self.assertEqual(len(vecs), 4)
        for vec in vecs:
            self.assertEqual(len(vec), self.svc.dimension)

    def test_embed_query_vs_document(self):
        """测试查询模式与文档模式的区别"""
        text = "番茄炒蛋"
        vec_doc = self.svc.embed_text(text, is_query=False)
        vec_query = self.svc.embed_text(text, is_query=True)
        self.assertNotEqual(vec_doc, vec_query)

    def test_semantic_similarity(self):
        """测试语义相似度：相关文本的相似度应高于无关文本"""
        vec_tomato = self.svc.embed_text("番茄炒蛋的营养价值")
        vec_egg = self.svc.embed_text("鸡蛋的蛋白质含量")
        vec_car = self.svc.embed_text("汽车发动机的工作原理")

        sim_related = self.svc.compute_similarity(vec_tomato, vec_egg)
        sim_unrelated = self.svc.compute_similarity(vec_tomato, vec_car)
        self.assertGreater(sim_related, sim_unrelated)

    def test_chinese_text_quality(self):
        """测试中文文本嵌入质量"""
        texts = [
            "低脂高蛋白的健康饮食",
            "减脂增肌的营养搭配",
            "深度学习模型训练技巧",
        ]
        vecs = self.svc.embed_texts(texts)
        sim_01 = self.svc.compute_similarity(vecs[0], vecs[1])
        sim_02 = self.svc.compute_similarity(vecs[0], vecs[2])
        self.assertGreater(sim_01, sim_02)

    def test_normalized_vectors(self):
        """测试归一化向量的 L2 范数接近 1"""
        import math
        vec = self.svc.embed_text("测试文本", normalize=True)
        norm = math.sqrt(sum(v * v for v in vec))
        self.assertAlmostEqual(norm, 1.0, places=3)


class TestEndToEndIntegration(unittest.TestCase):
    """
    端到端集成测试：嵌入 + ChromaDB 存储 + 检索
    """

    @classmethod
    def setUpClass(cls):
        from app.services.embedding_service import EmbeddingService
        cls.embed_svc = EmbeddingService(model_name="BAAI/bge-m3", device="cpu")
        try:
            cls.embed_svc._load_model()
            cls.model_available = True
        except Exception:
            cls.model_available = False

    def setUp(self):
        if not self.model_available:
            self.skipTest("BGE-M3 model not available")
        self._temp_dir = tempfile.mkdtemp(prefix="lifehub_e2e_")
        self._db_path = os.path.join(self._temp_dir, "e2e_chroma")

    def tearDown(self):
        try:
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        except Exception:
            pass

    def test_nutrition_knowledge_retrieval(self):
        """端到端测试：营养知识检索"""
        from app.services.vector_service import VectorService

        vec_svc = VectorService(db_path=self._db_path)
        collection = "nutrition_knowledge"
        dim = self.embed_svc.dimension

        vec_svc.create_collection(collection, dimension=dim)

        knowledge_texts = [
            "番茄炒蛋：每100g含热量约120kcal，蛋白质8g，脂肪7g，碳水6g。番茄富含番茄红素和维生素C。",
            "宫保鸡丁：每100g含热量约180kcal，蛋白质15g，脂肪10g，碳水8g。含花生，属花生过敏原。",
            "红烧肉：每100g含热量约350kcal，蛋白质12g，脂肪30g，碳水5g。高脂肪食物，减脂期慎食。",
            "清蒸鱼：每100g含热量约90kcal，蛋白质18g，脂肪2g，碳水0g。高蛋白低脂肪，健身首选。",
            "糖醋里脊：每100g含热量约250kcal，蛋白质14g，脂肪12g，碳水20g。含较多糖分。",
            "麻辣豆腐：每100g含热量约130kcal，蛋白质10g，脂肪8g，碳水5g。含大豆制品。",
        ]
        knowledge_metas = [
            {"food": "番茄炒蛋", "category": "家常菜"},
            {"food": "宫保鸡丁", "category": "川菜"},
            {"food": "红烧肉", "category": "家常菜"},
            {"food": "清蒸鱼", "category": "粤菜"},
            {"food": "糖醋里脊", "category": "鲁菜"},
            {"food": "麻辣豆腐", "category": "川菜"},
        ]

        vecs = self.embed_svc.embed_texts(knowledge_texts, is_query=False)
        ids = vec_svc.insert(collection, vectors=vecs, texts=knowledge_texts, metadatas=knowledge_metas)
        self.assertEqual(len(ids), 6)

        # 检索：高蛋白低脂肪 -> 清蒸鱼应排前
        query1 = "高蛋白低脂肪的菜"
        q_vec1 = self.embed_svc.embed_text(query1, is_query=True)
        results1 = vec_svc.search(collection, query_vector=q_vec1, top_k=2)
        self.assertGreater(len(results1), 0)
        self.assertIn("清蒸鱼", results1[0].get("text", ""))

        # 检索：含花生过敏原 -> 宫保鸡丁应排前
        query2 = "含花生过敏原的菜品"
        q_vec2 = self.embed_svc.embed_text(query2, is_query=True)
        results2 = vec_svc.search(collection, query_vector=q_vec2, top_k=2)
        self.assertGreater(len(results2), 0)
        self.assertIn("宫保鸡丁", results2[0].get("text", ""))

        vec_svc.close()

    def test_insert_search_delete_lifecycle(self):
        """端到端测试：插入-检索-删除完整生命周期"""
        from app.services.vector_service import VectorService

        vec_svc = VectorService(db_path=self._db_path)
        collection = "lifecycle_test"
        dim = self.embed_svc.dimension

        vec_svc.create_collection(collection, dimension=dim)

        texts = ["苹果富含维生素C", "香蕉含钾丰富"]
        vecs = self.embed_svc.embed_texts(texts)
        ids = vec_svc.insert(collection, vectors=vecs, texts=texts)
        self.assertEqual(len(ids), 2)

        # 检索
        q_vec = self.embed_svc.embed_text("维生素C水果", is_query=True)
        results = vec_svc.search(collection, query_vector=q_vec, top_k=2)
        self.assertEqual(len(results), 2)

        # 删除第一条
        vec_svc.delete_by_ids(collection, [ids[0]])

        # 再次检索，只剩一条
        results2 = vec_svc.search(collection, query_vector=q_vec, top_k=10)
        self.assertEqual(len(results2), 1)
        self.assertIn("香蕉", results2[0].get("text", ""))

        # 删除集合
        vec_svc.drop_collection(collection)
        self.assertFalse(vec_svc.has_collection(collection))

        vec_svc.close()

    def test_multiple_collections(self):
        """端到端测试：多集合独立性"""
        from app.services.vector_service import VectorService

        vec_svc = VectorService(db_path=self._db_path)
        dim = self.embed_svc.dimension

        vec_svc.create_collection("food_col", dimension=dim)
        vec_svc.create_collection("exercise_col", dimension=dim)

        food_texts = ["番茄炒蛋营养丰富"]
        exercise_texts = ["跑步30分钟消耗300卡"]

        food_vecs = self.embed_svc.embed_texts(food_texts)
        exercise_vecs = self.embed_svc.embed_texts(exercise_texts)

        vec_svc.insert("food_col", vectors=food_vecs, texts=food_texts)
        vec_svc.insert("exercise_col", vectors=exercise_vecs, texts=exercise_texts)

        # 检索食物集合
        q = self.embed_svc.embed_text("番茄", is_query=True)
        food_results = vec_svc.search("food_col", query_vector=q, top_k=1)
        exercise_results = vec_svc.search("exercise_col", query_vector=q, top_k=1)

        self.assertIn("番茄", food_results[0].get("text", ""))
        self.assertIn("跑步", exercise_results[0].get("text", ""))

        vec_svc.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
