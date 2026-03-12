"""
用户相关API路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.user import (
    UserPreferencesRequest,
    UserPreferencesResponse,
    UserPreferencesData,
    UserRegistrationRequest,
    UserRegistrationResponse,
    LoginRequest,
    LoginResponse,
    TokenInfo,
    RefreshTokenRequest,
    RefreshTokenResponse,
    DataForgetResponse,
    DataForgetData,
    DeletedCounts,
    AiCallLogResponse,
    AiCallLogListData,
    AiCallLogItem,
    AiCallLogStatsResponse,
    AiCallLogStatsData,
)
from typing import Optional
from app.database import get_db
from app.db_models.user import User
from app.dependencies import get_current_user
from app.services import user_service

router = APIRouter(prefix="/api/user", tags=["用户中心"])


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    userId: int,
    db: Session = Depends(get_db)
):
    """
    获取用户偏好

    - **userId**: 用户ID
    """
    return user_service.get_user_preferences(db, userId)


@router.get("/data", response_model=UserPreferencesResponse)
async def get_user_data_legacy(
    nickname: str,
    password: str,
    db: Session = Depends(get_db)
):
    """
    获取用户偏好（旧版登录接口，兼容保留）

    - **nickname**: 用户昵称
    - **password**: 用户密码

    注意：推荐使用 POST /api/user/login 接口进行登录，该接口返回JWT Token
    """
    return user_service.get_user_data_legacy(db, nickname, password)


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    用户登录（JWT认证）

    - **nickname**: 用户昵称
    - **password**: 用户密码

    返回Access Token和Refresh Token，Access Token有效期30分钟，Refresh Token有效期7天
    """
    return user_service.login(db, request)


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    刷新Access Token

    - **refresh_token**: Refresh Token

    使用有效的Refresh Token获取新的Access Token和Refresh Token
    """
    return user_service.refresh_token(db, request)


@router.put("/preferences", response_model=UserPreferencesResponse)
async def update_user_preferences(
    request: UserPreferencesRequest,
    db: Session = Depends(get_db)
):
    """
    更新用户偏好

    - **userId**: 用户ID
    - **healthGoal**: 健康目标（可选）
    - **allergens**: 过敏原列表（可选）
    - **travelPreference**: 出行偏好（可选）
    - **dailyBudget**: 出行日预算（可选）
    - **weight**: 体重（kg，可选）
    - **height**: 身高（cm，可选）
    - **age**: 年龄（可选）
    - **gender**: 性别（male/female/other，可选）
    """
    return user_service.update_user_preferences(db, request)


@router.get("/me", response_model=UserPreferencesResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录用户信息（需要JWT认证）

    请求头需要包含: Authorization: Bearer <access_token>
    """
    return user_service.get_current_user_info(current_user)


@router.post("/register", response_model=UserRegistrationResponse)
async def register_user(
    request: UserRegistrationRequest,
    db: Session = Depends(get_db)
) -> UserRegistrationResponse:
    """
    注册新用户（密码使用bcrypt加密存储）
    """
    return user_service.register_user(db, request)


@router.delete("/data", response_model=DataForgetResponse)
async def delete_user_data(
    userId: int,
    db: Session = Depends(get_db)
):
    """
    一键"遗忘"功能 - 删除用户所有历史数据，保留账号（Phase 55）

    级联删除以下数据：
    - 饮食记录（diet_record）
    - 运动记录（exercise_record）
    - 餐前餐后对比（meal_comparison）
    - 菜单识别记录（menu_recognition）
    - 运动计划及项目（trip_plan + trip_item）
    - 重置用户偏好设置（保留账号，不删除用户本身）

    - **userId**: 用户ID，必须大于0

    ⚠️ 历史数据删除后不可恢复，但账号保留可继续使用
    """
    return user_service.delete_user_data(db, userId)


# ============================================================
# Phase 56: AI调用记录/日志查看
# ============================================================

@router.get("/ai-logs", response_model=AiCallLogResponse)
async def get_ai_call_logs(
    user_id: int,
    call_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    获取用户AI调用日志列表（Phase 56）

    - **user_id**: 用户ID
    - **call_type**: 调用类型过滤（可选）: food_analysis/menu_recognition/trip_generation/exercise_intent
    - **limit**: 返回数量限制，默认50，最大200
    - **offset**: 偏移量，默认0
    """
    return user_service.get_ai_call_logs(db, user_id, call_type, limit, offset)


@router.get("/ai-logs/stats", response_model=AiCallLogStatsResponse)
async def get_ai_call_log_stats(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    获取用户AI调用统计（Phase 56）

    - **user_id**: 用户ID
    """
    return user_service.get_ai_call_log_stats(db, user_id)
