"""
运动记录表模型
Phase 25: 运动记录数据模型，用于存储用户的实际运动执行记录
"""
from sqlalchemy import Column, Integer, Float, String, Text, TIMESTAMP, ForeignKey, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class ExerciseRecord(Base):
    """
    运动记录表
    记录用户实际执行运动的数据，用于与计划进行对比分析
    """
    __tablename__ = "exercise_record"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="运动记录ID")
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, comment="用户ID")
    plan_id = Column(
        Integer,
        ForeignKey("trip_plan.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联的运动计划ID（可选，允许无计划的自由运动记录）"
    )

    # 运动执行数据
    exercise_type = Column(
        String(30),
        default="walking",
        comment="运动类型: walking/running/cycling/jogging/hiking/swimming/gym/indoor/outdoor"
    )
    actual_calories = Column(Float, nullable=False, comment="实际消耗热量（kcal）")
    actual_duration = Column(Integer, nullable=False, comment="实际运动时长（分钟）")
    distance = Column(Float, nullable=True, comment="运动距离（米）")

    # 路线数据（JSON格式存储轨迹点等）
    route_data = Column(Text, nullable=True, comment="路线数据（JSON格式：轨迹点列表等）")

    # 计划对比数据
    planned_calories = Column(Float, nullable=True, comment="计划消耗热量（kcal）")
    planned_duration = Column(Integer, nullable=True, comment="计划运动时长（分钟）")

    # 运动日期
    exercise_date = Column(Date, nullable=False, comment="运动日期（YYYY-MM-DD）")

    # 时间记录
    started_at = Column(TIMESTAMP, nullable=True, comment="运动开始时间")
    ended_at = Column(TIMESTAMP, nullable=True, comment="运动结束时间")

    # 备注
    notes = Column(Text, nullable=True, comment="运动备注")

    # 创建时间
    created_at = Column(TIMESTAMP, server_default=func.now(), comment="记录创建时间")

    # 关联关系
    user = relationship("User", backref="exercise_records")
    plan = relationship("TripPlan", backref="exercise_records")

    def __repr__(self):
        return (
            f"<ExerciseRecord(id={self.id}, user_id={self.user_id}, "
            f"exercise_type={self.exercise_type}, actual_calories={self.actual_calories})>"
        )
