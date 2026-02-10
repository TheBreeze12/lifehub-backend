"""
数据库模型（SQLAlchemy ORM）
"""
from app.db_models.user import User
from app.db_models.diet_record import DietRecord
from app.db_models.trip_plan import TripPlan
from app.db_models.trip_item import TripItem
from app.db_models.menu_recognition import MenuRecognition
from app.db_models.meal_comparison import MealComparison
from app.db_models.ai_call_log import AiCallLog

__all__ = ["User", "DietRecord", "TripPlan", "TripItem", "MenuRecognition", "MealComparison", "AiCallLog"]

