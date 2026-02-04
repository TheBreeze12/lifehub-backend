"""
餐前餐后对比表模型
Phase 10: 餐前餐后对比核心创新功能数据模型
"""
from sqlalchemy import Column, Integer, String, Float, Text, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class MealComparison(Base):
    """
    餐前餐后对比表
    用于存储餐前餐后图片对比的数据，计算净摄入热量
    """
    __tablename__ = "meal_comparison"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="对比记录ID")
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, comment="用户ID")
    
    # 餐前图片信息
    before_image_url = Column(String(500), comment="餐前图片URL/路径")
    before_features = Column(Text, comment="餐前图片特征（JSON格式：识别的菜品、估算份量等）")
    
    # 餐后图片信息
    after_image_url = Column(String(500), comment="餐后图片URL/路径")
    after_features = Column(Text, comment="餐后图片特征（JSON格式：剩余菜品、剩余份量等）")
    
    # 对比计算结果
    consumption_ratio = Column(Float, comment="消耗比例（0-1，1表示全部吃完）")
    original_calories = Column(Float, comment="原始估算热量（kcal）")
    net_calories = Column(Float, comment="净摄入热量（kcal）= 原始热量 × 消耗比例")
    
    # 营养素信息（可选，用于详细分析）
    original_protein = Column(Float, comment="原始蛋白质（g）")
    original_fat = Column(Float, comment="原始脂肪（g）")
    original_carbs = Column(Float, comment="原始碳水化合物（g）")
    net_protein = Column(Float, comment="净摄入蛋白质（g）")
    net_fat = Column(Float, comment="净摄入脂肪（g）")
    net_carbs = Column(Float, comment="净摄入碳水化合物（g）")
    
    # 状态字段
    status = Column(
        String(20),
        default="pending_before",
        comment="状态: pending_before(待餐前上传)/pending_after(待餐后上传)/completed(已完成)"
    )
    
    # AI分析说明
    comparison_analysis = Column(Text, comment="AI对比分析说明")
    
    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )
    
    # 关联关系
    user = relationship("User", backref="meal_comparisons")
    
    def __repr__(self):
        return f"<MealComparison(id={self.id}, user_id={self.user_id}, status={self.status})>"
