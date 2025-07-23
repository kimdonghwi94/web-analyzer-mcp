# app/core/config.py - 설정 관리
from pydantic import BaseModel
from typing import List
import os


class Settings(BaseModel):
    """애플리케이션 설정"""

    # 서버 설정
    HOST: str = "0.0.0.0"
    PORT: int = 8002
    DEBUG: bool = True

    # 보안 설정
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-this-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30
    
    # API Key 설정
    API_KEYS: List[str] = ["sk-Tby3rrjF196gbP8sM6S3TjJ9vwSiU7uTQ0XNHdnlyc8"]
    API_KEY_HEADER: str = "sk-Tby3rrjF196gbP8sM6S3TjJ9vwSiU7uTQ0XNHdnlyc8"

    # Redis 설정
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))

    # CORS 설정
    ALLOWED_HOSTS: List[str] = ["*"]

    # MCP 서버 설정
    MCP_SERVERS: dict = {
        "web_search": {
            "url": "http://localhost:8001",
            "name": "Web Search Server",
            "description": "웹 검색 및 RAG 기능 제공"
        },
        "database": {
            "url": "http://localhost:8002",
            "name": "Database Server",
            "description": "데이터베이스 쿼리 기능 제공"
        },
        "file_system": {
            "url": "http://localhost:8003",
            "name": "File System Server",
            "description": "파일 시스템 접근 기능 제공"
        },
        "custom_api": {
            "url": "http://localhost:8004",
            "name": "Custom API Server",
            "description": "커스텀 API 기능 제공"
        }
    }

    # 작업 설정
    TASK_TIMEOUT: int = 300  # 5분
    TASK_CLEANUP_INTERVAL: int = 3600  # 1시간

    # 프로토콜 설정
    MCP_PROTOCOL_VERSION: str = "2024-11-05"

    class Config:
        env_file = ".env"
        case_sensitive = True


# 전역 설정 인스턴스
settings = Settings()