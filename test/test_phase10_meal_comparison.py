"""
测试餐前餐后对比数据模型（Phase 10）
- 测试MealComparison数据库模型字段定义
- 测试Pydantic模型验证
- 测试数据库表创建和基本CRUD操作
- 测试模型关联关系
"""
import sys
import os
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime


def print_separator(title: str):
    """打印分隔线"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(success: bool, message: str):
    """打印测试结果"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {message}")
    return success


# ==================== 测试1：SQLAlchemy模型导入和字段定义 ====================

def test_model_import():
    """测试MealComparison模型能否正确导入"""
    print_separator("测试1：模型导入测试")
    
    try:
        from app.db_models.meal_comparison import MealComparison
        from app.db_models import MealComparison as MealComparisonFromInit
        
        # 验证两种导入方式一致
        assert MealComparison is MealComparisonFromInit, "导入的模型不一致"
        
        return print_result(True, "MealComparison模型导入成功")
    except ImportError as e:
        return print_result(False, f"模型导入失败: {e}")
    except Exception as e:
        return print_result(False, f"导入测试异常: {e}")


def test_model_table_name():
    """测试表名定义"""
    print_separator("测试2：表名定义测试")
    
    try:
        from app.db_models.meal_comparison import MealComparison
        
        assert hasattr(MealComparison, '__tablename__'), "缺少__tablename__属性"
        assert MealComparison.__tablename__ == "meal_comparison", f"表名不正确: {MealComparison.__tablename__}"
        
        return print_result(True, f"表名正确: {MealComparison.__tablename__}")
    except Exception as e:
        return print_result(False, f"表名测试失败: {e}")


def test_model_columns():
    """测试模型字段定义"""
    print_separator("测试3：模型字段定义测试")
    
    try:
        from app.db_models.meal_comparison import MealComparison
        from sqlalchemy import inspect
        
        # 获取模型的所有列
        mapper = inspect(MealComparison)
        columns = {col.key: col for col in mapper.columns}
        
        # 必须存在的字段
        required_columns = [
            'id', 'user_id', 
            'before_image_url', 'before_features',
            'after_image_url', 'after_features',
            'consumption_ratio', 'original_calories', 'net_calories',
            'original_protein', 'original_fat', 'original_carbs',
            'net_protein', 'net_fat', 'net_carbs',
            'status', 'comparison_analysis',
            'created_at', 'updated_at'
        ]
        
        missing_columns = []
        for col_name in required_columns:
            if col_name not in columns:
                missing_columns.append(col_name)
        
        if missing_columns:
            return print_result(False, f"缺少字段: {missing_columns}")
        
        print(f"  发现 {len(columns)} 个字段:")
        for col_name in required_columns:
            print(f"    - {col_name}")
        
        return print_result(True, "所有必需字段都已定义")
    except Exception as e:
        return print_result(False, f"字段测试失败: {e}")


def test_model_column_types():
    """测试字段类型"""
    print_separator("测试4：字段类型测试")
    
    try:
        from app.db_models.meal_comparison import MealComparison
        from sqlalchemy import inspect, Integer, String, Float, Text, TIMESTAMP
        
        mapper = inspect(MealComparison)
        columns = {col.key: col for col in mapper.columns}
        
        # 验证关键字段类型
        type_checks = [
            ('id', Integer),
            ('user_id', Integer),
            ('before_image_url', String),
            ('before_features', Text),
            ('consumption_ratio', Float),
            ('net_calories', Float),
            ('status', String),
        ]
        
        all_passed = True
        for col_name, expected_type in type_checks:
            if col_name in columns:
                col = columns[col_name]
                actual_type = type(col.type).__name__
                expected_type_name = expected_type.__name__
                
                # SQLAlchemy类型名称匹配
                if expected_type_name.upper() in actual_type.upper() or actual_type.upper() in expected_type_name.upper():
                    print(f"    ✓ {col_name}: {actual_type}")
                else:
                    print(f"    ✗ {col_name}: 期望 {expected_type_name}, 实际 {actual_type}")
                    all_passed = False
            else:
                print(f"    ✗ {col_name}: 字段不存在")
                all_passed = False
        
        return print_result(all_passed, "字段类型检查完成")
    except Exception as e:
        return print_result(False, f"字段类型测试失败: {e}")


def test_model_foreign_key():
    """测试外键关联"""
    print_separator("测试5：外键关联测试")
    
    try:
        from app.db_models.meal_comparison import MealComparison
        from sqlalchemy import inspect
        
        mapper = inspect(MealComparison)
        
        # 查找user_id列
        user_id_col = None
        for col in mapper.columns:
            if col.key == 'user_id':
                user_id_col = col
                break
        
        if user_id_col is None:
            return print_result(False, "user_id字段不存在")
        
        # 检查外键
        foreign_keys = list(user_id_col.foreign_keys)
        if not foreign_keys:
            return print_result(False, "user_id没有定义外键")
        
        fk = foreign_keys[0]
        target = str(fk.target_fullname)
        
        if 'user.id' in target:
            return print_result(True, f"外键关联正确: user_id -> {target}")
        else:
            return print_result(False, f"外键目标不正确: {target}")
            
    except Exception as e:
        return print_result(False, f"外键测试失败: {e}")


def test_model_relationship():
    """测试模型关联关系"""
    print_separator("测试6：模型关联关系测试")
    
    try:
        from app.db_models.meal_comparison import MealComparison
        from sqlalchemy import inspect
        
        mapper = inspect(MealComparison)
        
        # 检查relationship
        relationships = mapper.relationships
        
        if 'user' in relationships:
            user_rel = relationships['user']
            print(f"    ✓ 存在 'user' relationship")
            print(f"      - 目标: {user_rel.mapper.class_.__name__}")
            return print_result(True, "关联关系定义正确")
        else:
            # 检查是否有backref
            from app.db_models.user import User
            user_mapper = inspect(User)
            if 'meal_comparisons' in user_mapper.relationships:
                print(f"    ✓ User.meal_comparisons backref 存在")
                return print_result(True, "关联关系定义正确（通过backref）")
            
            return print_result(False, "未找到user关联关系")
            
    except Exception as e:
        return print_result(False, f"关联关系测试失败: {e}")


def test_model_default_status():
    """测试status字段默认值"""
    print_separator("测试7：status字段默认值测试")
    
    try:
        from app.db_models.meal_comparison import MealComparison
        from sqlalchemy import inspect
        
        mapper = inspect(MealComparison)
        
        status_col = None
        for col in mapper.columns:
            if col.key == 'status':
                status_col = col
                break
        
        if status_col is None:
            return print_result(False, "status字段不存在")
        
        default = status_col.default
        if default:
            default_value = default.arg if hasattr(default, 'arg') else str(default)
            print(f"    status默认值: {default_value}")
            if 'pending_before' in str(default_value):
                return print_result(True, "status默认值正确: pending_before")
        
        return print_result(False, "status默认值不正确或未设置")
            
    except Exception as e:
        return print_result(False, f"默认值测试失败: {e}")


# ==================== 测试2：Pydantic模型验证 ====================

def test_pydantic_models_import():
    """测试Pydantic模型导入"""
    print_separator("测试8：Pydantic模型导入测试")
    
    try:
        from app.models.meal_comparison import (
            BeforeMealUploadResponse,
            AfterMealUploadResponse,
            MealComparisonData,
            MealComparisonListResponse,
            MealComparisonDetailResponse,
            AdjustConsumptionRequest,
            AdjustConsumptionResponse,
            DishFeature,
            BeforeFeatures,
            RemainingDishFeature,
            AfterFeatures
        )
        
        models = [
            'BeforeMealUploadResponse',
            'AfterMealUploadResponse', 
            'MealComparisonData',
            'MealComparisonListResponse',
            'MealComparisonDetailResponse',
            'AdjustConsumptionRequest',
            'AdjustConsumptionResponse',
            'DishFeature',
            'BeforeFeatures',
            'RemainingDishFeature',
            'AfterFeatures'
        ]
        
        print(f"  成功导入 {len(models)} 个Pydantic模型:")
        for model in models:
            print(f"    - {model}")
        
        return print_result(True, "所有Pydantic模型导入成功")
    except ImportError as e:
        return print_result(False, f"Pydantic模型导入失败: {e}")
    except Exception as e:
        return print_result(False, f"导入测试异常: {e}")


def test_pydantic_dish_feature_validation():
    """测试DishFeature模型验证"""
    print_separator("测试9：DishFeature模型验证测试")
    
    try:
        from app.models.meal_comparison import DishFeature
        
        # 测试有效数据
        valid_dish = DishFeature(
            name="红烧肉",
            estimated_weight=200,
            estimated_calories=500,
            estimated_protein=25.0,
            estimated_fat=35.0,
            estimated_carbs=10.0
        )
        
        assert valid_dish.name == "红烧肉"
        assert valid_dish.estimated_calories == 500
        print(f"    ✓ 有效数据验证通过")
        
        # 测试必填字段
        try:
            invalid_dish = DishFeature(name="测试")  # 缺少estimated_calories
            return print_result(False, "应该拒绝缺少必填字段的数据")
        except Exception:
            print(f"    ✓ 正确拒绝缺少必填字段的数据")
        
        # 测试可选字段
        minimal_dish = DishFeature(
            name="清炒时蔬",
            estimated_calories=80
        )
        assert minimal_dish.estimated_weight is None
        print(f"    ✓ 可选字段正确处理")
        
        return print_result(True, "DishFeature模型验证正确")
    except Exception as e:
        return print_result(False, f"验证测试失败: {e}")


def test_pydantic_adjust_consumption_request():
    """测试AdjustConsumptionRequest模型验证"""
    print_separator("测试10：AdjustConsumptionRequest验证测试")
    
    try:
        from app.models.meal_comparison import AdjustConsumptionRequest
        
        # 测试有效数据
        valid_request = AdjustConsumptionRequest(
            userId=1,
            consumptionRatio=0.75
        )
        assert valid_request.userId == 1
        assert valid_request.consumptionRatio == 0.75
        print(f"    ✓ 有效数据验证通过")
        
        # 测试边界值 - consumptionRatio = 0
        edge_request = AdjustConsumptionRequest(userId=1, consumptionRatio=0)
        assert edge_request.consumptionRatio == 0
        print(f"    ✓ 边界值0验证通过")
        
        # 测试边界值 - consumptionRatio = 1
        edge_request = AdjustConsumptionRequest(userId=1, consumptionRatio=1)
        assert edge_request.consumptionRatio == 1
        print(f"    ✓ 边界值1验证通过")
        
        # 测试无效值 - userId <= 0
        try:
            invalid_request = AdjustConsumptionRequest(userId=0, consumptionRatio=0.5)
            return print_result(False, "应该拒绝userId=0")
        except Exception:
            print(f"    ✓ 正确拒绝userId=0")
        
        # 测试无效值 - consumptionRatio > 1
        try:
            invalid_request = AdjustConsumptionRequest(userId=1, consumptionRatio=1.5)
            return print_result(False, "应该拒绝consumptionRatio>1")
        except Exception:
            print(f"    ✓ 正确拒绝consumptionRatio>1")
        
        # 测试无效值 - consumptionRatio < 0
        try:
            invalid_request = AdjustConsumptionRequest(userId=1, consumptionRatio=-0.1)
            return print_result(False, "应该拒绝consumptionRatio<0")
        except Exception:
            print(f"    ✓ 正确拒绝consumptionRatio<0")
        
        return print_result(True, "AdjustConsumptionRequest验证正确")
    except Exception as e:
        return print_result(False, f"验证测试失败: {e}")


def test_pydantic_meal_comparison_data():
    """测试MealComparisonData模型"""
    print_separator("测试11：MealComparisonData模型测试")
    
    try:
        from app.models.meal_comparison import MealComparisonData
        
        # 测试完整数据
        full_data = MealComparisonData(
            id=1,
            userId=123,
            beforeImageUrl="/uploads/meal/before_1.jpg",
            afterImageUrl="/uploads/meal/after_1.jpg",
            beforeFeatures={"dishes": [{"name": "红烧肉", "estimated_calories": 500}]},
            afterFeatures={"dishes": [{"name": "红烧肉", "remaining_ratio": 0.25}]},
            consumptionRatio=0.75,
            originalCalories=580,
            netCalories=435,
            originalProtein=25.0,
            originalFat=35.0,
            originalCarbs=15.0,
            netProtein=18.75,
            netFat=26.25,
            netCarbs=11.25,
            status="completed",
            comparisonAnalysis="您大约吃掉了75%的食物",
            createdAt="2026-02-04T12:00:00",
            updatedAt="2026-02-04T12:30:00"
        )
        
        assert full_data.id == 1
        assert full_data.userId == 123
        assert full_data.consumptionRatio == 0.75
        assert full_data.netCalories == 435
        assert full_data.status == "completed"
        print(f"    ✓ 完整数据模型验证通过")
        
        # 测试最小必需数据
        minimal_data = MealComparisonData(
            id=2,
            userId=456,
            status="pending_before",
            createdAt="2026-02-04T12:00:00",
            updatedAt="2026-02-04T12:00:00"
        )
        
        assert minimal_data.id == 2
        assert minimal_data.beforeImageUrl is None
        assert minimal_data.netCalories is None
        print(f"    ✓ 最小数据模型验证通过")
        
        return print_result(True, "MealComparisonData模型验证正确")
    except Exception as e:
        return print_result(False, f"验证测试失败: {e}")


def test_pydantic_before_after_features():
    """测试BeforeFeatures和AfterFeatures模型"""
    print_separator("测试12：BeforeFeatures和AfterFeatures模型测试")
    
    try:
        from app.models.meal_comparison import (
            DishFeature, BeforeFeatures, 
            RemainingDishFeature, AfterFeatures
        )
        
        # 测试BeforeFeatures
        before = BeforeFeatures(
            dishes=[
                DishFeature(name="红烧肉", estimated_calories=500),
                DishFeature(name="清炒时蔬", estimated_calories=80)
            ],
            total_estimated_calories=580,
            total_estimated_protein=30.0,
            total_estimated_fat=38.0,
            total_estimated_carbs=15.0
        )
        
        assert len(before.dishes) == 2
        assert before.total_estimated_calories == 580
        print(f"    ✓ BeforeFeatures验证通过")
        
        # 测试AfterFeatures
        after = AfterFeatures(
            dishes=[
                RemainingDishFeature(name="红烧肉", remaining_ratio=0.25),
                RemainingDishFeature(name="清炒时蔬", remaining_ratio=0.0)
            ],
            overall_remaining_ratio=0.25
        )
        
        assert len(after.dishes) == 2
        assert after.overall_remaining_ratio == 0.25
        print(f"    ✓ AfterFeatures验证通过")
        
        # 测试RemainingDishFeature边界值
        try:
            invalid_remaining = RemainingDishFeature(name="测试", remaining_ratio=1.5)
            return print_result(False, "应该拒绝remaining_ratio>1")
        except Exception:
            print(f"    ✓ 正确拒绝remaining_ratio>1")
        
        return print_result(True, "特征模型验证正确")
    except Exception as e:
        return print_result(False, f"验证测试失败: {e}")


# ==================== 测试3：数据库表创建测试 ====================

def test_database_table_creation():
    """测试数据库表能否正常创建"""
    print_separator("测试13：数据库表创建测试")
    
    try:
        from app.database import engine, Base
        from app.db_models.meal_comparison import MealComparison
        
        # 检查表是否在metadata中
        if 'meal_comparison' in Base.metadata.tables:
            print(f"    ✓ meal_comparison表已在metadata中注册")
        else:
            return print_result(False, "meal_comparison表未在metadata中注册")
        
        # 尝试创建表（如果不存在）
        # 注意：这不会删除已存在的表
        Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables['meal_comparison']])
        print(f"    ✓ 表创建语句执行成功")
        
        # 检查表是否真的存在
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'meal_comparison' in tables:
            print(f"    ✓ meal_comparison表在数据库中存在")
            
            # 检查列
            columns = inspector.get_columns('meal_comparison')
            print(f"    ✓ 表有 {len(columns)} 个列")
            
            return print_result(True, "数据库表创建成功")
        else:
            return print_result(False, "meal_comparison表未在数据库中创建")
            
    except Exception as e:
        return print_result(False, f"数据库测试失败: {e}")


def test_database_crud_operations():
    """测试基本CRUD操作"""
    print_separator("测试14：数据库CRUD操作测试")
    
    try:
        from app.database import SessionLocal
        from app.db_models.meal_comparison import MealComparison
        from app.db_models.user import User
        import json
        
        db = SessionLocal()
        
        try:
            # 首先确保有一个测试用户
            test_user = db.query(User).filter(User.nickname == "phase10_test_user").first()
            if not test_user:
                test_user = User(
                    nickname="phase10_test_user",
                    password="test123"
                )
                db.add(test_user)
                db.commit()
                db.refresh(test_user)
                print(f"    ✓ 创建测试用户: id={test_user.id}")
            else:
                print(f"    ✓ 使用现有测试用户: id={test_user.id}")
            
            # CREATE - 创建记录
            new_comparison = MealComparison(
                user_id=test_user.id,
                before_image_url="/test/before.jpg",
                before_features=json.dumps({"dishes": [{"name": "测试菜品", "calories": 300}]}),
                status="pending_after"
            )
            db.add(new_comparison)
            db.commit()
            db.refresh(new_comparison)
            comparison_id = new_comparison.id
            print(f"    ✓ CREATE: 创建记录成功, id={comparison_id}")
            
            # READ - 读取记录
            read_comparison = db.query(MealComparison).filter(MealComparison.id == comparison_id).first()
            assert read_comparison is not None
            assert read_comparison.before_image_url == "/test/before.jpg"
            print(f"    ✓ READ: 读取记录成功")
            
            # UPDATE - 更新记录
            read_comparison.after_image_url = "/test/after.jpg"
            read_comparison.consumption_ratio = 0.75
            read_comparison.original_calories = 300
            read_comparison.net_calories = 225
            read_comparison.status = "completed"
            db.commit()
            
            updated_comparison = db.query(MealComparison).filter(MealComparison.id == comparison_id).first()
            assert updated_comparison.status == "completed"
            assert updated_comparison.net_calories == 225
            print(f"    ✓ UPDATE: 更新记录成功")
            
            # DELETE - 删除记录
            db.delete(updated_comparison)
            db.commit()
            
            deleted_comparison = db.query(MealComparison).filter(MealComparison.id == comparison_id).first()
            assert deleted_comparison is None
            print(f"    ✓ DELETE: 删除记录成功")
            
            return print_result(True, "CRUD操作全部成功")
            
        finally:
            db.close()
            
    except Exception as e:
        return print_result(False, f"CRUD测试失败: {e}")


def test_user_relationship():
    """测试用户关联关系"""
    print_separator("测试15：用户关联关系测试")
    
    try:
        from app.database import SessionLocal
        from app.db_models.meal_comparison import MealComparison
        from app.db_models.user import User
        import json
        
        db = SessionLocal()
        
        try:
            # 获取测试用户
            test_user = db.query(User).filter(User.nickname == "phase10_test_user").first()
            if not test_user:
                test_user = User(nickname="phase10_test_user", password="test123")
                db.add(test_user)
                db.commit()
                db.refresh(test_user)
            
            # 创建关联的MealComparison
            comparison = MealComparison(
                user_id=test_user.id,
                status="pending_before"
            )
            db.add(comparison)
            db.commit()
            db.refresh(comparison)
            
            # 测试通过comparison访问user
            assert comparison.user is not None
            assert comparison.user.id == test_user.id
            print(f"    ✓ comparison.user 关联正确")
            
            # 测试通过user访问meal_comparisons
            db.refresh(test_user)  # 刷新以获取最新关联
            comparisons = test_user.meal_comparisons
            assert len(comparisons) > 0
            print(f"    ✓ user.meal_comparisons 包含 {len(comparisons)} 条记录")
            
            # 清理测试数据
            db.delete(comparison)
            db.commit()
            
            return print_result(True, "关联关系测试成功")
            
        finally:
            db.close()
            
    except Exception as e:
        return print_result(False, f"关联关系测试失败: {e}")


# ==================== 主测试函数 ====================

def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("  Phase 10: 餐前餐后对比数据模型测试")
    print("="*60)
    
    results = []
    
    # 模型定义测试
    results.append(("模型导入", test_model_import()))
    results.append(("表名定义", test_model_table_name()))
    results.append(("字段定义", test_model_columns()))
    results.append(("字段类型", test_model_column_types()))
    results.append(("外键关联", test_model_foreign_key()))
    results.append(("关联关系", test_model_relationship()))
    results.append(("默认值", test_model_default_status()))
    
    # Pydantic模型测试
    results.append(("Pydantic导入", test_pydantic_models_import()))
    results.append(("DishFeature验证", test_pydantic_dish_feature_validation()))
    results.append(("AdjustConsumptionRequest验证", test_pydantic_adjust_consumption_request()))
    results.append(("MealComparisonData验证", test_pydantic_meal_comparison_data()))
    results.append(("BeforeAfterFeatures验证", test_pydantic_before_after_features()))
    
    # 数据库测试（需要数据库连接）
    try:
        from app.database import check_db_connection
        if check_db_connection():
            results.append(("数据库表创建", test_database_table_creation()))
            results.append(("CRUD操作", test_database_crud_operations()))
            results.append(("用户关联", test_user_relationship()))
        else:
            print("\n⚠️ 跳过数据库测试（数据库未连接）")
    except Exception as e:
        print(f"\n⚠️ 跳过数据库测试: {e}")
    
    # 打印测试总结
    print("\n" + "="*60)
    print("  测试总结")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n  总计: {passed}/{total} 通过")
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
