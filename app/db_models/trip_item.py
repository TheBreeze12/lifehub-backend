"""
行程节点表模型
"""
from sqlalchemy import Column, Integer, String, Float, Time, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class TripItem(Base):
    """行程节点表"""
    __tablename__ = "trip_item"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="节点ID")
    trip_id = Column(
        Integer,
        ForeignKey("trip_plan.id", ondelete="CASCADE"),
        nullable=False,
        comment="行程ID"
    )
    day_index = Column(Integer, nullable=False, comment="第几天（从1开始）")
    start_time = Column(Time, comment="开始时间（HH:mm）")
    place_name = Column(String(100), nullable=False, comment="地点名称")
    place_type = Column(
        String(20),
        comment="类型: walking/running/cycling/park/gym/indoor/outdoor (运动类型) 或 attraction/dining/transport/accommodation (兼容旧数据)"
    )
    duration = Column(Integer, comment="预计时长（分钟）")
    cost = Column(Float, comment="预计消耗卡路里（kcal），原为费用字段，现语义转换为卡路里")
    latitude = Column(Float, comment="纬度")
    longitude = Column(Float, comment="经度")
    notes = Column(Text, comment="备注")
    sort_order = Column(Integer, default=0, comment="排序序号")
    
    # 关联关系
    trip = relationship("TripPlan", back_populates="items")
    
    def __repr__(self):
        return f"<TripItem(id={self.id}, trip_id={self.trip_id}, place_name={self.place_name})>"

