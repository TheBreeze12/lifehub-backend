"""
菜单识别结果表模型
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, TIMESTAMP, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class MenuRecognition(Base):
    """菜单识别结果表"""
    __tablename__ = "menu_recognition"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True, comment="用户ID（可选）")
    dishes = Column(JSON, nullable=False, comment="识别出的菜品列表，JSON格式")
    created_at = Column(TIMESTAMP, server_default=func.now(), comment="创建时间")
    
    # 关联关系
    user = relationship("User", backref="menu_recognitions")
    
    def __repr__(self):
        return f"<MenuRecognition(id={self.id}, user_id={self.user_id})>"

