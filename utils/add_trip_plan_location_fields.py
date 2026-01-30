"""
为 trip_plan 表添加位置字段（latitude, longitude）
用于保存用户生成运动计划时的位置信息

使用方法：
    在backend目录下运行：
    python utils/add_trip_plan_location_fields.py
    
    或者：
    cd backend
    python -m utils.add_trip_plan_location_fields
"""
import sys
import os

# 添加backend目录到Python路径，确保可以导入app模块
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import text
from app.database import engine, check_db_connection


def add_trip_plan_location_fields():
    """添加位置字段到 trip_plan 表"""
    if not check_db_connection():
        print("❌ 数据库连接失败，请检查配置")
        return False
    
    try:
        with engine.connect() as conn:
            # 检查字段是否已存在
            check_latitude = text("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'trip_plan' 
                AND COLUMN_NAME = 'latitude'
            """)
            
            check_longitude = text("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'trip_plan' 
                AND COLUMN_NAME = 'longitude'
            """)
            
            result_lat = conn.execute(check_latitude).fetchone()
            result_lon = conn.execute(check_longitude).fetchone()
            
            # 添加 latitude 字段
            if result_lat[0] == 0:
                print("📝 添加 latitude 字段...")
                conn.execute(text("""
                    ALTER TABLE `trip_plan` 
                    ADD COLUMN `latitude` FLOAT DEFAULT NULL 
                    COMMENT '用户生成计划时的位置纬度（可选）' 
                    AFTER `destination`
                """))
                conn.commit()
                print("✅ latitude 字段添加成功")
            else:
                print("ℹ️  latitude 字段已存在，跳过")
            
            # 添加 longitude 字段
            if result_lon[0] == 0:
                print("📝 添加 longitude 字段...")
                conn.execute(text("""
                    ALTER TABLE `trip_plan` 
                    ADD COLUMN `longitude` FLOAT DEFAULT NULL 
                    COMMENT '用户生成计划时的位置经度（可选）' 
                    AFTER `latitude`
                """))
                conn.commit()
                print("✅ longitude 字段添加成功")
            else:
                print("ℹ️  longitude 字段已存在，跳过")
            
            print("\n✅ trip_plan 表位置字段添加完成！")
            return True
            
    except Exception as e:
        print(f"❌ 添加字段失败: {str(e)}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("为 trip_plan 表添加位置字段")
    print("=" * 50)
    add_trip_plan_location_fields()

