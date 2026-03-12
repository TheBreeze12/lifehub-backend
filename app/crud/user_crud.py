"""
User-related CRUD helpers.
"""
from typing import Optional
from sqlalchemy.orm import Session

from app.db_models.user import User


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_nickname(db: Session, nickname: str) -> Optional[User]:
    return db.query(User).filter(User.nickname == nickname).first()


def save_user(db: Session, user: User) -> None:
    db.add(user)


def create_user(db: Session, user: User) -> User:
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
