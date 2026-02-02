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
    
    class Config:
        json_schema_extra = {
            "example": {
                "userId": 123,
                "healthGoal": "reduce_fat",
                "allergens": ["海鲜", "花生"],
                "travelPreference": "self_driving",
                "dailyBudget": 500
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
    
    class Config:
        json_schema_extra = {
            "example": {
                "userId": 123,
                "nickname": "健康达人",
                "healthGoal": "reduce_fat",
                "allergens": ["海鲜", "花生"],
                "travelPreference": "self_driving",
                "dailyBudget": 500
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