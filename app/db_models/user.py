"""
用户表模型
"""
from sqlalchemy import Column, Integer, String, JSON, TIMESTAMP, Text
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """用户表"""
    __tablename__ = "user"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    nickname = Column(String(50), default="健康达人", comment="用户昵称")
    health_goal = Column(
        String(20),
        default="balanced",
        comment="健康目标: reduce_fat/gain_muscle/control_sugar/balanced"
    )
    allergens = Column(JSON, comment="过敏原列表，JSON格式: [\"海鲜\", \"花生\"]")
    travel_preference = Column(String(20), comment="出行偏好: self_driving/public_transport/walking")
    daily_budget = Column(Integer, comment="出行日预算（元）")
    created_at = Column(TIMESTAMP, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, nickname={self.nickname})>"

