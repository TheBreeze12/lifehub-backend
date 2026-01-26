"""
修复 trip_plan 表，添加缺失的列
"""
from sqlalchemy import text
from app.database import engine, check_db_connection


def fix_trip_plan_table():
    """添加缺失的列"""
    if not check_db_connection():
        print("❌ 数据库连接失败，请检查配置")
        return False
    
    try:
        with engine.connect() as conn:
            # 需要添加的列列表
            columns_to_add = [
                {
                    "name": "travelers",
                    "definition": "travelers JSON COMMENT '同行人员，JSON格式: [\"本人\", \"父母\"]'"
                },
                {
                    "name": "is_offline",
                    "definition": "is_offline INT DEFAULT 0 COMMENT '是否已下载离线包（0/1）'"
                },
                {
                    "name": "offline_size",
                    "definition": "offline_size INT COMMENT '离线包大小（字节）'"
                },
                {
                    "name": "status",
                    "definition": "status VARCHAR(20) DEFAULT 'planning' COMMENT '状态: planning/ongoing/done'"
                }
            ]
            
            # 检查并添加每个列
            for col in columns_to_add:
                # 检查列是否存在
                check_sql = f"""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'trip_plan'
                AND COLUMN_NAME = '{col["name"]}'
                """
                result = conn.execute(text(check_sql))
                count = result.fetchone()[0]
                
                if count > 0:
                    print(f"✅ {col['name']} 列已存在，跳过")
                else:
                    # 添加列
                    alter_sql = f"ALTER TABLE trip_plan ADD COLUMN {col['definition']}"
                    conn.execute(text(alter_sql))
                    conn.commit()
                    print(f"✅ 成功添加 {col['name']} 列")
            
            print("\n✅ trip_plan 表修复完成！")
            return True
            
    except Exception as e:
        print(f"❌ 修复失败: {str(e)}")
        return False


if __name__ == "__main__":
    print("🔧 开始修复 trip_plan 表...")
    print("=" * 50)
    fix_trip_plan_table()
    print("=" * 50)

