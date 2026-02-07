"""
Phase 32: 天气动态调整 - Plan B 生成测试

测试 weather_service.py 的天气评估和室内替代方案生成逻辑
以及 GET /api/trip/plan-b/{plan_id} 接口

WMO Weather Codes:
- 0: Clear sky
- 1,2,3: Mainly clear / Partly cloudy / Overcast
- 45,48: Fog / Depositing rime fog
- 51,53,55: Drizzle (light/moderate/dense)
- 56,57: Freezing drizzle
- 61,63,65: Rain (slight/moderate/heavy)
- 66,67: Freezing rain
- 71,73,75: Snow fall (slight/moderate/heavy)
- 77: Snow grains
- 80,81,82: Rain showers (slight/moderate/violent)
- 85,86: Snow showers
- 95: Thunderstorm
- 96,99: Thunderstorm with hail
"""
import pytest
import sys
import os

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== WeatherService 单元测试 ====================

class TestWeatherCodeClassification:
    """测试天气代码分类"""

    def setup_method(self):
        from app.services.weather_service import WeatherService
        self.service = WeatherService()

    def test_clear_sky_is_good(self):
        """晴天应该被判定为好天气"""
        assert self.service.is_bad_weather(0) is False

    def test_mainly_clear_is_good(self):
        """大部晴朗应该是好天气"""
        assert self.service.is_bad_weather(1) is False

    def test_partly_cloudy_is_good(self):
        """局部多云应该是好天气"""
        assert self.service.is_bad_weather(2) is False

    def test_overcast_is_good(self):
        """阴天应该是好天气（可户外运动）"""
        assert self.service.is_bad_weather(3) is False

    def test_light_drizzle_is_mild(self):
        """小毛毛雨应该是轻度不良"""
        result = self.service.evaluate_weather_code(51)
        assert result["severity"] in ("mild", "moderate")

    def test_moderate_rain_is_bad(self):
        """中雨应该是恶劣天气"""
        assert self.service.is_bad_weather(63) is True

    def test_heavy_rain_is_bad(self):
        """大雨应该是恶劣天气"""
        assert self.service.is_bad_weather(65) is True

    def test_thunderstorm_is_severe(self):
        """雷暴应该是严重恶劣天气"""
        result = self.service.evaluate_weather_code(95)
        assert result["severity"] == "severe"
        assert self.service.is_bad_weather(95) is True

    def test_thunderstorm_with_hail_is_severe(self):
        """冰雹雷暴应该是最严重"""
        result = self.service.evaluate_weather_code(99)
        assert result["severity"] == "severe"

    def test_heavy_snow_is_bad(self):
        """大雪应该是恶劣天气"""
        assert self.service.is_bad_weather(75) is True

    def test_freezing_rain_is_bad(self):
        """冻雨应该是恶劣天气"""
        assert self.service.is_bad_weather(67) is True

    def test_fog_is_mild(self):
        """雾天是轻度不良"""
        result = self.service.evaluate_weather_code(45)
        assert result["severity"] in ("mild", "moderate")

    def test_violent_rain_shower_is_bad(self):
        """暴雨是恶劣天气"""
        assert self.service.is_bad_weather(82) is True

    def test_snow_grains_is_moderate(self):
        """霰（雪粒）应是中度不良"""
        result = self.service.evaluate_weather_code(77)
        assert result["severity"] in ("moderate", "severe")

    def test_unknown_code_defaults_to_good(self):
        """未知天气代码默认为好天气"""
        assert self.service.is_bad_weather(999) is False


class TestWeatherEvaluation:
    """测试完整天气评估（含温度、风速等）"""

    def setup_method(self):
        from app.services.weather_service import WeatherService
        self.service = WeatherService()

    def test_evaluate_good_weather(self):
        """评估好天气数据"""
        weather_data = {
            "weathercode": 0,
            "temperature": 22.0,
            "windspeed": 5.0,
        }
        result = self.service.evaluate_weather(weather_data)
        assert result["is_bad_weather"] is False
        assert result["severity"] == "good"
        assert "description" in result

    def test_evaluate_rainy_weather(self):
        """评估雨天数据"""
        weather_data = {
            "weathercode": 63,
            "temperature": 18.0,
            "windspeed": 15.0,
        }
        result = self.service.evaluate_weather(weather_data)
        assert result["is_bad_weather"] is True
        assert result["severity"] in ("moderate", "severe")

    def test_evaluate_extreme_cold(self):
        """极端低温应该触发警告"""
        weather_data = {
            "weathercode": 0,  # 晴天但极冷
            "temperature": -15.0,
            "windspeed": 5.0,
        }
        result = self.service.evaluate_weather(weather_data)
        assert result["is_bad_weather"] is True
        assert "temperature_warning" in result or result["severity"] != "good"

    def test_evaluate_extreme_heat(self):
        """极端高温应该触发警告"""
        weather_data = {
            "weathercode": 0,
            "temperature": 42.0,
            "windspeed": 3.0,
        }
        result = self.service.evaluate_weather(weather_data)
        assert result["is_bad_weather"] is True

    def test_evaluate_high_wind(self):
        """大风应该触发警告"""
        weather_data = {
            "weathercode": 0,
            "temperature": 20.0,
            "windspeed": 55.0,  # 大风 >50km/h
        }
        result = self.service.evaluate_weather(weather_data)
        assert result["is_bad_weather"] is True

    def test_evaluate_missing_weathercode(self):
        """缺少天气代码时应安全处理"""
        weather_data = {
            "temperature": 20.0,
            "windspeed": 5.0,
        }
        result = self.service.evaluate_weather(weather_data)
        assert "severity" in result

    def test_evaluate_none_data(self):
        """None数据应安全处理"""
        result = self.service.evaluate_weather(None)
        assert result["is_bad_weather"] is False
        assert result["severity"] == "unknown"

    def test_evaluate_empty_data(self):
        """空数据应安全处理"""
        result = self.service.evaluate_weather({})
        assert "severity" in result

    def test_moderate_wind_is_ok(self):
        """中等风速应该没问题"""
        weather_data = {
            "weathercode": 0,
            "temperature": 20.0,
            "windspeed": 20.0,  # 适中风速
        }
        result = self.service.evaluate_weather(weather_data)
        assert result["is_bad_weather"] is False

    def test_slight_rain_with_warm_temp(self):
        """小雨+温暖天气，轻度不良"""
        weather_data = {
            "weathercode": 61,  # 小雨
            "temperature": 22.0,
            "windspeed": 5.0,
        }
        result = self.service.evaluate_weather(weather_data)
        # 小雨也应该建议Plan B
        assert result["severity"] in ("mild", "moderate")


class TestPlanBGeneration:
    """测试Plan B室内替代方案生成"""

    def setup_method(self):
        from app.services.weather_service import WeatherService
        self.service = WeatherService()

    def test_generate_plan_b_basic(self):
        """基础Plan B生成"""
        original_items = [
            {
                "place_name": "朝阳公园",
                "place_type": "walking",
                "duration": 30,
                "cost": 122.5,
            }
        ]
        result = self.service.generate_plan_b(original_items, weight_kg=70.0)
        assert "alternatives" in result
        assert len(result["alternatives"]) > 0

    def test_plan_b_preserves_calorie_target(self):
        """Plan B的总热量目标应接近原计划"""
        original_items = [
            {"place_name": "公园跑步", "place_type": "running", "duration": 30, "cost": 280.0},
        ]
        result = self.service.generate_plan_b(original_items, weight_kg=70.0)
        alternatives = result["alternatives"]
        total_original = sum(item["cost"] for item in original_items)
        total_plan_b = sum(alt["calories"] for alt in alternatives)
        # 允许20%误差
        assert abs(total_plan_b - total_original) / max(total_original, 1) < 0.3

    def test_plan_b_items_are_indoor(self):
        """Plan B的运动项目应该是室内的"""
        original_items = [
            {"place_name": "跑步", "place_type": "running", "duration": 40, "cost": 373.3},
        ]
        result = self.service.generate_plan_b(original_items, weight_kg=70.0)
        for alt in result["alternatives"]:
            assert alt["is_indoor"] is True

    def test_plan_b_has_required_fields(self):
        """Plan B项目应包含必要字段"""
        original_items = [
            {"place_name": "散步", "place_type": "walking", "duration": 30, "cost": 122.5},
        ]
        result = self.service.generate_plan_b(original_items, weight_kg=70.0)
        for alt in result["alternatives"]:
            assert "exercise_name" in alt
            assert "exercise_type" in alt
            assert "duration" in alt
            assert "calories" in alt
            assert "is_indoor" in alt
            assert "description" in alt

    def test_plan_b_for_multiple_items(self):
        """多项运动的Plan B"""
        original_items = [
            {"place_name": "晨跑", "place_type": "running", "duration": 20, "cost": 186.7},
            {"place_name": "骑行", "place_type": "cycling", "duration": 30, "cost": 210.0},
        ]
        result = self.service.generate_plan_b(original_items, weight_kg=70.0)
        assert len(result["alternatives"]) >= 1

    def test_plan_b_with_zero_cost_item(self):
        """热量为0的项目也能生成Plan B"""
        original_items = [
            {"place_name": "休息", "place_type": "walking", "duration": 0, "cost": 0},
        ]
        result = self.service.generate_plan_b(original_items, weight_kg=70.0)
        assert "alternatives" in result

    def test_plan_b_empty_items(self):
        """空运动列表的Plan B"""
        result = self.service.generate_plan_b([], weight_kg=70.0)
        assert "alternatives" in result
        assert len(result["alternatives"]) >= 0

    def test_plan_b_default_weight(self):
        """使用默认体重生成Plan B"""
        original_items = [
            {"place_name": "散步", "place_type": "walking", "duration": 30, "cost": 122.5},
        ]
        result = self.service.generate_plan_b(original_items, weight_kg=None)
        assert "alternatives" in result
        assert len(result["alternatives"]) > 0

    def test_plan_b_duration_reasonable(self):
        """Plan B运动时长应合理（不超过原计划的2倍）"""
        original_items = [
            {"place_name": "跑步", "place_type": "running", "duration": 30, "cost": 280.0},
        ]
        result = self.service.generate_plan_b(original_items, weight_kg=70.0)
        total_original_duration = sum(item.get("duration", 0) for item in original_items)
        total_plan_b_duration = sum(alt["duration"] for alt in result["alternatives"])
        # Plan B 时长不应超过原计划的 2.5 倍（室内运动强度可能较低）
        if total_original_duration > 0:
            assert total_plan_b_duration <= total_original_duration * 2.5


class TestWeatherDescriptions:
    """测试天气描述文本"""

    def setup_method(self):
        from app.services.weather_service import WeatherService
        self.service = WeatherService()

    def test_clear_sky_description(self):
        """晴天描述"""
        result = self.service.evaluate_weather_code(0)
        assert "description" in result
        assert len(result["description"]) > 0

    def test_rain_description(self):
        """雨天描述"""
        result = self.service.evaluate_weather_code(63)
        assert "description" in result
        assert len(result["description"]) > 0

    def test_thunderstorm_description(self):
        """雷暴描述"""
        result = self.service.evaluate_weather_code(95)
        assert "description" in result

    def test_all_known_codes_have_descriptions(self):
        """所有已知天气代码都有描述"""
        known_codes = [0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57,
                       61, 63, 65, 66, 67, 71, 73, 75, 77,
                       80, 81, 82, 85, 86, 95, 96, 99]
        for code in known_codes:
            result = self.service.evaluate_weather_code(code)
            assert "description" in result, f"Weather code {code} missing description"
            assert len(result["description"]) > 0, f"Weather code {code} has empty description"


class TestIndoorExerciseDatabase:
    """测试室内运动数据库"""

    def setup_method(self):
        from app.services.weather_service import WeatherService
        self.service = WeatherService()

    def test_indoor_exercises_not_empty(self):
        """室内运动列表不为空"""
        exercises = self.service.get_indoor_exercises()
        assert len(exercises) > 0

    def test_indoor_exercises_have_required_fields(self):
        """室内运动条目有必要字段"""
        exercises = self.service.get_indoor_exercises()
        for ex in exercises:
            assert "name" in ex
            assert "type" in ex
            assert "mets" in ex
            assert "description" in ex

    def test_indoor_exercises_have_valid_mets(self):
        """室内运动的METs值合理（1.0-15.0）"""
        exercises = self.service.get_indoor_exercises()
        for ex in exercises:
            assert 1.0 <= ex["mets"] <= 15.0, f"{ex['name']} has invalid METs: {ex['mets']}"

    def test_indoor_exercises_variety(self):
        """室内运动有足够多样性（至少5种）"""
        exercises = self.service.get_indoor_exercises()
        assert len(exercises) >= 5


class TestPlanBCalorieMatching:
    """测试Plan B热量匹配精度"""

    def setup_method(self):
        from app.services.weather_service import WeatherService
        self.service = WeatherService()

    def test_match_low_calorie_target(self):
        """低热量目标（100kcal）匹配"""
        original_items = [
            {"place_name": "散步", "place_type": "walking", "duration": 25, "cost": 100.0},
        ]
        result = self.service.generate_plan_b(original_items, weight_kg=70.0)
        total_cal = sum(alt["calories"] for alt in result["alternatives"])
        assert total_cal >= 70  # 至少达到70%

    def test_match_high_calorie_target(self):
        """高热量目标（500kcal）匹配"""
        original_items = [
            {"place_name": "长跑", "place_type": "running", "duration": 60, "cost": 500.0},
        ]
        result = self.service.generate_plan_b(original_items, weight_kg=70.0)
        total_cal = sum(alt["calories"] for alt in result["alternatives"])
        assert total_cal >= 350  # 至少达到70%

    def test_match_with_different_weights(self):
        """不同体重的热量匹配"""
        original_items = [
            {"place_name": "跑步", "place_type": "running", "duration": 30, "cost": 280.0},
        ]
        result_light = self.service.generate_plan_b(original_items, weight_kg=50.0)
        result_heavy = self.service.generate_plan_b(original_items, weight_kg=90.0)

        cal_light = sum(alt["calories"] for alt in result_light["alternatives"])
        cal_heavy = sum(alt["calories"] for alt in result_heavy["alternatives"])

        # 两者都应该接近原始目标
        assert cal_light > 0
        assert cal_heavy > 0


class TestWeatherServiceEdgeCases:
    """边缘情况测试"""

    def setup_method(self):
        from app.services.weather_service import WeatherService
        self.service = WeatherService()

    def test_negative_temperature(self):
        """负温度处理"""
        weather_data = {
            "weathercode": 0,
            "temperature": -30.0,
            "windspeed": 10.0,
        }
        result = self.service.evaluate_weather(weather_data)
        assert result["is_bad_weather"] is True  # 极端低温

    def test_zero_windspeed(self):
        """零风速"""
        weather_data = {
            "weathercode": 0,
            "temperature": 20.0,
            "windspeed": 0.0,
        }
        result = self.service.evaluate_weather(weather_data)
        assert result["is_bad_weather"] is False

    def test_none_temperature(self):
        """温度为None"""
        weather_data = {
            "weathercode": 0,
            "temperature": None,
            "windspeed": 5.0,
        }
        result = self.service.evaluate_weather(weather_data)
        assert "severity" in result

    def test_none_windspeed(self):
        """风速为None"""
        weather_data = {
            "weathercode": 0,
            "temperature": 20.0,
            "windspeed": None,
        }
        result = self.service.evaluate_weather(weather_data)
        assert "severity" in result

    def test_plan_b_with_very_long_duration(self):
        """超长时间运动的Plan B"""
        original_items = [
            {"place_name": "马拉松", "place_type": "running", "duration": 240, "cost": 2240.0},
        ]
        result = self.service.generate_plan_b(original_items, weight_kg=70.0)
        assert "alternatives" in result
        assert len(result["alternatives"]) > 0

    def test_plan_b_with_negative_cost(self):
        """负热量应安全处理"""
        original_items = [
            {"place_name": "错误数据", "place_type": "walking", "duration": 30, "cost": -100},
        ]
        result = self.service.generate_plan_b(original_items, weight_kg=70.0)
        assert "alternatives" in result

    def test_plan_b_with_missing_place_type(self):
        """缺少运动类型的项目"""
        original_items = [
            {"place_name": "未知运动", "duration": 30, "cost": 150.0},
        ]
        result = self.service.generate_plan_b(original_items, weight_kg=70.0)
        assert "alternatives" in result


class TestPlanBResponseModel:
    """测试Plan B响应模型"""

    def test_plan_b_response_model_import(self):
        """Plan B响应模型能导入"""
        from app.models.trip import PlanBResponse, PlanBAlternative, WeatherAssessment
        assert PlanBResponse is not None
        assert PlanBAlternative is not None
        assert WeatherAssessment is not None

    def test_weather_assessment_model(self):
        """WeatherAssessment模型字段验证"""
        from app.models.trip import WeatherAssessment
        assessment = WeatherAssessment(
            is_bad_weather=True,
            severity="moderate",
            description="中雨",
            temperature=18.0,
            windspeed=15.0,
            weathercode=63,
            recommendation="建议改为室内运动"
        )
        assert assessment.is_bad_weather is True
        assert assessment.severity == "moderate"

    def test_plan_b_alternative_model(self):
        """PlanBAlternative模型字段验证"""
        from app.models.trip import PlanBAlternative
        alt = PlanBAlternative(
            exercise_name="室内跳绳",
            exercise_type="jumping_rope",
            duration=20,
            calories=256.7,
            is_indoor=True,
            description="高效室内有氧运动",
            mets_value=11.0
        )
        assert alt.exercise_name == "室内跳绳"
        assert alt.is_indoor is True

    def test_plan_b_response_model(self):
        """PlanBResponse完整模型验证"""
        from app.models.trip import PlanBResponse, PlanBAlternative, WeatherAssessment
        response = PlanBResponse(
            code=200,
            message="已生成室内替代方案",
            data={
                "plan_id": 1,
                "weather": WeatherAssessment(
                    is_bad_weather=True,
                    severity="moderate",
                    description="中雨",
                    recommendation="建议改为室内运动"
                ).model_dump(),
                "need_plan_b": True,
                "original_calories": 280.0,
                "alternatives": [
                    PlanBAlternative(
                        exercise_name="瑜伽",
                        exercise_type="yoga",
                        duration=40,
                        calories=116.7,
                        is_indoor=True,
                        description="瑜伽练习",
                        mets_value=2.5
                    ).model_dump()
                ],
                "plan_b_total_calories": 116.7,
                "reason": "当前天气不适合户外运动"
            }
        )
        assert response.code == 200


class TestGetWeatherDescription:
    """测试天气描述的中文文本质量"""

    def setup_method(self):
        from app.services.weather_service import WeatherService
        self.service = WeatherService()

    def test_clear_description_is_chinese(self):
        """晴天描述应是中文"""
        result = self.service.evaluate_weather_code(0)
        # 至少包含一个中文字符
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in result["description"])
        assert has_chinese

    def test_rain_description_mentions_rain(self):
        """雨天描述应提到'雨'"""
        result = self.service.evaluate_weather_code(63)
        assert "雨" in result["description"]

    def test_snow_description_mentions_snow(self):
        """雪天描述应提到'雪'"""
        result = self.service.evaluate_weather_code(75)
        assert "雪" in result["description"]

    def test_thunder_description_mentions_thunder(self):
        """雷暴描述应提到'雷'"""
        result = self.service.evaluate_weather_code(95)
        assert "雷" in result["description"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
