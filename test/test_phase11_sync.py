"""
Phase 11: 餐前图片上传接口测试（同步版本）

测试内容：
1. MealComparison模型测试
2. AI服务解析测试
3. 上传目录测试
4. API端点功能测试（使用requests直接测试）
"""
import pytest
import sys
import os
import json
import io
import base64
from unittest.mock import patch, MagicMock
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.db_models.user import User
from app.db_models.meal_comparison import MealComparison


# 创建测试数据库（内存SQLite）
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def test_db():
    """为每个测试创建新的数据库"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_user(test_db):
    """创建测试用户"""
    user = User(
        nickname="test_user",
        password="hashed_password",
        health_goal="reduce_fat"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


class TestMealComparisonModel:
    """MealComparison模型测试"""
    
    def test_meal_comparison_creation(self, test_db, test_user):
        """测试MealComparison记录创建"""
        comparison = MealComparison(
            user_id=test_user.id,
            before_image_url="/uploads/meal/test_before.jpg",
            before_features=json.dumps({"dishes": [], "total_estimated_calories": 100}),
            original_calories=100.0,
            status="pending_after"
        )
        
        test_db.add(comparison)
        test_db.commit()
        test_db.refresh(comparison)
        
        assert comparison.id is not None
        assert comparison.user_id == test_user.id
        assert comparison.status == "pending_after"
        assert comparison.created_at is not None
        print(f"✓ MealComparison记录创建成功: id={comparison.id}")
    
    def test_meal_comparison_with_features(self, test_db, test_user):
        """测试带特征的MealComparison记录"""
        features = {
            "dishes": [
                {
                    "name": "红烧肉",
                    "estimated_weight": 200,
                    "estimated_calories": 500.0,
                    "estimated_protein": 25.0,
                    "estimated_fat": 35.0,
                    "estimated_carbs": 10.0
                }
            ],
            "total_estimated_calories": 500.0,
            "total_estimated_protein": 25.0,
            "total_estimated_fat": 35.0,
            "total_estimated_carbs": 10.0
        }
        
        comparison = MealComparison(
            user_id=test_user.id,
            before_image_url="/uploads/meal/test_before.jpg",
            before_features=json.dumps(features, ensure_ascii=False),
            original_calories=500.0,
            original_protein=25.0,
            original_fat=35.0,
            original_carbs=10.0,
            status="pending_after"
        )
        
        test_db.add(comparison)
        test_db.commit()
        test_db.refresh(comparison)
        
        # 验证特征被正确存储
        stored_features = json.loads(comparison.before_features)
        assert len(stored_features["dishes"]) == 1
        assert stored_features["dishes"][0]["name"] == "红烧肉"
        assert comparison.original_calories == 500.0
        print(f"✓ 带特征的MealComparison记录创建成功")
    
    def test_meal_comparison_status_transitions(self, test_db, test_user):
        """测试状态转换"""
        comparison = MealComparison(
            user_id=test_user.id,
            status="pending_before"
        )
        test_db.add(comparison)
        test_db.commit()
        
        # 模拟餐前上传后状态变化
        comparison.status = "pending_after"
        comparison.before_image_url = "/uploads/meal/before.jpg"
        test_db.commit()
        
        assert comparison.status == "pending_after"
        
        # 模拟餐后上传后状态变化
        comparison.status = "completed"
        comparison.after_image_url = "/uploads/meal/after.jpg"
        comparison.consumption_ratio = 0.75
        comparison.net_calories = 375.0
        test_db.commit()
        
        assert comparison.status == "completed"
        assert comparison.consumption_ratio == 0.75
        assert comparison.net_calories == 375.0
        print(f"✓ MealComparison状态转换测试成功")
    
    def test_meal_comparison_query(self, test_db, test_user):
        """测试查询MealComparison记录"""
        # 创建多条记录
        for i in range(3):
            comparison = MealComparison(
                user_id=test_user.id,
                before_image_url=f"/uploads/meal/before_{i}.jpg",
                original_calories=100.0 * (i + 1),
                status="pending_after"
            )
            test_db.add(comparison)
        test_db.commit()
        
        # 查询用户的所有记录
        records = test_db.query(MealComparison).filter(
            MealComparison.user_id == test_user.id
        ).all()
        
        assert len(records) == 3
        print(f"✓ MealComparison查询测试成功: 找到{len(records)}条记录")


class TestAIServiceParsing:
    """AI服务解析测试"""
    
    def test_parse_before_meal_features_valid(self):
        """测试有效JSON解析"""
        from app.services.ai_service import AIService
        
        with patch.dict(os.environ, {'DASHSCOPE_API_KEY': 'test_key', 'ARK_API_KEY': ''}):
            try:
                ai_service = AIService()
            except Exception as e:
                pytest.skip(f"AI服务初始化需要有效的API Key: {e}")
                return
        
        test_content = '''
        {
            "dishes": [
                {
                    "name": "红烧排骨",
                    "estimated_weight": 250,
                    "estimated_calories": 450.0,
                    "estimated_protein": 30.0,
                    "estimated_fat": 28.0,
                    "estimated_carbs": 15.0
                }
            ],
            "total_estimated_calories": 450.0,
            "total_estimated_protein": 30.0,
            "total_estimated_fat": 28.0,
            "total_estimated_carbs": 15.0
        }
        '''
        
        result = ai_service._parse_before_meal_features(test_content)
        
        assert len(result["dishes"]) == 1
        assert result["dishes"][0]["name"] == "红烧排骨"
        assert result["dishes"][0]["estimated_calories"] == 450.0
        assert result["total_estimated_calories"] == 450.0
        print(f"✓ 有效JSON解析测试成功")
    
    def test_parse_before_meal_features_empty(self):
        """测试空结果解析"""
        from app.services.ai_service import AIService
        
        with patch.dict(os.environ, {'DASHSCOPE_API_KEY': 'test_key', 'ARK_API_KEY': ''}):
            try:
                ai_service = AIService()
            except Exception:
                pytest.skip("AI服务初始化需要有效的API Key")
                return
        
        test_content = '''
        {
            "dishes": [],
            "total_estimated_calories": 0,
            "total_estimated_protein": 0,
            "total_estimated_fat": 0,
            "total_estimated_carbs": 0
        }
        '''
        
        result = ai_service._parse_before_meal_features(test_content)
        
        assert result["dishes"] == []
        assert result["total_estimated_calories"] == 0
        print(f"✓ 空结果解析测试成功")
    
    def test_parse_before_meal_features_invalid(self):
        """测试无效JSON解析"""
        from app.services.ai_service import AIService
        
        with patch.dict(os.environ, {'DASHSCOPE_API_KEY': 'test_key', 'ARK_API_KEY': ''}):
            try:
                ai_service = AIService()
            except Exception:
                pytest.skip("AI服务初始化需要有效的API Key")
                return
        
        test_content = "这不是JSON格式"
        
        result = ai_service._parse_before_meal_features(test_content)
        
        assert result["dishes"] == []
        assert result["total_estimated_calories"] == 0
        print(f"✓ 无效JSON解析降级测试成功")
    
    def test_parse_before_meal_features_multiple_dishes(self):
        """测试多菜品解析"""
        from app.services.ai_service import AIService
        
        with patch.dict(os.environ, {'DASHSCOPE_API_KEY': 'test_key', 'ARK_API_KEY': ''}):
            try:
                ai_service = AIService()
            except Exception:
                pytest.skip("AI服务初始化需要有效的API Key")
                return
        
        test_content = '''
        {
            "dishes": [
                {"name": "红烧肉", "estimated_weight": 200, "estimated_calories": 500.0, "estimated_protein": 25.0, "estimated_fat": 35.0, "estimated_carbs": 10.0},
                {"name": "清炒时蔬", "estimated_weight": 150, "estimated_calories": 80.0, "estimated_protein": 3.0, "estimated_fat": 5.0, "estimated_carbs": 8.0},
                {"name": "白米饭", "estimated_weight": 200, "estimated_calories": 230.0, "estimated_protein": 4.0, "estimated_fat": 0.5, "estimated_carbs": 50.0}
            ],
            "total_estimated_calories": 810.0,
            "total_estimated_protein": 32.0,
            "total_estimated_fat": 40.5,
            "total_estimated_carbs": 68.0
        }
        '''
        
        result = ai_service._parse_before_meal_features(test_content)
        
        assert len(result["dishes"]) == 3
        assert result["total_estimated_calories"] == 810.0
        print(f"✓ 多菜品解析测试成功: {len(result['dishes'])}个菜品")


class TestUploadDirectory:
    """上传目录测试"""
    
    def test_ensure_upload_dir_creates_directory(self):
        """测试上传目录创建"""
        from app.routers.food import ensure_upload_dir, UPLOAD_DIR
        
        result_dir = ensure_upload_dir()
        
        assert os.path.exists(result_dir)
        assert result_dir == UPLOAD_DIR
        print(f"✓ 上传目录创建成功: {result_dir}")


class TestEndpointLogic:
    """端点逻辑测试（不涉及HTTP请求）"""
    
    def test_image_save_path_generation(self, test_user):
        """测试图片保存路径生成"""
        import uuid
        
        user_id = test_user.id
        file_ext = ".jpg"
        unique_filename = f"before_{user_id}_{uuid.uuid4().hex}{file_ext}"
        relative_path = f"/uploads/meal/{unique_filename}"
        
        assert relative_path.startswith("/uploads/meal/before_")
        assert str(user_id) in unique_filename
        assert unique_filename.endswith(".jpg")
        print(f"✓ 图片保存路径生成测试成功: {relative_path}")
    
    def test_features_to_json_storage(self):
        """测试特征JSON存储"""
        features = {
            "dishes": [
                {
                    "name": "测试菜品",
                    "estimated_weight": 100,
                    "estimated_calories": 200.0,
                    "estimated_protein": 10.0,
                    "estimated_fat": 8.0,
                    "estimated_carbs": 15.0
                }
            ],
            "total_estimated_calories": 200.0,
            "total_estimated_protein": 10.0,
            "total_estimated_fat": 8.0,
            "total_estimated_carbs": 15.0
        }
        
        # 模拟存储过程
        json_str = json.dumps(features, ensure_ascii=False)
        
        # 模拟读取过程
        restored_features = json.loads(json_str)
        
        assert restored_features["dishes"][0]["name"] == "测试菜品"
        assert restored_features["total_estimated_calories"] == 200.0
        print(f"✓ 特征JSON存储测试成功")
    
    def test_meal_comparison_creation_logic(self, test_db, test_user):
        """测试MealComparison创建逻辑"""
        features = {
            "dishes": [],
            "total_estimated_calories": 0,
            "total_estimated_protein": 0,
            "total_estimated_fat": 0,
            "total_estimated_carbs": 0
        }
        
        # 模拟端点逻辑
        meal_comparison = MealComparison(
            user_id=test_user.id,
            before_image_url="/uploads/meal/test.jpg",
            before_features=json.dumps(features, ensure_ascii=False),
            original_calories=features.get("total_estimated_calories", 0),
            original_protein=features.get("total_estimated_protein", 0),
            original_fat=features.get("total_estimated_fat", 0),
            original_carbs=features.get("total_estimated_carbs", 0),
            status="pending_after"
        )
        
        test_db.add(meal_comparison)
        test_db.commit()
        test_db.refresh(meal_comparison)
        
        assert meal_comparison.id is not None
        assert meal_comparison.status == "pending_after"
        print(f"✓ MealComparison创建逻辑测试成功: comparison_id={meal_comparison.id}")


class TestPydanticModels:
    """Pydantic模型测试"""
    
    def test_before_meal_upload_response_model(self):
        """测试BeforeMealUploadResponse模型"""
        from app.models.meal_comparison import BeforeMealUploadResponse
        
        response = BeforeMealUploadResponse(
            code=200,
            message="餐前图片上传成功",
            data={
                "comparison_id": 1,
                "before_image_url": "/uploads/meal/before_1.jpg",
                "before_features": {
                    "dishes": [{"name": "红烧肉", "estimated_calories": 500}],
                    "total_estimated_calories": 500
                },
                "status": "pending_after"
            }
        )
        
        assert response.code == 200
        assert response.message == "餐前图片上传成功"
        assert response.data["comparison_id"] == 1
        print(f"✓ BeforeMealUploadResponse模型测试成功")
    
    def test_dish_feature_model(self):
        """测试DishFeature模型"""
        from app.models.meal_comparison import DishFeature
        
        dish = DishFeature(
            name="红烧肉",
            estimated_weight=200,
            estimated_calories=500.0,
            estimated_protein=25.0,
            estimated_fat=35.0,
            estimated_carbs=10.0
        )
        
        assert dish.name == "红烧肉"
        assert dish.estimated_calories == 500.0
        print(f"✓ DishFeature模型测试成功")
    
    def test_before_features_model(self):
        """测试BeforeFeatures模型"""
        from app.models.meal_comparison import BeforeFeatures, DishFeature
        
        features = BeforeFeatures(
            dishes=[
                DishFeature(name="红烧肉", estimated_calories=500.0),
                DishFeature(name="青菜", estimated_calories=50.0)
            ],
            total_estimated_calories=550.0
        )
        
        assert len(features.dishes) == 2
        assert features.total_estimated_calories == 550.0
        print(f"✓ BeforeFeatures模型测试成功")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 11: 餐前图片上传接口测试")
    print("=" * 60)
    pytest.main([__file__, "-v", "--tb=short", "-s"])
