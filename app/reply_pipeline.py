"""One shared rewrite budget across rules and semantic review."""
from time import monotonic
from .dialogue import conflicts,FALLBACK,CONVERSATION_FACT_RULES
from .grounding import grounding_conflicts,scene_conflicts
from .memory_source import source_time_conflicts
from .weather import weather_reply_conflicts,weather_fallback
from .emotion import emotion_reply_conflicts,emotion_fallback
from .semantic_review import needs_review,evidence_bundle,review_reply,rewrite_feedback
from . import weather_presentation as weather_voice
from . import emotion_presentation as emotion_voice
from . import fact_presentation as fact_voice

REWRITE='''\n上次输出违反证据或表达边界。重新回答：保留场景设定授权的温暖氛围、声音和日常动作，只修正无据的重要人物/事件/现实事实或不合角色口吻；无需追究谁翻书，不把普通背景描写改成事实报告。不要再用不知道自家店况的口吻，像熟悉店内环境的沈砚自然接话。地点名称照证据完整写出或用代词承接，不缩写地名。长期记忆不证明刚才/今天告诉我，改用不带来源时间的“我记得”，不要编造讲述时间。以沈砚的自然语气关心，不播报来源/日期，不用您；当前现实天气只作估计。情绪只是可纠正参考，不诊断、不报分数，尊重自述和倾听偏好。'''


async def generate_checked(provider,history,prompt,query,memories,weather,mood,mood_settings,
                           *,judge=None,review_enabled=True,review_timeout=8,companion=False, force_review=False,
                           locale='zh-CN', multilingual_weather=False,multilingual_emotion=False,multilingual_facts=False):
    from . import companion as natural
    from .localization import fixed_reply
    fallback = fixed_reply(natural.FALLBACK if companion else FALLBACK,locale)
    if multilingual_emotion and (not mood_settings.get('enabled',False) or not mood or mood.get('status')=='disabled'):
        mood={'status':'disabled','assessment':None}
    evidence=evidence_bundle(history,memories,weather,mood)
    if multilingual_facts:
        evidence.append({'id':'reply_policy','kind':'reply_policy','data':{'reply_locale':locale}})
    weather_active = multilingual_weather and bool(weather)
    emotion_context=multilingual_emotion and mood_settings.get('enabled',False) and bool(mood) and mood.get('status')!='disabled'
    emotion_active=emotion_context and (bool(mood.get('assessment')) or mood['status']!='waiting')
    if emotion_context:
        evidence=[item for item in evidence if item['id']!='emotion_current']
        view=emotion_voice.assessment_view(mood)
        if view:evidence.append({'id':'emotion_current','kind':'tentative_emotion','data':view})
        evidence.append({'id':'emotion_policy','kind':'emotion_policy','data':emotion_voice.policy(mood,mood_settings,locale)})
    def care_fallback():
        if emotion_active:
            return emotion_voice.combined_fallback(weather,mood,mood_settings,locale) if weather_active else emotion_voice.fallback(mood,mood_settings,locale)
        return fallback
    if weather_active:
        next(e for e in evidence if e['id']=='weather_current')['data'].update(
            demo=weather.get('source','').startswith('mock'),reply_locale=locale)
    guarded=False;review_calls=0;feedback='';review_spent=0.0
    status='disabled' if not review_enabled else 'mock_or_unavailable'
    for attempt in range(2):
        rewrite = (natural.REWRITE if companion else REWRITE+CONVERSATION_FACT_RULES) + (weather_voice.REWRITE if weather_active else '')+(emotion_voice.REWRITE if emotion_context else '')+(fact_voice.REWRITE if multilingual_facts else '')
        reply=await provider.generate(history,prompt+(rewrite+feedback if attempt else ''))
        if (multilingual_facts and attempt == 0 and not (force_review or memories or weather_active or emotion_active)
                and reply in fact_voice.TRUSTED_TEMPLATES.get(locale, ())):
            return reply,False,{'status':'trusted_template','calls':0}
        if weather_active and (judge is None or not review_enabled):
            # No semantic interpretation available: emit bounded tool facts in the
            # selected language instead of treating unreviewed wording as verified.
            return (care_fallback() if emotion_active else weather_voice.fallback(weather,locale)),True,{'status':'weather_safe_fallback','calls':0}
        if emotion_active and (judge is None or not review_enabled):
            return care_fallback(),True,{'status':'emotion_safe_fallback','calls':0}
        if multilingual_facts and (judge is None or not review_enabled):
            return care_fallback(),True,{'status':'reply_safe_fallback','calls':0}
        role_bad=False if multilingual_facts else conflicts(reply,query)
        weather_bad=False if weather_active else weather_reply_conflicts(reply,weather)
        mood_bad=False if emotion_context else emotion_reply_conflicts(reply,mood)
        hard=role_bad or weather_bad or mood_bad
        if multilingual_facts:
            soft=False
        elif companion:
            from .grounding import place_conflicts, protected_places
            soft=place_conflicts(reply,protected_places(memories,query)) or source_time_conflicts(reply,history)
        else:
            soft=grounding_conflicts(reply,memories,query) or source_time_conflicts(reply,history)
        flagged=hard or soft
        guarded=guarded or flagged
        review=None
        factual_scene=False
        if judge is not None and review_enabled:
            required = multilingual_facts or weather_active or emotion_active or force_review or natural.review_required(query,reply,memories,weather,mood,flagged=flagged) if companion else (multilingual_facts or weather_active or emotion_active or force_review or needs_review(reply,evidence=memories,weather=weather,mood=mood,flagged=flagged))
            if required:
                remaining=review_timeout-review_spent
                if remaining<=0:
                    return care_fallback(),True,{'status':'unavailable','calls':review_calls,'failure':'timeout'}
                review_calls+=1
                started=monotonic()
                outcome=await review_reply(judge,reply,history,evidence,timeout=remaining)
                review_spent+=monotonic()-started
                decision,review=outcome
                if decision in ('unavailable','uncertain'):
                    return care_fallback(),True,{'status':decision,'calls':review_calls,'failure':outcome.failure}
                controls=({'reply_policy'} if multilingual_facts else set()) | ({'emotion_policy'} if emotion_context else set())
                if any(controls.intersection(s.evidence_ids) for s in review.segments):
                    return care_fallback(),True,{'status':'unavailable','calls':review_calls,'failure':'unknown_evidence'}
                if weather_active:
                    # Judge attributes the claim; code compares its literal values.
                    # User scores/quotations must not be mistaken for weather data.
                    weather_bad=any(weather_voice.numeric_conflicts(s.text,weather)
                        for s in review.segments if set(s.evidence_ids)=={'weather_current'})
                    hard=role_bad or weather_bad or mood_bad
                # A validated high-confidence accept may correct lexical false
                # positives, but cannot override retained legacy role/tool checks.
                # In fact semantic mode, role/time/place meaning belongs to the judge.
                # Role identity alone cannot prove events. A supported segment
                # citing the explicit fiction license may override legacy scene
                # patterns; semantic scope still depends on the judge.
                factual_scene=bool(not multilingual_facts and not companion and review and any(s.kind in ('assertion','epistemic') and scene_conflicts(s.text)
                    and not (s.verdict=='supported' and 'scene_profile' in s.evidence_ids) for s in review.segments))
                flagged=hard or factual_scene or decision=='revise'
                status='revised' if attempt else 'accepted'
                guarded=guarded or flagged
            else:status='skipped'
        if not flagged:return reply,guarded,{'status':status,'calls':review_calls}
        feedback=fact_voice.feedback(review) if multilingual_facts else rewrite_feedback(review,scene_policy=factual_scene)
        if attempt:
            if emotion_active:reply=care_fallback()
            elif role_bad or soft or factual_scene or (review is not None and review.decision=='revise'):reply=fallback
            elif weather_bad:reply=weather_voice.fallback(weather,locale) if weather_active else weather_fallback(weather)
            elif mood_bad:reply=emotion_fallback(mood,mood_settings)
            else:reply=fallback
            return reply,True,{'status':'fallback','calls':review_calls}
    raise AssertionError('unreachable')
