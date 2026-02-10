"""
数据脱敏中间件 (Phase 54)

功能：
1. 日志中敏感信息脱敏（手机号/邮箱/位置坐标）
2. 上传数据中的位置信息模糊化
3. 响应中的敏感字段脱敏（password/token/secret/api_key等）

设计原则：
- 脱敏在中间件层统一处理，业务代码无需关心
- 坐标模糊化精度降低到小数点后2位（约1km精度），保留大致区域信息
- 敏感字段（password/token/secret）完全遮蔽或部分遮蔽
- 日志过滤器通过logging.Filter实现，对所有日志生效
"""
import re
import json
import copy
import logging
from typing import Any, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from fastapi.responses import JSONResponse


# ============================================================
# 1. 基础脱敏工具函数
# ============================================================

# 中国大陆手机号正则：1开头，第二位3-9，共11位
_PHONE_PATTERN = re.compile(
    r'(?<!\d)'                    # 前面不是数字
    r'(?:\+?86)?'                 # 可选+86或86前缀
    r'(1[3-9]\d)\d{4}(\d{4})'    # 捕获前3位和后4位
    r'(?!\d)'                     # 后面不是数字
)

# 邮箱正则
_EMAIL_PATTERN = re.compile(
    r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
)

# 敏感字段名集合（小写匹配）
_SENSITIVE_FIELD_NAMES = {
    "password", "passwd", "pwd",
    "token", "access_token", "refresh_token",
    "secret", "api_secret", "client_secret",
    "api_key", "apikey", "secret_key",
    "authorization",
}

# 坐标相关字段名集合（小写匹配）
_COORD_FIELD_NAMES = {
    "latitude", "lat",
    "longitude", "lng", "lon", "long",
}


def mask_phone(text: str) -> str:
    """
    脱敏单个手机号字符串
    - 标准11位：138****5678
    - 带+86前缀：+86138****5678
    - 非手机号格式：原样返回
    """
    if not text:
        return text

    # 尝试匹配完整手机号
    match = _PHONE_PATTERN.search(text)
    if match:
        return _PHONE_PATTERN.sub(
            lambda m: f"{m.group(1)}****{m.group(2)}",
            text
        )

    return text


def mask_email(text: str) -> str:
    """
    脱敏单个邮箱字符串
    - testuser@example.com -> te****@example.com
    - ab@example.com -> a****@example.com
    - 非邮箱格式：原样返回
    """
    if not text:
        return text

    match = _EMAIL_PATTERN.search(text)
    if not match:
        return text

    def _mask_email_match(m):
        local = m.group(1)
        domain = m.group(2)
        if len(local) <= 1:
            masked_local = local + "****"
        elif len(local) <= 3:
            masked_local = local[0] + "****"
        else:
            masked_local = local[:2] + "****"
        return f"{masked_local}@{domain}"

    return _EMAIL_PATTERN.sub(_mask_email_match, text)


def mask_sensitive_in_text(text: Optional[str]) -> Optional[str]:
    """
    对文本中的手机号和邮箱进行脱敏
    """
    if text is None:
        return None
    if not text:
        return text

    # 先脱敏手机号
    result = _PHONE_PATTERN.sub(
        lambda m: f"{m.group(1)}****{m.group(2)}",
        text
    )
    # 再脱敏邮箱
    def _mask_email_match(m):
        local = m.group(1)
        domain = m.group(2)
        if len(local) <= 1:
            masked_local = local + "****"
        elif len(local) <= 3:
            masked_local = local[0] + "****"
        else:
            masked_local = local[:2] + "****"
        return f"{masked_local}@{domain}"

    result = _EMAIL_PATTERN.sub(_mask_email_match, result)
    return result


# ============================================================
# 2. 位置坐标模糊化
# ============================================================

def fuzz_location(latitude: float, longitude: float) -> Tuple[float, float]:
    """
    模糊化经纬度坐标：截断到小数点后2位（约1km精度）
    """
    return round(latitude, 2), round(longitude, 2)


def fuzz_coords_in_dict(data: Any) -> Any:
    """
    递归遍历字典/列表，将坐标字段模糊化
    """
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if key.lower() in _COORD_FIELD_NAMES and isinstance(value, (int, float)):
                result[key] = round(float(value), 2)
            else:
                result[key] = fuzz_coords_in_dict(value)
        return result
    elif isinstance(data, list):
        return [fuzz_coords_in_dict(item) for item in data]
    else:
        return data


# ============================================================
# 3. 响应敏感字段脱敏
# ============================================================

def _mask_sensitive_value(key: str, value: Any) -> Any:
    """根据字段名对值进行脱敏"""
    if key.lower() in {"password", "passwd", "pwd"}:
        return "******"
    if value is None:
        return "******"
    if not isinstance(value, str):
        return "******"
    # token/secret/api_key 类型：保留前6个字符+******
    if len(value) <= 6:
        return "******"
    return value[:6] + "******"


def mask_sensitive_fields_in_dict(data: Any) -> Any:
    """
    递归遍历字典/列表，对敏感字段名对应的值进行脱敏
    """
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if key.lower() in _SENSITIVE_FIELD_NAMES:
                result[key] = _mask_sensitive_value(key, value)
            else:
                result[key] = mask_sensitive_fields_in_dict(value)
        return result
    elif isinstance(data, list):
        return [mask_sensitive_fields_in_dict(item) for item in data]
    else:
        return data


def mask_sensitive_text_in_dict(data: Any) -> Any:
    """
    递归遍历字典/列表，对字符串值中的手机号和邮箱进行脱敏
    """
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = mask_sensitive_in_text(value)
            elif isinstance(value, (dict, list)):
                result[key] = mask_sensitive_text_in_dict(value)
            else:
                result[key] = value
        return result
    elif isinstance(data, list):
        return [mask_sensitive_text_in_dict(item) for item in data]
    else:
        return data


# ============================================================
# 4. 综合脱敏入口
# ============================================================

def apply_response_masking(data: Any) -> Any:
    """
    对响应数据应用全部脱敏规则：
    1. 敏感字段脱敏（password/token/secret）
    2. 坐标模糊化
    3. 文本中手机号/邮箱脱敏
    """
    if not isinstance(data, (dict, list)):
        return data
    result = mask_sensitive_fields_in_dict(data)
    result = fuzz_coords_in_dict(result)
    result = mask_sensitive_text_in_dict(result)
    return result


def apply_request_masking(data: Any) -> Any:
    """
    对请求数据应用脱敏规则：
    1. 坐标模糊化（位置信息模糊化）
    2. 文本中手机号/邮箱脱敏
    """
    if not isinstance(data, (dict, list)):
        return data
    result = fuzz_coords_in_dict(data)
    result = mask_sensitive_text_in_dict(result)
    return result


# ============================================================
# 5. 日志脱敏过滤器
# ============================================================

class SensitiveDataFilter(logging.Filter):
    """
    日志脱敏过滤器：自动对日志消息中的手机号和邮箱进行脱敏
    使用方式：
        handler.addFilter(SensitiveDataFilter())
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_sensitive_in_text(record.msg)
        # 处理格式化参数中的字符串
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: mask_sensitive_in_text(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    mask_sensitive_in_text(a) if isinstance(a, str) else a
                    for a in record.args
                )
        return True


# ============================================================
# 6. FastAPI/Starlette 中间件
# ============================================================

class DataMaskingMiddleware(BaseHTTPMiddleware):
    """
    数据脱敏中间件：
    - 请求体：模糊化坐标、脱敏文本中的手机号/邮箱
    - 响应体：脱敏敏感字段、模糊化坐标、脱敏文本
    
    仅处理 application/json 类型的请求和响应
    """

    async def dispatch(self, request: Request, call_next):
        # --- 请求体脱敏 ---
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body_json = json.loads(body_bytes)
                    masked_body = apply_request_masking(body_json)
                    masked_bytes = json.dumps(masked_body, ensure_ascii=False).encode("utf-8")

                    # 替换请求体：创建一个新的receive函数
                    async def receive():
                        return {"type": "http.request", "body": masked_bytes}

                    request._receive = receive
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass  # 非合法JSON，跳过

        # --- 调用下游处理 ---
        response = await call_next(request)

        # --- 响应体脱敏 ---
        resp_content_type = response.headers.get("content-type", "")
        if "application/json" in resp_content_type:
            try:
                # 读取响应体
                body_chunks = []
                async for chunk in response.body_iterator:
                    if isinstance(chunk, bytes):
                        body_chunks.append(chunk)
                    else:
                        body_chunks.append(chunk.encode("utf-8"))
                body_bytes = b"".join(body_chunks)

                if body_bytes:
                    body_json = json.loads(body_bytes)
                    masked_json = apply_response_masking(body_json)
                    # 使用与FastAPI一致的紧凑JSON序列化格式，避免content-length不匹配
                    masked_bytes = json.dumps(
                        masked_json, ensure_ascii=False, separators=(",", ":")
                    ).encode("utf-8")

                    # 构建新的响应，移除原始content-length让Response自动计算
                    new_headers = {
                        k: v for k, v in response.headers.items()
                        if k.lower() != "content-length"
                    }
                    return Response(
                        content=masked_bytes,
                        status_code=response.status_code,
                        headers=new_headers,
                        media_type="application/json",
                    )
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass  # 非合法JSON响应，原样返回

        return response
