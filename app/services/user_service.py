"""
用户数据服务层
Phase 55: 一键"遗忘"功能 - 用户历史数据清除服务（保留账号）
"""

import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud import (
    diet_record_crud,
    exercise_record_crud,
    meal_comparison_crud,
    menu_recognition_crud,
    trip_item_crud,
    trip_plan_crud,
    user_crud,
)
from app.db_models.user import User
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
from app.utils.auth import (
    get_password_hash,
    verify_password,
    create_tokens,
    verify_refresh_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.services.ai_log_service import get_ai_log_service

logger = logging.getLogger(__name__)


def _build_preferences_data(user: User) -> UserPreferencesData:
    return UserPreferencesData(
        userId=user.id,
        nickname=user.nickname,
        healthGoal=user.health_goal,
        allergens=user.allergens if user.allergens else [],
        travelPreference=user.travel_preference,
        dailyBudget=user.daily_budget,
        weight=user.weight,
        height=user.height,
        age=user.age,
        gender=user.gender,
    )


def get_current_user_info(current_user: User) -> UserPreferencesResponse:
    return UserPreferencesResponse(
        code=200,
        message="获取成功",
        data=_build_preferences_data(current_user),
    )


def get_user_preferences(db: Session, user_id: int) -> UserPreferencesResponse:
    try:
        user = user_crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"用户不存在，userId: {user_id}",
            )
        return UserPreferencesResponse(
            code=200,
            message="获取成功",
            data=_build_preferences_data(user),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户偏好失败: {str(e)}")



def login(db: Session, request: LoginRequest) -> LoginResponse:
    try:
        user = user_crud.get_user_by_nickname(db, request.nickname)
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"用户不存在，nickname: {request.nickname}",
            )

        password_valid = False
        password_valid = verify_password(request.password, user.password)

        if not password_valid:
            raise HTTPException(status_code=401, detail="密码错误")

        access_token, refresh_token = create_tokens(user.id, user.nickname)
        token_info = TokenInfo(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

        return LoginResponse(
            code=200,
            message="登录成功",
            data=_build_preferences_data(user),
            token=token_info,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


def refresh_token(db: Session, request: RefreshTokenRequest) -> RefreshTokenResponse:
    try:
        token_data = verify_refresh_token(request.refresh_token)
        if token_data is None:
            raise HTTPException(status_code=401, detail="无效的Refresh Token")

        user = user_crud.get_user_by_id(db, token_data.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        access_token, refresh_token_value = create_tokens(user.id, user.nickname)
        token_info = TokenInfo(
            access_token=access_token,
            refresh_token=refresh_token_value,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        return RefreshTokenResponse(
            code=200,
            message="Token刷新成功",
            token=token_info,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token刷新失败: {str(e)}")


def update_user_preferences(
    db: Session, request: UserPreferencesRequest
) -> UserPreferencesResponse:
    try:
        user = user_crud.get_user_by_id(db, request.userId)
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"用户不存在，userId: {request.userId}",
            )

        if request.healthGoal is not None:
            user.health_goal = request.healthGoal
        if request.allergens is not None:
            user.allergens = request.allergens
        if request.travelPreference is not None:
            user.travel_preference = request.travelPreference
        if request.dailyBudget is not None:
            user.daily_budget = request.dailyBudget
        if request.weight is not None:
            user.weight = request.weight
        if request.height is not None:
            user.height = request.height
        if request.age is not None:
            user.age = request.age
        if request.gender is not None:
            user.gender = request.gender

        user_crud.save_user(db, user)
        db.commit()
        db.refresh(user)

        return UserPreferencesResponse(
            code=200,
            message="更新成功",
            data=_build_preferences_data(user),
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新用户偏好失败: {str(e)}")


def register_user(db: Session, request: UserRegistrationRequest) -> UserRegistrationResponse:
    try:
        user = user_crud.get_user_by_nickname(db, request.nickname)
        if user:
            raise HTTPException(
                status_code=400,
                detail=f"用户已存在，nickname: {request.nickname}",
            )

        hashed_password = get_password_hash(request.password)
        new_user = User(nickname=request.nickname, password=hashed_password)
        user_crud.create_user(db, new_user)

        return UserRegistrationResponse(
            code=200,
            message="注册成功",
            userId=new_user.id,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"用户注册失败: {str(e)}")


def delete_user_data(db: Session, user_id: int) -> DataForgetResponse:
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="无效的用户ID，必须大于0")
    try:
        result = _delete_user_data_internal(db, user_id)
        return DataForgetResponse(
            code=200,
            message="数据删除成功",
            data=DataForgetData(
                user_id=result["user_id"],
                nickname=result["nickname"],
                deleted_counts=DeletedCounts(**result["deleted_counts"]),
                total_deleted=result["total_deleted"],
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除用户数据失败: {str(e)}")


def get_ai_call_logs(
    db: Session,
    user_id: int,
    call_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> AiCallLogResponse:
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="无效的用户ID")

    if limit <= 0:
        limit = 50
    if limit > 200:
        limit = 200
    if offset < 0:
        offset = 0

    try:
        ai_log_service = get_ai_log_service()
        total, logs = ai_log_service.get_user_ai_logs(
            db, user_id=user_id, call_type=call_type, limit=limit, offset=offset
        )
        log_items = [
            AiCallLogItem(
                id=log.id,
                user_id=log.user_id,
                call_type=log.call_type,
                model_name=log.model_name,
                input_summary=log.input_summary,
                output_summary=log.output_summary,
                success=log.success,
                error_message=log.error_message,
                latency_ms=log.latency_ms,
                token_usage=log.token_usage,
                created_at=log.created_at.strftime("%Y-%m-%d %H:%M:%S")
                if log.created_at
                else None,
            )
            for log in logs
        ]

        return AiCallLogResponse(
            code=200,
            message="获取成功",
            data=AiCallLogListData(total=total, logs=log_items),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取AI调用日志失败: {str(e)}")


def get_ai_call_log_stats(db: Session, user_id: int) -> AiCallLogStatsResponse:
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="无效的用户ID")

    try:
        ai_log_service = get_ai_log_service()
        stats = ai_log_service.get_ai_log_stats(db, user_id=user_id)
        return AiCallLogStatsResponse(
            code=200,
            message="获取成功",
            data=AiCallLogStatsData(**stats),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取AI调用统计失败: {str(e)}")


def _delete_user_data_internal(db: Session, user_id: int) -> Dict[str, Any]:
    """
    完全删除用户的所有数据（一键"遗忘"功能）

    级联删除顺序（考虑外键约束）：
    1. exercise_record（引用 trip_plan.id，需先于 trip_plan 删除）
    2. trip_item（通过 trip_plan cascade 自动删除，但显式删除更安全）
    3. trip_plan
    4. diet_record
    5. meal_comparison
    6. menu_recognition
    7. 重置用户偏好设置（保留账号，不删除用户本身）

    Args:
        db: 数据库会话
        user_id: 要删除的用户ID

    Returns:
        包含删除统计信息的字典

    Raises:
        ValueError: 用户不存在时抛出
    """
    # 查询用户是否存在
    user = user_crud.get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"用户不存在，userId: {user_id}")

    nickname = user.nickname
    deleted_counts = {}

    try:
        # 1. 删除运动记录（引用了trip_plan，需先删除）
        exercise_count = exercise_record_crud.delete_exercise_records_by_user(
            db, user_id
        )
        deleted_counts["exercise_records"] = exercise_count

        # 2. 获取用户的所有运动计划ID，用于删除关联的trip_item
        plan_ids = trip_plan_crud.get_trip_plan_ids_by_user(db, user_id)

        # 3. 删除运动项目（trip_item）
        trip_item_count = 0
        if plan_ids:
            trip_item_count = trip_item_crud.delete_trip_items_by_trip_ids(
                db, plan_ids
            )

        # 4. 删除运动计划
        trip_plan_count = trip_plan_crud.delete_trip_plans_by_user(db, user_id)
        deleted_counts["trip_plans"] = trip_plan_count

        # 5. 删除饮食记录
        diet_count = diet_record_crud.delete_diet_records_by_user(db, user_id)
        deleted_counts["diet_records"] = diet_count

        # 6. 删除餐前餐后对比记录
        meal_comparison_count = meal_comparison_crud.delete_meal_comparisons_by_user(
            db, user_id
        )
        deleted_counts["meal_comparisons"] = meal_comparison_count

        # 7. 删除菜单识别记录
        menu_recognition_count = menu_recognition_crud.delete_menu_recognitions_by_user(
            db, user_id
        )
        deleted_counts["menu_recognitions"] = menu_recognition_count

        # 8. 重置用户偏好设置（保留账号，不删除用户本身）
        user.health_goal = "balanced"
        user.allergens = None
        user.travel_preference = None
        user.daily_budget = None
        user.weight = None
        user.height = None
        user.age = None
        user.gender = None
        user_crud.save_user(db, user)

        # 提交事务
        db.commit()

        total_deleted = sum(deleted_counts.values())

        logger.info(
            f"用户数据删除完成: user_id={user_id}, nickname={nickname}, "
            f"总计删除 {total_deleted} 条记录"
        )

        return {
            "user_id": user_id,
            "nickname": nickname,
            "deleted_counts": deleted_counts,
            "total_deleted": total_deleted,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"删除用户数据失败: user_id={user_id}, error={str(e)}")
        raise
