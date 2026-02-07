"""
Phase 26 测试文件: 饮食-运动数据联动测试

测试策略：
1. 直接测试服务层逻辑（使用内存SQLite数据库隔离测试）
2. 覆盖核心业务场景：
   - 运动记录关联到热量统计
   - 实际热量缺口计算
   - 目标达成率计算
   - 计划消耗 vs 实际消耗的区分
   - 每周统计中的联动数据
3. 边界条件覆盖

测试场景：
- 有饮食记录 + 运动记录的用户
- 只有饮食记录没有运动记录
- 只有运动记录没有饮食记录
- 有运动计划但没有实际运动记录
- 有实际运动记录但没有运动计划
- 多日联动统计
- 零值、大数值、负净热量等边界
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
        nickname="测试用户",
        password="test_password",
        health_goal="reduce_fat",
        weight=70.0,
        height=175.0,
        age=25,
        gender="male"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def today():
    """返回今天日期"""
    return date.today()


@pytest.fixture
def yesterday(today):
    """返回昨天日期"""
    return today - timedelta(days=1)


# ==================== 辅助函数 ====================

def create_diet_records(db_session, user_id, target_date, records_data):
    """批量创建饮食记录"""
    records = []
    for data in records_data:
        record = DietRecord(
            user_id=user_id,
            food_name=data["food_name"],
            calories=data["calories"],
            protein=data.get("protein", 0.0),
            fat=data.get("fat", 0.0),
            carbs=data.get("carbs", 0.0),
            meal_type=data.get("meal_type", "lunch"),
            record_date=target_date
        )
        db_session.add(record)
        records.append(record)
    db_session.commit()
    return records


def create_trip_plan(db_session, user_id, target_date, items_data):
    """创建运动计划及其项目"""
    trip = TripPlan(
        user_id=user_id,
        title="测试运动计划",
        destination="测试地点",
        start_date=target_date,
        end_date=target_date,
        status="done"
    )
    db_session.add(trip)
    db_session.commit()

    for item_data in items_data:
        item = TripItem(
            trip_id=trip.id,
            day_index=1,
            place_name=item_data.get("place_name", "测试场所"),
            place_type=item_data.get("place_type", "walking"),
            duration=item_data.get("duration", 30),
            cost=item_data.get("cost", 100.0),
        )
        db_session.add(item)
    db_session.commit()
    return trip


def create_exercise_records(db_session, user_id, target_date, records_data, plan_id=None):
    """批量创建运动记录"""
    records = []
    for data in records_data:
        record = ExerciseRecord(
            user_id=user_id,
            plan_id=data.get("plan_id", plan_id),
            exercise_type=data.get("exercise_type", "walking"),
            actual_calories=data["actual_calories"],
            actual_duration=data["actual_duration"],
            distance=data.get("distance"),
            planned_calories=data.get("planned_calories"),
            planned_duration=data.get("planned_duration"),
            exercise_date=target_date,
            notes=data.get("notes"),
        )
        db_session.add(record)
        records.append(record)
    db_session.commit()
    return records


# ==================== 核心联动功能测试 ====================

class TestDietExerciseLinkage:
    """饮食-运动数据联动核心测试"""

    def test_daily_stats_with_exercise_records(self, db_session, test_user, today):
        """测试包含运动记录的每日统计 - 核心场景"""
        # 创建饮食记录
        create_diet_records(db_session, test_user.id, today, [
            {"food_name": "早餐", "calories": 300.0, "meal_type": "breakfast"},
            {"food_name": "午餐", "calories": 500.0, "meal_type": "lunch"},
            {"food_name": "晚餐", "calories": 400.0, "meal_type": "dinner"},
        ])

        # 创建运动计划（计划消耗300）
        trip = create_trip_plan(db_session, test_user.id, today, [
            {"cost": 200.0, "duration": 30},
            {"cost": 100.0, "duration": 20},
        ])

        # 创建运动记录（实际消耗280）
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 180.0, "actual_duration": 35, "planned_calories": 200.0, "planned_duration": 30},
            {"actual_calories": 100.0, "actual_duration": 18, "planned_calories": 100.0, "planned_duration": 20},
        ], plan_id=trip.id)

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)

        # 摄入 = 300 + 500 + 400 = 1200
        assert stats.intake_calories == 1200.0

        # 计划消耗 = 200 + 100 = 300
        assert stats.planned_burn_calories == 300.0

        # 实际消耗 = 180 + 100 = 280
        assert stats.actual_burn_calories == 280.0

        # burn_calories 应该使用实际消耗（有运动记录时优先使用实际值）
        assert stats.burn_calories == 280.0

        # 实际热量缺口 = 摄入 - 实际消耗 = 1200 - 280 = 920
        assert stats.calorie_deficit == 920.0

        # 达成率 = 实际消耗 / 计划消耗 * 100 = 280 / 300 * 100 ≈ 93.3
        assert stats.goal_achievement_rate is not None
        assert abs(stats.goal_achievement_rate - 93.3) < 0.1

        # 验证运动记录统计
        assert stats.actual_exercise_count == 2
        assert stats.actual_exercise_duration == 35 + 18

        print(f"✓ 联动统计通过: 摄入={stats.intake_calories}, 实际消耗={stats.actual_burn_calories}, "
              f"计划消耗={stats.planned_burn_calories}, 达成率={stats.goal_achievement_rate}%")

    def test_daily_stats_only_planned_no_actual(self, db_session, test_user, today):
        """测试只有运动计划没有运动记录的情况"""
        create_diet_records(db_session, test_user.id, today, [
            {"food_name": "午餐", "calories": 800.0, "meal_type": "lunch"},
        ])

        # 只有运动计划
        create_trip_plan(db_session, test_user.id, today, [
            {"cost": 200.0, "duration": 30},
        ])

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)

        assert stats.intake_calories == 800.0
        assert stats.planned_burn_calories == 200.0
        assert stats.actual_burn_calories == 0.0

        # 没有运动记录时，burn_calories 使用计划值
        assert stats.burn_calories == 200.0

        # 热量缺口仍基于有效的burn_calories
        assert stats.calorie_deficit == 600.0

        # 没有实际运动记录时，达成率为0
        assert stats.goal_achievement_rate == 0.0

        print("✓ 只有计划无记录测试通过")

    def test_daily_stats_only_actual_no_planned(self, db_session, test_user, today):
        """测试只有运动记录没有运动计划的情况（自由运动）"""
        create_diet_records(db_session, test_user.id, today, [
            {"food_name": "午餐", "calories": 600.0, "meal_type": "lunch"},
        ])

        # 只有运动记录，无计划
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 250.0, "actual_duration": 40, "exercise_type": "running"},
        ])

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)

        assert stats.intake_calories == 600.0
        assert stats.planned_burn_calories == 0.0
        assert stats.actual_burn_calories == 250.0

        # 有运动记录时用实际值
        assert stats.burn_calories == 250.0

        # 热量缺口
        assert stats.calorie_deficit == 350.0

        # 无计划时达成率为None（无目标可对比）
        assert stats.goal_achievement_rate is None

        print("✓ 只有运动记录无计划测试通过")

    def test_daily_stats_no_exercise_at_all(self, db_session, test_user, today):
        """测试完全没有运动（计划和记录都没有）"""
        create_diet_records(db_session, test_user.id, today, [
            {"food_name": "午餐", "calories": 500.0, "meal_type": "lunch"},
        ])

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)

        assert stats.intake_calories == 500.0
        assert stats.planned_burn_calories == 0.0
        assert stats.actual_burn_calories == 0.0
        assert stats.burn_calories == 0.0
        assert stats.calorie_deficit == 500.0
        assert stats.goal_achievement_rate is None

        print("✓ 完全无运动测试通过")

    def test_daily_stats_no_data(self, db_session, test_user, today):
        """测试完全无数据"""
        future = today + timedelta(days=30)
        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, future)

        assert stats.intake_calories == 0.0
        assert stats.planned_burn_calories == 0.0
        assert stats.actual_burn_calories == 0.0
        assert stats.burn_calories == 0.0
        assert stats.calorie_deficit == 0.0
        assert stats.goal_achievement_rate is None
        assert stats.actual_exercise_count == 0
        assert stats.actual_exercise_duration == 0

        print("✓ 完全无数据测试通过")


# ==================== 达成率计算测试 ====================

class TestGoalAchievementRate:
    """目标达成率计算测试"""

    def test_achievement_100_percent(self, db_session, test_user, today):
        """测试达成率100%（实际等于计划）"""
        trip = create_trip_plan(db_session, test_user.id, today, [
            {"cost": 300.0, "duration": 30},
        ])
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 300.0, "actual_duration": 30, "planned_calories": 300.0},
        ], plan_id=trip.id)

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        assert stats.goal_achievement_rate == 100.0
        print("✓ 100%达成率测试通过")

    def test_achievement_over_100_percent(self, db_session, test_user, today):
        """测试超额完成（>100%）"""
        trip = create_trip_plan(db_session, test_user.id, today, [
            {"cost": 200.0, "duration": 30},
        ])
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 350.0, "actual_duration": 50, "planned_calories": 200.0},
        ], plan_id=trip.id)

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        assert stats.goal_achievement_rate is not None
        assert stats.goal_achievement_rate > 100.0
        # 350 / 200 * 100 = 175.0
        assert abs(stats.goal_achievement_rate - 175.0) < 0.1
        print(f"✓ 超额完成测试通过: {stats.goal_achievement_rate}%")

    def test_achievement_partial(self, db_session, test_user, today):
        """测试部分完成（<100%）"""
        trip = create_trip_plan(db_session, test_user.id, today, [
            {"cost": 400.0, "duration": 60},
        ])
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 200.0, "actual_duration": 30, "planned_calories": 400.0},
        ], plan_id=trip.id)

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        assert stats.goal_achievement_rate is not None
        # 200 / 400 * 100 = 50.0
        assert abs(stats.goal_achievement_rate - 50.0) < 0.1
        print(f"✓ 部分完成测试通过: {stats.goal_achievement_rate}%")

    def test_achievement_zero_planned(self, db_session, test_user, today):
        """测试计划消耗为0时的达成率"""
        # 只有运动记录，没有计划
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 200.0, "actual_duration": 30},
        ])

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        # 无计划时达成率应为None
        assert stats.goal_achievement_rate is None
        print("✓ 零计划达成率测试通过")

    def test_achievement_multiple_exercises(self, db_session, test_user, today):
        """测试多项运动记录的综合达成率"""
        trip = create_trip_plan(db_session, test_user.id, today, [
            {"cost": 150.0, "duration": 30},
            {"cost": 250.0, "duration": 40},
        ])
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 120.0, "actual_duration": 25},
            {"actual_calories": 200.0, "actual_duration": 35},
            {"actual_calories": 80.0, "actual_duration": 15},
        ], plan_id=trip.id)

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        # 计划: 150 + 250 = 400
        # 实际: 120 + 200 + 80 = 400
        # 达成率: 400 / 400 * 100 = 100.0
        assert stats.planned_burn_calories == 400.0
        assert stats.actual_burn_calories == 400.0
        assert abs(stats.goal_achievement_rate - 100.0) < 0.1
        print("✓ 多项运动达成率测试通过")


# ==================== 热量缺口计算测试 ====================

class TestCalorieDeficit:
    """热量缺口计算测试"""

    def test_positive_deficit(self, db_session, test_user, today):
        """测试正热量缺口（摄入 > 消耗）"""
        create_diet_records(db_session, test_user.id, today, [
            {"food_name": "大餐", "calories": 2000.0},
        ])
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 500.0, "actual_duration": 60},
        ])

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        assert stats.calorie_deficit == 1500.0
        assert stats.calorie_deficit > 0
        print(f"✓ 正热量缺口: {stats.calorie_deficit}")

    def test_negative_deficit(self, db_session, test_user, today):
        """测试负热量缺口（消耗 > 摄入）"""
        create_diet_records(db_session, test_user.id, today, [
            {"food_name": "少量食物", "calories": 200.0},
        ])
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 800.0, "actual_duration": 120},
        ])

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        assert stats.calorie_deficit == -600.0
        assert stats.calorie_deficit < 0
        print(f"✓ 负热量缺口: {stats.calorie_deficit}")

    def test_zero_deficit(self, db_session, test_user, today):
        """测试零热量缺口（摄入 = 消耗）"""
        create_diet_records(db_session, test_user.id, today, [
            {"food_name": "食物", "calories": 500.0},
        ])
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 500.0, "actual_duration": 60},
        ])

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        assert stats.calorie_deficit == 0.0
        print("✓ 零热量缺口测试通过")

    def test_deficit_precision(self, db_session, test_user, today):
        """测试热量缺口的浮点数精度"""
        create_diet_records(db_session, test_user.id, today, [
            {"food_name": "精确食物", "calories": 123.45},
        ])
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 67.89, "actual_duration": 15},
        ])

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        expected_deficit = 123.45 - 67.89
        assert abs(stats.calorie_deficit - expected_deficit) < 0.01
        print(f"✓ 热量缺口精度: {stats.calorie_deficit}")


# ==================== 每周联动统计测试 ====================

class TestWeeklyLinkage:
    """每周联动统计测试"""

    def test_weekly_stats_with_exercise_records(self, db_session, test_user, today):
        """测试含运动记录的每周统计"""
        week_start = today - timedelta(days=today.weekday())

        # 在周一创建饮食和运动记录
        monday = week_start
        create_diet_records(db_session, test_user.id, monday, [
            {"food_name": "周一午餐", "calories": 600.0, "meal_type": "lunch"},
        ])
        create_exercise_records(db_session, test_user.id, monday, [
            {"actual_calories": 200.0, "actual_duration": 30},
        ])

        # 在周三创建饮食和运动记录
        wednesday = week_start + timedelta(days=2)
        create_diet_records(db_session, test_user.id, wednesday, [
            {"food_name": "周三午餐", "calories": 700.0, "meal_type": "lunch"},
        ])
        create_exercise_records(db_session, test_user.id, wednesday, [
            {"actual_calories": 300.0, "actual_duration": 45},
        ])

        stats = stats_service.get_weekly_calorie_stats(db_session, test_user.id, week_start)

        # 验证总摄入
        assert stats.total_intake == 1300.0

        # 验证总消耗（应包含运动记录的实际消耗）
        assert stats.total_burn >= 500.0  # 200 + 300

        # 验证每日明细有7天
        assert len(stats.daily_breakdown) == 7

        # 验证活跃天数
        assert stats.active_days >= 2

        print(f"✓ 每周联动统计通过: 总摄入={stats.total_intake}, 总消耗={stats.total_burn}")

    def test_weekly_stats_mixed_plan_and_records(self, db_session, test_user, today):
        """测试混合计划和记录的每周统计"""
        week_start = today - timedelta(days=today.weekday())

        # 周一：只有计划
        monday = week_start
        create_trip_plan(db_session, test_user.id, monday, [
            {"cost": 200.0, "duration": 30},
        ])

        # 周三：有计划也有运动记录
        wednesday = week_start + timedelta(days=2)
        trip_wed = create_trip_plan(db_session, test_user.id, wednesday, [
            {"cost": 300.0, "duration": 40},
        ])
        create_exercise_records(db_session, test_user.id, wednesday, [
            {"actual_calories": 250.0, "actual_duration": 35},
        ], plan_id=trip_wed.id)

        stats = stats_service.get_weekly_calorie_stats(db_session, test_user.id, week_start)

        # 总消耗应反映混合数据
        assert stats.total_burn > 0
        assert len(stats.daily_breakdown) == 7

        print("✓ 混合计划和记录的每周统计通过")

    def test_weekly_no_data(self, db_session, test_user, today):
        """测试无数据的每周统计"""
        future_week = today + timedelta(days=60)
        week_start = future_week - timedelta(days=future_week.weekday())

        stats = stats_service.get_weekly_calorie_stats(db_session, test_user.id, week_start)

        assert stats.total_intake == 0.0
        assert stats.total_burn == 0.0
        assert stats.active_days == 0

        print("✓ 每周无数据测试通过")


# ==================== 边界条件测试 ====================

class TestEdgeCases:
    """边界条件测试"""

    def test_zero_calorie_exercise(self, db_session, test_user, today):
        """测试零消耗运动记录（如拉伸）"""
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 0.0, "actual_duration": 10, "exercise_type": "indoor"},
        ])

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        assert stats.actual_burn_calories == 0.0
        assert stats.actual_exercise_count == 1
        print("✓ 零消耗运动测试通过")

    def test_large_exercise_values(self, db_session, test_user, today):
        """测试大数值运动记录"""
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 3000.0, "actual_duration": 300, "exercise_type": "running"},
        ])

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        assert stats.actual_burn_calories == 3000.0
        print("✓ 大数值运动测试通过")

    def test_multiple_exercise_types(self, db_session, test_user, today):
        """测试多种运动类型"""
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 100.0, "actual_duration": 20, "exercise_type": "walking"},
            {"actual_calories": 200.0, "actual_duration": 25, "exercise_type": "running"},
            {"actual_calories": 150.0, "actual_duration": 30, "exercise_type": "cycling"},
            {"actual_calories": 80.0, "actual_duration": 15, "exercise_type": "swimming"},
        ])

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        assert stats.actual_burn_calories == 530.0
        assert stats.actual_exercise_count == 4
        assert stats.actual_exercise_duration == 90
        print("✓ 多运动类型测试通过")

    def test_chinese_meal_type_mapping(self, db_session, test_user, today):
        """测试中文餐次名映射"""
        create_diet_records(db_session, test_user.id, today, [
            {"food_name": "包子", "calories": 200.0, "meal_type": "早餐"},
            {"food_name": "盖饭", "calories": 500.0, "meal_type": "午餐"},
        ])

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        assert stats.intake_calories == 700.0
        if stats.meal_breakdown:
            assert stats.meal_breakdown.get("breakfast", 0) == 200.0
            assert stats.meal_breakdown.get("lunch", 0) == 500.0
        print("✓ 中文餐次映射测试通过")

    def test_nonexistent_user(self, db_session, today):
        """测试不存在的用户"""
        stats = stats_service.get_daily_calorie_stats(db_session, 99999, today)
        assert stats.intake_calories == 0.0
        assert stats.burn_calories == 0.0
        assert stats.actual_burn_calories == 0.0
        assert stats.planned_burn_calories == 0.0
        print("✓ 不存在用户测试通过")

    def test_exercise_record_different_user(self, db_session, test_user, today):
        """测试运动记录不会混入其他用户"""
        # 创建另一个用户
        user2 = User(
            id=2,
            nickname="其他用户",
            password="test",
            weight=60.0,
        )
        db_session.add(user2)
        db_session.commit()

        # 给用户2创建运动记录
        create_exercise_records(db_session, user2.id, today, [
            {"actual_calories": 500.0, "actual_duration": 60},
        ])

        # 查询用户1的统计
        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        assert stats.actual_burn_calories == 0.0
        assert stats.actual_exercise_count == 0
        print("✓ 用户隔离测试通过")


# ==================== 模型字段验证测试 ====================

class TestModelFields:
    """模型字段验证"""

    def test_daily_stats_all_fields_present(self, db_session, test_user, today):
        """验证DailyCalorieStats包含所有Phase 26新增字段"""
        create_diet_records(db_session, test_user.id, today, [
            {"food_name": "午餐", "calories": 500.0},
        ])
        trip = create_trip_plan(db_session, test_user.id, today, [
            {"cost": 200.0, "duration": 30},
        ])
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 150.0, "actual_duration": 25},
        ], plan_id=trip.id)

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)

        # Phase 26 新增字段
        assert hasattr(stats, 'planned_burn_calories')
        assert hasattr(stats, 'actual_burn_calories')
        assert hasattr(stats, 'actual_exercise_count')
        assert hasattr(stats, 'actual_exercise_duration')
        assert hasattr(stats, 'calorie_deficit')
        assert hasattr(stats, 'goal_achievement_rate')

        # 已有字段
        assert hasattr(stats, 'date')
        assert hasattr(stats, 'user_id')
        assert hasattr(stats, 'intake_calories')
        assert hasattr(stats, 'burn_calories')
        assert hasattr(stats, 'net_calories')
        assert hasattr(stats, 'meal_count')
        assert hasattr(stats, 'exercise_count')
        assert hasattr(stats, 'exercise_duration')
        assert hasattr(stats, 'meal_breakdown')

        print("✓ 所有字段验证通过")

    def test_stats_serialization(self, db_session, test_user, today):
        """测试统计数据可以正确序列化为JSON"""
        create_diet_records(db_session, test_user.id, today, [
            {"food_name": "午餐", "calories": 500.0},
        ])
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 200.0, "actual_duration": 30},
        ])

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)

        # 应该能序列化为dict
        stats_dict = stats.model_dump()
        assert isinstance(stats_dict, dict)
        assert 'planned_burn_calories' in stats_dict
        assert 'actual_burn_calories' in stats_dict
        assert 'calorie_deficit' in stats_dict
        assert 'goal_achievement_rate' in stats_dict

        print("✓ 序列化验证通过")

    def test_net_calories_backward_compat(self, db_session, test_user, today):
        """验证net_calories字段的向后兼容性"""
        create_diet_records(db_session, test_user.id, today, [
            {"food_name": "午餐", "calories": 800.0},
        ])
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 300.0, "actual_duration": 45},
        ])

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)

        # net_calories = intake - burn_calories（保持向后兼容）
        assert stats.net_calories == stats.intake_calories - stats.burn_calories

        # calorie_deficit 也等于 intake - burn_calories
        assert stats.calorie_deficit == stats.intake_calories - stats.burn_calories

        print("✓ 向后兼容性验证通过")


# ==================== 综合场景测试 ====================

class TestIntegrationScenarios:
    """综合业务场景测试"""

    def test_full_day_scenario(self, db_session, test_user, today):
        """完整的一天场景：三餐 + 计划 + 运动记录"""
        # 三餐饮食
        create_diet_records(db_session, test_user.id, today, [
            {"food_name": "燕麦粥", "calories": 250.0, "protein": 8.0, "fat": 3.0, "carbs": 40.0, "meal_type": "breakfast"},
            {"food_name": "鸡胸肉沙拉", "calories": 450.0, "protein": 35.0, "fat": 12.0, "carbs": 20.0, "meal_type": "lunch"},
            {"food_name": "清蒸鱼+米饭", "calories": 500.0, "protein": 30.0, "fat": 10.0, "carbs": 60.0, "meal_type": "dinner"},
            {"food_name": "酸奶", "calories": 100.0, "protein": 5.0, "fat": 2.0, "carbs": 12.0, "meal_type": "snack"},
        ])

        # 运动计划：餐后散步 + 晚间跑步
        trip = create_trip_plan(db_session, test_user.id, today, [
            {"cost": 150.0, "duration": 30, "place_type": "walking"},
            {"cost": 300.0, "duration": 30, "place_type": "running"},
        ])

        # 实际运动记录
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 130.0, "actual_duration": 28, "exercise_type": "walking",
             "planned_calories": 150.0, "planned_duration": 30},
            {"actual_calories": 320.0, "actual_duration": 32, "exercise_type": "running",
             "planned_calories": 300.0, "planned_duration": 30},
        ], plan_id=trip.id)

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)

        # 验证摄入
        assert stats.intake_calories == 1300.0  # 250+450+500+100
        assert stats.meal_count == 4

        # 验证计划消耗
        assert stats.planned_burn_calories == 450.0  # 150+300

        # 验证实际消耗
        assert stats.actual_burn_calories == 450.0  # 130+320

        # 验证有效消耗使用实际值
        assert stats.burn_calories == 450.0

        # 验证热量缺口
        assert stats.calorie_deficit == 850.0  # 1300-450

        # 验证达成率
        assert abs(stats.goal_achievement_rate - 100.0) < 0.1

        print("✓ 完整一天场景测试通过")

    def test_multi_day_tracking(self, db_session, test_user, today, yesterday):
        """多日跟踪场景"""
        # 昨天
        create_diet_records(db_session, test_user.id, yesterday, [
            {"food_name": "昨日午餐", "calories": 700.0},
        ])
        trip_y = create_trip_plan(db_session, test_user.id, yesterday, [
            {"cost": 200.0, "duration": 30},
        ])
        create_exercise_records(db_session, test_user.id, yesterday, [
            {"actual_calories": 180.0, "actual_duration": 28},
        ], plan_id=trip_y.id)

        # 今天
        create_diet_records(db_session, test_user.id, today, [
            {"food_name": "今日午餐", "calories": 800.0},
        ])
        trip_t = create_trip_plan(db_session, test_user.id, today, [
            {"cost": 300.0, "duration": 40},
        ])
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 350.0, "actual_duration": 45},
        ], plan_id=trip_t.id)

        # 验证昨天
        stats_y = stats_service.get_daily_calorie_stats(db_session, test_user.id, yesterday)
        assert stats_y.intake_calories == 700.0
        assert stats_y.actual_burn_calories == 180.0

        # 验证今天
        stats_t = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        assert stats_t.intake_calories == 800.0
        assert stats_t.actual_burn_calories == 350.0

        # 验证数据不会跨天混淆
        assert stats_y.actual_burn_calories != stats_t.actual_burn_calories

        print("✓ 多日跟踪场景测试通过")

    def test_reduce_fat_goal_scenario(self, db_session, test_user, today):
        """减脂目标场景：摄入少 + 运动多"""
        create_diet_records(db_session, test_user.id, today, [
            {"food_name": "低卡早餐", "calories": 200.0, "meal_type": "breakfast"},
            {"food_name": "低卡午餐", "calories": 350.0, "meal_type": "lunch"},
            {"food_name": "低卡晚餐", "calories": 250.0, "meal_type": "dinner"},
        ])

        trip = create_trip_plan(db_session, test_user.id, today, [
            {"cost": 400.0, "duration": 60},
        ])
        create_exercise_records(db_session, test_user.id, today, [
            {"actual_calories": 450.0, "actual_duration": 65},
        ], plan_id=trip.id)

        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)

        # 摄入800，消耗450，缺口350
        assert stats.intake_calories == 800.0
        assert stats.actual_burn_calories == 450.0
        assert stats.calorie_deficit == 350.0

        # 超额完成计划
        assert stats.goal_achievement_rate > 100.0

        print(f"✓ 减脂场景: 缺口={stats.calorie_deficit}, 达成率={stats.goal_achievement_rate}%")


# ==================== 主程序 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
