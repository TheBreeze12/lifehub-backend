"""
修复 trip_item 表，添加缺失的列
"""
from sqlalchemy import text
from app.database import engine, check_db_connection


def fix_trip_item_table():
    """添加缺失的列"""
    if not check_db_connection():
        print("❌ 数据库连接失败，请检查配置")
        return False
    
    try:
        with engine.connect() as conn:
            # 需要添加的列列表
            columns_to_add = [
                {
                    "name": "latitude",
                    "definition": "latitude FLOAT COMMENT '纬度'"
                },
                {
                    "name": "longitude",
                    "definition": "longitude FLOAT COMMENT '经度'"
                },
                {
                    "name": "sort_order",
                    "definition": "sort_order INT DEFAULT 0 COMMENT '排序序号'"
                }
            ]
            
            # 检查并添加每个列
            for col in columns_to_add:
                # 检查列是否存在
                check_sql = f"""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'trip_item'
                AND COLUMN_NAME = '{col["name"]}'
                """
                result = conn.execute(text(check_sql))
                count = result.fetchone()[0]
                
                if count > 0:
                    print(f"✅ {col['name']} 列已存在，跳过")
                else:
                    # 添加列
                    alter_sql = f"ALTER TABLE trip_item ADD COLUMN {col['definition']}"
                    conn.execute(text(alter_sql))
                    conn.commit()
                    print(f"✅ 成功添加 {col['name']} 列")
            
            print("\n✅ trip_item 表修复完成！")
            return True
            
    except Exception as e:
        print(f"❌ 修复失败: {str(e)}")
        return False


if __name__ == "__main__":
    print("🔧 开始修复 trip_item 表...")
    print("=" * 50)
    fix_trip_item_table()
    print("=" * 50)

