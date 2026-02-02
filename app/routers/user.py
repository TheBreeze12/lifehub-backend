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
    UserRegistrationResponse
)
from app.database import get_db
from app.db_models.user import User

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
            dailyBudget=user.daily_budget
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
async def get_user_preferences(
    nickname: str,
    password: str,
    db: Session = Depends(get_db)
):
    """
    获取用户偏好
    
    - **nickname**: 用户昵称
    - **password**: 用户密码
    """
    try:
        # 查询用户
        user = db.query(User).filter(User.nickname == nickname).first()
        
        if not user:
            raise HTTPException(
                status_code=404, 
                detail=f"用户不存在，nickname: {nickname}"
            )
        
        if user.password != password:
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
            dailyBudget=user.daily_budget
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
            dailyBudget=user.daily_budget
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

@router.post("/register", response_model=UserRegistrationResponse)
async def register_user(
    request: UserRegistrationRequest,
    db: Session = Depends(get_db)
) -> UserRegistrationResponse:
    """
    注册新用户
    """
    new_user = User(
        nickname=request.nickname,
        password=request.password
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
    except Exception as e:
        db.rollback()
        print(f"用户注册失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"用户注册失败: {str(e)}"
        )