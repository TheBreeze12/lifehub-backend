"""
后端完整集成测试 - 使用真实MySQL数据库 + FastAPI TestClient

测试覆盖Phase 1-24的所有API端点和数据库交互：
1. 数据库连接与表结构验证
2. 用户注册/登录/JWT认证完整流程
3. 饮食记录CRUD（增删改查）
4. 过敏原检测（关键词匹配+AI推理字段）
5. 统计接口（日/周热量、营养素统计）
6. 运动计划相关接口
7. METs计算服务
8. 天气服务
9. 健康检查接口
10. 边界条件与错误处理
"""
import os
import sys
import pytest
import uuid
from datetime import date, datetime, timedelta

# 确保项目根目录在sys.path中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db, engine, Base, DATABASE_URL


# ============= 测试配置 =============

# 使用与应用相同的数据库（lifehub），但在测试中使用事务回滚保持数据干净
# 为测试创建独立的session
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 测试用的唯一昵称前缀，避免与真实数据冲突
TEST_PREFIX = f"test_{uuid.uuid4().hex[:8]}"


def get_test_db():
    """测试用的数据库会话"""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# 覆盖FastAPI的数据库依赖
app.dependency_overrides[get_db] = get_test_db

client = TestClient(app)


# ============= 测试数据清理 =============

class TestState:
    """存储测试过程中产生的数据ID，便于后续清理"""
    user_id: int = None
    user_nickname: str = f"{TEST_PREFIX}_integration"
    user_password: str = "TestPass123!"
    access_token: str = None
    refresh_token: str = None
    diet_record_id: int = None
    trip_id: int = None


state = TestState()


@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data():
    """测试结束后清理测试数据"""
    yield
    # 清理测试产生的数据
    db = TestSessionLocal()
    try:
        # 删除测试用户的饮食记录
        if state.user_id:
            db.execute(text(f"DELETE FROM diet_record WHERE user_id = {state.user_id}"))
            db.execute(text(f"DELETE FROM meal_comparison WHERE user_id = {state.user_id}"))
            db.execute(text(f"DELETE FROM menu_recognition WHERE user_id = {state.user_id}"))
            db.execute(text(f"DELETE FROM trip_item WHERE plan_id IN (SELECT id FROM trip_plan WHERE user_id = {state.user_id})"))
            db.execute(text(f"DELETE FROM trip_plan WHERE user_id = {state.user_id}"))
            db.execute(text(f"DELETE FROM user WHERE id = {state.user_id}"))
            db.commit()
    except Exception as e:
        print(f"清理测试数据时出错: {e}")
        db.rollback()
    finally:
        db.close()


# ============= 1. 数据库连接与表结构验证 =============

class TestDatabaseConnection:
    """测试数据库连接和表结构"""

    def test_database_connection(self):
        """测试数据库连接是否正常"""
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1

    def test_database_name(self):
        """验证连接的是lifehub数据库"""
        with engine.connect() as conn:
            result = conn.execute(text("SELECT DATABASE()"))
            db_name = result.fetchone()[0]
            assert db_name == "lifehub"

    def test_all_tables_exist(self):
        """验证所有必需的表都存在"""
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        required_tables = ["user", "diet_record", "menu_recognition", 
                          "trip_plan", "trip_item", "meal_comparison"]
        for table in required_tables:
            assert table in tables, f"表 '{table}' 不存在"

    def test_user_table_columns(self):
        """验证user表包含所有必需的列（含Phase 4新增的身体参数列）"""
        inspector = inspect(engine)
        columns = {col['name'] for col in inspector.get_columns('user')}
        required_columns = {"id", "nickname", "password", "health_goal", 
                           "allergens", "travel_preference", "daily_budget",
                           "weight", "height", "age", "gender"}
        for col in required_columns:
            assert col in columns, f"user表缺少列 '{col}'"

    def test_diet_record_table_columns(self):
        """验证diet_record表包含所有必需的列"""
        inspector = inspect(engine)
        columns = {col['name'] for col in inspector.get_columns('diet_record')}
        required_columns = {"id", "user_id", "food_name", "calories", 
                           "protein", "fat", "carbs", "meal_type", 
                           "record_date", "created_at"}
        for col in required_columns:
            assert col in columns, f"diet_record表缺少列 '{col}'"

    def test_meal_comparison_table_columns(self):
        """验证meal_comparison表包含Phase 10-12新增的列"""
        inspector = inspect(engine)
        columns = {col['name'] for col in inspector.get_columns('meal_comparison')}
        required_columns = {"id", "user_id", "before_image_url", "after_image_url",
                           "before_features", "after_features", "consumption_ratio",
                           "original_calories", "net_calories", "status"}
        for col in required_columns:
            assert col in columns, f"meal_comparison表缺少列 '{col}'"

    def test_trip_plan_table_columns(self):
        """验证trip_plan表结构"""
        inspector = inspect(engine)
        columns = {col['name'] for col in inspector.get_columns('trip_plan')}
        required_columns = {"id", "user_id", "title", "destination"}
        for col in required_columns:
            assert col in columns, f"trip_plan表缺少列 '{col}'"

    def test_trip_item_table_columns(self):
        """验证trip_item表结构"""
        inspector = inspect(engine)
        columns = {col['name'] for col in inspector.get_columns('trip_item')}
        required_columns = {"id", "trip_id"}
        for col in required_columns:
            assert col in columns, f"trip_item表缺少列 '{col}'"


# ============= 2. 健康检查接口 =============

class TestHealthCheck:
    """测试健康检查和根路径"""

    def test_root_endpoint(self):
        """测试根路径返回API信息"""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "version" in data
        assert data["version"] == "1.0.0"

    def test_health_endpoint(self):
        """测试健康检查接口"""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "api_key_configured" in data

    def test_food_health_endpoint(self):
        """测试食物服务健康检查"""
        resp = client.get("/api/food/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "food-analysis"

    def test_stats_health_endpoint(self):
        """测试统计服务健康检查"""
        resp = client.get("/api/stats/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


# ============= 3. 用户注册/登录/JWT认证 =============

class TestUserRegistration:
    """测试用户注册"""

    def test_register_new_user(self):
        """注册新用户"""
        resp = client.post("/api/user/register", json={
            "nickname": state.user_nickname,
            "password": state.user_password
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["message"] == "注册成功"
        assert "userId" in data
        state.user_id = data["userId"]
        assert state.user_id > 0

    def test_register_duplicate_user(self):
        """注册重复用户名应失败"""
        resp = client.post("/api/user/register", json={
            "nickname": state.user_nickname,
            "password": "AnotherPass123"
        })
        assert resp.status_code == 400
        assert "用户已存在" in resp.json()["detail"]

    def test_register_empty_nickname(self):
        """空昵称注册（当前模型无min_length约束，允许成功）"""
        resp = client.post("/api/user/register", json={
            "nickname": "",
            "password": "ValidPass123"
        })
        # 当前Pydantic模型未限制nickname最小长度
        # 可能成功(200)、验证失败(422)、或因重复返回400
        assert resp.status_code in [200, 400, 422]

    def test_register_missing_fields(self):
        """缺少必填字段应失败"""
        resp = client.post("/api/user/register", json={})
        assert resp.status_code == 422


class TestUserLogin:
    """测试用户登录"""

    def test_login_jwt(self):
        """JWT登录获取token"""
        resp = client.post("/api/user/login", json={
            "nickname": state.user_nickname,
            "password": state.user_password
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["message"] == "登录成功"
        assert data["data"]["userId"] == state.user_id
        assert "token" in data
        assert "access_token" in data["token"]
        assert "refresh_token" in data["token"]
        assert data["token"]["token_type"] == "bearer"
        assert data["token"]["expires_in"] > 0
        state.access_token = data["token"]["access_token"]
        state.refresh_token = data["token"]["refresh_token"]

    def test_login_wrong_password(self):
        """密码错误应返回401"""
        resp = client.post("/api/user/login", json={
            "nickname": state.user_nickname,
            "password": "WrongPassword999"
        })
        assert resp.status_code == 401
        assert "密码错误" in resp.json()["detail"]

    def test_login_nonexistent_user(self):
        """不存在的用户应返回404"""
        resp = client.post("/api/user/login", json={
            "nickname": f"nonexistent_{uuid.uuid4().hex[:8]}",
            "password": "AnyPassword"
        })
        assert resp.status_code == 404
        assert "用户不存在" in resp.json()["detail"]

    def test_login_legacy_endpoint(self):
        """旧版登录接口兼容测试"""
        resp = client.get("/api/user/data", params={
            "nickname": state.user_nickname,
            "password": state.user_password
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["data"]["userId"] == state.user_id

    def test_legacy_login_wrong_password(self):
        """旧版登录接口密码错误"""
        resp = client.get("/api/user/data", params={
            "nickname": state.user_nickname,
            "password": "WrongPass"
        })
        assert resp.status_code == 401


class TestJWTAuth:
    """测试JWT认证机制"""

    def test_get_current_user_with_token(self):
        """使用有效token访问/me接口"""
        resp = client.get("/api/user/me", headers={
            "Authorization": f"Bearer {state.access_token}"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["userId"] == state.user_id
        assert data["data"]["nickname"] == state.user_nickname

    def test_get_current_user_without_token(self):
        """无token访问/me应返回401"""
        resp = client.get("/api/user/me")
        assert resp.status_code in [401, 403]

    def test_get_current_user_invalid_token(self):
        """无效token访问/me应返回401"""
        resp = client.get("/api/user/me", headers={
            "Authorization": "Bearer invalid_token_here"
        })
        assert resp.status_code in [401, 403]

    def test_refresh_token(self):
        """刷新token"""
        resp = client.post("/api/user/refresh", json={
            "refresh_token": state.refresh_token
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert "token" in data
        assert "access_token" in data["token"]
        # 更新state中的token
        state.access_token = data["token"]["access_token"]
        state.refresh_token = data["token"]["refresh_token"]

    def test_refresh_invalid_token(self):
        """无效refresh token应返回401"""
        resp = client.post("/api/user/refresh", json={
            "refresh_token": "invalid_refresh_token"
        })
        assert resp.status_code == 401


# ============= 4. 用户偏好设置 =============

class TestUserPreferences:
    """测试用户偏好设置（含Phase 4身体参数, Phase 9过敏原档案）"""

    def test_get_preferences(self):
        """获取用户偏好"""
        resp = client.get("/api/user/preferences", params={"userId": state.user_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["data"]["userId"] == state.user_id

    def test_get_preferences_nonexistent_user(self):
        """获取不存在用户的偏好应返回404"""
        resp = client.get("/api/user/preferences", params={"userId": 999999})
        assert resp.status_code == 404

    def test_update_health_goal(self):
        """更新健康目标"""
        resp = client.put("/api/user/preferences", json={
            "userId": state.user_id,
            "healthGoal": "reduce_fat"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["healthGoal"] == "reduce_fat"

    def test_update_body_parameters(self):
        """更新身体参数（Phase 4）"""
        resp = client.put("/api/user/preferences", json={
            "userId": state.user_id,
            "weight": 70.5,
            "height": 175.0,
            "age": 25,
            "gender": "male"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["weight"] == 70.5
        assert data["data"]["height"] == 175.0
        assert data["data"]["age"] == 25
        assert data["data"]["gender"] == "male"

    def test_update_allergens(self):
        """更新过敏原档案（Phase 9）"""
        resp = client.put("/api/user/preferences", json={
            "userId": state.user_id,
            "allergens": ["花生", "海鲜"]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "花生" in data["data"]["allergens"]
        assert "海鲜" in data["data"]["allergens"]

    def test_update_travel_preference(self):
        """更新出行偏好"""
        resp = client.put("/api/user/preferences", json={
            "userId": state.user_id,
            "travelPreference": "walking",
            "dailyBudget": 100
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["travelPreference"] == "walking"
        assert data["data"]["dailyBudget"] == 100

    def test_partial_update(self):
        """部分更新（只更新一个字段，其他不变）"""
        resp = client.put("/api/user/preferences", json={
            "userId": state.user_id,
            "healthGoal": "gain_muscle"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["healthGoal"] == "gain_muscle"
        # 之前设置的体重应该保持不变
        assert data["data"]["weight"] == 70.5

    def test_verify_preferences_persisted(self):
        """验证偏好设置持久化到数据库"""
        resp = client.get("/api/user/preferences", params={"userId": state.user_id})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["healthGoal"] == "gain_muscle"
        assert data["weight"] == 70.5
        assert data["height"] == 175.0
        assert data["age"] == 25
        assert data["gender"] == "male"
        assert "花生" in data["allergens"]


# ============= 5. 饮食记录CRUD =============

class TestDietRecordCreate:
    """测试饮食记录创建"""

    def test_add_diet_record(self):
        """添加饮食记录"""
        today = date.today().isoformat()
        resp = client.post("/api/food/record", json={
            "userId": state.user_id,
            "foodName": "番茄炒蛋",
            "calories": 150.0,
            "protein": 10.5,
            "fat": 8.2,
            "carbs": 6.3,
            "mealType": "午餐",
            "recordDate": today
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["message"] == "记录成功"

    def test_add_diet_record_english_meal_type(self):
        """使用英文餐次添加记录"""
        today = date.today().isoformat()
        resp = client.post("/api/food/record", json={
            "userId": state.user_id,
            "foodName": "全麦面包",
            "calories": 200.0,
            "protein": 8.0,
            "fat": 3.0,
            "carbs": 35.0,
            "mealType": "breakfast",
            "recordDate": today
        })
        assert resp.status_code == 200

    def test_add_diet_record_invalid_date(self):
        """无效日期格式应失败"""
        resp = client.post("/api/food/record", json={
            "userId": state.user_id,
            "foodName": "测试菜品",
            "calories": 100.0,
            "mealType": "lunch",
            "recordDate": "2026/02/06"  # 错误格式
        })
        assert resp.status_code == 400
        assert "日期格式错误" in resp.json()["detail"]

    def test_add_diet_record_nonexistent_user(self):
        """不存在的用户添加记录应失败"""
        resp = client.post("/api/food/record", json={
            "userId": 999999,
            "foodName": "测试菜品",
            "calories": 100.0,
            "mealType": "lunch",
            "recordDate": date.today().isoformat()
        })
        assert resp.status_code == 404


class TestDietRecordRead:
    """测试饮食记录查询"""

    def test_get_today_records(self):
        """获取今日饮食记录"""
        resp = client.get("/api/food/records/today", params={"userId": state.user_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        today = date.today().isoformat()
        assert today in data["data"]
        records = data["data"][today]
        assert len(records) >= 2  # 上面添加了2条
        # 验证记录包含必需字段
        record = records[0]
        assert "id" in record
        assert "userId" in record
        assert "foodName" in record
        assert "calories" in record
        assert "protein" in record
        assert "fat" in record
        assert "carbs" in record
        assert "mealType" in record
        assert "recordDate" in record

    def test_get_all_records(self):
        """获取所有饮食记录"""
        resp = client.get("/api/food/records", params={"userId": state.user_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        # 按日期分组
        assert isinstance(data["data"], dict)
        total_records = sum(len(v) for v in data["data"].values())
        assert total_records >= 2


class TestDietRecordUpdate:
    """测试饮食记录更新（Phase 2-3）"""

    def test_update_diet_record(self):
        """更新饮食记录"""
        # 先获取一条记录ID
        resp = client.get("/api/food/records/today", params={"userId": state.user_id})
        records = list(resp.json()["data"].values())[0]
        record_id = records[0]["id"]
        state.diet_record_id = record_id

        # 更新该记录
        resp = client.put(f"/api/food/diet/{record_id}", json={
            "userId": state.user_id,
            "foodName": "更新后的番茄炒蛋",
            "calories": 180.0
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["message"] == "更新成功"
        assert data["data"]["foodName"] == "更新后的番茄炒蛋"
        assert data["data"]["calories"] == 180.0

    def test_update_diet_record_permission(self):
        """不能更新他人的记录（权限校验）"""
        resp = client.put(f"/api/food/diet/{state.diet_record_id}", json={
            "userId": 999999,  # 不是记录的拥有者
            "foodName": "试图篡改"
        })
        assert resp.status_code == 403
        assert "无权操作" in resp.json()["detail"]

    def test_update_nonexistent_record(self):
        """更新不存在的记录应返回404"""
        resp = client.put("/api/food/diet/999999", json={
            "userId": state.user_id,
            "foodName": "不存在的记录"
        })
        assert resp.status_code == 404

    def test_update_record_date_format(self):
        """更新记录时使用无效日期格式"""
        resp = client.put(f"/api/food/diet/{state.diet_record_id}", json={
            "userId": state.user_id,
            "recordDate": "invalid-date"
        })
        assert resp.status_code == 400
        assert "日期格式错误" in resp.json()["detail"]


class TestDietRecordDelete:
    """测试饮食记录删除（Phase 2-3）"""

    def test_delete_diet_record_permission(self):
        """不能删除他人的记录"""
        # 先添加一条记录
        today = date.today().isoformat()
        client.post("/api/food/record", json={
            "userId": state.user_id,
            "foodName": "待删除的记录",
            "calories": 50.0,
            "mealType": "snack",
            "recordDate": today
        })
        # 获取该记录ID
        resp = client.get("/api/food/records/today", params={"userId": state.user_id})
        records = list(resp.json()["data"].values())[0]
        delete_id = records[-1]["id"]

        # 用错误的userId尝试删除
        resp = client.delete(f"/api/food/diet/{delete_id}", params={"userId": 999999})
        assert resp.status_code == 403

    def test_delete_diet_record(self):
        """删除饮食记录"""
        # 获取记录列表
        resp = client.get("/api/food/records/today", params={"userId": state.user_id})
        records = list(resp.json()["data"].values())[0]
        delete_id = records[-1]["id"]
        count_before = len(records)

        # 删除
        resp = client.delete(f"/api/food/diet/{delete_id}", params={"userId": state.user_id})
        assert resp.status_code == 200
        assert resp.json()["code"] == 200
        assert resp.json()["message"] == "删除成功"

        # 验证记录减少
        resp = client.get("/api/food/records/today", params={"userId": state.user_id})
        records_after = list(resp.json()["data"].values())[0]
        assert len(records_after) == count_before - 1

    def test_delete_nonexistent_record(self):
        """删除不存在的记录应返回404"""
        resp = client.delete("/api/food/diet/999999", params={"userId": state.user_id})
        assert resp.status_code == 404


# ============= 6. 过敏原检测（Phase 6-7） =============

class TestAllergenDetection:
    """测试过敏原检测接口"""

    def test_get_allergen_categories(self):
        """获取八大类过敏原列表"""
        resp = client.get("/api/food/allergen/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert len(data["data"]) == 8
        codes = {cat["code"] for cat in data["data"]}
        expected_codes = {"milk", "egg", "fish", "shellfish", "peanut", "tree_nut", "wheat", "soy"}
        assert codes == expected_codes

    def test_check_allergens_peanut(self):
        """检测含花生的菜品"""
        resp = client.post("/api/food/allergen/check", json={
            "food_name": "宫保鸡丁",
            "ingredients": ["鸡肉", "花生", "辣椒"],
            "user_allergens": ["花生"]
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["has_allergens"] is True
        assert data["allergen_count"] >= 1
        # 检查花生被检测到
        detected_codes = [a["code"] for a in data["detected_allergens"]]
        assert "peanut" in detected_codes
        # 检查用户告警
        assert data["has_warnings"] is True

    def test_check_allergens_no_allergens(self):
        """检测不含过敏原的菜品"""
        resp = client.post("/api/food/allergen/check", json={
            "food_name": "白米饭",
            "ingredients": ["大米"]
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        # 白米饭通常不含八大类过敏原
        assert data["allergen_count"] == 0

    def test_check_allergens_multiple(self):
        """检测含多种过敏原的菜品"""
        resp = client.post("/api/food/allergen/check", json={
            "food_name": "海鲜豆腐汤",
            "ingredients": ["虾", "豆腐", "鸡蛋"],
            "user_allergens": ["海鲜", "鸡蛋"]
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["has_allergens"] is True
        assert data["allergen_count"] >= 2

    def test_check_allergens_without_ingredients(self):
        """不提供配料列表时的检测"""
        resp = client.post("/api/food/allergen/check", json={
            "food_name": "宫保鸡丁"
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        # 仅基于菜名检测，花生在"宫保"中可能被检出
        assert isinstance(data["detected_allergens"], list)


# ============= 7. 统计接口（Phase 15-16） =============

class TestCalorieStats:
    """测试热量统计接口"""

    def test_daily_calorie_stats(self):
        """获取每日热量统计"""
        today = date.today().isoformat()
        resp = client.get("/api/stats/calories/daily", params={
            "userId": state.user_id,
            "date": today
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        stats = data["data"]
        assert "intake_calories" in stats
        assert "burn_calories" in stats
        assert "net_calories" in stats
        assert "meal_count" in stats
        # 我们之前添加了饮食记录，摄入热量应>0
        assert stats["intake_calories"] > 0
        assert stats["meal_count"] >= 1

    def test_daily_calorie_stats_invalid_date(self):
        """无效日期格式应返回400"""
        resp = client.get("/api/stats/calories/daily", params={
            "userId": state.user_id,
            "date": "invalid"
        })
        assert resp.status_code == 400

    def test_weekly_calorie_stats(self):
        """获取每周热量统计"""
        # 计算本周一
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        resp = client.get("/api/stats/calories/weekly", params={
            "userId": state.user_id,
            "week_start": monday.isoformat()
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        stats = data["data"]
        assert "total_intake" in stats
        assert "total_burn" in stats
        assert "daily_breakdown" in stats
        assert len(stats["daily_breakdown"]) == 7  # 一周7天

    def test_daily_calorie_stats_no_data(self):
        """查询无数据日期的统计"""
        resp = client.get("/api/stats/calories/daily", params={
            "userId": state.user_id,
            "date": "2020-01-01"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["intake_calories"] == 0.0


class TestNutrientStats:
    """测试营养素统计接口（Phase 16）"""

    def test_daily_nutrient_stats(self):
        """获取每日营养素统计"""
        today = date.today().isoformat()
        resp = client.get("/api/stats/nutrients/daily", params={
            "userId": state.user_id,
            "date": today
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        stats = data["data"]
        assert "total_protein" in stats
        assert "total_fat" in stats
        assert "total_carbs" in stats
        assert "total_calories" in stats
        assert "protein_ratio" in stats
        assert "fat_ratio" in stats
        assert "carbs_ratio" in stats
        assert "guidelines_comparison" in stats
        # 验证膳食指南对比结构
        gc = stats["guidelines_comparison"]
        assert "protein" in gc
        assert "fat" in gc
        assert "carbs" in gc
        for nutrient in [gc["protein"], gc["fat"], gc["carbs"]]:
            assert "actual_ratio" in nutrient
            assert "recommended_min" in nutrient
            assert "recommended_max" in nutrient
            assert "status" in nutrient

    def test_daily_nutrient_stats_no_data(self):
        """无数据时营养素统计"""
        resp = client.get("/api/stats/nutrients/daily", params={
            "userId": state.user_id,
            "date": "2020-01-01"
        })
        assert resp.status_code == 200
        stats = resp.json()["data"]
        assert stats["total_calories"] == 0.0


# ============= 8. 运动计划相关接口 =============

class TestTripEndpoints:
    """测试运动计划接口"""

    def test_get_trip_list_empty(self):
        """获取运动计划列表（新用户应为空）"""
        resp = client.get("/api/trip/list", params={"userId": state.user_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200

    def test_get_recent_trips(self):
        """获取最近运动计划"""
        resp = client.get("/api/trip/recent", params={"userId": state.user_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200

    def test_get_home_trips(self):
        """获取首页运动计划"""
        resp = client.get("/api/trip/home", params={"userId": state.user_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200

    def test_get_nonexistent_trip_detail(self):
        """获取不存在的运动计划详情"""
        resp = client.get("/api/trip/999999")
        assert resp.status_code == 404


# ============= 9. 天气服务 =============

class TestWeatherService:
    """测试天气服务接口"""

    def test_weather_by_address(self):
        """根据地址查询天气"""
        resp = client.get("/api/weather/by-address", params={
            "address": "北京市朝阳区"
        })
        # 天气服务需要网络，可能失败，但应该返回200或合理错误
        assert resp.status_code in [200, 500]

    def test_weather_by_plan_nonexistent(self):
        """根据不存在的计划ID查天气应返回错误"""
        resp = client.get("/api/weather/by-plan", params={
            "planId": 999999
        })
        assert resp.status_code in [404, 500]


# ============= 10. METs计算服务（Phase 19） =============

class TestMETsService:
    """测试METs热量计算服务"""

    def test_calculate_walking_calories(self):
        """步行热量计算"""
        from app.services.mets_service import METsService
        service = METsService()
        result = service.calculate_calories("walking", 70.0, 60)
        # walking METs = 3.5, 70kg, 1h = 3.5 * 70 * 1 = 245 kcal
        assert abs(result - 245.0) < 1.0

    def test_calculate_running_calories(self):
        """跑步热量计算"""
        from app.services.mets_service import METsService
        service = METsService()
        result = service.calculate_calories("running", 70.0, 30)
        # running METs ~= 8.0-10.0, result should be positive
        assert result > 0

    def test_heavier_person_burns_more(self):
        """体重越大消耗越多"""
        from app.services.mets_service import METsService
        service = METsService()
        light = service.calculate_calories("walking", 50.0, 60)
        heavy = service.calculate_calories("walking", 100.0, 60)
        assert heavy > light
        assert abs(heavy / light - 2.0) < 0.01

    def test_zero_duration(self):
        """零时长消耗应为0"""
        from app.services.mets_service import METsService
        service = METsService()
        result = service.calculate_calories("running", 70.0, 0)
        assert result == 0.0

    def test_all_exercise_types(self):
        """验证运动类型列表非空"""
        from app.services.mets_service import METsService
        service = METsService()
        types = service.get_all_exercise_types()
        assert len(types) > 10
        assert "walking" in types
        assert "running" in types
        assert "cycling" in types


# ============= 11. NSGA-II算法服务（Phase 20） =============

class TestNSGA2Service:
    """测试NSGA-II多目标优化算法"""

    def test_import_nsga2(self):
        """确保NSGA-II服务可导入"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        assert service is not None

    def test_nsga2_has_optimize_method(self):
        """验证优化器有optimize方法"""
        from app.services.nsga2_service import NSGA2Service
        service = NSGA2Service()
        assert hasattr(service, 'optimize')


# ============= 12. 路网服务（Phase 21） =============

class TestRouteService:
    """测试OSM路网服务"""

    def test_import_route_service(self):
        """确保路网服务可导入"""
        from app.services.route_service import RouteService
        service = RouteService()
        assert service is not None

    def test_route_service_has_methods(self):
        """验证路网服务有必需方法"""
        from app.services.route_service import RouteService
        service = RouteService()
        assert hasattr(service, 'get_road_network') or hasattr(service, 'get_network')


# ============= 13. 路径优化服务（Phase 22） =============

class TestRouteOptimizationService:
    """测试帕累托路径生成服务"""

    def test_import_route_optimization(self):
        """确保路径优化服务可导入"""
        from app.services.route_optimization_service import RouteOptimizationService
        service = RouteOptimizationService()
        assert service is not None


# ============= 14. 最新菜单识别结果 =============

class TestLatestRecognition:
    """测试获取最新识别结果"""

    def test_get_latest_recognition_empty(self):
        """新用户获取最新识别结果（应为空）"""
        resp = client.get("/api/food/latest-recognition", params={"userId": state.user_id})
        assert resp.status_code == 200
        data = resp.json()
        # 新用户可能没有识别记录
        assert data["code"] in [200, 404]


# ============= 15. API文档可访问性 =============

class TestAPIDocs:
    """测试API文档端点"""

    def test_openapi_schema(self):
        """OpenAPI schema可访问"""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "paths" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "智能生活服务工具API"

    def test_docs_endpoint(self):
        """Swagger UI可访问"""
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_redoc_endpoint(self):
        """ReDoc可访问"""
        resp = client.get("/redoc")
        assert resp.status_code == 200


# ============= 16. 边界条件测试 =============

class TestEdgeCases:
    """测试边界条件和错误处理"""

    def test_large_calorie_value(self):
        """大热量值饮食记录"""
        today = date.today().isoformat()
        resp = client.post("/api/food/record", json={
            "userId": state.user_id,
            "foodName": "大量食物",
            "calories": 9999.0,
            "protein": 500.0,
            "fat": 300.0,
            "carbs": 800.0,
            "mealType": "dinner",
            "recordDate": today
        })
        assert resp.status_code == 200

    def test_zero_calorie_value(self):
        """零热量饮食记录"""
        today = date.today().isoformat()
        resp = client.post("/api/food/record", json={
            "userId": state.user_id,
            "foodName": "水",
            "calories": 0.0,
            "protein": 0.0,
            "fat": 0.0,
            "carbs": 0.0,
            "mealType": "snack",
            "recordDate": today
        })
        assert resp.status_code == 200

    def test_unicode_food_name(self):
        """Unicode菜品名称"""
        today = date.today().isoformat()
        resp = client.post("/api/food/record", json={
            "userId": state.user_id,
            "foodName": "🍅番茄炒蛋（特辣版）",
            "calories": 200.0,
            "mealType": "lunch",
            "recordDate": today
        })
        assert resp.status_code == 200

    def test_future_date_record(self):
        """未来日期的饮食记录"""
        future = (date.today() + timedelta(days=30)).isoformat()
        resp = client.post("/api/food/record", json={
            "userId": state.user_id,
            "foodName": "未来的午餐",
            "calories": 100.0,
            "mealType": "lunch",
            "recordDate": future
        })
        # 应该允许（用户可能提前规划）
        assert resp.status_code == 200

    def test_invalid_endpoint(self):
        """访问不存在的端点"""
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404

    def test_missing_required_params(self):
        """缺少必需参数"""
        resp = client.get("/api/food/records")  # 缺少userId
        assert resp.status_code == 422

    def test_allergen_check_empty_food_name(self):
        """空菜品名称的过敏原检测"""
        resp = client.post("/api/food/allergen/check", json={
            "food_name": ""
        })
        # 应该返回422（验证失败）或200（空结果）
        assert resp.status_code in [200, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
