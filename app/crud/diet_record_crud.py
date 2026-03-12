"""
Diet record CRUD helpers.
"""
from datetime import date
from typing import Dict, List, Optional, Set

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.db_models.diet_record import DietRecord


def create_diet_record(db: Session, record: DietRecord) -> DietRecord:
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_diet_records_by_user(db: Session, user_id: int) -> List[DietRecord]:
    return (
        db.query(DietRecord)
        .filter(DietRecord.user_id == user_id)
        .order_by(desc(DietRecord.record_date), desc(DietRecord.created_at))
        .all()
    )


def get_diet_records_by_user_and_date(
    db: Session, user_id: int, target_date: date
) -> List[DietRecord]:
    return (
        db.query(DietRecord)
        .filter(
            DietRecord.user_id == user_id,
            DietRecord.record_date == target_date,
        )
        .order_by(DietRecord.created_at)
        .all()
    )


def get_diet_record_by_id(db: Session, record_id: int) -> Optional[DietRecord]:
    return db.query(DietRecord).filter(DietRecord.id == record_id).first()


def save_diet_record(db: Session, record: DietRecord) -> DietRecord:
    db.commit()
    db.refresh(record)
    return record


def delete_diet_record(db: Session, record: DietRecord) -> None:
    db.delete(record)
    db.commit()


def has_diet_record_on_date(db: Session, user_id: int, target_date: date) -> bool:
    return (
        db.query(DietRecord.id)
        .filter(
            and_(
                DietRecord.user_id == user_id,
                DietRecord.record_date == target_date,
            )
        )
        .first()
        is not None
    )


def get_today_intake_calories(db: Session, user_id: int, target_date: date) -> float:
    result = (
        db.query(func.sum(DietRecord.calories))
        .filter(
            and_(
                DietRecord.user_id == user_id,
                DietRecord.record_date == target_date,
            )
        )
        .scalar()
    )
    return float(result) if result else 0.0


def get_history_food_counts(
    db: Session, user_id: int, since_date: date
) -> Dict[str, int]:
    rows = (
        db.query(DietRecord.food_name, func.count(DietRecord.id).label("cnt"))
        .filter(
            and_(
                DietRecord.user_id == user_id,
                DietRecord.record_date >= since_date,
            )
        )
        .group_by(DietRecord.food_name)
        .all()
    )
    return {row.food_name: row.cnt for row in rows}


def get_today_eaten_foods(db: Session, user_id: int, target_date: date) -> Set[str]:
    rows = (
        db.query(DietRecord.food_name)
        .filter(
            and_(
                DietRecord.user_id == user_id,
                DietRecord.record_date == target_date,
            )
        )
        .all()
    )
    return {row.food_name for row in rows}


def delete_diet_records_by_user(db: Session, user_id: int) -> int:
    return (
        db.query(DietRecord)
        .filter(DietRecord.user_id == user_id)
        .delete(synchronize_session=False)
    )
