"""
运动记录相关Pydantic模型
Phase 25: 运动记录请求/响应模型
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CreateExerciseRecordRequest(BaseModel):
    """新增运动记录请求"""
    user_id: int = Field(..., description="用户ID", gt=0)
    plan_id: Optional[int] = Field(None, description="关联的运动计划ID（可选）")
    exercise_type: str = Field(
        "walking",
        description="运动类型: walking/running/cycling/jogging/hiking/swimming/gym/indoor/outdoor"
    )
    actual_calories: float = Field(..., description="实际消耗热量（kcal）", ge=0)
    actual_duration: int = Field(..., description="实际运动时长（分钟）", ge=1)
    distance: Optional[float] = Field(None, description="运动距离（米）", ge=0)
    route_data: Optional[str] = Field(None, description="路线数据（JSON格式）")
    planned_calories: Optional[float] = Field(None, description="计划消耗热量（kcal）", ge=0)
    planned_duration: Optional[int] = Field(None, description="计划运动时长（分钟）", ge=0)
    exercise_date: str = Field(..., description="运动日期（YYYY-MM-DD格式）")
    started_at: Optional[str] = Field(None, description="运动开始时间（ISO格式）")
    ended_at: Optional[str] = Field(None, description="运动结束时间（ISO格式）")
    notes: Optional[str] = Field(None, description="运动备注", max_length=500)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "plan_id": 1,
                "exercise_type": "running",
                "actual_calories": 280.0,
                "actual_duration": 35,
                "distance": 4500.0,
                "exercise_date": "2026-02-06",
                "started_at": "2026-02-06T18:00:00",
                "ended_at": "2026-02-06T18:35:00",
                "notes": "沿河跑步，感觉不错"
            }
        }


class ExerciseRecordData(BaseModel):
    """运动记录数据"""
    id: int = Field(..., description="运动记录ID")
    user_id: int = Field(..., description="用户ID")
    plan_id: Optional[int] = Field(None, description="关联的运动计划ID")
    exercise_type: str = Field(..., description="运动类型")
    actual_calories: float = Field(..., description="实际消耗热量（kcal）")
    actual_duration: int = Field(..., description="实际运动时长（分钟）")
    distance: Optional[float] = Field(None, description="运动距离（米）")
    route_data: Optional[str] = Field(None, description="路线数据（JSON格式）")
    planned_calories: Optional[float] = Field(None, description="计划消耗热量（kcal）")
    planned_duration: Optional[int] = Field(None, description="计划运动时长（分钟）")
    exercise_date: str = Field(..., description="运动日期（YYYY-MM-DD）")
    started_at: Optional[str] = Field(None, description="运动开始时间")
    ended_at: Optional[str] = Field(None, description="运动结束时间")
    notes: Optional[str] = Field(None, description="运动备注")
    created_at: str = Field(..., description="记录创建时间")
    # 计算字段
    calories_achievement: Optional[float] = Field(
        None, description="热量达成率（%），实际消耗/计划消耗×100"
    )
    duration_achievement: Optional[float] = Field(
        None, description="时长达成率（%），实际时长/计划时长×100"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "plan_id": 1,
                "exercise_type": "running",
                "actual_calories": 280.0,
                "actual_duration": 35,
                "distance": 4500.0,
                "planned_calories": 300.0,
                "planned_duration": 30,
                "exercise_date": "2026-02-06",
                "started_at": "2026-02-06T18:00:00",
                "ended_at": "2026-02-06T18:35:00",
                "notes": "沿河跑步",
                "created_at": "2026-02-06T18:40:00",
                "calories_achievement": 93.3,
                "duration_achievement": 116.7
            }
        }


class CreateExerciseRecordResponse(BaseModel):
    """新增运动记录响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("记录成功", description="消息")
    data: Optional[ExerciseRecordData] = Field(None, description="运动记录数据")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "运动记录添加成功",
                "data": {
                    "id": 1,
                    "user_id": 1,
                    "exercise_type": "running",
                    "actual_calories": 280.0,
                    "actual_duration": 35,
                    "exercise_date": "2026-02-06",
                    "created_at": "2026-02-06T18:40:00"
                }
            }
        }


class ExerciseRecordListResponse(BaseModel):
    """运动记录列表响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("获取成功", description="消息")
    data: list[ExerciseRecordData] = Field(default=[], description="运动记录列表")
    total: int = Field(0, description="记录总数")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "获取成功",
                "data": [
                    {
                        "id": 1,
                        "user_id": 1,
                        "exercise_type": "running",
                        "actual_calories": 280.0,
                        "actual_duration": 35,
                        "exercise_date": "2026-02-06",
                        "created_at": "2026-02-06T18:40:00"
                    }
                ],
                "total": 1
            }
        }


class ExerciseRecordDetailResponse(BaseModel):
    """运动记录详情响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("获取成功", description="消息")
    data: Optional[ExerciseRecordData] = Field(None, description="运动记录数据")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "id": 1,
                    "user_id": 1,
                    "exercise_type": "running",
                    "actual_calories": 280.0,
                    "actual_duration": 35,
                    "exercise_date": "2026-02-06",
                    "created_at": "2026-02-06T18:40:00"
                }
            }
        }
