import asyncio
import secrets
import time
from dataclasses import dataclass, field
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import ROOT, Settings
from .memory import MemoryStore, extract_candidates, memory_prompt
from .dialogue import CHARACTER, FALLBACK, build_provider, ProviderFailure, conflicts, instructions


@dataclass
class Session:
    user_id: str = ""
    memory_epoch: int = -1
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


class MemoryInput(BaseModel):
    fact: str = Field(min_length=1, max_length=300)

    @field_validator('fact')
    @classmethod
    def fact_nonblank(cls, value):
        if not value.strip(): raise ValueError('fact cannot be blank')
        return value.strip()


class MemoryEdit(BaseModel):
    version: int = Field(ge=1)
    fact: str | None = Field(default=None, min_length=1, max_length=300)
    confirm: bool = False
    replace_conflicts: bool = False
    keep_both: bool = False

    @field_validator('fact')
    @classmethod
    def fact_nonblank(cls, value):
        if value is not None and not value.strip(): raise ValueError('fact cannot be blank')
        return value.strip() if value is not None else None


class MemorySettingsInput(BaseModel):
    memory_enabled: bool
    timezone: str = 'Asia/Tokyo'

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls, value):
        try: ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError): raise ValueError('unknown timezone')
        return value


def create_app(settings=None, provider=None):
    settings = settings or Settings()
    provider = provider or build_provider(settings)
    store = MemoryStore(settings.memory_database_url.get_secret_value())
    app = FastAPI(docs_url=None, redoc_url=None)
    app.state.sessions = sessions = {}
    app.state.memory_store = store
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])

    @app.middleware('http')
    async def protect(request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        if request.method in ('POST', 'PATCH', 'DELETE'):
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
        if not store.is_owner(session.user_id, request.cookies.get('persona_player')):
            raise ProviderFailure('identity_mismatch', '本地身份已变化，请刷新网页。', 401)
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
        user_id, player_token = store.identity(request.cookies.get('persona_player'))
        sid = request.cookies.get('persona_session')
        if sid not in sessions or sessions[sid].user_id != user_id:
            if len(sessions) >= settings.max_sessions:
                raise ProviderFailure('capacity', '本地会话已满，请稍后重试。', 503)
            sid = secrets.token_urlsafe(32)
            sessions[sid] = Session(user_id=user_id)
        session = sessions[sid]
        session.touched = now
        current_settings = store.settings(user_id)
        if session.memory_epoch != current_settings['epoch']:
            session.messages.clear()
            session.memory_epoch = current_settings['epoch']
        response = JSONResponse({'csrf_token': session.csrf, 'messages': session.messages,
                                 'character': CHARACTER, 'provider': settings.chat_provider,
                                 'model': settings.selected_model,
                                 'api_key_env': settings.api_key_env,
                                 'configured': settings.configured,
                                 'memory_settings': store.settings(user_id)})
        response.set_cookie('persona_player', player_token, httponly=True, samesite='strict', max_age=31536000)
        response.set_cookie('persona_session', sid, httponly=True, samesite='strict', max_age=settings.session_ttl_seconds)
        return response

    @app.post('/v1/chat')
    async def chat(body: ChatInput, request: Request):
        session = get_session(request, True)
        if session.lock.locked():
            raise ProviderFailure('busy', '上一条消息还在回复，请稍候。', 409)
        async with session.lock:
            snapshot = store.settings(session.user_id)
            if session.memory_epoch != snapshot['epoch']:
                session.messages.clear()
                session.memory_epoch = snapshot['epoch']
            history = session.messages[-24:] + [{'role': 'user', 'content': body.message}]
            evidence = store.retrieve(session.user_id, body.message)
            prompt = instructions() + memory_prompt(evidence)
            try:
                async with asyncio.timeout(settings.api_timeout_seconds * 2 + 2):
                    reply = await provider.generate(history, prompt)
                    guarded = conflicts(reply)
                    if guarded:
                        reply = await provider.generate(history, prompt + '\n上次输出与正史冲突。重新回答，严格遵守已知事实。')
                        if conflicts(reply):
                            reply = FALLBACK
            except TimeoutError:
                raise ProviderFailure('timeout', '模型响应超时，请稍后重试。', 504) from None
            if store.settings(session.user_id)['epoch'] != snapshot['epoch']:
                session.messages.clear()
                raise ProviderFailure('memory_changed', '记忆或授权已变化，本轮回复已撤销，请重新发送。', 409)
            candidates = []
            if snapshot['memory_enabled']:
                for fact in extract_candidates(body.message):
                    candidate = store.candidate(session.user_id, fact, request.state.request_id, snapshot['epoch'])
                    if candidate and candidate['status'] == 'candidate': candidates.append(candidate)
            session.messages = (history + [{'role': 'assistant', 'content': reply}])[-24:]
            return {'reply': reply, 'request_id': request.state.request_id, 'guarded': guarded, 'memory_candidates': candidates,
                    'retrieved_memory_ids': [m['id'] for m in evidence]}

    @app.delete('/v1/session')
    async def reset(request: Request):
        session = get_session(request, True)
        if session.lock.locked():
            raise ProviderFailure('busy', '请等待当前回复完成后再清空。', 409)
        session.messages.clear()
        return {'ok': True}

    def invalidate_user_history(uid):
        for value in sessions.values():
            if value.user_id == uid:
                value.messages.clear()

    @app.get('/v1/memories')
    async def memories(request: Request):
        session = get_session(request)
        return {'items': store.list(session.user_id), 'settings': store.settings(session.user_id)}

    @app.post('/v1/memories')
    async def create_memory(body: MemoryInput, request: Request):
        session = get_session(request, True)
        snapshot = store.settings(session.user_id)
        if not snapshot['memory_enabled']:
            raise ProviderFailure('memory_disabled', '请先开启长期记忆。', 409)
        candidate = store.candidate(session.user_id, body.fact, request.state.request_id, snapshot['epoch'], manual=True)
        return {'item': candidate}

    @app.patch('/v1/memories/{memory_id}')
    async def edit_memory(memory_id: str, body: MemoryEdit, request: Request):
        session = get_session(request, True)
        if body.keep_both and body.replace_conflicts:
            raise ProviderFailure('invalid_choice', '替换与独立保留只能选择一种。', 422)
        item = store.mutate(session.user_id, memory_id, body.version, body.fact, body.confirm, body.replace_conflicts, keep_both=body.keep_both)
        invalidate_user_history(session.user_id)
        return {'item': item, 'history_cleared': True}

    @app.delete('/v1/memories/{memory_id}')
    async def delete_memory(memory_id: str, version: int, request: Request):
        session = get_session(request, True)
        store.mutate(session.user_id, memory_id, version, delete=True)
        invalidate_user_history(session.user_id)
        return {'ok': True, 'history_cleared': True}

    @app.delete('/v1/memories')
    async def clear_memories(request: Request):
        session = get_session(request, True)
        store.clear(session.user_id)
        invalidate_user_history(session.user_id)
        return {'ok': True, 'history_cleared': True}

    @app.patch('/v1/settings')
    async def configure_memory(body: MemorySettingsInput, request: Request):
        session = get_session(request, True)
        result = store.configure(session.user_id, body.memory_enabled, body.timezone)
        invalidate_user_history(session.user_id)
        return {'settings': result, 'history_cleared': True}

    @app.get('/v1/project')
    async def project_progress():
        return {'todo': (ROOT / 'TODOLIST.md').read_text(), 'plan': (ROOT / 'docs/PLAN.md').read_text()}

    app.mount('/static', StaticFiles(directory=ROOT / 'app/static'), name='static')
    return app


app = create_app()
