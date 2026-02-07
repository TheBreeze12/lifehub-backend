"""
用户数据服务层
Phase 55: 一键"遗忘"功能 - 用户数据完全删除服务
"""

import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.db_models.user import User
from app.db_models.diet_record import DietRecord
from app.db_models.exercise_record import ExerciseRecord
from app.db_models.meal_comparison import MealComparison
from app.db_models.menu_recognition import MenuRecognition
from app.db_models.trip_plan import TripPlan
from app.db_models.trip_item import TripItem

logger = logging.getLogger(__name__)


def delete_user_data(db: Session, user_id: int) -> Dict[str, Any]:
    """
    完全删除用户的所有数据（一键"遗忘"功能）

    级联删除顺序（考虑外键约束）：
    1. exercise_record（引用 trip_plan.id，需先于 trip_plan 删除）
    2. trip_item（通过 trip_plan cascade 自动删除，但显式删除更安全）
    3. trip_plan
    4. diet_record
    5. meal_comparison
    6. menu_recognition
    7. user（最后删除用户本身）

    Args:
        db: 数据库会话
        user_id: 要删除的用户ID

    Returns:
        包含删除统计信息的字典

    Raises:
        ValueError: 用户不存在时抛出
    """
    # 查询用户是否存在
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"用户不存在，userId: {user_id}")

    nickname = user.nickname
    deleted_counts = {}

    try:
        # 1. 删除运动记录（引用了trip_plan，需先删除）
        exercise_count = db.query(ExerciseRecord).filter(
            ExerciseRecord.user_id == user_id
        ).delete(synchronize_session=False)
        deleted_counts["exercise_records"] = exercise_count

        # 2. 获取用户的所有运动计划ID，用于删除关联的trip_item
        plan_ids = [
            p.id for p in db.query(TripPlan.id).filter(TripPlan.user_id == user_id).all()
        ]

        # 3. 删除运动项目（trip_item）
        trip_item_count = 0
        if plan_ids:
            trip_item_count = db.query(TripItem).filter(
                TripItem.trip_id.in_(plan_ids)
            ).delete(synchronize_session=False)

        # 4. 删除运动计划
        trip_plan_count = db.query(TripPlan).filter(
            TripPlan.user_id == user_id
        ).delete(synchronize_session=False)
        deleted_counts["trip_plans"] = trip_plan_count

        # 5. 删除饮食记录
        diet_count = db.query(DietRecord).filter(
            DietRecord.user_id == user_id
        ).delete(synchronize_session=False)
        deleted_counts["diet_records"] = diet_count

        # 6. 删除餐前餐后对比记录
        meal_comparison_count = db.query(MealComparison).filter(
            MealComparison.user_id == user_id
        ).delete(synchronize_session=False)
        deleted_counts["meal_comparisons"] = meal_comparison_count

        # 7. 删除菜单识别记录
        menu_recognition_count = db.query(MenuRecognition).filter(
            MenuRecognition.user_id == user_id
        ).delete(synchronize_session=False)
        deleted_counts["menu_recognitions"] = menu_recognition_count

        # 8. 删除用户本身
        db.delete(user)

        # 提交事务
        db.commit()

        total_deleted = sum(deleted_counts.values())

        logger.info(
            f"用户数据删除完成: user_id={user_id}, nickname={nickname}, "
            f"总计删除 {total_deleted} 条记录"
        )

        return {
            "user_id": user_id,
            "nickname": nickname,
            "deleted_counts": deleted_counts,
            "total_deleted": total_deleted,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"删除用户数据失败: user_id={user_id}, error={str(e)}")
        raise
