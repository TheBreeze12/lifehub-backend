"""
运动记录API路由
Phase 25: 运动记录数据模型与接口

提供运动记录的增删查功能：
- POST /api/exercise/record - 新增运动记录
- GET /api/exercise/records - 查询运动记录列表
- GET /api/exercise/record/{record_id} - 查询单条运动记录详情
- DELETE /api/exercise/record/{record_id} - 删除运动记录
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import exercise_service
from app.models.exercise import (
    CreateExerciseRecordRequest,
    CreateExerciseRecordResponse,
    ExerciseRecordData,
    ExerciseRecordListResponse,
    ExerciseRecordDetailResponse,
)

router = APIRouter(prefix="/api/exercise", tags=["运动记录"])


@router.post("/record", response_model=CreateExerciseRecordResponse)
async def create_exercise_record(
    request: CreateExerciseRecordRequest,
    db: Session = Depends(get_db),
):
    """
    新增运动记录

    - **user_id**: 用户ID（必须）
    - **plan_id**: 关联的运动计划ID（可选）
    - **exercise_type**: 运动类型
    - **actual_calories**: 实际消耗热量（kcal）
    - **actual_duration**: 实际运动时长（分钟）
    - **distance**: 运动距离（米，可选）
    - **exercise_date**: 运动日期（YYYY-MM-DD）
    - **started_at**: 运动开始时间（ISO格式，可选）
    - **ended_at**: 运动结束时间（ISO格式，可选）
    - **notes**: 运动备注（可选）
    """
    return exercise_service.create_exercise_record(db, request)


@router.get("/records", response_model=ExerciseRecordListResponse)
async def get_exercise_records(
    userId: int = Query(..., description="用户ID", gt=0),
    exercise_date: str | None = Query(None, description="按日期筛选（YYYY-MM-DD格式）"),
    exercise_type: str | None = Query(None, description="按运动类型筛选"),
    plan_id: int | None = Query(None, description="按运动计划ID筛选"),
    limit: int = Query(50, description="返回数量限制", ge=1, le=200),
    offset: int = Query(0, description="偏移量", ge=0),
    db: Session = Depends(get_db),
):
    """
    查询运动记录列表

    - **userId**: 用户ID（必须）
    - **exercise_date**: 按日期筛选（可选，YYYY-MM-DD格式）
    - **exercise_type**: 按运动类型筛选（可选）
    - **plan_id**: 按运动计划ID筛选（可选）
    - **limit**: 返回数量限制（默认50，最大200）
    - **offset**: 偏移量（默认0）
    """
    return exercise_service.get_exercise_records(
        db,
        userId,
        exercise_date=exercise_date,
        exercise_type=exercise_type,
        plan_id=plan_id,
        limit=limit,
        offset=offset,
    )


@router.get("/record/{record_id}", response_model=ExerciseRecordDetailResponse)
async def get_exercise_record_detail(
    record_id: int,
    userId: int = Query(..., description="用户ID（用于权限校验）", gt=0),
    db: Session = Depends(get_db),
):
    """
    查询单条运动记录详情

    - **record_id**: 运动记录ID
    - **userId**: 用户ID（用于权限校验）
    """
    return exercise_service.get_exercise_record_detail(db, record_id, userId)


@router.delete("/record/{record_id}")
async def delete_exercise_record(
    record_id: int,
    userId: int = Query(..., description="用户ID（用于权限校验）", gt=0),
    db: Session = Depends(get_db),
):
    """
    删除运动记录

    - **record_id**: 运动记录ID
    - **userId**: 用户ID（用于权限校验）
    """
    return exercise_service.delete_exercise_record(db, record_id, userId)


@router.get("/health")
async def exercise_health_check():
    """运动记录服务健康检查"""
    return {
        "status": "ok",
        "service": "exercise-record"
    }
