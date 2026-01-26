"""
数据库连接配置
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

# 从环境变量读取数据库配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "lifehub")

# 构建数据库URL
# 格式: mysql+pymysql://用户名:密码@主机:端口/数据库名
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# 创建数据库引擎
# echo=True 会在控制台打印SQL语句（开发时有用）
engine = create_engine(
    DATABASE_URL,
    echo=False,  # 生产环境设为False
    pool_pre_ping=True,  # 连接前检查连接是否有效
    pool_recycle=3600,  # 1小时后回收连接
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()


def get_db():
    """
    获取数据库会话（依赖注入）
    使用方式：
    @app.get("/api/xxx")
    async def some_endpoint(db: Session = Depends(get_db)):
        # 使用 db 进行数据库操作
        pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库（创建所有表）
    首次运行时调用此函数创建表结构
    """
    # 导入所有模型，确保它们被注册到Base.metadata
    # 注意：必须在函数内部导入，避免循环导入
    import app.db_models.user
    import app.db_models.diet_record
    import app.db_models.trip_plan
    import app.db_models.trip_item
    import app.db_models.menu_recognition
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建成功！")


def check_db_connection():
    """
    检查数据库连接是否正常
    """
    try:
        with engine.connect() as conn:
            # SQLAlchemy 2.0 需要使用 text() 包装 SQL 语句
            conn.execute(text("SELECT 1"))
        print("✅ 数据库连接成功！")
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {str(e)}")
        return False

