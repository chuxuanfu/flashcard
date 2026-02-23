"""
认证路由
简单的密码登录
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from backend.config import PASSWORD, SECRET_KEY, ALGORITHM, TOKEN_EXPIRE_DAYS
from backend.schemas import LoginRequest, Token

router = APIRouter(prefix="/auth", tags=["认证"])
security = HTTPBearer(auto_error=False)


def create_token() -> str:
    """创建 JWT token"""
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": "user"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> bool:
    """验证 token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub") == "user"
    except JWTError:
        return False


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """验证当前用户"""
    if not credentials:
        raise HTTPException(status_code=401, detail="未登录")
    
    if not verify_token(credentials.credentials):
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    
    return True


@router.post("/login", response_model=Token)
async def login(request: LoginRequest):
    """登录"""
    if request.password != PASSWORD:
        raise HTTPException(status_code=401, detail="密码错误")
    
    token = create_token()
    return Token(access_token=token)


@router.get("/verify")
async def verify(user: bool = Depends(get_current_user)):
    """验证 token 是否有效"""
    return {"valid": True}
