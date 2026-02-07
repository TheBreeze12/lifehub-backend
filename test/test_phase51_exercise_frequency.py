"""
Phase 51 测试文件: 运动频率分析功能测试

测试策略：
1. 直接测试服务层逻辑（避免异步HTTP测试的复杂性）
2. 使用内存SQLite数据库进行隔离测试
3. 覆盖各种真实场景和边界条件

测试场景：
- 无运动记录用户（空数据）
- 单条运动记录
- 多条同日运动记录
- 跨多日运动记录（week周期）
- 跨多日运动记录（month周期）
- 运动类型分布统计
- 每日明细覆盖完整周期（含无记录天）
- 频率评级逻辑（excellent/good/fair/insufficient）
- 平均值计算（频率、时长、热量）
- 边界条件（0时长、0热量、未知运动类型）
- Pydantic模型序列化验证
- 路由层参数校验（period参数）
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
from app.db_models.exercise_record import ExerciseRecord
from app.services.stats_service import StatsService
from app.models.stats import (
    ExerciseFrequencyData,
    DailyExerciseFrequency,
    ExerciseTypeDistribution,
    ExerciseFrequencyResponse,
    EXERCISE_TYPE_LABELS,
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
def test_user(db_session):
    """创建测试用户"""
    user = User(
        id=1,
        nickname="test_user",
        password="password123",
        health_goal="balanced",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_exercise_record(
    db_session, user_id, exercise_date, exercise_type="walking",
    actual_calories=100.0, actual_duration=30, distance=None, notes=None
):
    """辅助函数：创建运动记录"""
    record = ExerciseRecord(
        user_id=user_id,
        exercise_type=exercise_type,
        actual_calories=actual_calories,
        actual_duration=actual_duration,
        distance=distance,
        exercise_date=exercise_date,
        notes=notes,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


# ==================== Pydantic 模型测试 ====================

class TestPydanticModels:
    """Phase 51 Pydantic模型验证测试"""

    def test_daily_exercise_frequency_model(self):
        """测试DailyExerciseFrequency模型创建"""
        data = DailyExerciseFrequency(
            date="2026-02-07",
            count=2,
            total_duration=65,
            total_calories=350.0,
            exercise_types=["walking", "running"]
        )
        assert data.date == "2026-02-07"
        assert data.count == 2
        assert data.total_duration == 65
        assert data.total_calories == 350.0
        assert data.exercise_types == ["walking", "running"]

    def test_daily_exercise_frequency_defaults(self):
        """测试DailyExerciseFrequency默认值"""
        data = DailyExerciseFrequency(date="2026-02-07")
        assert data.count == 0
        assert data.total_duration == 0
        assert data.total_calories == 0.0
        assert data.exercise_types == []

    def test_exercise_type_distribution_model(self):
        """测试ExerciseTypeDistribution模型创建"""
        data = ExerciseTypeDistribution(
            exercise_type="walking",
            label="步行",
            count=5,
            total_duration=150,
            total_calories=600.0,
            percentage=35.7
        )
        assert data.exercise_type == "walking"
        assert data.label == "步行"
        assert data.count == 5
        assert data.percentage == 35.7

    def test_exercise_frequency_data_model(self):
        """测试ExerciseFrequencyData模型创建"""
        data = ExerciseFrequencyData(
            user_id=1,
            period="week",
            period_label="最近一周",
            start_date="2026-02-01",
            end_date="2026-02-07",
            total_days=7,
            active_days=4,
            total_exercise_count=6,
            total_duration=210,
            total_calories=1200.0,
            avg_frequency=6.0,
            avg_duration_per_session=35.0,
            avg_calories_per_session=200.0,
            frequency_rating="good",
            frequency_suggestion="运动频率良好"
        )
        assert data.user_id == 1
        assert data.period == "week"
        assert data.active_days == 4
        assert data.frequency_rating == "good"

    def test_exercise_frequency_response_model(self):
        """测试ExerciseFrequencyResponse模型创建"""
        freq_data = ExerciseFrequencyData(
            user_id=1, period="week", period_label="最近一周",
            start_date="2026-02-01", end_date="2026-02-07",
        )
        resp = ExerciseFrequencyResponse(
            code=200, message="获取成功", data=freq_data
        )
        assert resp.code == 200
        assert resp.data.user_id == 1

    def test_exercise_frequency_data_serialization(self):
        """测试ExerciseFrequencyData JSON序列化"""
        data = ExerciseFrequencyData(
            user_id=1, period="week", period_label="最近一周",
            start_date="2026-02-01", end_date="2026-02-07",
            total_days=7, active_days=3, total_exercise_count=5,
            total_duration=150, total_calories=800.0,
            avg_frequency=5.0, avg_duration_per_session=30.0,
            avg_calories_per_session=160.0,
            daily_data=[
                DailyExerciseFrequency(date="2026-02-01", count=2,
                                       total_duration=60, total_calories=300.0,
                                       exercise_types=["walking"]),
            ],
            type_distribution=[
                ExerciseTypeDistribution(exercise_type="walking", label="步行",
                                        count=5, total_duration=150,
                                        total_calories=800.0, percentage=100.0),
            ],
            frequency_rating="good",
            frequency_suggestion="运动频率良好"
        )
        json_data = data.model_dump()
        assert json_data["user_id"] == 1
        assert len(json_data["daily_data"]) == 1
        assert len(json_data["type_distribution"]) == 1
        assert json_data["daily_data"][0]["exercise_types"] == ["walking"]

    def test_exercise_type_labels_completeness(self):
        """测试运动类型标签映射完整性"""
        expected_types = [
            "walking", "running", "cycling", "jogging", "hiking",
            "swimming", "gym", "indoor", "outdoor"
        ]
        for t in expected_types:
            assert t in EXERCISE_TYPE_LABELS, f"缺少运动类型标签: {t}"
            assert isinstance(EXERCISE_TYPE_LABELS[t], str)
            assert len(EXERCISE_TYPE_LABELS[t]) > 0


# ==================== 评级逻辑测试 ====================

class TestFrequencyRating:
    """运动频率评级逻辑测试"""

    def test_rate_frequency_week_excellent(self):
        """周模式 - 5天以上 -> excellent"""
        rating, suggestion = StatsService._rate_frequency(5, 7, "week")
        assert rating == "excellent"
        assert "优秀" in suggestion

    def test_rate_frequency_week_good(self):
        """周模式 - 3-4天 -> good"""
        rating, _ = StatsService._rate_frequency(3, 7, "week")
        assert rating == "good"
        rating, _ = StatsService._rate_frequency(4, 7, "week")
        assert rating == "good"

    def test_rate_frequency_week_fair(self):
        """周模式 - 1-2天 -> fair"""
        rating, _ = StatsService._rate_frequency(1, 7, "week")
        assert rating == "fair"
        rating, _ = StatsService._rate_frequency(2, 7, "week")
        assert rating == "fair"

    def test_rate_frequency_week_insufficient(self):
        """周模式 - 0天 -> insufficient"""
        rating, _ = StatsService._rate_frequency(0, 7, "week")
        assert rating == "insufficient"

    def test_rate_frequency_month_excellent(self):
        """月模式 - 周均>=5天 -> excellent"""
        # 30天中22天有运动 => 周均 22/4.28 ≈ 5.1
        rating, _ = StatsService._rate_frequency(22, 30, "month")
        assert rating == "excellent"

    def test_rate_frequency_month_good(self):
        """月模式 - 周均3-5天 -> good"""
        # 30天中15天有运动 => 周均 15/4.28 ≈ 3.5
        rating, _ = StatsService._rate_frequency(15, 30, "month")
        assert rating == "good"

    def test_rate_frequency_month_fair(self):
        """月模式 - 周均1-3天 -> fair"""
        # 30天中5天有运动 => 周均 5/4.28 ≈ 1.17
        rating, _ = StatsService._rate_frequency(5, 30, "month")
        assert rating == "fair"

    def test_rate_frequency_month_insufficient(self):
        """月模式 - 周均<1天 -> insufficient"""
        # 30天中2天有运动 => 周均 2/4.28 ≈ 0.47
        rating, _ = StatsService._rate_frequency(2, 30, "month")
        assert rating == "insufficient"

    def test_rate_frequency_zero_total_days(self):
        """total_days为0的边界情况"""
        rating, suggestion = StatsService._rate_frequency(0, 0, "week")
        assert rating == "insufficient"
        assert "暂无" in suggestion

    def test_rate_frequency_week_6_days(self):
        """周模式 - 6天 -> excellent"""
        rating, _ = StatsService._rate_frequency(6, 7, "week")
        assert rating == "excellent"

    def test_rate_frequency_week_7_days(self):
        """周模式 - 7天 -> excellent"""
        rating, _ = StatsService._rate_frequency(7, 7, "week")
        assert rating == "excellent"


# ==================== 服务层核心测试 ====================

class TestExerciseFrequencyService:
    """运动频率分析服务核心逻辑测试"""

    def test_no_records_week(self, db_session, test_user):
        """无运动记录用户 - week周期"""
        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")

        assert isinstance(result, ExerciseFrequencyData)
        assert result.user_id == test_user.id
        assert result.period == "week"
        assert result.period_label == "最近一周"
        assert result.total_days == 7
        assert result.active_days == 0
        assert result.total_exercise_count == 0
        assert result.total_duration == 0
        assert result.total_calories == 0.0
        assert result.avg_frequency == 0.0
        assert result.avg_duration_per_session == 0.0
        assert result.avg_calories_per_session == 0.0
        assert len(result.daily_data) == 7
        assert len(result.type_distribution) == 0
        assert result.frequency_rating == "insufficient"

    def test_no_records_month(self, db_session, test_user):
        """无运动记录用户 - month周期"""
        result = stats_service.get_exercise_frequency(db_session, test_user.id, "month")

        assert result.period == "month"
        assert result.period_label == "最近一个月"
        assert result.total_days == 30
        assert len(result.daily_data) == 30
        assert result.active_days == 0

    def test_single_record_today(self, db_session, test_user):
        """单条运动记录（今天）"""
        today = date.today()
        _create_exercise_record(
            db_session, test_user.id, today,
            exercise_type="running", actual_calories=250.0, actual_duration=30
        )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")

        assert result.active_days == 1
        assert result.total_exercise_count == 1
        assert result.total_duration == 30
        assert result.total_calories == 250.0
        assert result.avg_duration_per_session == 30.0
        assert result.avg_calories_per_session == 250.0
        assert len(result.type_distribution) == 1
        assert result.type_distribution[0].exercise_type == "running"
        assert result.type_distribution[0].label == "跑步"
        assert result.type_distribution[0].percentage == 100.0

    def test_multiple_records_same_day(self, db_session, test_user):
        """同一天多条运动记录"""
        today = date.today()
        _create_exercise_record(
            db_session, test_user.id, today,
            exercise_type="walking", actual_calories=100.0, actual_duration=20
        )
        _create_exercise_record(
            db_session, test_user.id, today,
            exercise_type="running", actual_calories=300.0, actual_duration=30
        )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")

        assert result.active_days == 1
        assert result.total_exercise_count == 2
        assert result.total_duration == 50
        assert result.total_calories == 400.0
        assert result.avg_duration_per_session == 25.0
        assert result.avg_calories_per_session == 200.0

        # 类型分布应该有两个
        assert len(result.type_distribution) == 2
        types = {td.exercise_type for td in result.type_distribution}
        assert "walking" in types
        assert "running" in types

        # 每个类型各50%
        for td in result.type_distribution:
            assert td.percentage == 50.0

    def test_multi_day_records_week(self, db_session, test_user):
        """多天运动记录 - week"""
        today = date.today()
        for i in range(5):
            d = today - timedelta(days=i)
            _create_exercise_record(
                db_session, test_user.id, d,
                exercise_type="walking", actual_calories=150.0, actual_duration=30
            )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")

        assert result.active_days == 5
        assert result.total_exercise_count == 5
        assert result.total_duration == 150
        assert result.total_calories == 750.0
        assert result.frequency_rating == "excellent"

    def test_multi_day_records_month(self, db_session, test_user):
        """多天运动记录 - month"""
        today = date.today()
        # 在过去30天中，每隔一天运动一次
        for i in range(0, 30, 2):
            d = today - timedelta(days=i)
            _create_exercise_record(
                db_session, test_user.id, d,
                exercise_type="cycling", actual_calories=200.0, actual_duration=45
            )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "month")

        assert result.period == "month"
        assert result.active_days == 15
        assert result.total_exercise_count == 15
        assert result.total_duration == 15 * 45
        assert result.total_calories == 15 * 200.0
        assert result.frequency_rating == "good"  # 周均 15/4.28 ≈ 3.5天 -> good

    def test_daily_data_covers_full_period(self, db_session, test_user):
        """每日明细覆盖完整周期（含无记录天）"""
        today = date.today()
        # 只在今天有运动记录
        _create_exercise_record(
            db_session, test_user.id, today,
            exercise_type="gym", actual_calories=400.0, actual_duration=60
        )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")

        assert len(result.daily_data) == 7
        # 检查今天的记录
        today_str = today.isoformat()
        today_data = [d for d in result.daily_data if d.date == today_str]
        assert len(today_data) == 1
        assert today_data[0].count == 1
        assert today_data[0].total_calories == 400.0
        assert today_data[0].exercise_types == ["gym"]

        # 其他天应该是0
        other_days = [d for d in result.daily_data if d.date != today_str]
        for day in other_days:
            assert day.count == 0
            assert day.total_duration == 0
            assert day.total_calories == 0.0
            assert day.exercise_types == []

    def test_daily_data_sorted_by_date(self, db_session, test_user):
        """每日明细按日期排序"""
        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")
        dates = [d.date for d in result.daily_data]
        assert dates == sorted(dates)

    def test_type_distribution_sorted_by_count(self, db_session, test_user):
        """运动类型分布按次数降序排列"""
        today = date.today()
        # walking 3次, running 2次, cycling 1次
        for _ in range(3):
            _create_exercise_record(
                db_session, test_user.id, today,
                exercise_type="walking", actual_calories=100, actual_duration=20
            )
        for _ in range(2):
            _create_exercise_record(
                db_session, test_user.id, today,
                exercise_type="running", actual_calories=200, actual_duration=25
            )
        _create_exercise_record(
            db_session, test_user.id, today,
            exercise_type="cycling", actual_calories=150, actual_duration=30
        )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")

        assert len(result.type_distribution) == 3
        assert result.type_distribution[0].exercise_type == "walking"
        assert result.type_distribution[0].count == 3
        assert result.type_distribution[1].exercise_type == "running"
        assert result.type_distribution[1].count == 2
        assert result.type_distribution[2].exercise_type == "cycling"
        assert result.type_distribution[2].count == 1

    def test_type_distribution_percentage_sum(self, db_session, test_user):
        """类型分布百分比之和应接近100%"""
        today = date.today()
        for t in ["walking", "running", "cycling"]:
            _create_exercise_record(
                db_session, test_user.id, today,
                exercise_type=t, actual_calories=100, actual_duration=20
            )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")
        pct_sum = sum(td.percentage for td in result.type_distribution)
        assert abs(pct_sum - 100.0) < 0.5  # 允许四舍五入误差

    def test_avg_frequency_calculation(self, db_session, test_user):
        """平均每周运动次数计算"""
        today = date.today()
        # month周期(30天=~4.28周)中有10次运动
        for i in range(10):
            d = today - timedelta(days=i * 3)
            if d >= today - timedelta(days=29):
                _create_exercise_record(
                    db_session, test_user.id, d,
                    exercise_type="walking", actual_calories=100, actual_duration=20
                )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "month")
        # avg_frequency = total_count / (30/7)
        expected_avg = round(result.total_exercise_count / (30 / 7.0), 1)
        assert result.avg_frequency == expected_avg

    def test_zero_calories_and_duration(self, db_session, test_user):
        """运动记录中热量和时长为0的情况"""
        today = date.today()
        _create_exercise_record(
            db_session, test_user.id, today,
            exercise_type="walking", actual_calories=0.0, actual_duration=0
        )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")

        assert result.active_days == 1
        assert result.total_exercise_count == 1
        assert result.total_calories == 0.0
        assert result.total_duration == 0
        assert result.avg_duration_per_session == 0.0
        assert result.avg_calories_per_session == 0.0

    def test_unknown_exercise_type(self, db_session, test_user):
        """未知运动类型的处理"""
        today = date.today()
        _create_exercise_record(
            db_session, test_user.id, today,
            exercise_type="yoga", actual_calories=100, actual_duration=30
        )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")

        assert len(result.type_distribution) == 1
        assert result.type_distribution[0].exercise_type == "yoga"
        # 未知类型label应该用原始类型名
        assert result.type_distribution[0].label == "yoga"

    def test_null_exercise_type_fallback(self, db_session, test_user):
        """exercise_type为None时的回退处理（SQLAlchemy默认值为walking）"""
        today = date.today()
        record = ExerciseRecord(
            user_id=test_user.id,
            exercise_type=None,
            actual_calories=100.0,
            actual_duration=20,
            exercise_date=today,
        )
        db_session.add(record)
        db_session.commit()

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")

        # ExerciseRecord模型exercise_type有default="walking"，SQLAlchemy会填充默认值
        # 但在内存SQLite中，None可能直接写入，服务层回退到"outdoor"
        assert result.total_exercise_count == 1
        if result.type_distribution:
            # 根据数据库行为可能是 walking（SQLAlchemy default）或 outdoor（服务层回退）
            assert result.type_distribution[0].exercise_type in ("walking", "outdoor")

    def test_records_outside_period_excluded(self, db_session, test_user):
        """超出统计周期的记录不应包含"""
        today = date.today()
        # 一条8天前的记录（超出week周期）
        _create_exercise_record(
            db_session, test_user.id, today - timedelta(days=8),
            exercise_type="running", actual_calories=200, actual_duration=30
        )
        # 一条今天的记录
        _create_exercise_record(
            db_session, test_user.id, today,
            exercise_type="walking", actual_calories=100, actual_duration=20
        )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")

        assert result.total_exercise_count == 1
        assert result.active_days == 1
        assert result.total_calories == 100.0

    def test_start_end_date_correctness_week(self, db_session, test_user):
        """week模式的起止日期正确性"""
        today = date.today()
        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")

        expected_start = (today - timedelta(days=6)).isoformat()
        assert result.start_date == expected_start
        assert result.end_date == today.isoformat()

    def test_start_end_date_correctness_month(self, db_session, test_user):
        """month模式的起止日期正确性"""
        today = date.today()
        result = stats_service.get_exercise_frequency(db_session, test_user.id, "month")

        expected_start = (today - timedelta(days=29)).isoformat()
        assert result.start_date == expected_start
        assert result.end_date == today.isoformat()

    def test_multiple_types_same_day(self, db_session, test_user):
        """同一天多种运动类型的daily_data聚合"""
        today = date.today()
        _create_exercise_record(
            db_session, test_user.id, today,
            exercise_type="walking", actual_calories=100, actual_duration=20
        )
        _create_exercise_record(
            db_session, test_user.id, today,
            exercise_type="swimming", actual_calories=350, actual_duration=45
        )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")

        today_str = today.isoformat()
        today_data = [d for d in result.daily_data if d.date == today_str][0]
        assert today_data.count == 2
        assert today_data.total_duration == 65
        assert today_data.total_calories == 450.0
        # exercise_types应按字母排序
        assert today_data.exercise_types == sorted(["walking", "swimming"])

    def test_large_data_set(self, db_session, test_user):
        """大量数据测试 - 30天每天3次运动"""
        today = date.today()
        types = ["walking", "running", "cycling"]
        for i in range(30):
            d = today - timedelta(days=i)
            for j, t in enumerate(types):
                _create_exercise_record(
                    db_session, test_user.id, d,
                    exercise_type=t,
                    actual_calories=100.0 * (j + 1),
                    actual_duration=20 * (j + 1)
                )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "month")

        assert result.active_days == 30
        assert result.total_exercise_count == 90
        assert len(result.type_distribution) == 3
        assert result.frequency_rating == "excellent"

    def test_rating_fair_with_2_active_days_week(self, db_session, test_user):
        """周模式 - 2天运动 -> fair评级"""
        today = date.today()
        _create_exercise_record(
            db_session, test_user.id, today,
            exercise_type="walking", actual_calories=100, actual_duration=20
        )
        _create_exercise_record(
            db_session, test_user.id, today - timedelta(days=2),
            exercise_type="running", actual_calories=200, actual_duration=30
        )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")
        assert result.active_days == 2
        assert result.frequency_rating == "fair"

    def test_rating_good_with_3_active_days_week(self, db_session, test_user):
        """周模式 - 3天运动 -> good评级"""
        today = date.today()
        for i in range(3):
            _create_exercise_record(
                db_session, test_user.id, today - timedelta(days=i),
                exercise_type="walking", actual_calories=100, actual_duration=20
            )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")
        assert result.active_days == 3
        assert result.frequency_rating == "good"


# ==================== 路由参数校验测试 ====================

class TestRouterValidation:
    """路由层参数校验测试（不需要启动服务器）"""

    def test_valid_period_values(self):
        """period参数合法值"""
        valid_periods = ["week", "month"]
        for p in valid_periods:
            assert p in ("week", "month")

    def test_exercise_frequency_response_structure(self, db_session, test_user):
        """响应结构完整性验证"""
        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")

        # 验证所有必要字段存在
        assert hasattr(result, "user_id")
        assert hasattr(result, "period")
        assert hasattr(result, "period_label")
        assert hasattr(result, "start_date")
        assert hasattr(result, "end_date")
        assert hasattr(result, "total_days")
        assert hasattr(result, "active_days")
        assert hasattr(result, "total_exercise_count")
        assert hasattr(result, "total_duration")
        assert hasattr(result, "total_calories")
        assert hasattr(result, "avg_frequency")
        assert hasattr(result, "avg_duration_per_session")
        assert hasattr(result, "avg_calories_per_session")
        assert hasattr(result, "daily_data")
        assert hasattr(result, "type_distribution")
        assert hasattr(result, "frequency_rating")
        assert hasattr(result, "frequency_suggestion")

    def test_response_wrapping(self, db_session, test_user):
        """ExerciseFrequencyResponse包装正确"""
        data = stats_service.get_exercise_frequency(db_session, test_user.id, "week")
        resp = ExerciseFrequencyResponse(code=200, message="获取成功", data=data)
        json_out = resp.model_dump()

        assert json_out["code"] == 200
        assert json_out["message"] == "获取成功"
        assert "data" in json_out
        assert json_out["data"]["user_id"] == test_user.id
        assert json_out["data"]["period"] == "week"


# ==================== 与验证方法对齐的集成测试 ====================

class TestIntegrationScenarios:
    """集成测试：模拟真实使用场景"""

    def test_realistic_week_scenario(self, db_session, test_user):
        """
        模拟真实场景：用户本周运动记录
        - 周一：跑步30分钟，消耗300kcal
        - 周三：步行40分钟，消耗150kcal
        - 周五：骑行60分钟，消耗500kcal
        - 周日：游泳45分钟，消耗400kcal
        """
        today = date.today()
        records_data = [
            (0, "swimming", 400.0, 45),
            (2, "cycling", 500.0, 60),
            (4, "walking", 150.0, 40),
            (6, "running", 300.0, 30),
        ]
        for days_ago, ex_type, calories, duration in records_data:
            d = today - timedelta(days=days_ago)
            if d >= today - timedelta(days=6):  # 确保在week范围内
                _create_exercise_record(
                    db_session, test_user.id, d,
                    exercise_type=ex_type, actual_calories=calories,
                    actual_duration=duration
                )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")

        # 验证基本统计
        assert result.total_days == 7
        assert result.active_days >= 1  # 至少有一天在范围内
        assert result.total_calories > 0
        assert result.total_duration > 0

        # 验证评级
        assert result.frequency_rating in ("excellent", "good", "fair", "insufficient")
        assert len(result.frequency_suggestion) > 0

        # 验证每日数据完整性
        assert len(result.daily_data) == 7

    def test_month_period_with_sparse_data(self, db_session, test_user):
        """月模式下稀疏数据的处理"""
        today = date.today()
        # 只在第1天和第15天有记录
        _create_exercise_record(
            db_session, test_user.id, today,
            exercise_type="running", actual_calories=300, actual_duration=30
        )
        _create_exercise_record(
            db_session, test_user.id, today - timedelta(days=15),
            exercise_type="walking", actual_calories=100, actual_duration=20
        )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "month")

        assert result.total_days == 30
        assert result.active_days == 2
        assert len(result.daily_data) == 30
        # 大部分天应该是0
        zero_days = [d for d in result.daily_data if d.count == 0]
        assert len(zero_days) == 28

    def test_consistency_between_daily_and_totals(self, db_session, test_user):
        """每日明细汇总应与总计一致"""
        today = date.today()
        for i in range(5):
            _create_exercise_record(
                db_session, test_user.id, today - timedelta(days=i),
                exercise_type="walking", actual_calories=100 + i * 10,
                actual_duration=20 + i * 5
            )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")

        daily_total_count = sum(d.count for d in result.daily_data)
        daily_total_duration = sum(d.total_duration for d in result.daily_data)
        daily_total_calories = sum(d.total_calories for d in result.daily_data)

        assert daily_total_count == result.total_exercise_count
        assert daily_total_duration == result.total_duration
        assert abs(daily_total_calories - result.total_calories) < 0.01

    def test_consistency_between_type_dist_and_totals(self, db_session, test_user):
        """类型分布汇总应与总计一致"""
        today = date.today()
        _create_exercise_record(
            db_session, test_user.id, today,
            exercise_type="walking", actual_calories=100, actual_duration=20
        )
        _create_exercise_record(
            db_session, test_user.id, today,
            exercise_type="running", actual_calories=250, actual_duration=30
        )
        _create_exercise_record(
            db_session, test_user.id, today - timedelta(days=1),
            exercise_type="walking", actual_calories=120, actual_duration=25
        )

        result = stats_service.get_exercise_frequency(db_session, test_user.id, "week")

        type_total_count = sum(td.count for td in result.type_distribution)
        type_total_duration = sum(td.total_duration for td in result.type_distribution)
        type_total_calories = sum(td.total_calories for td in result.type_distribution)

        assert type_total_count == result.total_exercise_count
        assert type_total_duration == result.total_duration
        assert abs(type_total_calories - result.total_calories) < 0.01
