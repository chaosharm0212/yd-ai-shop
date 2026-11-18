"""公共依赖：从请求头 token 换出当前用户。"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if cred is None:
        raise HTTPException(status_code=401, detail="未登录：请求头缺少 token")
    user_id = decode_token(cred.credentials)
    if user_id is None:
        raise HTTPException(status_code=401, detail="token 无效或已过期")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    if not user.is_enabled:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    return user
