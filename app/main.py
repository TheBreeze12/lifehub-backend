"""
智能生活服务工具 - FastAPI主应用
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import logging

# 导入数据脱敏中间件
from app.middleware.data_masking import DataMaskingMiddleware, SensitiveDataFilter

# 加载环境变量
load_dotenv()

# 导入路由
from app.routers import food_router
from app.routers import user as user_router
from app.routers import trip as trip_router
from app.routers import weather as weather_router
from app.routers import stats as stats_router
from app.routers import exercise as exercise_router

# 导入数据库
from app.database import check_db_connection, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理（启动和关闭事件）
    替代已弃用的 @app.on_event("startup") 和 @app.on_event("shutdown")
    """
    # 启动时执行
    print("🚀 应用启动中...")
    # 检查数据库连接
    if check_db_connection():
        print("✅ 数据库连接正常")
        # 自动初始化数据库表（如果不存在则创建，已存在则跳过）
        try:
            init_db()
            print("✅ 数据库表初始化完成")
        except Exception as e:
            print(f"⚠️  数据库表初始化警告: {e}")
    else:
        print("⚠️  警告：数据库连接失败，请检查配置")

    yield  # 应用运行期间

    # 关闭时执行（如果需要清理资源，在这里添加）
    print("🛑 应用关闭中...")


# 创建FastAPI应用
app = FastAPI(
    title="智能生活服务工具API",
    description="提供餐饮营养分析、出行规划等AI驱动的生活服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan  # 使用新的lifespan事件处理器
)

# 配置CORS（跨域资源共享）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有来源，生产环境需要限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册数据脱敏中间件（Phase 54）
app.add_middleware(DataMaskingMiddleware)

# 注册日志脱敏过滤器（Phase 54）
for handler in logging.root.handlers:
    handler.addFilter(SensitiveDataFilter())
# 确保uvicorn的logger也加上脱敏过滤器
for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
    _logger = logging.getLogger(logger_name)
    for handler in _logger.handlers:
        handler.addFilter(SensitiveDataFilter())

# 注册路由
app.include_router(food_router)
app.include_router(user_router.router)
app.include_router(trip_router.router)
app.include_router(weather_router.router)
app.include_router(stats_router.router)
app.include_router(exercise_router.router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "智能生活服务工具API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    api_key_set = bool(os.getenv("DASHSCOPE_API_KEY"))
    return {
        "status": "ok",
        "api_key_configured": api_key_set
    }


if __name__ == "__main__":
    import uvicorn
    import sys

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    # 在打包为可执行文件（PyInstaller）时禁用 reload，避免不停重载
    is_frozen = getattr(sys, "frozen", False)
    env_reload = os.getenv("RELOAD")  # 可通过设置 RELOAD=1 在开发模式下强制启用
    reload_enabled = (not is_frozen) and (env_reload == "1" or env_reload is None)
    if is_frozen:
        print("⚙️ 检测到打包运行环境（frozen），禁用自动重载 reload")
    elif env_reload == "0":
        print("⚙️ RELOAD=0，禁用自动重载 reload")
    elif env_reload == "1":
        print("⚙️ RELOAD=1，启用自动重载 reload")

    uvicorn.run(
        app=app,
        host=host,
        port=port,
        reload=reload_enabled
    )
