"""
Meal comparison CRUD helpers.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.db_models.meal_comparison import MealComparison


def create_meal_comparison(
    db: Session, comparison: MealComparison
) -> MealComparison:
    db.add(comparison)
    db.commit()
    db.refresh(comparison)
    return comparison


def get_meal_comparison_by_id(
    db: Session, comparison_id: int
) -> Optional[MealComparison]:
    return db.query(MealComparison).filter(MealComparison.id == comparison_id).first()


def save_comparison(db: Session, comparison: MealComparison) -> MealComparison:
    db.commit()
    db.refresh(comparison)
    return comparison


def delete_meal_comparisons_by_user(db: Session, user_id: int) -> int:
    return (
        db.query(MealComparison)
        .filter(MealComparison.user_id == user_id)
        .delete(synchronize_session=False)
    )
