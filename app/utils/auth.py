"""
JWT认证工具函数
实现Access Token + Refresh Token双令牌机制
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# 密码加密上下文（使用bcrypt算法）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "lifehub-secret-key-change-in-production-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Access Token有效期30分钟
REFRESH_TOKEN_EXPIRE_DAYS = 7     # Refresh Token有效期7天


class TokenData(BaseModel):
    """Token数据模型"""
    user_id: Optional[int] = None
    nickname: Optional[str] = None
    token_type: Optional[str] = None  # "access" 或 "refresh"


class TokenResponse(BaseModel):
    """Token响应模型"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Access Token过期时间（秒）


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码与哈希密码是否匹配
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码
        
    Returns:
        bool: 密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    对密码进行哈希加密
    
    Args:
        password: 明文密码
        
    Returns:
        str: 哈希后的密码
    """
    return pwd_context.hash(password)


def create_access_token(user_id: int, nickname: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建Access Token
    
    Args:
        user_id: 用户ID
        nickname: 用户昵称
        expires_delta: 自定义过期时间
        
    Returns:
        str: JWT Access Token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(user_id),
        "nickname": nickname,
        "type": "access",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: int, nickname: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建Refresh Token
    
    Args:
        user_id: 用户ID
        nickname: 用户昵称
        expires_delta: 自定义过期时间
        
    Returns:
        str: JWT Refresh Token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": str(user_id),
        "nickname": nickname,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_tokens(user_id: int, nickname: str) -> Tuple[str, str]:
    """
    创建Access Token和Refresh Token对
    
    Args:
        user_id: 用户ID
        nickname: 用户昵称
        
    Returns:
        Tuple[str, str]: (access_token, refresh_token)
    """
    access_token = create_access_token(user_id, nickname)
    refresh_token = create_refresh_token(user_id, nickname)
    return access_token, refresh_token


def decode_token(token: str) -> Optional[TokenData]:
    """
    解码并验证JWT Token
    
    Args:
        token: JWT Token字符串
        
    Returns:
        Optional[TokenData]: 解码后的Token数据，验证失败返回None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        nickname: str = payload.get("nickname")
        token_type: str = payload.get("type")
        
        if user_id is None:
            return None
            
        return TokenData(
            user_id=int(user_id),
            nickname=nickname,
            token_type=token_type
        )
    except JWTError:
        return None


def verify_access_token(token: str) -> Optional[TokenData]:
    """
    验证Access Token
    
    Args:
        token: JWT Access Token
        
    Returns:
        Optional[TokenData]: 验证成功返回Token数据，失败返回None
    """
    token_data = decode_token(token)
    if token_data is None:
        return None
    if token_data.token_type != "access":
        return None
    return token_data


def verify_refresh_token(token: str) -> Optional[TokenData]:
    """
    验证Refresh Token
    
    Args:
        token: JWT Refresh Token
        
    Returns:
        Optional[TokenData]: 验证成功返回Token数据，失败返回None
    """
    token_data = decode_token(token)
    if token_data is None:
        return None
    if token_data.token_type != "refresh":
        return None
    return token_data
