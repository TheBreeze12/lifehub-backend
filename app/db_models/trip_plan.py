"""
行程计划表模型
"""
from sqlalchemy import Column, Integer, String, Date, TIMESTAMP, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class TripPlan(Base):
    """行程计划表"""
    __tablename__ = "trip_plan"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="行程ID")
    user_id = Column(Integer, nullable=False, comment="用户ID")
    title = Column(String(100), nullable=False, comment="运动计划标题（原为行程标题）")
    destination = Column(String(50), comment="运动区域/起点（原为目的地）")
    latitude = Column(Float, comment="用户生成计划时的位置纬度（可选）")
    longitude = Column(Float, comment="用户生成计划时的位置经度（可选）")
    start_date = Column(Date, nullable=False, comment="开始日期")
    end_date = Column(Date, nullable=False, comment="结束日期")
    travelers = Column(JSON, comment="同行人员，JSON格式: [\"本人\", \"父母\"]")
    is_offline = Column(Integer, default=0, comment="是否已下载离线包（0/1）")
    offline_size = Column(Integer, comment="离线包大小（字节）")
    status = Column(
        String(20),
        default="planning",
        comment="状态: planning/ongoing/done"
    )
    created_at = Column(TIMESTAMP, server_default=func.now(), comment="创建时间")
    
    # 关联关系
    items = relationship("TripItem", back_populates="trip", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TripPlan(id={self.id}, title={self.title})>"

