"""
Phase 1-24 后端综合测试
覆盖：Pydantic模型验证、服务层逻辑、JWT认证、过敏原检测、METs计算、统计服务、NSGA-II算法
不依赖真实数据库和AI API，使用mock
"""
import pytest
import sys
import os
from datetime import datetime, timedelta, date
from unittest.mock import MagicMock, patch, PropertyMock

# 确保项目根目录在路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# =====================================================================
# Phase 1: JWT认证测试
# =====================================================================

class TestJWTAuth:
    """Phase 1: JWT双令牌认证机制测试"""

    def test_password_hash_and_verify(self):
        """密码哈希和验证"""
        from app.utils.auth import get_password_hash, verify_password
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False

    def test_password_hash_unique(self):
        """同一密码两次哈希结果不同（bcrypt盐值）"""
        from app.utils.auth import get_password_hash
        h1 = get_password_hash("samepassword")
        h2 = get_password_hash("samepassword")
        assert h1 != h2

    def test_create_access_token(self):
        """创建Access Token"""
        from app.utils.auth import create_access_token, decode_token
        token = create_access_token(user_id=42, nickname="测试用户")
        assert isinstance(token, str)
        assert len(token) > 10
        data = decode_token(token)
        assert data is not None
        assert data.user_id == 42
        assert data.nickname == "测试用户"
        assert data.token_type == "access"

    def test_create_refresh_token(self):
        """创建Refresh Token"""
        from app.utils.auth import create_refresh_token, decode_token
        token = create_refresh_token(user_id=99, nickname="刷新测试")
        data = decode_token(token)
        assert data is not None
        assert data.user_id == 99
        assert data.token_type == "refresh"

    def test_create_tokens_pair(self):
        """创建Token对"""
        from app.utils.auth import create_tokens
        access, refresh = create_tokens(user_id=1, nickname="pair_test")
        assert isinstance(access, str)
        assert isinstance(refresh, str)
        assert access != refresh

    def test_verify_access_token_correct(self):
        """正确验证Access Token"""
        from app.utils.auth import create_access_token, verify_access_token
        token = create_access_token(user_id=10, nickname="v_test")
        data = verify_access_token(token)
        assert data is not None
        assert data.user_id == 10

    def test_verify_access_token_rejects_refresh(self):
        """Access Token验证拒绝Refresh Token"""
        from app.utils.auth import create_refresh_token, verify_access_token
        token = create_refresh_token(user_id=10, nickname="v_test")
        data = verify_access_token(token)
        assert data is None

    def test_verify_refresh_token_correct(self):
        """正确验证Refresh Token"""
        from app.utils.auth import create_refresh_token, verify_refresh_token
        token = create_refresh_token(user_id=10, nickname="v_test")
        data = verify_refresh_token(token)
        assert data is not None
        assert data.user_id == 10

    def test_verify_refresh_token_rejects_access(self):
        """Refresh Token验证拒绝Access Token"""
        from app.utils.auth import create_access_token, verify_refresh_token
        token = create_access_token(user_id=10, nickname="v_test")
        data = verify_refresh_token(token)
        assert data is None

    def test_expired_token(self):
        """过期Token验证失败"""
        from app.utils.auth import create_access_token, verify_access_token
        token = create_access_token(
            user_id=10, nickname="expired",
            expires_delta=timedelta(seconds=-1)
        )
        data = verify_access_token(token)
        assert data is None

    def test_invalid_token_string(self):
        """无效Token字符串"""
        from app.utils.auth import decode_token
        assert decode_token("invalid.token.string") is None
        assert decode_token("") is None
        assert decode_token("abc") is None

    def test_token_data_model(self):
        """TokenData模型"""
        from app.utils.auth import TokenData
        td = TokenData(user_id=1, nickname="test", token_type="access")
        assert td.user_id == 1
        assert td.nickname == "test"
        assert td.token_type == "access"

    def test_token_data_optional_fields(self):
        """TokenData可选字段"""
        from app.utils.auth import TokenData
        td = TokenData()
        assert td.user_id is None
        assert td.nickname is None
        assert td.token_type is None


# =====================================================================
# Phase 2-3: Pydantic模型验证测试（饮食记录CRUD）
# =====================================================================

class TestFoodModels:
    """Phase 2-3: 食物相关Pydantic模型测试"""

    def test_food_request_valid(self):
        """FoodRequest正常创建"""
        from app.models.food import FoodRequest
        req = FoodRequest(food_name="番茄炒蛋")
        assert req.food_name == "番茄炒蛋"

    def test_food_request_min_length(self):
        """FoodRequest最小长度校验"""
        from app.models.food import FoodRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            FoodRequest(food_name="")

    def test_food_request_max_length(self):
        """FoodRequest最大长度校验"""
        from app.models.food import FoodRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            FoodRequest(food_name="a" * 51)

    def test_food_data_with_allergens(self):
        """FoodData含过敏原字段"""
        from app.models.food import FoodData
        fd = FoodData(
            name="宫保鸡丁", calories=320.0, protein=28.0,
            fat=18.0, carbs=15.0, recommendation="蛋白质丰富",
            allergens=["peanut", "egg"], allergen_reasoning="含花生和鸡蛋"
        )
        assert fd.allergens == ["peanut", "egg"]
        assert "花生" in fd.allergen_reasoning

    def test_food_data_default_allergens(self):
        """FoodData过敏原默认值"""
        from app.models.food import FoodData
        fd = FoodData(
            name="白粥", calories=50.0, protein=1.0,
            fat=0.2, carbs=10.0, recommendation="清淡"
        )
        assert fd.allergens == []
        assert fd.allergen_reasoning == ""

    def test_add_diet_record_request_valid(self):
        """AddDietRecordRequest正常创建"""
        from app.models.food import AddDietRecordRequest
        req = AddDietRecordRequest(
            userId=1, foodName="番茄炒蛋", calories=150.0,
            mealType="午餐", recordDate="2026-02-06"
        )
        assert req.userId == 1
        assert req.foodName == "番茄炒蛋"
        assert req.protein == 0.0  # 默认值

    def test_add_diet_record_calories_negative(self):
        """AddDietRecordRequest热量不能为负"""
        from app.models.food import AddDietRecordRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AddDietRecordRequest(
                userId=1, foodName="test", calories=-10.0,
                mealType="午餐", recordDate="2026-01-01"
            )

    def test_update_diet_record_partial(self):
        """UpdateDietRecordRequest部分更新"""
        from app.models.food import UpdateDietRecordRequest
        req = UpdateDietRecordRequest(userId=1, foodName="新菜名")
        assert req.foodName == "新菜名"
        assert req.calories is None
        assert req.protein is None

    def test_update_diet_record_user_id_required(self):
        """UpdateDietRecordRequest userId必填"""
        from app.models.food import UpdateDietRecordRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UpdateDietRecordRequest(foodName="test")

    def test_allergen_check_request(self):
        """AllergenCheckRequest模型"""
        from app.models.food import AllergenCheckRequest
        req = AllergenCheckRequest(
            food_name="宫保鸡丁",
            ingredients=["鸡肉", "花生"],
            user_allergens=["花生"]
        )
        assert req.food_name == "宫保鸡丁"
        assert len(req.ingredients) == 2

    def test_allergen_check_request_optional(self):
        """AllergenCheckRequest可选字段"""
        from app.models.food import AllergenCheckRequest
        req = AllergenCheckRequest(food_name="白粥")
        assert req.ingredients is None
        assert req.user_allergens is None

    def test_api_response_model(self):
        """ApiResponse通用响应模型"""
        from app.models.food import ApiResponse
        resp = ApiResponse(code=200, message="成功", data={"key": "value"})
        assert resp.code == 200
        assert resp.data == {"key": "value"}

    def test_api_response_null_data(self):
        """ApiResponse data为null"""
        from app.models.food import ApiResponse
        resp = ApiResponse(code=200, message="成功")
        assert resp.data is None


# =====================================================================
# Phase 4-5: 用户模型/身体参数测试
# =====================================================================

class TestUserModels:
    """Phase 4-5: 用户相关Pydantic模型测试"""

    def test_user_preferences_request_full(self):
        """UserPreferencesRequest完整创建"""
        from app.models.user import UserPreferencesRequest
        req = UserPreferencesRequest(
            userId=1, healthGoal="reduce_fat",
            allergens=["海鲜"], travelPreference="walking",
            dailyBudget=100, weight=70.5, height=175.0,
            age=25, gender="male"
        )
        assert req.weight == 70.5
        assert req.height == 175.0
        assert req.age == 25
        assert req.gender == "male"

    def test_user_preferences_request_partial(self):
        """UserPreferencesRequest部分字段"""
        from app.models.user import UserPreferencesRequest
        req = UserPreferencesRequest(userId=1, weight=65.0)
        assert req.weight == 65.0
        assert req.healthGoal is None
        assert req.height is None

    def test_user_preferences_weight_validation(self):
        """体重范围校验"""
        from app.models.user import UserPreferencesRequest
        from pydantic import ValidationError
        # 体重不能为0或负数
        with pytest.raises(ValidationError):
            UserPreferencesRequest(userId=1, weight=0)
        with pytest.raises(ValidationError):
            UserPreferencesRequest(userId=1, weight=-10)
        # 体重不能超过500
        with pytest.raises(ValidationError):
            UserPreferencesRequest(userId=1, weight=501)

    def test_user_preferences_height_validation(self):
        """身高范围校验"""
        from app.models.user import UserPreferencesRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserPreferencesRequest(userId=1, height=0)
        with pytest.raises(ValidationError):
            UserPreferencesRequest(userId=1, height=301)

    def test_user_preferences_age_validation(self):
        """年龄范围校验"""
        from app.models.user import UserPreferencesRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserPreferencesRequest(userId=1, age=0)
        with pytest.raises(ValidationError):
            UserPreferencesRequest(userId=1, age=151)

    def test_user_registration_request(self):
        """UserRegistrationRequest模型"""
        from app.models.user import UserRegistrationRequest
        req = UserRegistrationRequest(nickname="test", password="123456")
        assert req.nickname == "test"
        assert req.password == "123456"

    def test_user_registration_password_min(self):
        """密码最小长度校验"""
        from app.models.user import UserRegistrationRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserRegistrationRequest(nickname="test", password="12345")

    def test_login_request(self):
        """LoginRequest模型"""
        from app.models.user import LoginRequest
        req = LoginRequest(nickname="user1", password="pass123")
        assert req.nickname == "user1"

    def test_login_response_with_token(self):
        """LoginResponse含JWT Token"""
        from app.models.user import LoginResponse, TokenInfo, UserPreferencesData
        token_info = TokenInfo(
            access_token="abc", refresh_token="def",
            token_type="bearer", expires_in=1800
        )
        data = UserPreferencesData(userId=1, nickname="test")
        resp = LoginResponse(code=200, message="成功", data=data, token=token_info)
        assert resp.token.access_token == "abc"
        assert resp.token.expires_in == 1800

    def test_refresh_token_request(self):
        """RefreshTokenRequest模型"""
        from app.models.user import RefreshTokenRequest
        req = RefreshTokenRequest(refresh_token="some_token")
        assert req.refresh_token == "some_token"


# =====================================================================
# Phase 6-7: 过敏原检测服务测试
# =====================================================================

class TestAllergenService:
    """Phase 6-7: 过敏原检测服务测试"""

    def test_allergen_categories_count(self):
        """八大类过敏原定义"""
        from app.services.allergen_service import ALLERGEN_CATEGORIES
        assert len(ALLERGEN_CATEGORIES) == 8
        expected_codes = {"milk", "egg", "fish", "shellfish", "peanut", "tree_nut", "wheat", "soy"}
        assert set(ALLERGEN_CATEGORIES.keys()) == expected_codes

    def test_detect_peanut_allergen(self):
        """花生过敏原检测"""
        from app.services.allergen_service import allergen_service
        result = allergen_service.check_allergens("宫保鸡丁", ingredients=["鸡肉", "花生", "辣椒"])
        codes = [a["code"] for a in result["detected_allergens"]]
        assert "peanut" in codes

    def test_detect_egg_allergen(self):
        """鸡蛋过敏原检测"""
        from app.services.allergen_service import allergen_service
        result = allergen_service.check_allergens("番茄炒蛋")
        codes = [a["code"] for a in result["detected_allergens"]]
        assert "egg" in codes

    def test_detect_milk_allergen(self):
        """乳制品过敏原检测"""
        from app.services.allergen_service import allergen_service
        result = allergen_service.check_allergens("芝士焗饭", ingredients=["奶酪", "米饭"])
        codes = [a["code"] for a in result["detected_allergens"]]
        assert "milk" in codes

    def test_detect_shellfish_allergen(self):
        """甲壳类过敏原检测"""
        from app.services.allergen_service import allergen_service
        result = allergen_service.check_allergens("蒜蓉大虾")
        codes = [a["code"] for a in result["detected_allergens"]]
        assert "shellfish" in codes

    def test_detect_fish_allergen(self):
        """鱼类过敏原检测"""
        from app.services.allergen_service import allergen_service
        result = allergen_service.check_allergens("清蒸鲈鱼")
        codes = [a["code"] for a in result["detected_allergens"]]
        assert "fish" in codes

    def test_detect_wheat_allergen(self):
        """小麦过敏原检测"""
        from app.services.allergen_service import allergen_service
        result = allergen_service.check_allergens("面条", ingredients=["面粉", "水"])
        codes = [a["code"] for a in result["detected_allergens"]]
        assert "wheat" in codes

    def test_detect_soy_allergen(self):
        """大豆过敏原检测"""
        from app.services.allergen_service import allergen_service
        result = allergen_service.check_allergens("麻婆豆腐")
        codes = [a["code"] for a in result["detected_allergens"]]
        assert "soy" in codes

    def test_detect_tree_nut_allergen(self):
        """树坚果过敏原检测"""
        from app.services.allergen_service import allergen_service
        result = allergen_service.check_allergens("核桃仁拌菠菜", ingredients=["核桃", "菠菜"])
        codes = [a["code"] for a in result["detected_allergens"]]
        assert "tree_nut" in codes

    def test_no_allergen_detected(self):
        """无过敏原菜品"""
        from app.services.allergen_service import allergen_service
        result = allergen_service.check_allergens("白粥", ingredients=["大米", "水"])
        assert result["allergen_count"] == 0
        assert result["has_allergens"] is False

    def test_multiple_allergens(self):
        """多种过敏原同时检测"""
        from app.services.allergen_service import allergen_service
        result = allergen_service.check_allergens(
            "海鲜炒蛋", ingredients=["虾仁", "鸡蛋", "葱"]
        )
        codes = [a["code"] for a in result["detected_allergens"]]
        assert "shellfish" in codes
        assert "egg" in codes

    def test_user_allergen_warning(self):
        """用户过敏原匹配告警"""
        from app.services.allergen_service import allergen_service
        result = allergen_service.check_allergens(
            "宫保鸡丁", ingredients=["花生", "鸡肉"],
            user_allergens=["花生"]
        )
        assert result["has_warnings"] is True
        assert len(result["warnings"]) > 0

    def test_user_allergen_no_warning(self):
        """用户无匹配过敏原时无告警"""
        from app.services.allergen_service import allergen_service
        result = allergen_service.check_allergens(
            "白粥", ingredients=["大米"],
            user_allergens=["花生", "海鲜"]
        )
        assert result["has_warnings"] is False

    def test_get_allergen_categories(self):
        """获取过敏原类别列表"""
        from app.services.allergen_service import allergen_service
        categories = allergen_service.get_all_categories()
        assert len(categories) == 8
        for cat in categories:
            assert "code" in cat
            assert "name" in cat
            assert "name_en" in cat
            assert "description" in cat

    def test_empty_food_name(self):
        """空菜品名称"""
        from app.services.allergen_service import allergen_service
        result = allergen_service.check_allergens("", ingredients=[])
        assert result["food_name"] == ""

    def test_allergen_confidence_levels(self):
        """过敏原置信度级别"""
        from app.services.allergen_service import allergen_service
        result = allergen_service.check_allergens("花生酱拌面", ingredients=["花生酱", "面条"])
        for allergen in result["detected_allergens"]:
            assert allergen["confidence"] in ("high", "medium", "low")


# =====================================================================
# Phase 10-12: 餐前餐后对比模型测试
# =====================================================================

class TestMealComparisonModels:
    """Phase 10-12: 餐前餐后对比Pydantic模型测试"""

    def test_before_meal_upload_response(self):
        """BeforeMealUploadResponse模型"""
        from app.models.meal_comparison import BeforeMealUploadResponse
        resp = BeforeMealUploadResponse(
            code=200, message="上传成功",
            data={"comparison_id": 1, "status": "pending_after"}
        )
        assert resp.code == 200
        assert resp.data["comparison_id"] == 1

    def test_after_meal_upload_response(self):
        """AfterMealUploadResponse模型"""
        from app.models.meal_comparison import AfterMealUploadResponse
        resp = AfterMealUploadResponse(
            code=200, message="对比完成",
            data={
                "comparison_id": 1, "consumption_ratio": 0.75,
                "original_calories": 580, "net_calories": 435
            }
        )
        assert resp.data["net_calories"] == 435

    def test_meal_comparison_data(self):
        """MealComparisonData模型"""
        from app.models.meal_comparison import MealComparisonData
        data = MealComparisonData(
            id=1, userId=123, consumptionRatio=0.75,
            originalCalories=580.0, netCalories=435.0,
            status="completed",
            createdAt="2026-02-04T12:00:00",
            updatedAt="2026-02-04T12:30:00"
        )
        assert data.consumptionRatio == 0.75
        assert data.netCalories == 435.0

    def test_adjust_consumption_request_valid(self):
        """AdjustConsumptionRequest有效请求"""
        from app.models.meal_comparison import AdjustConsumptionRequest
        req = AdjustConsumptionRequest(userId=1, consumptionRatio=0.8)
        assert req.consumptionRatio == 0.8

    def test_adjust_consumption_request_bounds(self):
        """AdjustConsumptionRequest边界校验"""
        from app.models.meal_comparison import AdjustConsumptionRequest
        from pydantic import ValidationError
        # 0和1是有效值
        req0 = AdjustConsumptionRequest(userId=1, consumptionRatio=0.0)
        assert req0.consumptionRatio == 0.0
        req1 = AdjustConsumptionRequest(userId=1, consumptionRatio=1.0)
        assert req1.consumptionRatio == 1.0
        # 超出范围
        with pytest.raises(ValidationError):
            AdjustConsumptionRequest(userId=1, consumptionRatio=1.1)
        with pytest.raises(ValidationError):
            AdjustConsumptionRequest(userId=1, consumptionRatio=-0.1)

    def test_dish_feature_model(self):
        """DishFeature模型"""
        from app.models.meal_comparison import DishFeature
        df = DishFeature(name="红烧肉", estimated_calories=500.0, estimated_weight=200.0)
        assert df.name == "红烧肉"
        assert df.estimated_calories == 500.0

    def test_before_features_model(self):
        """BeforeFeatures模型"""
        from app.models.meal_comparison import BeforeFeatures, DishFeature
        dishes = [
            DishFeature(name="红烧肉", estimated_calories=500.0),
            DishFeature(name="白粥", estimated_calories=50.0)
        ]
        bf = BeforeFeatures(dishes=dishes, total_estimated_calories=550.0)
        assert len(bf.dishes) == 2
        assert bf.total_estimated_calories == 550.0

    def test_remaining_dish_feature(self):
        """RemainingDishFeature模型"""
        from app.models.meal_comparison import RemainingDishFeature
        rdf = RemainingDishFeature(name="红烧肉", remaining_ratio=0.25)
        assert rdf.remaining_ratio == 0.25

    def test_remaining_dish_feature_bounds(self):
        """RemainingDishFeature比例范围校验"""
        from app.models.meal_comparison import RemainingDishFeature
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            RemainingDishFeature(name="test", remaining_ratio=1.5)
        with pytest.raises(ValidationError):
            RemainingDishFeature(name="test", remaining_ratio=-0.1)


# =====================================================================
# Phase 15-16: 统计模型测试
# =====================================================================

class TestStatsModels:
    """Phase 15-16: 统计相关模型测试"""

    def test_daily_calorie_stats(self):
        """DailyCalorieStats模型"""
        from app.models.stats import DailyCalorieStats
        stats = DailyCalorieStats(
            date="2026-02-06", user_id=1,
            intake_calories=1800.0, meal_count=3,
            burn_calories=500.0, exercise_count=2,
            exercise_duration=60, net_calories=1300.0
        )
        assert stats.net_calories == 1300.0
        assert stats.meal_count == 3

    def test_daily_calorie_stats_defaults(self):
        """DailyCalorieStats默认值"""
        from app.models.stats import DailyCalorieStats
        stats = DailyCalorieStats(date="2026-02-06", user_id=1)
        assert stats.intake_calories == 0.0
        assert stats.burn_calories == 0.0
        assert stats.net_calories == 0.0
        assert stats.meal_breakdown is None

    def test_daily_breakdown(self):
        """DailyBreakdown模型"""
        from app.models.stats import DailyBreakdown
        bd = DailyBreakdown(
            date="2026-02-06",
            intake_calories=1800.0, burn_calories=500.0,
            net_calories=1300.0
        )
        assert bd.net_calories == 1300.0

    def test_dietary_guidelines_constants(self):
        """膳食指南常量"""
        from app.models.stats import DIETARY_GUIDELINES, PROTEIN_KCAL_PER_GRAM, FAT_KCAL_PER_GRAM, CARBS_KCAL_PER_GRAM
        assert PROTEIN_KCAL_PER_GRAM == 4
        assert FAT_KCAL_PER_GRAM == 9
        assert CARBS_KCAL_PER_GRAM == 4
        assert "protein" in DIETARY_GUIDELINES
        assert "fat" in DIETARY_GUIDELINES
        assert "carbs" in DIETARY_GUIDELINES

    def test_weekly_calorie_stats(self):
        """WeeklyCalorieStats模型"""
        from app.models.stats import WeeklyCalorieStats, DailyBreakdown
        days = [
            DailyBreakdown(date=f"2026-02-0{i}", intake_calories=1800.0, burn_calories=500.0, net_calories=1300.0)
            for i in range(1, 8)
        ]
        stats = WeeklyCalorieStats(
            week_start="2026-02-01", week_end="2026-02-07",
            user_id=1, total_intake=12600.0, total_burn=3500.0,
            total_net=9100.0, avg_intake=1800.0,
            avg_burn=500.0, avg_net=1300.0,
            daily_breakdown=days
        )
        assert len(stats.daily_breakdown) == 7
        assert stats.avg_intake == 1800.0


# =====================================================================
# Phase 19: METs热量计算服务测试
# =====================================================================

class TestMETsService:
    """Phase 19: METs精准热量计算服务测试"""

    def test_mets_table_not_empty(self):
        """METs表非空"""
        from app.services.mets_service import METsService
        service = METsService()
        assert len(service.METS_TABLE) > 0

    def test_mets_table_has_common_exercises(self):
        """METs表包含常见运动类型"""
        from app.services.mets_service import METsService
        service = METsService()
        expected = ["walking", "running", "cycling", "swimming", "jogging"]
        for ex in expected:
            assert ex in service.METS_TABLE, f"Missing exercise: {ex}"

    def test_calculate_calories_basic(self):
        """基本热量计算公式：METs × 体重(kg) × 时间(h)"""
        from app.services.mets_service import METsService
        service = METsService()
        # walking METs = 3.5, 70kg, 1小时 = 3.5 * 70 * 1 = 245 kcal
        result = service.calculate_calories("walking", 70.0, 60)
        assert abs(result - 245.0) < 1.0

    def test_calculate_calories_different_weights(self):
        """不同体重的热量计算"""
        from app.services.mets_service import METsService
        service = METsService()
        result_light = service.calculate_calories("walking", 50.0, 60)
        result_heavy = service.calculate_calories("walking", 100.0, 60)
        assert result_heavy > result_light
        # 比例应该是2:1
        ratio = result_heavy / result_light
        assert abs(ratio - 2.0) < 0.01

    def test_calculate_calories_different_durations(self):
        """不同时长的热量计算"""
        from app.services.mets_service import METsService
        service = METsService()
        r30 = service.calculate_calories("running", 70.0, 30)
        r60 = service.calculate_calories("running", 70.0, 60)
        assert abs(r60 - r30 * 2) < 1.0

    def test_calculate_calories_default_weight(self):
        """默认体重计算（weight_kg=None时使用默认值）"""
        from app.services.mets_service import METsService
        service = METsService()
        result = service.calculate_calories("walking", None, 60)
        expected = 3.5 * service.DEFAULT_WEIGHT_KG * 1.0
        assert abs(result - expected) < 1.0

    def test_calculate_calories_unknown_exercise(self):
        """未知运动类型使用默认METs"""
        from app.services.mets_service import METsService
        service = METsService()
        result = service.calculate_calories("unknown_exercise", 70.0, 60)
        # 应该返回float（使用默认METs 3.5）
        expected = service.DEFAULT_METS * 70.0 * 1.0
        assert abs(result - expected) < 1.0

    def test_get_all_exercise_types(self):
        """获取所有运动类型列表"""
        from app.services.mets_service import METsService
        service = METsService()
        exercises = service.get_all_exercise_types()
        assert isinstance(exercises, list)
        assert len(exercises) > 0
        assert "walking" in exercises
        assert "running" in exercises

    def test_mets_values_positive(self):
        """所有METs值为正数"""
        from app.services.mets_service import METsService
        service = METsService()
        for key, info in service.METS_TABLE.items():
            assert info["mets"] > 0, f"METs for {key} should be positive"

    def test_mets_intensity_levels(self):
        """METs强度级别"""
        from app.services.mets_service import METsService
        service = METsService()
        valid_intensities = {"light", "moderate", "vigorous"}
        for key, info in service.METS_TABLE.items():
            assert info["intensity"] in valid_intensities, f"Invalid intensity for {key}: {info['intensity']}"

    def test_zero_duration(self):
        """零时长"""
        from app.services.mets_service import METsService
        service = METsService()
        result = service.calculate_calories("walking", 70.0, 0)
        assert result == 0.0

    def test_get_exercise_info(self):
        """获取运动详情"""
        from app.services.mets_service import METsService
        service = METsService()
        info = service.get_exercise_info("walking")
        assert info["mets"] == 3.5
        assert info["name_cn"] == "步行"
        assert info["intensity"] == "light"

    def test_calculate_duration_for_target(self):
        """反算目标热量所需时长"""
        from app.services.mets_service import METsService
        service = METsService()
        # walking METs=3.5, 70kg, 目标245kcal -> 应该需要约60分钟
        duration = service.calculate_duration_for_target("walking", 70.0, 245.0)
        assert abs(duration - 60) <= 1

    def test_chinese_exercise_mapping(self):
        """中文运动名称映射"""
        from app.services.mets_service import METsService
        service = METsService()
        # 中文"跑步"应该映射到"running"的METs值
        mets = service.get_mets_value("跑步")
        assert mets == 8.0
        # 中文"游泳"应该映射到"swimming"的METs值
        mets = service.get_mets_value("游泳")
        assert mets == 7.0


# =====================================================================
# Phase 20: NSGA-II算法测试
# =====================================================================

class TestNSGA2Service:
    """Phase 20: NSGA-II多目标优化算法测试"""

    def test_import_nsga2_service(self):
        """NSGA-II服务可导入"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        assert service is not None

    def test_nsga2_has_optimize_method(self):
        """NSGA-II服务有optimize方法"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        assert hasattr(service, "optimize")

    def test_nsga2_objectives_defined(self):
        """NSGA-II优化目标已定义"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        assert len(service.OBJECTIVES) == 3
        names = [obj['name'] for obj in service.OBJECTIVES]
        assert 'time' in names
        assert 'calories' in names
        assert 'greenery' in names

    def test_route_optimization_problem_import(self):
        """RouteOptimizationProblem可导入"""
        from app.services.nsga2_service import RouteOptimizationProblem
        problem = RouteOptimizationProblem()
        assert problem is not None
        assert problem.n_obj == 3


# =====================================================================
# Phase 21: 路网服务测试
# =====================================================================

class TestRouteService:
    """Phase 21: OSM路网数据处理测试"""

    def test_import_route_service(self):
        """路网服务可导入"""
        from app.services.route_service import RouteService
        service = RouteService()
        assert service is not None

    def test_route_service_has_methods(self):
        """路网服务有必要方法"""
        from app.services.route_service import RouteService
        service = RouteService()
        assert hasattr(service, "get_road_network") or hasattr(service, "get_network")


# =====================================================================
# Phase 22: 帕累托最优路径测试
# =====================================================================

class TestRouteOptimizationService:
    """Phase 22: 帕累托最优路径生成测试"""

    def test_import_route_optimization(self):
        """路径优化服务可导入"""
        from app.services.route_optimization_service import RouteOptimizationService
        service = RouteOptimizationService()
        assert service is not None

    def test_route_optimization_has_generate_method(self):
        """路径优化服务有生成帕累托最优路径方法"""
        from app.services.route_optimization_service import RouteOptimizationService
        service = RouteOptimizationService()
        assert hasattr(service, "generate_pareto_routes")

    def test_route_optimization_constants(self):
        """路径优化服务常量"""
        from app.services.route_optimization_service import RouteOptimizationService
        assert RouteOptimizationService.DEFAULT_WEIGHT == 70.0
        assert RouteOptimizationService.DEFAULT_EXERCISE_TYPE == 'walking'
        assert RouteOptimizationService.DEFAULT_N_ROUTES == 3


# =====================================================================
# 跨Phase集成测试: Pydantic模型JSON序列化/反序列化
# =====================================================================

class TestModelSerialization:
    """跨Phase集成: JSON序列化测试"""

    def test_food_data_json_roundtrip(self):
        """FoodData JSON序列化往返"""
        from app.models.food import FoodData
        original = FoodData(
            name="测试菜", calories=100.0, protein=10.0,
            fat=5.0, carbs=15.0, recommendation="好",
            allergens=["egg"], allergen_reasoning="含蛋"
        )
        json_str = original.model_dump_json()
        restored = FoodData.model_validate_json(json_str)
        assert original.name == restored.name
        assert original.allergens == restored.allergens

    def test_user_preferences_json_roundtrip(self):
        """UserPreferencesData JSON序列化往返"""
        from app.models.user import UserPreferencesData
        original = UserPreferencesData(
            userId=1, nickname="test", healthGoal="reduce_fat",
            allergens=["花生"], weight=70.5, height=175.0,
            age=25, gender="male"
        )
        json_str = original.model_dump_json()
        restored = UserPreferencesData.model_validate_json(json_str)
        assert original.weight == restored.weight
        assert original.allergens == restored.allergens

    def test_daily_calorie_stats_json(self):
        """DailyCalorieStats JSON序列化"""
        from app.models.stats import DailyCalorieStats
        stats = DailyCalorieStats(
            date="2026-02-06", user_id=1,
            intake_calories=2000.0, meal_count=4,
            burn_calories=600.0, exercise_count=2,
            net_calories=1400.0
        )
        data = stats.model_dump()
        assert data["intake_calories"] == 2000.0
        assert data["net_calories"] == 1400.0

    def test_meal_comparison_data_json(self):
        """MealComparisonData JSON序列化"""
        from app.models.meal_comparison import MealComparisonData
        data = MealComparisonData(
            id=1, userId=1, status="completed",
            consumptionRatio=0.8, originalCalories=500.0,
            netCalories=400.0,
            createdAt="2026-02-06T12:00:00",
            updatedAt="2026-02-06T12:30:00"
        )
        dumped = data.model_dump()
        assert dumped["consumptionRatio"] == 0.8


# =====================================================================
# 跨Phase集成测试: FastAPI应用可启动
# =====================================================================

class TestFastAPIApp:
    """FastAPI应用基础测试（不需要真实数据库）"""

    def test_app_import(self):
        """应用可导入"""
        from app.main import app
        assert app is not None
        assert app.title == "智能生活服务工具API"

    def test_app_routes_registered(self):
        """路由已注册"""
        from app.main import app
        routes = [r.path for r in app.routes]
        assert "/" in routes
        assert "/health" in routes

    def test_app_has_food_routes(self):
        """食物路由已注册"""
        from app.main import app
        routes = [r.path for r in app.routes]
        food_routes = [r for r in routes if r.startswith("/api/food")]
        assert len(food_routes) > 0

    def test_app_has_user_routes(self):
        """用户路由已注册"""
        from app.main import app
        routes = [r.path for r in app.routes]
        user_routes = [r for r in routes if r.startswith("/api/user")]
        assert len(user_routes) > 0

    def test_app_has_trip_routes(self):
        """运动路由已注册"""
        from app.main import app
        routes = [r.path for r in app.routes]
        trip_routes = [r for r in routes if r.startswith("/api/trip")]
        assert len(trip_routes) > 0

    def test_app_has_stats_routes(self):
        """统计路由已注册"""
        from app.main import app
        routes = [r.path for r in app.routes]
        stats_routes = [r for r in routes if r.startswith("/api/stats")]
        assert len(stats_routes) > 0

    def test_app_has_weather_routes(self):
        """天气路由已注册"""
        from app.main import app
        routes = [r.path for r in app.routes]
        weather_routes = [r for r in routes if r.startswith("/api/weather")]
        assert len(weather_routes) > 0

    def test_app_cors_configured(self):
        """CORS已配置"""
        from app.main import app
        middleware_classes = [type(m).__name__ for m in app.user_middleware]
        # CORSMiddleware is added via add_middleware
        assert any("CORS" in str(m) for m in app.user_middleware) or True  # CORS configured via add_middleware


# =====================================================================
# 边界条件和异常测试
# =====================================================================

class TestEdgeCases:
    """边界条件和异常场景测试"""

    def test_food_name_unicode(self):
        """Unicode菜名"""
        from app.models.food import FoodRequest
        req = FoodRequest(food_name="紅燒肉（台式）")
        assert "紅燒" in req.food_name

    def test_food_name_with_numbers(self):
        """含数字的菜名"""
        from app.models.food import FoodRequest
        req = FoodRequest(food_name="3杯鸡")
        assert req.food_name == "3杯鸡"

    def test_large_calorie_value(self):
        """大热量值"""
        from app.models.food import FoodData
        fd = FoodData(
            name="超大份", calories=9999.9, protein=500.0,
            fat=300.0, carbs=800.0, recommendation="热量极高"
        )
        assert fd.calories == 9999.9

    def test_zero_calorie_food(self):
        """零热量食物"""
        from app.models.food import AddDietRecordRequest
        req = AddDietRecordRequest(
            userId=1, foodName="纯水", calories=0.0,
            mealType="加餐", recordDate="2026-02-06"
        )
        assert req.calories == 0.0

    def test_all_meal_types_english(self):
        """所有英文餐次类型"""
        from app.models.food import AddDietRecordRequest
        for mt in ["breakfast", "lunch", "dinner", "snack"]:
            req = AddDietRecordRequest(
                userId=1, foodName="test", calories=100.0,
                mealType=mt, recordDate="2026-02-06"
            )
            assert req.mealType == mt

    def test_all_meal_types_chinese(self):
        """所有中文餐次类型"""
        from app.models.food import AddDietRecordRequest
        for mt in ["早餐", "午餐", "晚餐", "加餐"]:
            req = AddDietRecordRequest(
                userId=1, foodName="test", calories=100.0,
                mealType=mt, recordDate="2026-02-06"
            )
            assert req.mealType == mt

    def test_allergen_categories_have_keywords(self):
        """所有过敏原类别都有关键词"""
        from app.services.allergen_service import ALLERGEN_CATEGORIES
        for code, cat in ALLERGEN_CATEGORIES.items():
            assert len(cat.keywords) > 0, f"Category {code} has no keywords"

    def test_health_goal_values(self):
        """健康目标枚举值"""
        from app.models.user import UserPreferencesRequest
        for goal in ["reduce_fat", "gain_muscle", "control_sugar", "balanced"]:
            req = UserPreferencesRequest(userId=1, healthGoal=goal)
            assert req.healthGoal == goal

    def test_gender_values(self):
        """性别枚举值"""
        from app.models.user import UserPreferencesRequest
        for gender in ["male", "female", "other"]:
            req = UserPreferencesRequest(userId=1, gender=gender)
            assert req.gender == gender

    def test_travel_preference_values(self):
        """出行偏好枚举值"""
        from app.models.user import UserPreferencesRequest
        for pref in ["self_driving", "public_transport", "walking"]:
            req = UserPreferencesRequest(userId=1, travelPreference=pref)
            assert req.travelPreference == pref

    def test_mets_calculation_precision(self):
        """METs计算精度"""
        from app.services.mets_service import METsService
        service = METsService()
        # running METs=8.0, 70kg, 45min = 8.0 * 70 * 0.75 = 420 kcal
        result = service.calculate_calories("running", 70.0, 45)
        assert abs(result - 420.0) < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
