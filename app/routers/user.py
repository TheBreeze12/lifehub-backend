"""
用户相关API路由
"""
from fastapi import APIRouter, HTTPException, Depends
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
from app.utils.auth import (
    get_password_hash,
    verify_password,
    create_tokens,
    verify_refresh_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.dependencies import get_current_user

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
    try:
        # 查询用户
        user = db.query(User).filter(User.id == userId).first()
        
        if not user:
            raise HTTPException(
                status_code=404, 
                detail=f"用户不存在，userId: {userId}"
            )
        
        # 构建响应数据
        preferences_data = UserPreferencesData(
            userId=user.id,
            nickname=user.nickname,
            healthGoal=user.health_goal,
            allergens=user.allergens if user.allergens else [],
            travelPreference=user.travel_preference,
            dailyBudget=user.daily_budget,
            weight=user.weight,
            height=user.height,
            age=user.age,
            gender=user.gender
        )
        
        return UserPreferencesResponse(
            code=200,
            message="获取成功",
            data=preferences_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"获取用户偏好失败: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"获取用户偏好失败: {str(e)}"
        )


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
    try:
        # 查询用户
        user = db.query(User).filter(User.nickname == nickname).first()
        
        if not user:
            raise HTTPException(
                status_code=404, 
                detail=f"用户不存在，nickname: {nickname}"
            )
        
        # 兼容新旧密码验证（新用户使用哈希密码，旧用户使用明文密码）
        password_valid = False
        if user.password.startswith("$2b$"):  # bcrypt哈希密码
            password_valid = verify_password(password, user.password)
        else:
            password_valid = (user.password == password)
        
        if not password_valid:
            raise HTTPException(
                status_code=401,
                detail="密码错误"
            )
        
        # 构建响应数据
        preferences_data = UserPreferencesData(
            userId=user.id,
            nickname=user.nickname,
            healthGoal=user.health_goal,
            allergens=user.allergens if user.allergens else [],
            travelPreference=user.travel_preference,
            dailyBudget=user.daily_budget,
            weight=user.weight,
            height=user.height,
            age=user.age,
            gender=user.gender
        )
        
        return UserPreferencesResponse(
            code=200,
            message="获取成功",
            data=preferences_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"获取用户偏好失败: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"获取用户偏好失败: {str(e)}"
        )


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
    try:
        # 查询用户
        user = db.query(User).filter(User.nickname == request.nickname).first()
        
        if not user:
            raise HTTPException(
                status_code=404, 
                detail=f"用户不存在，nickname: {request.nickname}"
            )
        
        # 兼容新旧密码验证（新用户使用哈希密码，旧用户使用明文密码）
        password_valid = False
        if user.password.startswith("$2b$"):  # bcrypt哈希密码
            password_valid = verify_password(request.password, user.password)
        else:
            password_valid = (user.password == request.password)
        
        if not password_valid:
            raise HTTPException(
                status_code=401,
                detail="密码错误"
            )
        
        # 生成JWT Token
        access_token, refresh_token = create_tokens(user.id, user.nickname)
        
        # 构建响应数据
        preferences_data = UserPreferencesData(
            userId=user.id,
            nickname=user.nickname,
            healthGoal=user.health_goal,
            allergens=user.allergens if user.allergens else [],
            travelPreference=user.travel_preference,
            dailyBudget=user.daily_budget,
            weight=user.weight,
            height=user.height,
            age=user.age,
            gender=user.gender
        )
        
        token_info = TokenInfo(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
        return LoginResponse(
            code=200,
            message="登录成功",
            data=preferences_data,
            token=token_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"登录失败: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"登录失败: {str(e)}"
        )


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
    try:
        # 验证Refresh Token
        token_data = verify_refresh_token(request.refresh_token)
        
        if token_data is None:
            raise HTTPException(
                status_code=401,
                detail="无效的Refresh Token"
            )
        
        # 查询用户确保存在
        user = db.query(User).filter(User.id == token_data.user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="用户不存在"
            )
        
        # 生成新的Token对
        access_token, refresh_token = create_tokens(user.id, user.nickname)
        
        token_info = TokenInfo(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
        return RefreshTokenResponse(
            code=200,
            message="Token刷新成功",
            token=token_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Token刷新失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Token刷新失败: {str(e)}"
        )


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
    try:
        # 查询用户
        user = db.query(User).filter(User.id == request.userId).first()
        
        if not user:
            raise HTTPException(
                status_code=404, 
                detail=f"用户不存在，userId: {request.userId}"
            )
        
        # 更新用户偏好（只更新提供的字段）
        if request.healthGoal is not None:
            user.health_goal = request.healthGoal
        if request.allergens is not None:
            user.allergens = request.allergens
        if request.travelPreference is not None:
            user.travel_preference = request.travelPreference
        if request.dailyBudget is not None:
            user.daily_budget = request.dailyBudget
        # 身体参数字段（Phase 4新增）
        if request.weight is not None:
            user.weight = request.weight
        if request.height is not None:
            user.height = request.height
        if request.age is not None:
            user.age = request.age
        if request.gender is not None:
            user.gender = request.gender
        
        # 保存到数据库
        db.commit()
        db.refresh(user)  # 刷新对象以获取最新数据
        
        # 构建响应数据
        preferences_data = UserPreferencesData(
            userId=user.id,
            nickname=user.nickname,
            healthGoal=user.health_goal,
            allergens=user.allergens if user.allergens else [],
            travelPreference=user.travel_preference,
            dailyBudget=user.daily_budget,
            weight=user.weight,
            height=user.height,
            age=user.age,
            gender=user.gender
        )
        
        return UserPreferencesResponse(
            code=200,
            message="更新成功",
            data=preferences_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()  # 回滚事务
        print(f"更新用户偏好失败: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"更新用户偏好失败: {str(e)}"
        )


@router.get("/me", response_model=UserPreferencesResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录用户信息（需要JWT认证）
    
    请求头需要包含: Authorization: Bearer <access_token>
    """
    preferences_data = UserPreferencesData(
        userId=current_user.id,
        nickname=current_user.nickname,
        healthGoal=current_user.health_goal,
        allergens=current_user.allergens if current_user.allergens else [],
        travelPreference=current_user.travel_preference,
        dailyBudget=current_user.daily_budget,
        weight=current_user.weight,
        height=current_user.height,
        age=current_user.age,
        gender=current_user.gender
    )
    
    return UserPreferencesResponse(
        code=200,
        message="获取成功",
        data=preferences_data
    )


@router.post("/register", response_model=UserRegistrationResponse)
async def register_user(
    request: UserRegistrationRequest,
    db: Session = Depends(get_db)
) -> UserRegistrationResponse:
    """
    注册新用户（密码使用bcrypt加密存储）
    """
    # 使用bcrypt对密码进行哈希加密
    hashed_password = get_password_hash(request.password)
    new_user = User(
        nickname=request.nickname,
        password=hashed_password
    )
    # 如果用户名重复或者其他错误，会在这里抛出异常
    try:
        user = db.query(User).filter(User.nickname == request.nickname).first()
        if user:
            raise HTTPException(
                status_code=400,
                detail=f"用户已存在，nickname: {request.nickname}"
            )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return UserRegistrationResponse(
            code=200,
            message="注册成功",
            userId=new_user.id
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"用户注册失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"用户注册失败: {str(e)}"
        )


@router.delete("/data", response_model=DataForgetResponse)
async def delete_user_data(
    userId: int,
    db: Session = Depends(get_db)
):
    """
    一键"遗忘"功能 - 完全删除用户所有数据（Phase 55）
    
    级联删除以下数据：
    - 饮食记录（diet_record）
    - 运动记录（exercise_record）
    - 餐前餐后对比（meal_comparison）
    - 菜单识别记录（menu_recognition）
    - 运动计划及项目（trip_plan + trip_item）
    - 用户偏好设置及用户本身（user）
    
    - **userId**: 用户ID，必须大于0
    
    ⚠️ 此操作不可逆，删除后数据无法恢复
    """
    if userId <= 0:
        raise HTTPException(
            status_code=400,
            detail="无效的用户ID，必须大于0"
        )

    try:
        from app.services.user_service import delete_user_data as service_delete

        result = service_delete(db, userId)

        return DataForgetResponse(
            code=200,
            message="数据删除成功",
            data=DataForgetData(
                user_id=result["user_id"],
                nickname=result["nickname"],
                deleted_counts=DeletedCounts(**result["deleted_counts"]),
                total_deleted=result["total_deleted"]
            )
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"删除用户数据失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"删除用户数据失败: {str(e)}"
        )


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
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="无效的用户ID")
    
    # 约束limit范围
    if limit <= 0:
        limit = 50
    if limit > 200:
        limit = 200
    if offset < 0:
        offset = 0

    try:
        from app.services.ai_log_service import get_ai_log_service
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
                created_at=log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else None
            )
            for log in logs
        ]

        return AiCallLogResponse(
            code=200,
            message="获取成功",
            data=AiCallLogListData(total=total, logs=log_items)
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"获取AI调用日志失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取AI调用日志失败: {str(e)}"
        )


@router.get("/ai-logs/stats", response_model=AiCallLogStatsResponse)
async def get_ai_call_log_stats(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    获取用户AI调用统计（Phase 56）
    
    - **user_id**: 用户ID
    """
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="无效的用户ID")

    try:
        from app.services.ai_log_service import get_ai_log_service
        ai_log_service = get_ai_log_service()

        stats = ai_log_service.get_ai_log_stats(db, user_id=user_id)

        return AiCallLogStatsResponse(
            code=200,
            message="获取成功",
            data=AiCallLogStatsData(**stats)
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"获取AI调用统计失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取AI调用统计失败: {str(e)}"
        )