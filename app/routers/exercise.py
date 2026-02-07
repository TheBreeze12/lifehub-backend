"""
运动记录API路由
Phase 25: 运动记录数据模型与接口

提供运动记录的增删查功能：
- POST /api/exercise/record - 新增运动记录
- GET /api/exercise/records - 查询运动记录列表
- GET /api/exercise/record/{record_id} - 查询单条运动记录详情
- DELETE /api/exercise/record/{record_id} - 删除运动记录
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, date

from app.database import get_db
from app.db_models.exercise_record import ExerciseRecord
from app.db_models.user import User
from app.db_models.trip_plan import TripPlan
from app.db_models.trip_item import TripItem
from app.models.exercise import (
    CreateExerciseRecordRequest,
    CreateExerciseRecordResponse,
    ExerciseRecordData,
    ExerciseRecordListResponse,
    ExerciseRecordDetailResponse,
)

router = APIRouter(prefix="/api/exercise", tags=["运动记录"])

# 支持的运动类型
VALID_EXERCISE_TYPES = {
    "walking", "running", "cycling", "jogging", "hiking",
    "swimming", "gym", "indoor", "outdoor"
}


def _record_to_data(record: ExerciseRecord) -> ExerciseRecordData:
    """
    将ExerciseRecord ORM对象转换为Pydantic响应模型
    同时计算热量达成率和时长达成率
    """
    # 计算达成率
    calories_achievement = None
    if record.planned_calories and record.planned_calories > 0:
        calories_achievement = round(
            (record.actual_calories / record.planned_calories) * 100, 1
        )

    duration_achievement = None
    if record.planned_duration and record.planned_duration > 0:
        duration_achievement = round(
            (record.actual_duration / record.planned_duration) * 100, 1
        )

    return ExerciseRecordData(
        id=record.id,
        user_id=record.user_id,
        plan_id=record.plan_id,
        exercise_type=record.exercise_type or "walking",
        actual_calories=record.actual_calories,
        actual_duration=record.actual_duration,
        distance=record.distance,
        route_data=record.route_data,
        planned_calories=record.planned_calories,
        planned_duration=record.planned_duration,
        exercise_date=record.exercise_date.isoformat() if record.exercise_date else "",
        started_at=record.started_at.isoformat() if record.started_at else None,
        ended_at=record.ended_at.isoformat() if record.ended_at else None,
        notes=record.notes,
        created_at=record.created_at.isoformat() if record.created_at else "",
        calories_achievement=calories_achievement,
        duration_achievement=duration_achievement,
    )


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
    try:
        # 1. 验证用户存在
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"用户不存在，user_id: {request.user_id}"
            )

        # 2. 验证运动类型
        if request.exercise_type not in VALID_EXERCISE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的运动类型: {request.exercise_type}，"
                       f"支持的类型: {', '.join(sorted(VALID_EXERCISE_TYPES))}"
            )

        # 3. 解析运动日期
        try:
            exercise_date = datetime.strptime(request.exercise_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="运动日期格式错误，请使用 YYYY-MM-DD 格式"
            )

        # 4. 验证关联的运动计划（如果提供）
        planned_calories = request.planned_calories
        planned_duration = request.planned_duration
        if request.plan_id is not None:
            plan = db.query(TripPlan).filter(TripPlan.id == request.plan_id).first()
            if not plan:
                raise HTTPException(
                    status_code=404,
                    detail=f"运动计划不存在，plan_id: {request.plan_id}"
                )
            # 验证计划归属
            if plan.user_id != request.user_id:
                raise HTTPException(
                    status_code=403,
                    detail="无权关联此运动计划，只能关联自己的计划"
                )
            # 如果未提供计划数据，自动从计划中读取
            if planned_calories is None or planned_duration is None:
                plan_items = db.query(TripItem).filter(
                    TripItem.trip_id == request.plan_id
                ).all()
                if planned_calories is None:
                    planned_calories = sum(
                        (item.cost or 0) for item in plan_items
                    )
                if planned_duration is None:
                    planned_duration = sum(
                        (item.duration or 0) for item in plan_items
                    )

        # 5. 解析可选的时间戳
        started_at = None
        if request.started_at:
            try:
                started_at = datetime.fromisoformat(request.started_at)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="开始时间格式错误，请使用 ISO 格式（如 2026-02-06T18:00:00）"
                )

        ended_at = None
        if request.ended_at:
            try:
                ended_at = datetime.fromisoformat(request.ended_at)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="结束时间格式错误，请使用 ISO 格式（如 2026-02-06T18:35:00）"
                )

        # 6. 验证开始/结束时间逻辑
        if started_at and ended_at and ended_at <= started_at:
            raise HTTPException(
                status_code=400,
                detail="结束时间必须晚于开始时间"
            )

        # 7. 创建运动记录
        record = ExerciseRecord(
            user_id=request.user_id,
            plan_id=request.plan_id,
            exercise_type=request.exercise_type,
            actual_calories=request.actual_calories,
            actual_duration=request.actual_duration,
            distance=request.distance,
            route_data=request.route_data,
            planned_calories=planned_calories,
            planned_duration=planned_duration,
            exercise_date=exercise_date,
            started_at=started_at,
            ended_at=ended_at,
            notes=request.notes,
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        return CreateExerciseRecordResponse(
            code=200,
            message="运动记录添加成功",
            data=_record_to_data(record),
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"新增运动记录失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"新增运动记录失败: {str(e)}"
        )


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
    try:
        # 构建基础查询
        query = db.query(ExerciseRecord).filter(
            ExerciseRecord.user_id == userId
        )

        # 按日期筛选
        if exercise_date:
            try:
                target_date = datetime.strptime(exercise_date, "%Y-%m-%d").date()
                query = query.filter(ExerciseRecord.exercise_date == target_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="日期格式错误，请使用 YYYY-MM-DD 格式"
                )

        # 按运动类型筛选
        if exercise_type:
            if exercise_type not in VALID_EXERCISE_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的运动类型: {exercise_type}"
                )
            query = query.filter(ExerciseRecord.exercise_type == exercise_type)

        # 按计划ID筛选
        if plan_id is not None:
            query = query.filter(ExerciseRecord.plan_id == plan_id)

        # 获取总数
        total = query.count()

        # 按运动日期倒序排列，分页
        records = query.order_by(
            ExerciseRecord.exercise_date.desc(),
            ExerciseRecord.created_at.desc()
        ).offset(offset).limit(limit).all()

        # 转换为响应格式
        records_data = [_record_to_data(r) for r in records]

        return ExerciseRecordListResponse(
            code=200,
            message="获取成功",
            data=records_data,
            total=total,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"查询运动记录失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"查询运动记录失败: {str(e)}"
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
    try:
        record = db.query(ExerciseRecord).filter(
            ExerciseRecord.id == record_id
        ).first()

        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"运动记录不存在，record_id: {record_id}"
            )

        # 权限校验
        if record.user_id != userId:
            raise HTTPException(
                status_code=403,
                detail="无权查看此运动记录，只能查看自己的记录"
            )

        return ExerciseRecordDetailResponse(
            code=200,
            message="获取成功",
            data=_record_to_data(record),
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"查询运动记录详情失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"查询运动记录详情失败: {str(e)}"
        )


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
    try:
        record = db.query(ExerciseRecord).filter(
            ExerciseRecord.id == record_id
        ).first()

        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"运动记录不存在，record_id: {record_id}"
            )

        # 权限校验
        if record.user_id != userId:
            raise HTTPException(
                status_code=403,
                detail="无权删除此运动记录，只能删除自己的记录"
            )

        db.delete(record)
        db.commit()

        return {
            "code": 200,
            "message": "删除成功",
            "data": None,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"删除运动记录失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"删除运动记录失败: {str(e)}"
        )


@router.get("/health")
async def exercise_health_check():
    """运动记录服务健康检查"""
    return {
        "status": "ok",
        "service": "exercise-record"
    }
