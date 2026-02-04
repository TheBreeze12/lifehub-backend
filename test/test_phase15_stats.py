"""
Phase 15 测试文件: 热量收支统计功能测试

测试策略：
1. 直接测试服务层逻辑（避免异步HTTP测试的复杂性）
2. 使用内存数据库进行隔离测试
3. 覆盖核心业务场景

测试场景：
- 有饮食记录和运动计划的用户
- 没有记录的用户
- 热量计算精度
- 边界条件
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
def test_diet_records(db_session, test_user):
    """创建测试饮食记录"""
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    records = [
        DietRecord(
            user_id=test_user.id,
            food_name="早餐-燕麦粥",
            calories=200.0,
            protein=8.0,
            fat=3.0,
            carbs=35.0,
            meal_type="breakfast",
            record_date=today
        ),
        DietRecord(
            user_id=test_user.id,
            food_name="午餐-鸡胸肉沙拉",
            calories=350.0,
            protein=35.0,
            fat=12.0,
            carbs=15.0,
            meal_type="lunch",
            record_date=today
        ),
        DietRecord(
            user_id=test_user.id,
            food_name="晚餐-清蒸鱼",
            calories=280.0,
            protein=30.0,
            fat=8.0,
            carbs=10.0,
            meal_type="dinner",
            record_date=today
        ),
        DietRecord(
            user_id=test_user.id,
            food_name="昨日午餐",
            calories=500.0,
            protein=25.0,
            fat=20.0,
            carbs=45.0,
            meal_type="lunch",
            record_date=yesterday
        ),
    ]
    
    for record in records:
        db_session.add(record)
    db_session.commit()
    return records


@pytest.fixture
def test_trip_plans(db_session, test_user):
    """创建测试运动计划"""
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    # 今天的运动计划
    trip1 = TripPlan(
        user_id=test_user.id,
        title="餐后散步",
        destination="附近公园",
        start_date=today,
        end_date=today,
        status="done"
    )
    db_session.add(trip1)
    db_session.commit()
    
    item1 = TripItem(
        trip_id=trip1.id,
        day_index=1,
        place_name="公园",
        place_type="walking",
        duration=30,
        cost=150.0,
        notes="餐后慢走"
    )
    item2 = TripItem(
        trip_id=trip1.id,
        day_index=1,
        place_name="健身区",
        place_type="outdoor",
        duration=20,
        cost=100.0,
        notes="拉伸运动"
    )
    db_session.add(item1)
    db_session.add(item2)
    
    # 昨天的运动计划
    trip2 = TripPlan(
        user_id=test_user.id,
        title="昨日跑步",
        destination="体育场",
        start_date=yesterday,
        end_date=yesterday,
        status="done"
    )
    db_session.add(trip2)
    db_session.commit()
    
    item3 = TripItem(
        trip_id=trip2.id,
        day_index=1,
        place_name="跑道",
        place_type="running",
        duration=40,
        cost=300.0,
        notes="慢跑"
    )
    db_session.add(item3)
    db_session.commit()
    
    return [trip1, trip2]


# ==================== 每日统计服务测试 ====================

class TestDailyCalorieStatsService:
    """每日热量统计服务测试"""
    
    def test_daily_stats_with_data(self, db_session, test_user, test_diet_records, test_trip_plans):
        """测试有数据的情况"""
        today = date.today()
        
        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        
        # 验证摄入热量 (200 + 350 + 280 = 830)
        assert stats.intake_calories == 830.0
        
        # 验证消耗热量 (150 + 100 = 250)
        assert stats.burn_calories == 250.0
        
        # 验证净热量
        assert stats.net_calories == 830.0 - 250.0
        
        # 验证日期
        assert stats.date == today.isoformat()
        
        # 验证统计详情
        assert stats.meal_count == 3
        assert stats.exercise_count == 2
        
        print(f"✓ 每日统计测试通过: 摄入={stats.intake_calories}, 消耗={stats.burn_calories}, 净={stats.net_calories}")
    
    def test_daily_stats_no_data(self, db_session, test_user):
        """测试没有数据的情况"""
        future_date = date.today() + timedelta(days=30)
        
        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, future_date)
        
        # 无数据时应返回0
        assert stats.intake_calories == 0.0
        assert stats.burn_calories == 0.0
        assert stats.net_calories == 0.0
        assert stats.meal_count == 0
        assert stats.exercise_count == 0
        
        print("✓ 空数据测试通过")
    
    def test_daily_stats_yesterday(self, db_session, test_user, test_diet_records, test_trip_plans):
        """测试昨天的数据"""
        yesterday = date.today() - timedelta(days=1)
        
        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, yesterday)
        
        # 昨天摄入 500
        assert stats.intake_calories == 500.0
        
        # 昨天消耗 300
        assert stats.burn_calories == 300.0
        
        # 昨天净热量
        assert stats.net_calories == 500.0 - 300.0
        
        print(f"✓ 昨日统计测试通过: 摄入={stats.intake_calories}, 消耗={stats.burn_calories}")


# ==================== 每周统计服务测试 ====================

class TestWeeklyCalorieStatsService:
    """每周热量统计服务测试"""
    
    def test_weekly_stats_with_data(self, db_session, test_user, test_diet_records, test_trip_plans):
        """测试有数据的每周统计"""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        
        stats = stats_service.get_weekly_calorie_stats(db_session, test_user.id, week_start)
        
        # 验证周起止日期
        assert stats.week_start == week_start.isoformat()
        assert stats.week_end == (week_start + timedelta(days=6)).isoformat()
        
        # 验证总摄入 >= 0
        assert stats.total_intake >= 0
        
        # 验证总消耗 >= 0
        assert stats.total_burn >= 0
        
        # 验证每日明细有7天
        assert len(stats.daily_breakdown) == 7
        
        # 验证平均值字段存在
        assert stats.avg_intake >= 0
        assert stats.avg_burn >= 0
        
        print(f"✓ 每周统计测试通过: 总摄入={stats.total_intake}, 总消耗={stats.total_burn}")
    
    def test_weekly_stats_no_data(self, db_session, test_user):
        """测试没有数据的周"""
        future_week = date.today() + timedelta(days=60)
        week_start = future_week - timedelta(days=future_week.weekday())
        
        stats = stats_service.get_weekly_calorie_stats(db_session, test_user.id, week_start)
        
        assert stats.total_intake == 0.0
        assert stats.total_burn == 0.0
        assert stats.active_days == 0
        
        print("✓ 空周统计测试通过")
    
    def test_weekly_breakdown_structure(self, db_session, test_user, test_diet_records, test_trip_plans):
        """测试每日明细结构"""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        
        stats = stats_service.get_weekly_calorie_stats(db_session, test_user.id, week_start)
        
        for daily in stats.daily_breakdown:
            # 每日明细应有正确的字段
            assert hasattr(daily, 'date')
            assert hasattr(daily, 'intake_calories')
            assert hasattr(daily, 'burn_calories')
            assert hasattr(daily, 'net_calories')
            
            # 净热量 = 摄入 - 消耗
            assert daily.net_calories == daily.intake_calories - daily.burn_calories
        
        print("✓ 每日明细结构测试通过")


# ==================== 热量计算精度测试 ====================

class TestCalorieCalculationAccuracy:
    """热量计算精度测试"""
    
    def test_precise_calorie_sum(self, db_session, test_user):
        """测试精确数值的热量计算"""
        today = date.today()
        
        records = [
            DietRecord(
                user_id=test_user.id,
                food_name="测试食物1",
                calories=123.45,
                protein=10.0,
                fat=5.0,
                carbs=15.0,
                meal_type="breakfast",
                record_date=today
            ),
            DietRecord(
                user_id=test_user.id,
                food_name="测试食物2",
                calories=67.89,
                protein=5.0,
                fat=2.0,
                carbs=10.0,
                meal_type="lunch",
                record_date=today
            ),
        ]
        
        for record in records:
            db_session.add(record)
        db_session.commit()
        
        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        
        # 验证精确计算 (123.45 + 67.89 = 191.34)
        expected_intake = 123.45 + 67.89
        assert abs(stats.intake_calories - expected_intake) < 0.01
        
        print(f"✓ 精确计算测试通过: 预期={expected_intake}, 实际={stats.intake_calories}")
    
    def test_meal_breakdown(self, db_session, test_user):
        """测试餐次分类统计"""
        today = date.today()
        
        records = [
            DietRecord(user_id=test_user.id, food_name="早餐", calories=200.0, 
                      meal_type="breakfast", record_date=today, protein=0, fat=0, carbs=0),
            DietRecord(user_id=test_user.id, food_name="午餐", calories=400.0, 
                      meal_type="lunch", record_date=today, protein=0, fat=0, carbs=0),
            DietRecord(user_id=test_user.id, food_name="晚餐", calories=350.0, 
                      meal_type="dinner", record_date=today, protein=0, fat=0, carbs=0),
            DietRecord(user_id=test_user.id, food_name="加餐", calories=100.0, 
                      meal_type="snack", record_date=today, protein=0, fat=0, carbs=0),
        ]
        
        for record in records:
            db_session.add(record)
        db_session.commit()
        
        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        
        # 验证总热量
        assert stats.intake_calories == 200.0 + 400.0 + 350.0 + 100.0
        assert stats.meal_count == 4
        
        # 验证餐次分类
        if stats.meal_breakdown:
            assert stats.meal_breakdown["breakfast"] == 200.0
            assert stats.meal_breakdown["lunch"] == 400.0
            assert stats.meal_breakdown["dinner"] == 350.0
            assert stats.meal_breakdown["snack"] == 100.0
        
        print(f"✓ 餐次分类测试通过: 总热量={stats.intake_calories}")
    
    def test_exercise_burn_sum(self, db_session, test_user):
        """测试运动消耗热量计算"""
        today = date.today()
        
        trip = TripPlan(
            user_id=test_user.id,
            title="综合运动",
            destination="健身房",
            start_date=today,
            end_date=today,
            status="done"
        )
        db_session.add(trip)
        db_session.commit()
        
        items = [
            TripItem(trip_id=trip.id, day_index=1, place_name="跑步机",
                    place_type="running", duration=30, cost=200.0),
            TripItem(trip_id=trip.id, day_index=1, place_name="椭圆机",
                    place_type="cycling", duration=20, cost=150.0),
            TripItem(trip_id=trip.id, day_index=1, place_name="拉伸区",
                    place_type="indoor", duration=10, cost=50.0),
        ]
        
        for item in items:
            db_session.add(item)
        db_session.commit()
        
        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        
        # 验证总消耗
        assert stats.burn_calories == 200.0 + 150.0 + 50.0
        assert stats.exercise_count == 3
        assert stats.exercise_duration == 30 + 20 + 10
        
        print(f"✓ 运动消耗测试通过: 总消耗={stats.burn_calories}")


# ==================== 边界条件测试 ====================

class TestBoundaryConditions:
    """边界条件测试"""
    
    def test_zero_calories(self, db_session, test_user):
        """测试零热量记录"""
        today = date.today()
        
        record = DietRecord(
            user_id=test_user.id,
            food_name="水",
            calories=0.0,
            protein=0.0,
            fat=0.0,
            carbs=0.0,
            meal_type="snack",
            record_date=today
        )
        db_session.add(record)
        db_session.commit()
        
        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        
        assert stats.intake_calories == 0.0
        assert stats.meal_count == 1
        
        print("✓ 零热量记录测试通过")
    
    def test_large_calorie_values(self, db_session, test_user):
        """测试大数值热量"""
        today = date.today()
        
        record = DietRecord(
            user_id=test_user.id,
            food_name="自助餐",
            calories=5000.0,
            protein=200.0,
            fat=250.0,
            carbs=400.0,
            meal_type="dinner",
            record_date=today
        )
        db_session.add(record)
        db_session.commit()
        
        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        
        assert stats.intake_calories == 5000.0
        
        print("✓ 大数值热量测试通过")
    
    def test_negative_net_calories(self, db_session, test_user):
        """测试净热量为负（消耗大于摄入）"""
        today = date.today()
        
        # 少量摄入
        record = DietRecord(
            user_id=test_user.id,
            food_name="苹果",
            calories=100.0,
            protein=0.5,
            fat=0.3,
            carbs=25.0,
            meal_type="snack",
            record_date=today
        )
        db_session.add(record)
        
        # 大量运动
        trip = TripPlan(
            user_id=test_user.id,
            title="马拉松",
            destination="城市",
            start_date=today,
            end_date=today,
            status="done"
        )
        db_session.add(trip)
        db_session.commit()
        
        item = TripItem(
            trip_id=trip.id,
            day_index=1,
            place_name="马拉松路线",
            place_type="running",
            duration=240,
            cost=2500.0
        )
        db_session.add(item)
        db_session.commit()
        
        stats = stats_service.get_daily_calorie_stats(db_session, test_user.id, today)
        
        # 净热量应为负值
        assert stats.net_calories == 100.0 - 2500.0
        assert stats.net_calories < 0
        
        print(f"✓ 负净热量测试通过: 净热量={stats.net_calories}")
    
    def test_nonexistent_user(self, db_session):
        """测试不存在的用户"""
        today = date.today()
        
        stats = stats_service.get_daily_calorie_stats(db_session, 99999, today)
        
        # 不存在的用户应返回空数据
        assert stats.intake_calories == 0.0
        assert stats.burn_calories == 0.0
        
        print("✓ 不存在用户测试通过")


# ==================== 主程序 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
