# 🚀 MCP WebAnalyzer

고성능 웹 분석을 위한 엔터프라이즈급 MCP (Model Context Protocol) 서버입니다. FastMCP와 FastAPI를 기반으로 구축되었으며, 비동기 작업 처리, 캐싱, 모니터링 등 프로덕션 환경에 적합한 기능들을 제공합니다.

<a href="https://glama.ai/mcp/servers/@kimdonghwi94/web-analyzer-mcp">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@kimdonghwi94/web-analyzer-mcp/badge" alt="WebAnalyzer MCP server" />
</a>

## ✨ 주요 기능

### 🔍 웹 분석 도구
- **서브페이지 발견**: 웹사이트의 모든 링크와 서브페이지를 체계적으로 탐색
- **페이지 요약**: AI 기반 웹페이지 내용 요약 및 핵심 정보 추출
- **RAG 콘텐츠 추출**: 검색 증강 생성(RAG)을 위한 구조화된 콘텐츠 추출

### 🏗️ 엔터프라이즈 기능
- **비동기 작업 처리**: Celery + Redis 기반 분산 작업 처리
- **상태 저장**: Redis를 통한 캐싱 및 세션 관리
- **외부 API 연동**: OpenAI/Anthropic API 통합 지원
- **인증 및 보안**: JWT 토큰 및 API 키 기반 인증 시스템
- **모니터링**: Prometheus 메트릭 및 구조화된 로깅
- **실시간 모니터링**: Flower를 통한 Celery 작업 모니터링

## 📋 시스템 요구사항

### Windows 환경
- **Windows 10/11** 또는 **Windows Server 2019+**
- **Python 3.10+** 
- **uv** (Python 패키지 관리자)
- **Docker Desktop** (선택사항)
- **Redis** (로컬 설치 또는 Docker)

### 권장 사양
- **CPU**: 4코어 이상
- **메모리**: 8GB 이상
- **저장공간**: 10GB 이상

## 🚀 빠른 시작 (Windows)

### 1. 환경 준비

```powershell
# Python 3.10+ 설치 확인
python --version

# uv 설치
pip install uv

# 프로젝트 클론
git clone https://github.com/your-username/mcp-webanalyzer.git
cd mcp-webanalyzer

# 의존성 설치
uv sync
```

### 2. 환경 변수 설정

```powershell
# .env 파일 생성
copy .env.example .env

# 설정 파일 편집 (메모장 또는 VS Code)
notepad .env
```

필수 설정 값들:
```env
# 서버 설정
HOST=0.0.0.0
PORT=8080

# 보안 키 (반드시 변경!)
SECRET_KEY=your-very-secure-secret-key-change-this-now
API_KEY=your-secure-api-key-change-this-too

# Redis 설정
REDIS_URL=redis://localhost:6379/0
```

### 3. Redis 실행

#### Option A: Docker 사용
```powershell
docker run -d --name redis-server -p 6379:6379 redis:7-alpine
```

#### Option B: Windows용 Redis 설치
1. [Redis Windows 릴리스](https://github.com/microsoftarchive/redis/releases) 다운로드
2. 설치 후 서비스 시작

### 4. 서버 실행

```powershell
# API 서버 실행
uv run mcp-webanalyzer-api

# 다른 터미널에서 워커 실행 (선택사항)
uv run mcp-webanalyzer-worker
```

### 5. 테스트

```powershell
# 헬스 체크
curl http://localhost:8080/health

# API 테스트
curl -X POST http://localhost:8080/mcp/tools/extract_page_summary ^
  -H "X-API-Key: your-secure-api-key-change-this-too" ^
  -H "Content-Type: application/json" ^
  -d "{\"url\": \"https://example.com\"}"
```

## 🐳 Docker 실행 (Windows)

### 1. Docker Desktop 설치
[Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) 다운로드 및 설치

### 2. 컨테이너 실행
```powershell
# 모든 서비스 시작
docker-compose up -d

# 서비스 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f web-analyzer-api
```

### 3. 접속 확인
- **API 서버**: http://localhost:8080
- **API 문서**: http://localhost:8080/docs
- **Flower 모니터링**: http://localhost:5555
- **헬스 체크**: http://localhost:8080/health

## 🔧 Claude Desktop 연동

### 1. 설정 파일 위치
```
%APPDATA%\Claude\claude_desktop_config.json
```

### 2. 설정 추가
```json
{
  "mcpServers": {
    "web-analyzer": {
      "command": "uv",
      "args": ["run", "mcp-webanalyzer"],
      "cwd": "C:\\Users\\{username}\\mcp-webanalyzer",
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### 3. 원격 서버 연동
```json
{
  "mcpServers": {
    "web-analyzer-remote": {
      "command": "python",
      "args": ["-m", "mcp_webanalyzer.mcp_client"],
      "cwd": "C:\\Users\\{username}\\mcp-webanalyzer",
      "env": {
        "API_BASE_URL": "http://localhost:8080",
        "API_KEY": "your-secure-api-key-change-this-too"
      }
    }
  }
}
```

## 🎯 사용 예시

### 기본 웹 분석
```python
# 페이지 요약 추출
result = extract_page_summary("https://example.com")

# 서브페이지 발견
links = discover_subpages("https://example.com", max_depth=2)

# RAG용 콘텐츠 추출
content = extract_content_for_rag("https://example.com")
```

### API 호출
```powershell
# 서브페이지 발견
curl -X POST http://localhost:8080/mcp/tools/discover_subpages ^
  -H "X-API-Key: your-api-key" ^
  -H "Content-Type: application/json" ^
  -d "{\"url\": \"https://example.com\", \"max_depth\": 2}"
```

## 📊 모니터링 및 관리

### 로그 확인
```powershell
# 서비스 로그 (Docker)
docker-compose logs -f web-analyzer-api

# 로컬 실행 로그
Get-Content logs\app.log -Wait
```

### 메트릭 확인
- **Prometheus 메트릭**: http://localhost:9090/metrics
- **Flower 대시보드**: http://localhost:5555

### 성능 모니터링
```powershell
# 메모리 사용량 확인
tasklist /fi "imagename eq python.exe"

# Redis 상태 확인
redis-cli ping
```

## 🛠️ 개발 환경 설정

### 1. 개발 의존성 설치
```powershell
uv sync --dev
```

### 2. 코드 품질 도구
```powershell
# 코드 포맷팅
uv run black mcp_webanalyzer/

# 린팅
uv run flake8 mcp_webanalyzer/

# 타입 체크
uv run mypy mcp_webanalyzer/
```

### 3. 테스트 실행
```powershell
uv run pytest tests/
```

## 📖 추가 문서

- [Architecture Guide](./architecture.md) - 시스템 아키텍처 상세 설명
- [Deployment Guide](./REMOTE_DEPLOYMENT_GUIDE.md) - 프로덕션 배포 가이드
- [Quick Start Guide](./quick-start.md) - 빠른 시작 가이드
- [API Documentation](http://localhost:8080/docs) - 실시간 API 문서

## 🤝 기여 방법

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🆘 지원 및 문제 해결

### 일반적인 문제들

1. **포트 충돌**: 다른 애플리케이션이 8080 포트를 사용하는 경우
   ```powershell
   netstat -an | findstr :8080
   ```

2. **Redis 연결 실패**: Redis 서비스가 실행되지 않는 경우
   ```powershell
   redis-cli ping
   ```

3. **의존성 문제**: 가상 환경 재생성
   ```powershell
   rm -rf .venv
   uv sync
   ```

### 도움말
- GitHub Issues: [프로젝트 Issues](https://github.com/your-username/mcp-webanalyzer/issues)
- 문서: [전체 문서](./docs/)
- 예제: [examples/](./examples/)

---

**Made with ❤️ for the MCP community**