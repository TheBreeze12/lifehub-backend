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
    cost: Optional[float] = Field(None, description="预计消耗卡路里（kcal），基于METs公式精准计算")
    notes: Optional[str] = Field(None, description="备注（包含METs计算依据）")
    metsValue: Optional[float] = Field(None, description="METs值（Phase 19新增）")
    calculationBasis: Optional[str] = Field(None, description="热量计算依据（Phase 19新增）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dayIndex": 1,
                "startTime": "19:00",
                "placeName": "北京中央公园",
                "placeType": "walking",
                "duration": 30,
                "cost": 122.5,
                "notes": "餐后散步，建议慢走",
                "metsValue": 3.5,
                "calculationBasis": "METs=3.5 × 70kg × 0.5h"
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


# ==================== Phase 22: 帕累托最优路径模型 ====================

class RouteWaypoint(BaseModel):
    """路径点"""
    lat: float = Field(..., description="纬度", ge=-90, le=90)
    lng: float = Field(..., description="经度", ge=-180, le=180)
    order: int = Field(0, description="顺序")
    type: str = Field("waypoint", description="类型: start/waypoint/end")
    
    class Config:
        json_schema_extra = {
            "example": {
                "lat": 39.9042,
                "lng": 116.4074,
                "order": 0,
                "type": "start"
            }
        }


class ParetoRoute(BaseModel):
    """帕累托最优路径"""
    route_id: int = Field(..., description="路径ID")
    route_name: str = Field(..., description="路径名称（如：最短时间、最大消耗、最佳绿化）")
    time_minutes: float = Field(..., description="预计时间（分钟）", ge=0)
    calories_burn: float = Field(..., description="热量消耗（kcal）", ge=0)
    greenery_score: float = Field(..., description="绿化评分（0-100）", ge=0, le=100)
    distance_meters: float = Field(..., description="距离（米）", ge=0)
    waypoints: List[RouteWaypoint] = Field(default_factory=list, description="路径点列表")
    exercise_type: Optional[str] = Field(None, description="运动类型")
    intensity: Optional[float] = Field(None, description="运动强度（0-1）", ge=0, le=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "route_id": 1,
                "route_name": "最短时间",
                "time_minutes": 25.5,
                "calories_burn": 150.0,
                "greenery_score": 45.0,
                "distance_meters": 2100,
                "waypoints": [
                    {"lat": 39.9042, "lng": 116.4074, "order": 0, "type": "start"},
                    {"lat": 39.9052, "lng": 116.4084, "order": 1, "type": "waypoint"},
                    {"lat": 39.9042, "lng": 116.4074, "order": 2, "type": "end"}
                ],
                "exercise_type": "walking",
                "intensity": 0.8
            }
        }


class GenerateRoutesRequest(BaseModel):
    """生成帕累托路径请求"""
    start_lat: float = Field(..., description="起点纬度", ge=-90, le=90)
    start_lng: float = Field(..., description="起点经度", ge=-180, le=180)
    target_calories: float = Field(..., description="目标热量消耗（kcal）", gt=0)
    max_time_minutes: Optional[int] = Field(60, description="最大运动时间（分钟）", gt=0, le=240)
    exercise_type: Optional[str] = Field("walking", description="运动类型: walking/running/cycling/jogging/hiking")
    weight_kg: Optional[float] = Field(70.0, description="用户体重（kg）", gt=0, le=500)
    
    class Config:
        json_schema_extra = {
            "example": {
                "start_lat": 39.9042,
                "start_lng": 116.4074,
                "target_calories": 300,
                "max_time_minutes": 60,
                "exercise_type": "walking",
                "weight_kg": 70.0
            }
        }


class RoutesResponseData(BaseModel):
    """路径响应数据"""
    routes: List[ParetoRoute] = Field(default_factory=list, description="帕累托最优路径列表（2-3条）")
    start_point: RouteWaypoint = Field(..., description="起点坐标")
    target_calories: float = Field(..., description="目标热量消耗")
    max_time_minutes: int = Field(..., description="最大运动时间")
    exercise_type: str = Field(..., description="运动类型")
    weight_kg: float = Field(..., description="用户体重")
    n_routes: int = Field(..., description="返回的路径数量")
    
    class Config:
        json_schema_extra = {
            "example": {
                "routes": [],
                "start_point": {"lat": 39.9042, "lng": 116.4074, "order": 0, "type": "start"},
                "target_calories": 300,
                "max_time_minutes": 60,
                "exercise_type": "walking",
                "weight_kg": 70.0,
                "n_routes": 3
            }
        }


class GenerateRoutesResponse(BaseModel):
    """生成帕累托路径响应"""
    code: int = Field(..., description="状态码，200表示成功")
    message: str = Field(..., description="消息")
    data: Optional[RoutesResponseData] = Field(None, description="路径数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "路径生成成功",
                "data": {
                    "routes": [],
                    "start_point": {"lat": 39.9042, "lng": 116.4074, "order": 0, "type": "start"},
                    "target_calories": 300,
                    "max_time_minutes": 60,
                    "exercise_type": "walking",
                    "weight_kg": 70.0,
                    "n_routes": 3
                }
            }
        }


# ==================== Phase 32: 天气动态调整 Plan B 模型 ====================

class WeatherAssessment(BaseModel):
    """天气评估结果"""
    is_bad_weather: bool = Field(..., description="是否恶劣天气")
    severity: str = Field(..., description="严重程度: good/mild/moderate/severe/unknown")
    description: str = Field("", description="天气描述（中文）")
    temperature: Optional[float] = Field(None, description="当前温度（℃）")
    windspeed: Optional[float] = Field(None, description="风速（km/h）")
    weathercode: Optional[int] = Field(None, description="WMO天气代码")
    recommendation: str = Field("", description="建议")
    warnings: Optional[List[str]] = Field(None, description="警告列表")

    class Config:
        json_schema_extra = {
            "example": {
                "is_bad_weather": True,
                "severity": "moderate",
                "description": "中雨",
                "temperature": 18.0,
                "windspeed": 15.0,
                "weathercode": 63,
                "recommendation": "天气不佳，建议改为室内运动",
                "warnings": None
            }
        }


class PlanBAlternative(BaseModel):
    """Plan B 室内替代运动项"""
    exercise_name: str = Field(..., description="运动名称")
    exercise_type: str = Field(..., description="运动类型代码")
    duration: int = Field(..., description="建议时长（分钟）")
    calories: float = Field(..., description="预计消耗热量（kcal）")
    is_indoor: bool = Field(True, description="是否室内运动")
    description: str = Field("", description="运动描述")
    mets_value: Optional[float] = Field(None, description="METs值")

    class Config:
        json_schema_extra = {
            "example": {
                "exercise_name": "室内跳绳",
                "exercise_type": "jumping_rope",
                "duration": 20,
                "calories": 256.7,
                "is_indoor": True,
                "description": "高效室内有氧运动，燃脂效果好",
                "mets_value": 11.0
            }
        }


class PlanBData(BaseModel):
    """Plan B 响应数据"""
    plan_id: int = Field(..., description="原运动计划ID")
    weather: WeatherAssessment = Field(..., description="天气评估")
    need_plan_b: bool = Field(..., description="是否需要Plan B")
    original_calories: float = Field(0.0, description="原计划总热量（kcal）")
    alternatives: List[PlanBAlternative] = Field(default_factory=list, description="室内替代方案列表")
    plan_b_total_calories: float = Field(0.0, description="Plan B总热量（kcal）")
    reason: str = Field("", description="生成Plan B的原因")

    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": 1,
                "weather": {
                    "is_bad_weather": True,
                    "severity": "moderate",
                    "description": "中雨",
                    "recommendation": "天气不佳，建议改为室内运动"
                },
                "need_plan_b": True,
                "original_calories": 280.0,
                "alternatives": [],
                "plan_b_total_calories": 275.0,
                "reason": "当前天气不适合户外运动"
            }
        }


class PlanBResponse(BaseModel):
    """Plan B 响应"""
    code: int = Field(..., description="状态码，200表示成功")
    message: str = Field(..., description="消息")
    data: Optional[PlanBData] = Field(None, description="Plan B数据")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "已生成室内替代方案",
                "data": {
                    "plan_id": 1,
                    "weather": {
                        "is_bad_weather": True,
                        "severity": "moderate",
                        "description": "中雨",
                        "recommendation": "天气不佳，建议改为室内运动"
                    },
                    "need_plan_b": True,
                    "original_calories": 280.0,
                    "alternatives": [],
                    "plan_b_total_calories": 275.0,
                    "reason": "当前天气不适合户外运动"
                }
            }
        }

