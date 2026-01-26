"""
数据库连接测试脚本
用于验证数据库配置是否正确
"""
from app.database import check_db_connection, get_db, init_db
from app.db_models import User, DietRecord
from datetime import date
from sqlalchemy.orm import Session

def test_connection():
    """测试数据库连接"""
    print("=" * 50)
    print("🔍 测试数据库连接")
    print("=" * 50)
    
    if check_db_connection():
        print("✅ 数据库连接成功！\n")
        return True
    else:
        print("❌ 数据库连接失败！\n")
        return False


def test_create_tables():
    """测试创建表"""
    print("=" * 50)
    print("📝 测试创建数据表")
    print("=" * 50)
    
    try:
        init_db()
        print("✅ 数据表创建成功！\n")
        return True
    except Exception as e:
        print(f"❌ 创建表失败: {str(e)}\n")
        return False


def test_crud_operations(keep_data=False):
    """测试CRUD操作"""
    print("=" * 50)
    print("🧪 测试数据库操作（CRUD）")
    print("=" * 50)
    
    db: Session = next(get_db())
    test_user_id = None
    record_id = None
    
    try:
        # 1. 创建用户（Create）
        print("1️⃣  创建测试用户...")
        test_user = User(
            nickname="测试用户",
            health_goal="reduce_fat",
            allergens=["海鲜"]
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        test_user_id = test_user.id
        print(f"   ✅ 用户创建成功，ID: {test_user.id}")
        
        # 验证：重新查询确认数据已写入
        print("   🔍 验证：重新查询数据库...")
        verify_user = db.query(User).filter(User.id == test_user.id).first()
        if verify_user:
            print(f"   ✅ 验证成功：数据库中确实存在用户 ID={verify_user.id}, nickname={verify_user.nickname}")
        else:
            print("   ❌ 验证失败：数据库中未找到刚创建的用户！")
            return False
        
        # 2. 查询用户（Read）
        print("\n2️⃣  查询用户...")
        user = db.query(User).filter(User.id == test_user.id).first()
        all_users = db.query(User).all()
        print(f"   ✅ 查询成功，找到 {len(all_users)} 个用户")
        print(f"   📋 用户列表: {[f'ID={u.id}, 昵称={u.nickname}' for u in all_users]}")
        
        # 3. 创建饮食记录
        print("\n3️⃣  创建饮食记录...")
        record = DietRecord(
            user_id=test_user.id,
            food_name="测试菜品",
            calories=200.0,
            protein=15.0,
            fat=10.0,
            carbs=20.0,
            meal_type="lunch",
            record_date=date.today()
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        record_id = record.id
        print(f"   ✅ 记录创建成功，ID: {record.id}")
        
        # 4. 更新用户（Update）
        print("\n4️⃣  更新用户信息...")
        user.nickname = "更新后的昵称"
        db.commit()
        db.refresh(user)  # 刷新以获取最新数据
        print(f"   ✅ 更新成功: {user.nickname}")
        

        # 5. 删除记录（Delete）- 可选
        if not keep_data:
            print("\n5️⃣  删除测试数据...")
            db.delete(record)
            db.delete(user)
            db.commit()
            print("   ✅ 删除成功（测试数据已清理）")
        else:
            print("\n5️⃣  保留测试数据...")
            print(f"   ℹ️  测试数据已保留：")
            print(f"      - 用户 ID: {test_user_id}")
            print(f"      - 记录 ID: {record_id}")
            print(f"   💡 提示：可以使用以下SQL查询数据：")
            print(f"      SELECT * FROM user WHERE id = {test_user_id};")
            print(f"      SELECT * FROM diet_record WHERE id = {record_id};")
        
        print("\n✅ 所有CRUD操作测试通过！\n")
        return True
        
    except Exception as e:
        print(f"\n❌ 操作失败: {str(e)}\n")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 50)
    print("📦 数据库连接测试工具")
    print("=" * 50 + "\n")
    
    # 检查是否要保留测试数据
    keep_data = "--keep" in sys.argv or "-k" in sys.argv
    
    if keep_data:
        print("ℹ️  测试数据将保留在数据库中\n")
    
    # 测试1: 连接
    if not test_connection():
        print("❌ 请先解决数据库连接问题！")
        print("\n检查清单：")
        print("  1. MySQL服务是否启动？")
        print("  2. .env 文件配置是否正确？")
        print("  3. 数据库 LifeHub 是否已创建？")
        exit(1)
    
    # 测试2: 创建表
    if not test_create_tables():
        print("⚠️  表可能已存在，继续测试...\n")
    
    # 测试3: CRUD操作
    if test_crud_operations(keep_data=keep_data):
        print("=" * 50)
        print("🎉 所有测试通过！数据库配置正确！")
        if keep_data:
            print("\n💡 提示：测试数据已保留，可以在数据库中查看")
        print("=" * 50)
    else:
        print("=" * 50)
        print("❌ 测试失败，请检查错误信息")
        print("=" * 50)

