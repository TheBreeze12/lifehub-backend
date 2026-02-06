"""
Phase 25 测试文件: 运动记录数据模型与接口测试

测试策略：
1. 使用SQLite内存数据库进行隔离测试（避免依赖MySQL）
2. 直接测试路由层逻辑（通过FastAPI TestClient）
3. 覆盖核心业务场景和边缘情况

测试场景：
- 数据模型字段完整性
- 新增运动记录（正常、各种参数组合）
- 查询运动记录列表（筛选、分页、排序）
- 查询单条记录详情
- 删除运动记录
- 权限校验（只能操作自己的记录）
- 关联运动计划的验证
- 达成率计算
- 输入验证与错误处理（无效日期、不存在的用户、无效运动类型等）
- 边缘情况（零值、极大值、空列表等）
"""
import pytest
import sys
import os
import json
from datetime import date, datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.db_models.user import User
from app.db_models.exercise_record import ExerciseRecord
from app.db_models.trip_plan import TripPlan
from app.db_models.trip_item import TripItem


# ==================== 测试数据库配置 ====================

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """覆盖数据库依赖"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# 覆盖FastAPI的数据库依赖
app.dependency_overrides[get_db] = override_get_db

# 创建测试客户端
client = TestClient(app)


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
        password="test_password_hash",
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
def test_user2(db_session):
    """创建第二个测试用户（用于权限测试）"""
    user = User(
        id=2,
        nickname="另一用户",
        password="test_password_hash2",
        health_goal="gain_muscle",
        weight=80.0,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_plan(db_session, test_user):
    """创建测试运动计划"""
    plan = TripPlan(
        id=1,
        user_id=test_user.id,
        title="测试运动计划",
        destination="附近公园",
        start_date=date.today(),
        end_date=date.today(),
        status="planning"
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


@pytest.fixture
def test_plan_items(db_session, test_plan):
    """创建测试运动计划节点"""
    items = [
        TripItem(
            trip_id=test_plan.id,
            day_index=1,
            place_name="公园入口",
            place_type="walking",
            duration=20,
            cost=100.0,  # 100kcal
            sort_order=0
        ),
        TripItem(
            trip_id=test_plan.id,
            day_index=1,
            place_name="公园跑道",
            place_type="running",
            duration=15,
            cost=200.0,  # 200kcal
            sort_order=1
        ),
    ]
    for item in items:
        db_session.add(item)
    db_session.commit()
    return items


@pytest.fixture
def test_plan_user2(db_session, test_user2):
    """创建另一用户的运动计划"""
    plan = TripPlan(
        id=2,
        user_id=test_user2.id,
        title="他人的运动计划",
        destination="其他地点",
        start_date=date.today(),
        end_date=date.today(),
        status="planning"
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


@pytest.fixture
def test_exercise_record(db_session, test_user, test_plan):
    """创建测试运动记录"""
    record = ExerciseRecord(
        user_id=test_user.id,
        plan_id=test_plan.id,
        exercise_type="running",
        actual_calories=280.0,
        actual_duration=35,
        distance=4500.0,
        planned_calories=300.0,
        planned_duration=30,
        exercise_date=date.today(),
        started_at=datetime.now().replace(hour=18, minute=0, second=0, microsecond=0),
        ended_at=datetime.now().replace(hour=18, minute=35, second=0, microsecond=0),
        notes="测试运动记录"
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


# ==================== 数据模型测试 ====================

class TestExerciseRecordModel:
    """测试ExerciseRecord数据模型"""

    def test_model_creation(self, db_session, test_user):
        """测试基本模型创建"""
        record = ExerciseRecord(
            user_id=test_user.id,
            exercise_type="walking",
            actual_calories=150.0,
            actual_duration=30,
            exercise_date=date.today(),
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        assert record.id is not None
        assert record.user_id == test_user.id
        assert record.exercise_type == "walking"
        assert record.actual_calories == 150.0
        assert record.actual_duration == 30
        assert record.exercise_date == date.today()
        assert record.created_at is not None

    def test_model_all_fields(self, db_session, test_user, test_plan):
        """测试所有字段都能正确保存"""
        now = datetime.now()
        record = ExerciseRecord(
            user_id=test_user.id,
            plan_id=test_plan.id,
            exercise_type="cycling",
            actual_calories=350.5,
            actual_duration=45,
            distance=12000.0,
            route_data='[{"lat":39.9,"lng":116.4}]',
            planned_calories=400.0,
            planned_duration=50,
            exercise_date=date.today(),
            started_at=now,
            ended_at=now + timedelta(minutes=45),
            notes="骑行测试",
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        assert record.plan_id == test_plan.id
        assert record.exercise_type == "cycling"
        assert record.actual_calories == 350.5
        assert record.distance == 12000.0
        assert record.route_data == '[{"lat":39.9,"lng":116.4}]'
        assert record.planned_calories == 400.0
        assert record.planned_duration == 50
        assert record.notes == "骑行测试"

    def test_model_nullable_fields(self, db_session, test_user):
        """测试可选字段可以为空"""
        record = ExerciseRecord(
            user_id=test_user.id,
            exercise_type="walking",
            actual_calories=100.0,
            actual_duration=20,
            exercise_date=date.today(),
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        assert record.plan_id is None
        assert record.distance is None
        assert record.route_data is None
        assert record.planned_calories is None
        assert record.planned_duration is None
        assert record.started_at is None
        assert record.ended_at is None
        assert record.notes is None

    def test_model_user_relationship(self, db_session, test_user):
        """测试与用户的关联关系"""
        record = ExerciseRecord(
            user_id=test_user.id,
            exercise_type="walking",
            actual_calories=100.0,
            actual_duration=20,
            exercise_date=date.today(),
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        assert record.user is not None
        assert record.user.id == test_user.id
        assert record.user.nickname == "测试用户"

    def test_model_plan_relationship(self, db_session, test_user, test_plan):
        """测试与运动计划的关联关系"""
        record = ExerciseRecord(
            user_id=test_user.id,
            plan_id=test_plan.id,
            exercise_type="walking",
            actual_calories=100.0,
            actual_duration=20,
            exercise_date=date.today(),
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        assert record.plan is not None
        assert record.plan.id == test_plan.id
        assert record.plan.title == "测试运动计划"

    def test_model_repr(self, db_session, test_user):
        """测试__repr__方法"""
        record = ExerciseRecord(
            user_id=test_user.id,
            exercise_type="running",
            actual_calories=200.0,
            actual_duration=25,
            exercise_date=date.today(),
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        repr_str = repr(record)
        assert "ExerciseRecord" in repr_str
        assert str(record.id) in repr_str


# ==================== 创建运动记录API测试 ====================

class TestCreateExerciseRecord:
    """测试 POST /api/exercise/record"""

    def test_create_minimal_record(self, test_user):
        """测试最小必填字段创建记录"""
        response = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "exercise_type": "walking",
            "actual_calories": 150.0,
            "actual_duration": 30,
            "exercise_date": date.today().isoformat(),
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "运动记录添加成功"
        assert data["data"]["user_id"] == test_user.id
        assert data["data"]["exercise_type"] == "walking"
        assert data["data"]["actual_calories"] == 150.0
        assert data["data"]["actual_duration"] == 30
        assert data["data"]["id"] is not None

    def test_create_full_record(self, test_user, test_plan, test_plan_items):
        """测试所有字段创建记录"""
        today = date.today().isoformat()
        response = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "plan_id": test_plan.id,
            "exercise_type": "running",
            "actual_calories": 280.0,
            "actual_duration": 35,
            "distance": 4500.0,
            "route_data": json.dumps([{"lat": 39.9, "lng": 116.4}]),
            "planned_calories": 300.0,
            "planned_duration": 30,
            "exercise_date": today,
            "started_at": f"{today}T18:00:00",
            "ended_at": f"{today}T18:35:00",
            "notes": "沿河跑步",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        record = data["data"]
        assert record["plan_id"] == test_plan.id
        assert record["exercise_type"] == "running"
        assert record["actual_calories"] == 280.0
        assert record["actual_duration"] == 35
        assert record["distance"] == 4500.0
        assert record["planned_calories"] == 300.0
        assert record["planned_duration"] == 30
        assert record["notes"] == "沿河跑步"

    def test_create_record_auto_fill_plan_data(self, test_user, test_plan, test_plan_items):
        """测试关联计划时自动填充计划数据"""
        response = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "plan_id": test_plan.id,
            "exercise_type": "walking",
            "actual_calories": 250.0,
            "actual_duration": 30,
            "exercise_date": date.today().isoformat(),
        })
        assert response.status_code == 200
        data = response.json()
        record = data["data"]
        # 应自动从计划项读取planned_calories(100+200=300)和planned_duration(20+15=35)
        assert record["planned_calories"] == 300.0
        assert record["planned_duration"] == 35

    def test_create_record_calories_achievement(self, test_user):
        """测试热量达成率计算"""
        response = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "exercise_type": "running",
            "actual_calories": 280.0,
            "actual_duration": 35,
            "planned_calories": 300.0,
            "planned_duration": 30,
            "exercise_date": date.today().isoformat(),
        })
        assert response.status_code == 200
        record = response.json()["data"]
        # 热量达成率: 280/300*100 = 93.3%
        assert record["calories_achievement"] == 93.3
        # 时长达成率: 35/30*100 = 116.7%
        assert record["duration_achievement"] == 116.7

    def test_create_record_no_planned_no_achievement(self, test_user):
        """测试没有计划数据时达成率为None"""
        response = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "exercise_type": "walking",
            "actual_calories": 150.0,
            "actual_duration": 30,
            "exercise_date": date.today().isoformat(),
        })
        assert response.status_code == 200
        record = response.json()["data"]
        assert record["calories_achievement"] is None
        assert record["duration_achievement"] is None

    def test_create_record_user_not_found(self):
        """测试用户不存在"""
        response = client.post("/api/exercise/record", json={
            "user_id": 9999,
            "exercise_type": "walking",
            "actual_calories": 100.0,
            "actual_duration": 20,
            "exercise_date": date.today().isoformat(),
        })
        assert response.status_code == 404
        assert "用户不存在" in response.json()["detail"]

    def test_create_record_invalid_exercise_type(self, test_user):
        """测试无效运动类型"""
        response = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "exercise_type": "skateboarding",
            "actual_calories": 100.0,
            "actual_duration": 20,
            "exercise_date": date.today().isoformat(),
        })
        assert response.status_code == 400
        assert "不支持的运动类型" in response.json()["detail"]

    def test_create_record_invalid_date_format(self, test_user):
        """测试无效日期格式"""
        response = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "exercise_type": "walking",
            "actual_calories": 100.0,
            "actual_duration": 20,
            "exercise_date": "2026/02/06",
        })
        assert response.status_code == 400
        assert "日期格式错误" in response.json()["detail"]

    def test_create_record_plan_not_found(self, test_user):
        """测试关联不存在的计划"""
        response = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "plan_id": 9999,
            "exercise_type": "walking",
            "actual_calories": 100.0,
            "actual_duration": 20,
            "exercise_date": date.today().isoformat(),
        })
        assert response.status_code == 404
        assert "运动计划不存在" in response.json()["detail"]

    def test_create_record_plan_ownership(self, test_user, test_user2, test_plan_user2):
        """测试不能关联他人的运动计划"""
        response = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "plan_id": test_plan_user2.id,
            "exercise_type": "walking",
            "actual_calories": 100.0,
            "actual_duration": 20,
            "exercise_date": date.today().isoformat(),
        })
        assert response.status_code == 403
        assert "无权关联" in response.json()["detail"]

    def test_create_record_invalid_time_order(self, test_user):
        """测试结束时间早于开始时间"""
        today = date.today().isoformat()
        response = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "exercise_type": "walking",
            "actual_calories": 100.0,
            "actual_duration": 20,
            "exercise_date": today,
            "started_at": f"{today}T19:00:00",
            "ended_at": f"{today}T18:00:00",
        })
        assert response.status_code == 400
        assert "结束时间必须晚于开始时间" in response.json()["detail"]

    def test_create_record_invalid_started_at_format(self, test_user):
        """测试无效的开始时间格式"""
        response = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "exercise_type": "walking",
            "actual_calories": 100.0,
            "actual_duration": 20,
            "exercise_date": date.today().isoformat(),
            "started_at": "invalid-time",
        })
        assert response.status_code == 400
        assert "开始时间格式错误" in response.json()["detail"]

    def test_create_record_invalid_ended_at_format(self, test_user):
        """测试无效的结束时间格式"""
        today = date.today().isoformat()
        response = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "exercise_type": "walking",
            "actual_calories": 100.0,
            "actual_duration": 20,
            "exercise_date": today,
            "started_at": f"{today}T18:00:00",
            "ended_at": "not-a-time",
        })
        assert response.status_code == 400
        assert "结束时间格式错误" in response.json()["detail"]

    def test_create_record_zero_calories(self, test_user):
        """测试零热量记录（边缘情况，如短暂运动）"""
        response = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "exercise_type": "walking",
            "actual_calories": 0.0,
            "actual_duration": 1,
            "exercise_date": date.today().isoformat(),
        })
        assert response.status_code == 200
        assert response.json()["data"]["actual_calories"] == 0.0

    def test_create_record_large_values(self, test_user):
        """测试较大的数值（长距离运动）"""
        response = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "exercise_type": "cycling",
            "actual_calories": 5000.0,
            "actual_duration": 480,
            "distance": 150000.0,
            "exercise_date": date.today().isoformat(),
        })
        assert response.status_code == 200
        record = response.json()["data"]
        assert record["actual_calories"] == 5000.0
        assert record["actual_duration"] == 480
        assert record["distance"] == 150000.0

    def test_create_record_all_exercise_types(self, test_user):
        """测试所有支持的运动类型"""
        valid_types = [
            "walking", "running", "cycling", "jogging", "hiking",
            "swimming", "gym", "indoor", "outdoor"
        ]
        for ex_type in valid_types:
            response = client.post("/api/exercise/record", json={
                "user_id": test_user.id,
                "exercise_type": ex_type,
                "actual_calories": 100.0,
                "actual_duration": 20,
                "exercise_date": date.today().isoformat(),
            })
            assert response.status_code == 200, f"运动类型 {ex_type} 创建失败"
            assert response.json()["data"]["exercise_type"] == ex_type

    def test_create_record_negative_calories_rejected(self, test_user):
        """测试负数热量被Pydantic拒绝"""
        response = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "exercise_type": "walking",
            "actual_calories": -10.0,
            "actual_duration": 20,
            "exercise_date": date.today().isoformat(),
        })
        assert response.status_code == 422  # Pydantic验证错误

    def test_create_record_zero_duration_rejected(self, test_user):
        """测试零时长被Pydantic拒绝（最小1分钟）"""
        response = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "exercise_type": "walking",
            "actual_calories": 100.0,
            "actual_duration": 0,
            "exercise_date": date.today().isoformat(),
        })
        assert response.status_code == 422

    def test_create_record_missing_required_field(self, test_user):
        """测试缺少必填字段"""
        # 缺少actual_calories
        response = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "exercise_type": "walking",
            "actual_duration": 20,
            "exercise_date": date.today().isoformat(),
        })
        assert response.status_code == 422


# ==================== 查询运动记录列表API测试 ====================

class TestGetExerciseRecords:
    """测试 GET /api/exercise/records"""

    def test_get_records_empty(self, test_user):
        """测试没有记录时返回空列表"""
        response = client.get(f"/api/exercise/records?userId={test_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"] == []
        assert data["total"] == 0

    def test_get_records_basic(self, test_user, test_exercise_record):
        """测试基本查询"""
        response = client.get(f"/api/exercise/records?userId={test_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]) == 1
        assert data["total"] == 1
        assert data["data"][0]["id"] == test_exercise_record.id

    def test_get_records_filter_by_date(self, test_user, db_session):
        """测试按日期筛选"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # 创建两条不同日期的记录
        r1 = ExerciseRecord(
            user_id=test_user.id, exercise_type="walking",
            actual_calories=100.0, actual_duration=20,
            exercise_date=today,
        )
        r2 = ExerciseRecord(
            user_id=test_user.id, exercise_type="running",
            actual_calories=200.0, actual_duration=30,
            exercise_date=yesterday,
        )
        db_session.add_all([r1, r2])
        db_session.commit()

        # 筛选今天
        response = client.get(
            f"/api/exercise/records?userId={test_user.id}&exercise_date={today.isoformat()}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["data"][0]["exercise_type"] == "walking"

        # 筛选昨天
        response = client.get(
            f"/api/exercise/records?userId={test_user.id}&exercise_date={yesterday.isoformat()}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["data"][0]["exercise_type"] == "running"

    def test_get_records_filter_by_type(self, test_user, db_session):
        """测试按运动类型筛选"""
        today = date.today()
        r1 = ExerciseRecord(
            user_id=test_user.id, exercise_type="walking",
            actual_calories=100.0, actual_duration=20, exercise_date=today,
        )
        r2 = ExerciseRecord(
            user_id=test_user.id, exercise_type="running",
            actual_calories=200.0, actual_duration=30, exercise_date=today,
        )
        r3 = ExerciseRecord(
            user_id=test_user.id, exercise_type="walking",
            actual_calories=120.0, actual_duration=25, exercise_date=today,
        )
        db_session.add_all([r1, r2, r3])
        db_session.commit()

        response = client.get(
            f"/api/exercise/records?userId={test_user.id}&exercise_type=walking"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(r["exercise_type"] == "walking" for r in data["data"])

    def test_get_records_filter_by_plan_id(self, test_user, test_plan, db_session):
        """测试按计划ID筛选"""
        today = date.today()
        r1 = ExerciseRecord(
            user_id=test_user.id, plan_id=test_plan.id, exercise_type="walking",
            actual_calories=100.0, actual_duration=20, exercise_date=today,
        )
        r2 = ExerciseRecord(
            user_id=test_user.id, plan_id=None, exercise_type="running",
            actual_calories=200.0, actual_duration=30, exercise_date=today,
        )
        db_session.add_all([r1, r2])
        db_session.commit()

        response = client.get(
            f"/api/exercise/records?userId={test_user.id}&plan_id={test_plan.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["data"][0]["plan_id"] == test_plan.id

    def test_get_records_pagination(self, test_user, db_session):
        """测试分页"""
        today = date.today()
        for i in range(10):
            db_session.add(ExerciseRecord(
                user_id=test_user.id, exercise_type="walking",
                actual_calories=100.0 + i, actual_duration=20,
                exercise_date=today - timedelta(days=i),
            ))
        db_session.commit()

        # 第一页（3条）
        response = client.get(
            f"/api/exercise/records?userId={test_user.id}&limit=3&offset=0"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3
        assert data["total"] == 10

        # 第二页
        response = client.get(
            f"/api/exercise/records?userId={test_user.id}&limit=3&offset=3"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3
        assert data["total"] == 10

    def test_get_records_order_by_date_desc(self, test_user, db_session):
        """测试按日期倒序排列"""
        today = date.today()
        dates = [today - timedelta(days=i) for i in range(5)]
        for d in dates:
            db_session.add(ExerciseRecord(
                user_id=test_user.id, exercise_type="walking",
                actual_calories=100.0, actual_duration=20,
                exercise_date=d,
            ))
        db_session.commit()

        response = client.get(f"/api/exercise/records?userId={test_user.id}")
        assert response.status_code == 200
        data = response.json()
        record_dates = [r["exercise_date"] for r in data["data"]]
        # 应该是倒序
        assert record_dates == sorted(record_dates, reverse=True)

    def test_get_records_invalid_date_filter(self, test_user):
        """测试无效日期筛选"""
        response = client.get(
            f"/api/exercise/records?userId={test_user.id}&exercise_date=invalid"
        )
        assert response.status_code == 400
        assert "日期格式错误" in response.json()["detail"]

    def test_get_records_invalid_exercise_type_filter(self, test_user):
        """测试无效运动类型筛选"""
        response = client.get(
            f"/api/exercise/records?userId={test_user.id}&exercise_type=invalid_type"
        )
        assert response.status_code == 400
        assert "不支持的运动类型" in response.json()["detail"]

    def test_get_records_only_own(self, test_user, test_user2, db_session):
        """测试只能查看自己的记录"""
        today = date.today()
        r1 = ExerciseRecord(
            user_id=test_user.id, exercise_type="walking",
            actual_calories=100.0, actual_duration=20, exercise_date=today,
        )
        r2 = ExerciseRecord(
            user_id=test_user2.id, exercise_type="running",
            actual_calories=200.0, actual_duration=30, exercise_date=today,
        )
        db_session.add_all([r1, r2])
        db_session.commit()

        # 用户1只能看到自己的
        response = client.get(f"/api/exercise/records?userId={test_user.id}")
        data = response.json()
        assert data["total"] == 1
        assert data["data"][0]["user_id"] == test_user.id

        # 用户2只能看到自己的
        response = client.get(f"/api/exercise/records?userId={test_user2.id}")
        data = response.json()
        assert data["total"] == 1
        assert data["data"][0]["user_id"] == test_user2.id


# ==================== 查询记录详情API测试 ====================

class TestGetExerciseRecordDetail:
    """测试 GET /api/exercise/record/{record_id}"""

    def test_get_detail_success(self, test_user, test_exercise_record):
        """测试成功获取详情"""
        response = client.get(
            f"/api/exercise/record/{test_exercise_record.id}?userId={test_user.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["id"] == test_exercise_record.id
        assert data["data"]["exercise_type"] == "running"
        assert data["data"]["actual_calories"] == 280.0

    def test_get_detail_not_found(self, test_user):
        """测试记录不存在"""
        response = client.get(f"/api/exercise/record/9999?userId={test_user.id}")
        assert response.status_code == 404
        assert "运动记录不存在" in response.json()["detail"]

    def test_get_detail_no_permission(self, test_user, test_user2, test_exercise_record):
        """测试无权查看他人记录"""
        response = client.get(
            f"/api/exercise/record/{test_exercise_record.id}?userId={test_user2.id}"
        )
        assert response.status_code == 403
        assert "无权查看" in response.json()["detail"]

    def test_get_detail_with_achievement(self, test_user, test_exercise_record):
        """测试详情包含达成率"""
        response = client.get(
            f"/api/exercise/record/{test_exercise_record.id}?userId={test_user.id}"
        )
        assert response.status_code == 200
        record = response.json()["data"]
        # 280/300*100 = 93.3
        assert record["calories_achievement"] == 93.3
        # 35/30*100 = 116.7
        assert record["duration_achievement"] == 116.7


# ==================== 删除运动记录API测试 ====================

class TestDeleteExerciseRecord:
    """测试 DELETE /api/exercise/record/{record_id}"""

    def test_delete_success(self, test_user, test_exercise_record):
        """测试成功删除"""
        response = client.delete(
            f"/api/exercise/record/{test_exercise_record.id}?userId={test_user.id}"
        )
        assert response.status_code == 200
        assert response.json()["code"] == 200
        assert response.json()["message"] == "删除成功"

        # 验证确实删除了
        response = client.get(
            f"/api/exercise/record/{test_exercise_record.id}?userId={test_user.id}"
        )
        assert response.status_code == 404

    def test_delete_not_found(self, test_user):
        """测试删除不存在的记录"""
        response = client.delete(f"/api/exercise/record/9999?userId={test_user.id}")
        assert response.status_code == 404
        assert "运动记录不存在" in response.json()["detail"]

    def test_delete_no_permission(self, test_user, test_user2, test_exercise_record):
        """测试无权删除他人记录"""
        response = client.delete(
            f"/api/exercise/record/{test_exercise_record.id}?userId={test_user2.id}"
        )
        assert response.status_code == 403
        assert "无权删除" in response.json()["detail"]

    def test_delete_then_list(self, test_user, test_exercise_record):
        """测试删除后列表不再包含该记录"""
        # 先确认有记录
        response = client.get(f"/api/exercise/records?userId={test_user.id}")
        assert response.json()["total"] == 1

        # 删除
        client.delete(
            f"/api/exercise/record/{test_exercise_record.id}?userId={test_user.id}"
        )

        # 再查应该为空
        response = client.get(f"/api/exercise/records?userId={test_user.id}")
        assert response.json()["total"] == 0


# ==================== 健康检查测试 ====================

class TestExerciseHealthCheck:
    """测试运动记录服务健康检查"""

    def test_health_check(self):
        """测试健康检查接口"""
        response = client.get("/api/exercise/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "exercise-record"


# ==================== 综合场景测试 ====================

class TestExerciseRecordIntegration:
    """综合场景测试"""

    def test_create_then_query_then_delete_flow(self, test_user):
        """测试完整的增查删流程"""
        today = date.today().isoformat()

        # 1. 创建记录
        create_resp = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "exercise_type": "running",
            "actual_calories": 300.0,
            "actual_duration": 40,
            "distance": 5000.0,
            "exercise_date": today,
        })
        assert create_resp.status_code == 200
        record_id = create_resp.json()["data"]["id"]

        # 2. 查询列表
        list_resp = client.get(f"/api/exercise/records?userId={test_user.id}")
        assert list_resp.json()["total"] == 1
        assert list_resp.json()["data"][0]["id"] == record_id

        # 3. 查询详情
        detail_resp = client.get(
            f"/api/exercise/record/{record_id}?userId={test_user.id}"
        )
        assert detail_resp.status_code == 200
        assert detail_resp.json()["data"]["actual_calories"] == 300.0

        # 4. 删除
        del_resp = client.delete(
            f"/api/exercise/record/{record_id}?userId={test_user.id}"
        )
        assert del_resp.status_code == 200

        # 5. 确认删除
        list_resp = client.get(f"/api/exercise/records?userId={test_user.id}")
        assert list_resp.json()["total"] == 0

    def test_multiple_records_different_dates(self, test_user):
        """测试多天多条记录"""
        today = date.today()
        records_to_create = []
        for i in range(7):
            d = (today - timedelta(days=i)).isoformat()
            records_to_create.append({
                "user_id": test_user.id,
                "exercise_type": "walking" if i % 2 == 0 else "running",
                "actual_calories": 100.0 + i * 30,
                "actual_duration": 20 + i * 5,
                "exercise_date": d,
            })

        # 创建所有记录
        for rec in records_to_create:
            resp = client.post("/api/exercise/record", json=rec)
            assert resp.status_code == 200

        # 查询全部
        resp = client.get(f"/api/exercise/records?userId={test_user.id}")
        assert resp.json()["total"] == 7

        # 按类型筛选
        resp = client.get(
            f"/api/exercise/records?userId={test_user.id}&exercise_type=walking"
        )
        assert resp.json()["total"] == 4  # days 0,2,4,6

        resp = client.get(
            f"/api/exercise/records?userId={test_user.id}&exercise_type=running"
        )
        assert resp.json()["total"] == 3  # days 1,3,5

    def test_record_with_plan_association(self, test_user, test_plan, test_plan_items):
        """测试与运动计划关联的完整场景"""
        today = date.today().isoformat()

        # 创建关联计划的记录
        resp = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "plan_id": test_plan.id,
            "exercise_type": "running",
            "actual_calories": 250.0,
            "actual_duration": 32,
            "exercise_date": today,
        })
        assert resp.status_code == 200
        record = resp.json()["data"]

        # 验证自动填充的计划数据
        assert record["plan_id"] == test_plan.id
        assert record["planned_calories"] == 300.0  # 100+200
        assert record["planned_duration"] == 35  # 20+15

        # 验证达成率
        assert record["calories_achievement"] == 83.3  # 250/300*100
        assert record["duration_achievement"] == 91.4  # 32/35*100

        # 按计划ID筛选
        resp = client.get(
            f"/api/exercise/records?userId={test_user.id}&plan_id={test_plan.id}"
        )
        assert resp.json()["total"] == 1

    def test_achievement_100_percent(self, test_user):
        """测试100%达成率"""
        resp = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "exercise_type": "walking",
            "actual_calories": 300.0,
            "actual_duration": 30,
            "planned_calories": 300.0,
            "planned_duration": 30,
            "exercise_date": date.today().isoformat(),
        })
        assert resp.status_code == 200
        record = resp.json()["data"]
        assert record["calories_achievement"] == 100.0
        assert record["duration_achievement"] == 100.0

    def test_achievement_over_100_percent(self, test_user):
        """测试超额完成（>100%达成率）"""
        resp = client.post("/api/exercise/record", json={
            "user_id": test_user.id,
            "exercise_type": "running",
            "actual_calories": 450.0,
            "actual_duration": 50,
            "planned_calories": 300.0,
            "planned_duration": 30,
            "exercise_date": date.today().isoformat(),
        })
        assert resp.status_code == 200
        record = resp.json()["data"]
        assert record["calories_achievement"] == 150.0  # 450/300*100
        assert record["duration_achievement"] == 166.7  # 50/30*100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
