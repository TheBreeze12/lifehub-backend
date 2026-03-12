"""
Exercise record CRUD helpers.
"""
from datetime import date
from typing import List, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db_models.exercise_record import ExerciseRecord


def get_exercise_record_by_id(
    db: Session, record_id: int
) -> Optional[ExerciseRecord]:
    return db.query(ExerciseRecord).filter(ExerciseRecord.id == record_id).first()


def get_exercise_records(
    db: Session,
    user_id: int,
    exercise_date: Optional[date] = None,
    exercise_type: Optional[str] = None,
    plan_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[int, List[ExerciseRecord]]:
    query = db.query(ExerciseRecord).filter(ExerciseRecord.user_id == user_id)

    if exercise_date is not None:
        query = query.filter(ExerciseRecord.exercise_date == exercise_date)
    if exercise_type:
        query = query.filter(ExerciseRecord.exercise_type == exercise_type)
    if plan_id is not None:
        query = query.filter(ExerciseRecord.plan_id == plan_id)

    total = query.count()
    records = (
        query.order_by(
            ExerciseRecord.exercise_date.desc(), ExerciseRecord.created_at.desc()
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return total, records


def create_exercise_record(
    db: Session, record: ExerciseRecord
) -> ExerciseRecord:
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_exercise_record(db: Session, record: ExerciseRecord) -> None:
    db.delete(record)
    db.commit()


def get_exercise_records_by_date(
    db: Session, user_id: int, target_date: date
) -> List[ExerciseRecord]:
    return (
        db.query(ExerciseRecord)
        .filter(
            and_(
                ExerciseRecord.user_id == user_id,
                ExerciseRecord.exercise_date == target_date,
            )
        )
        .all()
    )


def has_exercise_record_on_date(
    db: Session, user_id: int, target_date: date
) -> bool:
    return (
        db.query(ExerciseRecord.id)
        .filter(
            and_(
                ExerciseRecord.user_id == user_id,
                ExerciseRecord.exercise_date == target_date,
            )
        )
        .first()
        is not None
    )


def get_exercise_records_between(
    db: Session, user_id: int, start_date: date, end_date: date
) -> List[ExerciseRecord]:
    return (
        db.query(ExerciseRecord)
        .filter(
            and_(
                ExerciseRecord.user_id == user_id,
                ExerciseRecord.exercise_date >= start_date,
                ExerciseRecord.exercise_date <= end_date,
            )
        )
        .order_by(ExerciseRecord.exercise_date)
        .all()
    )


def delete_exercise_records_by_user(db: Session, user_id: int) -> int:
    return (
        db.query(ExerciseRecord)
        .filter(ExerciseRecord.user_id == user_id)
        .delete(synchronize_session=False)
    )
