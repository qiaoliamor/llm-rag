import asyncio
import secrets
import time
from dataclasses import dataclass, field
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import ROOT, Settings
from .dialogue import CHARACTER, FALLBACK, build_provider, ProviderFailure, conflicts, instructions


@dataclass
class Session:
    csrf: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    messages: list = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    touched: float = field(default_factory=time.monotonic)


class ChatInput(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

    @field_validator('message')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('message cannot be blank')
        return value.strip()


def create_app(settings=None, provider=None):
    settings = settings or Settings()
    provider = provider or build_provider(settings)
    app = FastAPI(docs_url=None, redoc_url=None)
    app.state.sessions = sessions = {}
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])

    @app.middleware('http')
    async def protect(request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        if request.method in ('POST', 'DELETE'):
            if request.headers.get('origin') and request.headers['origin'] != str(request.base_url).rstrip('/'):
                return JSONResponse({'detail': '不允许跨站请求。'}, status_code=403)
            try:
                if int(request.headers.get('content-length', '0')) > 16384:
                    return JSONResponse({'detail': '请求过大。'}, status_code=413)
            except ValueError:
                return JSONResponse({'detail': '无效请求。'}, status_code=400)
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 16384:
                    return JSONResponse({'detail': '请求过大。'}, status_code=413)
                chunks.append(chunk)
            request._body = b''.join(chunks)
        response = await call_next(request)
        response.headers.update({'X-Request-ID': request_id, 'Cache-Control': 'no-store',
                                 'X-Content-Type-Options': 'nosniff',
                                 'Content-Security-Policy': "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'"})
        return response

    def get_session(request, mutate=False):
        sid = request.cookies.get('persona_session')
        session = sessions.get(sid)
        if not session or time.monotonic() - session.touched > settings.session_ttl_seconds:
            raise ProviderFailure('session_expired', '会话已过期，请刷新网页。', 401)
        if mutate and not secrets.compare_digest(request.headers.get('x-csrf-token', ''), session.csrf):
            raise ProviderFailure('forbidden', '会话验证失败，请刷新网页。', 403)
        session.touched = time.monotonic()
        return session

    @app.exception_handler(ProviderFailure)
    async def provider_error(request, exc):
        return JSONResponse({'code': exc.code, 'detail': exc.message}, status_code=exc.status)

    @app.get('/')
    async def index():
        return FileResponse(ROOT / 'app/static/index.html')

    @app.get('/v1/session')
    async def bootstrap(request: Request):
        now = time.monotonic()
        for key, value in list(sessions.items()):
            if now - value.touched > settings.session_ttl_seconds and not value.lock.locked():
                del sessions[key]
        sid = request.cookies.get('persona_session')
        if sid not in sessions:
            if len(sessions) >= settings.max_sessions:
                raise ProviderFailure('capacity', '本地会话已满，请稍后重试。', 503)
            sid = secrets.token_urlsafe(32)
            sessions[sid] = Session()
        session = sessions[sid]
        session.touched = now
        response = JSONResponse({'csrf_token': session.csrf, 'messages': session.messages,
                                 'character': CHARACTER, 'provider': settings.chat_provider,
                                 'model': settings.selected_model,
                                 'api_key_env': settings.api_key_env,
                                 'configured': settings.configured})
        response.set_cookie('persona_session', sid, httponly=True, samesite='strict', max_age=settings.session_ttl_seconds)
        return response

    @app.post('/v1/chat')
    async def chat(body: ChatInput, request: Request):
        session = get_session(request, True)
        if session.lock.locked():
            raise ProviderFailure('busy', '上一条消息还在回复，请稍候。', 409)
        async with session.lock:
            history = session.messages[-24:] + [{'role': 'user', 'content': body.message}]
            try:
                async with asyncio.timeout(settings.api_timeout_seconds * 2 + 2):
                    reply = await provider.generate(history, instructions())
                    guarded = conflicts(reply)
                    if guarded:
                        reply = await provider.generate(history, instructions() + '\n上次输出与正史冲突。重新回答，严格遵守已知事实。')
                        if conflicts(reply):
                            reply = FALLBACK
            except TimeoutError:
                raise ProviderFailure('timeout', '模型响应超时，请稍后重试。', 504) from None
            session.messages = (history + [{'role': 'assistant', 'content': reply}])[-24:]
            return {'reply': reply, 'request_id': request.state.request_id, 'guarded': guarded}

    @app.delete('/v1/session')
    async def reset(request: Request):
        session = get_session(request, True)
        if session.lock.locked():
            raise ProviderFailure('busy', '请等待当前回复完成后再清空。', 409)
        session.messages.clear()
        return {'ok': True}

    app.mount('/static', StaticFiles(directory=ROOT / 'app/static'), name='static')
    return app


app = create_app()
