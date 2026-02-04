"""
数据库结构验证测试
验证当前数据库是否包含所有必需的表和字段（Phase 1-11）

测试内容:
1. 验证所有表是否存在
2. 验证user表是否包含Phase 4新增的身体参数字段
3. 验证meal_comparison表是否存在（Phase 10）
4. 验证外键约束是否正确
"""
import os
import sys
from datetime import date, datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import engine, get_db, Base
from app.db_models.user import User
from app.db_models.diet_record import DietRecord
from app.db_models.menu_recognition import MenuRecognition
from app.db_models.trip_plan import TripPlan
from app.db_models.trip_item import TripItem
from app.db_models.meal_comparison import MealComparison


class TestDatabaseSchema:
    """数据库结构测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.inspector = inspect(engine)
        self.tables = self.inspector.get_table_names()
    
    # ==================== 表存在性测试 ====================
    
    def test_all_required_tables_exist(self):
        """测试所有必需的表是否存在"""
        required_tables = [
            'user',
            'diet_record',
            'menu_recognition',
            'trip_plan',
            'trip_item',
            'meal_comparison'  # Phase 10 新增
        ]
        
        for table in required_tables:
            assert table in self.tables, f"缺少表: {table}"
        
        print(f"✅ 所有 {len(required_tables)} 个必需表都存在")
    
    def test_user_table_exists(self):
        """测试user表是否存在"""
        assert 'user' in self.tables, "user表不存在"
        print("✅ user表存在")
    
    def test_meal_comparison_table_exists(self):
        """测试meal_comparison表是否存在（Phase 10）"""
        assert 'meal_comparison' in self.tables, \
            "meal_comparison表不存在，请执行 migrations/phase10_meal_comparison.sql"
        print("✅ meal_comparison表存在（Phase 10）")
    
    # ==================== User表字段测试（Phase 4） ====================
    
    def test_user_table_has_body_params_fields(self):
        """测试user表是否包含Phase 4新增的身体参数字段"""
        columns = {col['name'] for col in self.inspector.get_columns('user')}
        
        phase4_fields = ['weight', 'height', 'age', 'gender']
        missing_fields = [f for f in phase4_fields if f not in columns]
        
        assert not missing_fields, \
            f"user表缺少Phase 4身体参数字段: {missing_fields}，请执行 migrations/phase4_add_body_params.sql"
        
        print(f"✅ user表包含所有Phase 4身体参数字段: {phase4_fields}")
    
    def test_user_table_weight_field(self):
        """测试user表的weight字段"""
        columns = {col['name']: col for col in self.inspector.get_columns('user')}
        
        assert 'weight' in columns, "user表缺少weight字段"
        # weight应该是FLOAT类型
        weight_type = str(columns['weight']['type']).upper()
        assert 'FLOAT' in weight_type or 'REAL' in weight_type or 'DOUBLE' in weight_type, \
            f"weight字段类型不正确，期望FLOAT，实际: {weight_type}"
        
        print("✅ user表weight字段存在且类型正确")
    
    def test_user_table_height_field(self):
        """测试user表的height字段"""
        columns = {col['name']: col for col in self.inspector.get_columns('user')}
        
        assert 'height' in columns, "user表缺少height字段"
        height_type = str(columns['height']['type']).upper()
        assert 'FLOAT' in height_type or 'REAL' in height_type or 'DOUBLE' in height_type, \
            f"height字段类型不正确，期望FLOAT，实际: {height_type}"
        
        print("✅ user表height字段存在且类型正确")
    
    def test_user_table_age_field(self):
        """测试user表的age字段"""
        columns = {col['name']: col for col in self.inspector.get_columns('user')}
        
        assert 'age' in columns, "user表缺少age字段"
        age_type = str(columns['age']['type']).upper()
        assert 'INT' in age_type, f"age字段类型不正确，期望INT，实际: {age_type}"
        
        print("✅ user表age字段存在且类型正确")
    
    def test_user_table_gender_field(self):
        """测试user表的gender字段"""
        columns = {col['name']: col for col in self.inspector.get_columns('user')}
        
        assert 'gender' in columns, "user表缺少gender字段"
        gender_type = str(columns['gender']['type']).upper()
        assert 'VARCHAR' in gender_type or 'CHAR' in gender_type or 'TEXT' in gender_type, \
            f"gender字段类型不正确，期望VARCHAR，实际: {gender_type}"
        
        print("✅ user表gender字段存在且类型正确")
    
    # ==================== meal_comparison表字段测试（Phase 10） ====================
    
    def test_meal_comparison_table_columns(self):
        """测试meal_comparison表的所有必需字段"""
        columns = {col['name'] for col in self.inspector.get_columns('meal_comparison')}
        
        required_columns = [
            'id', 'user_id',
            'before_image_url', 'before_features',
            'after_image_url', 'after_features',
            'consumption_ratio', 'original_calories', 'net_calories',
            'status', 'created_at', 'updated_at'
        ]
        
        missing_columns = [col for col in required_columns if col not in columns]
        
        assert not missing_columns, \
            f"meal_comparison表缺少字段: {missing_columns}"
        
        print(f"✅ meal_comparison表包含所有 {len(required_columns)} 个必需字段")
    
    def test_meal_comparison_nutrient_fields(self):
        """测试meal_comparison表的营养素字段"""
        columns = {col['name'] for col in self.inspector.get_columns('meal_comparison')}
        
        nutrient_fields = [
            'original_protein', 'original_fat', 'original_carbs',
            'net_protein', 'net_fat', 'net_carbs'
        ]
        
        missing_fields = [f for f in nutrient_fields if f not in columns]
        
        assert not missing_fields, \
            f"meal_comparison表缺少营养素字段: {missing_fields}"
        
        print(f"✅ meal_comparison表包含所有营养素字段")
    
    # ==================== 外键约束测试 ====================
    
    def test_meal_comparison_foreign_key(self):
        """测试meal_comparison表的外键约束"""
        fks = self.inspector.get_foreign_keys('meal_comparison')
        
        user_fk_exists = any(
            fk['referred_table'] == 'user' and 'user_id' in fk['constrained_columns']
            for fk in fks
        )
        
        assert user_fk_exists, "meal_comparison表缺少user_id外键约束"
        print("✅ meal_comparison表的user_id外键约束正确")
    
    def test_diet_record_foreign_key(self):
        """测试diet_record表的外键约束"""
        fks = self.inspector.get_foreign_keys('diet_record')
        
        user_fk_exists = any(
            fk['referred_table'] == 'user' and 'user_id' in fk['constrained_columns']
            for fk in fks
        )
        
        assert user_fk_exists, "diet_record表缺少user_id外键约束"
        print("✅ diet_record表的user_id外键约束正确")
    
    def test_trip_item_foreign_key(self):
        """测试trip_item表的外键约束"""
        fks = self.inspector.get_foreign_keys('trip_item')
        
        trip_fk_exists = any(
            fk['referred_table'] == 'trip_plan' and 'trip_id' in fk['constrained_columns']
            for fk in fks
        )
        
        assert trip_fk_exists, "trip_item表缺少trip_id外键约束"
        print("✅ trip_item表的trip_id外键约束正确")


class TestDatabaseOperations:
    """数据库操作测试类 - 测试真实的CRUD操作"""
    
    def get_db_session(self):
        """获取数据库会话"""
        return next(get_db())
    
    def test_create_user_with_body_params(self):
        """测试创建包含身体参数的用户"""
        db = self.get_db_session()
        try:
            # 创建测试用户
            test_user = User(
                nickname=f"test_schema_user_{datetime.now().timestamp()}",
                password="test123456",
                health_goal="reduce_fat",
                weight=70.5,
                height=175.0,
                age=25,
                gender="male"
            )
            
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            
            # 验证
            assert test_user.id is not None, "用户ID不应为空"
            assert test_user.weight == 70.5, "体重值不正确"
            assert test_user.height == 175.0, "身高值不正确"
            assert test_user.age == 25, "年龄值不正确"
            assert test_user.gender == "male", "性别值不正确"
            
            print(f"✅ 成功创建包含身体参数的用户, ID: {test_user.id}")
            
            # 清理
            db.delete(test_user)
            db.commit()
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def test_create_meal_comparison(self):
        """测试创建餐前餐后对比记录"""
        db = self.get_db_session()
        try:
            # 先创建测试用户
            test_user = User(
                nickname=f"test_meal_user_{datetime.now().timestamp()}",
                password="test123456"
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            
            # 创建餐前餐后对比记录
            meal_comparison = MealComparison(
                user_id=test_user.id,
                before_image_url="/uploads/before_test.jpg",
                before_features='{"dishes": [{"name": "番茄炒蛋", "calories": 150}]}',
                original_calories=150.0,
                original_protein=10.5,
                original_fat=8.0,
                original_carbs=6.0,
                status="pending_after"
            )
            
            db.add(meal_comparison)
            db.commit()
            db.refresh(meal_comparison)
            
            # 验证
            assert meal_comparison.id is not None, "对比记录ID不应为空"
            assert meal_comparison.user_id == test_user.id, "用户ID不匹配"
            assert meal_comparison.status == "pending_after", "状态不正确"
            assert meal_comparison.original_calories == 150.0, "原始热量不正确"
            
            print(f"✅ 成功创建餐前餐后对比记录, ID: {meal_comparison.id}")
            
            # 清理
            db.delete(meal_comparison)
            db.delete(test_user)
            db.commit()
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def test_update_meal_comparison_after_image(self):
        """测试更新餐后图片信息"""
        db = self.get_db_session()
        try:
            # 创建测试用户
            test_user = User(
                nickname=f"test_update_user_{datetime.now().timestamp()}",
                password="test123456"
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            
            # 创建餐前记录
            meal_comparison = MealComparison(
                user_id=test_user.id,
                before_image_url="/uploads/before.jpg",
                original_calories=200.0,
                status="pending_after"
            )
            db.add(meal_comparison)
            db.commit()
            db.refresh(meal_comparison)
            
            # 更新餐后信息
            meal_comparison.after_image_url = "/uploads/after.jpg"
            meal_comparison.after_features = '{"remaining": 0.3}'
            meal_comparison.consumption_ratio = 0.7
            meal_comparison.net_calories = 140.0  # 200 * 0.7
            meal_comparison.status = "completed"
            
            db.commit()
            db.refresh(meal_comparison)
            
            # 验证
            assert meal_comparison.after_image_url == "/uploads/after.jpg", "餐后图片URL不正确"
            assert meal_comparison.consumption_ratio == 0.7, "消耗比例不正确"
            assert meal_comparison.net_calories == 140.0, "净摄入热量不正确"
            assert meal_comparison.status == "completed", "状态应为completed"
            
            print(f"✅ 成功更新餐后图片信息, 净摄入热量: {meal_comparison.net_calories} kcal")
            
            # 清理
            db.delete(meal_comparison)
            db.delete(test_user)
            db.commit()
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("LifeHub 数据库结构验证测试")
    print("=" * 60)
    
    # 结构测试
    print("\n📋 数据库结构测试:")
    print("-" * 40)
    schema_test = TestDatabaseSchema()
    schema_test.setup_method()
    
    tests = [
        ("所有必需表存在", schema_test.test_all_required_tables_exist),
        ("user表存在", schema_test.test_user_table_exists),
        ("meal_comparison表存在", schema_test.test_meal_comparison_table_exists),
        ("user表身体参数字段", schema_test.test_user_table_has_body_params_fields),
        ("user表weight字段", schema_test.test_user_table_weight_field),
        ("user表height字段", schema_test.test_user_table_height_field),
        ("user表age字段", schema_test.test_user_table_age_field),
        ("user表gender字段", schema_test.test_user_table_gender_field),
        ("meal_comparison表必需字段", schema_test.test_meal_comparison_table_columns),
        ("meal_comparison表营养素字段", schema_test.test_meal_comparison_nutrient_fields),
        ("meal_comparison外键约束", schema_test.test_meal_comparison_foreign_key),
        ("diet_record外键约束", schema_test.test_diet_record_foreign_key),
        ("trip_item外键约束", schema_test.test_trip_item_foreign_key),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {name}: 异常 - {e}")
            failed += 1
    
    # 操作测试
    print("\n📋 数据库操作测试:")
    print("-" * 40)
    ops_test = TestDatabaseOperations()
    
    ops_tests = [
        ("创建包含身体参数的用户", ops_test.test_create_user_with_body_params),
        ("创建餐前餐后对比记录", ops_test.test_create_meal_comparison),
        ("更新餐后图片信息", ops_test.test_update_meal_comparison_after_image),
    ]
    
    for name, test_func in ops_tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {name}: 异常 - {e}")
            failed += 1
    
    # 汇总
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    if failed > 0:
        print("\n⚠️ 数据库结构不完整，请执行以下迁移脚本:")
        print("   1. migrations/phase4_add_body_params.sql")
        print("   2. migrations/phase10_meal_comparison.sql")
        print("\n   或者使用最新的 create_db.sql 重建数据库")
        return False
    else:
        print("\n✅ 数据库结构验证通过，所有Phase 1-11的表和字段都存在")
        return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
