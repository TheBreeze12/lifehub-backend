"""
行程相关数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, time


class TripPreferences(BaseModel):
    """行程偏好"""
    healthGoal: Optional[str] = Field(None, description="健康目标")
    allergens: Optional[List[str]] = Field(None, description="过敏原列表")


class GenerateTripRequest(BaseModel):
    """生成行程请求（现用于运动计划）"""
    userId: int = Field(..., description="用户ID", gt=0)
    query: str = Field(..., description="用户查询文本", min_length=1, max_length=500)
    preferences: Optional[TripPreferences] = Field(None, description="用户偏好")
    latitude: Optional[float] = Field(None, description="用户当前位置纬度", ge=-90, le=90)
    longitude: Optional[float] = Field(None, description="用户当前位置经度", ge=-180, le=180)
    
    class Config:
        json_schema_extra = {
            "example": {
                "userId": 123,
                "query": "规划周末带娃去杭州玩",
                "preferences": {
                    "healthGoal": "reduce_fat",
                    "allergens": ["海鲜", "花生"]
                }
            }
        }


class TripItemData(BaseModel):
    """行程节点数据"""
    dayIndex: int = Field(..., description="第几天（从1开始）")
    startTime: Optional[str] = Field(None, description="开始时间（HH:mm格式）")
    placeName: str = Field(..., description="地点名称")
    placeType: Optional[str] = Field(None, description="类型: walking/running/cycling/park/gym/indoor/outdoor (运动类型) 或 attraction/dining/transport/accommodation (兼容旧数据)")
    duration: Optional[int] = Field(None, description="预计时长（分钟）")
    cost: Optional[float] = Field(None, description="预计消耗卡路里（kcal），原为费用字段，现语义转换为卡路里")
    notes: Optional[str] = Field(None, description="备注")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dayIndex": 1,
                "startTime": "09:00",
                "placeName": "西湖风景区",
                "placeType": "attraction",
                "duration": 180,
                "notes": "建议游玩3小时"
            }
        }


class TripData(BaseModel):
    """行程数据（现用于运动计划）"""
    tripId: int = Field(..., description="行程ID")
    title: str = Field(..., description="运动计划标题（原为行程标题）")
    destination: Optional[str] = Field(None, description="运动区域/起点（原为目的地）")
    startDate: str = Field(..., description="开始日期（YYYY-MM-DD）")
    endDate: str = Field(..., description="结束日期（YYYY-MM-DD）")
    items: List[TripItemData] = Field(default_factory=list, description="行程节点列表")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tripId": 456,
                "title": "杭州2日亲子游",
                "destination": "杭州",
                "startDate": "2026-01-25",
                "endDate": "2026-01-26",
                "items": [
                    {
                        "dayIndex": 1,
                        "startTime": "09:00",
                        "placeName": "西湖风景区",
                        "placeType": "attraction",
                        "duration": 180,
                        "notes": "建议游玩3小时"
                    }
                ]
            }
        }


class GenerateTripResponse(BaseModel):
    """生成行程响应"""
    code: int = Field(..., description="状态码，200表示成功")
    message: str = Field(..., description="消息")
    data: Optional[TripData] = Field(None, description="行程数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "行程生成成功",
                "data": {
                    "tripId": 456,
                    "title": "杭州2日亲子游",
                    "destination": "杭州",
                    "startDate": "2026-01-25",
                    "endDate": "2026-01-26",
                    "items": []
                }
            }
        }


class TripSummary(BaseModel):
    """行程摘要（用于列表展示，现用于运动计划）"""
    tripId: int = Field(..., description="行程ID")
    title: str = Field(..., description="运动计划标题（原为行程标题）")
    destination: Optional[str] = Field(None, description="运动区域/起点（原为目的地）")
    startDate: str = Field(..., description="开始日期（YYYY-MM-DD）")
    endDate: str = Field(..., description="结束日期（YYYY-MM-DD）")
    status: Optional[str] = Field(None, description="状态: planning/ongoing/done")
    itemCount: int = Field(0, description="行程节点数量")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tripId": 456,
                "title": "杭州2日亲子游",
                "destination": "杭州",
                "startDate": "2026-01-25",
                "endDate": "2026-01-26",
                "status": "planning",
                "itemCount": 5
            }
        }


class TripListResponse(BaseModel):
    """行程列表响应"""
    code: int = Field(..., description="状态码，200表示成功")
    message: str = Field(..., description="消息")
    data: Optional[List[TripSummary]] = Field(None, description="行程列表")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "获取成功",
                "data": [
                    {
                        "tripId": 456,
                        "title": "杭州2日亲子游",
                        "destination": "杭州",
                        "startDate": "2026-01-25",
                        "endDate": "2026-01-26",
                        "status": "planning",
                        "itemCount": 5
                    }
                ]
            }
        }


class TripDetailResponse(BaseModel):
    """行程详情响应"""
    code: int = Field(..., description="状态码，200表示成功")
    message: str = Field(..., description="消息")
    data: Optional[TripData] = Field(None, description="行程详情")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "tripId": 456,
                    "title": "杭州2日亲子游",
                    "destination": "杭州",
                    "startDate": "2026-01-25",
                    "endDate": "2026-01-26",
                    "items": []
                }
            }
        }

