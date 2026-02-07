"""Phase 16: 营养素统计功能测试

测试策略：
1. 直接测试服务层逻辑（避免异步HTTP测试的复杂性）
2. 使用内存数据库进行隔离测试
3. 覆盖核心业务场景

测试场景：
1. 正常场景 - 有饮食记录时计算营养素占比
2. 空数据场景 - 无饮食记录时返回零值
3. 边界场景 - 单一餐次、多餐次、营养素为零
4. 膳食指南对比 - 验证与建议值对比逻辑
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
        health_goal="balanced"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_date():
    """返回测试日期"""
    return date.today()


# ==================== 营养素统计服务测试 ====================

class TestNutrientStatsService:
    """营养素统计服务测试"""
    
    def test_daily_nutrients_with_records(self, db_session, test_user, test_date):
        """测试有饮食记录时的营养素统计"""
        # 准备测试数据 - 添加多条饮食记录
        records = [
            DietRecord(
                user_id=test_user.id,
                food_name="番茄炒蛋",
                calories=150.0,
                protein=10.5,
                fat=8.2,
                carbs=6.3,
                meal_type="breakfast",
                record_date=test_date
            ),
            DietRecord(
                user_id=test_user.id,
                food_name="红烧肉",
                calories=350.0,
                protein=20.0,
                fat=25.0,
                carbs=10.0,
                meal_type="lunch",
                record_date=test_date
            ),
            DietRecord(
                user_id=test_user.id,
                food_name="米饭",
                calories=230.0,
                protein=4.0,
                fat=0.5,
                carbs=50.0,
                meal_type="lunch",
                record_date=test_date
            ),
        ]
        for record in records:
            db_session.add(record)
        db_session.commit()
        
        # 调用服务
        stats = stats_service.get_daily_nutrient_stats(db_session, test_user.id, test_date)
        
        # 验证基本字段
        assert stats.date == test_date.isoformat()
        assert stats.user_id == test_user.id
        
        # 验证营养素总量
        # 蛋白质: 10.5 + 20.0 + 4.0 = 34.5g
        # 脂肪: 8.2 + 25.0 + 0.5 = 33.7g
        # 碳水: 6.3 + 10.0 + 50.0 = 66.3g
        assert abs(stats.total_protein - 34.5) < 0.1
        assert abs(stats.total_fat - 33.7) < 0.1
        assert abs(stats.total_carbs - 66.3) < 0.1
        
        # 验证总热量
        assert abs(stats.total_calories - 730.0) < 0.1
        
        # 验证营养素占比在合理范围内
        assert 0 <= stats.protein_ratio <= 100
        assert 0 <= stats.fat_ratio <= 100
        assert 0 <= stats.carbs_ratio <= 100
        
        # 验证与膳食指南对比存在
        assert stats.guidelines_comparison is not None
        
    def test_daily_nutrients_no_records(self, db_session, test_user, test_date):
        """测试无饮食记录时返回零值"""
        stats = stats_service.get_daily_nutrient_stats(db_session, test_user.id, test_date)
        
        assert stats.total_protein == 0.0
        assert stats.total_fat == 0.0
        assert stats.total_carbs == 0.0
        assert stats.total_calories == 0.0
        assert stats.protein_ratio == 0.0
        assert stats.fat_ratio == 0.0
        assert stats.carbs_ratio == 0.0
        assert stats.meal_count == 0
        
    def test_daily_nutrients_single_meal(self, db_session, test_user, test_date):
        """测试单一餐次的营养素统计"""
        record = DietRecord(
            user_id=test_user.id,
            food_name="沙拉",
            calories=100.0,
            protein=5.0,
            fat=2.0,
            carbs=15.0,
            meal_type="dinner",
            record_date=test_date
        )
        db_session.add(record)
        db_session.commit()
        
        stats = stats_service.get_daily_nutrient_stats(db_session, test_user.id, test_date)
        
        assert stats.total_protein == 5.0
        assert stats.total_fat == 2.0
        assert stats.total_carbs == 15.0
        assert stats.meal_count == 1
        
    def test_daily_nutrients_only_carbs(self, db_session, test_user, test_date):
        """测试只有碳水的情况"""
        record = DietRecord(
            user_id=test_user.id,
            food_name="白糖",
            calories=400.0,
            protein=0.0,
            fat=0.0,
            carbs=100.0,
            meal_type="snack",
            record_date=test_date
        )
        db_session.add(record)
        db_session.commit()
        
        stats = stats_service.get_daily_nutrient_stats(db_session, test_user.id, test_date)
        
        assert stats.total_protein == 0.0
        assert stats.total_fat == 0.0
        assert stats.total_carbs == 100.0
        assert stats.carbs_ratio == 100.0
        
    def test_guidelines_comparison_high_fat(self, db_session, test_user, test_date):
        """测试高脂肪饮食的膳食指南对比"""
        record = DietRecord(
            user_id=test_user.id,
            food_name="炸鸡",
            calories=500.0,
            protein=20.0,
            fat=40.0,
            carbs=15.0,
            meal_type="dinner",
            record_date=test_date
        )
        db_session.add(record)
        db_session.commit()
        
        stats = stats_service.get_daily_nutrient_stats(db_session, test_user.id, test_date)
        
        # 脂肪占比应该很高 (72%)
        assert stats.fat_ratio > 50
        assert stats.guidelines_comparison.fat.status == "high"
        
    def test_guidelines_comparison_low_protein(self, db_session, test_user, test_date):
        """测试低蛋白饮食的膳食指南对比"""
        record = DietRecord(
            user_id=test_user.id,
            food_name="白粥",
            calories=200.0,
            protein=2.0,
            fat=0.5,
            carbs=45.0,
            meal_type="breakfast",
            record_date=test_date
        )
        db_session.add(record)
        db_session.commit()
        
        stats = stats_service.get_daily_nutrient_stats(db_session, test_user.id, test_date)
        
        assert stats.guidelines_comparison.protein.status == "low"
        
    def test_different_dates_isolation(self, db_session, test_user):
        """测试不同日期的数据隔离"""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        record_today = DietRecord(
            user_id=test_user.id,
            food_name="今天",
            calories=500.0,
            protein=20.0,
            fat=15.0,
            carbs=60.0,
            meal_type="lunch",
            record_date=today
        )
        record_yesterday = DietRecord(
            user_id=test_user.id,
            food_name="昨天",
            calories=300.0,
            protein=10.0,
            fat=8.0,
            carbs=40.0,
            meal_type="lunch",
            record_date=yesterday
        )
        db_session.add_all([record_today, record_yesterday])
        db_session.commit()
        
        stats_today = stats_service.get_daily_nutrient_stats(db_session, test_user.id, today)
        stats_yesterday = stats_service.get_daily_nutrient_stats(db_session, test_user.id, yesterday)
        
        assert stats_today.total_calories == 500.0
        assert stats_yesterday.total_calories == 300.0
        
    def test_meal_breakdown(self, db_session, test_user, test_date):
        """测试按餐次的营养素分类统计"""
        records = [
            DietRecord(
                user_id=test_user.id,
                food_name="早餐",
                calories=300.0,
                protein=15.0,
                fat=10.0,
                carbs=35.0,
                meal_type="breakfast",
                record_date=test_date
            ),
            DietRecord(
                user_id=test_user.id,
                food_name="午餐",
                calories=600.0,
                protein=30.0,
                fat=20.0,
                carbs=70.0,
                meal_type="lunch",
                record_date=test_date
            ),
        ]
        for record in records:
            db_session.add(record)
        db_session.commit()
        
        stats = stats_service.get_daily_nutrient_stats(db_session, test_user.id, test_date)
        
        assert stats.meal_count == 2
        if stats.meal_breakdown:
            assert "breakfast" in stats.meal_breakdown
            assert "lunch" in stats.meal_breakdown


class TestNutrientCalculation:
    """营养素计算逻辑测试（单元测试）"""
    
    def test_ratio_calculation_formula(self):
        """测试营养素占比计算公式"""
        PROTEIN_KCAL_PER_GRAM = 4
        FAT_KCAL_PER_GRAM = 9
        CARBS_KCAL_PER_GRAM = 4
        
        protein = 50.0
        fat = 30.0
        carbs = 100.0
        
        protein_kcal = protein * PROTEIN_KCAL_PER_GRAM
        fat_kcal = fat * FAT_KCAL_PER_GRAM
        carbs_kcal = carbs * CARBS_KCAL_PER_GRAM
        
        total_nutrient_kcal = protein_kcal + fat_kcal + carbs_kcal
        
        protein_ratio = (protein_kcal / total_nutrient_kcal) * 100
        fat_ratio = (fat_kcal / total_nutrient_kcal) * 100
        carbs_ratio = (carbs_kcal / total_nutrient_kcal) * 100
        
        # 验证占比总和接近100%
        assert abs(protein_ratio + fat_ratio + carbs_ratio - 100) < 0.01
        
    def test_guidelines_ranges(self):
        """测试膳食指南建议范围"""
        guidelines = {
            "protein": {"min": 10, "max": 15},
            "fat": {"min": 20, "max": 30},
            "carbs": {"min": 50, "max": 65},
        }
        
        for nutrient, range_val in guidelines.items():
            assert range_val["min"] < range_val["max"]
            assert range_val["min"] >= 0
            assert range_val["max"] <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
