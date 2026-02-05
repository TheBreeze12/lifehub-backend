"""
Phase 19: METs精准热量计算 - 测试文件

测试内容：
1. METs值表正确性
2. 热量计算公式：消耗(kcal) = METs × 体重(kg) × 时间(h)
3. 运动类型识别
4. 边界情况处理
5. 与trip路由的集成
"""

import pytest
import sys
import os
from datetime import datetime, date

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMETsValueTable:
    """测试METs值表的正确性"""
    
    def test_mets_table_exists(self):
        """测试METs值表存在"""
        from app.services.mets_service import METsService
        service = METsService()
        assert hasattr(service, 'METS_TABLE') or hasattr(service, 'mets_table')
        
    def test_walking_mets_value(self):
        """测试步行METs值（约3.0-4.0）"""
        from app.services.mets_service import METsService
        service = METsService()
        mets = service.get_mets_value("walking")
        assert 2.5 <= mets <= 5.0, f"步行METs值应在2.5-5.0之间，实际：{mets}"
        
    def test_running_mets_value(self):
        """测试跑步METs值（约7.0-12.0）"""
        from app.services.mets_service import METsService
        service = METsService()
        mets = service.get_mets_value("running")
        assert 6.0 <= mets <= 15.0, f"跑步METs值应在6.0-15.0之间，实际：{mets}"
        
    def test_cycling_mets_value(self):
        """测试骑行METs值（约4.0-8.0）"""
        from app.services.mets_service import METsService
        service = METsService()
        mets = service.get_mets_value("cycling")
        assert 3.5 <= mets <= 12.0, f"骑行METs值应在3.5-12.0之间，实际：{mets}"
        
    def test_swimming_mets_value(self):
        """测试游泳METs值（约6.0-10.0）"""
        from app.services.mets_service import METsService
        service = METsService()
        mets = service.get_mets_value("swimming")
        assert 5.0 <= mets <= 12.0, f"游泳METs值应在5.0-12.0之间，实际：{mets}"
        
    def test_gym_mets_value(self):
        """测试健身房训练METs值"""
        from app.services.mets_service import METsService
        service = METsService()
        mets = service.get_mets_value("gym")
        assert 3.0 <= mets <= 8.0, f"健身房训练METs值应在3.0-8.0之间，实际：{mets}"
        
    def test_unknown_exercise_default_mets(self):
        """测试未知运动类型返回默认METs值"""
        from app.services.mets_service import METsService
        service = METsService()
        mets = service.get_mets_value("unknown_exercise_type")
        assert mets > 0, "未知运动类型应返回正的默认METs值"
        assert 2.0 <= mets <= 5.0, "未知运动类型应返回合理的默认METs值"


class TestCalorieCalculation:
    """测试热量计算公式"""
    
    def test_basic_calorie_formula(self):
        """测试基础热量计算公式：消耗(kcal) = METs × 体重(kg) × 时间(h)"""
        from app.services.mets_service import METsService
        service = METsService()
        
        # 假设：步行(METs=3.5)，体重70kg，1小时
        weight_kg = 70.0
        duration_hours = 1.0
        exercise_type = "walking"
        
        calories = service.calculate_calories(
            exercise_type=exercise_type,
            weight_kg=weight_kg,
            duration_minutes=60
        )
        
        # 预期消耗：3.5 × 70 × 1 = 245 kcal（允许10%误差）
        mets = service.get_mets_value("walking")
        expected = mets * weight_kg * duration_hours
        assert abs(calories - expected) < expected * 0.1, f"计算结果{calories}与预期{expected}差异过大"
        
    def test_calorie_calculation_with_different_weights(self):
        """测试不同体重的热量计算"""
        from app.services.mets_service import METsService
        service = METsService()
        
        # 相同运动，不同体重
        light_person = service.calculate_calories("walking", 50.0, 30)
        heavy_person = service.calculate_calories("walking", 100.0, 30)
        
        # 重的人消耗应该更多
        assert heavy_person > light_person, "体重大的人运动消耗应该更高"
        # 体重翻倍，消耗也应该翻倍
        ratio = heavy_person / light_person
        assert 1.9 <= ratio <= 2.1, f"体重翻倍，消耗应该接近翻倍，实际比例：{ratio}"
        
    def test_calorie_calculation_with_different_durations(self):
        """测试不同时长的热量计算"""
        from app.services.mets_service import METsService
        service = METsService()
        
        # 相同运动和体重，不同时长
        short_exercise = service.calculate_calories("running", 70.0, 15)
        long_exercise = service.calculate_calories("running", 70.0, 60)
        
        # 时间翻4倍，消耗也应该翻4倍
        ratio = long_exercise / short_exercise
        assert 3.8 <= ratio <= 4.2, f"时间翻4倍，消耗应该接近翻4倍，实际比例：{ratio}"
        
    def test_running_burns_more_than_walking(self):
        """测试跑步消耗比步行多"""
        from app.services.mets_service import METsService
        service = METsService()
        
        weight = 70.0
        duration = 30  # 分钟
        
        walking_calories = service.calculate_calories("walking", weight, duration)
        running_calories = service.calculate_calories("running", weight, duration)
        
        assert running_calories > walking_calories, "跑步消耗应该比步行多"
        # 跑步METs通常是步行的2倍以上
        ratio = running_calories / walking_calories
        assert ratio >= 1.5, f"跑步消耗应该至少是步行的1.5倍，实际：{ratio}"


class TestEdgeCases:
    """测试边界情况"""
    
    def test_zero_duration(self):
        """测试0时长"""
        from app.services.mets_service import METsService
        service = METsService()
        
        calories = service.calculate_calories("walking", 70.0, 0)
        assert calories == 0, "0时长应该返回0热量消耗"
        
    def test_negative_duration_handled(self):
        """测试负数时长处理"""
        from app.services.mets_service import METsService
        service = METsService()
        
        # 负数时长应该返回0或抛出异常
        try:
            calories = service.calculate_calories("walking", 70.0, -30)
            assert calories >= 0, "负数时长不应返回负数热量"
        except ValueError:
            pass  # 抛出异常也是可接受的处理方式
            
    def test_none_weight_uses_default(self):
        """测试体重为None时使用默认值"""
        from app.services.mets_service import METsService
        service = METsService()
        
        # 体重为None应该使用默认值（如70kg）
        calories = service.calculate_calories("walking", None, 30)
        assert calories > 0, "体重为None时应使用默认值计算"
        
    def test_very_short_duration(self):
        """测试极短时长（1分钟）"""
        from app.services.mets_service import METsService
        service = METsService()
        
        calories = service.calculate_calories("walking", 70.0, 1)
        assert calories > 0, "1分钟运动也应有热量消耗"
        assert calories < 10, "1分钟步行热量消耗应该很小"
        
    def test_very_long_duration(self):
        """测试长时长（3小时）"""
        from app.services.mets_service import METsService
        service = METsService()
        
        calories = service.calculate_calories("walking", 70.0, 180)
        # 3小时步行约消耗 3.5 × 70 × 3 = 735 kcal
        assert 600 <= calories <= 900, f"3小时步行热量消耗应该在合理范围，实际：{calories}"


class TestExerciseTypeMapping:
    """测试运动类型映射"""
    
    def test_chinese_exercise_type_walking(self):
        """测试中文运动类型：步行/散步"""
        from app.services.mets_service import METsService
        service = METsService()
        
        mets_cn = service.get_mets_value("步行")
        mets_en = service.get_mets_value("walking")
        assert mets_cn == mets_en, "中英文运动类型应该映射到相同METs值"
        
    def test_chinese_exercise_type_running(self):
        """测试中文运动类型：跑步"""
        from app.services.mets_service import METsService
        service = METsService()
        
        mets_cn = service.get_mets_value("跑步")
        mets_en = service.get_mets_value("running")
        assert mets_cn == mets_en, "中英文运动类型应该映射到相同METs值"
        
    def test_park_exercise_type(self):
        """测试park类型（对应轻度活动）"""
        from app.services.mets_service import METsService
        service = METsService()
        
        mets = service.get_mets_value("park")
        assert 2.0 <= mets <= 5.0, "公园活动METs应在合理范围"
        
    def test_indoor_outdoor_types(self):
        """测试室内/室外类型"""
        from app.services.mets_service import METsService
        service = METsService()
        
        indoor_mets = service.get_mets_value("indoor")
        outdoor_mets = service.get_mets_value("outdoor")
        
        assert indoor_mets > 0, "室内运动应有METs值"
        assert outdoor_mets > 0, "室外运动应有METs值"


class TestGetAllExerciseTypes:
    """测试获取所有运动类型"""
    
    def test_get_all_exercise_types(self):
        """测试获取所有支持的运动类型"""
        from app.services.mets_service import METsService
        service = METsService()
        
        exercise_types = service.get_all_exercise_types()
        
        assert isinstance(exercise_types, list), "应返回列表"
        assert len(exercise_types) >= 5, "应至少支持5种运动类型"
        
        # 检查基本运动类型是否包含
        basic_types = ["walking", "running", "cycling"]
        for t in basic_types:
            assert t in exercise_types, f"应包含基本运动类型：{t}"
            
    def test_get_exercise_info(self):
        """测试获取运动类型详细信息"""
        from app.services.mets_service import METsService
        service = METsService()
        
        info = service.get_exercise_info("running")
        
        assert "mets" in info, "应包含METs值"
        assert "name" in info or "name_cn" in info, "应包含运动名称"
        assert info["mets"] > 0, "METs值应为正数"


class TestCalculateForTripItem:
    """测试为运动计划项目计算热量"""
    
    def test_calculate_for_trip_item_basic(self):
        """测试基本的运动项目热量计算"""
        from app.services.mets_service import METsService
        service = METsService()
        
        # 模拟一个运动项目
        trip_item = {
            "placeType": "walking",
            "duration": 30,  # 分钟
        }
        
        calories = service.calculate_for_trip_item(trip_item, weight_kg=70.0)
        assert calories > 0, "运动项目应有热量消耗"
        
    def test_calculate_for_trip_item_with_notes(self):
        """测试从notes字段推断运动类型"""
        from app.services.mets_service import METsService
        service = METsService()
        
        # notes中包含运动类型信息
        trip_item = {
            "placeType": None,
            "duration": 30,
            "notes": "慢跑，注意控制强度"
        }
        
        calories = service.calculate_for_trip_item(trip_item, weight_kg=70.0)
        assert calories > 0, "应能从notes推断运动类型并计算热量"


class TestIntegrationWithTripRouter:
    """测试与trip路由的集成"""
    
    def test_mets_service_can_be_imported_in_router(self):
        """测试METs服务可以在router中导入"""
        try:
            from app.services.mets_service import METsService
            from app.routers.trip import router
            
            service = METsService()
            assert service is not None
        except ImportError as e:
            pytest.fail(f"无法导入METs服务或trip路由：{e}")
            
    def test_calculate_with_typical_values(self):
        """测试典型运动场景的热量计算"""
        from app.services.mets_service import METsService
        service = METsService()
        
        # 场景1：餐后散步30分钟，体重70kg
        walk_cal = service.calculate_calories("walking", 70.0, 30)
        # 预期：3.5 × 70 × 0.5 = 122.5 kcal
        assert 80 <= walk_cal <= 180, f"餐后散步30分钟热量消耗应在合理范围，实际：{walk_cal}"
        
        # 场景2：慢跑20分钟，体重65kg
        run_cal = service.calculate_calories("running", 65.0, 20)
        # 预期：8.0 × 65 × 0.33 = 171.6 kcal
        assert 120 <= run_cal <= 250, f"慢跑20分钟热量消耗应在合理范围，实际：{run_cal}"


class TestRealisticScenarios:
    """测试真实场景"""
    
    def test_scenario_light_weight_person_walking(self):
        """场景：轻体重者步行"""
        from app.services.mets_service import METsService
        service = METsService()
        
        # 50kg的人步行60分钟
        calories = service.calculate_calories("walking", 50.0, 60)
        # 预期约：3.5 × 50 × 1 = 175 kcal
        assert 140 <= calories <= 210, f"轻体重者步行1小时消耗应在合理范围：{calories}"
        
    def test_scenario_heavy_person_running(self):
        """场景：重体重者跑步"""
        from app.services.mets_service import METsService
        service = METsService()
        
        # 90kg的人跑步45分钟
        calories = service.calculate_calories("running", 90.0, 45)
        # 预期约：8.0 × 90 × 0.75 = 540 kcal
        assert 400 <= calories <= 700, f"重体重者跑步45分钟消耗应在合理范围：{calories}"
        
    def test_scenario_target_calorie_burn(self):
        """场景：达到目标热量消耗所需时间计算"""
        from app.services.mets_service import METsService
        service = METsService()
        
        # 70kg的人想通过步行消耗300kcal，需要多长时间？
        target_calories = 300
        weight = 70.0
        
        duration_needed = service.calculate_duration_for_target(
            exercise_type="walking",
            weight_kg=weight,
            target_calories=target_calories
        )
        
        # 验证：用这个时长计算的热量应该接近目标
        actual_calories = service.calculate_calories("walking", weight, duration_needed)
        assert abs(actual_calories - target_calories) < 20, \
            f"计算的时长{duration_needed}分钟应该能消耗接近{target_calories}kcal，实际：{actual_calories}"


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
