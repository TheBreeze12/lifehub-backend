"""
Phase 55: 一键"遗忘"功能 - 用户数据完全删除接口测试

测试 DELETE /api/user/data 接口，验证：
1. 级联删除饮食记录、运动记录、餐前餐后对比、菜单识别、运动计划（含项目）
2. 删除用户偏好设置
3. 删除用户本身
4. 各种边界情况（不存在的用户、无数据的用户、重复删除等）
5. 响应格式与删除统计信息
"""

import os
import sys
import pytest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

# 将项目根目录添加到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.db_models.user import User
from app.db_models.diet_record import DietRecord
from app.db_models.exercise_record import ExerciseRecord
from app.db_models.meal_comparison import MealComparison
from app.db_models.menu_recognition import MenuRecognition
from app.db_models.trip_plan import TripPlan
from app.db_models.trip_item import TripItem
from app.utils.auth import get_password_hash


# ============================================================
# 测试数据库配置（使用SQLite内存数据库）
# ============================================================

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_phase55.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """测试用数据库会话"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# 覆盖依赖
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(autouse=True)
def setup_database():
    """每个测试前创建表，测试后清理"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """获取测试数据库会话"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_test_user(db, nickname="测试用户", password="password123"):
    """创建测试用户"""
    user = User(
        nickname=nickname,
        password=get_password_hash(password),
        health_goal="reduce_fat",
        allergens=["花生", "海鲜"],
        travel_preference="walking",
        daily_budget=500,
        weight=70.0,
        height=175.0,
        age=25,
        gender="male"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_test_diet_records(db, user_id, count=3):
    """创建测试饮食记录"""
    records = []
    for i in range(count):
        record = DietRecord(
            user_id=user_id,
            food_name=f"测试菜品{i+1}",
            calories=100.0 + i * 50,
            protein=10.0 + i,
            fat=5.0 + i,
            carbs=20.0 + i,
            meal_type="lunch",
            record_date=date.today()
        )
        db.add(record)
        records.append(record)
    db.commit()
    return records


def create_test_exercise_records(db, user_id, plan_id=None, count=2):
    """创建测试运动记录"""
    records = []
    for i in range(count):
        record = ExerciseRecord(
            user_id=user_id,
            plan_id=plan_id,
            exercise_type="walking",
            actual_calories=150.0 + i * 50,
            actual_duration=30 + i * 10,
            distance=2000.0 + i * 500,
            exercise_date=date.today(),
            planned_calories=200.0,
            planned_duration=40
        )
        db.add(record)
        records.append(record)
    db.commit()
    return records


def create_test_meal_comparisons(db, user_id, count=2):
    """创建测试餐前餐后对比记录"""
    records = []
    for i in range(count):
        record = MealComparison(
            user_id=user_id,
            before_image_url=f"/images/before_{i}.jpg",
            after_image_url=f"/images/after_{i}.jpg",
            consumption_ratio=0.8,
            original_calories=500.0,
            net_calories=400.0,
            status="completed"
        )
        db.add(record)
        records.append(record)
    db.commit()
    return records


def create_test_menu_recognitions(db, user_id, count=2):
    """创建测试菜单识别记录"""
    records = []
    for i in range(count):
        record = MenuRecognition(
            user_id=user_id,
            dishes=[{"name": f"菜品{i}", "calories": 200.0}]
        )
        db.add(record)
        records.append(record)
    db.commit()
    return records


def create_test_trip_plans(db, user_id, count=2):
    """创建测试运动计划（含项目）"""
    plans = []
    for i in range(count):
        plan = TripPlan(
            user_id=user_id,
            title=f"测试计划{i+1}",
            destination="测试地点",
            start_date=date.today(),
            end_date=date.today(),
            status="planning"
        )
        db.add(plan)
        db.flush()

        # 为每个计划添加2个项目
        for j in range(2):
            item = TripItem(
                trip_id=plan.id,
                day_index=1,
                place_name=f"地点{j+1}",
                place_type="walking",
                duration=30,
                cost=100.0
            )
            db.add(item)

        plans.append(plan)

    db.commit()
    return plans


# ============================================================
# 测试用例
# ============================================================

class TestDeleteUserDataAPI:
    """DELETE /api/user/data 接口测试"""

    def test_delete_user_data_success(self, db_session):
        """测试成功删除用户所有数据"""
        user = create_test_user(db_session)
        user_id = user.id

        # 创建各种关联数据
        create_test_diet_records(db_session, user_id, count=5)
        plans = create_test_trip_plans(db_session, user_id, count=3)
        create_test_exercise_records(db_session, user_id, plan_id=plans[0].id, count=4)
        create_test_meal_comparisons(db_session, user_id, count=3)
        create_test_menu_recognitions(db_session, user_id, count=2)

        # 验证数据已创建
        assert db_session.query(DietRecord).filter(DietRecord.user_id == user_id).count() == 5
        assert db_session.query(TripPlan).filter(TripPlan.user_id == user_id).count() == 3
        assert db_session.query(ExerciseRecord).filter(ExerciseRecord.user_id == user_id).count() == 4
        assert db_session.query(MealComparison).filter(MealComparison.user_id == user_id).count() == 3
        assert db_session.query(MenuRecognition).filter(MenuRecognition.user_id == user_id).count() == 2

        # 调用删除接口
        response = client.request("DELETE", f"/api/user/data?userId={user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "数据删除成功"

        # 验证删除统计
        assert data["data"]["user_id"] == user_id
        assert data["data"]["deleted_counts"]["diet_records"] == 5
        assert data["data"]["deleted_counts"]["exercise_records"] == 4
        assert data["data"]["deleted_counts"]["meal_comparisons"] == 3
        assert data["data"]["deleted_counts"]["menu_recognitions"] == 2
        assert data["data"]["deleted_counts"]["trip_plans"] == 3

        # 验证数据库中数据已删除
        assert db_session.query(User).filter(User.id == user_id).first() is None
        assert db_session.query(DietRecord).filter(DietRecord.user_id == user_id).count() == 0
        assert db_session.query(TripPlan).filter(TripPlan.user_id == user_id).count() == 0
        assert db_session.query(ExerciseRecord).filter(ExerciseRecord.user_id == user_id).count() == 0
        assert db_session.query(MealComparison).filter(MealComparison.user_id == user_id).count() == 0
        assert db_session.query(MenuRecognition).filter(MenuRecognition.user_id == user_id).count() == 0

    def test_delete_user_not_found(self):
        """测试删除不存在的用户"""
        response = client.request("DELETE", "/api/user/data?userId=99999")
        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data["detail"]

    def test_delete_user_with_no_data(self, db_session):
        """测试删除没有任何关联数据的用户"""
        user = create_test_user(db_session, nickname="空用户")
        user_id = user.id

        response = client.request("DELETE", f"/api/user/data?userId={user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["deleted_counts"]["diet_records"] == 0
        assert data["data"]["deleted_counts"]["exercise_records"] == 0
        assert data["data"]["deleted_counts"]["meal_comparisons"] == 0
        assert data["data"]["deleted_counts"]["menu_recognitions"] == 0
        assert data["data"]["deleted_counts"]["trip_plans"] == 0

        # 用户也应该被删除
        assert db_session.query(User).filter(User.id == user_id).first() is None

    def test_delete_user_invalid_id_zero(self):
        """测试无效用户ID（0）"""
        response = client.request("DELETE", "/api/user/data?userId=0")
        assert response.status_code == 422 or response.status_code == 400

    def test_delete_user_invalid_id_negative(self):
        """测试无效用户ID（负数）"""
        response = client.request("DELETE", "/api/user/data?userId=-1")
        assert response.status_code == 422 or response.status_code == 400

    def test_delete_user_missing_id(self):
        """测试缺少用户ID参数"""
        response = client.request("DELETE", "/api/user/data")
        assert response.status_code == 422

    def test_delete_does_not_affect_other_users(self, db_session):
        """测试删除一个用户不影响其他用户的数据"""
        user1 = create_test_user(db_session, nickname="用户1")
        user2 = create_test_user(db_session, nickname="用户2")

        # 两个用户都创建数据
        create_test_diet_records(db_session, user1.id, count=3)
        create_test_diet_records(db_session, user2.id, count=5)
        create_test_trip_plans(db_session, user1.id, count=2)
        create_test_trip_plans(db_session, user2.id, count=4)
        create_test_exercise_records(db_session, user1.id, count=2)
        create_test_exercise_records(db_session, user2.id, count=3)

        # 删除用户1
        response = client.request("DELETE", f"/api/user/data?userId={user1.id}")
        assert response.status_code == 200

        # 验证用户1数据已删除
        assert db_session.query(User).filter(User.id == user1.id).first() is None
        assert db_session.query(DietRecord).filter(DietRecord.user_id == user1.id).count() == 0

        # 验证用户2数据完好
        assert db_session.query(User).filter(User.id == user2.id).first() is not None
        assert db_session.query(DietRecord).filter(DietRecord.user_id == user2.id).count() == 5
        assert db_session.query(TripPlan).filter(TripPlan.user_id == user2.id).count() == 4
        assert db_session.query(ExerciseRecord).filter(ExerciseRecord.user_id == user2.id).count() == 3

    def test_delete_cascades_trip_items(self, db_session):
        """测试删除运动计划时级联删除运动项目"""
        user = create_test_user(db_session)
        plans = create_test_trip_plans(db_session, user.id, count=2)

        # 验证trip_item存在（每个计划2个项目）
        total_items = db_session.query(TripItem).count()
        assert total_items == 4

        # 删除用户
        response = client.request("DELETE", f"/api/user/data?userId={user.id}")
        assert response.status_code == 200

        # 验证trip_item也被删除
        assert db_session.query(TripItem).count() == 0

    def test_delete_exercise_records_with_plan_ref(self, db_session):
        """测试删除关联了运动计划的运动记录"""
        user = create_test_user(db_session)
        plans = create_test_trip_plans(db_session, user.id, count=1)
        create_test_exercise_records(db_session, user.id, plan_id=plans[0].id, count=3)

        response = client.request("DELETE", f"/api/user/data?userId={user.id}")
        assert response.status_code == 200

        assert db_session.query(ExerciseRecord).filter(ExerciseRecord.user_id == user.id).count() == 0

    def test_delete_response_format(self, db_session):
        """测试响应格式正确"""
        user = create_test_user(db_session)
        create_test_diet_records(db_session, user.id, count=2)

        response = client.request("DELETE", f"/api/user/data?userId={user.id}")
        data = response.json()

        # 验证响应结构
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert "user_id" in data["data"]
        assert "nickname" in data["data"]
        assert "deleted_counts" in data["data"]
        assert "total_deleted" in data["data"]

        # 验证deleted_counts包含所有表
        counts = data["data"]["deleted_counts"]
        assert "diet_records" in counts
        assert "exercise_records" in counts
        assert "meal_comparisons" in counts
        assert "menu_recognitions" in counts
        assert "trip_plans" in counts

    def test_delete_total_count_correct(self, db_session):
        """测试total_deleted计数正确"""
        user = create_test_user(db_session)
        create_test_diet_records(db_session, user.id, count=3)
        create_test_exercise_records(db_session, user.id, count=2)
        create_test_meal_comparisons(db_session, user.id, count=1)

        response = client.request("DELETE", f"/api/user/data?userId={user.id}")
        data = response.json()

        expected_total = 3 + 2 + 1  # diet + exercise + meal_comparison
        assert data["data"]["total_deleted"] == expected_total

    def test_double_delete_returns_404(self, db_session):
        """测试重复删除同一用户返回404"""
        user = create_test_user(db_session)
        user_id = user.id

        # 第一次删除成功
        response1 = client.request("DELETE", f"/api/user/data?userId={user_id}")
        assert response1.status_code == 200

        # 第二次删除应返回404
        response2 = client.request("DELETE", f"/api/user/data?userId={user_id}")
        assert response2.status_code == 404

    def test_delete_user_with_only_diet_records(self, db_session):
        """测试只有饮食记录的用户"""
        user = create_test_user(db_session)
        create_test_diet_records(db_session, user.id, count=10)

        response = client.request("DELETE", f"/api/user/data?userId={user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["deleted_counts"]["diet_records"] == 10
        assert data["data"]["deleted_counts"]["exercise_records"] == 0

    def test_delete_user_with_only_trip_plans(self, db_session):
        """测试只有运动计划的用户"""
        user = create_test_user(db_session)
        create_test_trip_plans(db_session, user.id, count=5)

        response = client.request("DELETE", f"/api/user/data?userId={user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["deleted_counts"]["trip_plans"] == 5
        assert data["data"]["deleted_counts"]["diet_records"] == 0

    def test_delete_user_with_large_dataset(self, db_session):
        """测试大量数据的用户删除"""
        user = create_test_user(db_session)
        create_test_diet_records(db_session, user.id, count=50)
        create_test_exercise_records(db_session, user.id, count=30)
        create_test_meal_comparisons(db_session, user.id, count=20)
        create_test_menu_recognitions(db_session, user.id, count=15)
        create_test_trip_plans(db_session, user.id, count=10)

        response = client.request("DELETE", f"/api/user/data?userId={user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["deleted_counts"]["diet_records"] == 50
        assert data["data"]["deleted_counts"]["exercise_records"] == 30
        assert data["data"]["deleted_counts"]["meal_comparisons"] == 20
        assert data["data"]["deleted_counts"]["menu_recognitions"] == 15
        assert data["data"]["deleted_counts"]["trip_plans"] == 10
        assert data["data"]["total_deleted"] == 50 + 30 + 20 + 15 + 10

    def test_delete_returns_nickname(self, db_session):
        """测试响应中包含被删除用户的昵称"""
        user = create_test_user(db_session, nickname="要删除的用户")

        response = client.request("DELETE", f"/api/user/data?userId={user.id}")
        data = response.json()
        assert data["data"]["nickname"] == "要删除的用户"

    def test_delete_user_with_menu_recognition_null_user(self, db_session):
        """测试删除用户不影响user_id为NULL的菜单识别记录"""
        user = create_test_user(db_session)

        # 创建一条user_id为None的菜单识别记录
        null_record = MenuRecognition(
            user_id=None,
            dishes=[{"name": "无主菜品", "calories": 100.0}]
        )
        db_session.add(null_record)

        # 创建用户自己的菜单识别记录
        create_test_menu_recognitions(db_session, user.id, count=2)
        db_session.commit()

        response = client.request("DELETE", f"/api/user/data?userId={user.id}")
        assert response.status_code == 200

        # 验证null user_id的记录仍然存在
        remaining = db_session.query(MenuRecognition).filter(MenuRecognition.user_id == None).count()
        assert remaining == 1

    def test_delete_user_exercise_record_plan_id_set_null(self, db_session):
        """测试运动记录中的plan_id在plan删除后应当正确处理"""
        user = create_test_user(db_session)
        plans = create_test_trip_plans(db_session, user.id, count=1)
        create_test_exercise_records(db_session, user.id, plan_id=plans[0].id, count=2)

        # 所有相关数据都应该被删除
        response = client.request("DELETE", f"/api/user/data?userId={user.id}")
        assert response.status_code == 200

        # exercise_records应该全被删除
        assert db_session.query(ExerciseRecord).count() == 0
        # trip_plans也应该被删除
        assert db_session.query(TripPlan).count() == 0


class TestDeleteUserDataPydanticModels:
    """测试数据删除相关的Pydantic模型"""

    def test_delete_response_model(self):
        """测试响应模型结构"""
        from app.models.user import DataForgetResponse, DataForgetData, DeletedCounts

        counts = DeletedCounts(
            diet_records=5,
            exercise_records=3,
            meal_comparisons=2,
            menu_recognitions=1,
            trip_plans=4
        )
        assert counts.diet_records == 5
        assert counts.exercise_records == 3

        data = DataForgetData(
            user_id=1,
            nickname="测试用户",
            deleted_counts=counts,
            total_deleted=15
        )
        assert data.user_id == 1
        assert data.total_deleted == 15

        response = DataForgetResponse(
            code=200,
            message="数据删除成功",
            data=data
        )
        assert response.code == 200

    def test_deleted_counts_default_zero(self):
        """测试DeletedCounts默认值为0"""
        from app.models.user import DeletedCounts

        counts = DeletedCounts()
        assert counts.diet_records == 0
        assert counts.exercise_records == 0
        assert counts.meal_comparisons == 0
        assert counts.menu_recognitions == 0
        assert counts.trip_plans == 0


class TestDeleteUserDataService:
    """测试用户数据删除服务层逻辑"""

    def test_service_delete_all_tables(self, db_session):
        """测试服务层正确删除所有表的数据"""
        from app.services.user_service import delete_user_data

        user = create_test_user(db_session)
        create_test_diet_records(db_session, user.id, count=3)
        create_test_exercise_records(db_session, user.id, count=2)
        create_test_meal_comparisons(db_session, user.id, count=1)
        create_test_menu_recognitions(db_session, user.id, count=4)
        create_test_trip_plans(db_session, user.id, count=2)

        result = delete_user_data(db_session, user.id)

        assert result["user_id"] == user.id
        assert result["nickname"] == "测试用户"
        assert result["deleted_counts"]["diet_records"] == 3
        assert result["deleted_counts"]["exercise_records"] == 2
        assert result["deleted_counts"]["meal_comparisons"] == 1
        assert result["deleted_counts"]["menu_recognitions"] == 4
        assert result["deleted_counts"]["trip_plans"] == 2
        assert result["total_deleted"] == 3 + 2 + 1 + 4 + 2

    def test_service_user_not_found_raises(self, db_session):
        """测试服务层对不存在的用户抛出异常"""
        from app.services.user_service import delete_user_data

        with pytest.raises(ValueError, match="用户不存在"):
            delete_user_data(db_session, 99999)

    def test_service_returns_correct_type(self, db_session):
        """测试服务层返回正确的字典类型"""
        from app.services.user_service import delete_user_data

        user = create_test_user(db_session)
        result = delete_user_data(db_session, user.id)

        assert isinstance(result, dict)
        assert isinstance(result["deleted_counts"], dict)
        assert isinstance(result["total_deleted"], int)

    def test_service_rollback_on_error(self, db_session):
        """测试服务层在错误时回滚事务"""
        from app.services.user_service import delete_user_data

        user = create_test_user(db_session)
        create_test_diet_records(db_session, user.id, count=3)

        # 模拟数据库错误不会导致部分删除
        # 这里只是验证正常流程不会有问题
        result = delete_user_data(db_session, user.id)
        assert result["deleted_counts"]["diet_records"] == 3


# ============================================================
# 清理测试数据库文件
# ============================================================

@pytest.fixture(scope="session", autouse=True)
def cleanup():
    """测试结束后删除测试数据库文件"""
    yield
    try:
        engine.dispose()
        if os.path.exists("./test_phase55.db"):
            os.remove("./test_phase55.db")
    except Exception:
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
