"""
AI log CRUD helpers.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db_models.ai_call_log import AiCallLog


def create_ai_call_log(db: Session, log_entry: AiCallLog) -> None:
    db.add(log_entry)
    db.commit()


def get_user_ai_logs(
    db: Session,
    user_id: int,
    call_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[int, List[AiCallLog]]:
    query = db.query(AiCallLog).filter(AiCallLog.user_id == user_id)

    if call_type:
        query = query.filter(AiCallLog.call_type == call_type)

    query = query.order_by(desc(AiCallLog.created_at))

    total = query.count()
    logs = query.offset(offset).limit(limit).all()

    return total, logs


def get_ai_log_stats(db: Session, user_id: int) -> Dict[str, Any]:
    base_query = db.query(AiCallLog).filter(AiCallLog.user_id == user_id)

    total_calls = base_query.count()
    success_count = base_query.filter(AiCallLog.success == True).count()
    failure_count = total_calls - success_count
    success_rate = round(success_count / total_calls, 4) if total_calls > 0 else 0.0

    avg_latency = (
        db.query(func.avg(AiCallLog.latency_ms))
        .filter(AiCallLog.user_id == user_id, AiCallLog.latency_ms.isnot(None))
        .scalar()
    )
    avg_latency_ms = round(float(avg_latency), 1) if avg_latency else 0.0

    type_rows = (
        db.query(AiCallLog.call_type, func.count(AiCallLog.id))
        .filter(AiCallLog.user_id == user_id)
        .group_by(AiCallLog.call_type)
        .all()
    )
    call_type_distribution = {row[0]: row[1] for row in type_rows}

    model_rows = (
        db.query(AiCallLog.model_name, func.count(AiCallLog.id))
        .filter(AiCallLog.user_id == user_id)
        .group_by(AiCallLog.model_name)
        .all()
    )
    model_distribution = {row[0]: row[1] for row in model_rows}

    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_7days_count = base_query.filter(AiCallLog.created_at >= seven_days_ago).count()

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
