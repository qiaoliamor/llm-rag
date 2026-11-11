import asyncio
import secrets
import time
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import ROOT, Settings
from .memory_routing import route_memory, NO_MEMORY_CONTEXT, Route
from .memory_understanding import understand, select_evidence, ModelMemoryUnderstanding, MemoryMetadata, ExactMemory, MEMORY_CONTEXT_RULES
from .semantic_review import ModelAnalysisProvider
from .reply_pipeline import generate_checked
from . import companion
from .localization import language_prompt, language_provider, fixed_reply
from .progression import Progression
from typing import Literal
from .availability import BUSY_MESSAGE, CHAT_TRANSIENT_CODES, REVIEW_TRANSIENT_FAILURES
from .weather import OpenMeteoProvider, MockWeatherProvider, WeatherError, MESSAGES, query_weather, weather_prompt, validate_city
from .emotion import EmotionState, EmotionSettingsInput, CorrectionInput, Estimate, ModelEmotionProvider, MockEmotionProvider, assess, emotion_prompt, decorate
from .grounding import grounding_prompt
from .memory import MemoryStore, extract_candidates, memory_prompt
from .dialogue import CHARACTER, build_provider, ProviderFailure, instructions


@dataclass
class Session:
    reply_locale: str = "zh-CN"
    user_id: str = ""
    memory_epoch: int = -1
    pending_weather: dict | None = None
    emotion: EmotionState = field(default_factory=EmotionState)
    csrf: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    messages: list = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    touched: float = field(default_factory=time.monotonic)


class ChatInput(BaseModel):
    locale: Literal['zh-CN', 'ja-JP'] = 'zh-CN'
    message: str = Field(min_length=1, max_length=2000)

    @field_validator('message')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('message cannot be blank')
        return value.strip()


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(default='',max_length=40,strict=True)
    email: str = Field(default='',max_length=254,strict=True)
    phone: str = Field(default='',max_length=24,strict=True)

    @field_validator('name','email','phone')
    @classmethod
    def profile_fields(cls, value, info):
        import re
        value=value.strip()
        if value and info.field_name=='email' and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value):
            raise ValueError('invalid email')
        if value and info.field_name=='phone' and not re.fullmatch(r'\+?[0-9 ()-]{5,24}',value):
            raise ValueError('invalid phone')
        return value


class ActionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID


class GiftInput(ActionInput):
    gift_id: Literal['bookmark','tea','lamp']


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


class WeatherSettingsInput(BaseModel):
    enabled: bool
    city_id: int | None = Field(default=None, gt=0)


def create_app(settings=None, provider=None, weather_provider=None, emotion_provider=None, memory_router=None, semantic_judge=None, memory_understander=None):
    settings = settings or Settings()
    provider = provider or build_provider(settings)
    weather = weather_provider or (MockWeatherProvider() if settings.weather_provider == 'mock' else OpenMeteoProvider())
    emotion = emotion_provider or (MockEmotionProvider() if settings.chat_provider == 'mock' else ModelEmotionProvider(settings))
    analysis_type = companion.CompanionAnalysisProvider if settings.dialogue_mode == 'companion' else ModelAnalysisProvider
    auxiliary = analysis_type(settings) if settings.chat_provider != 'mock' else None
    router = memory_router if memory_router is not None else auxiliary
    judge = semantic_judge if semantic_judge is not None else auxiliary
    semantic_memory = settings.memory_understanding_mode == 'semantic'
    memory_understander = memory_understander if memory_understander is not None else (ModelMemoryUnderstanding(settings) if settings.chat_provider != 'mock' else None)
    store = MemoryStore(settings.memory_database_url.get_secret_value())
    growth = Progression(store) if settings.growth_enabled else None
    app = FastAPI(docs_url=None, redoc_url=None)
    app.state.sessions = sessions = {}
    app.state.memory_store = store
    app.state.progression = growth
    app.state.weather_provider = weather
    app.state.emotion_provider = emotion
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
        detail = BUSY_MESSAGE if request.url.path == '/v1/chat' and exc.code in CHAT_TRANSIENT_CODES else exc.message
        return JSONResponse({'code': exc.code, 'detail': detail}, status_code=exc.status)

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
            session.pending_weather = None
            session.emotion = EmotionState()
            session.memory_epoch = current_settings['epoch']
        response = JSONResponse({'csrf_token': session.csrf, 'messages': session.messages,
                                 'character': CHARACTER, 'provider': settings.chat_provider,
                                 'model': settings.selected_model,
                                 'api_key_env': settings.api_key_env,
                                 'configured': settings.configured,
                                 'memory_settings': store.settings(user_id),
                                 **({'account':growth.get(user_id)} if growth else {})})
        response.set_cookie('persona_player', player_token, httponly=True, samesite='strict', max_age=31536000)
        response.set_cookie('persona_session', sid, httponly=True, samesite='strict', max_age=settings.session_ttl_seconds)
        return response

    def verify_epoch(session, expected):
        current = store.settings(session.user_id)['epoch']
        if current != expected:
            session.messages.clear()
            session.pending_weather = None
            # A concurrent user correction may already have installed newer state.
            if session.memory_epoch != current:
                session.emotion = EmotionState()
                session.memory_epoch = current
            raise ProviderFailure('memory_changed', '记忆、天气、情绪或授权已变化，本轮回复已撤销，请重新发送。', 409)

    @app.post('/v1/chat')
    async def chat(body: ChatInput, request: Request):
        session = get_session(request, True)
        if session.lock.locked():
            raise ProviderFailure('busy', '上一条消息还在回复，请稍候。', 409)
        async with session.lock:
            turn_started = growth.clock() if growth else None
            snapshot = store.settings(session.user_id)
            abilities = growth.get(session.user_id)['character']['abilities'] if growth else {'memory':True,'emotion':True,'weather':True}
            if session.memory_epoch != snapshot['epoch']:
                session.messages.clear()
                session.pending_weather = None
                session.emotion = EmotionState()
                session.memory_epoch = snapshot['epoch']
            turn = session.emotion.turn + 1
            history = session.messages[-24:] + [{'role': 'user', 'content': body.message, 'id':f'u{turn}'}]
            understood = None
            selection_status = 'not_requested'
            if semantic_memory:
                memory_deadline = time.monotonic() + settings.memory_understanding_timeout_seconds
                understood = await understand(memory_understander, body.message, history,
                    enabled=snapshot['memory_enabled'] and abilities['memory'], tz=snapshot['timezone'],
                    timeout=settings.memory_understanding_timeout_seconds)
                verify_epoch(session,snapshot['epoch'])
                plan = understood.plan
                route = Route(bool(plan and plan.need_memory), plan.query if plan else '',
                    plan.reason if plan else understood.status, 'semantic')
                evidence = []
                if route.need_memory:
                    candidates = store.semantic_candidates(session.user_id, route.query, target_slots=plan.target_slots)
                    evidence, selection_status = await select_evidence(memory_understander, route.query, history, candidates,
                        timeout=memory_deadline-time.monotonic())
                    verify_epoch(session,snapshot['epoch'])
            else:
                route = await route_memory(body.message, history, enabled=snapshot['memory_enabled'] and abilities['memory'],
                    router=router,timeout=settings.memory_route_timeout_seconds,routing_enabled=settings.memory_router_enabled)
                verify_epoch(session,snapshot['epoch'])
                evidence = store.retrieve(session.user_id, route.query) if route.need_memory else []
            weather_config = store.weather_settings(session.user_id)
            if not abilities['weather']: weather_config={**weather_config,'enabled':False}
            weather_result, pending = await query_weather(weather, body.message, weather_config, session.pending_weather)
            verify_epoch(session, snapshot['epoch'])
            mood_settings = store.emotion_settings(session.user_id)
            if not abilities['emotion']: mood_settings={**mood_settings,'enabled':False}
            mood_result = await assess(emotion, session.emotion, mood_settings, history)
            verify_epoch(session, snapshot['epoch'])
            session.pending_weather = pending
            natural = settings.dialogue_mode == 'companion'
            if natural:
                prompt = companion.instructions() + companion.memory_context(evidence, body.message)
                prompt += weather_prompt(weather_result) + emotion_prompt(mood_result, mood_settings)
            else:
                prompt = instructions() + weather_prompt(weather_result) + memory_prompt(evidence) + emotion_prompt(mood_result, mood_settings) + grounding_prompt(evidence, body.message)
                if not route.need_memory:
                    prompt += NO_MEMORY_CONTEXT
            if semantic_memory and evidence: prompt += MEMORY_CONTEXT_RULES
            prompt += language_prompt(body.locale, previous=session.reply_locale)
            model_history = [{'role':m['role'], 'content':m['content']} for m in history]
            try:
                async with asyncio.timeout(settings.api_timeout_seconds * 2 + settings.semantic_review_timeout_seconds + 2):
                    reply, guarded, review_status = await generate_checked(language_provider(provider,body.locale),model_history,prompt,body.message,
                        evidence,weather_result,mood_result,mood_settings,judge=judge,
                        review_enabled=settings.semantic_review_enabled,review_timeout=settings.semantic_review_timeout_seconds,companion=natural,
                        force_review=semantic_memory and route.need_memory)
            except TimeoutError:
                raise ProviderFailure('timeout', '模型响应超时，请稍后重试。', 504) from None
            verify_epoch(session, snapshot['epoch'])
            if review_status.get('status') == 'unavailable' and review_status.get('failure') in REVIEW_TRANSIENT_FAILURES:
                raise ProviderFailure('review_busy', BUSY_MESSAGE, 503)
            facts = list(understood.candidates) if understood is not None else (extract_candidates(body.message) if snapshot['memory_enabled'] and abilities['memory'] else [])
            reply = fixed_reply(reply, body.locale)
            candidates = []
            account_result = None
            if growth:
                account_result,candidates = growth.complete_turn(session.user_id, turn_started if not guarded else None,
                    facts=facts, source=request.state.request_id, epoch=snapshot['epoch'])
            else:
                for fact in facts:
                    candidate = store.candidate(session.user_id, fact.fact, request.state.request_id, snapshot['epoch'], metadata=fact.metadata) if isinstance(fact, ExactMemory) else store.candidate(session.user_id, fact, request.state.request_id, snapshot['epoch'])
                    if candidate and candidate['status'] == 'candidate': candidates.append(candidate)
            session.reply_locale = body.locale
            session.emotion.turn = turn
            if mood_result['assessment']:
                if mood_result['status'] not in ('cached','user_override'): session.emotion.remember(mood_result['assessment'],turn)
            else: session.emotion.assessment = None
            session.messages = (history + [{'role': 'assistant', 'content': reply, **({'weather': weather_result} if weather_result and weather_result['status'] == 'ok' else {})}])[-24:]
            return {'emotion': mood_result, 'weather': weather_result, 'reply': reply, 'request_id': request.state.request_id, 'guarded': guarded, 'memory_candidates': candidates,
                    **({'account':account_result} if account_result is not None else {}),
                    'retrieved_memory_ids': [m['id'] for m in evidence],
                    'memory_route':route.public(),'semantic_review':review_status,
                    **({'memory_understanding':{**understood.public(), 'selection':selection_status}} if understood is not None else {})}

    @app.delete('/v1/session')
    async def reset(request: Request):
        session = get_session(request, True)
        if session.lock.locked():
            raise ProviderFailure('busy', '请等待当前回复完成后再清空。', 409)
        session.messages.clear()
        session.pending_weather = None
        session.emotion = EmotionState()
        return {'ok': True}

    def invalidate_user_history(uid):
        for value in sessions.values():
            if value.user_id == uid:
                value.messages.clear()
                value.pending_weather = None
                value.emotion = EmotionState()

    @app.get('/v1/memories')
    async def memories(request: Request):
        session = get_session(request)
        return {'items': store.list(session.user_id, strict_fact=True) if semantic_memory else store.list(session.user_id), 'settings': store.settings(session.user_id)}

    async def manual_metadata(fact, session, snapshot):
        if growth: growth.require(session.user_id,'memory')
        if not snapshot['memory_enabled']:
            raise ProviderFailure('memory_disabled','请先开启长期记忆。',409)
        verify_epoch(session,snapshot['epoch'])
        result = await understand(memory_understander, fact, [], enabled=True, tz=snapshot['timezone'],
            timeout=settings.memory_understanding_timeout_seconds, operation='manual_metadata')
        verify_epoch(session,snapshot['epoch'])
        return result.candidates[0].metadata if result.candidates else MemoryMetadata()

    @app.post('/v1/memories')
    async def create_memory(body: MemoryInput, request: Request):
        session = get_session(request, True)
        if growth: growth.require(session.user_id,'memory')
        snapshot = store.settings(session.user_id)
        if not snapshot['memory_enabled']:
            raise ProviderFailure('memory_disabled', '请先开启长期记忆。', 409)
        metadata = await manual_metadata(body.fact, session, snapshot) if semantic_memory else None
        candidate = store.candidate(session.user_id, body.fact, request.state.request_id, snapshot['epoch'], manual=True, metadata=metadata)
        return {'item': candidate}

    @app.patch('/v1/memories/{memory_id}')
    async def edit_memory(memory_id: str, body: MemoryEdit, request: Request):
        session = get_session(request, True)
        if growth and body.confirm: growth.require(session.user_id,'memory')
        if body.keep_both and body.replace_conflicts:
            raise ProviderFailure('invalid_choice', '替换与独立保留只能选择一种。', 422)
        metadata = None
        if semantic_memory and body.fact is not None:
            original = store.validate_edit(session.user_id, memory_id, body.version)
            if original != body.fact:
                metadata = await manual_metadata(body.fact, session, store.settings(session.user_id))
        item = store.mutate(session.user_id, memory_id, body.version, body.fact, body.confirm, body.replace_conflicts, keep_both=body.keep_both, metadata=metadata, strict_fact=semantic_memory)
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
        if growth and body.memory_enabled: growth.require(session.user_id,'memory')
        result = store.configure(session.user_id, body.memory_enabled, body.timezone)
        invalidate_user_history(session.user_id)
        return {'settings': result, 'history_cleared': True}

    @app.exception_handler(WeatherError)
    async def weather_error(request, exc):
        return JSONResponse({'code': 'weather_' + exc.code, 'detail': MESSAGES[exc.code]}, status_code=503 if exc.code in ('timeout', 'unavailable', 'invalid_response', 'rate_limit') else 422)

    @app.get('/v1/weather/settings')
    async def weather_settings(request: Request):
        session = get_session(request)
        return store.weather_settings(session.user_id)

    @app.get('/v1/weather/locations')
    async def weather_locations(request: Request, q: str):
        session=get_session(request)
        if growth: growth.require(session.user_id,'weather')
        validate_city(q)
        return {'items': [p.model_dump() for p in await weather.search(q.strip())]}

    @app.patch('/v1/weather/settings')
    async def configure_weather(body: WeatherSettingsInput, request: Request):
        session = get_session(request, True)
        # Reuse a trusted saved place for consent toggles, so opt-out works offline.
        epoch = store.settings(session.user_id)['epoch']
        saved = store.weather_settings(session.user_id)['place']
        if growth and (body.enabled or (body.city_id is not None and (not saved or saved['id']!=body.city_id))):
            growth.require(session.user_id,'weather')
        place = saved if saved and saved['id'] == body.city_id else ((await weather.place(body.city_id)).model_dump() if body.city_id else None)
        if store.settings(session.user_id)['epoch'] != epoch:
            raise ProviderFailure('memory_changed', '设置已变化，请刷新后重试。', 409)
        result = store.configure_weather(session.user_id, body.enabled, place)
        weather.clear()
        invalidate_user_history(session.user_id)
        return {'settings': result, 'history_cleared': True}

    @app.delete('/v1/weather/settings')
    async def delete_weather_settings(request: Request):
        session = get_session(request, True)
        result = store.configure_weather(session.user_id, remove=True)
        weather.clear()
        invalidate_user_history(session.user_id)
        return {'settings': result, 'history_cleared': True}

    def fresh_emotion_session(request, mutate=False):
        session = get_session(request, mutate)
        epoch = store.settings(session.user_id)['epoch']
        if session.memory_epoch != epoch:
            session.messages.clear()
            session.pending_weather = None
            session.emotion = EmotionState()
            session.memory_epoch = epoch
        return session

    @app.get('/v1/emotion')
    async def emotion_status(request: Request):
        session = fresh_emotion_session(request)
        return {'settings': store.emotion_settings(session.user_id), 'assessment': session.emotion.current()}

    @app.patch('/v1/emotion/settings')
    async def configure_emotion(body: EmotionSettingsInput, request: Request):
        session = get_session(request, True)
        if growth and body.enabled: growth.require(session.user_id,'emotion')
        result = store.configure_emotion(session.user_id, body.model_dump())
        invalidate_user_history(session.user_id)
        return {'settings': result, 'history_cleared': True}

    @app.delete('/v1/emotion/settings')
    async def delete_emotion_settings(request: Request):
        session = get_session(request, True)
        result = store.configure_emotion(session.user_id, remove=True)
        invalidate_user_history(session.user_id)
        return {'settings': result, 'history_cleared': True}

    @app.patch('/v1/emotion/assessment')
    async def correct_emotion(body: CorrectionInput, request: Request):
        session = fresh_emotion_session(request, True)
        if growth: growth.require(session.user_id,'emotion')
        config = store.emotion_settings(session.user_id)
        if not config['enabled']:
            raise ProviderFailure('emotion_disabled', '请先开启情绪分析。', 409)
        store.invalidate(session.user_id)
        invalidate_user_history(session.user_id)
        session.memory_epoch = store.settings(session.user_id)['epoch']
        value = Estimate(labels=[body.label], intensity=.5, confidence=1, evidence_message_ids=[], response_strategy=body.preference)
        result = decorate(value,'user',0)
        session.emotion.remember(result,0)
        return {'assessment': result, 'history_cleared': True}

    @app.delete('/v1/emotion/assessment')
    async def clear_emotion(request: Request):
        session = get_session(request, True)
        store.invalidate(session.user_id)
        invalidate_user_history(session.user_id)
        return {'ok': True, 'history_cleared': True}

    def account_session(request, mutate=False):
        session=get_session(request,mutate)
        if not growth:
            raise ProviderFailure('growth_disabled','此运行模式未开启成长账户。',503)
        return session

    @app.get('/v1/account')
    async def account(request: Request):
        session=account_session(request)
        return growth.get(session.user_id)

    @app.patch('/v1/account/profile')
    async def update_profile(body: ProfileInput, request: Request):
        session=account_session(request,True)
        return growth.profile(session.user_id,body.model_dump())

    @app.delete('/v1/account/profile')
    async def clear_profile(request: Request):
        session=account_session(request,True)
        return growth.profile(session.user_id,{'name':'','email':'','phone':''})

    @app.post('/v1/account/demo-credit')
    async def demo_credit(body: ActionInput, request: Request):
        session=account_session(request,True)
        return growth.action(session.user_id,str(body.request_id))

    @app.post('/v1/characters/{character_id}/gifts')
    async def send_gift(character_id: str, body: GiftInput, request: Request):
        session=account_session(request,True)
        return growth.action(session.user_id,str(body.request_id),body.gift_id,character_id)

    app.mount('/static', StaticFiles(directory=ROOT / 'app/static'), name='static')
    return app


app = create_app()
