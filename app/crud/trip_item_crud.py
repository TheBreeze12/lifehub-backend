"""
Trip item CRUD helpers.
"""
from typing import List

from sqlalchemy.orm import Session

from app.db_models.trip_item import TripItem


def create_trip_item(db: Session, trip_item: TripItem) -> TripItem:
    db.add(trip_item)
    return trip_item


def get_trip_items_by_trip_id(db: Session, trip_id: int) -> List[TripItem]:
    return (
        db.query(TripItem)
        .filter(TripItem.trip_id == trip_id)
        .order_by(TripItem.sort_order, TripItem.day_index, TripItem.start_time)
        .all()
    )


def get_trip_items_by_trip_id_simple(db: Session, trip_id: int) -> List[TripItem]:
    return (
        db.query(TripItem)
        .filter(TripItem.trip_id == trip_id)
        .order_by(TripItem.sort_order)
        .all()
    )


def count_trip_items_by_trip_id(db: Session, trip_id: int) -> int:
    return db.query(TripItem).filter(TripItem.trip_id == trip_id).count()


def delete_trip_items_by_trip_ids(db: Session, trip_ids: List[int]) -> int:
    if not trip_ids:
        return 0
    return (
        db.query(TripItem)
        .filter(TripItem.trip_id.in_(trip_ids))
        .delete(synchronize_session=False)
    )
