"""
Phase 57: Few-shot Prompt模板管理 - 综合测试

测试内容：
1. 模板加载与初始化
2. 模板注册与获取
3. Few-shot示例管理（增删查）
4. 动态变量替换
5. 模板渲染（system + few-shot + user prompt 拼接）
6. 模板版本管理
7. 模板持久化（JSON文件读写）
8. 与ai_service集成（prompt构建对比）
9. 边界条件与异常处理
10. 并发安全性
"""

import os
import sys
import json
import copy
import tempfile
import shutil
import threading
import pytest

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ────────────────────────────────────────────────────────────
# 1. 模板服务导入与基本初始化
# ────────────────────────────────────────────────────────────
class TestPromptTemplateServiceImport:
    """测试模板服务能正确导入和初始化"""

    def test_import_service(self):
        """测试模块可以正常导入"""
        from app.services.prompt_template_service import PromptTemplateService
        assert PromptTemplateService is not None

    def test_import_singleton(self):
        """测试单例获取函数可以导入"""
        from app.services.prompt_template_service import get_prompt_template_service
        assert callable(get_prompt_template_service)

    def test_singleton_returns_same_instance(self):
        """测试单例每次返回同一个实例"""
        from app.services.prompt_template_service import get_prompt_template_service
        s1 = get_prompt_template_service()
        s2 = get_prompt_template_service()
        assert s1 is s2

    def test_init_with_custom_dir(self, tmp_path):
        """测试可用自定义目录初始化"""
        from app.services.prompt_template_service import PromptTemplateService
        svc = PromptTemplateService(templates_dir=str(tmp_path))
        assert svc is not None


# ────────────────────────────────────────────────────────────
# 2. 内置模板加载
# ────────────────────────────────────────────────────────────
class TestBuiltinTemplates:
    """测试内置默认模板正确加载"""

    @pytest.fixture
    def svc(self, tmp_path):
        from app.services.prompt_template_service import PromptTemplateService
        return PromptTemplateService(templates_dir=str(tmp_path))

    def test_builtin_template_types(self, svc):
        """测试所有内置模板类型都存在"""
        expected_types = [
            "food_analysis",
            "exercise_intent",
            "trip_generation",
            "menu_recognition",
            "before_meal_features",
            "meal_comparison",
        ]
        available = svc.list_templates()
        for t in expected_types:
            assert t in available, f"缺少内置模板: {t}"

    def test_builtin_template_has_system_prompt(self, svc):
        """每个内置模板都应有system_prompt"""
        for name in svc.list_templates():
            tpl = svc.get_template(name)
            assert tpl is not None, f"获取模板失败: {name}"
            assert "system_prompt" in tpl, f"模板缺少system_prompt: {name}"
            assert len(tpl["system_prompt"]) > 0, f"system_prompt为空: {name}"

    def test_builtin_template_has_few_shot_examples(self, svc):
        """每个内置模板都应至少有1个few-shot示例"""
        for name in svc.list_templates():
            tpl = svc.get_template(name)
            assert "few_shot_examples" in tpl, f"模板缺少few_shot_examples: {name}"
            assert isinstance(tpl["few_shot_examples"], list), f"few_shot_examples应为列表: {name}"
            assert len(tpl["few_shot_examples"]) >= 1, f"模板至少需要1个few-shot示例: {name}"

    def test_builtin_template_has_user_prompt_template(self, svc):
        """每个内置模板都应有user_prompt_template"""
        for name in svc.list_templates():
            tpl = svc.get_template(name)
            assert "user_prompt_template" in tpl, f"模板缺少user_prompt_template: {name}"
            assert len(tpl["user_prompt_template"]) > 0, f"user_prompt_template为空: {name}"

    def test_few_shot_example_structure(self, svc):
        """few-shot示例应包含input和output字段"""
        for name in svc.list_templates():
            tpl = svc.get_template(name)
            for i, example in enumerate(tpl["few_shot_examples"]):
                assert "input" in example, f"模板{name}的第{i}个示例缺少input"
                assert "output" in example, f"模板{name}的第{i}个示例缺少output"


# ────────────────────────────────────────────────────────────
# 3. 模板注册与管理
# ────────────────────────────────────────────────────────────
class TestTemplateManagement:
    """测试模板注册、更新、删除"""

    @pytest.fixture
    def svc(self, tmp_path):
        from app.services.prompt_template_service import PromptTemplateService
        return PromptTemplateService(templates_dir=str(tmp_path))

    def test_register_new_template(self, svc):
        """测试注册新模板"""
        tpl = {
            "system_prompt": "你是一个测试助手。",
            "few_shot_examples": [
                {"input": "测试输入", "output": "测试输出"}
            ],
            "user_prompt_template": "请处理: {query}",
            "version": "1.0",
        }
        svc.register_template("test_template", tpl)
        result = svc.get_template("test_template")
        assert result is not None
        assert result["system_prompt"] == "你是一个测试助手。"

    def test_update_template(self, svc):
        """测试更新已有模板"""
        tpl_v1 = {
            "system_prompt": "版本1",
            "few_shot_examples": [{"input": "a", "output": "b"}],
            "user_prompt_template": "{query}",
            "version": "1.0",
        }
        tpl_v2 = {
            "system_prompt": "版本2",
            "few_shot_examples": [{"input": "c", "output": "d"}],
            "user_prompt_template": "{query}",
            "version": "2.0",
        }
        svc.register_template("my_tpl", tpl_v1)
        svc.register_template("my_tpl", tpl_v2)
        result = svc.get_template("my_tpl")
        assert result["system_prompt"] == "版本2"
        assert result["version"] == "2.0"

    def test_get_nonexistent_template_returns_none(self, svc):
        """获取不存在的模板应返回None"""
        assert svc.get_template("nonexistent_xyz") is None

    def test_list_templates(self, svc):
        """list_templates返回所有已注册模板名称"""
        names = svc.list_templates()
        assert isinstance(names, list)
        # 至少包含内置模板
        assert len(names) >= 6

    def test_add_few_shot_example(self, svc):
        """测试向模板添加few-shot示例"""
        tpl_name = "food_analysis"
        original = svc.get_template(tpl_name)
        original_count = len(original["few_shot_examples"])

        new_example = {"input": "红烧排骨", "output": '{"calories": 250.0}'}
        svc.add_few_shot_example(tpl_name, new_example)

        updated = svc.get_template(tpl_name)
        assert len(updated["few_shot_examples"]) == original_count + 1
        assert updated["few_shot_examples"][-1]["input"] == "红烧排骨"

    def test_remove_few_shot_example(self, svc):
        """测试删除指定索引的few-shot示例"""
        tpl_name = "food_analysis"
        original = svc.get_template(tpl_name)
        original_count = len(original["few_shot_examples"])

        svc.remove_few_shot_example(tpl_name, 0)
        updated = svc.get_template(tpl_name)
        assert len(updated["few_shot_examples"]) == original_count - 1

    def test_remove_few_shot_out_of_range(self, svc):
        """删除超出范围的索引应引发异常或安全忽略"""
        with pytest.raises((IndexError, ValueError)):
            svc.remove_few_shot_example("food_analysis", 999)

    def test_add_few_shot_to_nonexistent_template(self, svc):
        """向不存在的模板添加示例应引发异常"""
        with pytest.raises((KeyError, ValueError)):
            svc.add_few_shot_example("no_such_template", {"input": "x", "output": "y"})


# ────────────────────────────────────────────────────────────
# 4. 动态变量替换
# ────────────────────────────────────────────────────────────
class TestVariableSubstitution:
    """测试模板中的动态变量替换"""

    @pytest.fixture
    def svc(self, tmp_path):
        from app.services.prompt_template_service import PromptTemplateService
        return PromptTemplateService(templates_dir=str(tmp_path))

    def test_simple_variable_substitution(self, svc):
        """简单变量替换"""
        tpl = {
            "system_prompt": "分析{food_name}的营养。",
            "few_shot_examples": [],
            "user_prompt_template": "请分析菜品{food_name}。",
            "version": "1.0",
        }
        svc.register_template("test_sub", tpl)
        rendered = svc.render_prompt("test_sub", variables={"food_name": "番茄炒蛋"})
        assert "番茄炒蛋" in rendered["user_prompt"]

    def test_multiple_variables(self, svc):
        """多个变量替换"""
        tpl = {
            "system_prompt": "城市: {city}, 目标: {goal}。",
            "few_shot_examples": [],
            "user_prompt_template": "在{city}做{goal}运动。",
            "version": "1.0",
        }
        svc.register_template("multi_var", tpl)
        rendered = svc.render_prompt("multi_var", variables={"city": "北京", "goal": "减脂"})
        assert "北京" in rendered["user_prompt"]
        assert "减脂" in rendered["user_prompt"]

    def test_missing_variable_left_as_placeholder(self, svc):
        """缺少的变量应保留占位符或用空字符串替代，不崩溃"""
        tpl = {
            "system_prompt": "系统提示",
            "few_shot_examples": [],
            "user_prompt_template": "查询: {query}, 上下文: {context}",
            "version": "1.0",
        }
        svc.register_template("partial_var", tpl)
        # 只传query，不传context
        rendered = svc.render_prompt("partial_var", variables={"query": "测试"})
        assert "测试" in rendered["user_prompt"]
        # 不应崩溃

    def test_empty_variables(self, svc):
        """传空变量字典不崩溃"""
        rendered = svc.render_prompt("food_analysis", variables={})
        assert rendered is not None
        assert "user_prompt" in rendered

    def test_extra_variables_ignored(self, svc):
        """传入多余变量应被安全忽略"""
        rendered = svc.render_prompt("food_analysis", variables={
            "food_name": "番茄炒蛋",
            "nonexistent_var": "应被忽略",
        })
        assert rendered is not None


# ────────────────────────────────────────────────────────────
# 5. 模板渲染（完整prompt构建）
# ────────────────────────────────────────────────────────────
class TestTemplateRendering:
    """测试完整的prompt渲染流程"""

    @pytest.fixture
    def svc(self, tmp_path):
        from app.services.prompt_template_service import PromptTemplateService
        return PromptTemplateService(templates_dir=str(tmp_path))

    def test_render_returns_required_keys(self, svc):
        """render_prompt返回值包含必需字段"""
        rendered = svc.render_prompt("food_analysis", variables={"food_name": "宫保鸡丁"})
        assert "system_prompt" in rendered
        assert "user_prompt" in rendered
        assert "few_shot_messages" in rendered

    def test_render_few_shot_messages_format(self, svc):
        """few_shot_messages应为user/assistant消息对列表"""
        rendered = svc.render_prompt("food_analysis", variables={"food_name": "宫保鸡丁"})
        messages = rendered["few_shot_messages"]
        assert isinstance(messages, list)
        # 每个few-shot示例应生成2条消息(user + assistant)
        for i in range(0, len(messages), 2):
            assert messages[i]["role"] == "user"
            if i + 1 < len(messages):
                assert messages[i + 1]["role"] == "assistant"

    def test_render_food_analysis_prompt(self, svc):
        """渲染food_analysis模板应包含菜品名称"""
        rendered = svc.render_prompt("food_analysis", variables={
            "food_name": "麻婆豆腐",
        })
        assert "麻婆豆腐" in rendered["user_prompt"]

    def test_render_food_analysis_with_rag_context(self, svc):
        """渲染food_analysis模板时可注入RAG上下文"""
        rag_ctx = "参考数据：麻婆豆腐 每100g 热量130千卡"
        rendered = svc.render_prompt("food_analysis", variables={
            "food_name": "麻婆豆腐",
            "rag_context": rag_ctx,
        })
        assert "麻婆豆腐" in rendered["user_prompt"]
        # RAG上下文应出现在prompt中
        assert "参考数据" in rendered["user_prompt"] or "参考数据" in rendered["system_prompt"]

    def test_render_exercise_intent_prompt(self, svc):
        """渲染exercise_intent模板"""
        rendered = svc.render_prompt("exercise_intent", variables={
            "query": "餐后散步30分钟",
            "today_date": "2026-03-01",
        })
        assert "餐后散步30分钟" in rendered["user_prompt"]

    def test_render_trip_generation_prompt(self, svc):
        """渲染trip_generation模板"""
        rendered = svc.render_prompt("trip_generation", variables={
            "destination": "北京中央公园",
            "start_date": "2026-03-01",
            "end_date": "2026-03-01",
            "days": "1",
            "calories_target": "300",
        })
        assert "北京中央公园" in rendered["user_prompt"]

    def test_render_menu_recognition_prompt(self, svc):
        """渲染menu_recognition模板"""
        rendered = svc.render_prompt("menu_recognition", variables={})
        assert rendered is not None
        assert len(rendered["user_prompt"]) > 0

    def test_render_nonexistent_template_raises(self, svc):
        """渲染不存在的模板应引发异常"""
        with pytest.raises((KeyError, ValueError)):
            svc.render_prompt("nonexistent_template_xyz", variables={})

    def test_render_with_max_examples(self, svc):
        """可通过max_examples限制使用的few-shot示例数量"""
        rendered_all = svc.render_prompt("food_analysis", variables={"food_name": "鱼"})
        rendered_1 = svc.render_prompt("food_analysis", variables={"food_name": "鱼"}, max_examples=1)
        # 限制为1时，few_shot_messages应只有2条（1对user/assistant）
        assert len(rendered_1["few_shot_messages"]) <= 2
        # 不限制时应更多
        assert len(rendered_all["few_shot_messages"]) >= len(rendered_1["few_shot_messages"])

    def test_render_with_zero_examples(self, svc):
        """max_examples=0时不包含few-shot示例"""
        rendered = svc.render_prompt("food_analysis", variables={"food_name": "鱼"}, max_examples=0)
        assert len(rendered["few_shot_messages"]) == 0

    def test_build_messages_list(self, svc):
        """build_messages方法应返回完整的消息列表（system+few-shot+user）"""
        messages = svc.build_messages("food_analysis", variables={"food_name": "鱼香肉丝"})
        assert isinstance(messages, list)
        assert len(messages) >= 2  # 至少system + user
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert "鱼香肉丝" in messages[-1]["content"]


# ────────────────────────────────────────────────────────────
# 6. 模板版本管理
# ────────────────────────────────────────────────────────────
class TestTemplateVersioning:
    """测试模板版本管理"""

    @pytest.fixture
    def svc(self, tmp_path):
        from app.services.prompt_template_service import PromptTemplateService
        return PromptTemplateService(templates_dir=str(tmp_path))

    def test_template_has_version(self, svc):
        """每个内置模板应有version字段"""
        for name in svc.list_templates():
            tpl = svc.get_template(name)
            assert "version" in tpl, f"模板{name}缺少version字段"

    def test_get_template_version(self, svc):
        """获取特定模板的版本号"""
        tpl = svc.get_template("food_analysis")
        assert isinstance(tpl["version"], str)
        assert len(tpl["version"]) > 0


# ────────────────────────────────────────────────────────────
# 7. 模板持久化（JSON文件读写）
# ────────────────────────────────────────────────────────────
class TestTemplatePersistence:
    """测试模板的文件持久化"""

    def test_save_and_load_template(self, tmp_path):
        """保存模板到JSON文件后应能重新加载"""
        from app.services.prompt_template_service import PromptTemplateService

        svc1 = PromptTemplateService(templates_dir=str(tmp_path))
        custom_tpl = {
            "system_prompt": "自定义系统提示",
            "few_shot_examples": [
                {"input": "自定义输入", "output": "自定义输出"}
            ],
            "user_prompt_template": "处理: {query}",
            "version": "1.0",
        }
        svc1.register_template("custom_test", custom_tpl)
        svc1.save_template("custom_test")

        # 创建新实例，从文件加载
        svc2 = PromptTemplateService(templates_dir=str(tmp_path))
        svc2.load_templates_from_dir()
        loaded = svc2.get_template("custom_test")
        assert loaded is not None
        assert loaded["system_prompt"] == "自定义系统提示"

    def test_save_all_templates(self, tmp_path):
        """save_all_templates保存所有模板"""
        from app.services.prompt_template_service import PromptTemplateService

        svc = PromptTemplateService(templates_dir=str(tmp_path))
        svc.save_all_templates()

        # 检查文件生成
        json_files = [f for f in os.listdir(str(tmp_path)) if f.endswith(".json")]
        assert len(json_files) >= 6

    def test_load_from_json_file(self, tmp_path):
        """从JSON文件正确加载模板"""
        from app.services.prompt_template_service import PromptTemplateService

        # 手动写入一个JSON模板文件
        tpl_data = {
            "system_prompt": "手动写入的模板",
            "few_shot_examples": [{"input": "q", "output": "a"}],
            "user_prompt_template": "{query}",
            "version": "0.1",
        }
        json_path = os.path.join(str(tmp_path), "manual_test.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(tpl_data, f, ensure_ascii=False)

        svc = PromptTemplateService(templates_dir=str(tmp_path))
        svc.load_templates_from_dir()
        loaded = svc.get_template("manual_test")
        assert loaded is not None
        assert loaded["system_prompt"] == "手动写入的模板"

    def test_corrupted_json_file_ignored(self, tmp_path):
        """损坏的JSON文件应被安全跳过，不崩溃"""
        from app.services.prompt_template_service import PromptTemplateService

        bad_path = os.path.join(str(tmp_path), "bad_template.json")
        with open(bad_path, "w", encoding="utf-8") as f:
            f.write("这不是合法的JSON{{{")

        svc = PromptTemplateService(templates_dir=str(tmp_path))
        svc.load_templates_from_dir()  # 不应崩溃
        assert svc.get_template("bad_template") is None


# ────────────────────────────────────────────────────────────
# 8. 与ai_service集成
# ────────────────────────────────────────────────────────────
class TestAIServiceIntegration:
    """测试模板服务与ai_service的集成"""

    @pytest.fixture
    def svc(self, tmp_path):
        from app.services.prompt_template_service import PromptTemplateService
        return PromptTemplateService(templates_dir=str(tmp_path))

    def test_food_analysis_prompt_contains_json_format(self, svc):
        """food_analysis渲染的prompt应包含JSON格式要求"""
        rendered = svc.render_prompt("food_analysis", variables={"food_name": "番茄炒蛋"})
        full_prompt = rendered["system_prompt"] + rendered["user_prompt"]
        assert "JSON" in full_prompt or "json" in full_prompt

    def test_food_analysis_prompt_mentions_allergens(self, svc):
        """food_analysis模板应提及过敏原分析"""
        rendered = svc.render_prompt("food_analysis", variables={"food_name": "宫保鸡丁"})
        full_prompt = rendered["system_prompt"] + rendered["user_prompt"]
        assert "过敏原" in full_prompt or "allergen" in full_prompt.lower()

    def test_food_analysis_prompt_mentions_cooking_methods(self, svc):
        """food_analysis模板应提及烹饪方式对比"""
        rendered = svc.render_prompt("food_analysis", variables={"food_name": "红烧肉"})
        full_prompt = rendered["system_prompt"] + rendered["user_prompt"]
        assert "烹饪" in full_prompt or "cooking" in full_prompt.lower()

    def test_exercise_intent_prompt_mentions_date(self, svc):
        """exercise_intent模板应包含日期要求"""
        rendered = svc.render_prompt("exercise_intent", variables={
            "query": "规划餐后运动",
            "today_date": "2026-03-01",
        })
        full_prompt = rendered["system_prompt"] + rendered["user_prompt"]
        assert "2026-03-01" in full_prompt or "日期" in full_prompt

    def test_trip_generation_prompt_mentions_items(self, svc):
        """trip_generation模板应包含运动节点items格式要求"""
        rendered = svc.render_prompt("trip_generation", variables={
            "destination": "公园",
            "start_date": "2026-03-01",
            "end_date": "2026-03-01",
            "days": "1",
            "calories_target": "300",
        })
        full_prompt = rendered["system_prompt"] + rendered["user_prompt"]
        assert "items" in full_prompt or "节点" in full_prompt

    def test_food_analysis_few_shot_includes_complete_example(self, svc):
        """food_analysis的few-shot示例应包含完整的营养数据JSON"""
        tpl = svc.get_template("food_analysis")
        for example in tpl["few_shot_examples"]:
            output = example["output"]
            # output应该是可解析的JSON或包含JSON的文本
            if isinstance(output, str):
                json_start = output.find("{")
                json_end = output.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    data = json.loads(output[json_start:json_end])
                    assert "calories" in data
                    assert "protein" in data


# ────────────────────────────────────────────────────────────
# 9. 边界条件与异常处理
# ────────────────────────────────────────────────────────────
class TestEdgeCases:
    """边界条件和异常处理测试"""

    @pytest.fixture
    def svc(self, tmp_path):
        from app.services.prompt_template_service import PromptTemplateService
        return PromptTemplateService(templates_dir=str(tmp_path))

    def test_register_template_with_missing_fields(self, svc):
        """注册缺少必需字段的模板应引发异常"""
        with pytest.raises((KeyError, ValueError)):
            svc.register_template("bad_tpl", {"system_prompt": "只有system_prompt"})

    def test_register_template_empty_name(self, svc):
        """注册空名称的模板应引发异常"""
        tpl = {
            "system_prompt": "ok",
            "few_shot_examples": [],
            "user_prompt_template": "{q}",
            "version": "1.0",
        }
        with pytest.raises((KeyError, ValueError)):
            svc.register_template("", tpl)

    def test_unicode_in_template(self, svc):
        """模板中包含Unicode字符（中文、emoji）应正常工作"""
        tpl = {
            "system_prompt": "你是营养分析助手🥗",
            "few_shot_examples": [{"input": "红烧肉", "output": "高热量菜品"}],
            "user_prompt_template": "分析: {food_name}",
            "version": "1.0",
        }
        svc.register_template("unicode_test", tpl)
        rendered = svc.render_prompt("unicode_test", variables={"food_name": "麻辣火锅🔥"})
        assert "麻辣火锅🔥" in rendered["user_prompt"]

    def test_large_few_shot_examples(self, svc):
        """大量few-shot示例不影响功能"""
        examples = [
            {"input": f"菜品{i}", "output": f"分析{i}"} for i in range(50)
        ]
        tpl = {
            "system_prompt": "测试",
            "few_shot_examples": examples,
            "user_prompt_template": "{query}",
            "version": "1.0",
        }
        svc.register_template("large_few_shot", tpl)
        rendered = svc.render_prompt("large_few_shot", variables={"query": "测试"}, max_examples=5)
        assert len(rendered["few_shot_messages"]) == 10  # 5 pairs * 2

    def test_special_chars_in_variables(self, svc):
        """变量中包含特殊字符（大括号等）不崩溃"""
        tpl = {
            "system_prompt": "系统",
            "few_shot_examples": [],
            "user_prompt_template": "处理: {query}",
            "version": "1.0",
        }
        svc.register_template("special_chars", tpl)
        rendered = svc.render_prompt("special_chars", variables={
            "query": "包含{大括号}和$特殊字符"
        })
        assert rendered is not None

    def test_template_immutability(self, svc):
        """get_template返回的应是副本，修改不影响原模板"""
        tpl = svc.get_template("food_analysis")
        original_system = tpl["system_prompt"]
        tpl["system_prompt"] = "被修改了"
        
        tpl2 = svc.get_template("food_analysis")
        assert tpl2["system_prompt"] == original_system


# ────────────────────────────────────────────────────────────
# 10. 并发安全性
# ────────────────────────────────────────────────────────────
class TestConcurrency:
    """测试多线程并发访问安全性"""

    @pytest.fixture
    def svc(self, tmp_path):
        from app.services.prompt_template_service import PromptTemplateService
        return PromptTemplateService(templates_dir=str(tmp_path))

    def test_concurrent_reads(self, svc):
        """并发读取模板不崩溃"""
        errors = []

        def read_template():
            try:
                for _ in range(50):
                    tpl = svc.get_template("food_analysis")
                    assert tpl is not None
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=read_template) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"并发读取出错: {errors}"

    def test_concurrent_render(self, svc):
        """并发渲染模板不崩溃"""
        errors = []

        def render_template(idx):
            try:
                for _ in range(20):
                    rendered = svc.render_prompt("food_analysis", variables={
                        "food_name": f"菜品{idx}"
                    })
                    assert f"菜品{idx}" in rendered["user_prompt"]
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=render_template, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"并发渲染出错: {errors}"


# ────────────────────────────────────────────────────────────
# 运行入口
# ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
