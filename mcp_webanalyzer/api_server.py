"""FastAPI HTTP server for Web Analyzer MCP."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import APIKeyHeader
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from pydantic import BaseModel, Field
import uvicorn
from contextlib import asynccontextmanager

from .config import get_settings
from .server import discover_subpages, extract_page_summary, extract_content_for_rag
from .worker import (
    discover_subpages_task, 
    extract_page_summary_task, 
    extract_content_for_rag_task,
    batch_analyze_urls_task
)
from .resources import resource_manager, ResourceManager
from .external_apis import api_manager, ExternalAPIManager
from .utils.auth import require_auth, create_access_token, AuthError
from .utils.cache import cache_manager, CacheManager
from .utils.monitoring import (
    metrics_collector, 
    MetricsCollector, 
    RequestMonitor,
    monitor_performance,
    get_logger
)

settings = get_settings()
logger = get_logger(__name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Pydantic models
class AnalysisRequest(BaseModel):
    url: str = Field(..., description="URL to analyze")
    max_depth: Optional[int] = Field(default=2, ge=1, le=5, description="Maximum crawl depth")
    max_pages: Optional[int] = Field(default=100, ge=1, le=1000, description="Maximum pages to discover")

class SummaryRequest(BaseModel):
    url: str = Field(..., description="URL to summarize")
    enhance: Optional[bool] = Field(default=False, description="Use AI enhancement")
    provider: Optional[str] = Field(default="openai", description="AI provider for enhancement")

class RAGRequest(BaseModel):
    url: str = Field(..., description="URL to analyze for RAG")
    question: Optional[str] = Field(default=None, description="Question to focus analysis on")
    enhance: Optional[bool] = Field(default=False, description="Use AI enhancement")

class BatchAnalysisRequest(BaseModel):
    urls: List[str] = Field(..., min_items=1, max_items=50, description="URLs to analyze")
    analysis_type: str = Field(default="summary", description="Type of analysis")

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class AuthRequest(BaseModel):
    username: str
    password: str

# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Web Analyzer API Server")
    
    # Startup
    try:
        # Initialize connections
        await cache_manager.get_redis()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error("Failed to connect to Redis", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("Shutting down Web Analyzer API Server")
    await cache_manager.close()
    await api_manager.close()
    await metrics_collector.close()

# Create FastAPI app
app = FastAPI(
    title="Web Analyzer MCP Server",
    description="Advanced web content analysis and extraction API",
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(SlowAPIMiddleware)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
)

# Middleware for request monitoring
@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    """Monitor HTTP requests."""
    async with RequestMonitor():
        start_time = datetime.now()
        response = await call_next(request)
        duration = (datetime.now() - start_time).total_seconds()
        
        await metrics_collector.record_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration=duration
        )
        
        return response

# Health and monitoring endpoints
@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Health check endpoint."""
    health_status = await metrics_collector.get_health_status()
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)

@app.get("/metrics", tags=["Monitoring"])
async def get_metrics():
    """Prometheus metrics endpoint."""
    metrics_data = await metrics_collector.get_metrics_data()
    return Response(content=metrics_data, media_type="text/plain")

@app.get("/", response_class=HTMLResponse, tags=["General"])
async def dashboard():
    """Dashboard homepage."""
    dashboard_html = await resource_manager.create_dashboard()
    return HTMLResponse(content=dashboard_html)

# Authentication endpoints
@app.post("/auth/token", tags=["Authentication"])
async def login(auth_request: AuthRequest):
    """Get access token."""
    # Simple authentication (in production, verify against database)
    if auth_request.username == "admin" and auth_request.password == "admin":
        access_token = create_access_token(
            data={"sub": auth_request.username, "role": "admin"}
        )
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

# Core analysis endpoints
@app.post("/analyze/discover", response_model=TaskResponse, tags=["Analysis"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def discover_pages(
    request: Request,
    analysis_request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    user: Dict[str, Any] = Depends(require_auth)
):
    """Discover subpages from a URL (async task)."""
    try:
        # Start async task
        task = discover_subpages_task.delay(
            analysis_request.url,
            analysis_request.max_depth,
            analysis_request.max_pages
        )
        
        logger.info(
            "Started page discovery task",
            task_id=task.id,
            url=analysis_request.url,
            user=user.get("sub")
        )
        
        return TaskResponse(
            task_id=task.id,
            status="pending",
            message=f"Started discovering pages for {analysis_request.url}"
        )
        
    except Exception as e:
        logger.error("Failed to start discovery task", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/summary", response_model=TaskResponse, tags=["Analysis"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def extract_summary(
    request: Request,
    summary_request: SummaryRequest,
    user: Dict[str, Any] = Depends(require_auth)
):
    """Extract page summary (async task)."""
    try:
        task = extract_page_summary_task.delay(summary_request.url)
        
        logger.info(
            "Started summary extraction task",
            task_id=task.id,
            url=summary_request.url,
            user=user.get("sub")
        )
        
        return TaskResponse(
            task_id=task.id,
            status="pending",
            message=f"Started extracting summary for {summary_request.url}"
        )
        
    except Exception as e:
        logger.error("Failed to start summary task", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/rag", response_model=TaskResponse, tags=["Analysis"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def extract_rag_content(
    request: Request,
    rag_request: RAGRequest,
    user: Dict[str, Any] = Depends(require_auth)
):
    """Extract content for RAG (async task)."""
    try:
        task = extract_content_for_rag_task.delay(
            rag_request.url,
            rag_request.question
        )
        
        logger.info(
            "Started RAG extraction task",
            task_id=task.id,
            url=rag_request.url,
            question=rag_request.question,
            user=user.get("sub")
        )
        
        return TaskResponse(
            task_id=task.id,
            status="pending",
            message=f"Started RAG extraction for {rag_request.url}"
        )
        
    except Exception as e:
        logger.error("Failed to start RAG task", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/batch", response_model=TaskResponse, tags=["Analysis"])
@limiter.limit("10/minute")
async def batch_analyze(
    request: Request,
    batch_request: BatchAnalysisRequest,
    user: Dict[str, Any] = Depends(require_auth)
):
    """Batch analyze multiple URLs."""
    try:
        task = batch_analyze_urls_task.delay(
            batch_request.urls,
            batch_request.analysis_type
        )
        
        logger.info(
            "Started batch analysis task",
            task_id=task.id,
            url_count=len(batch_request.urls),
            analysis_type=batch_request.analysis_type,
            user=user.get("sub")
        )
        
        return TaskResponse(
            task_id=task.id,
            status="pending",
            message=f"Started batch analysis of {len(batch_request.urls)} URLs"
        )
        
    except Exception as e:
        logger.error("Failed to start batch task", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Synchronous analysis endpoints (for immediate results)
@app.post("/analyze/sync/summary", tags=["Synchronous Analysis"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
@monitor_performance("sync_summary")
async def sync_extract_summary(
    request: Request,
    summary_request: SummaryRequest,
    user: Dict[str, Any] = Depends(require_auth)
):
    """Extract page summary synchronously."""
    try:
        # Check cache first
        cache_key = f"summary:{summary_request.url}"
        cached_result = await cache_manager.get(cache_key)
        
        if cached_result:
            await metrics_collector.record_cache_hit("summary")
            return {"result": cached_result, "cached": True}
        
        await metrics_collector.record_cache_miss("summary")
        
        # Extract summary
        result = await extract_page_summary(summary_request.url)
        
        # Enhance with AI if requested
        if summary_request.enhance:
            enhanced_result = await api_manager.enhance_analysis(
                result,
                provider=summary_request.provider,
                task="summarize"
            )
            result = {
                "original": result,
                "enhanced": enhanced_result["result"],
                "provider": summary_request.provider
            }
        
        # Cache result
        await cache_manager.set(cache_key, result, ttl=3600)
        
        return {"result": result, "cached": False}
        
    except Exception as e:
        logger.error("Sync summary extraction failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Task status endpoints
@app.get("/tasks/{task_id}", tags=["Tasks"])
async def get_task_status(
    task_id: str,
    user: Dict[str, Any] = Depends(require_auth)
):
    """Get task status and result."""
    try:
        from celery.result import AsyncResult
        
        task_result = AsyncResult(task_id)
        
        if task_result.state == "PENDING":
            response = {
                "task_id": task_id,
                "status": "pending",
                "message": "Task is waiting to be processed"
            }
        elif task_result.state == "PROGRESS":
            response = {
                "task_id": task_id,
                "status": "progress",
                "message": "Task is being processed",
                "meta": task_result.info
            }
        elif task_result.state == "SUCCESS":
            response = {
                "task_id": task_id,
                "status": "success",
                "result": task_result.result
            }
        else:  # FAILURE
            response = {
                "task_id": task_id,
                "status": "failed",
                "error": str(task_result.info)
            }
        
        return response
        
    except Exception as e:
        logger.error("Failed to get task status", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Resource endpoints
@app.get("/reports/{report_id}", response_class=HTMLResponse, tags=["Resources"])
async def get_report(
    report_id: str,
    user: Dict[str, Any] = Depends(require_auth)
):
    """Get generated report by ID."""
    try:
        report_html = await resource_manager.get_report(report_id)
        
        if not report_html:
            raise HTTPException(status_code=404, detail="Report not found")
        
        return HTMLResponse(content=report_html)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get report", report_id=report_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports", tags=["Resources"])
async def list_reports(
    limit: int = 50,
    user: Dict[str, Any] = Depends(require_auth)
):
    """List available reports."""
    try:
        reports = await resource_manager.list_reports(limit)
        return {"reports": reports}
        
    except Exception as e:
        logger.error("Failed to list reports", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Cache management endpoints
@app.delete("/cache/{prefix}", tags=["Cache"])
async def clear_cache(
    prefix: str,
    user: Dict[str, Any] = Depends(require_auth)
):
    """Clear cache by prefix."""
    try:
        cleared_count = await cache_manager.clear_prefix(prefix)
        
        logger.info("Cache cleared", prefix=prefix, count=cleared_count, user=user.get("sub"))
        
        return {"message": f"Cleared {cleared_count} items from cache", "prefix": prefix}
        
    except Exception as e:
        logger.error("Failed to clear cache", prefix=prefix, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# MCP compatibility endpoint
@app.post("/mcp/tools/{tool_name}", tags=["MCP Compatibility"])
async def call_mcp_tool(
    tool_name: str,
    parameters: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_auth)
):
    """Call MCP tool for compatibility."""
    try:
        if tool_name == "discover_subpages":
            result = await discover_subpages(
                parameters.get("url"),
                parameters.get("max_depth", 2),
                parameters.get("max_pages", 100)
            )
        elif tool_name == "extract_page_summary":
            result = await extract_page_summary(parameters.get("url"))
        elif tool_name == "extract_content_for_rag":
            result = await extract_content_for_rag(
                parameters.get("url"),
                parameters.get("question")
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
        
        return {"result": result}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("MCP tool call failed", tool=tool_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Main entry point for the API server."""
    uvicorn.run(
        "mcp_webanalyzer.api_server:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()