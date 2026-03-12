"""
Exercise API application services.
"""
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud import (
    exercise_record_crud,
    trip_item_crud,
    trip_plan_crud,
    user_crud,
)
from app.db_models.exercise_record import ExerciseRecord
from app.models.exercise import (
    CreateExerciseRecordRequest,
    CreateExerciseRecordResponse,
    ExerciseRecordData,
    ExerciseRecordListResponse,
    ExerciseRecordDetailResponse,
)

VALID_EXERCISE_TYPES = {
    "walking",
    "running",
    "cycling",
    "jogging",
    "hiking",
    "swimming",
    "gym",
    "indoor",
    "outdoor",
}


def _record_to_data(record: ExerciseRecord) -> ExerciseRecordData:
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
        exercise_date=record.exercise_date.isoformat()
        if record.exercise_date
        else "",
        started_at=record.started_at.isoformat() if record.started_at else None,
        ended_at=record.ended_at.isoformat() if record.ended_at else None,
        notes=record.notes,
        created_at=record.created_at.isoformat() if record.created_at else "",
        calories_achievement=calories_achievement,
        duration_achievement=duration_achievement,
    )


def create_exercise_record(
    db: Session, request: CreateExerciseRecordRequest
) -> CreateExerciseRecordResponse:
    try:
        user = user_crud.get_user_by_id(db, request.user_id)
        if not user:
            raise HTTPException(
                status_code=404, detail=f"用户不存在，user_id: {request.user_id}"
            )

        if request.exercise_type not in VALID_EXERCISE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"不支持的运动类型: {request.exercise_type}，"
                    f"支持的类型: {', '.join(sorted(VALID_EXERCISE_TYPES))}"
                ),
            )

        try:
            exercise_date = datetime.strptime(request.exercise_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400, detail="运动日期格式错误，请使用 YYYY-MM-DD 格式"
            )

        planned_calories = request.planned_calories
        planned_duration = request.planned_duration
        if request.plan_id is not None:
            plan = trip_plan_crud.get_trip_plan_by_id(db, request.plan_id)
            if not plan:
                raise HTTPException(
                    status_code=404, detail=f"运动计划不存在，plan_id: {request.plan_id}"
                )
            if plan.user_id != request.user_id:
                raise HTTPException(
                    status_code=403, detail="无权关联此运动计划，只能关联自己的计划"
                )
            if planned_calories is None or planned_duration is None:
                plan_items = trip_item_crud.get_trip_items_by_trip_id(
                    db, request.plan_id
                )
                if planned_calories is None:
                    planned_calories = sum((item.cost or 0) for item in plan_items)
                if planned_duration is None:
                    planned_duration = sum((item.duration or 0) for item in plan_items)

        started_at = None
        if request.started_at:
            try:
                started_at = datetime.fromisoformat(request.started_at)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="开始时间格式错误，请使用 ISO 格式（如 2026-02-06T18:00:00）",
                )

        ended_at = None
        if request.ended_at:
            try:
                ended_at = datetime.fromisoformat(request.ended_at)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="结束时间格式错误，请使用 ISO 格式（如 2026-02-06T18:35:00）",
                )

        if started_at and ended_at and ended_at <= started_at:
            raise HTTPException(status_code=400, detail="结束时间必须晚于开始时间")

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

        record = exercise_record_crud.create_exercise_record(db, record)

        return CreateExerciseRecordResponse(
            code=200,
            message="运动记录添加成功",
            data=_record_to_data(record),
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"新增运动记录失败: {str(e)}")


def get_exercise_records(
    db: Session,
    user_id: int,
    exercise_date: str | None = None,
    exercise_type: str | None = None,
    plan_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ExerciseRecordListResponse:
    try:
        target_date = None
        if exercise_date:
            try:
                target_date = datetime.strptime(exercise_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD 格式"
                )

        if exercise_type and exercise_type not in VALID_EXERCISE_TYPES:
            raise HTTPException(
                status_code=400, detail=f"不支持的运动类型: {exercise_type}"
            )

        total, records = exercise_record_crud.get_exercise_records(
            db,
            user_id,
            exercise_date=target_date,
            exercise_type=exercise_type,
            plan_id=plan_id,
            limit=limit,
            offset=offset,
        )

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
        raise HTTPException(status_code=500, detail=f"查询运动记录失败: {str(e)}")


def get_exercise_record_detail(
    db: Session, record_id: int, user_id: int
) -> ExerciseRecordDetailResponse:
    try:
        record = exercise_record_crud.get_exercise_record_by_id(db, record_id)
        if not record:
            raise HTTPException(
                status_code=404, detail=f"运动记录不存在，record_id: {record_id}"
            )

        if record.user_id != user_id:
            raise HTTPException(
                status_code=403, detail="无权查看此运动记录，只能查看自己的记录"
            )

        return ExerciseRecordDetailResponse(
            code=200,
            message="获取成功",
            data=_record_to_data(record),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询运动记录详情失败: {str(e)}")


def delete_exercise_record(db: Session, record_id: int, user_id: int) -> dict:
    try:
        record = exercise_record_crud.get_exercise_record_by_id(db, record_id)
        if not record:
            raise HTTPException(
                status_code=404, detail=f"运动记录不存在，record_id: {record_id}"
            )

        if record.user_id != user_id:
            raise HTTPException(
                status_code=403, detail="无权删除此运动记录，只能删除自己的记录"
            )

        exercise_record_crud.delete_exercise_record(db, record)

        return {"code": 200, "message": "删除成功", "data": None}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除运动记录失败: {str(e)}")
