"""
初始化数据库脚本
首次运行此脚本创建所有数据表
"""
from app.database import init_db, check_db_connection

if __name__ == "__main__":
    print("=" * 50)
    print("📦 数据库初始化脚本")
    print("=" * 50)
    
    # 检查数据库连接
    if not check_db_connection():
        print("\n❌ 数据库连接失败，请检查配置：")
        print("   1. 确认MySQL服务已启动")
        print("   2. 检查 .env 文件中的数据库配置")
        print("   3. 确认数据库 lifehub 已创建")
        print("\n创建数据库命令：")
        print("   CREATE DATABASE lifehub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        exit(1)
    
    # 初始化数据库（创建表）
    print("\n📝 开始创建数据表...")
    try:
        init_db()
        print("\n✅ 数据库初始化完成！")
        print("\n已创建的表：")
        print("  - user (用户表)")
        print("  - diet_record (饮食记录表)")
        print("  - trip_plan (行程计划表)")
        print("  - trip_item (行程节点表)")
    except Exception as e:
        print(f"\n❌ 初始化失败: {str(e)}")
        exit(1)

