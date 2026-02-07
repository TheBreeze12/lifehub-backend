"""
用户相关数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class UserPreferencesRequest(BaseModel):
    """更新用户偏好请求"""
    userId: int = Field(..., description="用户ID", gt=0)
    healthGoal: Optional[str] = Field(
        None, 
        description="健康目标: reduce_fat/gain_muscle/control_sugar/balanced"
    )
    allergens: Optional[List[str]] = Field(
        None, 
        description="过敏原列表，如: [\"海鲜\", \"花生\"]"
    )
    travelPreference: Optional[str] = Field(
        None, 
        description="出行偏好: self_driving/public_transport/walking"
    )
    dailyBudget: Optional[int] = Field(
        None, 
        description="出行日预算（元）", 
        ge=0
    )
    # 身体参数字段（Phase 4新增）
    weight: Optional[float] = Field(
        None,
        description="体重（kg）",
        gt=0,
        le=500
    )
    height: Optional[float] = Field(
        None,
        description="身高（cm）",
        gt=0,
        le=300
    )
    age: Optional[int] = Field(
        None,
        description="年龄",
        gt=0,
        le=150
    )
    gender: Optional[str] = Field(
        None,
        description="性别: male/female/other"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "userId": 123,
                "healthGoal": "reduce_fat",
                "allergens": ["海鲜", "花生"],
                "travelPreference": "self_driving",
                "dailyBudget": 500,
                "weight": 70.5,
                "height": 175.0,
                "age": 25,
                "gender": "male"
            }
        }


class UserPreferencesData(BaseModel):
    """用户偏好数据"""
    userId: int = Field(..., description="用户ID")
    nickname: Optional[str] = Field(None, description="用户昵称")
    healthGoal: Optional[str] = Field(None, description="健康目标")
    allergens: Optional[List[str]] = Field(None, description="过敏原列表")
    travelPreference: Optional[str] = Field(None, description="出行偏好")
    dailyBudget: Optional[int] = Field(None, description="出行日预算（元）")
    # 身体参数字段（Phase 4新增）
    weight: Optional[float] = Field(None, description="体重（kg）")
    height: Optional[float] = Field(None, description="身高（cm）")
    age: Optional[int] = Field(None, description="年龄")
    gender: Optional[str] = Field(None, description="性别: male/female/other")
    
    class Config:
        json_schema_extra = {
            "example": {
                "userId": 123,
                "nickname": "健康达人",
                "healthGoal": "reduce_fat",
                "allergens": ["海鲜", "花生"],
                "travelPreference": "self_driving",
                "dailyBudget": 500,
                "weight": 70.5,
                "height": 175.0,
                "age": 25,
                "gender": "male"
            }
        }


class UserPreferencesResponse(BaseModel):
    """用户偏好API响应"""
    code: int = Field(..., description="状态码，200表示成功")
    message: str = Field(..., description="消息")
    data: Optional[UserPreferencesData] = Field(None, description="用户偏好数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "更新成功",
                "data": {
                    "userId": 123,
                    "nickname": "健康达人",
                    "healthGoal": "reduce_fat",
                    "allergens": ["海鲜", "花生"],
                    "travelPreference": "self_driving",
                    "dailyBudget": 500
                }
            }
        }


class UserRegistrationRequest(BaseModel):
    """用户注册请求"""
    nickname: str = Field(..., description="用户昵称", max_length=50)
    password: str = Field(..., description="用户密码", min_length=6, max_length=128)
    
    class Config:
        json_schema_extra = {
            "example": {
                "nickname": "健康达人",
                "password": "securepassword123"
            }
        }
        
        
class UserRegistrationResponse(BaseModel):
    """用户注册API响应"""
    code: int = Field(..., description="状态码，200表示成功")
    message: str = Field(..., description="消息")
    userId: Optional[int] = Field(None, description="新注册用户的ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "注册成功",
                "userId": 123
            }
        }


class LoginRequest(BaseModel):
    """用户登录请求"""
    nickname: str = Field(..., description="用户昵称", max_length=50)
    password: str = Field(..., description="用户密码", min_length=6, max_length=128)
    
    class Config:
        json_schema_extra = {
            "example": {
                "nickname": "健康达人",
                "password": "securepassword123"
            }
        }


class TokenInfo(BaseModel):
    """Token信息"""
    access_token: str = Field(..., description="Access Token，用于API认证")
    refresh_token: str = Field(..., description="Refresh Token，用于刷新Access Token")
    token_type: str = Field(default="bearer", description="Token类型")
    expires_in: int = Field(..., description="Access Token过期时间（秒）")


class LoginResponse(BaseModel):
    """用户登录API响应（含JWT Token）"""
    code: int = Field(..., description="状态码，200表示成功")
    message: str = Field(..., description="消息")
    data: Optional[UserPreferencesData] = Field(None, description="用户偏好数据")
    token: Optional[TokenInfo] = Field(None, description="JWT Token信息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "登录成功",
                "data": {
                    "userId": 123,
                    "nickname": "健康达人",
                    "healthGoal": "reduce_fat",
                    "allergens": ["海鲜", "花生"],
                    "travelPreference": "self_driving",
                    "dailyBudget": 500
                },
                "token": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 1800
                }
            }
        }


class RefreshTokenRequest(BaseModel):
    """刷新Token请求"""
    refresh_token: str = Field(..., description="Refresh Token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class RefreshTokenResponse(BaseModel):
    """刷新Token响应"""
    code: int = Field(..., description="状态码，200表示成功")
    message: str = Field(..., description="消息")
    token: Optional[TokenInfo] = Field(None, description="新的JWT Token信息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "Token刷新成功",
                "token": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 1800
                }
            }
        }


# ============================================================
# Phase 55: 一键"遗忘"功能 - 用户数据完全删除
# ============================================================

class DeletedCounts(BaseModel):
    """各表删除数量统计"""
    diet_records: int = Field(default=0, description="删除的饮食记录数")
    exercise_records: int = Field(default=0, description="删除的运动记录数")
    meal_comparisons: int = Field(default=0, description="删除的餐前餐后对比数")
    menu_recognitions: int = Field(default=0, description="删除的菜单识别记录数")
    trip_plans: int = Field(default=0, description="删除的运动计划数")


class DataForgetData(BaseModel):
    """数据删除结果"""
    user_id: int = Field(..., description="被删除的用户ID")
    nickname: str = Field(..., description="被删除用户的昵称")
    deleted_counts: DeletedCounts = Field(..., description="各表删除数量")
    total_deleted: int = Field(..., description="总计删除记录数")


class DataForgetResponse(BaseModel):
    """一键遗忘API响应"""
    code: int = Field(..., description="状态码，200表示成功")
    message: str = Field(..., description="消息")
    data: Optional[DataForgetData] = Field(None, description="删除结果数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "数据删除成功",
                "data": {
                    "user_id": 123,
                    "nickname": "健康达人",
                    "deleted_counts": {
                        "diet_records": 15,
                        "exercise_records": 8,
                        "meal_comparisons": 3,
                        "menu_recognitions": 5,
                        "trip_plans": 4
                    },
                    "total_deleted": 35
                }
            }
        }