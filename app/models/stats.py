"""
统计相关数据模型
Phase 15: 热量收支统计
"""
from pydantic import BaseModel, Field
from typing import Optional


class DailyCalorieStats(BaseModel):
    """每日热量统计数据"""
    date: str = Field(..., description="统计日期（YYYY-MM-DD）")
    user_id: int = Field(..., description="用户ID")
    
    # 摄入相关
    intake_calories: float = Field(0.0, description="摄入热量（kcal）")
    meal_count: int = Field(0, description="餐次数量")
    
    # 消耗相关
    burn_calories: float = Field(0.0, description="消耗热量（kcal）")
    exercise_count: int = Field(0, description="运动项目数量")
    exercise_duration: int = Field(0, description="运动总时长（分钟）")
    
    # 净热量
    net_calories: float = Field(0.0, description="净热量（摄入-消耗）")
    
    # 餐次分类统计（可选）
    meal_breakdown: Optional[dict] = Field(None, description="餐次分类统计")
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2026-02-04",
                "user_id": 1,
                "intake_calories": 1800.0,
                "meal_count": 3,
                "burn_calories": 500.0,
                "exercise_count": 2,
                "exercise_duration": 60,
                "net_calories": 1300.0,
                "meal_breakdown": {
                    "breakfast": 400.0,
                    "lunch": 700.0,
                    "dinner": 600.0,
                    "snack": 100.0
                }
            }
        }


class DailyBreakdown(BaseModel):
    """每日统计明细（用于周统计）"""
    date: str = Field(..., description="日期")
    intake_calories: float = Field(0.0, description="摄入热量")
    burn_calories: float = Field(0.0, description="消耗热量")
    net_calories: float = Field(0.0, description="净热量")
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2026-02-04",
                "intake_calories": 1800.0,
                "burn_calories": 500.0,
                "net_calories": 1300.0
            }
        }


class WeeklyCalorieStats(BaseModel):
    """每周热量统计数据"""
    week_start: str = Field(..., description="周起始日期（YYYY-MM-DD，周一）")
    week_end: str = Field(..., description="周结束日期（YYYY-MM-DD，周日）")
    user_id: int = Field(..., description="用户ID")
    
    # 周总计
    total_intake: float = Field(0.0, description="周总摄入热量（kcal）")
    total_burn: float = Field(0.0, description="周总消耗热量（kcal）")
    total_net: float = Field(0.0, description="周净热量")
    
    # 周平均
    avg_intake: float = Field(0.0, description="日均摄入热量（kcal）")
    avg_burn: float = Field(0.0, description="日均消耗热量（kcal）")
    avg_net: float = Field(0.0, description="日均净热量")
    
    # 统计数据
    total_meals: int = Field(0, description="周总餐次")
    total_exercises: int = Field(0, description="周总运动次数")
    active_days: int = Field(0, description="有记录的天数")
    
    # 每日明细
    daily_breakdown: list[DailyBreakdown] = Field(default_factory=list, description="每日明细")
    
    class Config:
        json_schema_extra = {
            "example": {
                "week_start": "2026-02-03",
                "week_end": "2026-02-09",
                "user_id": 1,
                "total_intake": 12600.0,
                "total_burn": 3500.0,
                "total_net": 9100.0,
                "avg_intake": 1800.0,
                "avg_burn": 500.0,
                "avg_net": 1300.0,
                "total_meals": 21,
                "total_exercises": 14,
                "active_days": 7,
                "daily_breakdown": []
            }
        }


class DailyCalorieStatsResponse(BaseModel):
    """每日热量统计响应"""
    code: int = Field(200, description="状态码，200表示成功")
    message: str = Field("获取成功", description="消息")
    data: DailyCalorieStats = Field(..., description="统计数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "date": "2026-02-04",
                    "user_id": 1,
                    "intake_calories": 1800.0,
                    "meal_count": 3,
                    "burn_calories": 500.0,
                    "exercise_count": 2,
                    "exercise_duration": 60,
                    "net_calories": 1300.0
                }
            }
        }


class WeeklyCalorieStatsResponse(BaseModel):
    """每周热量统计响应"""
    code: int = Field(200, description="状态码，200表示成功")
    message: str = Field("获取成功", description="消息")
    data: WeeklyCalorieStats = Field(..., description="统计数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "week_start": "2026-02-03",
                    "week_end": "2026-02-09",
                    "user_id": 1,
                    "total_intake": 12600.0,
                    "total_burn": 3500.0,
                    "total_net": 9100.0,
                    "avg_intake": 1800.0,
                    "avg_burn": 500.0,
                    "avg_net": 1300.0,
                    "total_meals": 21,
                    "total_exercises": 14,
                    "active_days": 7,
                    "daily_breakdown": []
                }
            }
        }
