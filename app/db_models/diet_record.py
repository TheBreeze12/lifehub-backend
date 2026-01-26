"""
饮食记录表模型
"""
from sqlalchemy import Column, Integer, String, Float, Date, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class DietRecord(Base):
    """饮食记录表"""
    __tablename__ = "diet_record"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, comment="用户ID")
    food_name = Column(String(100), nullable=False, comment="菜品名称")
    calories = Column(Float, nullable=False, comment="热量（kcal）")
    protein = Column(Float, comment="蛋白质（g）")
    fat = Column(Float, comment="脂肪（g）")
    carbs = Column(Float, comment="碳水化合物（g）")
    meal_type = Column(
        String(20),
        comment="餐次: breakfast/lunch/dinner/snack"
    )
    # is_actual = Column(
    #     Integer,
    #     default=0,
    #     comment="是否为实际摄入（餐后对比修正后为1）"
    # )
    # image_path = Column(String(255), comment="本地图片路径")
    record_date = Column(Date, nullable=False, comment="记录日期（YYYY-MM-DD）")
    created_at = Column(TIMESTAMP, server_default=func.now(), comment="创建时间")
    
    # 关联关系
    user = relationship("User", backref="diet_records")
    
    def __repr__(self):
        return f"<DietRecord(id={self.id}, user_id={self.user_id}, food_name={self.food_name})>"

