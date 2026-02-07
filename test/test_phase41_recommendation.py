"""
Phase 41 测试文件：个性化菜品推荐接口
测试覆盖：
1. 推荐服务单元测试（算法逻辑）
2. API接口集成测试
3. 边缘情况测试

注意：本测试使用 SQLite 内存数据库，不依赖 MySQL
"""
import sys
import os
import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ============================================================
# 测试用 SQLite 内存数据库配置（覆盖 MySQL 配置）
# ============================================================
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = "sqlite:///./test_phase41.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# 导入 Base 并创建表
from app.database import Base
from app.db_models.user import User
from app.db_models.diet_record import DietRecord

# 创建所有表
Base.metadata.create_all(bind=test_engine)


def get_test_db():
    """测试用数据库会话"""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def clean_db():
    """每个测试前清空数据库"""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    # 测试后也清理
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """获取测试数据库会话"""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_test_user(db, user_id=1, health_goal="reduce_fat", allergens=None,
                     weight=70.0, height=170.0, age=30, gender="male"):
    """创建测试用户"""
    user = User(
        id=user_id,
        nickname=f"test_user_{user_id}",
        password="test_password",
        health_goal=health_goal,
        allergens=allergens or [],
        weight=weight,
        height=height,
        age=age,
        gender=gender,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_test_diet_record(db, user_id=1, food_name="番茄炒蛋",
                            calories=150.0, protein=10.0, fat=8.0, carbs=6.0,
                            meal_type="lunch", record_date=None):
    """创建测试饮食记录"""
    record = DietRecord(
        user_id=user_id,
        food_name=food_name,
        calories=calories,
        protein=protein,
        fat=fat,
        carbs=carbs,
        meal_type=meal_type,
        record_date=record_date or date.today(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ============================================================
# 1. 推荐服务单元测试
# ============================================================
class TestRecommendationService:
    """推荐服务核心逻辑测试"""

    def test_basic_recommendation(self, db_session):
        """测试基本推荐功能：返回非空推荐列表"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="balanced")
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch", limit=5)

        assert result is not None
        assert result.user_id == 1
        assert result.meal_type == "lunch"
        assert result.health_goal == "balanced"
        assert result.health_goal_label == "均衡"
        assert len(result.recommendations) > 0
        assert len(result.recommendations) <= 5

    def test_reduce_fat_goal_prefers_low_cal_high_protein(self, db_session):
        """测试减脂目标：应优先推荐低热量高蛋白菜品"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="reduce_fat")
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch", limit=10)

        # 前3名应该是低热量或高蛋白
        top_3 = result.recommendations[:3]
        for food in top_3:
            # 减脂推荐不应含高热量食物（>300kcal）
            assert food.calories <= 300, f"{food.food_name} 热量 {food.calories} 过高，不适合减脂推荐前列"

    def test_gain_muscle_goal_prefers_high_protein(self, db_session):
        """测试增肌目标：应优先推荐高蛋白菜品"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="gain_muscle")
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch", limit=10)

        # 前3名蛋白质应该较高
        top_3 = result.recommendations[:3]
        for food in top_3:
            assert food.protein >= 10.0, f"{food.food_name} 蛋白质 {food.protein} 偏低，不适合增肌推荐前列"

    def test_control_sugar_goal_prefers_low_carbs(self, db_session):
        """测试控糖目标：应优先推荐低碳水菜品"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="control_sugar")
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch", limit=10)

        # 前3名碳水应该较低
        top_3 = result.recommendations[:3]
        for food in top_3:
            assert food.carbs <= 20.0, f"{food.food_name} 碳水 {food.carbs} 偏高，不适合控糖推荐前列"

    def test_allergen_filtering(self, db_session):
        """测试过敏原过滤：包含用户过敏原的菜品不应出现在推荐中"""
        from app.services.recommendation_service import RecommendationService

        # 用户对海鲜和鸡蛋过敏
        create_test_user(db_session, health_goal="balanced", allergens=["海鲜", "鸡蛋"])
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch", limit=20)

        for food in result.recommendations:
            # 不应包含含海鲜或鸡蛋的菜品
            assert food.food_name not in ["白灼虾", "番茄炒蛋", "蒸蛋羹", "番茄蛋汤", "木须肉"], \
                f"过敏原过滤失败：{food.food_name} 含有用户过敏原"

    def test_allergen_filtering_english_codes(self, db_session):
        """测试过敏原过滤（英文代码）"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="balanced", allergens=["fish", "peanut"])
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch", limit=20)

        for food in result.recommendations:
            assert food.food_name not in ["清蒸鲈鱼", "香煎三文鱼", "宫保鸡丁"], \
                f"过敏原过滤失败：{food.food_name} 含有用户过敏原"

    def test_meal_type_filtering_breakfast(self, db_session):
        """测试餐次过滤：早餐应推荐早餐类菜品"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="balanced")
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="breakfast", limit=10)

        assert len(result.recommendations) > 0
        # 早餐推荐不应包含纯午晚餐菜品
        breakfast_only_names = {f.food_name for f in result.recommendations}
        # 这些菜只在lunch/dinner中
        lunch_dinner_only = {"青椒肉丝", "西红柿牛腩", "红烧牛肉", "糖醋排骨"}
        assert not breakfast_only_names & lunch_dinner_only, \
            f"早餐推荐中出现了非早餐菜品: {breakfast_only_names & lunch_dinner_only}"

    def test_meal_type_filtering_snack(self, db_session):
        """测试餐次过滤：加餐推荐"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="balanced")
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="snack", limit=10)

        assert len(result.recommendations) > 0

    def test_calorie_quota_consideration(self, db_session):
        """测试热量配额：今天已摄入很多热量时，应推荐低热量菜品"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="balanced")
        # 今天已经吃了很多高热量食物
        create_test_diet_record(db_session, calories=800, meal_type="breakfast")
        create_test_diet_record(db_session, calories=700, meal_type="lunch")

        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="dinner", limit=5)

        assert result.remaining_calories < result.daily_calorie_target
        # 推荐的菜品热量应该相对较低
        if result.remaining_calories > 0:
            avg_cal = sum(f.calories for f in result.recommendations) / len(result.recommendations)
            # 剩余配额少时，推荐的平均热量不应太高
            assert avg_cal <= 300, f"剩余热量不多时，推荐平均热量 {avg_cal} 偏高"

    def test_daily_calorie_target_calculation(self, db_session):
        """测试每日热量目标计算"""
        from app.services.recommendation_service import RecommendationService

        # 减脂用户
        create_test_user(db_session, user_id=1, health_goal="reduce_fat",
                         weight=70, height=170, age=30, gender="male")
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch")

        # BMR = 10*70 + 6.25*170 - 5*30 + 5 = 700 + 1062.5 - 150 + 5 = 1617.5
        # TDEE = 1617.5 * 1.375 = 2224.06
        # reduce_fat target = 2224.06 - 500 = 1724.06
        assert 1600 < result.daily_calorie_target < 1850

        # 增肌用户
        create_test_user(db_session, user_id=2, health_goal="gain_muscle",
                         weight=70, height=170, age=30, gender="male")
        result2 = service.get_recommendations(db_session, user_id=2, meal_type="lunch")
        # gain_muscle target = 2224.06 + 300 = 2524.06
        assert 2400 < result2.daily_calorie_target < 2650

    def test_history_preference_boost(self, db_session):
        """测试历史偏好加分：用户常吃的菜品分数应更高"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="balanced")

        # 添加多条历史记录，用户偏好番茄炒蛋
        for i in range(5):
            create_test_diet_record(
                db_session, food_name="番茄炒蛋",
                calories=150, protein=10, fat=8, carbs=6,
                record_date=date.today() - timedelta(days=i + 1)
            )

        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch", limit=20)

        # 番茄炒蛋应该在推荐列表中（如果有的话），且分数较高
        tomato_egg = [f for f in result.recommendations if f.food_name == "番茄炒蛋"]
        if tomato_egg:
            # 由于有偏好加分，分数不应过低
            assert tomato_egg[0].score >= 30, "历史偏好菜品分数过低"

    def test_today_eaten_variety(self, db_session):
        """测试多样性：今天已吃过的菜品应降分"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="balanced")
        # 今天已经吃了番茄炒蛋
        create_test_diet_record(db_session, food_name="番茄炒蛋", meal_type="lunch")

        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="dinner", limit=20)

        # 番茄炒蛋如果出现，分数应低于未吃过的菜品
        tomato_egg = [f for f in result.recommendations if f.food_name == "番茄炒蛋"]
        other_foods = [f for f in result.recommendations if f.food_name != "番茄炒蛋"]
        if tomato_egg and other_foods:
            assert tomato_egg[0].score <= other_foods[0].score, \
                "今天已吃过的菜品分数不应高于未吃过的菜品"

    def test_recommendation_has_reason(self, db_session):
        """测试每道推荐菜品都有推荐理由"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="reduce_fat")
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch", limit=5)

        for food in result.recommendations:
            assert food.reason, f"{food.food_name} 缺少推荐理由"
            assert len(food.reason) > 5, f"{food.food_name} 推荐理由过短"

    def test_recommendation_has_tags(self, db_session):
        """测试推荐菜品有标签"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="balanced")
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch", limit=10)

        # 至少部分菜品应该有标签
        foods_with_tags = [f for f in result.recommendations if len(f.tags) > 0]
        assert len(foods_with_tags) > 0, "推荐列表中没有任何菜品有标签"

    def test_score_range(self, db_session):
        """测试评分范围：所有推荐的分数应在0-100之间"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="balanced")
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch", limit=20)

        for food in result.recommendations:
            assert 0 <= food.score <= 100, f"{food.food_name} 分数 {food.score} 超出范围"

    def test_user_not_found(self, db_session):
        """测试用户不存在时抛出异常"""
        from app.services.recommendation_service import RecommendationService

        service = RecommendationService()
        with pytest.raises(ValueError, match="用户不存在"):
            service.get_recommendations(db_session, user_id=9999, meal_type="lunch")

    def test_limit_parameter(self, db_session):
        """测试limit参数控制返回数量"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="balanced")
        service = RecommendationService()

        result3 = service.get_recommendations(db_session, user_id=1, meal_type="lunch", limit=3)
        assert len(result3.recommendations) <= 3

        result1 = service.get_recommendations(db_session, user_id=1, meal_type="lunch", limit=1)
        assert len(result1.recommendations) == 1

    def test_chinese_meal_type(self, db_session):
        """测试中文餐次参数"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="balanced")
        service = RecommendationService()

        result = service.get_recommendations(db_session, user_id=1, meal_type="午餐", limit=5)
        assert result.meal_type == "lunch"
        assert len(result.recommendations) > 0

    def test_female_user_calorie_target(self, db_session):
        """测试女性用户热量目标计算"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="reduce_fat",
                         weight=55, height=160, age=25, gender="female")
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch")

        # 女性 BMR = 10*55 + 6.25*160 - 5*25 - 161 = 550 + 1000 - 125 - 161 = 1264
        # TDEE = 1264 * 1.375 = 1738
        # reduce_fat = 1738 - 500 = 1238
        assert 1100 < result.daily_calorie_target < 1400

    def test_multiple_allergens(self, db_session):
        """测试多种过敏原同时过滤"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="balanced",
                         allergens=["海鲜", "鸡蛋", "花生", "大豆"])
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch", limit=20)

        # 所有推荐都不应含这些过敏原
        for food in result.recommendations:
            # 清蒸鲈鱼(fish相关但不是shellfish), 蒸蛋羹(egg), 宫保鸡丁(peanut+soy) 都不应出现
            forbidden = {"白灼虾", "蒸蛋羹", "番茄炒蛋", "宫保鸡丁", "家常豆腐",
                         "红烧牛肉", "牛肉面", "鸡蛋灌饼", "木须肉", "番茄蛋汤",
                         "豆浆"}
            assert food.food_name not in forbidden, \
                f"多过敏原过滤失败：{food.food_name}"

    def test_default_body_params(self, db_session):
        """测试用户缺少身体参数时使用默认值"""
        from app.services.recommendation_service import RecommendationService

        # 创建没有身体参数的用户
        user = User(
            id=1, nickname="no_params", password="test",
            health_goal="balanced",
        )
        db_session.add(user)
        db_session.commit()

        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch")

        # 应该能正常返回结果
        assert result is not None
        assert result.daily_calorie_target > 0
        assert len(result.recommendations) > 0

    def test_remaining_calories_when_over_quota(self, db_session):
        """测试超配额时剩余热量为0"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="reduce_fat")
        # 大量进食超过配额
        create_test_diet_record(db_session, calories=1000, meal_type="breakfast")
        create_test_diet_record(db_session, calories=1000, meal_type="lunch")
        create_test_diet_record(db_session, calories=1000, meal_type="snack")

        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="dinner")

        assert result.remaining_calories == 0.0
        # 超配额时仍然应该返回推荐（低热量菜品）
        assert len(result.recommendations) > 0

    def test_recommendations_sorted_by_score(self, db_session):
        """测试推荐列表按分数降序排列"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="balanced")
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch", limit=10)

        scores = [f.score for f in result.recommendations]
        assert scores == sorted(scores, reverse=True), "推荐列表未按分数降序排列"


# ============================================================
# 2. Pydantic 模型测试
# ============================================================
class TestPydanticModels:
    """Pydantic模型验证测试"""

    def test_recommended_food_model(self):
        """测试 RecommendedFood 模型"""
        from app.models.food import RecommendedFood

        food = RecommendedFood(
            food_name="清蒸鲈鱼",
            calories=105.0,
            protein=19.5,
            fat=3.0,
            carbs=0.5,
            score=92.5,
            reason="高蛋白低脂肪，适合减脂",
            tags=["高蛋白", "低脂肪"],
        )
        assert food.food_name == "清蒸鲈鱼"
        assert food.score == 92.5
        assert "高蛋白" in food.tags

    def test_recommendation_data_model(self):
        """测试 RecommendationData 模型"""
        from app.models.food import RecommendationData, RecommendedFood

        data = RecommendationData(
            user_id=1,
            meal_type="lunch",
            remaining_calories=800.0,
            daily_calorie_target=2000.0,
            health_goal="reduce_fat",
            health_goal_label="减脂",
            recommendations=[
                RecommendedFood(
                    food_name="清蒸鲈鱼",
                    calories=105.0,
                    protein=19.5,
                    fat=3.0,
                    carbs=0.5,
                    score=92.5,
                    reason="适合减脂",
                    tags=["高蛋白"],
                )
            ],
        )
        assert data.user_id == 1
        assert len(data.recommendations) == 1

    def test_recommendation_response_model(self):
        """测试 RecommendationResponse 模型"""
        from app.models.food import RecommendationResponse

        resp = RecommendationResponse(
            code=200,
            message="推荐成功",
            data=None,
        )
        assert resp.code == 200


# ============================================================
# 3. API 接口集成测试
# ============================================================
class TestRecommendationAPI:
    """API接口测试（使用 FastAPI TestClient）"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.database import get_db

        # 覆盖数据库依赖
        app.dependency_overrides[get_db] = get_test_db
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    def test_recommend_endpoint_success(self, client, db_session):
        """测试推荐接口正常返回"""
        create_test_user(db_session, health_goal="reduce_fat")

        response = client.get("/api/food/recommend", params={
            "user_id": 1,
            "meal_type": "lunch",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "推荐成功"
        assert data["data"]["user_id"] == 1
        assert data["data"]["meal_type"] == "lunch"
        assert len(data["data"]["recommendations"]) > 0

    def test_recommend_endpoint_with_limit(self, client, db_session):
        """测试推荐接口limit参数"""
        create_test_user(db_session, health_goal="balanced")

        response = client.get("/api/food/recommend", params={
            "user_id": 1,
            "meal_type": "lunch",
            "limit": 3,
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["recommendations"]) <= 3

    def test_recommend_endpoint_user_not_found(self, client):
        """测试推荐接口用户不存在"""
        response = client.get("/api/food/recommend", params={
            "user_id": 9999,
            "meal_type": "lunch",
        })
        assert response.status_code == 404

    def test_recommend_endpoint_missing_user_id(self, client):
        """测试推荐接口缺少user_id参数"""
        response = client.get("/api/food/recommend", params={
            "meal_type": "lunch",
        })
        assert response.status_code == 422

    def test_recommend_endpoint_default_meal_type(self, client, db_session):
        """测试推荐接口默认餐次"""
        create_test_user(db_session, health_goal="balanced")

        response = client.get("/api/food/recommend", params={
            "user_id": 1,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["meal_type"] == "lunch"  # 默认午餐

    def test_recommend_endpoint_breakfast(self, client, db_session):
        """测试早餐推荐接口"""
        create_test_user(db_session, health_goal="balanced")

        response = client.get("/api/food/recommend", params={
            "user_id": 1,
            "meal_type": "breakfast",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["meal_type"] == "breakfast"
        assert len(data["data"]["recommendations"]) > 0

    def test_recommend_endpoint_response_structure(self, client, db_session):
        """测试推荐接口响应结构完整性"""
        create_test_user(db_session, health_goal="reduce_fat")

        response = client.get("/api/food/recommend", params={
            "user_id": 1,
            "meal_type": "lunch",
        })
        data = response.json()

        # 检查顶层结构
        assert "code" in data
        assert "message" in data
        assert "data" in data

        # 检查 data 结构
        result = data["data"]
        assert "user_id" in result
        assert "meal_type" in result
        assert "remaining_calories" in result
        assert "daily_calorie_target" in result
        assert "health_goal" in result
        assert "health_goal_label" in result
        assert "recommendations" in result

        # 检查推荐菜品结构
        if result["recommendations"]:
            food = result["recommendations"][0]
            assert "food_name" in food
            assert "calories" in food
            assert "protein" in food
            assert "fat" in food
            assert "carbs" in food
            assert "score" in food
            assert "reason" in food
            assert "tags" in food

    def test_recommend_with_allergens(self, client, db_session):
        """测试带过敏原的推荐接口"""
        create_test_user(db_session, health_goal="balanced", allergens=["鸡蛋", "海鲜"])

        response = client.get("/api/food/recommend", params={
            "user_id": 1,
            "meal_type": "lunch",
        })
        assert response.status_code == 200
        data = response.json()

        # 推荐列表不应包含含鸡蛋和海鲜的菜品
        for food in data["data"]["recommendations"]:
            assert food["food_name"] not in ["番茄炒蛋", "白灼虾", "蒸蛋羹"], \
                f"API返回了含过敏原的菜品: {food['food_name']}"


# ============================================================
# 4. 内部方法单元测试
# ============================================================
class TestInternalMethods:
    """内部方法测试"""

    def test_normalize_allergens_chinese(self):
        """测试中文过敏原规范化"""
        from app.services.recommendation_service import RecommendationService

        service = RecommendationService()
        result = service._normalize_allergens(["海鲜", "鸡蛋", "花生"])
        assert "shellfish" in result
        assert "egg" in result
        assert "peanut" in result

    def test_normalize_allergens_english(self):
        """测试英文过敏原规范化"""
        from app.services.recommendation_service import RecommendationService

        service = RecommendationService()
        result = service._normalize_allergens(["fish", "milk", "wheat"])
        assert "fish" in result
        assert "milk" in result
        assert "wheat" in result

    def test_normalize_allergens_mixed(self):
        """测试中英文混合过敏原规范化"""
        from app.services.recommendation_service import RecommendationService

        service = RecommendationService()
        result = service._normalize_allergens(["海鲜", "milk", "花生"])
        assert "shellfish" in result
        assert "milk" in result
        assert "peanut" in result

    def test_normalize_allergens_empty(self):
        """测试空过敏原列表"""
        from app.services.recommendation_service import RecommendationService

        service = RecommendationService()
        result = service._normalize_allergens([])
        assert len(result) == 0

    def test_generate_tags_low_cal(self):
        """测试低热量标签生成"""
        from app.services.recommendation_service import RecommendationService

        service = RecommendationService()
        tags = service._generate_tags({"calories": 50, "protein": 3, "fat": 1, "carbs": 8})
        assert "低热量" in tags

    def test_generate_tags_high_protein(self):
        """测试高蛋白标签生成"""
        from app.services.recommendation_service import RecommendationService

        service = RecommendationService()
        tags = service._generate_tags({"calories": 200, "protein": 25, "fat": 5, "carbs": 10})
        assert "高蛋白" in tags

    def test_generate_tags_low_carbs(self):
        """测试低碳水标签生成"""
        from app.services.recommendation_service import RecommendationService

        service = RecommendationService()
        tags = service._generate_tags({"calories": 150, "protein": 20, "fat": 8, "carbs": 2})
        assert "低碳水" in tags

    def test_score_health_goal_reduce_fat(self):
        """测试减脂目标评分"""
        from app.services.recommendation_service import RecommendationService

        service = RecommendationService()
        # 低热量高蛋白食物应得高分
        low_cal_food = {"calories": 80, "protein": 18, "fat": 2, "carbs": 1}
        high_cal_food = {"calories": 400, "protein": 5, "fat": 30, "carbs": 40}

        score_low = service._score_health_goal(low_cal_food, "reduce_fat")
        score_high = service._score_health_goal(high_cal_food, "reduce_fat")
        assert score_low > score_high, "减脂目标下低热量高蛋白食物分数应更高"

    def test_score_health_goal_gain_muscle(self):
        """测试增肌目标评分"""
        from app.services.recommendation_service import RecommendationService

        service = RecommendationService()
        high_prot = {"calories": 250, "protein": 28, "fat": 10, "carbs": 5}
        low_prot = {"calories": 100, "protein": 3, "fat": 1, "carbs": 20}

        score_high = service._score_health_goal(high_prot, "gain_muscle")
        score_low = service._score_health_goal(low_prot, "gain_muscle")
        assert score_high > score_low, "增肌目标下高蛋白食物分数应更高"

    def test_score_calorie_fit_within_quota(self):
        """测试热量配额内的评分"""
        from app.services.recommendation_service import RecommendationService

        service = RecommendationService()
        food = {"calories": 200}
        # 剩余1000kcal，200kcal食物在理想范围内(100-500)
        score = service._score_calorie_fit(food, 1000)
        assert score >= 20, f"在配额内的食物分数 {score} 过低"

    def test_score_calorie_fit_over_quota(self):
        """测试超配额热量评分"""
        from app.services.recommendation_service import RecommendationService

        service = RecommendationService()
        food = {"calories": 500}
        # 剩余200kcal，500kcal食物超出很多
        score = service._score_calorie_fit(food, 200)
        assert score < 20, f"超出配额的食物分数 {score} 过高"

    def test_generate_reason_non_empty(self):
        """测试推荐理由生成非空"""
        from app.services.recommendation_service import RecommendationService

        service = RecommendationService()
        food = {"calories": 100, "protein": 18, "fat": 2, "carbs": 1, "food_name": "测试"}
        reason = service._generate_reason(food, "reduce_fat", 800.0, ["高蛋白", "低脂肪"], False)
        assert len(reason) > 0


# ============================================================
# 5. 边缘情况测试
# ============================================================
class TestEdgeCases:
    """边缘情况测试"""

    def test_all_foods_filtered_by_allergens(self, db_session):
        """测试所有菜品都被过敏原过滤的情况"""
        from app.services.recommendation_service import RecommendationService

        # 对几乎所有食材过敏
        create_test_user(db_session, health_goal="balanced",
                         allergens=["海鲜", "鸡蛋", "花生", "大豆", "乳制品",
                                    "鱼类", "坚果", "小麦"])
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch")

        # 应该返回空列表或仅有少量无过敏原菜品
        assert result is not None
        # 有些蔬菜和肉类不含八大过敏原
        for food in result.recommendations:
            assert food is not None  # 不应崩溃

    def test_zero_limit(self, db_session):
        """测试limit=0"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="balanced")
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch", limit=0)
        assert len(result.recommendations) == 0

    def test_very_large_limit(self, db_session):
        """测试很大的limit值"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="balanced")
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch", limit=1000)
        # 不应崩溃，返回数量不超过菜品库大小
        assert result is not None
        assert len(result.recommendations) <= 1000

    def test_no_diet_records(self, db_session):
        """测试用户没有任何饮食记录时的推荐"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="reduce_fat")
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="lunch")

        # 没有记录时，剩余配额等于每日目标
        assert result.remaining_calories == result.daily_calorie_target
        assert len(result.recommendations) > 0

    def test_invalid_meal_type_returns_empty(self, db_session):
        """测试无效餐次类型"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="balanced")
        service = RecommendationService()
        result = service.get_recommendations(db_session, user_id=1, meal_type="midnight_snack")

        # 无效餐次应该返回空推荐（没有菜品匹配）
        assert result is not None
        assert len(result.recommendations) == 0

    def test_concurrent_recommendations(self, db_session):
        """测试同一用户多次调用推荐一致性"""
        from app.services.recommendation_service import RecommendationService

        create_test_user(db_session, health_goal="reduce_fat")
        service = RecommendationService()

        result1 = service.get_recommendations(db_session, user_id=1, meal_type="lunch", limit=5)
        result2 = service.get_recommendations(db_session, user_id=1, meal_type="lunch", limit=5)

        # 同一状态下两次调用结果应一致
        names1 = [f.food_name for f in result1.recommendations]
        names2 = [f.food_name for f in result2.recommendations]
        assert names1 == names2, "相同条件下两次推荐结果不一致"


# ============================================================
# 清理测试数据库文件
# ============================================================
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    """测试会话结束后清理测试数据库文件"""
    yield
    test_db_path = "./test_phase41.db"
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
