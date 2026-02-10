"""
Phase 46 测试文件：离线运动包生成接口
测试覆盖：
1. OfflinePackageService 单元测试（包生成逻辑）
2. API接口集成测试（POST生成 + GET下载）
3. 边缘情况测试（无效plan_id、无坐标、空items等）
4. 版本管理测试
5. 包内容完整性验证

注意：本测试使用 SQLite 内存数据库，不依赖 MySQL
"""
import sys
import os
import json
import zipfile
import io
import pytest
import shutil
import tempfile
from datetime import date, time, datetime
from unittest.mock import patch, MagicMock

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ============================================================
# 测试用 SQLite 内存数据库配置（覆盖 MySQL 配置）
# ============================================================
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = "sqlite:///./test_phase46.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# 导入 Base 并创建表
from app.database import Base
from app.db_models.user import User
from app.db_models.trip_plan import TripPlan
from app.db_models.trip_item import TripItem

# 创建所有表
Base.metadata.create_all(bind=test_engine)


def get_test_db():
    """测试用数据库会话"""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# 临时目录用于存放离线包
TEST_PACKAGE_DIR = tempfile.mkdtemp(prefix="lifehub_test_packages_")


@pytest.fixture(autouse=True)
def clean_db():
    """每个测试前清空数据库和包目录"""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    # 清理包目录
    if os.path.exists(TEST_PACKAGE_DIR):
        for f in os.listdir(TEST_PACKAGE_DIR):
            fp = os.path.join(TEST_PACKAGE_DIR, f)
            if os.path.isfile(fp):
                os.remove(fp)
            elif os.path.isdir(fp):
                shutil.rmtree(fp)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """获取测试数据库会话"""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_test_user(db, user_id=1, weight=70.0):
    """创建测试用户"""
    user = User(
        id=user_id,
        nickname=f"test_user_{user_id}",
        password="test_password",
        health_goal="reduce_fat",
        weight=weight,
        height=170.0,
        age=30,
        gender="male",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_test_plan(db, user_id=1, plan_id=None, with_items=True,
                     lat=39.9042, lng=116.4074, destination="北京奥林匹克公园"):
    """创建测试运动计划（含运动项目）"""
    plan = TripPlan(
        user_id=user_id,
        title="餐后运动计划-消耗300kcal",
        destination=destination,
        latitude=lat,
        longitude=lng,
        start_date=date(2026, 2, 7),
        end_date=date(2026, 2, 7),
        status="planning",
    )
    if plan_id:
        plan.id = plan_id
    db.add(plan)
    db.flush()

    if with_items:
        items = [
            TripItem(
                trip_id=plan.id, day_index=1,
                start_time=time(18, 0),
                place_name="奥林匹克公园南门",
                place_type="walking", duration=20, cost=80.0,
                latitude=39.9042, longitude=116.4074,
                notes="热身散步", sort_order=0,
            ),
            TripItem(
                trip_id=plan.id, day_index=1,
                start_time=time(18, 20),
                place_name="鸟巢体育场周边",
                place_type="running", duration=15, cost=150.0,
                latitude=39.9908, longitude=116.3966,
                notes="慢跑", sort_order=1,
            ),
            TripItem(
                trip_id=plan.id, day_index=1,
                start_time=time(18, 35),
                place_name="水立方附近",
                place_type="walking", duration=10, cost=40.0,
                latitude=39.9929, longitude=116.3890,
                notes="放松散步", sort_order=2,
            ),
        ]
        for item in items:
            db.add(item)

    db.commit()
    db.refresh(plan)
    return plan


# ============================================================
# 第一组：OfflinePackageService 单元测试
# ============================================================

class TestOfflinePackageService:
    """离线包服务单元测试"""

    def test_service_init(self):
        """测试服务初始化"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)
        assert service is not None
        assert os.path.exists(service.storage_dir)

    def test_generate_plan_text(self, db_session):
        """测试运动方案文本生成"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id)
        items = db_session.query(TripItem).filter(TripItem.trip_id == plan.id).order_by(TripItem.sort_order).all()

        plan_text = service.generate_plan_text(plan, items)
        assert isinstance(plan_text, dict)
        assert "title" in plan_text
        assert "destination" in plan_text
        assert "date" in plan_text
        assert "total_duration" in plan_text
        assert "total_calories" in plan_text
        assert "items" in plan_text
        assert len(plan_text["items"]) == 3
        # 验证总时长和总热量
        assert plan_text["total_duration"] == 45  # 20+15+10
        assert plan_text["total_calories"] == 270.0  # 80+150+40

    def test_extract_poi_data(self, db_session):
        """测试POI数据提取"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id)
        items = db_session.query(TripItem).filter(TripItem.trip_id == plan.id).order_by(TripItem.sort_order).all()

        pois = service.extract_poi_data(items)
        assert isinstance(pois, list)
        assert len(pois) == 3
        for poi in pois:
            assert "name" in poi
            assert "type" in poi
            assert "latitude" in poi
            assert "longitude" in poi
        # 验证第一个POI
        assert pois[0]["name"] == "奥林匹克公园南门"
        assert pois[0]["type"] == "walking"
        assert pois[0]["latitude"] == 39.9042

    def test_calculate_tile_bounds(self):
        """测试地图瓦片区域计算"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        points = [
            {"latitude": 39.9042, "longitude": 116.4074},
            {"latitude": 39.9908, "longitude": 116.3966},
            {"latitude": 39.9929, "longitude": 116.3890},
        ]
        tile_meta = service.calculate_tile_bounds(points)
        assert isinstance(tile_meta, dict)
        assert "bounds" in tile_meta
        assert "min_lat" in tile_meta["bounds"]
        assert "max_lat" in tile_meta["bounds"]
        assert "min_lng" in tile_meta["bounds"]
        assert "max_lng" in tile_meta["bounds"]
        assert "zoom_levels" in tile_meta
        assert "tile_count_estimate" in tile_meta
        # 验证边界正确
        assert tile_meta["bounds"]["min_lat"] <= 39.9042
        assert tile_meta["bounds"]["max_lat"] >= 39.9929
        assert tile_meta["bounds"]["min_lng"] <= 116.3890
        assert tile_meta["bounds"]["max_lng"] >= 116.4074

    def test_calculate_tile_bounds_with_padding(self):
        """测试地图瓦片区域带缓冲区"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        points = [{"latitude": 39.9042, "longitude": 116.4074}]
        tile_meta = service.calculate_tile_bounds(points, padding_km=1.0)
        bounds = tile_meta["bounds"]
        # 单点加缓冲后，边界应该扩大
        assert bounds["min_lat"] < 39.9042
        assert bounds["max_lat"] > 39.9042
        assert bounds["min_lng"] < 116.4074
        assert bounds["max_lng"] > 116.4074

    def test_generate_package(self, db_session):
        """测试完整离线包生成"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id)
        items = db_session.query(TripItem).filter(TripItem.trip_id == plan.id).order_by(TripItem.sort_order).all()

        result = service.generate_package(plan, items)
        assert isinstance(result, dict)
        assert "package_id" in result
        assert "file_path" in result
        assert "file_size" in result
        assert "version" in result
        assert result["version"] == 1
        # 验证文件存在
        assert os.path.exists(result["file_path"])
        assert result["file_size"] > 0

    def test_package_is_valid_zip(self, db_session):
        """测试生成的离线包是有效的ZIP文件"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id)
        items = db_session.query(TripItem).filter(TripItem.trip_id == plan.id).order_by(TripItem.sort_order).all()

        result = service.generate_package(plan, items)
        # 验证是有效的ZIP
        assert zipfile.is_zipfile(result["file_path"])

    def test_package_contains_required_files(self, db_session):
        """测试离线包包含所有必需文件"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id)
        items = db_session.query(TripItem).filter(TripItem.trip_id == plan.id).order_by(TripItem.sort_order).all()

        result = service.generate_package(plan, items)
        with zipfile.ZipFile(result["file_path"], "r") as zf:
            names = zf.namelist()
            assert "metadata.json" in names
            assert "plan.json" in names
            assert "pois.json" in names
            assert "tiles_meta.json" in names

    def test_package_metadata_content(self, db_session):
        """测试离线包metadata.json内容"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id)
        items = db_session.query(TripItem).filter(TripItem.trip_id == plan.id).order_by(TripItem.sort_order).all()

        result = service.generate_package(plan, items)
        with zipfile.ZipFile(result["file_path"], "r") as zf:
            metadata = json.loads(zf.read("metadata.json"))
            assert metadata["plan_id"] == plan.id
            assert metadata["version"] == 1
            assert "created_at" in metadata
            assert "package_id" in metadata

    def test_package_plan_json_content(self, db_session):
        """测试离线包plan.json内容"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id)
        items = db_session.query(TripItem).filter(TripItem.trip_id == plan.id).order_by(TripItem.sort_order).all()

        result = service.generate_package(plan, items)
        with zipfile.ZipFile(result["file_path"], "r") as zf:
            plan_data = json.loads(zf.read("plan.json"))
            assert plan_data["title"] == "餐后运动计划-消耗300kcal"
            assert len(plan_data["items"]) == 3
            assert plan_data["total_calories"] == 270.0

    def test_package_pois_json_content(self, db_session):
        """测试离线包pois.json内容"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id)
        items = db_session.query(TripItem).filter(TripItem.trip_id == plan.id).order_by(TripItem.sort_order).all()

        result = service.generate_package(plan, items)
        with zipfile.ZipFile(result["file_path"], "r") as zf:
            pois = json.loads(zf.read("pois.json"))
            assert isinstance(pois, list)
            assert len(pois) == 3
            assert pois[0]["name"] == "奥林匹克公园南门"

    def test_version_increment(self, db_session):
        """测试版本自增（同一个plan多次生成）"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id)
        items = db_session.query(TripItem).filter(TripItem.trip_id == plan.id).order_by(TripItem.sort_order).all()

        result1 = service.generate_package(plan, items)
        result2 = service.generate_package(plan, items)
        assert result1["version"] == 1
        assert result2["version"] == 2
        assert result1["package_id"] != result2["package_id"]

    def test_get_package_info(self, db_session):
        """测试获取离线包信息"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id)
        items = db_session.query(TripItem).filter(TripItem.trip_id == plan.id).order_by(TripItem.sort_order).all()

        result = service.generate_package(plan, items)
        info = service.get_package_info(result["package_id"])
        assert info is not None
        assert info["package_id"] == result["package_id"]
        assert info["plan_id"] == plan.id

    def test_get_nonexistent_package(self):
        """测试获取不存在的离线包"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        info = service.get_package_info("nonexistent_id")
        assert info is None

    def test_get_package_file_path(self, db_session):
        """测试获取离线包文件路径"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id)
        items = db_session.query(TripItem).filter(TripItem.trip_id == plan.id).order_by(TripItem.sort_order).all()

        result = service.generate_package(plan, items)
        file_path = service.get_package_file_path(result["package_id"])
        assert file_path is not None
        assert os.path.exists(file_path)

    def test_empty_items_plan(self, db_session):
        """测试空运动项目的计划生成离线包"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id, with_items=False)
        items = []

        result = service.generate_package(plan, items)
        assert result is not None
        assert result["file_size"] > 0
        with zipfile.ZipFile(result["file_path"], "r") as zf:
            plan_data = json.loads(zf.read("plan.json"))
            assert plan_data["total_calories"] == 0.0
            assert len(plan_data["items"]) == 0

    def test_plan_without_coordinates(self, db_session):
        """测试无坐标的计划生成离线包"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id, lat=None, lng=None)
        items = db_session.query(TripItem).filter(TripItem.trip_id == plan.id).order_by(TripItem.sort_order).all()
        # 手动清除item坐标
        for item in items:
            item.latitude = None
            item.longitude = None
        db_session.commit()

        result = service.generate_package(plan, items)
        assert result is not None
        with zipfile.ZipFile(result["file_path"], "r") as zf:
            tiles_meta = json.loads(zf.read("tiles_meta.json"))
            # 无坐标时应返回0
            assert tiles_meta["tile_count_estimate"] == 0

    def test_list_packages_for_plan(self, db_session):
        """测试列出某个计划的所有离线包"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id)
        items = db_session.query(TripItem).filter(TripItem.trip_id == plan.id).order_by(TripItem.sort_order).all()

        service.generate_package(plan, items)
        service.generate_package(plan, items)

        packages = service.list_packages_for_plan(plan.id)
        assert len(packages) == 2
        assert packages[0]["version"] == 1
        assert packages[1]["version"] == 2


# ============================================================
# 第二组：API接口集成测试（使用 FastAPI TestClient）
# ============================================================

class TestOfflinePackageAPI:
    """离线包API接口集成测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.database import get_db
        from app.services.offline_package_service import OfflinePackageService

        # 覆盖数据库依赖
        app.dependency_overrides[get_db] = get_test_db

        # 将 offline_package_service 的 storage_dir 设为测试目录
        with patch("app.routers.trip.offline_package_service",
                   OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)):
            client = TestClient(app)
            yield client

        app.dependency_overrides.clear()

    def test_generate_offline_package_success(self, client, db_session):
        """测试成功生成离线包"""
        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id)

        response = client.post("/api/trip/offline-package", json={
            "plan_id": plan.id,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["plan_id"] == plan.id
        assert data["data"]["package_id"] is not None
        assert data["data"]["version"] == 1
        assert data["data"]["file_size"] > 0

    def test_generate_offline_package_plan_not_found(self, client, db_session):
        """测试生成离线包-计划不存在"""
        response = client.post("/api/trip/offline-package", json={
            "plan_id": 9999,
        })
        assert response.status_code == 404

    def test_generate_offline_package_invalid_plan_id(self, client):
        """测试生成离线包-无效plan_id"""
        response = client.post("/api/trip/offline-package", json={
            "plan_id": 0,
        })
        assert response.status_code == 422

    def test_generate_offline_package_negative_plan_id(self, client):
        """测试生成离线包-负数plan_id"""
        response = client.post("/api/trip/offline-package", json={
            "plan_id": -1,
        })
        assert response.status_code == 422

    def test_download_offline_package_success(self, client, db_session):
        """测试成功下载离线包"""
        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id)

        # 先生成
        gen_resp = client.post("/api/trip/offline-package", json={
            "plan_id": plan.id,
        })
        package_id = gen_resp.json()["data"]["package_id"]

        # 再下载
        dl_resp = client.get(f"/api/trip/offline-package/{package_id}")
        assert dl_resp.status_code == 200
        assert dl_resp.headers["content-type"] == "application/zip"
        # 验证返回的是有效ZIP
        zip_bytes = io.BytesIO(dl_resp.content)
        assert zipfile.is_zipfile(zip_bytes)

    def test_download_nonexistent_package(self, client):
        """测试下载不存在的离线包"""
        dl_resp = client.get("/api/trip/offline-package/nonexistent_id")
        assert dl_resp.status_code == 404

    def test_generate_then_download_verify_content(self, client, db_session):
        """测试生成后下载并验证内容完整性"""
        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id)

        gen_resp = client.post("/api/trip/offline-package", json={
            "plan_id": plan.id,
        })
        package_id = gen_resp.json()["data"]["package_id"]

        dl_resp = client.get(f"/api/trip/offline-package/{package_id}")
        zip_bytes = io.BytesIO(dl_resp.content)
        with zipfile.ZipFile(zip_bytes, "r") as zf:
            names = zf.namelist()
            assert "metadata.json" in names
            assert "plan.json" in names
            assert "pois.json" in names
            assert "tiles_meta.json" in names

            plan_data = json.loads(zf.read("plan.json"))
            assert plan_data["title"] == "餐后运动计划-消耗300kcal"

    def test_version_increment_via_api(self, client, db_session):
        """测试通过API多次生成版本递增"""
        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id)

        resp1 = client.post("/api/trip/offline-package", json={"plan_id": plan.id})
        resp2 = client.post("/api/trip/offline-package", json={"plan_id": plan.id})
        assert resp1.json()["data"]["version"] == 1
        assert resp2.json()["data"]["version"] == 2

    def test_generate_package_empty_plan(self, client, db_session):
        """测试生成空运动项目计划的离线包"""
        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id, with_items=False)

        response = client.post("/api/trip/offline-package", json={
            "plan_id": plan.id,
        })
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["file_size"] > 0

    def test_generate_package_no_coords(self, client, db_session):
        """测试无坐标计划生成离线包"""
        user = create_test_user(db_session)
        plan = create_test_plan(db_session, user_id=user.id, lat=None, lng=None)

        response = client.post("/api/trip/offline-package", json={
            "plan_id": plan.id,
        })
        assert response.status_code == 200


# ============================================================
# 第三组：边缘情况和健壮性测试
# ============================================================

class TestOfflinePackageEdgeCases:
    """边缘情况测试"""

    def test_large_item_count(self, db_session):
        """测试大量运动项目的离线包生成"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan = TripPlan(
            user_id=user.id,
            title="超长计划",
            destination="测试",
            latitude=39.9, longitude=116.4,
            start_date=date(2026, 2, 7),
            end_date=date(2026, 2, 7),
            status="planning",
        )
        db_session.add(plan)
        db_session.flush()

        # 添加50个运动项目
        for i in range(50):
            db_session.add(TripItem(
                trip_id=plan.id, day_index=1,
                place_name=f"运动点{i}",
                place_type="walking",
                duration=5, cost=20.0,
                latitude=39.9 + i * 0.001,
                longitude=116.4 + i * 0.001,
                sort_order=i,
            ))
        db_session.commit()

        items = db_session.query(TripItem).filter(TripItem.trip_id == plan.id).all()
        result = service.generate_package(plan, items)
        assert result["file_size"] > 0
        with zipfile.ZipFile(result["file_path"], "r") as zf:
            pois = json.loads(zf.read("pois.json"))
            assert len(pois) == 50

    def test_special_characters_in_plan_title(self, db_session):
        """测试计划标题含特殊字符"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan = TripPlan(
            user_id=user.id,
            title='测试计划@#$%^&*()',
            destination="测试地点",
            start_date=date(2026, 2, 7),
            end_date=date(2026, 2, 7),
            status="planning",
        )
        db_session.add(plan)
        db_session.commit()

        result = service.generate_package(plan, [])
        assert result is not None
        assert os.path.exists(result["file_path"])

    def test_zero_duration_items(self, db_session):
        """测试时长为0的运动项目"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan = TripPlan(
            user_id=user.id,
            title="零时长计划",
            destination="测试",
            start_date=date(2026, 2, 7),
            end_date=date(2026, 2, 7),
            status="planning",
        )
        db_session.add(plan)
        db_session.flush()

        db_session.add(TripItem(
            trip_id=plan.id, day_index=1,
            place_name="测试点",
            place_type="walking",
            duration=0, cost=0.0,
            sort_order=0,
        ))
        db_session.commit()

        items = db_session.query(TripItem).filter(TripItem.trip_id == plan.id).all()
        result = service.generate_package(plan, items)
        assert result is not None
        with zipfile.ZipFile(result["file_path"], "r") as zf:
            plan_data = json.loads(zf.read("plan.json"))
            assert plan_data["total_duration"] == 0
            assert plan_data["total_calories"] == 0.0

    def test_none_cost_items(self, db_session):
        """测试cost为None的运动项目"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan = TripPlan(
            user_id=user.id,
            title="无热量计划",
            destination="测试",
            start_date=date(2026, 2, 7),
            end_date=date(2026, 2, 7),
            status="planning",
        )
        db_session.add(plan)
        db_session.flush()

        db_session.add(TripItem(
            trip_id=plan.id, day_index=1,
            place_name="测试点",
            place_type="walking",
            duration=30, cost=None,
            sort_order=0,
        ))
        db_session.commit()

        items = db_session.query(TripItem).filter(TripItem.trip_id == plan.id).all()
        result = service.generate_package(plan, items)
        assert result is not None
        with zipfile.ZipFile(result["file_path"], "r") as zf:
            plan_data = json.loads(zf.read("plan.json"))
            assert plan_data["total_calories"] == 0.0

    def test_tile_bounds_single_point(self):
        """测试单点的瓦片区域计算"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        points = [{"latitude": 39.9042, "longitude": 116.4074}]
        tile_meta = service.calculate_tile_bounds(points, padding_km=0.5)
        assert tile_meta["bounds"]["min_lat"] < 39.9042
        assert tile_meta["bounds"]["max_lat"] > 39.9042

    def test_tile_bounds_empty_points(self):
        """测试空点列表的瓦片区域计算"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        tile_meta = service.calculate_tile_bounds([])
        assert tile_meta["tile_count_estimate"] == 0

    def test_tile_bounds_extreme_coordinates(self):
        """测试极端坐标值"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        points = [
            {"latitude": -89.0, "longitude": -179.0},
            {"latitude": 89.0, "longitude": 179.0},
        ]
        tile_meta = service.calculate_tile_bounds(points)
        assert tile_meta["tile_count_estimate"] > 0

    def test_concurrent_package_generation(self, db_session):
        """测试并发生成不同plan的离线包不冲突"""
        from app.services.offline_package_service import OfflinePackageService
        service = OfflinePackageService(storage_dir=TEST_PACKAGE_DIR)

        user = create_test_user(db_session)
        plan1 = create_test_plan(db_session, user_id=user.id)

        # 创建第二个计划
        plan2 = TripPlan(
            user_id=user.id,
            title="第二个计划",
            destination="另一个地方",
            start_date=date(2026, 2, 8),
            end_date=date(2026, 2, 8),
            status="planning",
        )
        db_session.add(plan2)
        db_session.commit()

        items1 = db_session.query(TripItem).filter(TripItem.trip_id == plan1.id).all()
        items2 = []

        result1 = service.generate_package(plan1, items1)
        result2 = service.generate_package(plan2, items2)

        assert result1["package_id"] != result2["package_id"]
        assert os.path.exists(result1["file_path"])
        assert os.path.exists(result2["file_path"])


# ============================================================
# 第四组：Pydantic模型验证测试
# ============================================================

class TestOfflinePackageModels:
    """离线包Pydantic模型验证测试"""

    def test_generate_request_valid(self):
        """测试有效的生成请求"""
        from app.models.trip import OfflinePackageRequest
        req = OfflinePackageRequest(plan_id=1)
        assert req.plan_id == 1

    def test_generate_request_invalid_zero(self):
        """测试plan_id=0的请求"""
        from app.models.trip import OfflinePackageRequest
        with pytest.raises(Exception):
            OfflinePackageRequest(plan_id=0)

    def test_generate_request_invalid_negative(self):
        """测试负数plan_id"""
        from app.models.trip import OfflinePackageRequest
        with pytest.raises(Exception):
            OfflinePackageRequest(plan_id=-5)

    def test_response_model(self):
        """测试响应模型序列化"""
        from app.models.trip import OfflinePackageData, OfflinePackageResponse
        data = OfflinePackageData(
            plan_id=1,
            package_id="pkg_123",
            version=1,
            file_size=1024,
            created_at="2026-02-07T15:00:00",
            tile_bounds=None,
        )
        resp = OfflinePackageResponse(
            code=200,
            message="生成成功",
            data=data,
        )
        d = resp.model_dump()
        assert d["code"] == 200
        assert d["data"]["package_id"] == "pkg_123"


# ============================================================
# 运行入口
# ============================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
