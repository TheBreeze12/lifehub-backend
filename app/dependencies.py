"""
FastAPI依赖注入模块
提供认证、数据库会话等通用依赖
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models.user import User
from app.utils.auth import verify_access_token, TokenData

# HTTP Bearer认证方案
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    获取当前认证用户
    
    从请求头的Authorization字段提取Bearer Token，验证后返回用户对象
    
    Args:
        credentials: HTTP Bearer凭证
        db: 数据库会话
        
    Returns:
        User: 当前认证用户
        
    Raises:
        HTTPException: 401 未授权（Token无效或缺失）
        HTTPException: 404 用户不存在
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 检查是否提供了凭证
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证Access Token
    token = credentials.credentials
    token_data: Optional[TokenData] = verify_access_token(token)
    
    if token_data is None:
        raise credentials_exception
    
    # 查询用户
    user = db.query(User).filter(User.id == token_data.user_id).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    获取当前认证用户（可选）
    
    与get_current_user类似，但如果未提供Token则返回None而不是抛出异常
    适用于同时支持认证和非认证访问的接口
    
    Args:
        credentials: HTTP Bearer凭证（可选）
        db: 数据库会话
        
    Returns:
        Optional[User]: 当前认证用户，未认证时返回None
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    token_data: Optional[TokenData] = verify_access_token(token)
    
    if token_data is None:
        return None
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    return user
