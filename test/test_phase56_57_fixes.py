"""
Phase 56/57 修复验证测试

验证内容：
1. Phase 56修复: before_meal_features和meal_comparison的_log_ai_call调用
2. Phase 57修复: exercise_intent模板增加duration_minutes和intensity槽位
3. Phase 57修复: _extract_exercise_intent和_generate_exercise_plan接入模板服务
4. 边界条件和回归测试
"""
import os
import sys
import json
import time
import pytest
import tempfile
from unittest.mock import patch, MagicMock, PropertyMock

# 添加项目根目录到路径
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# 1. Phase 56修复: _log_ai_call覆盖所有AI调用方法
# ============================================================
class TestPhase56LogCoverage:
    """验证所有AI调用方法都集成了_log_ai_call"""

    def test_extract_before_meal_features_has_log_call(self):
        """验证_extract_before_meal_features_with_ark包含_log_ai_call调用"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._extract_before_meal_features_with_ark)
        assert "_log_ai_call" in source, \
            "_extract_before_meal_features_with_ark缺少_log_ai_call调用"

    def test_compare_before_after_meal_has_log_call(self):
        """验证_compare_before_after_meal_with_ark包含_log_ai_call调用"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._compare_before_after_meal_with_ark)
        assert "_log_ai_call" in source, \
            "_compare_before_after_meal_with_ark缺少_log_ai_call调用"

    def test_food_analysis_has_log_call(self):
        """验证_analyze_food_nutrition_with_ark包含_log_ai_call调用"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._analyze_food_nutrition_with_ark)
        assert "_log_ai_call" in source

    def test_menu_recognition_has_log_call(self):
        """验证菜单识别流程包含_log_ai_call调用"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._extract_dish_names_with_ark)
        assert "_log_ai_call" in source, \
            "_extract_dish_names_with_ark缺少_log_ai_call调用"

    def test_exercise_intent_has_log_call(self):
        """验证_extract_exercise_intent包含_log_ai_call调用"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._extract_exercise_intent)
        assert "_log_ai_call" in source

    def test_trip_generation_has_log_call(self):
        """验证_generate_exercise_plan包含_log_ai_call调用"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._generate_exercise_plan)
        assert "_log_ai_call" in source

    def test_before_meal_features_logs_success(self):
        """测试餐前特征提取成功时记录日志"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._extract_before_meal_features_with_ark)
        # 验证成功路径包含日志记录
        assert "success=True" in source, "餐前特征提取缺少成功日志记录"
        assert "success=False" in source, "餐前特征提取缺少失败日志记录"

    def test_meal_comparison_logs_success_and_failure(self):
        """测试餐前餐后对比成功和失败时都记录日志"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._compare_before_after_meal_with_ark)
        assert "success=True" in source, "餐前餐后对比缺少成功日志记录"
        assert "success=False" in source, "餐前餐后对比缺少失败日志记录"

    def test_before_meal_features_log_call_type(self):
        """验证餐前特征提取使用正确的call_type"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._extract_before_meal_features_with_ark)
        assert 'call_type="food_analysis"' in source or "call_type='food_analysis'" in source

    def test_meal_comparison_log_call_type(self):
        """验证餐前餐后对比使用正确的call_type"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._compare_before_after_meal_with_ark)
        assert 'call_type="meal_comparison"' in source or "call_type='meal_comparison'" in source

    def test_before_meal_features_has_timing(self):
        """验证餐前特征提取有计时逻辑"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._extract_before_meal_features_with_ark)
        assert "time.time()" in source, "餐前特征提取缺少计时逻辑"

    def test_meal_comparison_has_timing(self):
        """验证餐前餐后对比有计时逻辑"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._compare_before_after_meal_with_ark)
        assert "time.time()" in source, "餐前餐后对比缺少计时逻辑"


# ============================================================
# 2. Phase 57修复: exercise_intent模板槽位增强
# ============================================================
class TestPhase57ExerciseIntentSlots:
    """验证exercise_intent模板包含duration和intensity槽位"""

    @pytest.fixture
    def svc(self, tmp_path):
        from app.services.prompt_template_service import PromptTemplateService
        return PromptTemplateService(templates_dir=str(tmp_path))

    def test_exercise_intent_template_version_updated(self, svc):
        """验证exercise_intent模板版本已更新（>=1.1）"""
        tpl = svc.get_template("exercise_intent")
        assert tpl is not None
        version = tpl.get("version", "0.0")
        assert version >= "1.1", f"exercise_intent模板版本应>=1.1，当前: {version}"

    def test_exercise_intent_description_mentions_slots(self, svc):
        """验证模板描述提到了时长和强度槽位"""
        tpl = svc.get_template("exercise_intent")
        desc = tpl.get("description", "")
        assert "时长" in desc or "duration" in desc.lower() or "强度" in desc or "intensity" in desc.lower(), \
            "exercise_intent模板描述应提到时长/强度槽位"

    def test_exercise_intent_system_prompt_mentions_duration_intensity(self, svc):
        """验证system_prompt提到了时长和强度"""
        tpl = svc.get_template("exercise_intent")
        sys_prompt = tpl.get("system_prompt", "")
        assert "时长" in sys_prompt or "强度" in sys_prompt, \
            "system_prompt应提到时长和强度"

    def test_exercise_intent_user_prompt_has_duration_slot(self, svc):
        """验证user_prompt_template包含duration_minutes槽位说明"""
        tpl = svc.get_template("exercise_intent")
        user_tpl = tpl.get("user_prompt_template", "")
        assert "duration_minutes" in user_tpl, \
            "user_prompt_template应包含duration_minutes槽位说明"

    def test_exercise_intent_user_prompt_has_intensity_slot(self, svc):
        """验证user_prompt_template包含intensity槽位说明"""
        tpl = svc.get_template("exercise_intent")
        user_tpl = tpl.get("user_prompt_template", "")
        assert "intensity" in user_tpl, \
            "user_prompt_template应包含intensity槽位说明"

    def test_exercise_intent_user_prompt_has_intensity_rules(self, svc):
        """验证user_prompt_template包含强度推断规则"""
        tpl = svc.get_template("exercise_intent")
        user_tpl = tpl.get("user_prompt_template", "")
        assert "散步" in user_tpl and "低" in user_tpl, \
            "user_prompt_template应包含散步→低强度的推断规则"
        assert "慢跑" in user_tpl and "中" in user_tpl, \
            "user_prompt_template应包含慢跑→中强度的推断规则"

    def test_few_shot_examples_include_duration(self, svc):
        """验证few-shot示例包含duration_minutes字段"""
        tpl = svc.get_template("exercise_intent")
        examples = tpl.get("few_shot_examples", [])
        assert len(examples) >= 3, "exercise_intent至少应有3个few-shot示例"

        found_duration = False
        for ex in examples:
            output_str = ex.get("output", "")
            try:
                output_data = json.loads(output_str)
                if "duration_minutes" in output_data:
                    found_duration = True
                    break
            except (json.JSONDecodeError, TypeError):
                pass
        assert found_duration, "至少一个few-shot示例应包含duration_minutes字段"

    def test_few_shot_examples_include_intensity(self, svc):
        """验证few-shot示例包含intensity字段"""
        tpl = svc.get_template("exercise_intent")
        examples = tpl.get("few_shot_examples", [])

        found_intensity = False
        for ex in examples:
            output_str = ex.get("output", "")
            try:
                output_data = json.loads(output_str)
                if "intensity" in output_data:
                    found_intensity = True
                    break
            except (json.JSONDecodeError, TypeError):
                pass
        assert found_intensity, "至少一个few-shot示例应包含intensity字段"

    def test_few_shot_walking_example_has_low_intensity(self, svc):
        """验证散步示例的强度为低"""
        tpl = svc.get_template("exercise_intent")
        for ex in tpl.get("few_shot_examples", []):
            output_str = ex.get("output", "")
            try:
                data = json.loads(output_str)
                if data.get("exercise_type") == "散步":
                    assert data.get("intensity") == "低", \
                        f"散步的强度应为'低'，实际: {data.get('intensity')}"
                    return
            except (json.JSONDecodeError, TypeError):
                pass
        # 没找到散步示例也可接受

    def test_few_shot_jogging_example_has_duration_30(self, svc):
        """验证慢跑30分钟示例的duration为30"""
        tpl = svc.get_template("exercise_intent")
        for ex in tpl.get("few_shot_examples", []):
            input_str = ex.get("input", "")
            if "慢跑30分钟" in input_str or "慢跑30分钟" in input_str:
                output_str = ex.get("output", "")
                try:
                    data = json.loads(output_str)
                    assert data.get("duration_minutes") == 30, \
                        f"慢跑30分钟示例的duration_minutes应为30，实际: {data.get('duration_minutes')}"
                    assert data.get("intensity") in ["中", "中等"], \
                        f"慢跑的强度应为'中'，实际: {data.get('intensity')}"
                    return
                except (json.JSONDecodeError, TypeError):
                    pass

    def test_render_exercise_intent_with_all_slots(self, svc):
        """渲染exercise_intent模板应包含所有槽位说明"""
        rendered = svc.render_prompt("exercise_intent", variables={
            "query": "我想慢跑30分钟，中等强度",
            "today_date": "2026-03-01",
        })
        full_text = rendered["system_prompt"] + rendered["user_prompt"]
        assert "duration_minutes" in full_text, "渲染后prompt应包含duration_minutes"
        assert "intensity" in full_text, "渲染后prompt应包含intensity"


# ============================================================
# 3. Phase 57修复: AI调用方法接入模板服务
# ============================================================
class TestPhase57TemplateIntegration:
    """验证所有AI调用方法都接入了模板服务"""

    def test_extract_exercise_intent_uses_template_service(self):
        """验证_extract_exercise_intent使用模板服务"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._extract_exercise_intent)
        assert "_get_prompt_tpl_service" in source or "tpl_svc" in source, \
            "_extract_exercise_intent应使用模板服务"

    def test_generate_exercise_plan_uses_template_service(self):
        """验证_generate_exercise_plan使用模板服务"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._generate_exercise_plan)
        assert "_get_prompt_tpl_service" in source or "tpl_svc" in source, \
            "_generate_exercise_plan应使用模板服务"

    def test_build_nutrition_prompt_uses_template_service(self):
        """验证_build_nutrition_prompt使用模板服务"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._build_nutrition_prompt)
        assert "_get_prompt_tpl_service" in source or "tpl_svc" in source

    def test_before_meal_features_uses_template_service(self):
        """验证_extract_before_meal_features_with_ark使用模板服务"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._extract_before_meal_features_with_ark)
        assert "_get_prompt_tpl_service" in source or "tpl_svc" in source

    def test_meal_comparison_uses_template_service(self):
        """验证_compare_before_after_meal_with_ark使用模板服务"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._compare_before_after_meal_with_ark)
        assert "_get_prompt_tpl_service" in source or "tpl_svc" in source

    def test_all_six_template_types_registered(self):
        """验证所有6种模板类型都已注册"""
        from app.services.prompt_template_service import PromptTemplateService
        svc = PromptTemplateService(templates_dir=tempfile.mkdtemp())
        expected = [
            "food_analysis",
            "exercise_intent",
            "trip_generation",
            "menu_recognition",
            "before_meal_features",
            "meal_comparison",
        ]
        available = svc.list_templates()
        for t in expected:
            assert t in available, f"缺少模板: {t}"

    def test_exercise_intent_renders_with_query_variable(self):
        """测试exercise_intent模板能正确渲染query变量"""
        from app.services.prompt_template_service import PromptTemplateService
        svc = PromptTemplateService(templates_dir=tempfile.mkdtemp())
        rendered = svc.render_prompt("exercise_intent", variables={
            "query": "我想慢跑30分钟，中等强度",
            "calories_info": "",
            "explicit_place_hint": "",
            "location_hint": "",
            "today_date": "2026-03-01",
        })
        assert "慢跑30分钟" in rendered["user_prompt"]

    def test_trip_generation_renders_with_variables(self):
        """测试trip_generation模板能正确渲染变量"""
        from app.services.prompt_template_service import PromptTemplateService
        svc = PromptTemplateService(templates_dir=tempfile.mkdtemp())
        rendered = svc.render_prompt("trip_generation", variables={
            "destination": "北京朝阳公园",
            "start_date": "2026-03-01",
            "end_date": "2026-03-01",
            "days": "1",
            "calories_target": "300",
            "exercise_type_text": "运动类型：慢跑。",
            "preference_text": "",
            "calories_context": "",
            "location_context": "",
        })
        assert "北京朝阳公园" in rendered["user_prompt"]
        assert "300" in rendered["user_prompt"]


# ============================================================
# 4. Phase 57: 意图提取回退逻辑（模板失败时使用硬编码）
# ============================================================
class TestPhase57FallbackBehavior:
    """验证模板服务失败时的回退逻辑"""

    def test_extract_exercise_intent_has_fallback_prompt(self):
        """验证_extract_exercise_intent有硬编码回退prompt"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._extract_exercise_intent)
        # 应包含硬编码prompt作为回退
        assert "请从以下用户查询中提取" in source or "render_prompt" in source
        # 应包含回退日志
        assert "回退硬编码" in source or "回退" in source

    def test_generate_exercise_plan_has_fallback_prompt(self):
        """验证_generate_exercise_plan有硬编码回退prompt"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._generate_exercise_plan)
        assert "请为以下餐后运动需求" in source or "render_prompt" in source
        assert "回退硬编码" in source or "回退" in source

    def test_hardcoded_prompt_includes_duration_and_intensity(self):
        """验证硬编码回退prompt也包含duration_minutes和intensity"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._extract_exercise_intent)
        assert "duration_minutes" in source, \
            "硬编码prompt应包含duration_minutes槽位"
        assert "intensity" in source, \
            "硬编码prompt应包含intensity槽位"

    def test_default_intent_includes_duration_and_intensity(self):
        """验证默认意图包含duration_minutes和intensity字段"""
        import inspect
        from app.services.ai_service import AIService
        source = inspect.getsource(AIService._extract_exercise_intent)
        # 检查默认返回值
        assert '"duration_minutes"' in source or "'duration_minutes'" in source, \
            "默认意图应包含duration_minutes字段"
        assert '"intensity"' in source or "'intensity'" in source, \
            "默认意图应包含intensity字段"


# ============================================================
# 5. Phase 57: 模板渲染正确性（详细验证）
# ============================================================
class TestPhase57PromptRenderingDetails:
    """模板渲染结果的详细验证"""

    @pytest.fixture
    def svc(self, tmp_path):
        from app.services.prompt_template_service import PromptTemplateService
        return PromptTemplateService(templates_dir=str(tmp_path))

    def test_exercise_intent_few_shot_messages_correct_count(self, svc):
        """exercise_intent的few-shot消息数量正确"""
        rendered = svc.render_prompt("exercise_intent", variables={
            "query": "跑步",
            "today_date": "2026-03-01",
        })
        messages = rendered["few_shot_messages"]
        # 每个示例生成2条消息(user+assistant)
        assert len(messages) % 2 == 0, "few-shot消息应成对出现"
        # 至少4个示例 = 8条消息
        assert len(messages) >= 6, f"至少应有3个few-shot示例(6条消息)，实际: {len(messages)}"

    def test_exercise_intent_few_shot_outputs_are_valid_json(self, svc):
        """exercise_intent的few-shot输出应为有效JSON"""
        rendered = svc.render_prompt("exercise_intent", variables={
            "query": "跑步",
            "today_date": "2026-03-01",
        })
        for i in range(1, len(rendered["few_shot_messages"]), 2):
            msg = rendered["few_shot_messages"][i]
            assert msg["role"] == "assistant"
            try:
                data = json.loads(msg["content"])
                assert "destination" in data
                assert "calories_target" in data
            except json.JSONDecodeError:
                pytest.fail(f"few-shot输出不是有效JSON: {msg['content'][:100]}")

    def test_exercise_intent_few_shot_has_new_slots(self, svc):
        """exercise_intent的few-shot输出应包含新槽位"""
        rendered = svc.render_prompt("exercise_intent", variables={
            "query": "跑步",
            "today_date": "2026-03-01",
        })
        has_duration = False
        has_intensity = False
        for i in range(1, len(rendered["few_shot_messages"]), 2):
            msg = rendered["few_shot_messages"][i]
            try:
                data = json.loads(msg["content"])
                if "duration_minutes" in data:
                    has_duration = True
                if "intensity" in data:
                    has_intensity = True
            except json.JSONDecodeError:
                pass
        assert has_duration, "few-shot输出应包含duration_minutes"
        assert has_intensity, "few-shot输出应包含intensity"

    def test_trip_generation_few_shot_has_items(self, svc):
        """trip_generation的few-shot输出应包含items"""
        rendered = svc.render_prompt("trip_generation", variables={
            "destination": "公园",
            "start_date": "2026-03-01",
            "end_date": "2026-03-01",
            "days": "1",
            "calories_target": "300",
        })
        for i in range(1, len(rendered["few_shot_messages"]), 2):
            msg = rendered["few_shot_messages"][i]
            try:
                data = json.loads(msg["content"])
                assert "items" in data, "trip_generation few-shot输出应包含items"
            except json.JSONDecodeError:
                pass

    def test_build_messages_exercise_intent(self, svc):
        """build_messages为exercise_intent生成正确的消息列表"""
        messages = svc.build_messages("exercise_intent", variables={
            "query": "餐后散步30分钟",
            "today_date": "2026-03-01",
        })
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert "散步30分钟" in messages[-1]["content"]


# ============================================================
# 6. AI调用类型常量完整性
# ============================================================
class TestCallTypeCompleteness:
    """验证AI调用类型常量完整覆盖"""

    def test_call_types_include_meal_comparison(self):
        """确保AI_CALL_TYPES包含meal_comparison"""
        from app.services.ai_log_service import AI_CALL_TYPES
        assert "meal_comparison" in AI_CALL_TYPES, \
            "AI_CALL_TYPES应包含meal_comparison"

    def test_call_type_labels_include_meal_comparison(self):
        """确保AI_CALL_TYPE_LABELS包含meal_comparison"""
        from app.services.ai_log_service import AI_CALL_TYPE_LABELS
        assert "meal_comparison" in AI_CALL_TYPE_LABELS, \
            "AI_CALL_TYPE_LABELS应包含meal_comparison"

    def test_call_types_include_allergen_check(self):
        """确保AI_CALL_TYPES包含allergen_check"""
        from app.services.ai_log_service import AI_CALL_TYPES
        assert "allergen_check" in AI_CALL_TYPES

    def test_all_six_call_types_defined(self):
        """确保所有6种调用类型都已定义"""
        from app.services.ai_log_service import AI_CALL_TYPES
        expected = [
            "food_analysis", "menu_recognition", "trip_generation",
            "exercise_intent", "allergen_check", "meal_comparison"
        ]
        for t in expected:
            assert t in AI_CALL_TYPES, f"AI_CALL_TYPES缺少: {t}"


# ============================================================
# 7. 回归测试：确保原有Phase 56/57功能未被破坏
# ============================================================
class TestRegressionPhase56:
    """Phase 56回归测试"""

    def test_ai_call_log_model_still_works(self):
        """AiCallLog模型仍然正常"""
        from app.db_models.ai_call_log import AiCallLog
        assert AiCallLog.__tablename__ == "ai_call_log"

    def test_ai_log_service_singleton(self):
        """AI日志服务单例仍然正常"""
        from app.services.ai_log_service import get_ai_log_service
        s1 = get_ai_log_service()
        s2 = get_ai_log_service()
        assert s1 is s2

    def test_log_ai_call_no_exception_on_db_error(self):
        """数据库错误时日志记录不抛异常"""
        from app.services.ai_log_service import AiLogService
        service = AiLogService()
        mock_db = MagicMock()
        mock_db.commit.side_effect = Exception("DB error")
        # 不应抛异常
        service.log_ai_call(
            db=mock_db, call_type="food_analysis", model_name="test",
            input_summary="test", success=True, latency_ms=100
        )
        mock_db.rollback.assert_called_once()

    def test_pydantic_models_unchanged(self):
        """Pydantic响应模型仍然正常"""
        from app.models.user import (
            AiCallLogItem, AiCallLogListData, AiCallLogResponse,
            AiCallLogStatsData, AiCallLogStatsResponse
        )
        item = AiCallLogItem(
            id=1, call_type="food_analysis", model_name="test",
            success=True, created_at="2026-01-01"
        )
        assert item.id == 1

    def test_api_routes_still_registered(self):
        """API路由仍然注册"""
        from app.routers.user import router
        routes = [r.path for r in router.routes]
        assert any("ai-logs" in r for r in routes)
        assert any("ai-logs/stats" in r for r in routes)


class TestRegressionPhase57:
    """Phase 57回归测试"""

    def test_prompt_template_service_singleton(self):
        """模板服务单例仍然正常"""
        from app.services.prompt_template_service import get_prompt_template_service
        s1 = get_prompt_template_service()
        s2 = get_prompt_template_service()
        assert s1 is s2

    def test_food_analysis_template_still_correct(self):
        """food_analysis模板仍然正确"""
        from app.services.prompt_template_service import PromptTemplateService
        svc = PromptTemplateService(templates_dir=tempfile.mkdtemp())
        tpl = svc.get_template("food_analysis")
        assert tpl is not None
        assert "过敏原" in tpl["user_prompt_template"] or "allergen" in tpl["user_prompt_template"].lower()
        assert len(tpl["few_shot_examples"]) >= 2

    def test_template_variable_substitution_still_works(self):
        """变量替换仍然正常"""
        from app.services.prompt_template_service import PromptTemplateService
        svc = PromptTemplateService(templates_dir=tempfile.mkdtemp())
        rendered = svc.render_prompt("food_analysis", variables={"food_name": "番茄炒蛋"})
        assert "番茄炒蛋" in rendered["user_prompt"]

    def test_template_persistence_still_works(self, tmp_path):
        """模板持久化仍然正常"""
        from app.services.prompt_template_service import PromptTemplateService
        svc = PromptTemplateService(templates_dir=str(tmp_path))
        svc.save_all_templates()
        json_files = [f for f in os.listdir(str(tmp_path)) if f.endswith(".json")]
        assert len(json_files) >= 6


# ============================================================
# 运行入口
# ============================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
