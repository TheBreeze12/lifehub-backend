"""
Trip plan CRUD helpers.
"""
from datetime import date
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db_models.trip_plan import TripPlan


def create_trip_plan(db: Session, trip_plan: TripPlan) -> TripPlan:
    db.add(trip_plan)
    db.flush()
    return trip_plan


def save_trip_plan(db: Session, trip_plan: TripPlan) -> TripPlan:
    db.commit()
    db.refresh(trip_plan)
    return trip_plan


def get_trip_plan_by_id(db: Session, trip_id: int) -> Optional[TripPlan]:
    return db.query(TripPlan).filter(TripPlan.id == trip_id).first()


def get_trip_plans_by_user(db: Session, user_id: int) -> List[TripPlan]:
    return (
        db.query(TripPlan)
        .filter(TripPlan.user_id == user_id)
        .order_by(TripPlan.created_at.desc())
        .all()
    )


def get_trip_plans_by_user_limit(
    db: Session, user_id: int, limit: int
) -> List[TripPlan]:
    return (
        db.query(TripPlan)
        .filter(TripPlan.user_id == user_id)
        .order_by(TripPlan.created_at.desc())
        .limit(limit)
        .all()
    )


def get_trip_plans_covering_date(
    db: Session, user_id: int, target_date: date
) -> List[TripPlan]:
    return (
        db.query(TripPlan)
        .filter(
            and_(
                TripPlan.user_id == user_id,
                TripPlan.start_date <= target_date,
                TripPlan.end_date >= target_date,
            )
        )
        .all()
    )


def get_trip_plan_ids_by_user(db: Session, user_id: int) -> List[int]:
    rows = db.query(TripPlan.id).filter(TripPlan.user_id == user_id).all()
    return [row.id for row in rows]


def delete_trip_plans_by_user(db: Session, user_id: int) -> int:
    return (
        db.query(TripPlan)
        .filter(TripPlan.user_id == user_id)
        .delete(synchronize_session=False)
    )
