"""
AI调用日志服务
Phase 56: 记录和查询AI调用日志，供用户查看AI调用记录和数据上传日志
"""
import logging
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db_models.ai_call_log import AiCallLog

logger = logging.getLogger(__name__)

# AI调用类型常量
AI_CALL_TYPES = [
    "food_analysis",
    "menu_recognition",
    "trip_generation",
    "exercise_intent",
    "allergen_check",
    "meal_comparison",
]

# AI调用类型中文标签
AI_CALL_TYPE_LABELS = {
    "food_analysis": "菜品营养分析",
    "menu_recognition": "菜单图片识别",
    "trip_generation": "运动计划生成",
    "exercise_intent": "运动意图提取",
    "allergen_check": "过敏原检测",
    "meal_comparison": "餐前餐后对比",
}


class AiLogService:
    """AI调用日志服务类"""

    def _truncate(self, text: Optional[str], max_len: int = 200) -> Optional[str]:
        """截断文本到指定长度"""
        if text is None:
            return None
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."

    def log_ai_call(
        self,
        db: Session,
        call_type: str,
        model_name: str,
        input_summary: str,
        success: bool,
        latency_ms: int,
        user_id: Optional[int] = None,
        output_summary: Optional[str] = None,
        error_message: Optional[str] = None,
        token_usage: Optional[int] = None,
    ) -> None:
        """
        记录一次AI调用日志

        注意：此方法不应抛出异常，避免影响主业务流程

        Args:
            db: 数据库会话
            call_type: 调用类型
            model_name: 模型名称
            input_summary: 输入摘要
            success: 是否成功
            latency_ms: 耗时（毫秒）
            user_id: 用户ID（可选）
            output_summary: 输出摘要（可选）
            error_message: 错误信息（可选）
            token_usage: Token使用量（可选）
        """
        try:
            # 处理负数token_usage
            if token_usage is not None and token_usage < 0:
                token_usage = None

            log_entry = AiCallLog(
                user_id=user_id,
                call_type=call_type,
                model_name=model_name,
                input_summary=self._truncate(input_summary, max_len=450),
                output_summary=self._truncate(output_summary, max_len=450),
                success=success,
                error_message=self._truncate(error_message, max_len=1000),
                latency_ms=latency_ms,
                token_usage=token_usage,
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.warning(f"记录AI调用日志失败: {e}")
            try:
                db.rollback()
            except Exception:
                pass

    def get_user_ai_logs(
        self,
        db: Session,
        user_id: int,
        call_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[AiCallLog]]:
        """
        查询用户的AI调用日志

        Args:
            db: 数据库会话
            user_id: 用户ID
            call_type: 调用类型过滤（可选）
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            (总数, 日志列表)
        """
        query = db.query(AiCallLog).filter(AiCallLog.user_id == user_id)

        if call_type:
            query = query.filter(AiCallLog.call_type == call_type)

        query = query.order_by(desc(AiCallLog.created_at))

        total = query.count()
        logs = query.offset(offset).limit(limit).all()

        return total, logs

    def get_ai_log_stats(
        self,
        db: Session,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        获取用户AI调用统计

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            统计数据字典
        """
        base_query = db.query(AiCallLog).filter(AiCallLog.user_id == user_id)

        total_calls = base_query.count()
        success_count = base_query.filter(AiCallLog.success == True).count()
        failure_count = total_calls - success_count
        success_rate = round(success_count / total_calls, 4) if total_calls > 0 else 0.0

        # 平均延迟
        avg_latency = db.query(func.avg(AiCallLog.latency_ms)).filter(
            AiCallLog.user_id == user_id,
            AiCallLog.latency_ms.isnot(None)
        ).scalar()
        avg_latency_ms = round(float(avg_latency), 1) if avg_latency else 0.0

        # 按调用类型分布
        type_rows = db.query(
            AiCallLog.call_type, func.count(AiCallLog.id)
        ).filter(
            AiCallLog.user_id == user_id
        ).group_by(AiCallLog.call_type).all()
        call_type_distribution = {row[0]: row[1] for row in type_rows}

        # 按模型分布
        model_rows = db.query(
            AiCallLog.model_name, func.count(AiCallLog.id)
        ).filter(
            AiCallLog.user_id == user_id
        ).group_by(AiCallLog.model_name).all()
        model_distribution = {row[0]: row[1] for row in model_rows}

        # 最近7天调用数
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_7days_count = base_query.filter(
            AiCallLog.created_at >= seven_days_ago
        ).count()

        return {
            "total_calls": total_calls,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": success_rate,
            "avg_latency_ms": avg_latency_ms,
            "call_type_distribution": call_type_distribution,
            "model_distribution": model_distribution,
            "recent_7days_count": recent_7days_count,
        }


# 全局单例
_ai_log_service: Optional[AiLogService] = None


def get_ai_log_service() -> AiLogService:
    """获取AI日志服务单例"""
    global _ai_log_service
    if _ai_log_service is None:
        _ai_log_service = AiLogService()
    return _ai_log_service
