"""One shared rewrite budget across rules and semantic review."""
from time import monotonic
from .dialogue import conflicts,FALLBACK,CONVERSATION_FACT_RULES
from .grounding import grounding_conflicts,scene_conflicts
from .memory_source import source_time_conflicts
from .weather import weather_reply_conflicts,weather_fallback
from .emotion import emotion_reply_conflicts,emotion_fallback
from .semantic_review import needs_review,evidence_bundle,review_reply,rewrite_feedback

REWRITE='''\n上次输出违反证据或表达边界。重新回答：保留场景设定授权的温暖氛围，删除无据的具体事件或玩家经历；不要再用不知道自家店况的口吻，像熟悉店内环境的沈砚自然接话。地点名称照证据完整写出或用代词承接，不缩写地名。长期记忆不证明刚才/今天告诉我，改用不带来源时间的“我记得”，不要编造讲述时间。以沈砚的自然语气关心，不播报来源/日期，不用您；当前现实天气只作估计。情绪只是可纠正参考，不诊断、不报分数，尊重自述和倾听偏好。'''


async def generate_checked(provider,history,prompt,query,memories,weather,mood,mood_settings,
                           *,judge=None,review_enabled=True,review_timeout=8):
    evidence=evidence_bundle(history,memories,weather,mood)
    guarded=False;review_calls=0;feedback='';review_spent=0.0
    status='disabled' if not review_enabled else 'mock_or_unavailable'
    for attempt in range(2):
        reply=await provider.generate(history,prompt+(REWRITE+CONVERSATION_FACT_RULES+feedback if attempt else ''))
        role_bad=conflicts(reply,query)
        weather_bad=weather_reply_conflicts(reply,weather)
        mood_bad=emotion_reply_conflicts(reply,mood)
        hard=role_bad or weather_bad or mood_bad
        soft=grounding_conflicts(reply,memories,query) or source_time_conflicts(reply,history)
        flagged=hard or soft
        guarded=guarded or flagged
        review=None
        factual_scene=False
        if judge is not None and review_enabled:
            if needs_review(reply,evidence=memories,weather=weather,mood=mood,flagged=flagged):
                remaining=review_timeout-review_spent
                if remaining<=0:
                    return FALLBACK,True,{'status':'unavailable','calls':review_calls,'failure':'timeout'}
                review_calls+=1
                started=monotonic()
                outcome=await review_reply(judge,reply,history,evidence,timeout=remaining)
                review_spent+=monotonic()-started
                decision,review=outcome
                if decision in ('unavailable','uncertain'):
                    return FALLBACK,True,{'status':decision,'calls':review_calls,'failure':outcome.failure}
                # A validated high-confidence accept may correct lexical false
                # positives, but cannot override hard role/tool constraints.
                # Role identity alone cannot prove events. A supported segment
                # citing the explicit fiction license may override legacy scene
                # patterns; semantic scope still depends on the judge.
                factual_scene=bool(review and any(s.kind in ('assertion','epistemic') and scene_conflicts(s.text)
                    and not (s.verdict=='supported' and 'scene_profile' in s.evidence_ids) for s in review.segments))
                flagged=hard or factual_scene or decision=='revise'
                status='revised' if attempt else 'accepted'
                guarded=guarded or decision=='revise'
            else:status='skipped'
        if not flagged:return reply,guarded,{'status':status,'calls':review_calls}
        feedback=rewrite_feedback(review,scene_policy=factual_scene)
        if attempt:
            if role_bad or soft or factual_scene or (review is not None and review.decision=='revise'):reply=FALLBACK
            elif weather_bad:reply=weather_fallback(weather)
            elif mood_bad:reply=emotion_fallback(mood,mood_settings)
            else:reply=FALLBACK
            return reply,True,{'status':'fallback','calls':review_calls}
    raise AssertionError('unreachable')
