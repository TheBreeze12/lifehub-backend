"""
执行Phase 4数据库迁移脚本
"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_migration():
    """执行数据库迁移"""
    import pymysql
    
    # 从环境变量获取数据库配置
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'lifehub')
    }
    
    print(f"连接数据库: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    
    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        # 检查字段是否已存在
        cursor.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'user' 
            AND COLUMN_NAME IN ('weight', 'height', 'age', 'gender')
        """, (db_config['database'],))
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        print(f"已存在的字段: {existing_columns}")
        
        # 添加缺失的字段
        migrations = [
            ("weight", "ALTER TABLE `user` ADD COLUMN `weight` FLOAT DEFAULT NULL COMMENT '体重（kg）' AFTER `daily_budget`"),
            ("height", "ALTER TABLE `user` ADD COLUMN `height` FLOAT DEFAULT NULL COMMENT '身高（cm）' AFTER `weight`"),
            ("age", "ALTER TABLE `user` ADD COLUMN `age` INT DEFAULT NULL COMMENT '年龄' AFTER `height`"),
            ("gender", "ALTER TABLE `user` ADD COLUMN `gender` VARCHAR(10) DEFAULT NULL COMMENT '性别: male/female/other' AFTER `age`")
        ]
        
        for column_name, sql in migrations:
            if column_name not in existing_columns:
                print(f"添加字段: {column_name}")
                try:
                    cursor.execute(sql)
                    conn.commit()
                    print(f"  ✅ 成功添加 {column_name}")
                except Exception as e:
                    print(f"  ⚠️ 添加 {column_name} 失败: {e}")
            else:
                print(f"  ⏭️ 字段 {column_name} 已存在，跳过")
        
        # 验证结果
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_COMMENT 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'user' 
            AND COLUMN_NAME IN ('weight', 'height', 'age', 'gender')
        """, (db_config['database'],))
        
        print("\n验证迁移结果:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} (nullable={row[2]}) - {row[3]}")
        
        cursor.close()
        conn.close()
        print("\n✅ 数据库迁移完成!")
        return True
        
    except Exception as e:
        print(f"❌ 数据库迁移失败: {e}")
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
