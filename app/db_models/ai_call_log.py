"""
AI调用日志表模型
Phase 56: 记录每次AI服务调用的详细信息，用于用户查看AI调用记录和数据上传日志
"""
from sqlalchemy import Column, Integer, Float, String, Text, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class AiCallLog(Base):
    """
    AI调用日志表
    记录每次AI模型调用的类型、输入输出摘要、耗时、状态等信息
    """
    __tablename__ = "ai_call_log"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="日志ID")
    user_id = Column(
        Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=True,
        comment="用户ID（部分调用可能无用户上下文）"
    )

    # 调用信息
    call_type = Column(
        String(50),
        nullable=False,
        comment="调用类型: food_analysis/menu_recognition/trip_generation/exercise_intent/allergen_check/meal_comparison"
    )
    model_name = Column(
        String(100),
        nullable=False,
        comment="模型名称: doubao-seed-1-6-251015/qwen-turbo等"
    )

    # 输入输出摘要
    input_summary = Column(
        String(500),
        nullable=True,
        comment="输入摘要（如菜品名称、查询文本等，截断存储）"
    )
    output_summary = Column(
        String(500),
        nullable=True,
        comment="输出摘要（如营养数据、计划标题等，截断存储）"
    )

    # 调用状态
    success = Column(Boolean, default=True, nullable=False, comment="调用是否成功")
    error_message = Column(
        String(1000),
        nullable=True,
        comment="错误信息（调用失败时记录）"
    )

    # 性能指标
    latency_ms = Column(Integer, nullable=True, comment="调用耗时（毫秒）")
    token_usage = Column(Integer, nullable=True, comment="Token使用量（估算）")

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.now(), comment="记录创建时间")

    # 关联关系
    user = relationship("User", backref="ai_call_logs")

    def __repr__(self):
        return (
            f"<AiCallLog(id={self.id}, call_type={self.call_type}, "
            f"model_name={self.model_name}, success={self.success})>"
        )
