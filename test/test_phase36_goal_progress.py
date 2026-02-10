"""
Phase 36 测试文件: 健康目标达成率功能测试

测试策略：
1. 直接测试服务层逻辑（避免异步HTTP测试的复杂性）
2. 使用内存SQLite数据库进行隔离测试
3. 覆盖所有健康目标类型和边界条件

测试场景：
- reduce_fat（减脂）目标的达成率计算
- gain_muscle（增肌）目标的达成率计算
- control_sugar（控糖）目标的达成率计算
- balanced（均衡）目标的达成率计算
- 无健康目标用户
- 无数据用户
- 边界条件（零数据、大数据、非法输入等）
- 连续记录天数统计
- 多日期范围测试
- Pydantic模型验证
"""
import pytest
import sys
import os
from datetime import date, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.db_models.user import User
from app.db_models.diet_record import DietRecord
from app.db_models.trip_plan import TripPlan
from app.db_models.trip_item import TripItem
from app.db_models.exercise_record import ExerciseRecord
from app.services.stats_service import StatsService
from app.models.stats import (
    GoalProgressData,
    GoalDimension,
    GoalProgressResponse,
    HEALTH_GOAL_LABELS,
)


# ==================== 测试数据库配置 ====================

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建统计服务实例
stats_service = StatsService()


# ==================== Fixtures ====================

@pytest.fixture(autouse=True)
def setup_database():
    """每个测试前创建表，测试后删除表"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """获取数据库会话"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def reduce_fat_user(db_session):
    """创建减脂目标用户"""
    user = User(
        id=1,
        nickname="减脂用户",
        password="test_password",
        health_goal="reduce_fat",
        weight=80.0,
        height=175.0,
        age=30,
        gender="male"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def gain_muscle_user(db_session):
    """创建增肌目标用户"""
    user = User(
        id=2,
        nickname="增肌用户",
        password="test_password",
        health_goal="gain_muscle",
        weight=65.0,
        height=170.0,
        age=25,
        gender="male"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def control_sugar_user(db_session):
    """创建控糖目标用户"""
    user = User(
        id=3,
        nickname="控糖用户",
        password="test_password",
        health_goal="control_sugar",
        weight=70.0,
        height=165.0,
        age=45,
        gender="female"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def balanced_user(db_session):
    """创建均衡目标用户"""
    user = User(
        id=4,
        nickname="均衡用户",
        password="test_password",
        health_goal="balanced",
        weight=60.0,
        height=160.0,
        age=28,
        gender="female"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def no_goal_user(db_session):
    """创建无健康目标用户"""
    user = User(
        id=5,
        nickname="普通用户",
        password="test_password",
        health_goal=None,
        weight=70.0,
        height=170.0,
        age=30,
        gender="male"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_diet_records_for_days(db_session, user_id, days_back=7, 
                                   daily_calories=1800.0, protein=60.0, 
                                   fat=60.0, carbs=240.0):
    """辅助函数：创建多天饮食记录"""
    today = date.today()
    records = []
    for i in range(days_back):
        record_date = today - timedelta(days=i)
        record = DietRecord(
            user_id=user_id,
            food_name=f"Day{i}_meal",
            calories=daily_calories,
            protein=protein,
            fat=fat,
            carbs=carbs,
            meal_type="lunch",
            record_date=record_date
        )
        db_session.add(record)
        records.append(record)
    db_session.commit()
    return records


def _create_exercise_records_for_days(db_session, user_id, days_back=7,
                                       daily_calories=300.0, duration=30):
    """辅助函数：创建多天运动记录"""
    today = date.today()
    records = []
    for i in range(days_back):
        record_date = today - timedelta(days=i)
        record = ExerciseRecord(
            user_id=user_id,
            exercise_type="running",
            actual_calories=daily_calories,
            actual_duration=duration,
            exercise_date=record_date,
        )
        db_session.add(record)
        records.append(record)
    db_session.commit()
    return records


def _create_trip_plans_for_days(db_session, user_id, days_back=7,
                                 planned_calories=350.0, duration=40):
    """辅助函数：创建多天运动计划"""
    today = date.today()
    plans = []
    for i in range(days_back):
        plan_date = today - timedelta(days=i)
        trip = TripPlan(
            user_id=user_id,
            title=f"Day{i}_plan",
            destination="公园",
            start_date=plan_date,
            end_date=plan_date,
            status="done"
        )
        db_session.add(trip)
        db_session.commit()

        item = TripItem(
            trip_id=trip.id,
            day_index=1,
            place_name="跑步",
            place_type="running",
            duration=duration,
            cost=planned_calories
        )
        db_session.add(item)
        plans.append(trip)
    db_session.commit()
    return plans


# ==================== Pydantic模型测试 ====================

class TestGoalProgressModels:
    """健康目标达成率Pydantic模型测试"""

    def test_goal_dimension_creation(self):
        """测试GoalDimension模型创建"""
        dim = GoalDimension(
            name="热量控制",
            score=85.0,
            status="good",
            current_value=1800.0,
            target_value=2000.0,
            unit="kcal",
            description="日均摄入热量在合理范围内"
        )
        assert dim.name == "热量控制"
        assert dim.score == 85.0
        assert dim.status == "good"
        print("✓ GoalDimension模型创建测试通过")

    def test_goal_progress_data_creation(self):
        """测试GoalProgressData模型创建"""
        dim = GoalDimension(
            name="热量控制", score=80.0, status="good",
            current_value=1800.0, target_value=2000.0,
            unit="kcal", description="合理"
        )
        data = GoalProgressData(
            user_id=1,
            health_goal="reduce_fat",
            health_goal_label="减脂",
            period_days=7,
            start_date="2026-02-01",
            end_date="2026-02-07",
            overall_score=75.0,
            overall_status="good",
            dimensions=[dim],
            suggestions=["继续保持"],
            streak_days=5
        )
        assert data.user_id == 1
        assert data.health_goal == "reduce_fat"
        assert data.overall_score == 75.0
        assert len(data.dimensions) == 1
        assert len(data.suggestions) == 1
        assert data.streak_days == 5
        print("✓ GoalProgressData模型创建测试通过")

    def test_goal_progress_response_creation(self):
        """测试GoalProgressResponse模型创建"""
        dim = GoalDimension(
            name="热量控制", score=80.0, status="good",
            current_value=1800.0, target_value=2000.0,
            unit="kcal", description="合理"
        )
        data = GoalProgressData(
            user_id=1, health_goal="reduce_fat", health_goal_label="减脂",
            period_days=7, start_date="2026-02-01", end_date="2026-02-07",
            overall_score=75.0, overall_status="good",
            dimensions=[dim], suggestions=["继续保持"], streak_days=5
        )
        response = GoalProgressResponse(
            code=200, message="获取成功", data=data
        )
        assert response.code == 200
        assert response.data.overall_score == 75.0
        print("✓ GoalProgressResponse模型创建测试通过")

    def test_health_goal_labels_exist(self):
        """测试健康目标标签常量存在"""
        assert "reduce_fat" in HEALTH_GOAL_LABELS
        assert "gain_muscle" in HEALTH_GOAL_LABELS
        assert "control_sugar" in HEALTH_GOAL_LABELS
        assert "balanced" in HEALTH_GOAL_LABELS
        print("✓ 健康目标标签常量测试通过")

    def test_overall_status_values(self):
        """测试overall_status允许的值"""
        for status in ["excellent", "good", "fair", "poor"]:
            dim = GoalDimension(
                name="test", score=50.0, status=status,
                current_value=0, target_value=100, unit="", description=""
            )
            assert dim.status == status
        print("✓ 状态值测试通过")


# ==================== 减脂目标测试 ====================

class TestReduceFatGoal:
    """减脂目标达成率测试"""

    def test_reduce_fat_with_calorie_deficit(self, db_session, reduce_fat_user):
        """测试减脂用户有热量缺口的情况（理想状态）"""
        # 创建7天的饮食记录 - 低热量饮食
        _create_diet_records_for_days(
            db_session, reduce_fat_user.id, days_back=7,
            daily_calories=1600.0, protein=80.0, fat=40.0, carbs=200.0
        )
        # 创建运动记录
        _create_exercise_records_for_days(
            db_session, reduce_fat_user.id, days_back=7,
            daily_calories=400.0, duration=45
        )

        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=7
        )

        assert result.health_goal == "reduce_fat"
        assert result.health_goal_label == "减脂"
        assert result.overall_score >= 0.0
        assert result.overall_score <= 100.0
        assert result.overall_status in ["excellent", "good", "fair", "poor"]
        assert len(result.dimensions) > 0
        assert result.period_days == 7
        # 有热量缺口，减脂分数应该不错
        assert result.overall_score >= 50.0
        print(f"✓ 减脂+热量缺口测试通过: overall_score={result.overall_score}")

    def test_reduce_fat_with_calorie_surplus(self, db_session, reduce_fat_user):
        """测试减脂用户热量过剩的情况（不理想）"""
        # 高热量饮食、不运动
        _create_diet_records_for_days(
            db_session, reduce_fat_user.id, days_back=7,
            daily_calories=3000.0, protein=60.0, fat=120.0, carbs=400.0
        )

        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=7
        )

        assert result.health_goal == "reduce_fat"
        # 高热量且无运动，分数应该较低
        assert result.overall_score < 80.0
        assert len(result.suggestions) > 0
        print(f"✓ 减脂+热量过剩测试通过: overall_score={result.overall_score}")

    def test_reduce_fat_dimension_names(self, db_session, reduce_fat_user):
        """测试减脂目标的维度名称"""
        _create_diet_records_for_days(db_session, reduce_fat_user.id, days_back=3)
        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=3
        )
        dim_names = [d.name for d in result.dimensions]
        # 减脂应包含：热量控制、脂肪比例、运动消耗
        assert "热量控制" in dim_names
        assert "脂肪比例" in dim_names
        assert "运动消耗" in dim_names
        print(f"✓ 减脂维度名称测试通过: {dim_names}")


# ==================== 增肌目标测试 ====================

class TestGainMuscleGoal:
    """增肌目标达成率测试"""

    def test_gain_muscle_high_protein(self, db_session, gain_muscle_user):
        """测试增肌用户高蛋白饮食"""
        # 高蛋白饮食
        _create_diet_records_for_days(
            db_session, gain_muscle_user.id, days_back=7,
            daily_calories=2500.0, protein=150.0, fat=70.0, carbs=280.0
        )
        _create_exercise_records_for_days(
            db_session, gain_muscle_user.id, days_back=7,
            daily_calories=500.0, duration=60
        )

        result = stats_service.get_goal_progress(
            db_session, gain_muscle_user.id, days=7
        )

        assert result.health_goal == "gain_muscle"
        assert result.health_goal_label == "增肌"
        assert result.overall_score >= 0.0
        assert result.overall_score <= 100.0
        assert len(result.dimensions) > 0
        print(f"✓ 增肌+高蛋白测试通过: overall_score={result.overall_score}")

    def test_gain_muscle_low_protein(self, db_session, gain_muscle_user):
        """测试增肌用户低蛋白饮食（不理想）"""
        _create_diet_records_for_days(
            db_session, gain_muscle_user.id, days_back=7,
            daily_calories=1500.0, protein=30.0, fat=40.0, carbs=250.0
        )

        result = stats_service.get_goal_progress(
            db_session, gain_muscle_user.id, days=7
        )

        assert result.health_goal == "gain_muscle"
        # 低蛋白不利于增肌，分数应该较低
        assert len(result.suggestions) > 0
        print(f"✓ 增肌+低蛋白测试通过: overall_score={result.overall_score}")

    def test_gain_muscle_dimension_names(self, db_session, gain_muscle_user):
        """测试增肌目标的维度名称"""
        _create_diet_records_for_days(db_session, gain_muscle_user.id, days_back=3)
        result = stats_service.get_goal_progress(
            db_session, gain_muscle_user.id, days=3
        )
        dim_names = [d.name for d in result.dimensions]
        assert "蛋白质摄入" in dim_names
        assert "运动消耗" in dim_names
        print(f"✓ 增肌维度名称测试通过: {dim_names}")


# ==================== 控糖目标测试 ====================

class TestControlSugarGoal:
    """控糖目标达成率测试"""

    def test_control_sugar_low_carbs(self, db_session, control_sugar_user):
        """测试控糖用户低碳水饮食"""
        _create_diet_records_for_days(
            db_session, control_sugar_user.id, days_back=7,
            daily_calories=1800.0, protein=80.0, fat=70.0, carbs=150.0
        )

        result = stats_service.get_goal_progress(
            db_session, control_sugar_user.id, days=7
        )

        assert result.health_goal == "control_sugar"
        assert result.health_goal_label == "控糖"
        assert result.overall_score >= 0.0
        assert result.overall_score <= 100.0
        print(f"✓ 控糖+低碳水测试通过: overall_score={result.overall_score}")

    def test_control_sugar_high_carbs(self, db_session, control_sugar_user):
        """测试控糖用户高碳水饮食（不理想）"""
        _create_diet_records_for_days(
            db_session, control_sugar_user.id, days_back=7,
            daily_calories=2500.0, protein=50.0, fat=40.0, carbs=450.0
        )

        result = stats_service.get_goal_progress(
            db_session, control_sugar_user.id, days=7
        )

        assert result.health_goal == "control_sugar"
        assert len(result.suggestions) > 0
        print(f"✓ 控糖+高碳水测试通过: overall_score={result.overall_score}")

    def test_control_sugar_dimension_names(self, db_session, control_sugar_user):
        """测试控糖目标的维度名称"""
        _create_diet_records_for_days(db_session, control_sugar_user.id, days_back=3)
        result = stats_service.get_goal_progress(
            db_session, control_sugar_user.id, days=3
        )
        dim_names = [d.name for d in result.dimensions]
        assert "碳水比例" in dim_names
        print(f"✓ 控糖维度名称测试通过: {dim_names}")


# ==================== 均衡目标测试 ====================

class TestBalancedGoal:
    """均衡目标达成率测试"""

    def test_balanced_ideal(self, db_session, balanced_user):
        """测试均衡用户理想饮食"""
        # 均衡饮食：蛋白质12.5%, 脂肪25%, 碳水62.5%
        _create_diet_records_for_days(
            db_session, balanced_user.id, days_back=7,
            daily_calories=2000.0, protein=62.5, fat=55.6, carbs=312.5
        )
        _create_exercise_records_for_days(
            db_session, balanced_user.id, days_back=7,
            daily_calories=300.0, duration=30
        )

        result = stats_service.get_goal_progress(
            db_session, balanced_user.id, days=7
        )

        assert result.health_goal == "balanced"
        assert result.health_goal_label == "均衡"
        assert result.overall_score >= 0.0
        assert result.overall_score <= 100.0
        print(f"✓ 均衡+理想饮食测试通过: overall_score={result.overall_score}")

    def test_balanced_dimension_names(self, db_session, balanced_user):
        """测试均衡目标的维度名称"""
        _create_diet_records_for_days(db_session, balanced_user.id, days_back=3)
        result = stats_service.get_goal_progress(
            db_session, balanced_user.id, days=3
        )
        dim_names = [d.name for d in result.dimensions]
        assert "营养均衡" in dim_names
        assert "运动规律" in dim_names
        print(f"✓ 均衡维度名称测试通过: {dim_names}")


# ==================== 无目标用户测试 ====================

class TestNoGoalUser:
    """无健康目标用户测试"""

    def test_no_goal_defaults_to_balanced(self, db_session, no_goal_user):
        """测试无健康目标用户默认使用balanced"""
        _create_diet_records_for_days(db_session, no_goal_user.id, days_back=3)
        result = stats_service.get_goal_progress(
            db_session, no_goal_user.id, days=3
        )
        # 无目标时默认使用balanced
        assert result.health_goal == "balanced"
        assert result.overall_score >= 0.0
        print(f"✓ 无目标用户默认balanced测试通过: overall_score={result.overall_score}")


# ==================== 边界条件测试 ====================

class TestBoundaryConditions:
    """边界条件测试"""

    def test_no_data_user(self, db_session, reduce_fat_user):
        """测试没有任何数据的用户"""
        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=7
        )

        assert result.user_id == reduce_fat_user.id
        assert result.overall_score >= 0.0
        assert result.overall_score <= 100.0
        assert result.streak_days == 0
        print(f"✓ 无数据用户测试通过: overall_score={result.overall_score}")

    def test_single_day(self, db_session, reduce_fat_user):
        """测试单日数据"""
        _create_diet_records_for_days(
            db_session, reduce_fat_user.id, days_back=1,
            daily_calories=1800.0
        )
        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=1
        )

        assert result.period_days == 1
        assert result.overall_score >= 0.0
        print(f"✓ 单日数据测试通过: overall_score={result.overall_score}")

    def test_large_period(self, db_session, reduce_fat_user):
        """测试30天长周期"""
        _create_diet_records_for_days(
            db_session, reduce_fat_user.id, days_back=30,
            daily_calories=1800.0, protein=60.0, fat=50.0, carbs=250.0
        )
        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=30
        )

        assert result.period_days == 30
        assert result.overall_score >= 0.0
        print(f"✓ 30天长周期测试通过: overall_score={result.overall_score}")

    def test_zero_calorie_records(self, db_session, reduce_fat_user):
        """测试零热量记录"""
        _create_diet_records_for_days(
            db_session, reduce_fat_user.id, days_back=3,
            daily_calories=0.0, protein=0.0, fat=0.0, carbs=0.0
        )
        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=3
        )

        assert result.overall_score >= 0.0
        assert result.overall_score <= 100.0
        print(f"✓ 零热量记录测试通过: overall_score={result.overall_score}")

    def test_very_high_calories(self, db_session, reduce_fat_user):
        """测试极高热量"""
        _create_diet_records_for_days(
            db_session, reduce_fat_user.id, days_back=3,
            daily_calories=10000.0, protein=200.0, fat=500.0, carbs=1000.0
        )
        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=3
        )

        assert result.overall_score >= 0.0
        assert result.overall_score <= 100.0
        print(f"✓ 极高热量测试通过: overall_score={result.overall_score}")

    def test_only_exercise_no_diet(self, db_session, reduce_fat_user):
        """测试只有运动没有饮食记录"""
        _create_exercise_records_for_days(
            db_session, reduce_fat_user.id, days_back=5,
            daily_calories=400.0
        )
        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=5
        )

        assert result.overall_score >= 0.0
        assert result.overall_score <= 100.0
        print(f"✓ 只有运动无饮食测试通过: overall_score={result.overall_score}")

    def test_only_diet_no_exercise(self, db_session, reduce_fat_user):
        """测试只有饮食没有运动记录"""
        _create_diet_records_for_days(
            db_session, reduce_fat_user.id, days_back=5,
            daily_calories=1800.0
        )
        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=5
        )

        assert result.overall_score >= 0.0
        assert result.overall_score <= 100.0
        print(f"✓ 只有饮食无运动测试通过: overall_score={result.overall_score}")


# ==================== 连续记录天数测试 ====================

class TestStreakDays:
    """连续记录天数测试"""

    def test_consecutive_days(self, db_session, reduce_fat_user):
        """测试连续7天记录"""
        _create_diet_records_for_days(
            db_session, reduce_fat_user.id, days_back=7
        )
        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=7
        )
        assert result.streak_days == 7
        print(f"✓ 连续7天记录测试通过: streak_days={result.streak_days}")

    def test_gap_in_records(self, db_session, reduce_fat_user):
        """测试记录中有间隔（不连续）"""
        today = date.today()
        # 今天和昨天有记录，前天没有，大前天有
        for day_offset in [0, 1, 3]:
            record = DietRecord(
                user_id=reduce_fat_user.id,
                food_name=f"meal_day{day_offset}",
                calories=1800.0,
                protein=60.0, fat=50.0, carbs=250.0,
                meal_type="lunch",
                record_date=today - timedelta(days=day_offset)
            )
            db_session.add(record)
        db_session.commit()

        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=7
        )
        # 从今天往前连续的天数应为2（今天和昨天）
        assert result.streak_days == 2
        print(f"✓ 记录间隔测试通过: streak_days={result.streak_days}")

    def test_no_records_zero_streak(self, db_session, reduce_fat_user):
        """测试无记录时streak为0"""
        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=7
        )
        assert result.streak_days == 0
        print(f"✓ 无记录streak=0测试通过")


# ==================== 日期范围测试 ====================

class TestDateRange:
    """日期范围测试"""

    def test_date_range_correct(self, db_session, reduce_fat_user):
        """测试返回的日期范围正确"""
        today = date.today()
        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=7
        )
        expected_start = (today - timedelta(days=6)).isoformat()
        expected_end = today.isoformat()
        assert result.start_date == expected_start
        assert result.end_date == expected_end
        print(f"✓ 日期范围正确测试通过: {result.start_date} ~ {result.end_date}")

    def test_single_day_date_range(self, db_session, reduce_fat_user):
        """测试单日的日期范围"""
        today = date.today()
        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=1
        )
        assert result.start_date == today.isoformat()
        assert result.end_date == today.isoformat()
        print(f"✓ 单日日期范围测试通过")


# ==================== 建议生成测试 ====================

class TestSuggestions:
    """建议生成测试"""

    def test_suggestions_not_empty_with_data(self, db_session, reduce_fat_user):
        """测试有数据时建议非空"""
        _create_diet_records_for_days(
            db_session, reduce_fat_user.id, days_back=7,
            daily_calories=3000.0  # 高热量
        )
        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=7
        )
        assert len(result.suggestions) > 0
        assert all(isinstance(s, str) for s in result.suggestions)
        print(f"✓ 建议生成测试通过: {len(result.suggestions)}条建议")

    def test_suggestions_are_strings(self, db_session, reduce_fat_user):
        """测试建议都是字符串"""
        _create_diet_records_for_days(db_session, reduce_fat_user.id, days_back=3)
        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=3
        )
        for suggestion in result.suggestions:
            assert isinstance(suggestion, str)
            assert len(suggestion) > 0
        print(f"✓ 建议字符串测试通过")


# ==================== 分数范围测试 ====================

class TestScoreRanges:
    """分数范围测试"""

    def test_all_scores_in_range(self, db_session, reduce_fat_user):
        """测试所有分数在0-100范围内"""
        _create_diet_records_for_days(
            db_session, reduce_fat_user.id, days_back=7,
            daily_calories=1800.0, protein=60.0, fat=50.0, carbs=250.0
        )
        _create_exercise_records_for_days(
            db_session, reduce_fat_user.id, days_back=7
        )

        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=7
        )

        assert 0.0 <= result.overall_score <= 100.0
        for dim in result.dimensions:
            assert 0.0 <= dim.score <= 100.0, \
                f"维度'{dim.name}'分数{dim.score}超出0-100范围"
        print(f"✓ 所有分数范围测试通过")

    def test_dimension_statuses(self, db_session, reduce_fat_user):
        """测试维度状态值都合法"""
        _create_diet_records_for_days(db_session, reduce_fat_user.id, days_back=5)
        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=5
        )
        valid_statuses = {"excellent", "good", "fair", "poor"}
        assert result.overall_status in valid_statuses
        for dim in result.dimensions:
            assert dim.status in valid_statuses, \
                f"维度'{dim.name}'状态'{dim.status}'不在合法值中"
        print(f"✓ 维度状态值测试通过")


# ==================== 不同用户隔离测试 ====================

class TestUserIsolation:
    """不同用户数据隔离测试"""

    def test_different_users_different_results(self, db_session, reduce_fat_user, gain_muscle_user):
        """测试不同用户的结果不同"""
        _create_diet_records_for_days(
            db_session, reduce_fat_user.id, days_back=5,
            daily_calories=1600.0, protein=50.0, fat=30.0, carbs=250.0
        )
        _create_diet_records_for_days(
            db_session, gain_muscle_user.id, days_back=5,
            daily_calories=2800.0, protein=150.0, fat=80.0, carbs=300.0
        )

        result1 = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=5
        )
        result2 = stats_service.get_goal_progress(
            db_session, gain_muscle_user.id, days=5
        )

        assert result1.health_goal == "reduce_fat"
        assert result2.health_goal == "gain_muscle"
        assert result1.user_id != result2.user_id
        print(f"✓ 用户隔离测试通过: user1_score={result1.overall_score}, user2_score={result2.overall_score}")


# ==================== 综合场景测试 ====================

class TestIntegrationScenarios:
    """综合场景测试"""

    def test_reduce_fat_perfect_week(self, db_session, reduce_fat_user):
        """测试减脂用户完美一周（低热量+高运动）"""
        _create_diet_records_for_days(
            db_session, reduce_fat_user.id, days_back=7,
            daily_calories=1500.0, protein=80.0, fat=35.0, carbs=180.0
        )
        _create_exercise_records_for_days(
            db_session, reduce_fat_user.id, days_back=7,
            daily_calories=500.0, duration=60
        )
        _create_trip_plans_for_days(
            db_session, reduce_fat_user.id, days_back=7,
            planned_calories=500.0, duration=60
        )

        result = stats_service.get_goal_progress(
            db_session, reduce_fat_user.id, days=7
        )

        # 完美减脂周，分数应该很高
        assert result.overall_score >= 60.0
        assert result.streak_days == 7
        print(f"✓ 减脂完美周测试通过: overall_score={result.overall_score}")

    def test_gain_muscle_with_exercise_records(self, db_session, gain_muscle_user):
        """测试增肌用户有运动记录和计划"""
        _create_diet_records_for_days(
            db_session, gain_muscle_user.id, days_back=7,
            daily_calories=2800.0, protein=140.0, fat=80.0, carbs=350.0
        )
        _create_exercise_records_for_days(
            db_session, gain_muscle_user.id, days_back=7,
            daily_calories=600.0, duration=75
        )
        _create_trip_plans_for_days(
            db_session, gain_muscle_user.id, days_back=7,
            planned_calories=600.0, duration=75
        )

        result = stats_service.get_goal_progress(
            db_session, gain_muscle_user.id, days=7
        )

        assert result.health_goal == "gain_muscle"
        assert result.overall_score >= 0.0
        assert result.streak_days == 7
        print(f"✓ 增肌+运动记录测试通过: overall_score={result.overall_score}")

    def test_partial_records(self, db_session, balanced_user):
        """测试部分天有记录的情况"""
        today = date.today()
        # 只有3天有记录，7天周期
        for i in [0, 2, 4]:
            record = DietRecord(
                user_id=balanced_user.id,
                food_name=f"meal_day{i}",
                calories=1800.0,
                protein=60.0, fat=50.0, carbs=250.0,
                meal_type="lunch",
                record_date=today - timedelta(days=i)
            )
            db_session.add(record)
        db_session.commit()

        result = stats_service.get_goal_progress(
            db_session, balanced_user.id, days=7
        )

        assert result.overall_score >= 0.0
        assert result.overall_score <= 100.0
        # 只有今天连续记录
        assert result.streak_days == 1
        print(f"✓ 部分记录测试通过: overall_score={result.overall_score}, streak={result.streak_days}")


# ==================== 主程序 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
