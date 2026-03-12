"""
Menu recognition CRUD helpers.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.db_models.menu_recognition import MenuRecognition


def create_menu_recognition(
    db: Session, user_id: int, dishes: list
) -> MenuRecognition:
    recognition = MenuRecognition(user_id=user_id, dishes=dishes)
    db.add(recognition)
    db.commit()
    db.refresh(recognition)
    return recognition


def get_latest_menu_recognition(
    db: Session, user_id: Optional[int] = None
) -> Optional[MenuRecognition]:
    query = db.query(MenuRecognition)
    if user_id:
        query = query.filter(MenuRecognition.user_id == user_id)
    return query.order_by(MenuRecognition.created_at.desc()).first()


def delete_menu_recognitions_by_user(db: Session, user_id: int) -> int:
    return (
        db.query(MenuRecognition)
        .filter(MenuRecognition.user_id == user_id)
        .delete(synchronize_session=False)
    )
