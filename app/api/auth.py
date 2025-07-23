# app/api/auth.py - 인증 관련 엔드포인트
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict, Any
import logging
from datetime import datetime, timedelta

from app.core.security import security_manager, get_current_user
from app.core.redis import redis_manager
from pydantic import BaseModel, EmailStr
import uuid

logger = logging.getLogger(__name__)

# 인증 라우터 생성
auth_router = APIRouter()


# ==== 요청/응답 모델 ====

class UserRegister(BaseModel):
    """사용자 등록 요청"""
    username: str
    email: EmailStr
    password: str
    full_name: str = ""


class UserLogin(BaseModel):
    """사용자 로그인 요청"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """토큰 응답"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_info: Dict[str, Any]


class UserProfile(BaseModel):
    """사용자 프로필"""
    user_id: str
    username: str
    email: str
    full_name: str
    created_at: str
    last_login: str


# ==== 임시 사용자 데이터베이스 (실제 환경에서는 PostgreSQL 등 사용) ====
USERS_DB = {
    "admin": {
        "user_id": "user_001",
        "username": "admin",
        "email": "admin@mcpbridge.com",
        "full_name": "MCP Bridge Administrator",
        "hashed_password": security_manager.hash_password("admin123"),
        "created_at": "2024-01-01T00:00:00",
        "is_active": True
    },
    "test_user": {
        "user_id": "user_002",
        "username": "test_user",
        "email": "test@mcpbridge.com",
        "full_name": "Test User",
        "hashed_password": security_manager.hash_password("test123"),
        "created_at": "2024-01-01T00:00:00",
        "is_active": True
    }
}


# ==== 인증 헬퍼 함수 ====

async def authenticate_user(username: str, password: str) -> Dict[str, Any]:
    """사용자 인증"""
    user = USERS_DB.get(username)
    if not user:
        return None

    if not user["is_active"]:
        return None

    if not security_manager.verify_password(password, user["hashed_password"]):
        return None

    # 마지막 로그인 시간 업데이트
    user["last_login"] = datetime.now().isoformat()

    return user


async def get_user_by_username(username: str) -> Dict[str, Any]:
    """사용자명으로 사용자 조회"""
    return USERS_DB.get(username)


# ==== 인증 엔드포인트 ====

@auth_router.post("/register", response_model=Dict[str, str])
async def register_user(user_data: UserRegister):
    """사용자 등록"""
    try:
        # 중복 사용자명 확인
        if user_data.username in USERS_DB:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )

        # 새 사용자 생성
        user_id = f"user_{str(uuid.uuid4())[:8]}"
        new_user = {
            "user_id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "hashed_password": security_manager.hash_password(user_data.password),
            "created_at": datetime.now().isoformat(),
            "is_active": True
        }

        # 데이터베이스에 저장
        USERS_DB[user_data.username] = new_user

        logger.info(f"새 사용자 등록: {user_data.username}")
        return {
            "message": "User registered successfully",
            "user_id": user_id,
            "username": user_data.username
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 등록 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@auth_router.post("/login", response_model=TokenResponse)
async def login_user(login_data: UserLogin):
    """사용자 로그인"""
    try:
        # 사용자 인증
        user = await authenticate_user(login_data.username, login_data.password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # API 키 확인 (테스트 목적으로 설정의 첫 번째 API 키 사용)
        api_key = "sk-Tby3rrjF196gbP8sM6S3TjJ9vwSiU7uTQ0XNHdnlyc8"

        # 사용자 정보 (비밀번호 제외)
        user_info = {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"]
        }

        logger.info(f"사용자 로그인 성공: {user['username']}")

        return TokenResponse(
            access_token=api_key,
            token_type="apikey",
            expires_in=0,  # API 키는 만료되지 않음
            user_info=user_info
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"로그인 처리 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@auth_router.post("/logout")
async def logout_user(user: Dict[str, Any] = Depends(get_current_user)):
    """사용자 로그아웃 처리"""
    try:
        # API 키 기반 인증에서는 로그아웃 처리가 단순화됨
        logger.info(f"사용자 로그아웃: {user['username']}")
        return {"message": "Logout successful"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"로그아웃 처리 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@auth_router.get("/me", response_model=UserProfile)
async def get_current_user_profile(user: Dict[str, Any] = Depends(get_current_user)):
    """현재 사용자 프로필 조회"""
    try:
        # 데이터베이스에서 최신 사용자 정보 조회
        full_user = await get_user_by_username(user["username"])

        if not full_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserProfile(
            user_id=full_user["user_id"],
            username=full_user["username"],
            email=full_user["email"],
            full_name=full_user["full_name"],
            created_at=full_user["created_at"],
            last_login=full_user.get("last_login", "")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"프로필 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile retrieval failed"
        )


@auth_router.post("/verify-token")
async def verify_token(user: Dict[str, Any] = Depends(get_current_user)):
    """토큰 유효성 검증"""
    return {
        "valid": True,
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"]
        }
    }


@auth_router.get("/sessions")
async def get_user_sessions(user: Dict[str, Any] = Depends(get_current_user)):
    """사용자의 활성 세션 목록 조회"""
    try:
        # Redis에서 사용자의 모든 세션 조회
        # 실제 구현에서는 Redis key pattern 검색 사용
        sessions = []

        # 예시 세션 정보 (실제로는 Redis에서 조회)
        sessions.append({
            "session_id": "session_example",
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "ip_address": "127.0.0.1",
            "user_agent": "MCP Client Bridge"
        })

        return {"sessions": sessions}

    except Exception as e:
        logger.error(f"세션 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session retrieval failed"
        )


# ==== OAuth2 호환 엔드포인트 ====

@auth_router.post("/token", response_model=TokenResponse)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 호환 토큰 엔드포인트 (API 키 반환)"""
    # UserLogin 형식으로 변환
    login_data = UserLogin(
        username=form_data.username,
        password=form_data.password
    )

    # 기존 login_user 함수 재사용
    return await login_user(login_data)