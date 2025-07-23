# app/api/mcp.py - MCP 핵심 엔드포인트 구현 (필수 5개 + 고급 기능)
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import httpx
import uuid
import logging
from datetime import datetime
from fastapi import FastAPI, Request
# from fastmcp import FastMCP, jsonrpc_http_handler
import anyio, uuid, json
import asyncio
from app.core.config import settings
from app.core.security import get_current_user, get_optional_user
from app.core.redis import redis_manager
from app.models.mcp_models import (
    JSONRPCRequest, JSONRPCResponse, JSONRPCNotification,
    InitializeParams, InitializeResult, MCPCapabilities, MCPServerInfo,
    ToolsListResult, ToolCallParams, ToolCallResult, MCPTool,
    ResourcesListResult, MCPResource, ResourceReadParams, ResourceReadResult,
    AsyncTask, TaskStatus, TaskResponse, ServerStatus, BridgeStatus,
    MCPErrorCodes, create_error_response, create_success_response
)
from app.tools import extract_url, build_output, summary_question
logger = logging.getLogger(__name__)


# MCP 라우터 생성
mcp_router = APIRouter()
from pydantic import BaseModel


# ==== 1. INITIALIZE (필수 엔드포인트) ====
class RPC(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: dict | None = None


TOOLS: dict[str, callable] = {"web_search":extract_url, "web_data":build_output,
                              "web_qna":summary_question}


def mcp_tool(fn):
    TOOLS[fn.__name__] = fn
    return fn


@mcp_router.post("/")
async def mcp_handler(
        request: Request,
):
    """
    MCP JSON-RPC 2.0 메인 핸들러
    Host(Claude)에서 보내는 모든 MCP 요청을 처리합니다.
    """
    try:
        # API 키 인증 검사
        api_key = request.headers.get("x-api-key")
        if not api_key or api_key not in settings.API_KEYS:
            return JSONResponse({
                "jsonrpc": "2.0",
                "error": {
                    "code": MCPErrorCodes.AUTHENTICATION_FAILED,
                    "message": "인증 실패: 유효한 API 키가 필요합니다"
                }
            }, status_code=401)

        user = None
        payload = await request.json()
        rpc = RPC.model_validate(payload)
        method = rpc.method
        logger.info(f"MCP 요청 수신: {method} ")
        # 메서드별 라우팅
        if method == "initialize":
            return JSONResponse({"jsonrpc": "2.0", "id": rpc.id,
                                 "result": {"protocolVersion": "2025-03-26",
                                            "capabilities": {"tools": {}},
                                            "serverInfo": {"name": "FastAPI MCP", "version": "0.1.0"}}})
        elif method == "notifications/initialized":
            return JSONResponse({"jsonrpc": "2.0", "id": rpc.id})
        elif method == "server/status":
            print()

        elif method == "tools/list":
            meta = [
                {"name": "web_search",
                 "description": "웹 하위 페이지 추출",
                 "inputSchema": {
                     "type": "object",
                     "properties": {
                         "url": {
                             "type": "string",
                             "description": "웹 url"
                         },
                     }
                     }
                 },
                {"name": "web_data",
                 "description": "웹 페이지 데이터화",
                 "inputSchema": {
                     "type": "object",
                     "properties": {
                         "url": {
                             "type": "string",
                             "description": "웹 url"
                         },
                     }
                 }
                 },
                {"name": "web_qna",
                 "description": "사용자가 url과 질문 2개를 입력하면 url 기반 질의응답 출력",
                 "inputSchema": {
                     "type": "object",
                     "properties": {
                         "url": {
                             "type": "string",
                             "description": "웹 url"
                         },
                         "question": {
                             "type": "string",
                             "description": "url 기반 질문"
                         },
                     }
                 }
                 }
            ]
            return JSONResponse({"jsonrpc": "2.0", "id": rpc.id, "result": {"tools": meta}})
        elif method == "tools/call":
            # 도구 호출 시 API 키 인증 필요
            api_key = request.headers.get("x-api-key")
            if not api_key or api_key not in settings.API_KEYS:
                return JSONResponse({
                    "jsonrpc": "2.0", 
                    "id": rpc.id,
                    "error": {
                        "code": MCPErrorCodes.AUTHENTICATION_FAILED, 
                        "message": "인증 실패: 유효한 API 키가 필요합니다"
                    }
                }, status_code=401)

            args = rpc.params.get("arguments", {})
            name = rpc.params["name"]

            # 등록된 도구 호출
            try:
                if name not in TOOLS:
                    return JSONResponse({
                        "jsonrpc": "2.0", 
                        "id": rpc.id,
                        "error": {
                            "code": MCPErrorCodes.TOOL_NOT_FOUND, 
                            "message": f"도구를 찾을 수 없음: {name}"
                        }
                    }, status_code=404)

                # 도구 실행 (비동기 함수는 await, 동기 함수는 to_thread.run_sync 사용)
                func = TOOLS[name]
                result = func(**args)

                # 결과 포맷팅 및 반환
                return JSONResponse({
                    "jsonrpc": "2.0", 
                    "id": rpc.id,
                    "result": {
                        "content": [{"type": "text", "text": result}]
                    }
                })
            except Exception as e:
                logger.error(f"도구 실행 오류: {name}, {str(e)}")
                return JSONResponse({
                    "jsonrpc": "2.0", 
                    "id": rpc.id,
                    "error": {
                        "code": MCPErrorCodes.INTERNAL_ERROR, 
                        "message": f"도구 실행 오류: {str(e)}"
                    }
                }, status_code=500)
        elif method == "resources/list":
            return await handle_resources_list(request, user)
        elif method == "resources/read":
            return await handle_resources_read(request, user)
        else:
            # 지원하지 않는 메서드
            return JSONResponse({"jsonrpc": "2.0", "id": rpc.id,
                                 "error": {"code": -32601, "message": "method not found"}})

    except Exception as e:
        logger.error(f"MCP 핸들러 오류: {e}")
        return create_error_response(
            request,
            MCPErrorCodes.INTERNAL_ERROR,
            "Internal server error"
        )


# 1) Discovery
@mcp_router.get("/mcp/", include_in_schema=False)
async def mcp_discover():
    return {
        "protocolVersion": "2025-06-18",
        "capabilities": {
            "tools": True,
            "resources": False,
            "prompts": False,
            "roots": {"listChanged": False},
            "logging": False
        },
        "serverInfo": {"name": "Web Analyzer MCP", "version": "0.1.0"},
        "endpoints": {"http": {"jsonrpc": "/mcp/rpc"}}
    }


# @mcp_router.post("/mcp/rpc", include_in_schema=False)
# async def mcp_rpc(req: Request):
#     # fastmcp가 제공하는 헬퍼(이름은 사용하는 버전에 따라 다를 수 있음)
#     payload = await req.body()
#     return await jsonrpc_http_handler(mcp, payload)


async def handle_initialize(request: JSONRPCRequest, user: Optional[Dict[str, Any]]):
    """초기화 요청 처리 - 프로토콜 버전과 기능 협상"""
    try:
        # 매개변수 파싱
        if not request.params:
            return create_error_response(
                request.id, MCPErrorCodes.INVALID_PARAMS, "Missing initialization parameters"
            )

        init_params = InitializeParams(**request.params)

        # 프로토콜 버전 확인
        if init_params.protocolVersion != settings.MCP_PROTOCOL_VERSION:
            logger.warning(f"Protocol version mismatch: {init_params.protocolVersion}")

        # 서버 기능 정의
        server_capabilities = MCPCapabilities(
            tools={"listChanged": True},
            resources={"subscribe": True, "listChanged": True},
            prompts={"listChanged": True}
        )

        # 서버 정보 생성
        server_info = MCPServerInfo(
            name="MCP Client Bridge",
            version="1.0.0"
        )

        # 초기화 결과 생성
        result = InitializeResult(
            protocolVersion=settings.MCP_PROTOCOL_VERSION,
            capabilities=server_capabilities,
            serverInfo=server_info
        )

        # 사용자 세션 생성 (인증된 경우)
        if user:
            session_id = str(uuid.uuid4())
            await redis_manager.create_session(session_id, user, ttl=1800)
            logger.info(f"사용자 세션 생성: {session_id}")

        logger.info("MCP 초기화 완료")
        return create_success_response(request.id, result.dict())

    except Exception as e:
        logger.error(f"초기화 처리 오류: {e}")
        return create_error_response(
            request.id, MCPErrorCodes.INTERNAL_ERROR, str(e)
        )


# ==== 2. TOOLS/LIST (필수 엔드포인트) ====

@mcp_router.post("/tools/list")
async def handle_tools_list(request: JSONRPCRequest, user: Optional[Dict[str, Any]]):
    """모든 MCP 서버의 도구 목록을 통합하여 반환"""
    try:
        all_tools = []

        # 각 MCP 서버에서 도구 목록 수집
        async with httpx.AsyncClient(timeout=30.0) as client:
            for server_name, server_config in settings.MCP_SERVERS.items():
                try:
                    server_request = {
                        "jsonrpc": "2.0",
                        "id": f"{request.id}_{server_name}",
                        "method": "tools/list",
                        "params": {}
                    }

                    response = await client.post(
                        f"{server_config['url']}/mcp",
                        json=server_request,
                        headers={"Content-Type": "application/json"}
                    )

                    if response.status_code == 200:
                        server_response = response.json()
                        if "result" in server_response and "tools" in server_response["result"]:
                            # 서버별로 도구 이름에 prefix 추가
                            for tool in server_response["result"]["tools"]:
                                tool_name = f"{server_name}_{tool['name']}"
                                mcp_tool = MCPTool(
                                    name=tool_name,
                                    description=tool.get("description", ""),
                                    server=server_name,
                                    inputSchema=tool.get("inputSchema", {})
                                )
                                all_tools.append(mcp_tool)
                        logger.info(
                            f"서버 {server_name}에서 {len(server_response.get('result', {}).get('tools', []))}개 도구 수집")
                    else:
                        logger.warning(f"서버 {server_name} 응답 실패: {response.status_code}")

                except Exception as e:
                    logger.error(f"서버 {server_name} 연결 실패: {e}")
                    continue

        result = ToolsListResult(tools=all_tools)
        logger.info(f"총 {len(all_tools)}개 도구 반환")
        return create_success_response(request.id, result.dict())

    except Exception as e:
        logger.error(f"도구 목록 처리 오류: {e}")
        return create_error_response(
            request.id, MCPErrorCodes.INTERNAL_ERROR, str(e)
        )


# ==== 3. TOOLS/CALL (필수 엔드포인트) ====

@mcp_router.post("/tools/call")
async def handle_tools_call(
        request: JSONRPCRequest,
        user: Dict[str, Any] = Depends(get_current_user),
        background_tasks: BackgroundTasks = None
):
    """도구 실행 요청 처리 - 동기/비동기 지원"""
    try:
        # 인증 필수
        if not user:
            return create_error_response(
                request.id, MCPErrorCodes.AUTHENTICATION_FAILED, "Authentication required"
            )

        # 매개변수 파싱
        if not request.params:
            return create_error_response(
                request.id, MCPErrorCodes.INVALID_PARAMS, "Missing tool call parameters"
            )

        tool_params = ToolCallParams(**request.params)

        # 도구 이름에서 서버 추출
        if "_" not in tool_params.name:
            return create_error_response(
                request.id, MCPErrorCodes.TOOL_NOT_FOUND, "Invalid tool name format"
            )

        server_name, tool_name = tool_params.name.split("_", 1)

        if server_name not in settings.MCP_SERVERS:
            return create_error_response(
                request.id, MCPErrorCodes.TOOL_NOT_FOUND, f"Server '{server_name}' not found"
            )

        # 긴 작업인지 확인 (예: RAG 검색)
        is_long_task = "rag" in tool_name.lower() or "search" in tool_name.lower()

        if is_long_task:
            # 비동기 처리
            task_id = str(uuid.uuid4())

            # 작업 정보 저장
            task_data = AsyncTask(
                task_id=task_id,
                status=TaskStatus.PENDING,
                server_name=server_name,
                method="tools/call",
                user_id=user["user_id"],
                created_at=datetime.now().isoformat()
            )

            await redis_manager.store_task(task_id, task_data.dict())

            # 백그라운드에서 실행
            background_tasks.add_task(
                execute_tool_async, task_id, server_name, tool_name, tool_params.arguments, user
            )

            # 즉시 task_id 반환
            response = TaskResponse(
                task_id=task_id,
                status=TaskStatus.PENDING,
                message="작업이 백그라운드에서 처리 중입니다."
            )

            return create_success_response(request.id, response.dict())

        else:
            # 동기 처리
            result = await execute_tool_sync(server_name, tool_name, tool_params.arguments)
            return create_success_response(request.id, result)

    except Exception as e:
        logger.error(f"도구 호출 처리 오류: {e}")
        return create_error_response(
            request.id, MCPErrorCodes.INTERNAL_ERROR, str(e)
        )


async def execute_tool_sync(server_name: str, tool_name: str, arguments: Dict[str, Any]):
    """동기적 도구 실행"""
    server_config = settings.MCP_SERVERS[server_name]

    async with httpx.AsyncClient(timeout=60.0) as client:
        server_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        response = await client.post(
            f"{server_config['url']}/mcp",
            json=server_request,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            server_response = response.json()
            return server_response.get("result", {})
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Server {server_name} error"
            )


async def execute_tool_async(
        task_id: str,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
        user: Dict[str, Any]
):
    """비동기적 도구 실행"""
    try:
        # 상태를 RUNNING으로 업데이트
        await redis_manager.update_task_status(task_id, TaskStatus.RUNNING)

        # 실제 도구 실행
        result = await execute_tool_sync(server_name, tool_name, arguments)

        # 성공 결과 저장
        await redis_manager.update_task_status(task_id, TaskStatus.COMPLETED, result)
        logger.info(f"비동기 작업 완료: {task_id}")

    except Exception as e:
        # 실패 결과 저장
        await redis_manager.update_task_status(task_id, TaskStatus.FAILED, str(e))
        logger.error(f"비동기 작업 실패: {task_id}, 오류: {e}")


# ==== 4. RESOURCES/LIST (필수 엔드포인트) ====

@mcp_router.post("/resources/list")
async def handle_resources_list(request: JSONRPCRequest, user: Optional[Dict[str, Any]]):
    """모든 MCP 서버의 리소스 목록을 통합하여 반환"""
    try:
        all_resources = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for server_name, server_config in settings.MCP_SERVERS.items():
                try:
                    server_request = {
                        "jsonrpc": "2.0",
                        "id": f"{request.id}_{server_name}",
                        "method": "resources/list",
                        "params": {}
                    }

                    response = await client.post(
                        f"{server_config['url']}/mcp",
                        json=server_request
                    )

                    if response.status_code == 200:
                        server_response = response.json()
                        if "result" in server_response and "resources" in server_response["result"]:
                            for resource in server_response["result"]["resources"]:
                                mcp_resource = MCPResource(
                                    uri=f"{server_name}://{resource.get('uri', '')}",
                                    name=f"[{server_name}] {resource.get('name', '')}",
                                    description=resource.get("description", ""),
                                    mimeType=resource.get("mimeType")
                                )
                                all_resources.append(mcp_resource)

                except Exception as e:
                    logger.error(f"서버 {server_name} 리소스 조회 실패: {e}")
                    continue

        result = ResourcesListResult(resources=all_resources)
        return create_success_response(request.id, result.dict())

    except Exception as e:
        logger.error(f"리소스 목록 처리 오류: {e}")
        return create_error_response(
            request.id, MCPErrorCodes.INTERNAL_ERROR, str(e)
        )


# ==== 5. RESOURCES/READ (필수 엔드포인트) ====

@mcp_router.post("/resources/read")
async def handle_resources_read(request: JSONRPCRequest, user: Optional[Dict[str, Any]]):
    """리소스 내용 읽기"""
    try:
        if not request.params:
            return create_error_response(
                request.id, MCPErrorCodes.INVALID_PARAMS, "Missing resource URI"
            )

        read_params = ResourceReadParams(**request.params)

        # URI에서 서버 이름 추출
        if "://" not in read_params.uri:
            return create_error_response(
                request.id, MCPErrorCodes.INVALID_PARAMS, "Invalid resource URI format"
            )

        server_name, resource_uri = read_params.uri.split("://", 1)

        if server_name not in settings.MCP_SERVERS:
            return create_error_response(
                request.id, MCPErrorCodes.RESOURCE_NOT_FOUND, f"Server '{server_name}' not found"
            )

        # 해당 서버에 리소스 읽기 요청
        server_config = settings.MCP_SERVERS[server_name]

        async with httpx.AsyncClient(timeout=60.0) as client:
            server_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "resources/read",
                "params": {"uri": resource_uri}
            }

            response = await client.post(
                f"{server_config['url']}/mcp",
                json=server_request
            )

            if response.status_code == 200:
                server_response = response.json()
                return create_success_response(request.id, server_response.get("result", {}))
            else:
                return create_error_response(
                    request.id, MCPErrorCodes.RESOURCE_NOT_FOUND, "Resource read failed"
                )

    except Exception as e:
        logger.error(f"리소스 읽기 처리 오류: {e}")
        return create_error_response(
            request.id, MCPErrorCodes.INTERNAL_ERROR, str(e)
        )


# ==== 추가 기능: 비동기 작업 상태 조회 ====

@mcp_router.get("/task/{task_id}")
async def get_task_status(
        task_id: str,
        user: Dict[str, Any] = Depends(get_current_user)
):
    """비동기 작업 상태 조회"""
    try:
        task_data = await redis_manager.get_task(task_id)

        if not task_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # 작업 소유자 확인
        if task_data.get("user_id") != user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        return AsyncTask(**task_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"작업 상태 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# ==== 추가 기능: 서버 상태 조회 ====

@mcp_router.get("/status")
async def get_bridge_status():
    """MCP Bridge 전체 상태 조회"""
    try:
        servers_status = []

        # 각 서버 상태 확인
        async with httpx.AsyncClient(timeout=10.0) as client:
            for server_name, server_config in settings.MCP_SERVERS.items():
                try:
                    start_time = datetime.now()
                    response = await client.get(f"{server_config['url']}/health")
                    ping_time = datetime.now()

                    if response.status_code == 200:
                        status_info = "healthy"
                    else:
                        status_info = f"unhealthy ({response.status_code})"

                except Exception:
                    status_info = "unreachable"
                    ping_time = None

                server_status = ServerStatus(
                    name=server_config["name"],
                    url=server_config["url"],
                    status=status_info,
                    last_ping=ping_time.isoformat() if ping_time else None,
                    tools_count=0,  # TODO: 실제 도구 수 계산
                    resources_count=0  # TODO: 실제 리소스 수 계산
                )
                servers_status.append(server_status)

        # 전체 상태 생성
        bridge_status = BridgeStatus(
            service="MCP Client Bridge",
            version="1.0.0",
            uptime="N/A",  # TODO: 실제 uptime 계산
            servers=servers_status,
            active_sessions=0,  # TODO: 실제 세션 수 계산
            active_tasks=0  # TODO: 실제 작업 수 계산
        )

        return bridge_status

    except Exception as e:
        logger.error(f"상태 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Status check failed"
        )


# ==== 알림 처리 (notifications/initialized) ====

@mcp_router.post("/initialized")
async def handle_initialized(notification: JSONRPCNotification):
    """초기화 완료 알림 처리"""
    logger.info("MCP 클라이언트 초기화 완료 알림 수신")
    return {"status": "acknowledged"}

